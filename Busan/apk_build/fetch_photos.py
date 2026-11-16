# -*- coding: utf-8 -*-
"""抓取 Wikimedia Commons 实景图并内置到 APK assets/photos。
仅使用 Commons/维基百科上可自由再使用的图片，保留作者/许可/来源页。
Commons 429 时退避重试；没有 Commons 结果的景点用维基百科条目首图兜底。
"""
import html, json, os, re, time, urllib.parse, urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(BASE, "android", "assets", "photos")
MANIFEST = os.path.join(BASE, "android", "assets", "photos_manifest.json")
API = "https://commons.wikimedia.org/w/api.php"
UA = "BusanTravelAssistant/2.3 (photo import; contact: local app)"

SPOTS = [
    ("甘川文化村", "Gamcheon Culture Village", ["Gamcheon"], "gamcheon", ["station", "subway"]),
    ("多大浦梦之夕阳喷泉", "Dadaepo Sunset Fountain", ["Dadaepo", "Fountain"], "dadaepo-fountain", ["station", "subway"]),
    ("多大浦海水浴场", "Dadaepo Beach", ["Dadaepo", "Beach"], "dadaepo-beach", ["station", "subway", "entrance", "platform"]),
    ("没云台", "Molundae", ["Molundae"], "molundae", []),
    ("乙淑岛候鸟公园", "Eulsukdo", ["Eulsukdo", "Eulsuk"], "eulsukdo", ["station"]),
    ("峨嵋山观景台", "Amisan Observatory", ["Amisan"], "amisan", []),
    ("洛东江河口生态中心", "Nakdong River Estuary", ["Nakdong", "Estuary", "Eulsukdo"], "nakdong-estuary", ["barrage"]),
    ("长林浦口", "Jangnim Port", ["Jangnim"], "jangnim", ["station"]),
    ("海云台海水浴场", "Haeundae Beach", ["Haeundae"], "haeundae", ["sand art", "avatar", "station"]),
    ("广安里海水浴场", "Gwangalli Beach", ["Gwangalli", "Gwangan"], "gwangalli", ["station"]),
    ("太宗台", "Taejongdae", ["Taejongdae"], "taejongdae", []),
    ("札嘎其市场", "Jagalchi Market", ["Jagalchi"], "jagalchi", []),
    ("南浦洞BIFF广场", "BIFF Square", ["BIFF", "Nampo"], "biff", []),
    ("松岛海水浴场", "Songdo Beach", ["Songdo"], "songdo", ["station"]),
    ("白浅滩文化村", "Huinnyeoul Culture Village", ["Huinnyeoul"], "huinnyeoul", []),
    ("龙头山公园", "Yongdusan Park", ["Yongdusan", "Busan Tower"], "yongdusan", []),
    ("海东龙宫寺", "Haedong Yonggungsa", ["Yonggungsa", "Haedong"], "yonggungsa", []),
    ("西面", "Seomyeon", ["Seomyeon"], "seomyeon", ["station"]),
]


def get_json(url):
    last = None
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=45) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            last = e
            if "429" in str(e) or "Too Many" in str(e):
                wait = 12 * (attempt + 1)
                print("429, wait %ss" % wait)
                time.sleep(wait)
            else:
                time.sleep(2)
    raise last


def strip(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", str(s or "")))).strip()


def search(term, tokens, bad_tokens, limit=8):
    q = urllib.parse.urlencode({
        "action": "query", "format": "json", "generator": "search",
        "gsrnamespace": "6", "gsrlimit": str(limit), "gsrsearch": term,
        "prop": "imageinfo", "iiprop": "url|extmetadata|mime|size",
        "iiurlwidth": "900",
    })
    data = get_json(API + "?" + q)
    pages = list((data.get("query", {}) or {}).get("pages", {}).values())
    pages.sort(key=lambda p: p.get("index", 99))
    good = []
    for p in pages:
        info = (p.get("imageinfo") or [{}])[0]
        title = p.get("title", "")
        low = title.lower()
        if not info.get("thumburl"):
            continue
        if info.get("mime") not in ("image/jpeg", "image/png"):
            continue
        if any(b.lower() in low for b in bad_tokens):
            continue
        if tokens and not any(t.lower() in low for t in tokens):
            continue
        if info.get("width", 0) < 500 or info.get("height", 0) < 300:
            continue
        good.append((p, info))
    if not good:
        for p in pages:
            info = (p.get("imageinfo") or [{}])[0]
            title = p.get("title", "")
            if info.get("thumburl") and info.get("mime") in ("image/jpeg", "image/png") and not any(b.lower() in title.lower() for b in bad_tokens):
                good.append((p, info))
    return good


def wiki_lead(titles):
    for lang in ("ko", "en"):
        for title in titles:
            q = urllib.parse.urlencode({
                "action": "query", "format": "json", "prop": "pageimages",
                "piprop": "thumbnail|original", "pithumbsize": "900",
                "titles": title,
            })
            try:
                data = get_json("https://%s.wikipedia.org/w/api.php?%s" % (lang, q))
                page = list((data.get("query", {}).get("pages", {}) or {}).values())[0]
                src = (page.get("thumbnail") or {}).get("source") or (page.get("original") or {}).get("source")
                if src:
                    return src, "https://%s.wikipedia.org/wiki/%s" % (lang, urllib.parse.quote(title))
            except Exception:
                continue
    return None, None


def download(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as f:
        f.write(r.read())


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    if os.path.exists(MANIFEST):
        existing = json.load(open(MANIFEST, encoding="utf-8"))
    else:
        existing = {}
    out = {}
    used = set()
    for name, term, tokens, slug, bad in SPOTS:
        candidates = []
        try:
            candidates = search(term, tokens, bad)
        except Exception as e:
            print("SEARCH FAIL", name, e)
        picked = []
        for p, info in candidates:
            title = p.get("title", "")
            if title in used:
                continue
            meta = info.get("extmetadata", {}) or {}
            lic = strip((meta.get("LicenseShortName", {}) or {}).get("value"))
            artist = strip((meta.get("Artist", {}) or {}).get("value"))
            desc = strip((meta.get("ImageDescription", {}) or {}).get("value"))
            url = info.get("thumburl") or info.get("url")
            ext = ".png" if info.get("mime") == "image/png" else ".jpg"
            n = len(picked) + 1
            fname = "%s-%02d%s" % (slug, n, ext)
            dest = os.path.join(OUT_DIR, fname)
            try:
                download(url, dest)
            except Exception as e:
                print("DOWNLOAD FAIL", title, e)
                continue
            used.add(title)
            picked.append({
                "src": "photos/" + fname,
                "caption": name,
                "credit": artist or "Wikimedia Commons",
                "license": lic or "CC",
                "sourceUrl": info.get("descriptionurl") or "",
                "title": title.replace("File:", ""),
                "alt": (desc[:140] if desc else name),
            })
            if len(picked) >= 3:
                break
        if not picked:
            src, page = wiki_lead([name, term])
            if src:
                fname = "%s-01.jpg" % slug
                dest = os.path.join(OUT_DIR, fname)
                try:
                    download(src, dest)
                    picked.append({
                        "src": "photos/" + fname,
                        "caption": name,
                        "credit": "Wikipedia",
                        "license": "See source",
                        "sourceUrl": page,
                        "title": name,
                        "alt": name,
                    })
                except Exception as e:
                    print("WIKI DOWNLOAD FAIL", name, e)
        out[name] = picked
        print(name, len(picked), "; ".join(x["title"] for x in picked))
        time.sleep(3)
    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    photos_js = os.path.join(os.path.dirname(MANIFEST), "photos.js")
    with open(photos_js, "w", encoding="utf-8") as f:
        f.write("window.BUSAN_PHOTOS=" + json.dumps(out, ensure_ascii=False, separators=(",", ":")) + ";\n")
    print("manifest", MANIFEST, "spots", len(out), "photos", sum(len(v) for v in out.values()))
    print("photos.js", photos_js)


if __name__ == "__main__":
    main()
