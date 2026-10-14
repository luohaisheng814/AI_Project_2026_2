def detect_language(text):
    """检测文本语言"""
    if not text: return 'unknown'
    zh_count = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    ko_count = sum(1 for c in text if '\uac00' <= c <= '\ud7af')
    en_count = sum(1 for c in text if 'a' <= c.lower() <= 'z')
    
    if zh_count > ko_count and zh_count > en_count: return 'zh'
    if ko_count > zh_count and ko_count > en_count: return 'ko'
    if en_count > zh_count and en_count > ko_count: return 'en'
    return 'unknown'

def get_language_name(lang_code):
    names = {'zh': '🇨🇳 中文', 'ko': '🇰🇷 한국어', 'en': '🇺🇸 English'}
    return names.get(lang_code, '未知')