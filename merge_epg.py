import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import gzip
import shutil

def merge_epg():
    merged_root = ET.Element("tv")
    merged_root.set("generator-info-name", "OTT-Navigator-NoSpaces")
    merged_root.set("date", datetime.now().strftime("%Y%m%d%H%M%S"))

    try:
        with open("channels.txt", "r") as f:
            lines = [line.strip() for line in f if line.strip() and "|" in line]
    except FileNotFoundError:
        print("Error: channels.txt not found.")
        return

    for line in lines:
        url, display_name = line.split("|")
        url = url.strip()
        display_name = display_name.strip()
        
        # REMOVE SPACES: "Playing For Change" -> "PlayingForChange.metax"
        target_id = f"{display_name.replace(' ', '')}.metax"
        
        try:
            print(f"Fetching: {display_name} -> ID: {target_id}")
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                source_root = ET.fromstring(response.content)
                
                # Add Channel Node
                chan_elem = ET.SubElement(merged_root, "channel", id=target_id)
                ET.SubElement(chan_elem, "display-name").text = display_name
                
                # Add Programme Nodes and update their channel reference
                for prog in source_root.findall("programme"):
                    prog.set("channel", target_id)
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
    
    print("Files updated successfully.")

if __name__ == "__main__":
    merge_epg()
