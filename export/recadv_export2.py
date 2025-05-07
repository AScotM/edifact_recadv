from datetime import datetime
import uuid
import os

def generate_recadv():
    def segment(tag, *elements):
        return f"{tag}+{'+'.join(elements)}'"

    now = datetime.utcnow()
    timestamp = now.strftime("%y%m%d:%H%M")
    control_ref = str(uuid.uuid4())[:8].upper()

    message = []

    # --- UNB (Interchange header) ---
    sender_id = "SENDERID"       # Replace with actual sender ID
    receiver_id = "RECEIVERID"   # Replace with actual receiver ID
    message.append(segment("UNB", "UNOA:1", sender_id, receiver_id, timestamp, control_ref))

    # --- UNH (Message header) ---
    message_ref = str(uuid.uuid4())[:14].replace('-', '')
    message.append(segment("UNH", message_ref, "RECADV:D:96A:UN:EAN008"))

    # --- BGM (Beginning of message) ---
    message.append(segment("BGM", "351", "RECADV001", "9"))

    # --- DTM (Document date/time) ---
    message.append(segment("DTM", "137:" + now.strftime("%Y%m%d:%H%M") + ":203"))

    # --- RFF (Delivery note ref) ---
    message.append(segment("RFF", "DQ:123456789"))

    # --- NAD (Buyer/Supplier) ---
    message.append(segment("NAD", "BY", "5412345000176::9"))
    message.append(segment("NAD", "SU", "4012345500004::9"))

    # --- Line items ---
    line_items = [
        {"line_no": "1", "ean": "4000862141404", "qty": "12"},
        {"line_no": "2", "ean": "4000862141405", "qty": "5"},
    ]

    for item in line_items:
        message.append(segment("LIN", item["line_no"], "", f"EN:{item['ean']}"))
        message.append(segment("QTY", "113:" + item["qty"]))

    # --- UNT (Message trailer) ---
    segment_count = len(message) - 1  # exclude UNB
    message.append(segment("UNT", str(segment_count), message_ref))

    # --- UNZ (Interchange trailer) ---
    message.append(segment("UNZ", "1", control_ref))

    return "\n".join(message)

def export_to_edi_file(content, filename="recadv.edi", directory="."):
    filepath = os.path.join(directory, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"RECADV interchange written to: {filepath}")

# Generate and export
recadv_message = generate_recadv()
export_to_edi_file(recadv_message)
