import os
import sys
import json
import re
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
BASE_URL = os.getenv("OPENAI_BASE_URL") or os.getenv("DASHSCOPE_BASE_URL")
MODEL = os.getenv("MODEL", "qwen-plus")

if not API_KEY:
    print("❌ .env未配置API_KEY。 / API_KEY not configured. / .env에 API_KEY가 설정되지 않았습니다.")
    sys.exit(1)

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
OUTPUT_BASE = "classified_data"

def read_rules():
    try:
        with open("rules.txt", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print("❌ 未找到 rules.txt 文件。 / rules.txt not found. / rules.txt 파일을 찾을 수 없습니다.")
        sys.exit(1)

def classify_with_ai(text):
    prompt = f"""请将以下釜山设施文本分类为三大类：银行、政府机关、文旅设施。
Bank / Government / Tourism.
은행 / 정부 기관 / 관광 시설.

文本内容 / Text / 텍스트 내용:
{text}

输出严格JSON格式 / Output strict JSON format / 엄격한 JSON 형식으로 출력:
[{{"main_category": "银行 / Bank / 은행", "sub_category": "釜山银行 / Busan Bank / 부산은행", "title": "标题 / Title / 제목", "content": "内容 / Content / 내용"}}]"""
    
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=2000,
        )
        
        raw_content = response.choices[0].message.content
        
        if not raw_content or not raw_content.strip():
            print("❌ 错误：模型返回为空。 / Error: Model returned empty. / 오류: 모델이 빈 값을 반환했습니다.")
            return []
            
        cleaned_content = re.sub(r'^```(?:json)?\s*|\s*```$', '', raw_content.strip())
        return json.loads(cleaned_content)
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON解析失败 / JSON parse failed / JSON 파싱 실패: {e}")
        return []
    except Exception as e:
        print(f"❌ API调用或其他错误 / API call or other error / API 호출 또는 기타 오류: {e}")
        return []

def create_files(data):
    if not os.path.exists(OUTPUT_BASE):
        os.makedirs(OUTPUT_BASE)
        
    for item in data:
        main = item["main_category"].split(" / ")[0]
        sub = item["sub_category"].split(" / ")[0]
        dir_path = os.path.join(OUTPUT_BASE, main, sub)
        os.makedirs(dir_path, exist_ok=True)
        
        file_path = os.path.join(dir_path, f"{item['title'].split(' / ')[0]}.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(item["content"])
        print(f"✅ 已创建 / Created / 생성됨: {file_path}")

def main():
    print("=" * 50)
    print("  釜山设施数据 - 自动分类系统")
    print("  Busan Facilities Data - Auto Classification System")
    print("  부산 시설 데이터 - 자동 분류 시스템")
    print("=" * 50)
    
    rules_text = read_rules()
    print(f"📄 已读取 rules.txt / Read rules.txt / rules.txt 읽음")
    
    print("🤖 AI 正在分析... / AI is analyzing... / AI가 분석 중입니다...")
    classified_data = classify_with_ai(rules_text)
    
    if classified_data:
        create_files(classified_data)
        print("🎉 分类完成！ / Classification completed! / 분류 완료!")
    else:
        print(" 未生成任何分类数据，请检查模型返回。 / No data classified. / 분류된 데이터가 없습니다.")

if __name__ == "__main__":
    main()