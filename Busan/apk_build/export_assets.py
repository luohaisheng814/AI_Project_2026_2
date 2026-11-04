# -*- coding: utf-8 -*-
"""
export_assets.py —— 为 Android 独立安装包生成离线数据资产

做的事：
  1. 读取四大玩法分类库 + docs 重点档案（复用 rag_core.KnowledgeBase 的解析结果）；
  2. 把每个景点的字段正文（去掉中文标签前缀）导出为 data.json；
  3. 中文正文经一次 LLM 调用批量翻译成韩文 / 英文，结果按内容哈希缓存，
     重复构建不会重复调用（缓存文件：apk_build/cache/translate.json）；
  4. 一并导出分类名 / 人数名 / 字段名 / 界面文案的三语表，供 app.js 直接使用。

输出：Busan/android/assets/data.json
用法：python apk_build/export_assets.py [--no-translate]
"""
import hashlib
import json
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

import config          # noqa: E402
import core_api        # noqa: E402
import intent_parser as IP  # noqa: E402
import i18n            # noqa: E402
import rag_core as RAG # noqa: E402

CACHE_DIR = os.path.join(BASE, "apk_build", "cache")
CACHE_FILE = os.path.join(CACHE_DIR, "translate.json")
OUT_FILE = os.path.join(BASE, "android", "assets", "data.json")

TRANSLATE_SYSTEM = (
    "你是釜山旅游资料的专业译者。把给定的中文景点字段逐条翻译成目标语言。\n"
    "硬性要求：\n"
    "1) 只输出 JSON 对象，键与输入完全一致，一个都不能少、不能多；\n"
    "2) 数字、时间、票价、距离、电话号码、公交/地铁线路号、URL 保持原样，不换算不省略；\n"
    "3) 不合并、不拆分、不新增、不删除条目；原文字里的换行用 \\n 保留；\n"
    "4) 专有名词用目标语言的惯用译法（如 감천문화마을 / Gamcheon Culture Village）；"
    "没有通用译法的地名保留中文原名；\n"
    "5) 不要输出解释、不要代码块标记。"
)

LANG_NAME = {"ko": "韩语", "en": "英语"}

# 人工校订的景点常用名：档案里的别名不全或缺译时以此为准，避免「喷泉写成海水浴场」这类错配
NAME_FIX = {
    "甘川文化村": {"ko": "감천문화마을", "en": "Gamcheon Culture Village"},
    "多大浦梦之夕阳喷泉": {"ko": "다대포 꿈의 낙조분수", "en": "Sunset Fountain of Dream"},
    "多大浦海水浴场": {"ko": "다대포해수욕장", "en": "Dadaepo Beach"},
    "没云台": {"ko": "몰운대", "en": "Molundae"},
    "乙淑岛候鸟公园": {"ko": "을숙도 철새도래지", "en": "Eulsukdo Migratory Bird Park"},
    "峨嵋山观景台": {"ko": "아미산 전망대", "en": "Amisan Observatory"},
    "洛东江河口生态中心": {"ko": "낙동강하구에코센터", "en": "Nakdong River Estuary Eco Center"},
    "长林浦口": {"ko": "장림포구", "en": "Jangnim Port"},
}

# ---------------- 离线安装包专用标签映射 ----------------
# 原始 txt 混用三种写法：「标签：」（块）/「标签」（块，无冒号）/「标签：内容」（单行）。
# 桌面版靠 LLM 读全文，离线版必须把每块拆成独立字段才能按问题命中，所以这里补全标签。
OFFLINE_LABEL_MAP = {
    "基本信息": "overview", "基本概况": "overview", "景点介绍": "overview", "介绍": "overview",
    "简介": "overview", "概况": "overview", "概览": "overview", "详情": "overview", "详细信息": "overview",

    "开放时间": "hours", "开放信息": "hours", "营业时间": "hours", "运营时间": "hours",
    "开放": "hours", "演出时间": "hours",

    "门票": "ticket", "费用": "ticket", "票价": "ticket", "价格": "ticket", "收费": "ticket",

    "游玩亮点": "highlights", "亮点": "highlights", "主要看点": "highlights", "看点": "highlights",

    "推荐路线": "course", "游玩路线": "course", "游览路线": "course", "游览顺序": "course",
    "行程": "course", "建议游玩时长": "course", "最佳时段": "course", "建议时长": "course",

    "拍照": "photo", "拍照点": "photo", "打卡": "photo", "打卡点": "photo", "摄影": "photo", "机位": "photo",

    "美食": "food", "餐饮": "food", "餐厅": "food", "推荐美食": "food", "小吃": "food",

    "适合人群": "audience", "适合谁": "audience", "推荐人群": "audience",

    "约束与注意事项": "tips", "注意事项": "tips", "贴士": "tips", "温馨提示": "tips",
    "注意": "tips", "提醒": "tips",

    "交通方式": "transport", "交通": "transport", "交通信息": "transport", "交通指南": "transport",
    "怎么去": "transport", "到达方式": "transport", "如何去": "transport", "怎么走": "transport",

    "周边配套": "around", "周边": "around", "附近": "around", "周边景点": "around",
    "距其他景点距离": "around", "距离其他景点": "around",

    "住宿": "stay", "住哪": "stay", "酒店": "stay",

    "历史": "history", "历史背景": "history", "由来": "history", "背景": "history",

    "来源网址": "source", "来源": "source", "官网": "source", "官方网站": "source",
    "参考网址": "source", "出处": "source", "网址": "source",
}

# 离线字段顺序（含 highlights，用于「亮点」类问题的独立小节）
OFFLINE_FIELD_ORDER = ["overview", "highlights", "hours", "ticket", "course", "transport",
                       "photo", "food", "audience", "tips", "stay", "around", "history", "source"]

_HEAD = re.compile(r"^([^\s：:\[\]【】]{2,16})(?:[：:](.*))?$")


def _norm_label(label):
    """「来源网址1」「来源网址2」这类带序号的标签归一到同一字段。"""
    return re.sub(r"\d+$", "", (label or "").strip())


def parse_offline_fields(raw):
    """把景点 txt 拆成 {字段: 正文}，三种标签写法都能识别，正文保留换行与要点符号。"""
    fields, order = {}, []
    cur = None
    for line in (raw or "").splitlines():
        text = line.rstrip()
        if not text.strip():
            if cur:
                fields[cur] += "\n"
            continue
        if text.strip().startswith("【") and text.strip().endswith("】"):
            continue                      # 景点标题行
        m = _HEAD.match(text.strip())
        key = None
        body = ""
        if m:
            key = OFFLINE_LABEL_MAP.get(_norm_label(m.group(1)))
            body = (m.group(2) or "").strip()
        if key:
            if key not in fields:
                fields[key] = ""
                order.append(key)
            cur = key
            if body:
                fields[cur] += ("\n" if fields[cur].strip() else "") + body
            continue
        if cur:
            fields[cur] += ("\n" if fields[cur].strip() else "") + text.strip()
    return {k: re.sub(r"\n{3,}", "\n\n", v).strip() for k, v in fields.items() if v.strip()}



def _strip_label(value):
    """'[基本信息]\\n正文' -> '正文'；没有标签前缀时原样返回。"""
    return re.sub(r"^[\[【][^\]】]{1,14}[\]】]\s*", "", (value or "").strip()).strip()


def _pick(raw, keys):
    for k in keys:
        m = re.search(rf"{k}\s*[：:]\s*(.+)", raw or "")
        if m:
            return m.group(1).strip()
    return ""


def _coords(raw):
    m = re.search(r"坐标\s*[：:]\s*([\d.]+)\s*[，,]\s*([\d.]+)", raw or "")
    if not m:
        return None, None
    try:
        return float(m.group(1)), float(m.group(2))
    except ValueError:
        return None, None


def _load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_cache(cache):
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=0, sort_keys=True)


def _key(text, lang):
    return hashlib.sha1((lang + "|" + text).encode("utf-8")).hexdigest()[:16]


def _parse_json_reply(text):
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(text[start:end + 1])
    except Exception:
        return None


def translate_fields(fields, lang, cache, verbose=True):
    """把 {field: 中文正文} 翻成目标语言；命中缓存直接用，失败的字段保留中文。"""
    todo = {k: v for k, v in fields.items() if v and _key(v, lang) not in cache}
    for k, v in fields.items():
        if v and _key(v, lang) in cache:
            cache[_key(v, lang)] = cache[_key(v, lang)]  # 保持键存在

    if todo and core_api.is_configured():
        payload = json.dumps(todo, ensure_ascii=False)
        reply = core_api.complete(
            TRANSLATE_SYSTEM,
            f"目标语言：{LANG_NAME[lang]}\n输入 JSON：\n{payload}",
            temperature=0.2, timeout=120, retries=1,
        )
        got = _parse_json_reply(reply) or {}
        for k, v in todo.items():
            out = (got.get(k) or "").strip()
            if out:
                cache[_key(v, lang)] = out
        if verbose:
            print(f"    [{lang}] 翻译 {len(todo)} 段，成功 {sum(1 for v in todo.values() if _key(v, lang) in cache)} 段")

    out = {}
    for k, v in fields.items():
        out[k] = cache.get(_key(v, lang), v) if v else ""
    return out


def main():
    no_translate = "--no-translate" in sys.argv
    if not core_api.is_configured():
        print("警告：未检测到可用 LLM 密钥，韩 / 英正文将回退中文原文（仅界面标签本地化）。")
        no_translate = True

    kb = RAG.KnowledgeBase()
    kb.load()

    cache = _load_cache()

    # 汇总景点：分类库里的档案 + 未被覆盖的重点档案
    docs = []
    seen = set()
    for cat in config.CATEGORIES:
        for doc in kb.by_category.get(cat, []):
            docs.append(doc)
            seen.add(doc.name)
    for cat, prof in kb.spot_profiles.items():
        if prof.name not in seen:
            docs.append(prof)
            seen.add(prof.name)

    spots = []
    for i, doc in enumerate(docs, 1):
        zh_fields = parse_offline_fields(doc.raw)
        if not zh_fields:                       # 兜底：解析不出块时整篇归入概况
            zh_fields = {"overview": (doc.raw or "").strip()}

        print(f"[{i}/{len(docs)}] {doc.name}（{doc.category}）字段 {len(zh_fields)} 个：{','.join(zh_fields.keys())}")
        entry = {
            "id": doc.name,
            "name": doc.name,
            "category": doc.category,
            "aliases": sorted({a for a in doc.aliases if a}),
            "address": _pick(doc.raw, ["地址"]),
            "lat": None,
            "lng": None,
            "fields": {"zh": zh_fields},
        }
        lat, lng = _coords(doc.raw)
        entry["lat"], entry["lng"] = lat, lng

        # 惯用名：韩文别名 / 英文别名，再用人工校订表兜底
        for lg, pat in (("ko", r"[가-힣]"), ("en", r"[A-Za-z\s'\-()]+")):
            name = next((a for a in doc.aliases if re.search(pat, a)), "")
            entry["name_" + lg] = NAME_FIX.get(doc.name, {}).get(lg) or name

        for lg in ("ko", "en"):
            if no_translate:
                entry["fields"][lg] = zh_fields
            else:
                entry["fields"][lg] = translate_fields(zh_fields, lg, cache)

        spots.append(entry)

    _save_cache(cache)

    # 分类级「适合人群」：三语文件都已存在，直接取正文
    audience = {}
    for cat in config.CATEGORIES:
        block = kb.audience.get("zh", "")
        audience[cat] = {}
        for lg in ("zh", "ko", "en"):
            seg = re.search(rf"\[{re.escape(cat)}\]\s*(.+?)(?=\n\[|\Z)",
                            kb.audience.get(lg, ""), re.S)
            audience[cat][lg] = (seg.group(1).strip() if seg else "")

    # 离线字段名：沿用桌面版三语字段名，另补 highlights（游玩亮点）三语名
    labels = {f: {lg: IP.FIELD_LABEL.get(f, {}).get(lg, f) for lg in config.SUPPORTED_LANGS}
              for f in OFFLINE_FIELD_ORDER if f != "highlights"}
    labels["highlights"] = {"zh": "游玩亮点", "ko": "주요 볼거리", "en": "Highlights"}

    strings = {
        "categories": {c: {lg: i18n.STRINGS[i18n.CATEGORY_KEYS[c]][lg] for lg in config.SUPPORTED_LANGS}
                       for c in config.CATEGORIES},
        "groups": {g: {lg: i18n.STRINGS[i18n.GROUP_KEYS[g]][lg] for lg in config.SUPPORTED_LANGS}
                   for g in config.GROUP_TYPES},
        "field_labels": labels,
        "field_order": OFFLINE_FIELD_ORDER,
        "ui": {k: {lg: v.get(lg, v.get("zh", "")) for lg in config.SUPPORTED_LANGS}
               for k, v in i18n.STRINGS.items() if isinstance(v, dict) and "zh" in v},
    }

    data = {
        "schema": 1,
        "generated_at": __import__("datetime").date.today().isoformat(),
        "strings": strings,
        "audience": audience,
        "spots": spots,
    }

    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))

    # 同时写一份 data.js：WebView 以 file:// 打开时读取本地 JSON 会被 CORS 拦截，
    # 直接以脚本注入全局变量最稳，不需要任何网络权限。
    js_file = os.path.join(os.path.dirname(OUT_FILE), "data.js")
    with open(js_file, "w", encoding="utf-8") as f:
        f.write("window.BUSAN_DATA=")
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")

    size = os.path.getsize(OUT_FILE)
    print(f"\n已写出 {OUT_FILE}（{len(spots)} 个景点，{size / 1024:.1f} KB）")
    print(f"已写出 {js_file}（{os.path.getsize(js_file) / 1024:.1f} KB）")
    empty_ko = sum(1 for s in spots if s["fields"]["ko"] == s["fields"]["zh"])
    if empty_ko:
        print(f"提示：{empty_ko} 个景点的韩文正文仍等同中文（翻译未生效或未配置密钥）")


if __name__ == "__main__":
    main()
