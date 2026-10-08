"""
语言检测程序 / Language Detection Program / 언어 감지 프로그램
功能：根据用户输入自动识别中文、韩文或英文，并给出对应语言的回复。
"""

import re

def detect_language(text):
    """
    检测输入文本的主要语言 / Detect the main language of input text / 입력 텍스트의 주요 언어 감지
    
    Args:
        text (str): 用户输入的文本 / User input text / 사용자 입력 텍스트
    
    Returns:
        str: 语言代码 'zh'(中文) / 'ko'(韩文) / 'en'(英文) / 'unknown'(未知)
    """
    if not text or not text.strip():
        return 'unknown'
    
    # 统计各语言字符数量 / Count characters by language / 언어별 문자 수 계산
    chinese_count = 0   # 中文 / Chinese / 중국어
    korean_count = 0    # 韩文 / Korean / 한국어
    english_count = 0   # 英文 / English / 영어
    
    for char in text:
        # 检查中文（CJK统一汉字） / Check Chinese (CJK Unified Ideographs)
        if '\u4e00' <= char <= '\u9fff' or '\u3400' <= char <= '\u4dbf':
            chinese_count += 1
        # 检查韩文（韩文字母 + 兼容字母） / Check Korean (Hangul Syllables + Jamo)
        elif '\uac00' <= char <= '\ud7af' or '\u1100' <= char <= '\u11ff' or '\u3130' <= char <= '\u318f':
            korean_count += 1
        # 检查英文（ASCII字母） / Check English (ASCII letters)
        elif ('a' <= char <= 'z') or ('A' <= char <= 'Z'):
            english_count += 1
    
    # 返回占比最高的语言 / Return language with highest count / 가장 많은 비중을 차지하는 언어 반환
    max_count = max(chinese_count, korean_count, english_count)
    
    if max_count == 0:
        return 'unknown'
    elif max_count == chinese_count:
        return 'zh'
    elif max_count == korean_count:
        return 'ko'
    else:
        return 'en'


def get_response(lang_code, original_text):
    """
    根据检测到的语言返回对应语言的回复 / Return response in detected language / 감지된 언어로 응답 반환
    
    Args:
        lang_code (str): 语言代码 / Language code / 언어 코드
        original_text (str): 原始输入文本 / Original input text / 원본 입력 텍스트
    
    Returns:
        str: 对应语言的回复 / Response in target language / 대상 언어로 된 응답
    """
    if lang_code == 'zh':
        return f"✅ 检测到中文 / Detected Chinese / 중국어 감지됨\n您输入的是：{original_text}\n你好！这是中文回复。欢迎使用釜山文旅智能问答系统！"
    
    elif lang_code == 'ko':
        return f"✅ 한국어 감지됨 / Korean detected / 检测到韩文\n입력한 내용: {original_text}\n안녕하세요! 이것은 한국어 응답입니다. 부산 문화관광 지능형 질의응답 시스템을 이용해 주셔서 감사합니다!"
    
    elif lang_code == 'en':
        return f"✅ English detected / 检测到英文 / 영어 감지됨\nYou entered: {original_text}\nHello! This is an English response. Welcome to the Busan Culture & Tourism Intelligent QA System!"
    
    else:
        return "❌ 无法识别语言 / Unable to detect language / 언어를 감지할 수 없습니다. 请输入中文、韩文或英文。"


def main():
    """主函数 / Main function / 메인 함수"""
    print("=" * 60)
    print("  🌏 中韩英语言检测程序")
    print("  🌏 Chinese / Korean / English Language Detector")
    print("  🌏 중·한·영 언어 감지 프로그램")
    print("=" * 60)
    print()
    print("📝 使用说明 / Instructions / 사용 방법:")
    print("  - 输入中文 → 显示中文回复")
    print("  - 输入韩文 → 显示韩文回复")
    print("  - 输入英文 → 显示英文回复")
    print("  - 输入 'exit' 退出程序")
    print()
    
    while True:
        user_input = input("\n💬 请输入文本 / Enter text / 텍스트를 입력하세요: ").strip()
        
        if not user_input:
            print("⚠️  输入为空，请重新输入。 / Empty input. / 빈 입력입니다.")
            continue
        
        if user_input.lower() == 'exit':
            print("\n👋 再见！ / Goodbye! / 안녕히 가세요!")
            break
        
        # 检测语言 / Detect language / 언어 감지
        lang = detect_language(user_input)
        
        # 获取并输出回复 / Get and print response / 응답 가져와서 출력
        response = get_response(lang, user_input)
        print("\n" + "-" * 50)
        print(response)
        print("-" * 50)


if __name__ == "__main__":
    main()