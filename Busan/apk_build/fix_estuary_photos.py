# -*- coding: utf-8 -*-
"""修正洛东江河口/乙淑岛图片：用生态中心与河口全景替换卫星图和农田图。"""
import json, os, urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(BASE, "android", "assets")
PHOTOS = os.path.join(ASSETS, "photos")
MANIFEST = os.path.join(ASSETS, "photos_manifest.json")
UA = "BusanTravelAssistant/2.3"

ECO_URL = "https://aka.doubaocdn.com/l/LjkodWU1U8"
ECO_SOURCE = "https://koreatourinfo.com/%EB%B6%80%EC%82%B0-%EB%82%99%EB%8F%99%EA%B0%95%ED%95%98%EA%B5%AC%EC%97%90%EC%BD%94%EC%84%BC%ED%84%B0/"
PANORAMA_URL = "https://thumb.wikimedia.org/wikipedia/commons/thumb/5/50/Panorama_Saha-gu_Busan.JPG/960px-Panorama_Saha-gu_Busan.JPG"
PANORAMA_SOURCE = "https://commons.wikimedia.org/wiki/File:Panorama_Saha-gu_Busan.JPG"


def get(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as f:
        f.write(r.read())


def main():
    data = json.load(open(MANIFEST, encoding="utf-8"))
    get(ECO_URL, os.path.join(PHOTOS, "nakdong-estuary-01.jpg"))
    data["洛东江河口生态中心"][0] = {
        "src": "photos/nakdong-estuary-01.jpg",
        "caption": "洛东江河口生态中心",
        "credit": "韩国观光公社（VisitKorea）",
        "license": "公共机构旅游宣传图（来源标注）",
        "sourceUrl": ECO_SOURCE,
        "title": "Nakdong River Estuary Eco Center",
        "alt": "洛东江河口生态中心建筑与湿地",
    }
    get(PANORAMA_URL, os.path.join(PHOTOS, "eulsukdo-02.jpg"))
    data["乙淑岛候鸟公园"].append({
        "src": "photos/eulsukdo-02.jpg",
        "caption": "乙淑岛候鸟公园",
        "credit": "Wikimedia Commons",
        "license": "CC BY-SA",
        "sourceUrl": PANORAMA_SOURCE,
        "title": "Panorama Saha-gu Busan",
        "alt": "沙下区乙淑岛与洛东江河口全景",
    })
    get(ECO_URL, os.path.join(PHOTOS, "eulsukdo-03.jpg"))
    data["乙淑岛候鸟公园"].append({
        "src": "photos/eulsukdo-03.jpg",
        "caption": "乙淑岛候鸟公园",
        "credit": "韩国观光公社（VisitKorea）",
        "license": "公共机构旅游宣传图（来源标注）",
        "sourceUrl": ECO_SOURCE,
        "title": "Nakdong River Estuary Eco Center",
        "alt": "乙淑岛上的洛东江河口生态中心",
    })
    json.dump(data, open(MANIFEST, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    with open(os.path.join(ASSETS, "photos.js"), "w", encoding="utf-8") as f:
        f.write("window.BUSAN_PHOTOS=" + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n")
    print("spots", len(data), "photos", sum(len(v) for v in data.values()))


if __name__ == "__main__":
    main()
