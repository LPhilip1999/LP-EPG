import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import gzip
import shutil
import re

def fix_timestamp(ts):
    """Converts various formats to standard XMLTV YYYYMMDDHHMMSS +0000"""
    if not ts: return ts
    # Extract only digits
    digits = re.sub(r'\D', '', ts)
    if len(digits) >= 14:
        main_time = digits[:14]
        # Check for timezone offset in original string
        offset_match = re.search(r'([+-]\d{4})', ts)
        offset = offset_match.group(1) if offset_match else "+0000"
        return f"{main_time} {offset}"
    return ts

def fix_yachting_time(date_str, time_str):
    """Specific fix for Yachting TV separate date/time attributes"""
    try:
        dt = datetime.strptime(f"{date_str} {time_str}", "%d.%m.%Y %H:%M:%S")
        return dt.strftime("%Y%m%d%H%M%S +0000")
    except:
        return None

def merge_epg():
    # Setup the combined XML structure
    merged_root = ET.Element("tv")
    merged_root.set("source-info-name", "EPG Service")
    merged_root.set("generator-info-name", "Metax-Universal-V5-Resilient")

    # User-Agent to prevent blocks by Google/Cloudflare during redirects
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        with open("channels.txt", "r") as f:
            lines = [line.strip() for line in f if line.strip() and "|" in line]
    except FileNotFoundError:
        print("Error: channels.txt not found.")
        return

    for line in lines:
        url, display_name = line.split("|")
        url, display_name = url.strip(), display_name.strip()
        # ID with no spaces as requested
        target_id = f"{display_name.replace(' ', '')}.metax"
        
        try:
            print(f"Syncing: {display_name}...")
            # Following redirects for Choppertown/Frequency links
            response = requests.get(url, headers=headers, timeout=60, allow_redirects=True)
            
            if response.status_code != 200:
                print(f"Failed {display_name}: HTTP {response.status_code}")
                continue

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

            # --- 2. XML HANDLING (HI LIFE, YACHTING, CHOPPERTOWN, SOFAST) ---
            else:
                content = response.content
                try:
                    # Normal Attempt
                    source_root = ET.fromstring(content)
                except (ET.ParseError, UnicodeDecodeError):
                    try:
                        # Attempt 2: Handle UTF-16 (Choppertown) and ignore truncated/broken bytes
                        decoded = content.decode('utf-16', errors='ignore').encode('utf-8')
                        source_root = ET.fromstring(decoded)
                    except Exception:
                        # Final Fallback
                        decoded = content.decode('latin-1', errors='ignore').encode('utf-8')
                        source_root = ET.fromstring(decoded)

                chan_elem = ET.SubElement(merged_root, "channel", id=target_id)
                ET.SubElement(chan_elem, "display-name").text = display_name
                
                # Support both <programme> and <program> (for Hi Life)
                for prog in source_root.findall(".//programme") + source_root.findall(".//program"):
                    if "yachting" in url.lower() or "Yachting" in display_name:
                        xmltv_start = fix_yachting_time(prog.get("date"), prog.get("start"))
                        xmltv_stop = fix_yachting_time(prog.get("date"), prog.get("end"))
                    else:
                        xmltv_start = fix_timestamp(prog.get("start"))
                        xmltv_stop = fix_timestamp(prog.get("stop"))

                    if xmltv_start and xmltv_stop:
                        clean_prog = ET.SubElement(merged_root, "programme", channel=target_id, start=xmltv_start, stop=xmltv_stop)
                        
                        # Map titles, descriptions, and thumbnails (SoFast TV fix)
                        tags_to_find = {
                            "title": ["title", "original_title"],
                            "desc": ["desc", "description"],
                            "icon": ["icon", "ThumbnailUrl"]
                        }
                        
                        for standard_tag, source_tags in tags_to_find.items():
                            for s_tag in source_tags:
                                found = prog.find(s_tag)
                                if found is not None:
                                    new_elem = ET.SubElement(clean_prog, standard_tag)
                                    if standard_tag == "icon":
                                        img_url = found.get("src") or found.text
                                        if img_url: new_elem.set("src", img_url.strip())
                                    else:
                                        new_elem.text = found.text
                                    break

        except Exception as e:
            print(f"Error processing {display_name}: {e}")

    # Generate final files
    xml_file = "epg.xml"
    gz_file = "epg.xml.gz"
    declaration = '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE tv SYSTEM "xmltv.dtd">\n'
    
    # Save standard XML
    xml_data = ET.tostring(merged_root, encoding="utf-8")
    with open(xml_file, "wb") as f:
        f.write(declaration.encode("utf-8") + xml_data)
    
    # Save Gzipped version for OTT Navigator
    with open(xml_file, 'rb') as f_in, gzip.open(gz_file, 'wb') as f_out:
        shutil.copyfileobj(f_in, f_out)
    
    print(f"Success! {xml_file} and {gz_file} updated.")

if __name__ == "__main__":
    merge_epg()
