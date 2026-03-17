import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import gzip
import shutil
import re

def fix_timestamp(ts):
    """General fix for ISO and compact formats"""
    if not ts: return ts
    digits = re.sub(r'\D', '', ts)
    if len(digits) >= 14:
        return f"{digits[:14]} +0000"
    return ts

def fix_yachting_time(date_str, time_str):
    """Converts date='12.3.2026' and start='11:46:52' to '20260312114652 +0000'"""
    try:
        # Parse '12.3.2026 11:46:52'
        dt = datetime.strptime(f"{date_str} {time_str}", "%d.%m.%Y %H:%M:%S")
        return dt.strftime("%Y%m%d%H%M%S +0000")
    except:
        return None

def merge_epg():
    merged_root = ET.Element("tv")
    merged_root.set("source-info-name", "EPG Service")
    merged_root.set("generator-info-name", "Metax-Multi-Bridge")

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

            # --- 1. BLOOMBERG JSON HANDLING ---
            if "bloomberg" in url.lower() or url.endswith(".json"):
                data = response.json()
                ET.SubElement(merged_root, "channel", id=target_id).append(ET.Element("display-name"))
                merged_root.find(f"channel[@id='{target_id}']/display-name").text = display_name
                
                for item in data:
                    show, ep = item.get("showInfo", {}), item.get("episodeInfo", {})
                    prog = ET.SubElement(merged_root, "programme", 
                        channel=target_id,
                        start=fix_timestamp(ep.get("episodeStartTime")),
                        stop=fix_timestamp(ep.get("episodeEndTime"))
                    )
                    ET.SubElement(prog, "title").text = show.get("showTitle", "Bloomberg")
                    ET.SubElement(prog, "desc").text = ep.get("episodeDescription", "")
            
            # --- 2. YACHTING TV (NON-STANDARD XML) ---
            elif "yachting" in url.lower() or "Yachting" in display_name:
                source_root = ET.fromstring(response.content)
                ET.SubElement(merged_root, "channel", id=target_id).append(ET.Element("display-name"))
                merged_root.find(f"channel[@id='{target_id}']/display-name").text = display_name

                for p in source_root.findall("programme"):
                    date_val = p.get("date")
                    start_val = p.get("start")
                    end_val = p.get("end")
                    
                    xmltv_start = fix_yachting_time(date_val, start_val)
                    xmltv_stop = fix_yachting_time(date_val, end_val)
                    
                    if xmltv_start and xmltv_stop:
                        prog = ET.SubElement(merged_root, "programme", channel=target_id, start=xmltv_start, stop=xmltv_stop)
                        # Map original_title to title
                        title_node = p.find("original_title")
                        desc_node = p.find("description")
                        
                        ET.SubElement(prog, "title").text = title_node.text if title_node is not None else "Yachting TV"
                        if desc_node is not None:
                            ET.SubElement(prog, "desc").text = desc_node.text

            # --- 3. STANDARD XMLTV HANDLING ---
            else:
                source_root = ET.fromstring(response.content)
                ET.SubElement(merged_root, "channel", id=target_id).append(ET.Element("display-name"))
                merged_root.find(f"channel[@id='{target_id}']/display-name").text = display_name
                
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

    # File Generation
    xml_file = "epg.xml"
    declaration = '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE tv SYSTEM "xmltv.dtd">\n'
    xml_data = ET.tostring(merged_root, encoding="utf-8")
    with open(xml_file, "wb") as f:
        f.write(declaration.encode("utf-8") + xml_data)
    with open(xml_file, 'rb') as f_in, gzip.open("epg.xml.gz", 'wb') as f_out:
        shutil.copyfileobj(f_in, f_out)

if __name__ == "__main__":
    merge_epg()
