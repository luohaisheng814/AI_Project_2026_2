"""核心逻辑接口（确保返回纯字符串，不返回列表或元组）"""

SPOT_INFO = {
    "甘川文化村": "位于沙下区的艺术村落，以彩色壁画和阶梯式建筑闻名。",
    "多大浦海水浴场": "适合看日落的海水浴场，夏季有梦幻夕阳喷泉。",
    "洛东江河口生态中心": "可以观察湿地生态和候鸟的天然教育场。"
}

def ask(question, session_id="default"):
    """统一的问答接口，必须返回纯字符串"""
    if not question or not question.strip():
        return ""
        
    if "沙下区" in question or "景点" in question:
        reply = "📍 沙下区核心景点：甘川文化村、多大浦海水浴场、洛东江河口生态中心等。"
    else:
        spot_found = None
        for spot in SPOT_INFO:
            if spot in question:
                spot_found = spot
                break
        
        if spot_found:
            if "概况" in question:
                reply = f"🤖 {spot_found}概况：{SPOT_INFO[spot_found]}"
            elif "怎么去" in question:
                reply = f"🚇 前往{spot_found}：建议乘坐釜山地铁1号线。"
            else:
                reply = f"🤖 系统：已识别到{spot_found}，请问需要了解概况还是交通？"
        else:
            reply = "💡 未识别到景点，试试：甘川文化村 概况 / 多大浦海水浴场 怎么去"
            
    return reply

def reset_session(session_id):
    print(f"Session {session_id} reset.")