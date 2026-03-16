import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import gzip
import shutil
import re

def fix_timestamp(ts):
    """Converts 2026-03-16T00:00:00.000+0000 to 20260316000000 +0000"""
    if not ts:
        return ts
    # Remove dashes, colons, and the 'T'
    clean_ts = re.sub(r'[-:T]', '', ts)
    # Split the main time from the offset (handling the .000 milliseconds)
    # Target format: YYYYMMDDHHMMSS +Offset
    match = re.match(r'(\d{14})(\.\d+)?\s?([+-]\d{4})?', clean_ts)
    if match:
        main_time = match.group(1)
        offset = match.group(3) if match.group(3) else "+0000"
        return f"{main_time} {offset}"
    return ts

def merge_epg():
    merged_root = ET.Element("tv")
    merged_root.set("generator-info-name", "OTT-Navigator-TimeFixed")
    merged_root.set("date", datetime.now().strftime("%Y%m%d%H%M%S"))

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
            print(f"Processing: {display_name}...")
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                source_root = ET.fromstring(response.content)
                
                # Add Channel Node
                chan_elem = ET.SubElement(merged_root, "channel", id=target_id)
                ET.SubElement(chan_elem, "display-name").text = display_name
                
                # Add and Fix Programme Nodes
                for prog in source_root.findall("programme"):
                    prog.set("channel", target_id)
                    
                    # FIX START AND STOP TIMES
                    start_time = prog.get("start")
                    stop_time = prog.get("stop")
                    
                    prog.set("start", fix_timestamp(start_time))
                    prog.set("stop", fix_timestamp(stop_time))
                    
                    merged_root.append(prog)
        except Exception as e:
            print(f"Error processing {display_name}: {e}")

    # Save epg.xml
    xml_file = "epg.xml"
    tree = ET.ElementTree(merged_root)
    with open(xml_file, "wb") as f:
        f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
        tree.write(f, encoding="utf-8", xml_declaration=False)

    # Save epg.xml.gz
    gz_file = "epg.xml.gz"
    with open(xml_file, 'rb') as f_in:
        with gzip.open(gz_file, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    
    print("Time formats fixed and files updated.")

if __name__ == "__main__":
    merge_epg()
