import requests
import xml.etree.ElementTree as ET
import gzip

sources = {
    "https://api-ott.afrolandtv.com/getrawvideosegments?version=12.5&rss_format=xmltv&days=8&linear_channel_id=3920&language=en&partner=metax": "AfroLandComedy.metaX",
    "https://epg.sofast.tv/api/ChannelXML/GetEpgXml?ChannelId=GOLF-NETWORK&DurationHours=72": "GolfNetwork.metaX",
    "https://epg.frequency.com/output?id=11&format=xmltv": "Choppertown.metaX",
    "https://epg-schedule.dw.com/epg-dwenglish/epg.xml": "DWEnglish.metaX",
    "https://d3bd0tgyk368z1.cloudfront.net/feeds/epg/fra24gb_metax/FRA24.xml": "France24.metaX",
    "https://api.bloomberg.com/syndication/feed/liveschedules/1822d1fb-ffc2-44bd-8fc4-39d9f2786930?access_token=fd24ea542693ebfbc70b4b66318e9da4": "Bloomberg.metaX"
}

headers = {'User-Agent': 'Mozilla/5.0'}

def merge_xml():
    root = ET.Element("tv")
    root.set("generator-info-name", "Gemini-EPG-Merger")

    for url, new_id in sources.items():
        try:
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                tree = ET.fromstring(response.content)
                for channel in tree.findall("channel"):
                    channel.set("id", new_id)
                    root.append(channel)
                for prog in tree.findall("programme"):
                    prog.set("channel", new_id)
                    root.append(prog)
            print(f"Processed: {new_id}")
        except Exception as e:
            print(f"Error {new_id}: {e}")

    xml_data = ET.tostring(root, encoding='utf-8', method='xml')
    with gzip.open("epg.xml.gz", "wb") as f:
        f.write(xml_data)
    with open("epg.xml", "wb") as f:
        f.write(xml_data)

if __name__ == "__main__":
    merge_xml()
