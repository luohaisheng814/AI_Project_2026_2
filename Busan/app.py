import os
import sys
import re
from dotenv import load_dotenv
from openai import OpenAI

# 将当前脚本所在目录强制添加到 Python 搜索路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
BASE_URL = os.getenv("OPENAI_BASE_URL") or os.getenv("DASHSCOPE_BASE_URL")
MODEL = os.getenv("MODEL", "qwen-plus")

if not API_KEY:
    print("❌ .env未配置API_KEY，请先填写。 / API_KEY not configured. / .env에 API_KEY가 설정되지 않았습니다.")
    sys.exit(1)

# 导入推荐模块 / Import recommendation module / 추천 모듈 가져오기
from recommend import build_reco_text
from user_tracker import get_tracker, reset_tracker

# ============================================================
# 语言检测模块 / Language Detection Module / 언어 감지 모듈
# ============================================================

def detect_language(text):
    if not text or not text.strip():
        return 'unknown'
    chinese_count = 0
    korean_count = 0
    english_count = 0
    for char in text:
        if '\u4e00' <= char <= '\u9fff' or '\u3400' <= char <= '\u4dbf':
            chinese_count += 1
        elif '\uac00' <= char <= '\ud7af' or '\u1100' <= char <= '\u11ff' or '\u3130' <= char <= '\u318f':
            korean_count += 1
        elif ('a' <= char <= 'z') or ('A' <= char <= 'Z'):
            english_count += 1
    max_count = max(chinese_count, korean_count, english_count)
    if max_count == 0:
        return 'unknown'
    elif max_count == chinese_count:
        return 'zh'
    elif max_count == korean_count:
        return 'ko'
    else:
        return 'en'

def get_language_prompt(lang_code):
    if lang_code == 'zh':
        return "你必须始终使用中文回复用户。回答要详细、友好。知识库中有韩文原文时，请翻译成中文一并展示。"
    elif lang_code == 'ko':
        return "당신은 반드시 한국어로만 사용자에게 응답해야 합니다. 답변은 자세하고 친절하게 해주세요."
    elif lang_code == 'en':
        return "You must always reply in English. Be detailed and friendly."
    else:
        return "请使用中文回复。 / Please reply in Chinese. / 중국어로 답변해 주세요."

def get_language_name(lang_code):
    names = {
        'zh': '🇨🇳 中文 / Chinese / 중국어',
        'ko': '🇰🇷 韩文 / Korean / 한국어',
        'en': '🇺🇸 英文 / English / 영어',
        'unknown': '❓ 未知 / Unknown / 알 수 없음'
    }
    return names.get(lang_code, names['unknown'])

# ============================================================
# 知识库与问答模块 / Knowledge Base & Q&A / 지식 베이스 및 질의응답
# ============================================================

def load_rules():
    try:
        with open("rules.txt", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""

def ask(question, context, lang_code='zh'):
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    lang_instruction = get_language_prompt(lang_code)
    system_content = f"你是釜山旅游与设施问答助手。 / You are a Busan travel assistant. / 당신은 부산 여행 어시스턴트입니다.\n{lang_instruction}"
    
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_content},
            {"role": "user", "content": f"知识库上下文:\n{context}\n\n用户问题: {question}"}
        ],
        temperature=0.3,
        max_tokens=2000,
    )
    return response.choices[0].message.content

def classify_query(text):
    """
    简单分类查询文本 / Simple classification of query text / 조회 텍스트 간단 분류
    """
    text_lower = text.lower()
    categories = {
        "银行 / Bank / 은행": ["银行", "bank", "은행", "釜山银行", "友利银行", "부산은행", "우리은행"],
        "政府机关 / Government / 정부 기관": ["政府", "厅", "海关", "government", "office", "customs", "구청", "세관", "정부"],
        "文旅设施 / Tourism / 관광 시설": ["文化村", "海水浴场", "生态", "景点", "tourism", "beach", "village", "감천", "해수욕장", "관광"]
    }
    
    for category, keywords in categories.items():
        for kw in keywords:
            if kw.lower() in text_lower:
                return category, kw
    
    return "其他 / Other / 기타", ""

# ============================================================
# 主程序 / Main Program / 메인 프로그램
# ============================================================

def main():
    print("=" * 60)
    print("  🌏 釜山旅游与设施问答助手（智能追踪版）")
    print("  Busan Travel & Facilities Assistant (Smart Tracker)")
    print("  부산 여행 및 시설 질의응답 어시스턴트 (스마트 추적)")
    print("=" * 60)
    
    # 初始化追踪器 / Initialize tracker / 추적기 초기화
    tracker = get_tracker()
    
    # ---- 第一步：语言偏好检测 ----
    print("\n📌 语言偏好设置 / Language Preference / 언어 선호도 설정")
    print("-" * 50)
    lang_input = input("💬 请输入一句话检测语言偏好 / Enter to detect language / 언어 감지용 문장 입력: ").strip()
    
    if not lang_input:
        user_lang = 'zh'
    else:
        user_lang = detect_language(lang_input)
    
    lang_name = get_language_name(user_lang)
    print(f"\n✅ 检测到语言偏好：{lang_name}")
    print("-" * 50)
    
    # ---- 第二步：加载知识库 ----
    print("\n📄 加载知识库... / Loading knowledge base... / 지식 베이스 로딩 중...")
    rules_context = load_rules()
    if rules_context:
        print("✅ 知识库加载成功！ / Loaded! / 로드 완료!")
    else:
        print("⚠️ 未找到 rules.txt / Not found / 찾을 수 없음")
    
    # ---- 第三步：交互式问答 ----
    print("\n" + "=" * 60)
    print("  💬 开始问答（输入 'exit' 退出 / 'stats' 查看统计）")
    print("  Start Q&A / 질의응답 시작")
    print("=" * 60)
    
    query_count = 0
    
    while True:
        user_input = input("\n🙋 您的问题 / Question / 질문: ").strip()
        
        if not user_input:
            continue
        
        if user_input.lower() == 'exit':
            # 退出时显示会话总结 / Show session summary on exit / 종료 시 세션 요약 표시
            print("\n" + "=" * 60)
            print("  📊 会话总结 / Session Summary / 세션 요약")
            print("=" * 60)
            summary = tracker.get_session_summary()
            intent = tracker.predict_intent()
            
            if user_lang == 'zh':
                print(f"  总查询次数：{summary['total_queries']}")
                print(f"  会话时长：{summary['duration']}")
                print(f"  最常查询类别：{summary['top_category']}")
                print(f"  高频关键词：{summary['top_keyword']}")
                print(f"\n  🎯 意图预测：{intent['intent']}")
                print(f"  置信度：{intent['confidence']:.0%}")
                print(f"  原因：{intent['reason']}")
            elif user_lang == 'ko':
                print(f"  총 조회 횟수: {summary['total_queries']}")
                print(f"  세션 시간: {summary['duration']}")
                print(f"  가장 많이 조회한 분류: {summary['top_category']}")
                print(f"  자주 검색한 키워드: {summary['top_keyword']}")
                print(f"\n  🎯 의도 예측: {intent['intent']}")
                print(f"  신뢰도: {intent['confidence']:.0%}")
                print(f"  이유: {intent['reason']}")
            else:
                print(f"  Total queries: {summary['total_queries']}")
                print(f"  Session duration: {summary['duration']}")
                print(f"  Top category: {summary['top_category']}")
                print(f"  Top keyword: {summary['top_keyword']}")
                print(f"\n  🎯 Intent Prediction: {intent['intent']}")
                print(f"  Confidence: {intent['confidence']:.0%}")
                print(f"  Reason: {intent['reason']}")
            
            print("\n👋 感谢使用！再见！ / Thank you! Goodbye! / 이용해 주셔서 감사합니다!")
            break
        
        if user_input.lower() == 'stats':
            # 显示详细统计 / Show detailed stats / 상세 통계 표시
            print("\n" + "─" * 50)
            summary = tracker.get_session_summary()
            intent = tracker.predict_intent()
            frequent = tracker.get_frequent_items(threshold=2)
            
            if user_lang == 'zh':
                print("📊 会话统计 / Session Stats:")
                print(f"  查询次数：{summary['total_queries']}")
                print(f"  时长：{summary['duration']}")
                print(f"  类别分布：{dict(tracker.category_counts)}")
                print(f"  高频项目：{frequent}")
                print(f"\n🎯 意图预测：{intent['intent']} ({intent['confidence']:.0%})")
                print(f"   {intent['reason']}")
            elif user_lang == 'ko':
                print("📊 세션 통계:")
                print(f"  조회 횟수: {summary['total_queries']}")
                print(f"  시간: {summary['duration']}")
                print(f"  분류 분포: {dict(tracker.category_counts)}")
                print(f"\n🎯 의도 예측: {intent['intent']} ({intent['confidence']:.0%})")
                print(f"  {intent['reason']}")
            else:
                print("📊 Session Stats:")
                print(f"  Queries: {summary['total_queries']}")
                print(f"  Duration: {summary['duration']}")
                print(f"  Category distribution: {dict(tracker.category_counts)}")
                print(f"\n🎯 Intent: {intent['intent']} ({intent['confidence']:.0%})")
                print(f"  {intent['reason']}")
            print("─" * 50)
            continue
        
        # 检测当前输入语言 / Detect current input language / 현재 입력 언어 감지
        current_lang = detect_language(user_input)
        if current_lang != 'unknown' and current_lang != user_lang:
            user_lang = current_lang
            print(f"   🔄 语言切换至 / Language switched to / 언어 변경: {get_language_name(user_lang)}")
        
        # 分类查询 / Classify query / 조회 분류
        category, keyword = classify_query(user_input)
        
        # 记录到追踪器 / Record to tracker / 추적기에 기록
        tracker.record_query(user_input, category=category, keywords=[keyword] if keyword else None)
        query_count += 1
        
        # 每3次查询触发一次个性化推荐 / Trigger recommendation every 3 queries / 3회마다 추천 트리거
        if query_count % 3 == 0:
            print("\n" + "─" * 50)
            if user_lang == 'zh':
                print("📌 个性化推荐（基于您的查询历史）：")
            elif user_lang == 'ko':
                print("📌 개인화 추천 (조회 이력 기반):")
            else:
                print("📌 Personalized Recommendations (based on your history):")
            
            deep_recs = tracker.get_deep_recommendations(user_lang)
            if deep_recs:
                for rec in deep_recs:
                    print(f"  {rec}")
            else:
                if user_lang == 'zh':
                    print("  💡 继续查询以解锁更多个性化推荐！")
                elif user_lang == 'ko':
                    print("  💡 더 많은 개인화 추천을 위해 계속 조회해 주세요!")
                else:
                    print("  💡 Keep querying to unlock more personalized recommendations!")
            print("─" * 50)
        
        # 调用大模型回答 / Call LLM for answer / LLM 호출하여 답변
        print("\n🤖 助手思考中... / Thinking... / 생각 중...")
        answer = ask(user_input, rules_context, user_lang)
        print(f"\n{'─' * 50}")
        print(answer)
        print(f"{'─' * 50}")
        
        # 意图预测提示（每5次查询显示一次） / Show intent prediction every 5 queries / 5회마다 의도 예측 표시
        if query_count % 5 == 0:
            intent = tracker.predict_intent()
            print("\n" + "─" * 50)
            if user_lang == 'zh':
                print(f"🔮 意图预测：{intent['intent']} (置信度 {intent['confidence']:.0%})")
                print(f"   {intent['reason']}")
                print("   💡 接下来您可能需要：")
                if "旅游" in intent['intent']:
                    print("   → 查询交通路线、推荐住宿、查看天气")
                elif "居留" in intent['intent']:
                    print("   → 查询签证延期、银行开户、区厅地址")
                elif "金融" in intent['intent']:
                    print("   → 查询汇率、ATM位置、营业时间")
                elif "观光" in intent['intent']:
                    print("   → 查询门票价格、最佳游览时间、周边美食")
            elif user_lang == 'ko':
                print(f"🔮 의도 예측: {intent['intent']} (신뢰도 {intent['confidence']:.0%})")
                print(f"   {intent['reason']}")
                print("   💡 다음에 필요할 수 있는 것:")
                if "여행" in intent['intent']:
                    print("   → 교통 경로, 숙박 추천, 날씨 확인")
                elif "거주" in intent['intent']:
                    print("   → 비자 연장, 은행 계좌 개설, 구청 주소")
                elif "금융" in intent['intent']:
                    print("   → 환율, ATM 위치, 영업 시간")
                elif "관광" in intent['intent']:
                    print("   → 입장료, 베스트 방문 시간, 주변 맛집")
            else:
                print(f"🔮 Intent Prediction: {intent['intent']} (Confidence {intent['confidence']:.0%})")
                print(f"   {intent['reason']}")
                print("   💡 You may also need:")
                if "Travel" in intent['intent'] or "tourism" in intent['intent'].lower():
                    print("   → Transportation routes, accommodation, weather")
                elif "Residence" in intent['intent']:
                    print("   → Visa extension, bank account, district office")
                elif "Financial" in intent['intent']:
                    print("   → Exchange rates, ATM locations, business hours")
                elif "Sightseeing" in intent['intent']:
                    print("   → Ticket prices, best visiting time, nearby food")
            print("─" * 50)


if __name__ == "__main__":
    main()