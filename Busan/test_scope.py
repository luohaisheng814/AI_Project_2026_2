# -*- coding: utf-8 -*-
"""本轮改动离线冒烟测试：作用域数据源 / 跨类限量补充 / 推断联动。"""
import rag_core
import intent_parser as IP

rag_core.KB.load()

cases = [
    ("甘川文化村 介绍", "01_艺术村落_文化街区", "two_mf"),
    ("多大浦海水浴场 开放时间", "02_海岸休闲_日落夜景", "group_3plus"),
    ("乙淑岛候鸟公园 怎么去", "03_湿地生态_自然观景", "solo_female"),
    ("长林浦口 拍照", "04_小众渔港_文艺拍照", "two_ff"),
]

for q, cat, grp in cases:
    r = rag_core.answer(q, category=cat, group_type=grp)
    print("=" * 70)
    print("Q:", q)
    print("  recognize:", r["recognize"])
    print("  resolved category:", r.get("category"), " group:", r.get("group_type"))
    print("  spot:", r["spot"], " field:", r["field"], " offline:", r["offline"])
    print("  supplements:", [(s["name"], s["cat_label"]) for s in r.get("supplements", [])])
    print("  sources:", [s["detail"] for s in r["sources"]])
    # 校验：主回答来源里不应出现其它分类文件夹
    other = [c for c in rag_core.config.CATEGORIES if c != r.get("category")]
    leaked = [s["detail"] for s in r["sources"] if any(o in s["detail"] for o in other)]
    print("  cross-category leak in main sources:", leaked)

# 推断联动检查
print("\n--- inference ---")
for q in ["情侣去海边看日落", "一个男生独自拍照", "闺蜜两人逛文创小巷", "一家三口看候鸟"]:
    print(f"  {q} -> cat={IP.infer_category(q)} group={IP.infer_group(q)}")
