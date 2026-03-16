import os
import xml.etree.ElementTree as ET
import gzip
import shutil
from datetime import datetime, timedelta

def generate_epg():
    # 1. Locate channels.txt safely
    base_path = os.getcwd()
    input_file = os.path.join(base_path, "channels.txt")
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found. Please create it.")
        return

    try:
        with open(input_file, "r", encoding="utf-8") as f:
            channels = [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"Error reading channels.txt: {e}")
        return

    # 2. Start building XMLTV
    root = ET.Element("tv", {"generator-info-name": "MetaX-EPG-Generator"})
    
    # Open ID list for your reference
    with open("tvg-ids.txt", "w", encoding="utf-8") as txt_file:
        txt_file.write(f"# MetaXPlay TVG-ID List (.metax)\n# Last Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        for name in channels:
            # Format ID: "DW English" -> "dw_english.metax"
            clean_id = name.lower().replace(" ", "_").replace("-", "_").replace(".", "") + ".metax"
            
            # Record the ID for M3U mapping
            txt_file.write(f"ID: {clean_id} | Name: {name}\n")

            # Channel Node
            channel_node = ET.SubElement(root, "channel", id=clean_id)
            ET.SubElement(channel_node, "display-name").text = name

            # 3. Create a 24-hour Placeholder Program
            # This ensures OTT Navigator shows a listing even without a live API
            now = datetime.now()
            start_time = now.strftime("%Y%m%d000000 +0800")
            stop_time = (now + timedelta(days=1)).strftime("%Y%m%d000000 +0800")

            prog_node = ET.SubElement(root, "programme", 
                                    channel=clean_id, 
                                    start=start_time, 
                                    stop=stop_time)
            ET.SubElement(prog_node, "title", lang="en").text = f"{name} Live Stream"
            ET.SubElement(prog_node, "desc", lang="en").text = "Continuous digital broadcast powered by MetaXPlay."

    # 4. Save epg.xml
    tree = ET.ElementTree(root)
    tree.write("epg.xml", encoding="utf-8", xml_declaration=True)

    # 5. Create epg.xml.gz (Compression for faster loading)
    try:
        with open("epg.xml", "rb") as f_in:
            with gzip.open("epg.xml.gz", "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        print("Success: epg.xml, epg.xml.gz, and tvg-ids.txt created.")
    except Exception as e:
        print(f"Error during compression: {e}")

if __name__ == "__main__":
    generate_epg()
