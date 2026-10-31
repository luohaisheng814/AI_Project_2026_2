# -*- coding: utf-8 -*-
"""
本轮语言策略回归测试（离线口径，未配置 LLM_API_KEY）：
1. 输出语言只由按钮 ui_lang 决定，与提问语言、数据来源无关；
2. 后端先按中文数据库检索/组织；按钮为中文跳过翻译，非中文在线时整体翻译（离线时保留中文草稿并标注）；
3. 提问语言与按钮不一致时仍以按钮语言作答；
4. 来源标签、补充推荐分类名/理由按按钮语言本地化；补充数量受限、顺序稳定；
5. 翻译辅助函数：中文直通；非中文在未配置 LLM 时安全返回 None 由上层降级。
"""
import rag_core
import i18n

rag_core.KB.load()

# (提问, 提问语言, 按钮语言, 分类, 人数)
cases = [
    ("감천문화마을 소개", "ko", "zh", "01_艺术村落_文化街区", "two_mf"),  # 韩文提问 + 中文按钮 -> 中文答
    ("甘川文化村 介绍", "zh", "ko", "01_艺术村落_文化街区", "two_mf"),   # 中文提问 + 韩文按钮 -> 韩文界面标签
    ("How do I get to Gamcheon Culture Village?", "en", "en", "01_艺术村落_文化街区", "solo_male"),
    ("다대포해수욕장 개방시간", "ko", "en", "02_海岸休闲_日落夜景", "group_3plus"),  # 韩文提问 + 英文按钮
]

failures = []
prev_supp = {}

for q, qlang, btn, cat, grp in cases:
    r = rag_core.answer(q, category=cat, group_type=grp, ui_lang=btn)
    print("=" * 72)
    print(f"Q={q!r}  提问语言={qlang}  按钮={btn}")
    print("  输出语言 lang =", r["lang"], " recognize =", r["recognize"])
    print("  sources =", [(s["type"], s["label"]) for s in r["sources"]])
    print("  supplements =", [(s["name"], s["cat_label"]) for s in r["supplements"]])

    # ① 输出语言必须等于按钮语言，不跟随提问语言
    if r["lang"] != btn:
        failures.append(f"[{btn}] 输出语言 {r['lang']} != 按钮语言 {btn}")

    # ② 提问语言与按钮不一致时，状态栏应记录“提问=xxx”
    if qlang != btn and f"提问=" not in r["recognize"]:
        failures.append(f"[{btn}] 未在状态栏标注提问语言 {qlang}")

    # ③ 来源标签按按钮语言本地化
    labels = [s["label"] for s in r["sources"]]
    if btn == "ko":
        if not any("자료" in x or "분류" in x or "핵심" in x for x in labels):
            failures.append("[ko] 来源标签未本地化")
    elif btn == "en":
        if not any("Local" in x or "Profile" in x or "Core" in x or "online" in x.lower() for x in labels):
            failures.append("[en] 来源标签未本地化")

    # ④ 补充推荐：数量 <= 2，分类名/理由为按钮语言
    sups = r["supplements"]
    if len(sups) > 2:
        failures.append(f"补充推荐数量 {len(sups)} 超过上限 2")
    for s in sups:
        label = s["cat_label"]
        if btn == "ko" and not any(k in label for k in ("·", "예술", "해안", "습지", "어항")):
            failures.append(f"[ko] 补充分类名未本地化: {label}")
        if btn == "en" and not any(k in label for k in ("·", "Art", "Coastal", "Wetland", "Hidden")):
            failures.append(f"[en] 补充分类名未本地化: {label}")

    # ⑤ 离线非中文应标注“离线无法在线翻译”；中文不出现该提示
    offline_note = i18n.STRINGS["offline_no_translate"][btn]
    if btn != "zh":
        if offline_note not in r["answer"]:
            failures.append(f"[{btn}] 离线非中文缺少不可翻译标注")
    else:
        if offline_note in r["answer"]:
            failures.append("[zh] 中文模式不应出现离线翻译标注")

    # ⑥ 同一分类下补充顺序跨语言保持一致（不随语言改变推荐顺序）
    order = [s["name"] for s in sups]
    if cat in prev_supp and order != prev_supp[cat]:
        failures.append(f"[{cat}] 补充推荐顺序发生变化: {prev_supp[cat]} -> {order}")
    prev_supp[cat] = order

# ⑦ 翻译辅助函数：中文直通；离线非中文返回 None（上层降级保留中文草稿）
draft = "**甘川文化村**\n交通：地铁 1 号线..."
if rag_core._translate_to(draft, "zh") != draft:
    failures.append("中文模式应跳过翻译、原样返回草稿")
if rag_core._translate_to(draft, "ko") is not None:
    failures.append("离线未配置 LLM 时韩文翻译应返回 None 以便降级")

print("\n" + "=" * 72)
if failures:
    print("FAILED:")
    for f in failures:
        print("  -", f)
    raise SystemExit(1)
print("ALL LANG-POLICY CHECKS PASSED")
