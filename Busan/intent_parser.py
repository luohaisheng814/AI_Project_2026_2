import re
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_BASE = os.path.join(BASE_DIR, "activity_classified")
RULES_FILE = os.path.join(BASE_DIR, "rules.txt")

# 景点别名映射（兼容用户输入差异）
SPOT_ALIAS = {
    "甘川文化村": "甘川文化村",
    "多大浦海水浴场": "多大浦海水浴场",
    "多大浦": "多大浦海水浴场",
    "洛东江河口生态中心": "洛东江河口生态中心",
    "乙淑岛候鸟公园": "乙淑岛候鸟公园",
    "峨嵋山观景台": "峨嵋山观景台",
    "峨眉山": "峨嵋山观景台",
    "长林浦口": "长林浦口",
    "长林浦": "长林浦口"
}

INTENT_KEYWORDS = {
    "概况": ["概况", "基本信息", "介绍"],
    "交通": ["交通", "怎么去", "地址", "位置", "几号线"],
    "适合人群": ["适合人群", "适合谁", "带小孩", "亲子"],
    "玩法": ["玩法", "看点", "推荐活动", "怎么玩"]
}

def detect_spot(text):
    """识别文本中的景点名称"""
    for alias, standard_name in SPOT_ALIAS.items():
        if alias in text:
            return standard_name
    return None

def detect_intent(text):
    """识别用户意图"""
    for intent, keywords in INTENT_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                return intent
    return "概况"  # 默认意图

def find_spot_file(spot_name):
    """在分类文件夹中查找景点文件"""
    if not os.path.exists(OUTPUT_BASE):
        return None
        
    for folder in os.listdir(OUTPUT_BASE):
        folder_path = os.path.join(OUTPUT_BASE, folder)
        if os.path.isdir(folder_path):
            file_path = os.path.join(folder_path, f"{spot_name}.txt")
            if os.path.exists(file_path):
                return file_path
    return None

def read_core_db(spot_name):
    """从核心数据库rules.txt中读取景点内容"""
    if not os.path.exists(RULES_FILE):
        return None
        
    with open(RULES_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # 简单匹配景点段落（按数字序号或标题）
    pattern = re.compile(rf'(?:^|\n)\d+\.\s*{re.escape(spot_name)}.*?(?=\n\d+\.|$)', re.DOTALL)
    match = pattern.search(content)
    if match:
        return match.group(0).strip()
    return None

def extract_section(text, intent):
    """从景点文本中提取特定意图的段落"""
    if not text:
        return None
        
    # 匹配标题行（兼容emoji、序号、冒号等格式）
    # 修正了之前的regex错误，并增强了匹配能力
    lines = text.split('\n')
    target_lines = []
    capture = False
    
    intent_map = {
        "概况": ["基本概况", "景点介绍", "概况", "基本信息"],
        "交通": ["交通信息", "交通指南", "怎么去", "地址"],
        "适合人群": ["适合人群", "推荐人群"],
        "玩法": ["玩法推荐", "看点", "活动推荐"]
    }
    
    keywords = intent_map.get(intent, [])
    
    for line in lines:
        stripped = line.strip()
        # 检查是否为目标标题
        is_target_title = any(kw in stripped for kw in keywords)
        # 检查是否为其他板块的标题（停止捕获）
        is_other_title = any(stripped.startswith(kw) for kw in ["基本概况", "交通信息", "适合人群", "玩法推荐", "景点介绍"])
        
        if is_target_title:
            capture = True
            target_lines.append(stripped)
        elif is_other_title and capture:
            break
        elif capture:
            target_lines.append(stripped)
            
    if len(target_lines) > 1:
        return "\n".join(target_lines)
        
    # 如果没匹配到结构化段落，且是概况意图，返回前几行作为兜底
    if intent == "概况" and len(lines) > 1:
        return "\n".join(lines[:3]) # 返回前三行
        
    return None

def get_spot_info(spot_name, intent):
    """整合获取景点信息"""
    # 1. 优先从分类文件夹查找
    file_path = find_spot_file(spot_name)
    content = None
    
    if file_path:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
    # 2. 如果分类文件夹没有，从核心库查找
    if not content:
        content = read_core_db(spot_name)
        
    if not content:
        return f"⚠️ 暂无【{spot_name}】的相关内容，请待开发者补充。"
        
    # 3. 提取特定意图的内容
    section = extract_section(content, intent)
    
    if section:
        return f"📖 关于“{spot_name}”的{intent}：\n{section}"
    else:
        # 兜底：如果没提取到特定段落，返回简要提示
        return f"📖 关于“{spot_name}”的{intent}：\n(已找到该景点基础数据，但未发现结构化“{intent}”标签。默认展示概况)\n{content.split(chr(10))[0] if content else ''}"

def get_recommendations(history):
    last = history[-1]
    spot = detect_spot(last)
    if spot:
        return f"已识别景点【{spot}】，可继续问「交通/玩法/适合人群」"
    if "沙下区" in last:
        return "→ 推荐：甘川文化村、多大浦海水浴场、长林浦口"
    return "→ 试试问：某某景点 怎么去 / 适合谁"

def predict_intent(history):
    if len(history) < 3:
        return "数据不足"
    if any("交通" in h or "怎么去" in h for h in history):
        return "🎯 意图：出行规划"
    if any("玩法" in h or "概况" in h for h in history):
        return "🎯 意图：游览规划"
    return "🎯 意图：一般咨询"