import requests
import xml.etree.ElementTree as ET
import gzip

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

def merge_xml():
    root = ET.Element("tv")
    root.set("generator-info-name", "Gemini-EPG-Merger")

    for url, (new_id, display_name) in sources.items():
        try:
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                tree = ET.fromstring(response.content)
                
                # 1. Create/Update Channel Info
                channel_elem = ET.SubElement(root, "channel", id=new_id)
                dname_elem = ET.SubElement(channel_elem, "display-name")
                dname_elem.set("lang", "en")
                dname_elem.text = display_name

                # 2. Process Programmes
                for prog in tree.findall("programme"):
                    # We create a new element to avoid issues with moving nodes
                    new_prog = ET.SubElement(root, "programme")
                    # Copy all attributes from original (start, stop, etc)
                    for attr_name, attr_val in prog.attrib.items():
                        new_prog.set(attr_name, attr_val)
                    
                    # Force the channel ID to match our new .metaX ID
                    new_prog.set("channel", new_id)
                    
                    # Copy all children (title, desc, icon, etc)
                    for child in prog:
                        new_prog.append(child)
                        
            print(f"Processed: {display_name} ({new_id})")
        except Exception as e:
            print(f"Error processing {url}: {e}")

    # Generate XML string
    xml_data = ET.tostring(root, encoding='utf-8', method='xml')
    
    # Save Compressed
    with gzip.open("epg.xml.gz", "wb") as f:
        f.write(xml_data)
        
    # Save Uncompressed (for previewing on GitHub)
    with open("epg.xml", "wb") as f:
        f.write(xml_data)

if __name__ == "__main__":
    merge_xml()
