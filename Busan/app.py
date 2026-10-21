# -*- coding: utf-8 -*-


import config
import i18n
import rag_core
import lang_detect as LD

config.ensure_runtime()


def pick(options, title):
    """通用选择菜单：既接受序号，也接受直接输入选项文字。"""
    print("\n" + title)
    for i, (label, _) in enumerate(options, 1):
        print(f"  {i}) {label}")
    while True:
        s = input(">>> ").strip()
        if s.isdigit() and 1 <= int(s) <= len(options):
            return options[int(s) - 1][1]
        for label, val in options:
            if s == label:
                return val
        print("  (请输入序号)")


def choose_language():
    return pick([(i18n.LANGUAGES[k], k) for k in config.SUPPORTED_LANGS], i18n.t("cli_lang_menu"))


def choose_category():
    return pick([(i18n.I.cat_name(c), c) for c in config.CATEGORIES], i18n.t("nav_play"))


def choose_group():
    return pick([(i18n.I.group_name(g), g) for g in config.GROUP_TYPES], i18n.t("nav_people"))


def show(result):
    print("\n" + "-" * 72)
    print(result.get("answer", "").strip())

    sources = result.get("sources") or []
    if sources:
        print("\n📚 " + i18n.t("sources_label"))
        for s in sources:
            print(f"   - {s.get('label','')}：{s.get('detail','')}")

    followups = result.get("followups") or []
    if followups:
        print("\n💡 " + i18n.t("suggest_label"))
        for q in followups:
            print("   - " + q)

    if result.get("offline"):
        print("\n" + i18n.t("offline_mode"))
    print("-" * 72)


def main():
    i18n.I.set_lang(choose_language())
    print("\n" + i18n.t("cli_title"))
    print(i18n.t("cli_switch"))

    category = choose_category()
    group = choose_group()
    print(f"\n{i18n.t('current_selection')}：{i18n.I.cat_name(category)} / {i18n.I.group_name(group)}")

    while True:
        q = input("\n" + i18n.t("cli_ask") + " >>> ").strip()
        if not q:
            continue
        low = q.lower()
        if low in ("/quit", "/exit", "quit", "exit"):
            print(i18n.t("cli_bye"))
            break
        if low == "/lang":
            i18n.I.set_lang(choose_language())
            print(f"🌐 {i18n.I.current_name}")
            continue
        if low == "/cat":
            category = choose_category()
            continue
        if low == "/grp":
            group = choose_group()
            continue

        print(i18n.t("searching"), f"[回答语言：{LD.detect_name(LD.resolve(q, i18n.I.lang))}]")
        result = rag_core.answer(q, category=category, group_type=group,
                                 lang=None, ui_lang=i18n.I.lang, username="cli_tester")
        show(result)


if __name__ == "__main__":
    main()