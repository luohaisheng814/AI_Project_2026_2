# -*- coding: utf-8 -*-
"""手机版本地接口冒烟测试（8011）。"""
import json
import urllib.request

BASE = "http://127.0.0.1:8011"


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=15) as r:
        return r.status, r.read()


def get_json(path):
    st, body = get(path)
    return st, json.loads(body.decode("utf-8"))


def post(path, payload):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.status, json.loads(r.read().decode("utf-8"))


# 1. 首页
st, body = get("/")
print("GET / ->", st, "html bytes:", len(body), "has catSel:", b"catSel" in body)

# 2. manifest
st, body = get("/manifest.json")
print("GET /manifest.json ->", st)

# 3. meta
st, meta = get_json("/api/meta")
print("GET /api/meta ->", st, "categories:", len(meta["categories"]), "groups:", len(meta["groups"]))

# 4. chat：手动选 02 海岸，问多大浦
st, r = post("/api/chat", {"question": "多大浦海水浴场开放时间", "category": "02_海岸休闲_日落夜景",
                           "group_type": "group_3plus", "ui_lang": "zh"})
print("\nPOST /api/chat (02) ->", st)
print("  category:", r["category"], "group:", r["group_type"], "spot:", r["spot"])
print("  recognize:", r["recognize"])
print("  supplements:", [(s["name"], s["cat_label"]) for s in r["supplements"]])
leak = [s["detail"] for s in r["sources"] if "01_" in s["detail"] or "03_" in s["detail"] or "04_" in s["detail"]]
print("  main-source cross-category leak:", leak)

# 5. chat：不传分类，自动推断 04 渔港
st, r = post("/api/chat", {"question": "长林浦口拍照打卡", "category": "", "group_type": "", "ui_lang": "zh"})
print("\nPOST /api/chat (auto) ->", st)
print("  inferred category:", r["category"], "group:", r["group_type"], "spot:", r["spot"])
print("  supplements:", [(s["name"], s["cat_label"]) for s in r["supplements"]])

# 5b. 语言策略：输出语言只跟 ui_lang 按钮走，与提问语言无关
lang_cases = [
    ({"question": "감천문화마을 소개", "category": "01_艺术村落_文化街区", "group_type": "two_mf", "ui_lang": "zh"}, "zh"),
    ({"question": "甘川文化村 介绍", "category": "01_艺术村落_文化街区", "group_type": "two_mf", "ui_lang": "ko"}, "ko"),
    ({"question": "How do I get to Gamcheon Culture Village?", "category": "01_艺术村落_文化街区", "group_type": "solo_male", "ui_lang": "en"}, "en"),
]
print("\n--- language policy (button lang wins over question lang) ---")
for payload, expect in lang_cases:
    st, r = post("/api/chat", payload)
    ok = r["lang"] == expect
    print(f"  question lang -> button {expect}: http={st} reply lang={r['lang']} {'OK' if ok else 'FAIL'}")
    print("    sources:", [s["label"] for s in r["sources"]])
    print("    supplements:", [(s["name"], s["cat_label"]) for s in r["supplements"]])
    assert ok, f"reply lang {r['lang']} != button {expect}"

# 6. nearby
st, nb = post("/api/nearby", {"lat": 35.09, "lng": 128.97})
print("\nPOST /api/nearby ->", st, "spots:", len(nb["spots"]), "nearest:", nb["spots"][0]["name"])

# 7. 安装包下载
st, body = get("/download/Busan_Tour_App.zip")
print("\nGET /download/Busan_Tour_App.zip ->", st, "bytes:", len(body), "zip magic:", body[:2] == b"PK")
