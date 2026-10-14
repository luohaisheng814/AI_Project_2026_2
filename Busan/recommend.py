def get_recommendations(history):
    last = history[-1]
    if "银行" in last:
        return "→ 检测到您关注银行，推荐：友利银行沙下区网点"
    if "海水浴场" in last:
        return "→ 检测到您关注海岸，推荐：没云台海岸"
    if "沙下区" in last:
        return "→ 推荐探索：甘川文化村、乙淑岛候鸟公园"
    return "→ 试试问：某某景点 怎么去 / 适合谁"

def predict_intent(history):
    if len(history) < 3: return "数据不足"
    if any("交通" in h or "怎么去" in h for h in history):
        return "🎯 意图：出行规划"
    if any("玩法" in h or "概况" in h for h in history):
        return "🎯 意图：游览规划"
    return "🎯 意图：一般咨询"