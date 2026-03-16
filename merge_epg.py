import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import gzip
import shutil
import re

def fix_timestamp(ts):
    """Converts ISO '2026-03-16T10:00:00.000Z' to XMLTV '20260316100000 +0000'"""
    if not ts: return ts
    digits = re.sub(r'\D', '', ts)
    if len(digits) >= 14:
        return f"{digits[:14]} +0000"
    return ts

def merge_epg():
    merged_root = ET.Element("tv")
    merged_root.set("source-info-name", "EPG Service")
    merged_root.set("generator-info-name", "Metax-JSON-Bridge")

    try:
        with open("channels.txt", "r") as f:
            lines = [line.strip() for line in f if line.strip() and "|" in line]
    except FileNotFoundError:
        return

    for line in lines:
        url, display_name = line.split("|")
        url, display_name = url.strip(), display_name.strip()
        target_id = f"{display_name.replace(' ', '')}.metax"
        
        try:
            print(f"Syncing: {display_name}...")
            response = requests.get(url, timeout=30)
            if response.status_code != 200: continue

            # --- SPECIAL HANDLING FOR BLOOMBERG JSON ---
            if "bloomberg" in url.lower() or url.endswith(".json") or response.headers.get('Content-Type') == 'application/json':
                data = response.json()
                
                # Add Channel Node
                chan_elem = ET.SubElement(merged_root, "channel", id=target_id)
                ET.SubElement(chan_elem, "display-name").text = display_name
                
                # Convert JSON objects to XML programme nodes
                for item in data:
                    show = item.get("showInfo", {})
                    ep = item.get("episodeInfo", {})
                    
                    prog = ET.SubElement(merged_root, "programme", 
                        channel=target_id,
                        start=fix_timestamp(ep.get("episodeStartTime")),
                        stop=fix_timestamp(ep.get("episodeEndTime"))
                    )
                    ET.SubElement(prog, "title").text = show.get("showTitle", "")
                    ET.SubElement(prog, "desc").text = ep.get("episodeDescription", "")
            
            # --- STANDARD XMLTV HANDLING ---
            else:
                source_root = ET.fromstring(response.content)
                chan_elem = ET.SubElement(merged_root, "channel", id=target_id)
                ET.SubElement(chan_elem, "display-name").text = display_name
                
                for prog in source_root.findall("programme"):
                    clean_prog = ET.Element("programme")
                    clean_prog.set("channel", target_id)
                    clean_prog.set("start", fix_timestamp(prog.get("start")))
                    clean_prog.set("stop", fix_timestamp(prog.get("stop")))
                    
                    for tag in ["title", "desc", "icon"]:
                        for elem in prog.findall(tag):
                            clean_prog.append(elem)
                    merged_root.append(clean_prog)

        except Exception as e:
            print(f"Skip {display_name}: {e}")

    # Output Files
    xml_file = "epg.xml"
    declaration = '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE tv SYSTEM "xmltv.dtd">\n'
    xml_data = ET.tostring(merged_root, encoding="utf-8")
    
    with open(xml_file, "wb") as f:
        f.write(declaration.encode("utf-8"))
        f.write(xml_data)

    with open(xml_file, 'rb') as f_in, gzip.open("epg.xml.gz", 'wb') as f_out:
        shutil.copyfileobj(f_in, f_out)
    
    print("Bloomberg JSON converted and merged successfully.")

if __name__ == "__main__":
    merge_epg()
