from datetime import datetime
import uuid

def generate_recadv():
    def segment(tag, *elements):
        return f"{tag}+{'+'.join(elements)}'"

    message = []

    # Message header
    message_ref = str(uuid.uuid4())[:14].replace('-', '')
    message.append(segment("UNH", message_ref, "RECADV:D:96A:UN:EAN008"))

    # Beginning of message
    message.append(segment("BGM", "351", "RECADV001", "9"))  # 351 = Receiving Advice, 9 = Original

    # Date/time of message
    message.append(segment("DTM", "137:" + datetime.now().strftime("%Y%m%d:%H%M") + ":203"))  # 137 = Document date/time, format 203 = CCYYMMDD:HHMM

    # Reference to dispatch/delivery note
    message.append(segment("RFF", "DQ:123456789"))  # DQ = Delivery Note Number

    # Name and address - buyer and supplier
    message.append(segment("NAD", "BY", "5412345000176::9"))  # Buyer GLN
    message.append(segment("NAD", "SU", "4012345500004::9"))  # Supplier GLN

    # Item level (example with two lines)
    line_items = [
        {"line_no": "1", "ean": "4000862141404", "qty": "12"},
        {"line_no": "2", "ean": "4000862141405", "qty": "5"},
    ]

    for item in line_items:
        message.append(segment("LIN", item["line_no"], "", f"EN:{item['ean']}"))
        message.append(segment("QTY", "113:" + item["qty"]))  # 113 = Quantity received

    # Message trailer
    segment_count = len(message) + 1  # +1 for UNT
    message.append(segment("UNT", str(segment_count), message_ref))

    return "\n".join(message)

# Usage
print(generate_recadv())
