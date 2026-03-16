import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

def generate_epg():
    # 1. Read your existing channels.txt
    try:
        with open("channels.txt", "r", encoding="utf-8") as f:
            channels = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print("Error: channels.txt not found!")
        return

    root = ET.Element("tv", {"generator-info-name": "MetaX-Manual-Mapper"})
    
    # Open the ID viewer file
    with open("tvg-ids.txt", "w", encoding="utf-8") as txt_file:
        txt_file.write(f"# MetaXPlay TVG-ID List (.metax) - Generated {datetime.now()}\n\n")

        for name in channels:
            # Create a clean ID: "Golf Network" -> "golf_network.metax"
            clean_id = name.lower().replace(" ", "_").replace("-", "_") + ".metax"
            
            # Write to TXT for your reference
            txt_file.write(f"ID: {clean_id} | Name: {name}\n")

            # XML Channel Definition
            channel_node = ET.SubElement(root, "channel", id=clean_id)
            ET.SubElement(channel_node, "display-name").text = name

            # Create Dummy Programs (OTT Navigator needs data to show the channel)
            # This creates a 24-hour "Live Stream" block
            now = datetime.now()
            start_time = now.strftime("%Y%m%d000000 +0800")
            stop_time = (now + timedelta(days=1)).strftime("%Y%m%d000000 +0800")

            p = ET.SubElement(root, "programme", 
                            channel=clean_id, 
                            start=start_time, 
                            stop=stop_time)
            ET.SubElement(p, "title", lang="en").text = f"{name} Live"
            ET.SubElement(p, "desc", lang="en").text = "Continuous programming from MetaXPlay."

    # Save the files
    tree = ET.ElementTree(root)
    tree.write("guide.xml", encoding="utf-8", xml_declaration=True)
    print(f"Success! Processed {len(channels)} channels.")

if __name__ == "__main__":
    generate_epg()
