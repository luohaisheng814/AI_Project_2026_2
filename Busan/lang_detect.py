import re
import config

RE_HANGUL = re.compile(r"[\uac00-\ud7af\u1100-\u11ff\u3130-\u318f]")   # 谚文
RE_HAN = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")                   # 汉字
RE_LATIN = re.compile(r"[A-Za-z]")

SUPPORTED = ("zh", "ko", "en")


def scores(text):
    t = text or ""
    return {"ko": len(RE_HANGUL.findall(t)),
            "zh": len(RE_HAN.findall(t)),
            "en": len(RE_LATIN.findall(t))}


def detect(text):
    """返回 zh / ko / en / None（None = 识别不出）。"""
    s = scores(text)
    if s["ko"] > 0:
        return "ko"
    if s["zh"] > 0:
        return "zh"
    if s["en"] > 0:
        return "en"
    return None


def resolve(question, ui_lang=None):
    """决定本次回答语言：优先提问语言，识别不出才用界面语言。"""
    ui_lang = ui_lang or getattr(config, "DEFAULT_LANG", "zh") or "zh"
    if ui_lang not in SUPPORTED:
        ui_lang = "zh"

    if getattr(config, "ANSWER_LANG_MODE", "question") == "ui":
        return ui_lang
    return detect(question) or ui_lang


def detect_name(lang):
    return {"zh": "中文", "ko": "한국어", "en": "English"}.get(lang, lang)


if __name__ == "__main__":
    for s in ["甘川文化村 交通", "감천문화마을 교통", "How do I get to Gamcheon?", "甘川文化村", "1234"]:
        print(f"{s!r:40} detect={detect(s)}  resolve(zh 界面)={resolve(s, 'zh')}")