from datetime import datetime
import uuid
import os

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
    message.append(segment("DTM", "137:" + datetime.now().strftime("%Y%m%d:%H%M") + ":203"))

    # Reference to dispatch/delivery note
    message.append(segment("RFF", "DQ:123456789"))

    # Name and address
    message.append(segment("NAD", "BY", "5412345000176::9"))  # Buyer
    message.append(segment("NAD", "SU", "4012345500004::9"))  # Supplier

    # Line items
    line_items = [
        {"line_no": "1", "ean": "4000862141404", "qty": "12"},
        {"line_no": "2", "ean": "4000862141405", "qty": "5"},
    ]

    for item in line_items:
        message.append(segment("LIN", item["line_no"], "", f"EN:{item['ean']}"))
        message.append(segment("QTY", "113:" + item["qty"]))

    # Trailer
    segment_count = len(message) + 1
    message.append(segment("UNT", str(segment_count), message_ref))

    return "\n".join(message)

def export_to_edi_file(content, filename="recadv.edi", directory="."):
    filepath = os.path.join(directory, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"RECADV message written to: {filepath}")

# Generate and export
recadv_message = generate_recadv()
export_to_edi_file(recadv_message)
