from datetime import datetime
import uuid
import os
import xml.etree.ElementTree as ET

def generate_recadv_segments():
    def segment(tag, *elements):
        return f"{tag}+{'+'.join(elements)}'"

    now = datetime.utcnow()
    timestamp = now.strftime("%y%m%d:%H%M")
    control_ref = str(uuid.uuid4())[:8].upper()

    message = []

    # --- UNB ---
    sender_id = "SENDERID"
    receiver_id = "RECEIVERID"
    message.append(segment("UNB", "UNOA:1", sender_id, receiver_id, timestamp, control_ref))

    # --- UNH ---
    message_ref = str(uuid.uuid4())[:14].replace('-', '')
    message.append(segment("UNH", message_ref, "RECADV:D:96A:UN:EAN008"))

    # --- BGM, DTM, RFF ---
    message.append(segment("BGM", "351", "RECADV001", "9"))
    message.append(segment("DTM", "137:" + now.strftime("%Y%m%d:%H%M") + ":203"))
    message.append(segment("RFF", "DQ:123456789"))
    message.append(segment("NAD", "BY", "5412345000176::9"))
    message.append(segment("NAD", "SU", "4012345500004::9"))

    # --- Line items ---
    line_items = [
        {"line_no": "1", "ean": "4000862141404", "qty": "12", "status": "OK"},
        {"line_no": "2", "ean": "4000862141405", "qty": "0", "status": "MISSING"},
        {"line_no": "3", "ean": "4000862141406", "qty": "8", "status": "DAMAGED"},
    ]

    for item in line_items:
        message.append(segment("LIN", item["line_no"], "", f"EN:{item['ean']}"))
        message.append(segment("QTY", "113:" + item["qty"]))

        if item["status"] == "DAMAGED":
            message.append(segment("DOC", "751", "DAM-20250507"))  # 751 = Damage Report
            message.append(segment("FTX", "AAI", "", "", "", "Damaged goods on arrival"))
        elif item["status"] == "MISSING":
            message.append(segment("FTX", "AAI", "", "", "", "Item missing from shipment"))

    # --- UNT ---
    segment_count = len(message) - 1
    message.append(segment("UNT", str(segment_count), message_ref))

    # --- UNZ ---
    message.append(segment("UNZ", "1", control_ref))

    return message

def export_to_edi_file(segments, filename="recadv.edi", directory="."):
    filepath = os.path.join(directory, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(segments))
    print(f"RECADV EDIFACT written to: {filepath}")

def export_to_xml(segments, filename="recadv.xml", directory="."):
    root = ET.Element("RECADV")
    for seg in segments:
        if not seg.strip():
            continue
        tag, *parts = seg.strip().split("+")
        element = ET.SubElement(root, tag)
        for i, part in enumerate(parts):
            sub = ET.SubElement(element, f"Element{i+1}")
            sub.text = part
    tree = ET.ElementTree(root)
    filepath = os.path.join(directory, filename)
    tree.write(filepath, encoding="utf-8", xml_declaration=True)
    print(f"RECADV XML written to: {filepath}")

# Generate and export
segments = generate_recadv_segments()
export_to_edi_file(segments)
export_to_xml(segments)
