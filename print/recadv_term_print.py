from datetime import datetime
import uuid
from typing import List, Dict, Any

def edifact_escape(value: str) -> str:
    """
    Escapes EDIFACT special characters.
    This is a basic implementation; adjust as needed for your requirements.
    """
    if not isinstance(value, str):
        return value
    return value.replace("'", "?").replace("+", "?").replace(":", "?")

class RecadvGenerator:
    """
    Generates a simplified EDIFACT RECADV (Receiving Advice) message.
    """

    def __init__(
        self,
        buyer_code: str = "5412345000176::9",
        supplier_code: str = "4012345500004::9",
        carrier: str = "CarrierX",
        delivery_location: str = "DEHAM",
        reference: str = "DQ:123456789"
    ):
        self.buyer_code = buyer_code
        self.supplier_code = supplier_code
        self.carrier = carrier
        self.delivery_location = delivery_location
        self.reference = reference

    def _generate_message_reference(self) -> str:
        """
        Generates a unique message reference using the current timestamp and a UUID.
        """
        return datetime.now().strftime("%Y%m%d%H%M") + str(uuid.uuid4().int)[:4]

    def _segment(self, tag: str, *elements: Any) -> str:
        """
        Formats a segment according to EDIFACT syntax.
        """
        elements_escaped = [edifact_escape(str(e)) if e is not None else "" for e in elements]
        return f"{tag}+{'+'.join(elements_escaped)}'"

    def add_una_segment(self, message: List[str]) -> None:
        """
        Adds the UNA service string advice segment.
        """
        message.append("UNA:+.? '")

    def add_header(self, message: List[str], message_ref: str) -> None:
        """
        Adds header segments (UNH, BGM, DTM, RFF).
        """
        message.append(self._segment("UNH", message_ref, "RECADV:D:96A:UN:EAN008"))
        message.append(self._segment("BGM", "351", "RECADV001", "9"))
        message.append(self._segment("DTM", f"137:{datetime.now().strftime('%Y%m%d:%H%M')}:203"))
        message.append(self._segment("RFF", self.reference))

    def add_parties(self, message: List[str]) -> None:
        """
        Adds party segments (NAD).
        """
        message.append(self._segment("NAD", "BY", self.buyer_code))
        message.append(self._segment("NAD", "SU", self.supplier_code))

    def add_transport_details(self, message: List[str]) -> None:
        """
        Adds transport details (TDT, LOC).
        """
        message.append(self._segment("TDT", "20", "", "", "31", "", self.carrier))
        message.append(self._segment("LOC", "9", self.delivery_location))

    def add_line_items(self, message: List[str], line_items: List[Dict[str, str]]) -> None:
        """
        Adds line items (LIN, QTY, PAC, MEA).
        """
        for item in line_items:
            message.append(self._segment("LIN", item.get("line_no", ""), "", f"EN:{item.get('ean', '')}"))
            message.append(self._segment("QTY", f"113:{item.get('qty', '')}"))
            message.append(self._segment("PAC", "1", "CT"))
            message.append(self._segment("MEA", "AAE", "G", "KGM:6.5"))

    def add_trailer(self, message: List[str], segment_count: int, message_ref: str) -> None:
        """
        Adds the trailer (UNT) segment.
        """
        message.append(self._segment("UNT", str(segment_count), message_ref))

    def generate(self, line_items: List[Dict[str, str]]) -> str:
        """
        Generates the full RECADV message as a string.
        """
        message: List[str] = []
        message_ref = self._generate_message_reference()
        self.add_una_segment(message)
        self.add_header(message, message_ref)
        self.add_parties(message)
        self.add_transport_details(message)
        self.add_line_items(message, line_items)
        # UNT segment count: all segments except UNA
        segment_count = len(message)  # If UNA is counted, use len(message), else len(message) - 1
        self.add_trailer(message, segment_count, message_ref)
        return "\n".join(message)

# Usage Example
if __name__ == "__main__":
    items = [
        {"line_no": "1", "ean": "4000862141404", "qty": "12"},
        {"line_no": "2", "ean": "4000862141405", "qty": "5"},
    ]

    recadv = RecadvGenerator()
    print(recadv.generate(items))
