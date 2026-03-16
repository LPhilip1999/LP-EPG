import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import gzip
import shutil
import re

def fix_timestamp(ts):
    """Converts ISO and other formats to YYYYMMDDHHMMSS +0000"""
    if not ts:
        return ts
    digits = re.sub(r'\D', '', ts)
    if len(digits) >= 14:
        main_time = digits[:14]
        offset_match = re.search(r'([+-]\d{4})', ts)
        offset = offset_match.group(1) if offset_match else "+0000"
        return f"{main_time} {offset}"
    return ts

def merge_epg():
    merged_root = ET.Element("tv")
    merged_root.set("source-info-name", "EPG Service")
    merged_root.set("generator-info-name", "Metax-Final-Generator")

    try:
        with open("channels.txt", "r") as f:
            lines = [line.strip() for line in f if line.strip() and "|" in line]
    except FileNotFoundError:
        print("Error: channels.txt not found.")
        return

    for line in lines:
        url, display_name = line.split("|")
        url, display_name = url.strip(), display_name.strip()
        target_id = f"{display_name.replace(' ', '')}.metax"
        
        try:
            print(f"Syncing: {display_name}...")
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                source_root = ET.fromstring(response.content)
                
                # Add Channel Node
                chan_elem = ET.SubElement(merged_root, "channel", id=target_id)
                ET.SubElement(chan_elem, "display-name").text = display_name
                
                # Process Programs
                for prog in source_root.findall("programme"):
                    clean_prog = ET.Element("programme")
                    clean_prog.set("channel", target_id)
                    clean_prog.set("start", fix_timestamp(prog.get("start")))
                    clean_prog.set("stop", fix_timestamp(prog.get("stop")))
                    
                    # Keep only Title, Desc, and Icon
                    for tag in ["title", "desc", "icon"]:
                        found_elements = prog.findall(tag)
                        for elem in found_elements:
                            clean_prog.append(elem)
                    
                    merged_root.append(clean_prog)
        except Exception as e:
            print(f"Skip {display_name}: {e}")

    # 1. Save epg.xml with DOCTYPE
    xml_file = "epg.xml"
    declaration = '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE tv SYSTEM "xmltv.dtd">\n'
    xml_data = ET.tostring(merged_root, encoding="utf-8")
    
    with open(xml_file, "wb") as f:
        f.write(declaration.encode("utf-8"))
        f.write(xml_data)

    # 2. Save epg.xml.gz
    gz_file = "epg.xml.gz"
    with open(xml_file, 'rb') as f_in:
        with gzip.open(gz_file, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    
    print(f"Success! {xml_file} and {gz_file} created.")

if __name__ == "__main__":
    merge_epg()
