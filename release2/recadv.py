from datetime import datetime
import uuid
from typing import List, Dict, Any, Optional, Union
import os
import tempfile
import shutil


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
        self.message_ref: str = ""  # Generated fresh each message
        self.carrier = carrier
        self.delivery_location = delivery_location
        self.buyer_ean = self._validate_ean(buyer_ean)
        self.supplier_ean = self._validate_ean(supplier_ean)
        self.reference_number = reference_number
        self.document_number = document_number
        self.output_dir = output_dir
        self.verbose = verbose
        os.makedirs(self.output_dir, exist_ok=True)

    def _generate_message_reference(self) -> str:
        """Generate a unique message reference (timestamp + short UUID)."""
        return datetime.now().strftime("%Y%m%d%H%M") + uuid.uuid4().hex[:8]

    def _validate_ean(self, ean: str) -> str:
        if not (ean.isdigit() and len(ean) == 13):
            raise ValueError(f"Invalid EAN: {ean}. Must be 13 digits.")
        return ean

    def _segment(self, tag: str, *elements: Any) -> str:
        """Format EDIFACT segment, trimming redundant '+' at the end."""
        escaped = [
            str(e).replace("?", "??").replace("'", "?'").replace(":", "?:")
            for e in elements if e != "" and e is not None
        ]
        segment = f"{tag}+{'+'.join(escaped)}'"
        return segment

    def add_una_segment(self) -> None:
        self.message.append("UNA:+.? '")

    def add_header(self) -> None:
        self.message.append(self._segment("UNH", self.message_ref, "RECADV:D:96A:UN:EAN008"))
        self.message.append(self._segment("BGM", "351", self.document_number, "9"))
        self.message.append(self._segment("DTM", f"137:{datetime.now().strftime('%Y%m%d%H%M')}:203"))
        self.message.append(self._segment("RFF", f"DQ:{self.reference_number}"))

    def add_party(self, qualifier: str, ean: str) -> None:
        self._validate_ean(ean)
        self.message.append(self._segment("NAD", qualifier, f"{ean}::9"))

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
        self._validate_ean(ean)
        qty_str = str(qty)
        if not qty_str.isdigit():
            raise ValueError(f"Quantity must be numeric, got: {qty}")

        self.message.append(self._segment("LIN", line_no, "", f"EN:{ean}"))
        self.message.append(self._segment("QTY", f"113:{qty_str}"))
        self.message.append(self._segment("PAC", str(cartons), "CT"))
        self.message.append(self._segment("MEA", "AAE", "G", weight))

    def add_trailer(self) -> None:
        segment_count = len(self.message) + 1
        self.message.append(self._segment("UNT", str(segment_count), self.message_ref))

    def generate(self, line_items: List[Dict[str, Any]], as_list: bool = False) -> Union[str, List[str]]:
        if not line_items:
            raise ValueError("At least one line item is required.")

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
        filename = filename or f"RECADV_{self.message_ref}.edi"
        filepath = os.path.join(self.output_dir, filename)

        # Write safely via temporary file
        tmp_file = None
        try:
            with tempfile.NamedTemporaryFile("w", delete=False, dir=self.output_dir, encoding="utf-8") as tmp:
                tmp.write(edi_content)
                tmp_file = tmp.name
            shutil.move(tmp_file, filepath)
        finally:
            if tmp_file and os.path.exists(tmp_file):
                os.remove(tmp_file)

        return filepath


# Example usage
if __name__ == "__main__":
    items = [
        {"line_no": "1", "ean": "4000862141404", "qty": "12", "cartons": 2, "weight": "KGM:12.0"},
        {"line_no": "2", "ean": "4000862141405", "qty": "5"},  # uses defaults
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

    except ValueError as e:
        print(f"Error generating RECADV: {e}")
