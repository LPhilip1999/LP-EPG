import requests
import xml.etree.ElementTree as ET
import gzip
from datetime import datetime

# Mapping: URL -> (tvg-id, Display Name)
sources = {
    "https://api-ott.afrolandtv.com/getrawvideosegments?version=12.5&rss_format=xmltv&days=8&linear_channel_id=3920&language=en&partner=metax": 
        ("AfroLandComedy.metaX", "AfloLand Comedy"),
    "https://epg.sofast.tv/api/ChannelXML/GetEpgXml?ChannelId=GOLF-NETWORK&DurationHours=72": 
        ("GolfNetwork.metaX", "Golf Network"),
    "https://epg.frequency.com/output?id=11&format=xmltv": 
        ("Choppertown.metaX", "Choppertown"),
    "https://epg-schedule.dw.com/epg-dwenglish/epg.xml": 
        ("DWEnglish.metaX", "DW English"),
    "https://d3bd0tgyk368z1.cloudfront.net/feeds/epg/fra24gb_metax/FRA24.xml": 
        ("France24.metaX", "France 24 FAST"),
    "https://api.bloomberg.com/syndication/feed/liveschedules/1822d1fb-ffc2-44bd-8fc4-39d9f2786930?access_token=fd24ea542693ebfbc70b4b66318e9da4": 
        ("Bloomberg.metaX", "Bloomberg TV")
}

headers = {'User-Agent': 'Mozilla/5.0'}

def format_bloomberg_time(time_str):
    """Converts Bloomberg ISO time to XMLTV format (YYYYMMDDHHMMSS +0000)"""
    try:
        dt = datetime.strptime(time_str.replace('Z', '+0000'), "%Y-%m-%dT%H:%M:%S.%f%z")
    except:
        dt = datetime.strptime(time_str.replace('Z', '+0000'), "%Y-%m-%dT%H:%M:%S%z")
    return dt.strftime("%Y%m%d%H%M%S %z")

def merge_xml():
    root = ET.Element("tv")
    root.set("generator-info-name", "Gemini-EPG-Merger")

    for url, (new_id, display_name) in sources.items():
        try:
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code != 200:
                continue

            # Handle Bloomberg JSON format
            if "bloomberg.com" in url:
                data = response.json()
                # Create Channel Entry
                chan = ET.SubElement(root, "channel", id=new_id)
                ET.SubElement(chan, "display-name", lang="en").text = display_name
                
                # Create Programme Entries from JSON
                for item in data:
                    show = item.get("showInfo", {})
                    episode = item.get("episodeInfo", {})
                    
                    start = format_bloomberg_time(episode.get("episodeStartTime"))
                    stop = format_bloomberg_time(episode.get("episodeEndTime"))
                    
                    prog = ET.SubElement(root, "programme", start=start, stop=stop, channel=new_id)
                    ET.SubElement(prog, "title", lang="en").text = show.get("showTitle", "Bloomberg News")
                    ET.SubElement(prog, "desc", lang="en").text = show.get("showDescription", "")
            
            # Handle Standard XMLTV format
            else:
                tree = ET.fromstring(response.content)
                chan = ET.SubElement(root, "channel", id=new_id)
                ET.SubElement(chan, "display-name", lang="en").text = display_name

                for prog in tree.findall("programme"):
                    new_prog = ET.SubElement(root, "programme")
                    for attr, val in prog.attrib.items():
                        new_prog.set(attr, val)
                    new_prog.set("channel", new_id)
                    for child in prog:
                        new_prog.append(child)

            print(f"Successfully processed: {display_name}")
        except Exception as e:
            print(f"Error processing {display_name}: {e}")

    xml_data = ET.tostring(root, encoding='utf-8', method='xml')
    with gzip.open("epg.xml.gz", "wb") as f:
        f.write(xml_data)
    with open("epg.xml", "wb") as f:
        f.write(xml_data)

if __name__ == "__main__":
    merge_xml()
