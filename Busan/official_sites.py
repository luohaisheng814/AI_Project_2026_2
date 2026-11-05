# -*- coding: utf-8 -*-
"""
official_sites.py —— 各景点「官方网站」来源登记表 + 联网抓取
--------------------------------------------------------------
用途：登录后的在线模式里，回答 = 本地数据库 + 各景点官方网站信息。
依据：2026-11-05 实测可达的官方站点（沙下区文化观光官网 tour.contents、甘川文化村官网）。
说明：韩国观光门户 visitbusan.net 为前端 JS 渲染，服务端抓不到正文，故不作为抓取源；
      洛东江河口生态中心 / 峨嵋山观景台在沙下区官网上没有独立详情页，只能引用相邻的
      官方条目（철새도래지 / 대표명소），抓不到时如实标注「官网无独立页」。
"""

import datetime

import web_lookup

SAHA = "https://www.saha.go.kr/tour/contents.do?mId=%s"

OFFICIAL = {
    "甘川文化村": {
        "ko": "감천문화마을",
        "keywords": ["감천문화마을", "감천", "마을", "벽화"],
        "sites": [
            {"portal": "沙下区文化观光（감천문화마을）", "url": SAHA % "0101010000"},
            {"portal": "甘川文化村官网（감천문화마을）", "url": "https://www.gamcheon.or.kr/"},
        ],
    },
    "多大浦海水浴场": {
        "ko": "다대포해수욕장",
        "keywords": ["다대포", "해수욕장", "해변", "일몰"],
        "sites": [
            {"portal": "沙下区文化观光（다대포 해수욕장）", "url": SAHA % "0101030000"},
        ],
    },
    "多大浦梦之夕阳喷泉": {
        "ko": "꿈의낙조분수",
        "keywords": ["낙조분수", "분수", "공연", "음악"],
        "sites": [
            {"portal": "沙下区文化观光（꿈의 낙조분수）", "url": SAHA % "0600000000"},
            {"portal": "沙下区文化观光（낙조분수 운영안내）", "url": SAHA % "0609000000"},
        ],
    },
    "没云台": {
        "ko": "몰운대",
        "keywords": ["몰운대", "낙조", "등대", "기념물"],
        "sites": [
            {"portal": "沙下区文化观光（몰운대）", "url": SAHA % "0101040000"},
        ],
    },
    "乙淑岛候鸟公园": {
        "ko": "을숙도 철새공원",
        "keywords": ["을숙도", "철새", "습지", "공원"],
        "sites": [
            {"portal": "沙下区文化观光（을숙도 생태·철새공원）", "url": SAHA % "0101060000"},
            {"portal": "沙下区文化观光（철새도래지）", "url": SAHA % "0301050000"},
        ],
    },
    "洛东江河口生态中心": {
        "ko": "낙동강하구에코센터",
        "keywords": ["낙동강", "하구", "에코", "철새"],
        "sites": [
            {"portal": "沙下区文化观光（철새도래지）", "url": SAHA % "0301050000"},
        ],
        "note": "釜山市 낙동강하구에코센터 官网（busan.go.kr/eco）在本机网络下不可达，暂以沙下区官方 철새도래지 条目代用",
    },
    "峨嵋山观景台": {
        "ko": "아미산전망대",
        "keywords": ["아미산", "전망대", "일몰", "낙조"],
        "sites": [
            {"portal": "沙下区文化观光（대표명소）", "url": SAHA % "0101000000"},
        ],
        "note": "沙下区文化观光官网没有 아미산전망대 独立详情页，只能抓 대표명소 汇总页，信息有限",
    },
    "长林浦口": {
        "ko": "장림포구",
        "keywords": ["장림포구", "포구", "부네치아", "사진"],
        "sites": [
            {"portal": "沙下区文化观光（부네치아 장림항）", "url": SAHA % "0101110000"},
            {"portal": "沙下区文化观光（대표명소）", "url": SAHA % "0101000000"},
        ],
    },
}

# 别名归一：资料库里同一景点可能有多个写法
ALIAS = {
    "甘川洞文化村": "甘川文化村",
    "多大浦": "多大浦海水浴场",
    "梦之夕阳喷泉": "多大浦梦之夕阳喷泉",
    "多大浦梦之夕阳喷泉": "多大浦梦之夕阳喷泉",
    "乙淑岛": "乙淑岛候鸟公园",
    "乙淑岛候鸟公园": "乙淑岛候鸟公园",
    "洛东江": "洛东江河口生态中心",
    "峨嵋山": "峨嵋山观景台",
    "长林": "长林浦口",
}

_CACHE = {}          # (name, kw) -> (ts, hits)
_TTL_SECONDS = 600   # 官网抓取缓存 10 分钟，避免连续提问反复打官网


def resolve_name(name):
    name = (name or "").strip()
    return ALIAS.get(name, name)


def entries(name):
    """返回某景点的官网登记项（含 note），无登记返回空。"""
    return OFFICIAL.get(resolve_name(name))


def sites_for(name):
    e = entries(name) or {}
    return list(e.get("sites") or [])


def has_site(name):
    return bool(sites_for(name))


def fetch(name, extra_keywords=None, max_pages=2, use_cache=True):
    """
    抓取该景点登记的官方网站，返回
        [{"portal","url","title","snippet","fetched_at"}]，失败项跳过。
    """
    site_cfg = entries(name)
    if not site_cfg:
        return []
    keywords = list(site_cfg.get("keywords") or []) + list(extra_keywords or [])
    key = (resolve_name(name), tuple(extra_keywords or ()))
    now = datetime.datetime.now()

    if use_cache and key in _CACHE:
        ts, hits = _CACHE[key]
        if (now - ts).total_seconds() < _TTL_SECONDS:
            return hits

    hits = []
    for s in (site_cfg.get("sites") or [])[:max_pages]:
        res = web_lookup.fetch_url(s["url"], keywords=keywords, prefer_ids=("conts", "contents"))
        if not res:
            continue
        hits.append({
            "portal": s.get("portal", ""),
            "url": res["url"],
            "title": res.get("title", ""),
            "snippet": res.get("snippet", ""),
            "fetched_at": now.strftime("%Y-%m-%d %H:%M"),
        })
        if len(hits) >= max_pages:
            break

    _CACHE[key] = (now, hits)
    return hits


def source_entries(name):
    """给 sources 列表用的精简条目（不抓正文，只登记 URL），保证界面能点开官网。"""
    out = []
    for s in sites_for(name):
        out.append({"type": "official", "label": s.get("portal", "官网"), "detail": s.get("url", "")})
    return out


if __name__ == "__main__":
    for nm in OFFICIAL:
        hits = fetch(nm, max_pages=1)
        print(f"{nm}: {len(hits)} 条")
        for h in hits:
            print("   ", h["portal"], "|", h["url"], "|", h["snippet"][:90])
