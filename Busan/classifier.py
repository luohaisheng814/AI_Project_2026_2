# classifier.py
import os
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RULES_FILE = os.path.join(BASE_DIR, "rules.txt")
OUTPUT_BASE = os.path.join(BASE_DIR, "activity_classified")

# 四类映射（严格按 rules.txt 底部写法）
CATEGORIES = {
    "01_艺术村落_文化街区": {
        "name_zh": "🎨 艺术村落 & 文化街区类",
        "spots": ["甘川文化村"],
        "audience_zh": "文艺青年、亲子家庭、摄影爱好者",
        "audience_ko": "문예 청년, 가족 여행객, 사진 애호가",
        "audience_en": "Art lovers, families, photographers",
    },
    "02_海岸休闲_日落夜景": {
        "name_zh": "🌅 海岸休闲 & 日落夜景类",
        "spots": ["多大浦海水浴场", "多大浦梦之夕阳喷泉", "没云台"],
        "audience_zh": "情侣、家庭游客、喜欢看海和夜景的人",
        "audience_ko": "커플, 가족, 바다·야경 선호 관광객",
        "audience_en": "Couples, families, sea/sunset lovers",
    },
    "03_湿地生态_自然观景": {
        "name_zh": "🏞️ 湿地生态 & 自然观景类",
        "spots": ["洛东江河口生态中心", "乙淑岛候鸟公园", "峨嵋山观景台"],
        "audience_zh": "自然爱好者、鸟类摄影师、亲子研学",
        "audience_ko": "자연 애호가, 조류 사진가, 가족 생태학습",
        "audience_en": "Nature lovers, bird photographers, families",
    },
    "04_小众渔港_文艺拍照": {
        "name_zh": "📸 小众渔港 & 文艺拍照类",
        "spots": ["长林浦口"],
        "audience_zh": "喜欢避开人潮的背包客、SNS打卡族",
        "audience_ko": "한적한 곳을 찾는 배낭여행객, SNS 촬영족",
        "audience_en": "Backpackers avoiding crowds, SNS photographers",
    },
}

def read_rules():
    if not os.path.exists(RULES_FILE):
        print("❌ 找不到 rules.txt")
        return ""
    with open(RULES_FILE, "r", encoding="utf-8") as f:
        return f.read()

def split_spots(text):
    """按『N. 景点名』切分 rules.txt"""
    pattern = re.compile(r'^(\d+)\.\s*(.+)$', re.MULTILINE)
    matches = list(pattern.finditer(text))
    spots = {}
    for i, m in enumerate(matches):
        title = m.group(2).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else text.find("按玩法来划分")
        # 没到「按玩法」之前都算景点正文
        if end == -1:
            end = len(text)
        body = text[start:end].strip()
        spots[title] = body
    return spots

def build_files(spots):
    total = 0
    for cat_key, cat in CATEGORIES.items():
        cat_dir = os.path.join(OUTPUT_BASE, cat_key)
        os.makedirs(cat_dir, exist_ok=True)

        # 适合人群三语
        for lang, suf in [("zh", "中文"), ("en", "English"), ("ko", "한국어")]:
            with open(os.path.join(cat_dir, f"适合人群_{suf}.txt"), "w", encoding="utf-8") as f:
                f.write(f"{cat['name_zh']}\n适合人群：{cat[f'audience_{lang}']}\n")
            total += 1

        # 每个景点一个文件
        for spot in cat["spots"]:
            # rules.txt 里标题可能带韩文，做模糊匹配
            matched_body = ""
            matched_title = spot
            for t, b in spots.items():
                if spot.split()[0] in t:
                    matched_body = b
                    matched_title = t
                    break

            spot_file = os.path.join(cat_dir, f"{spot}.txt")
            with open(spot_file, "w", encoding="utf-8") as f:
                f.write(f"【{spot}】\n")
                f.write(f"所属分类：{cat['name_zh']}\n\n")
                f.write(matched_body if matched_body else "（核心库待补充）")
            total += 1

    return total

def main():
    print("🗂️ 按玩法四类拆分 rules.txt ...")
    text = read_rules()
    if not text:
        return
    spots = split_spots(text)
    n = build_files(spots)
    print(f"✅ 完成，生成 {n} 个文件 → {OUTPUT_BASE}/")

if __name__ == "__main__":
    main()