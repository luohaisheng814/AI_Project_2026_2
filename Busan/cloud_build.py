# -*- coding: utf-8 -*-
"""
cloud_build.py —— 生成「云端数据库」快照

来源：android/assets/data.json（三语景点档案）+ 坐标表（与 mobile_app.SPOTS_GEO 一致）
产物：
  mobile/cloud/spots.json        云端数据库（随 GitHub 发布，供 APK 联网直连读取）
  android/assets/cloud_snapshot.json  同一份快照，打进 APK 作为「联网失败时的最近一份云端数据」

用法：
  python cloud_build.py
"""
import json
import os
import re

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "android", "assets", "data.json")
CLOUD_DIR = os.path.join(BASE, "mobile", "cloud")
CLOUD_JSON = os.path.join(CLOUD_DIR, "spots.json")
SNAPSHOT = os.path.join(BASE, "android", "assets", "cloud_snapshot.json")
SNAPSHOT_JS = os.path.join(BASE, "android", "assets", "cloud_snapshot.js")

# 与 mobile_app.SPOTS_GEO 对齐；长林浦口在原始档案里没有写坐标，这里补上
GEO = {
    "甘川文化村": (35.0972, 128.9769),
    "多大浦海水浴场": (35.0550, 128.8910),
    "没云台": (35.0510, 128.8820),
    "多大浦梦之夕阳喷泉": (35.0550, 128.8920),
    "洛东江河口生态中心": (35.1065, 128.9680),
    "乙淑岛候鸟公园": (35.1060, 128.9660),
    "峨嵋山观景台": (35.0620, 128.8980),
    "长林浦口": (35.0880, 128.9450),
}

KEEP_FIELDS = ["overview", "highlights", "hours", "ticket", "transport", "photo",
               "course", "tips", "around", "audience", "history", "source"]

MID_RE = re.compile(r"https?://[^\s]*?[?&]mId=(\d+)")

# 已实测可用的沙下区官网 mId（与 official_sites.py 一致），用于补齐档案里缺 mId 的景点
OFFICIAL_MID = {
    "甘川文化村": ("0101010000", ["0101000000"]),
    "多大浦海水浴场": ("0101030000", ["0600000000", "0609000000"]),
    "多大浦梦之夕阳喷泉": ("0600000000", ["0609000000"]),
    "没云台": ("0101040000", []),
    "乙淑岛候鸟公园": ("0101060000", ["0301050000"]),
    "洛东江河口生态中心": ("0301050000", ["0101060000"]),
    "长林浦口": ("0101110000", ["0101000000"]),
    "峨嵋山观景台": ("", ["0101000000"]),
}


def pick_official(fields, fallback_sources):
    """从档案里找出官网入口：优先 saha.go.kr 的 mId 链接，其次其它官方域名。"""
    urls = []
    for lang in ("zh", "ko", "en"):
        block = fields.get(lang) or {}
        for key in ("source", "overview", "hours", "ticket"):
            text = block.get(key) or ""
            urls.extend(re.findall(r"https?://[^\s)）]+", text))
    urls.extend(fallback_sources or [])
    for u in urls:
        if "saha.go.kr" in u and "mId=" in u:
            m = MID_RE.search(u)
            if m:
                return {"url": "https://www.saha.go.kr/tour/contents.do?mId=" + m.group(1),
                        "mId": m.group(1), "host": "saha.go.kr"}
    for u in urls:
        if "gamcheon.or.kr" in u:
            return {"url": "https://www.gamcheon.or.kr/", "mId": "", "host": "gamcheon.or.kr"}
        if "busan.go.kr" in u:
            return {"url": u, "mId": "", "host": "busan.go.kr"}
    return {"url": "", "mId": "", "host": ""}


def official_for(spot_id, fields, fallback_sources):
    """官网入口：先用实测 mId 表，再从档案正文里找；返回主入口 + 备选。"""
    base = pick_official(fields, fallback_sources)
    mid, extras = OFFICIAL_MID.get(spot_id, ("", []))
    if mid:
        return {
            "url": "https://www.saha.go.kr/tour/contents.do?mId=" + mid,
            "mId": mid,
            "host": "saha.go.kr",
            "extra": ["https://www.saha.go.kr/tour/contents.do?mId=" + x for x in extras],
        }
    base["extra"] = []
    return base


def main():
    with open(SRC, "r", encoding="utf-8") as f:
        src = json.load(f)

    spots = []
    for s in src.get("spots", []):
        lat = s.get("lat")
        lng = s.get("lng")
        if (lat is None or lng is None) and s["id"] in GEO:
            lat, lng = GEO[s["id"]]
        fields = s.get("fields") or {}
        clean = {}
        for lang in ("zh", "ko", "en"):
            block = fields.get(lang) or {}
            clean[lang] = {k: block[k] for k in KEEP_FIELDS if block.get(k)}
        spots.append({
            "id": s["id"],
            "name": s.get("name") or s["id"],
            "name_ko": s.get("name_ko", ""),
            "name_en": s.get("name_en", ""),
            "category": s.get("category", ""),
            "address": s.get("address", ""),
            "lat": lat,
            "lng": lng,
            "aliases": s.get("aliases", []),
            "official": official_for(s["id"], fields, [clean["zh"].get("source", "")]),
            "fields": clean,
        })

    payload = {
        "schema": 2,
        "updated_at": "2026-11-08",
        "note": "云端数据库：景点档案 + 官网入口；APK 联网直连读取，不经过任何电脑服务",
        "strings": {
            "categories": src["strings"]["categories"],
            "groups": src["strings"]["groups"],
            "audience": src.get("audience", {}),
        },
        "spots": spots,
    }

    os.makedirs(CLOUD_DIR, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    with open(CLOUD_JSON, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    with open(SNAPSHOT, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    # 同时给 APK 一份可直接加载的 JS 快照：离线时 cloud.js 用它补足地图/排序所需的数据
    with open(SNAPSHOT_JS, "w", encoding="utf-8", newline="\n") as f:
        f.write("window.BUSAN_CLOUD_SNAPSHOT=" + text + ";\n")

    print("云端库：%s（%d 字节，%d 个景点）" % (CLOUD_JSON, len(text.encode("utf-8")), len(spots)))
    print("包内快照：%s / %s" % (SNAPSHOT, SNAPSHOT_JS))
    for s in spots:
        print("  - %-14s mId=%-10s 坐标=%s,%s" % (s["id"], s["official"]["mId"] or "-", s["lat"], s["lng"]))


if __name__ == "__main__":
    main()
