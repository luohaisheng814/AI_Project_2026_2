import os
import json
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# 1. app.py 옆의 .env를 읽는다. · 读取app.py旁的.env。
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

api_key = os.getenv("DASHSCOPE_API_KEY")
base_url = os.getenv("DASHSCOPE_BASE_URL")
if not api_key or not base_url:
    raise ValueError("API Key와 Base URL을 확인하세요 / 请检查API Key和Base URL：week05_recommendation/.env")

client = OpenAI(api_key=api_key, base_url=base_url)

# 2. 첫 실행은 사용자 A. 비교할 때 이 부분만 바꾼다. · 首次使用用户A，比较时只修改这里。
profile_name = "B"
profile = {
    "interests": ["Statistics"],
    "level": "intermediate",
    "available_minutes": 90
}

# 3. 두 사용자에게 같은 후보를 사용한다. · 两位用户使用相同候选项。
candidates = [
    {"id": "C1", "title": "AI API 입문 / AI API入门", "minutes": 10, "level": "beginner", "tags": ["AI"]},
    {"id": "C2", "title": "고급 모델 학습 / 高级模型训练", "minutes": 90, "level": "advanced", "tags": ["AI"]},
    {"id": "C3", "title": "VR 인터랙션 입문 / VR交互入门", "minutes": 25, "level": "beginner", "tags": ["VR"]},
    {"id": "C4", "title": "통계 강의 / 统计课程", "minutes": 60, "level": "intermediate", "tags": ["Statistics"]}
]

# 4. 선택 조건과 출력 형식을 전달한다. · 提供筛选条件与输出格式。
prompt = f"""
请根据用户资料，从候选课程中按推荐顺序选择最多两门课程。
只能使用候选列表中的ID，不得编造课程或重复ID。
每门推荐课程必须同时满足以下三个条件：
1. 至少一个tags标签与用户的interests兴趣匹配。
2. 课程level必须与用户level完全相同。
3. 课程minutes不得超过用户的available_minutes。
available_minutes是每门课程的时长上限，不是所有推荐课程的总时长。
beginner表示初级，intermediate表示中级，advanced表示高级。
Statistics表示统计学。用韩语和中文解释时，请使用对应语言的名称。

请返回两个列表：
- recommendations：推荐课程，最多两门，每项包含id、reason_ko和reason_zh。
  说明兴趣、水平和时长为什么都符合条件。
- excluded：所有未推荐的候选课程，每项包含id、reason_ko和reason_zh。
  列出该课程不满足的所有条件，并引用实际资料。
  如果课程满足全部条件，但因最多推荐两门而未被选中，应明确说明数量限制，
  不得编造不满足条件的理由。
每个候选ID必须在这两个列表中的一个列表里出现恰好一次。
如果没有课程满足全部条件，recommendations必须为空，
所有候选课程及其排除理由仍须出现在excluded中。
每项的reason_ko必须用韩语，reason_zh必须用简体中文。
两种语言的理由必须表达相同的事实、条件和数值。
所有理由仅依据用户资料和候选信息，不要加入额外事实。
只返回JSON对象，不要添加Markdown或其他文字。
输出结构如下（具体ID和理由必须根据实际输入填写）：
{{"recommendations": [{{"id": "C1", "reason_ko": "한국어 추천 이유", "reason_zh": "中文推荐理由"}}],
  "excluded": [{{"id": "C2", "reason_ko": "한국어 제외 이유", "reason_zh": "中文排除理由"}}]}}

用户资料：{json.dumps(profile, ensure_ascii=False)}
候选课程：{json.dumps(candidates, ensure_ascii=False)}
"""

# 5. Qwen에 요청하고 JSON 응답을 읽는다. · 请求Qwen并读取JSON回复。
response = client.chat.completions.create(
    model="qwen3.8-flash",
    messages=[{"role": "user", "content": prompt}],
    response_format={"type": "json_object"},
    extra_body={"enable_thinking": False}
)
result = json.loads(response.choices[0].message.content)

# 6. 화면에 출력하고 사용자별 파일로 저장한다. · 显示结果并按用户保存。
print(f"=== 사용자 {profile_name} 추천·제외 결과 / 用户 {profile_name} 的推荐与排除结果 ===")
print(json.dumps(result, ensure_ascii=False, indent=2))

output_path = BASE_DIR / f"result_{profile_name}.json"
record = {"profile": profile, "result": result}
output_path.write_text(
    json.dumps(record, ensure_ascii=False, indent=2),
    encoding="utf-8"
)
print(f"저장 완료 / 保存完成: {output_path.name}")