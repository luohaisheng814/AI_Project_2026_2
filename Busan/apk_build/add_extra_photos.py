# -*- coding: utf-8 -*-
"""补齐 Commons 没有结果的 5 个景点图片；来源为韩国观光公社/釜山观光公社公开旅游图。"""
import json, os, urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(BASE, "android", "assets")
PHOTOS = os.path.join(ASSETS, "photos")
MANIFEST = os.path.join(ASSETS, "photos_manifest.json")
UA = "BusanTravelAssistant/2.3 (photo import)"

EXTRA = {
    "多大浦梦之夕阳喷泉": [
        ("https://aka.doubaocdn.com/l/9lD13y9LoK", "Dadaepo Sunset Fountain at night", "https://big5chinese.visitkorea.or.kr/svc/contents/contentsView.do?vcontsId=91852", "韩国观光公社（VisitKorea）"),
        ("https://aka.doubaocdn.com/l/TK72b7VoUc", "Dadaepo Sunset Fountain water column", "https://big5chinese.visitkorea.or.kr/svc/contents/contentsView.do?vcontsId=91852", "韩国观光公社（VisitKorea）"),
        ("https://aka.doubaocdn.com/l/X9xW9Ve0V6", "Dadaepo Sunset Fountain color show", "https://sg.trip.com/travel-guide/attraction/busan/dadaepo-sunset-fountain-of-dream-10759020", "Trip.com 旅游页面"),
    ],
    "没云台": [
        ("https://aka.doubaocdn.com/l/TBJSL3Y1NT", "Molundae islet and lighthouse", "https://infotravelog.com/official-photos/regions/busan/spots/%EB%AA%B0%EC%9A%B4%EB%8C%80", "釜山观光公社 / 韩国观光公社"),
        ("https://aka.doubaocdn.com/l/eCTK7yQ8pY", "Molundae rocky coast", "https://www.saha.go.kr/tour/contents.do?mId=0300000000", "釜山市沙下区厅"),
        ("https://aka.doubaocdn.com/l/qAQ075fZp6", "Molundae sea view", "https://visitbusan.net/archive/dataSearch/view.nm?dataSid=METADATA004121", "釜山观光公社（VisitBusan）"),
    ],
    "峨嵋山观景台": [
        ("https://aka.doubaocdn.com/l/ScPKd74qhD", "Amisan Observatory sunset over river mouth", "https://visitbusan.net/ja/index.do?lang_cd=ja&menuCd=DOM_000000401001001000&uc_seq=287", "釜山观光公社（VisitBusan）"),
        ("https://aka.doubaocdn.com/l/l5I6Fo15IV", "Amisan Observatory building", "https://hk.trip.com/travel-guide/attraction/busan/amisan-observatory-65176608", "Trip.com 旅游页面"),
        ("https://aka.doubaocdn.com/l/32FzsyrOkv", "View from Amisan Observatory", "https://wanderlog.com/zh/place/details/510753/amisan-observatory", "Wanderlog 旅游页面"),
    ],
    "长林浦口": [
        ("https://aka.doubaocdn.com/l/NwX72bu2nC", "Jangnim Port colorful houses and boats", "https://korean.visitkorea.or.kr/detail/rem_detail.do?cotid=341bd0b5-b872-43c9-9be4-ebcc6d70fedc", "韩国观光公社（VisitKorea）"),
        ("https://aka.doubaocdn.com/l/fBM1wEQvDp", "Jangnim Port colorful facade", "https://www.ardentnews.co.kr/news/articleView.html?idxno=14542", "韩国观光公社 / 釜山观光公社"),
        ("https://aka.doubaocdn.com/l/EQiYFpaV1V", "Jangnim Port waterfront", "https://korean.visitkorea.or.kr/detail/rem_detail.do?cotid=341bd0b5-b872-43c9-9be4-ebcc6d70fedc", "韩国观光公社（VisitKorea）"),
    ],
    "多大浦海水浴场": [
        ("https://aka.doubaocdn.com/l/ViGU2i7xJ6", "Dadaepo Beach wide sand", "https://www.ardentnews.co.kr/news/articleView.html?idxno=16417", "釜山观光公社"),
        ("https://aka.doubaocdn.com/l/dG3HCWa8LK", "Dadaepo Beach sunset", "https://www.terrapost.kr/1505", "韩国观光公社（VisitKorea）"),
        ("https://aka.doubaocdn.com/l/ntWUE3ZHEP", "Dadaepo Beach surfers at sunset", "https://www.terrapost.kr/1505", "韩国观光公社（VisitKorea）"),
    ],
}


def main():
    data = json.load(open(MANIFEST, encoding="utf-8"))
    for spot, items in EXTRA.items():
        slug = {
            "多大浦梦之夕阳喷泉": "dadaepo-fountain",
            "没云台": "molundae",
            "峨嵋山观景台": "amisan",
            "长林浦口": "jangnim",
            "多大浦海水浴场": "dadaepo-beach",
        }[spot]
        existing = data.get(spot, [])
        start = len(existing) + 1
        for i, (url, title, source, credit) in enumerate(items, start=start):
            fname = "%s-%02d.jpg" % (slug, i)
            dest = os.path.join(PHOTOS, fname)
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as f:
                f.write(r.read())
            existing.append({
                "src": "photos/" + fname,
                "caption": spot,
                "credit": credit,
                "license": "公共机构旅游宣传图（来源标注）",
                "sourceUrl": source,
                "title": title,
                "alt": title,
            })
            print("OK", spot, fname, os.path.getsize(dest))
        data[spot] = existing
    json.dump(data, open(MANIFEST, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    with open(os.path.join(ASSETS, "photos.js"), "w", encoding="utf-8") as f:
        f.write("window.BUSAN_PHOTOS=" + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n")
    print("spots", len(data), "photos", sum(len(v) for v in data.values()))


if __name__ == "__main__":
    main()
