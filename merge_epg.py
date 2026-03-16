import xml.etree.ElementTree as ET
import gzip
import shutil
from datetime import datetime, timedelta

def generate_epg():
    # 1. Read your channels.txt
    try:
        with open("channels.txt", "r", encoding="utf-8") as f:
            channels = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print("Error: channels.txt not found!")
        return

    root = ET.Element("tv", {"generator-info-name": "MetaX-EPG-Generator"})
    
    with open("tvg-ids.txt", "w", encoding="utf-8") as txt_file:
        txt_file.write(f"# MetaXPlay TVG-ID List (.metax)\n# Generated: {datetime.now()}\n\n")

        for name in channels:
            # Format: "Bloomberg TV" -> "bloomberg_tv.metax"
            clean_id = name.lower().replace(" ", "_").replace("-", "_").replace(".", "") + ".metax"
            
            txt_file.write(f"ID: {clean_id} | Name: {name}\n")

            # Define Channel
            channel_node = ET.SubElement(root, "channel", id=clean_id)
            ET.SubElement(channel_node, "display-name").text = name

            # Define 24-hour Placeholder Schedule (Ensures OTT Navigator displays the channel)
            now = datetime.now()
            start_time = now.strftime("%Y%m%d000000 +0800")
            stop_time = (now + timedelta(days=1)).strftime("%Y%m%d000000 +0800")

            p = ET.SubElement(root, "programme", channel=clean_id, start=start_time, stop=stop_time)
            ET.SubElement(p, "title", lang="en").text = f"{name} Live"
            ET.SubElement(p, "desc", lang="en").text = "Continuous digital broadcast via MetaXPlay."

    # 2. Save as epg.xml
    tree = ET.ElementTree(root)
    tree.write("epg.xml", encoding="utf-8", xml_declaration=True)

    # 3. Create epg.xml.gz (Compressed version)
    with open("epg.xml", "rb") as f_in:
        with gzip.open("epg.xml.gz", "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)

    print(f"Success: epg.xml and epg.xml.gz generated for {len(channels)} channels.")

if __name__ == "__main__":
    generate_epg()
