import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import gzip
import shutil
import re

def fix_timestamp(ts):
    """General fix for ISO and compact formats"""
    if not ts: return ts
    # Ensure there is a space before the offset (e.g., 20260316234853 0000)
    digits = re.sub(r'\D', '', ts)
    if len(digits) >= 14:
        offset_match = re.search(r'([+-]\d{4})', ts)
        offset = offset_match.group(1) if offset_match else "+0000"
        return f"{digits[:14]} {offset}"
    return ts

def fix_yachting_time(date_str, time_str):
    try:
        dt = datetime.strptime(f"{date_str} {time_str}", "%d.%m.%Y %H:%M:%S")
        return dt.strftime("%Y%m%d%H%M%S +0000")
    except:
        return None

def merge_epg():
    merged_root = ET.Element("tv")
    merged_root.set("source-info-name", "EPG Service")
    merged_root.set("generator-info-name", "Metax-Universal-Bridge")

    try:
        with open("channels.txt", "r") as f:
            lines = [line.strip() for line in f if line.strip() and "|" in line]
    except FileNotFoundError:
        print("channels.txt not found.")
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
                chan_elem = ET.SubElement(merged_root, "channel", id=target_id)
                ET.SubElement(chan_elem, "display-name").text = display_name
                for item in data:
                    show, ep = item.get("showInfo", {}), item.get("episodeInfo", {})
                    prog = ET.SubElement(merged_root, "programme", 
                        channel=target_id,
                        start=fix_timestamp(ep.get("episodeStartTime")),
                        stop=fix_timestamp(ep.get("episodeEndTime"))
                    )
                    ET.SubElement(prog, "title").text = show.get("showTitle", "Bloomberg")
                    ET.SubElement(prog, "desc").text = ep.get("episodeDescription", "")

            # --- 2. YACHTING TV & CHOPPERTOWN (NON-STANDARD XML) ---
            else:
                # Handle UTF-16 for Choppertown/Frequency sources
                content = response.content
                try:
                    source_root = ET.fromstring(content)
                except ET.ParseError:
                    source_root = ET.fromstring(content.decode('utf-16').encode('utf-8'))

                chan_elem = ET.SubElement(merged_root, "channel", id=target_id)
                ET.SubElement(chan_elem, "display-name").text = display_name
                
                for prog in source_root.findall("programme"):
                    # Use provided start/stop or calculate for Yachting
                    if "yachting" in url.lower() or "Yachting" in display_name:
                        xmltv_start = fix_yachting_time(prog.get("date"), prog.get("start"))
                        xmltv_stop = fix_yachting_time(prog.get("date"), prog.get("end"))
                    else:
                        xmltv_start = fix_timestamp(prog.get("start"))
                        xmltv_stop = fix_timestamp(prog.get("stop"))

                    if xmltv_start and xmltv_stop:
                        clean_prog = ET.SubElement(merged_root, "programme", channel=target_id, start=xmltv_start, stop=xmltv_stop)
                        
                        # Extract and Clean Tags (Handling CDATA and different Title tags)
                        tags_to_find = {
                            "title": ["title", "original_title"],
                            "desc": ["desc", "description"],
                            "icon": ["icon"]
                        }
                        
                        for standard_tag, source_tags in tags_to_find.items():
                            for s_tag in source_tags:
                                found = prog.find(s_tag)
                                if found is not None:
                                    new_elem = ET.SubElement(clean_prog, standard_tag)
                                    new_elem.text = found.text
                                    if s_tag == "icon":
                                        new_elem.set("src", found.get("src", ""))
                                    break

        except Exception as e:
            print(f"Skip {display_name}: {e}")

    # Output Generation
    xml_file = "epg.xml"
    declaration = '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE tv SYSTEM "xmltv.dtd">\n'
    xml_data = ET.tostring(merged_root, encoding="utf-8")
    with open(xml_file, "wb") as f:
        f.write(declaration.encode("utf-8") + xml_data)
    with open(xml_file, 'rb') as f_in, gzip.open("epg.xml.gz", 'wb') as f_out:
        shutil.copyfileobj(f_in, f_out)
    print("All sources (including Choppertown) merged and cleaned.")

if __name__ == "__main__":
    merge_epg()
