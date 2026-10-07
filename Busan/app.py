import os
import sys
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

def load_rules():
    """读取知识库 / Read knowledge base / 지식 베이스 읽기"""
    try:
        with open("rules.txt", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""

def ask(question, context):
    """调用大模型问答 / Call LLM for Q&A / LLM 호출"""
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "你是釜山旅游与设施问答助手。 / You are a Busan travel and facilities assistant. / 당신은 부산 여행 및 시설 질의응답 어시스턴트입니다.\n【强制语言指令 / Mandatory Language Instruction / 강제 언어 지침】：你必须始终使用中文、英文、韩文三种语言回复用户。回答的主体和详细内容必须优先使用中文。如果知识库上下文中有韩文原文，请将其保留并翻译为中文和英文。禁止只使用单一语言（尤其是禁止只回复韩文）作答。"},
            {"role": "user", "content": f"知识库上下文:\n{context}\n\n用户问题: {question} / Question: {question} / 질문: {question}"}
        ]
    )
    return response.choices[0].message.content

if __name__ == "__main__":
    print("=" * 50)
    print("  釜山旅游与设施问答助手")
    print("  Busan Travel and Facilities Assistant")
    print("  부산 여행 및 시설 질의응답 어시스턴트")
    print("=" * 50)
    
    # 读取知识库 / Read knowledge base / 지식 베이스 읽기
    rules_context = load_rules()
    
    # 测试推荐功能 / Test recommendation feature / 추천 기능 테스트
    category = "银行 / Bank / 은행"
    sub_category = "釜山银行 / Busan Bank / 부산은행"
    print(build_reco_text(category, sub_category))
    
    # 交互式问答 / Interactive Q&A / 대화형 질의응답
    while True:
        user_input = input("请输入您的问题 / Enter your question / 질문을 입력하세요 (输入 'exit' 退出 / type 'exit' to quit / 'exit' 입력 시 종료): ")
        if user_input.lower() == 'exit':
            break
            
        answer = ask(user_input, rules_context)
        print(f"🤖 助手回答 / Assistant Answer / 어시스턴트 답변:")
        print(answer)
    