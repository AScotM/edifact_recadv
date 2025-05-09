from datetime import datetime
import uuid

class RecadvGenerator:
    def __init__(self):
        self.message = []
        self.message_ref = self._generate_message_reference()

    def _generate_message_reference(self):
        return datetime.now().strftime("%Y%m%d%H%M") + str(uuid.uuid4().int)[:4]

    def _segment(self, tag, *elements):
        return f"{tag}+{'+'.join(elements)}'"

    def add_una_segment(self):
        self.message.append("UNA:+.? '")

    def add_header(self):
        self.message.append(self._segment("UNH", self.message_ref, "RECADV:D:96A:UN:EAN008"))
        self.message.append(self._segment("BGM", "351", "RECADV001", "9"))
        self.message.append(self._segment("DTM", f"137:{datetime.now().strftime('%Y%m%d:%H%M')}:203"))
        self.message.append(self._segment("RFF", "DQ:123456789"))

    def add_parties(self):
        self.message.append(self._segment("NAD", "BY", "5412345000176::9"))
        self.message.append(self._segment("NAD", "SU", "4012345500004::9"))

    def add_line_items(self, line_items):
        for item in line_items:
            self.message.append(self._segment("LIN", item["line_no"], "", f"EN:{item['ean']}"))
            self.message.append(self._segment("QTY", f"113:{item['qty']}"))
            self.message.append(self._segment("PAC", "1"))  # Example: 1 package per line item

    def add_trailer(self):
        segment_count = len(self.message) + 1  # for UNT
        self.message.append(self._segment("UNT", str(segment_count), self.message_ref))

    def generate(self, line_items):
        self.add_una_segment()
        self.add_header()
        self.add_parties()
        self.add_line_items(line_items)
        self.add_trailer()
        return "\n".join(self.message)

# Usage
if __name__ == "__main__":
    items = [
        {"line_no": "1", "ean": "4000862141404", "qty": "12"},
        {"line_no": "2", "ean": "4000862141405", "qty": "5"},
    ]

    recadv = RecadvGenerator()
    print(recadv.generate(items))
