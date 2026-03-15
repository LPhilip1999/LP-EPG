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
        ("France24FAST.metaX", "France 24 FAST"),
    "https://api.bloomberg.com/syndication/feed/liveschedules/1822d1fb-ffc2-44bd-8fc4-39d9f2786930?access_token=fd24ea542693ebfbc70b4b66318e9da4": 
        ("Bloomberg.metaX", "Bloomberg TV"),
    "https://api.bloomberg.com/syndication/feed/liveschedules/2d399335-fa7a-4aaf-8ad3-a55ea7e91b89?access_token=fd24ea542693ebfbc70b4b66318e9da4&channel=qt_digital_live": 
        ("BloombergOriginals.metaX", "Bloomberg Originals"),
    "https://api.toongoggles.com/getrawvideosegments?version=12.5&rss_format=xmltv&linear_channel_id=261204&partner=metax": 
        ("ToonGogglesWW.metaX", "Toon Goggles WW"),
"https://api.toongoggles.com/getrawvideosegments?version=12.5&rss_format=xmltv&linear_channel_id=259981&partner=metax": 
        ("TGJunior.metaX", "TG Junior"),
"https://api-ott.afrolandtv.com/getrawvideosegments?version=12.5&rss_format=xmltv&linear_channel_id=1484&partner=metax": 
        ("AfroKiddos.metaX", "AfroKiddos"),
"https://epg.sofast.tv/api/ChannelXML/GetEpgXml?ChannelId=USERIES-TV&DurationHours=96": 
        ("UseriesTV.metaX", "Useries TV"),
"https://app2.evrideo.com/api/reports/epg?channelUid=860e6f4f-38ca-400d-8c37-b251f4f4209e&minDurationSecs=180&groupSameIdSequence=false&durationHours=96&encodingCodePag": 
        ("NoveboxENG.metaX", "Novebox ENG"), 
"https://d3bd0tgyk368z1.cloudfront.net/feeds/epg/wapis_metax/WAPIS.xml": 
        ("WedoAmorPeilSavaje.metaX", "WedoAmor Peil Savaje")
}

headers = {'User-Agent': 'Mozilla/5.0'}

def format_bloomberg_time(time_str):
    """Converts Bloomberg ISO time to XMLTV format"""
    if not time_str:
        return ""
    try:
        # Handles cases with or without milliseconds
        dt_str = time_str.replace('Z', '+0000')
        if '.' in dt_str:
            dt = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S.%f%z")
        else:
            dt = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S%z")
        return dt.strftime("%Y%m%d%H%M%S %z")
    except Exception:
        return ""

def merge_xml():
    root = ET.Element("tv")
    root.set("generator-info-name", "Gemini-EPG-Merger")

    for url, (new_id, display_name) in sources.items():
        try:
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code != 200:
                print(f"Skipping {display_name}: HTTP {response.status_code}")
                continue

            # Check if source is Bloomberg (JSON)
            if "bloomberg.com" in url:
                data = response.json()
                # Add Channel Node
                chan = ET.SubElement(root, "channel", id=new_id)
                ET.SubElement(chan, "display-name", lang="en").text = display_name
                
                # Parse JSON array into programme nodes
                for item in data:
                    show = item.get("showInfo", {})
                    episode = item.get("episodeInfo", {})
                    
                    start = format_bloomberg_time(episode.get("episodeStartTime"))
                    stop = format_bloomberg_time(episode.get("episodeEndTime"))
                    
                    if start and stop:
                        prog = ET.SubElement(root, "programme", start=start, stop=stop, channel=new_id)
                        ET.SubElement(prog, "title", lang="en").text = show.get("showTitle", "Bloomberg News")
                        ET.SubElement(prog, "desc", lang="en").text = episode.get("episodeDescription") or show.get("showDescription", "")
            
            # Handle Standard XML Sources
            else:
                tree = ET.fromstring(response.content)
                # Add Channel Node
                chan = ET.SubElement(root, "channel", id=new_id)
                ET.SubElement(chan, "display-name", lang="en").text = display_name

                # Filter and re-tag programmes
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

    # Finalize and Save
    xml_data = ET.tostring(root, encoding='utf-8', method='xml')
    
    with gzip.open("epg.xml.gz", "wb") as f:
        f.write(xml_data)
    with open("epg.xml", "wb") as f:
        f.write(xml_data)

if __name__ == "__main__":
    merge_xml()
