# classifier.py
# 按玩法把 rules.txt（核心数据库）拆成四类资料库。
# v2 (2026-10-22): 新增【】块提取，支持嵌套子景点（没云台/梦之夕阳喷泉/乙淑岛候鸟公园）。
import os
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RULES_FILE = os.path.join(BASE_DIR, "docs", "rules.txt")
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

# 分类文件里的景点名 -> rules.txt【】块标题的对应（扩展子景点）
BLOCK_ALIAS = {
    "多大浦梦之夕阳喷泉": "梦之夕阳喷泉",
    "乙淑岛候鸟公园": "乙淑岛候鸟公园",
    "没云台": "没云台",
}


def read_rules():
    if not os.path.exists(RULES_FILE):
        print("❌ 找不到 rules.txt:", RULES_FILE)
        return ""
    with open(RULES_FILE, "r", encoding="utf-8") as f:
        return f.read()


def split_spots(text):
    """按『N. 景点名』切分一级编号景点。"""
    pattern = re.compile(r'^(\d+)\.\s*(.+)$', re.MULTILINE)
    matches = list(pattern.finditer(text))
    spots = {}
    for i, m in enumerate(matches):
        title = m.group(2).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else text.find("按玩法来划分")
        if end == -1:
            end = len(text)
        body = text[start:end].strip()
        spots[title] = body
    return spots


def split_blocks(text):
    """按『【景点名】...』切分扩展子景点块（2026-10-22 补全段）。"""
    pattern = re.compile(r'【([^】]+)】[^\n]*\n(.*?)(?=\n【|$)', re.DOTALL)
    blocks = {}
    for m in pattern.finditer(text):
        title = m.group(1).strip()
        body = m.group(2).strip()
        if body:
            blocks[title] = body
    return blocks


def find_spot_body(spot, numbered, blocks):
    """依次：编号标题精确匹配 -> 编号标题子串匹配 -> 【】块别名匹配。"""
    # 1) 编号标题精确/子串匹配
    for t, b in numbered.items():
        if spot.split()[0] in t:
            return b
    # 2) 【】块：先按别名映射，再按名字包含
    block_title = BLOCK_ALIAS.get(spot, spot)
    if block_title in blocks:
        return blocks[block_title]
    for t, b in blocks.items():
        if block_title in t or t in block_title:
            return b
    return ""


def build_files(text):
    numbered = split_spots(text)
    blocks = split_blocks(text)
    print(f"  · 识别编号景点 {len(numbered)} 个，【】块 {len(blocks)} 个：{list(blocks.keys())}")

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
            body = find_spot_body(spot, numbered, blocks)
            spot_file = os.path.join(cat_dir, f"{spot}.txt")
            with open(spot_file, "w", encoding="utf-8") as f:
                f.write(f"【{spot}】\n")
                f.write(f"所属分类：{cat['name_zh']}\n\n")
                f.write(body if body else "（核心库待补充）")
            status = "✅" if body else "⚠️ 空"
            print(f"    {status} {cat_key}/{spot}.txt  ({len(body)} 字)")
            total += 1

    return total


def main():
    print("🗂️ 按玩法四类拆分 rules.txt ...")
    text = read_rules()
    if not text:
        return
    n = build_files(text)
    print(f"✅ 完成，生成 {n} 个文件 → {OUTPUT_BASE}/")


if __name__ == "__main__":
    main()
