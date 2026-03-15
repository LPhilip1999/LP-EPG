import requests
import xml.etree.ElementTree as ET
import gzip
import os
from datetime import datetime

headers = {'User-Agent': 'Mozilla/5.0'}

def format_bloomberg_time(time_str):
    if not time_str: return ""
    try:
        dt_str = time_str.replace('Z', '+0000')
        dt = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S.%f%z") if '.' in dt_str else datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S%z")
        return dt.strftime("%Y%m%d%H%M%S %z")
    except: return ""

def merge_xml():
    root = ET.Element("tv")
    root.set("generator-info-name", "Gemini-EPG-Merger-v2")

    # Read the text file
    if not os.path.exists("channels.txt"):
        print("Error: channels.txt not found!")
        return

    with open("channels.txt", "r") as f:
        lines = f.readlines()

    for line in lines:
        if "|" not in line: continue
        url, display_name = line.strip().split("|")
        # Create tvg-id: Remove spaces and add .metaX (e.g., "Bloomberg TV" -> "BloombergTV.metaX")
        new_id = f"{display_name.replace(' ', '')}.metaX"

        try:
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code != 200: continue

            # Handle JSON (Bloomberg)
            if "bloomberg.com" in url:
                data = response.json()
                chan = ET.SubElement(root, "channel", id=new_id)
                ET.SubElement(chan, "display-name", lang="en").text = display_name
                for item in data:
                    show = item.get("showInfo", {})
                    episode = item.get("episodeInfo", {})
                    start = format_bloomberg_time(episode.get("episodeStartTime"))
                    stop = format_bloomberg_time(episode.get("episodeEndTime"))
                    if start and stop:
                        prog = ET.SubElement(root, "programme", start=start, stop=stop, channel=new_id)
                        ET.SubElement(prog, "title", lang="en").text = show.get("showTitle", "News")
                        ET.SubElement(prog, "desc", lang="en").text = episode.get("episodeDescription") or show.get("showDescription", "")
            
            # Handle XML
            else:
                tree = ET.fromstring(response.content)
                chan = ET.SubElement(root, "channel", id=new_id)
                ET.SubElement(chan, "display-name", lang="en").text = display_name
                for prog in tree.findall("programme"):
                    new_prog = ET.SubElement(root, "programme")
                    for attr, val in prog.attrib.items(): new_prog.set(attr, val)
                    new_prog.set("channel", new_id)
                    for child in prog: new_prog.append(child)

            print(f"Processed: {display_name}")
        except Exception as e:
            print(f"Failed {display_name}: {e}")

    # Save files
    xml_data = ET.tostring(root, encoding='utf-8', method='xml')
    with gzip.open("epg.xml.gz", "wb") as f: f.write(xml_data)
    with open("epg.xml", "wb") as f: f.write(xml_data)

if __name__ == "__main__":
    merge_xml()
