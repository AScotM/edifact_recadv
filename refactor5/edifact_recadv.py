from datetime import datetime
import uuid
from typing import List, Dict, Any, Optional
import os

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
    ):
        """
        Initialize the RECADV generator with configurable defaults.

        Args:
            carrier: Name of the carrier (default: "CarrierX").
            delivery_location: UN/LOCODE for delivery location (default: "DEHAM").
            buyer_ean: Buyer's EAN (13 digits, default: "5412345000176").
            supplier_ean: Supplier's EAN (13 digits, default: "4012345500004").
            reference_number: Reference number for RFF segment (default: "123456789").
            output_dir: Directory to save .edi files (default: "output").
        """
        self.message: List[str] = []
        self.message_ref = self._generate_message_reference()
        self.carrier = carrier
        self.delivery_location = delivery_location
        self.buyer_ean = self._validate_ean(buyer_ean)
        self.supplier_ean = self._validate_ean(supplier_ean)
        self.reference_number = reference_number
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)  # Ensure output dir exists

    def _generate_message_reference(self) -> str:
        """Generate a unique message reference (timestamp + UUID suffix)."""
        return datetime.now().strftime("%Y%m%d%H%M") + str(uuid.uuid4().int)[:4]

    def _validate_ean(self, ean: str) -> str:
        """Validate EAN (must be 13 digits)."""
        if not (ean.isdigit() and len(ean) == 13):
            raise ValueError(f"Invalid EAN: {ean}. Must be 13 digits.")
        return ean

    def _segment(self, tag: str, *elements: Any) -> str:
        """
        Format an EDIFACT segment with escaping for special characters.
        Example: _segment("LIN", "1", "", "EN:4000862141404") -> "LIN+1++EN:4000862141404'"
        """
        escaped = [
            str(e).replace("?", "??").replace("'", "?'").replace(":", "?:")
            for e in elements
        ]
        return f"{tag}+{'+'.join(escaped)}'"

    def add_una_segment(self) -> None:
        """Add the UNA service segment (defines delimiters)."""
        self.message.append("UNA:+.? '")

    def add_header(self) -> None:
        """Add the header segments (UNH, BGM, DTM, RFF)."""
        self.message.append(
            self._segment("UNH", self.message_ref, "RECADV:D:96A:UN:EAN008")
        )
        self.message.append(self._segment("BGM", "351", "RECADV001", "9"))
        self.message.append(
            self._segment("DTM", f"137:{datetime.now().strftime('%Y%m%d:%H%M')}:203")
        )
        self.message.append(self._segment("RFF", f"DQ:{self.reference_number}"))

    def add_parties(self) -> None:
        """Add NAD segments for buyer and supplier."""
        self.message.append(self._segment("NAD", "BY", f"{self.buyer_ean}::9"))
        self.message.append(self._segment("NAD", "SU", f"{self.supplier_ean}::9"))

    def add_transport_details(self) -> None:
        """Add transport (TDT) and location (LOC) segments."""
        self.message.append(
            self._segment("TDT", "20", "", "", "31", "", self.carrier)
        )
        self.message.append(self._segment("LOC", "9", self.delivery_location))

    def add_line_item(self, line_no: str, ean: str, qty: str) -> None:
        """
        Add segments for a single line item (LIN, QTY, PAC, MEA).

        Args:
            line_no: Line item number (e.g., "1").
            ean: Product EAN (13 digits).
            qty: Quantity received.
        """
        self._validate_ean(ean)  # Validate EAN before adding
        self.message.append(self._segment("LIN", line_no, "", f"EN:{ean}"))
        self.message.append(self._segment("QTY", f"113:{qty}"))
        self.message.append(self._segment("PAC", "1", "CT"))  # 1 carton
        self.message.append(self._segment("MEA", "AAE", "G", "KGM:6.5"))  # 6.5 kg gross weight

    def add_trailer(self) -> None:
        """Add the UNT trailer segment (counts segments + message reference)."""
        segment_count = len(self.message) + 1  # Includes UNT itself
        self.message.append(self._segment("UNT", str(segment_count), self.message_ref))

    def generate(self, line_items: List[Dict[str, str]]) -> str:
        """
        Generate the full RECADV message.

        Args:
            line_items: List of dicts with keys: line_no, ean, qty.

        Returns:
            The complete EDIFACT message as a string.

        Raises:
            ValueError: If line_items is empty or invalid.
        """
        if not line_items:
            raise ValueError("At least one line item is required.")

        self.message.clear()  # Reset for reusability
        self.add_una_segment()
        self.add_header()
        self.add_parties()
        self.add_transport_details()

        for item in line_items:
            self.add_line_item(item["line_no"], item["ean"], item["qty"])

        self.add_trailer()
        return "\n".join(self.message)

    def generate_and_save(
        self,
        line_items: List[Dict[str, str]],
        filename: Optional[str] = None,
    ) -> str:
        """
        Generate the RECADV message and save it to an .edi file.

        Args:
            line_items: List of dicts with keys: line_no, ean, qty.
            filename: Custom filename (default: "RECADV_<message_ref>.edi").

        Returns:
            Path to the saved .edi file.

        Raises:
            ValueError: If line_items is empty or invalid.
        """
        edi_content = self.generate(line_items)
        filename = filename or f"RECADV_{self.message_ref}.edi"
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(edi_content)

        return filepath

# Example Usage
if __name__ == "__main__":
    items = [
        {"line_no": "1", "ean": "4000862141404", "qty": "12"},
        {"line_no": "2", "ean": "4000862141405", "qty": "5"},
    ]

    generator = RecadvGenerator(
        carrier="OceanFreight",
        delivery_location="USNYC",
        buyer_ean="5412345000176",
        supplier_ean="4012345500004",
        output_dir="edi_files",  # Saves to ./edi_files/
    )

    try:
        # Generate and print (optional)
        recadv_message = generator.generate(items)
        print(recadv_message)

        # Save to .edi file (automatically uses message_ref in filename)
        saved_path = generator.generate_and_save(items)
        print(f"\nSaved to: {saved_path}")

    except ValueError as e:
        print(f"Error generating RECADV: {e}")
