# -*- coding: utf-8 -*-
"""
语言识别（zh/ko/en）。
v2 (2026-10-22): 由"有某字符即判"改为按字符占比判定，解决中韩混排
（如"감천문화마을怎么去"应判 zh 而非 ko）与纯数字/短词回退问题。
"""
import re

RE_HANGUL = re.compile(r"[가-힣ᄀ-ᇿ㄰-ㆎ]")          # 谚文
RE_HAN = re.compile(r"[一-鿿㐀-䶿]")                   # 汉字
RE_LATIN = re.compile(r"[A-Za-z]")

SUPPORTED = ("zh", "ko", "en")

# 某语言字符占有效字符总数的比例超过该阈值才判定为该语言
DOMINANT_RATIO = 0.55
# 有效字符总数过少（纯标点/数字/短缩写）时不强行判定，回退界面语言
MIN_MEANINGFUL_CHARS = 2


def scores(text):
    t = text or ""
    return {"ko": len(RE_HANGUL.findall(t)),
            "zh": len(RE_HAN.findall(t)),
            "en": len(RE_LATIN.findall(t))}


def detect(text):
    """返回 zh / ko / en / None（None = 识别不出，回退界面语言）。

    判定规则：
      1. 统计三类字符数，取占比最高者；
      2. 最高者占比 < DOMINANT_RATIO 或有效字符过少 -> 返回 None；
      3. 中韩混排时，中文实词多即判 zh（韩文多为景点专名）。
    """
    s = scores(text)
    total = s["ko"] + s["zh"] + s["en"]
    if total < MIN_MEANINGFUL_CHARS:
        return None

    best = max(s, key=lambda k: s[k])
    if s[best] == 0:
        return None
    # 若第一名未达主导比例（混排严重），不强行判定
    if s[best] / total < DOMINANT_RATIO:
        return None
    return best


def resolve(question, ui_lang=None):
    """决定本次回答语言：优先提问语言，识别不出才用界面语言。"""
    ui_lang = ui_lang or "zh"
    if ui_lang not in SUPPORTED:
        ui_lang = "zh"

    import config
    if getattr(config, "ANSWER_LANG_MODE", "question") == "ui":
        return ui_lang
    return detect(question) or ui_lang


def detect_name(lang):
    return {"zh": "中文", "ko": "한국어", "en": "English"}.get(lang, lang)


if __name__ == "__main__":
    tests = [
        "甘川文化村 交通",
        "감천문화마을 교통",
        "How do I get to Gamcheon?",
        "감천문화마을怎么去",          # 中韩混排：应判 zh
        "甘川文化村怎么去啊",
        "1234",
        "多大浦海水浴场开放时间",
        "다대포해수욕장 몇 시에요?",
    ]
    for s in tests:
        sc = scores(s)
        print(f"{s!r:36} scores={sc} detect={detect(s)}")
