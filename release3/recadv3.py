#!/usr/bin/env python3

from datetime import datetime
import uuid
from typing import List, Dict, Any, Optional, Union
import os
import tempfile
import shutil
import re
from pathlib import Path


class RecadvGenerator:
    def __init__(
        self,
        *,
        carrier: str = "CarrierX",
        delivery_location: str = "DEHAM",
        buyer_ean: str = "5412345000176",
        supplier_ean: str = "4012345500004",
        reference_number: str = "123456789",
        output_dir: str = "output",
        document_number: str = "RECADV001",
        verbose: bool = False,
    ):
        self.message: List[str] = []
        self.message_ref: str = ""
        self.carrier = self._sanitize_string(carrier)
        self.delivery_location = self._sanitize_string(delivery_location)
        self.buyer_ean = self._validate_ean(buyer_ean)
        self.supplier_ean = self._validate_ean(supplier_ean)
        self.reference_number = self._sanitize_string(reference_number)
        self.document_number = self._sanitize_string(document_number)
        self.output_dir = self._validate_output_dir(output_dir)
        self.verbose = verbose

    def _sanitize_string(self, value: str) -> str:
        if not isinstance(value, str):
            raise ValueError(f"Expected string, got {type(value)}")
        return re.sub(r'[^\w\s\-\.]', '', value.strip())

    def _validate_output_dir(self, output_dir: str) -> Path:
        path = Path(output_dir).resolve()
        try:
            path.mkdir(parents=True, exist_ok=True)
            test_file = path / ".write_test"
            test_file.touch()
            test_file.unlink()
            return path
        except (OSError, PermissionError) as e:
            raise ValueError(f"Cannot write to output directory {output_dir}: {e}")

    def _generate_message_reference(self) -> str:
        return datetime.now().strftime("%Y%m%d%H%M") + uuid.uuid4().hex[:8]

    def _validate_ean(self, ean: str) -> str:
        if not isinstance(ean, str):
            raise ValueError(f"EAN must be string, got {type(ean)}")
        ean = ean.strip()
        if not (ean.isdigit() and len(ean) == 13):
            raise ValueError(f"Invalid EAN: {ean}. Must be 13 digits.")
        return ean

    def _validate_quantity(self, qty: Union[str, int]) -> str:
        if isinstance(qty, int):
            if qty < 0:
                raise ValueError(f"Quantity cannot be negative: {qty}")
            return str(qty)
        elif isinstance(qty, str):
            if not qty.isdigit():
                raise ValueError(f"Quantity must be numeric, got: {qty}")
            if int(qty) < 0:
                raise ValueError(f"Quantity cannot be negative: {qty}")
            return qty
        else:
            raise ValueError(f"Quantity must be string or integer, got {type(qty)}")

    def _escape_edifact(self, value: Any) -> str:
        if value is None:
            return ""
        value_str = str(value)
        return value_str.replace("?", "??").replace("'", "?'").replace(":", "?:").replace("+", "?+")

    def _segment(self, tag: str, *elements: Any) -> str:
        escaped_elements = [self._escape_edifact(e) for e in elements if e not in ("", None)]
        return f"{tag}+{'+'.join(escaped_elements)}'"

    def add_una_segment(self) -> None:
        self.message.append("UNA:+.? '")

    def add_header(self) -> None:
        self.message.append(self._segment("UNH", self.message_ref, "RECADV:D:96A:UN:EAN008"))
        self.message.append(self._segment("BGM", "351", self.document_number, "9"))
        self.message.append(self._segment("DTM", f"137:{datetime.now().strftime('%Y%m%d%H%M')}:203"))
        self.message.append(self._segment("RFF", f"DQ:{self.reference_number}"))

    def add_party(self, qualifier: str, ean: str) -> None:
        self.message.append(self._segment("NAD", qualifier, f"{self._validate_ean(ean)}::9"))

    def add_default_parties(self) -> None:
        self.add_party("BY", self.buyer_ean)
        self.add_party("SU", self.supplier_ean)

    def add_transport_details(self) -> None:
        self.message.append(self._segment("TDT", "20", "", "", "31", "", self.carrier))
        self.message.append(self._segment("LOC", "9", self.delivery_location))

    def add_line_item(
        self,
        line_no: str,
        ean: str,
        qty: Union[str, int],
        cartons: int = 1,
        weight: str = "KGM:6.5",
    ) -> None:
        if not isinstance(line_no, str) or not line_no.strip():
            raise ValueError(f"Line number must be non-empty string, got: {line_no}")

        validated_ean = self._validate_ean(ean)
        validated_qty = self._validate_quantity(qty)

        if not isinstance(cartons, int) or cartons < 1:
            raise ValueError(f"Cartons must be positive integer, got: {cartons}")

        if not isinstance(weight, str) or ":" not in weight:
            raise ValueError(f"Weight must be in format 'UNIT:VALUE', got: {weight}")

        self.message.append(self._segment("LIN", line_no.strip(), "", f"EN:{validated_ean}"))
        self.message.append(self._segment("QTY", f"113:{validated_qty}"))
        self.message.append(self._segment("PAC", str(cartons), "CT"))
        self.message.append(self._segment("MEA", "AAE", "G", weight))

    def add_trailer(self) -> None:
        segment_count = len(self.message) + 1
        self.message.append(self._segment("UNT", str(segment_count), self.message_ref))

    def validate_line_items(self, line_items: List[Dict[str, Any]]) -> None:
        if not line_items:
            raise ValueError("At least one line item is required")

        if not isinstance(line_items, list):
            raise ValueError(f"Line items must be a list, got {type(line_items)}")

        seen_line_numbers = set()
        for i, item in enumerate(line_items):
            if not isinstance(item, dict):
                raise ValueError(f"Line item {i} must be a dictionary, got {type(item)}")

            required_fields = {"line_no", "ean", "qty"}
            missing_fields = required_fields - set(item.keys())
            if missing_fields:
                raise ValueError(f"Line item {i} missing required fields: {missing_fields}")

            line_no = item["line_no"]
            if line_no in seen_line_numbers:
                raise ValueError(f"Duplicate line number: {line_no}")
            seen_line_numbers.add(line_no)

    def generate(self, line_items: List[Dict[str, Any]], as_list: bool = False) -> Union[str, List[str]]:
        self.validate_line_items(line_items)

        self.message.clear()
        self.message_ref = self._generate_message_reference()

        self.add_una_segment()
        self.add_header()
        self.add_default_parties()
        self.add_transport_details()

        for item in line_items:
            self.add_line_item(
                item["line_no"],
                item["ean"],
                item["qty"],
                item.get("cartons", 1),
                item.get("weight", "KGM:6.5"),
            )

        self.add_trailer()

        if self.verbose:
            print("Generated segments:")
            for seg in self.message:
                print(seg)

        return self.message if as_list else "\n".join(self.message)

    def generate_and_save(self, line_items: List[Dict[str, Any]], filename: Optional[str] = None) -> str:
        edi_content = self.generate(line_items)
        
        if filename is None:
            filename = f"RECADV_{self.message_ref}.edi"
        else:
            filename = self._sanitize_string(filename)
            if not filename.endswith('.edi'):
                filename += '.edi'

        safe_filename = re.sub(r'[^\w\.\-]', '_', filename)
        filepath = self.output_dir / safe_filename

        tmp_file = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", 
                delete=False, 
                dir=str(self.output_dir), 
                encoding="utf-8",
                suffix=".tmp"
            ) as tmp:
                tmp.write(edi_content)
                tmp_file = tmp.name

            shutil.move(tmp_file, str(filepath))
            tmp_file = None

        except Exception as e:
            raise RuntimeError(f"Failed to save EDI file: {e}")
        finally:
            if tmp_file and os.path.exists(tmp_file):
                try:
                    os.remove(tmp_file)
                except OSError:
                    pass

        return str(filepath)


if __name__ == "__main__":
    items = [
        {"line_no": "1", "ean": "4000862141404", "qty": "12", "cartons": 2, "weight": "KGM:12.0"},
        {"line_no": "2", "ean": "4000862141405", "qty": "5"},
    ]

    generator = RecadvGenerator(
        carrier="OceanFreight",
        delivery_location="USNYC",
        buyer_ean="5412345000176",
        supplier_ean="4012345500004",
        output_dir="edi_files",
        document_number="RECADV2025-01",
        verbose=True,
    )

    try:
        recadv_message = generator.generate(items)
        print("\nFinal Message:\n", recadv_message)

        saved_path = generator.generate_and_save(items)
        print(f"\nSaved to: {saved_path}")

    except (ValueError, RuntimeError) as e:
        print(f"Error generating RECADV: {e}")
