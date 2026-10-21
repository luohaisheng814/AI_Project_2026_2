# -*- coding: utf-8 -*-

import re

FIELDS = ["overview", "transport", "hours", "ticket", "photo", "food",
          "course", "audience", "tips", "source", "stay", "around", "history"]

FIELD_LABEL = {
    "overview":  {"zh": "介绍/概况", "ko": "소개/개요", "en": "Overview"},
    "transport": {"zh": "交通", "ko": "교통", "en": "Transportation"},
    "hours":     {"zh": "开放信息", "ko": "개방 정보", "en": "Opening Hours"},
    "ticket":    {"zh": "门票/费用", "ko": "요금", "en": "Tickets & Fees"},
    "course":    {"zh": "推荐路线", "ko": "추천 코스", "en": "Suggested Route"},
    "photo":     {"zh": "拍照打卡", "ko": "사진 명소", "en": "Photo Spots"},
    "food":      {"zh": "美食", "ko": "맛집", "en": "Food"},
    "audience":  {"zh": "适合人群", "ko": "추천 대상", "en": "Best For"},
    "tips":      {"zh": "注意事项", "ko": "주의사항", "en": "Tips"},
    "source":    {"zh": "来源网址", "ko": "출처", "en": "Sources"},
    "stay":      {"zh": "住宿", "ko": "숙소", "en": "Accommodation"},
    "around":    {"zh": "周边", "ko": "주변", "en": "Nearby"},
    "history":   {"zh": "历史背景", "ko": "역사/배경", "en": "History"},
}

FIELD_ORDER = ["overview", "transport", "hours", "ticket", "course", "photo",
               "food", "audience", "tips", "stay", "around", "history", "source"]

# ---------------- 标签 -> 字段（解析 txt） ----------------
LABEL_MAP = {
    "介绍": "overview", "简介": "overview", "概况": "overview", "概览": "overview",
    "详情": "overview", "详细信息": "overview", "景点介绍": "overview", "基本信息": "overview",
    "소개": "overview", "개요": "overview",
    "introduction": "overview", "overview": "overview", "about": "overview", "description": "overview",

    "交通": "transport", "交通信息": "transport", "交通指南": "transport", "怎么去": "transport",
    "到达方式": "transport", "怎么走": "transport", "如何去": "transport", "位置": "transport",
    "교통": "transport", "가는법": "transport", "가는 법": "transport", "오시는 길": "transport",
    "교통정보": "transport", "교통 안내": "transport",
    "transportation": "transport", "transport": "transport", "getting there": "transport",
    "how to get": "transport", "access": "transport", "directions": "transport", "location": "transport",

    "开放信息": "hours", "开放时间": "hours", "营业时间": "hours", "运营时间": "hours",
    "开放": "hours", "入园时间": "hours", "演出时间": "hours",
    "개방정보": "hours", "개방시간": "hours", "운영시간": "hours", "개방 시간": "hours", "운영 시간": "hours",
    "opening hours": "hours", "opening": "hours", "hours": "hours", "open time": "hours",
    "opening time": "hours", "business hours": "hours",

    "门票": "ticket", "费用": "ticket", "票价": "ticket", "价格": "ticket", "收费": "ticket",
    "입장료": "ticket", "요금": "ticket", "이용요금": "ticket",
    "ticket": "ticket", "price": "ticket", "fee": "ticket", "cost": "ticket",
    "admission": "ticket", "entrance fee": "ticket",

    "来源网址": "source", "来源": "source", "参考网址": "source", "官方网址": "source",
    "官网": "source", "出处": "source", "参考资料": "source", "网址": "source",
    "출처": "source", "공식 사이트": "source", "참고 사이트": "source", "출처 사이트": "source",
    "source": "source", "website": "source", "official site": "source", "link": "source",
    "reference": "source", "url": "source",

    "贴士": "tips", "注意事项": "tips", "建议": "tips", "温馨提示": "tips", "注意": "tips",
    "주의사항": "tips", "팁": "tips", "유의사항": "tips",
    "tips": "tips", "note": "tips", "notice": "tips", "advice": "tips", "caution": "tips",

    "拍照": "photo", "打卡": "photo", "打卡点": "photo", "摄影": "photo", "拍照点": "photo",
    "사진": "photo", "포토존": "photo", "촬영": "photo", "사진 명소": "photo",
    "photo": "photo", "picture": "photo", "photo spot": "photo", "instagram": "photo",

    "美食": "food", "餐饮": "food", "餐厅": "food", "推荐美食": "food",
    "맛집": "food", "음식": "food", "식당": "food",
    "food": "food", "restaurant": "food", "eat": "food", "dining": "food",

    "适合人群": "audience", "适合谁": "audience", "推荐人群": "audience",
    "적합한 사람": "audience", "추천 대상": "audience", "적합 대상": "audience",
    "suitable for": "audience", "best for": "audience", "audience": "audience", "who should go": "audience",

    "推荐路线": "course", "游玩路线": "course", "游览路线": "course", "行程": "course",
    "怎么玩": "course", "路线": "course", "游览顺序": "course",
    "추천 코스": "course", "코스": "course", "여행 코스": "course", "관람 코스": "course",
    "course": "course", "itinerary": "course", "route": "course", "how to play": "course",

    "住宿": "stay", "住哪": "stay", "酒店": "stay", "숙소": "stay", "호텔": "stay",
    "hotel": "stay", "stay": "stay", "accommodation": "stay",

    "周边": "around", "附近": "around", "周边景点": "around", "주변": "around", "근처": "around",
    "nearby": "around", "around": "around",

    "历史": "history", "由来": "history", "背景": "history", "역사": "history", "유래": "history",
    "history": "history", "background": "history",
}

# ---------------- 提问意图规则（顺序即优先级，越具体越靠前） ----------------
INTENT_RULES = [
    ("source", ["来源网址", "来源", "出处", "网址", "官网", "链接", "출처", "공식사이트", "공식 사이트",
                "source", "website", "official", "link", "url"]),
    ("transport", ["怎么去", "怎么走", "如何去", "怎么到达", "怎么过去", "交通", "坐地铁", "地铁", "公交",
                   "巴士", "公交巴士", "打车", "停车", "교통", "가는법", "가는 법", "지하철", "버스",
                   "transportation", "transport", "how to get", "how do i get", "how do i go",
                   "get to", "go to", "getting there", "subway", "bus",
                   "access", "direction"]),
    ("hours", ["开放时间", "开放信息", "营业时间", "运营时间", "几点开门", "几点关门", "几点", "开放",
               "开门", "关门", "개방시간", "운영시간", "개방", "운영 시간", "몇 시",
               "opening hours", "when does", "opening", "hours", "open time", "open"]),
    ("ticket", ["多少钱", "门票", "票价", "收费", "免费吗", "要钱吗", "费用", "입장료", "요금", "무료",
                "ticket", "price", "fee", "cost", "admission", "free"]),
    ("photo", ["拍照", "出片", "打卡", "摄影", "사진", "포토", "촬영", "photo", "picture", "instagram"]),
    ("food", ["美食", "吃什么", "餐厅", "好吃", "맛집", "음식", "food", "restaurant", "eat"]),
    ("course", ["怎么玩", "游玩路线", "推荐路线", "游览路线", "行程", "路线", "安排", "半天", "一日",
                "추천 코스", "코스", "관람 코스", "itinerary", "course", "route", "plan", "how to play"]),
    ("audience", ["适合人群", "适合谁", "什么人", "带小孩", "带孩子", "적합", "추천 대상",
                  "suitable", "best for", "who should"]),
    ("tips", ["注意", "贴士", "建议", "准备", "穿什么", "주의", "팁", "tip", "advice", "note", "prepare"]),
    ("stay", ["住宿", "住哪", "酒店", "숙소", "hotel", "stay", "accommodation"]),
    ("around", ["周边", "附近", "旁边", "주변", "근처", "nearby", "around"]),
    ("history", ["历史", "由来", "背景", "为什么叫", "역사", "유래", "history", "background"]),
    ("overview", ["介绍", "简介", "概况", "详情", "详细", "什么样", "是什么", "怎么样", "好玩吗",
                  "개요", "소개", "어때", "about", "overview", "introduction", "introduce",
                  "what is", "tell me about", "info"]),
]

# ---------------- 停用词（助词 / 辅助词，检索时忽略） ----------------
STOPWORDS = set("""
的 了 是 在 我 你 他 她 它 们 请 想 要 问 一下 请问 帮我 告诉 我 知道 吗 呢 啊 呀 吧 哦 嗯 哈
关于 对于 这个 那个 这里 那里 有 没有 可以 能 会 很 太 非常 就 都 也 还 再 又 和 与 或 及
谢谢 感谢 麻烦 你好 您好 hi hello 请问下 请问一下 一下儿 给我 我想 我想要 谁能 谁可以
은 는 이 가 을 를 의 에 에서 로 으로 와 과 도 만 까지 부터 요 죠 네요 네 다
the a an is are was were do does did i you he she it we they my your this that there here
about please tell me can could would should what when where who how why
""".split())


def strip_noise(text):
    """去掉标点与助词，返回核心关键词列表。"""
    text = re.sub(r"[，。！？、；：""''（）()\[\]【】《》,.!?;:'\"~/|]", " ", text or "")
    return [t for t in text.split() if t and t not in STOPWORDS]


def detect_field(query):
    """识别要查的字段；None = 要全部信息（只给了景点名）。"""
    q = (query or "").lower()
    for field, words in INTENT_RULES:
        for w in sorted(words, key=len, reverse=True):
            if w.lower() in q:
                return field
    return None


def detect_field_detail(query):
    """返回 (field, 命中的词)，便于调试与日志。"""
    q = (query or "").lower()
    for field, words in INTENT_RULES:
        for w in sorted(words, key=len, reverse=True):
            if w.lower() in q:
                return field, w
    return None, None


def is_only_spot_name(question, spot_aliases):
    """判断是不是只输入了景点名（去掉景点名后没有其它实词）。"""
    rest = question or ""
    for a in sorted(spot_aliases or [], key=len, reverse=True):
        rest = rest.replace(a, " ")
    return not strip_noise(rest)


def parse_fields(text):
    """把 txt 解析成 {field_key: "[标签]\n内容"}，兼容 [标签] / 【标签】 / 标签：/ 纯文本。"""
    text = (text or "").strip()
    if not text:
        return {}

    pattern = re.compile(r"^\s*[\[【]?\s*([^\]\[】\n]{1,12})\s*[\]】]?\s*[:：]?\s*$", re.M)
    matches = list(pattern.finditer(text))

    fields = {}
    if matches:
        for idx, m in enumerate(matches):
            label = m.group(1).strip()
            start = m.end()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
            body = text[start:end].strip()
            key = LABEL_MAP.get(label.lower()) or LABEL_MAP.get(label)
            if key:
                fields.setdefault(key, "")
                fields[key] += ("\n" if fields[key] else "") + f"[{label}]\n{body}"
        if fields:
            return fields

    fields["overview"] = text
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        head = re.split(r"[:：\s]", line, 1)[0][:12].lower()
        key = LABEL_MAP.get(head)
        if key and key != "overview":
            fields.setdefault(key, "")
            fields[key] += ("\n" if fields[key] else "") + line
    return fields


def localize_labels(text, lang):
    """把 [交通] 换成当前语言标签（离线直出时不露中文标签）。"""
    def rep(m):
        label = m.group(1).strip()
        key = LABEL_MAP.get(label) or LABEL_MAP.get(label.lower())
        if key:
            return f"【{FIELD_LABEL.get(key, {}).get(lang, label)}】"
        return m.group(0)
    return re.sub(r"[\[【]\s*([^\]\[】\n]{1,12})\s*[\]】]", rep, text or "")


if __name__ == "__main__":
    for q in ["甘川文化村", "甘川文化村 交通", "감천문화마을 교통", "Gamcheon opening hours", "请问甘川文化村怎么去啊？"]:
        print(f"{q!r:42} -> field={detect_field(q)}  keywords={strip_noise(q)}")