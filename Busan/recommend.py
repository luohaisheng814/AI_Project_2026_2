import json
import os

RECOMMENDATIONS_FILE = "recommend_rules.json"

def load_recommendations():
    """加载推荐数据 / Load recommendation data / 추천 데이터 로드"""
    if not os.path.exists(RECOMMENDATIONS_FILE):
        print(f"❌ 未找到 {RECOMMENDATIONS_FILE} / Not found / 파일을 찾을 수 없습니다.")
        return {}
    try:
        with open(RECOMMENDATIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print("❌ JSON解析失败 / JSON parse failed / JSON 파싱 실패")
        return {}

def build_reco_text(category, sub_category):
    """生成推荐文本 / Generate recommendation text / 추천 텍스트 생성"""
    data = load_recommendations()
    
    # 默认推荐 / Default recommendation / 기본 추천
    default_reco = {
        "related": ["暂无相关推荐。 / No related recommendations. / 관련 추천이 없습니다."],
        "other_pick": "暂无其他推荐。 / No other picks. / 다른 추천이 없습니다."
    }
    
    try:
        cat_data = data.get(category, {})
        reco_info = cat_data.get(sub_category, default_reco)
        
        related_text = "\n".join([f"- {item}" for item in reco_info.get("related", [])])
        other_pick = reco_info.get("other_pick", default_reco["other_pick"])
        
        # 拼接三语输出 / Concatenate trilingual output / 삼중 언어 출력 결합
        result = f"""📌 相关推荐 / Related Recommendations / 관련 추천:
{related_text}

💡 其他推荐 / Other Pick / 다른 추천:
- {other_pick}
"""
        return result
    except Exception as e:
        print(f"❌ 生成推荐文本出错 / Error generating text / 텍스트 생성 오류: {e}")
        return "推荐功能暂时不可用。 / Recommendation unavailable. / 추천 기능을 사용할 수 없습니다."

if __name__ == "__main__":
    # 测试 / Test / 테스트
    print(build_reco_text("银行 / Bank / 은행", "釜山银行 / Busan Bank / 부산은행"))