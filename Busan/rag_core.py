# -*- coding: utf-8 -*-

import os
import re

import config
import i18n
import core_api
import web_lookup
import intent_parser as IP
import recommend as RC
import lang_detect as LD


# ==================================================================
# 一、知识库
# ==================================================================
class SpotDoc:
    """一个景点档案：字段字典 + 别名集合。"""

    def __init__(self, name, path, category):
        self.name = name
        self.path = path
        self.category = category
        self.fields = {}       # field_key -> "【标签】\n内容"
        self.aliases = {name}
        self.raw = ""

    def get(self, field):
        return self.fields.get(field, "")

    def full_text(self, max_chars=8000):
        """只给景点名时调用：按固定顺序输出全部字段，不做截断。"""
        parts = [self.get(f) for f in IP.FIELD_ORDER if self.get(f)]
        return "\n\n".join(parts or [self.raw])[:max_chars]


class KnowledgeBase:
    """一次性加载全部 txt 常驻内存（改了 txt 调 KB.load(force=True) 热更新）。"""

    def __init__(self):
        self.spots = {}
        self.by_category = {c: [] for c in config.CATEGORIES}
        self.rules_text = ""
        self.audience = {"zh": "", "ko": "", "en": ""}
        self.spot_profiles = {}     # 分类 -> docs 下重点档案（甘川 / 多大浦）
        self.loaded = False

    def load(self, force=False):
        if self.loaded and not force:
            return
        self.spots.clear()
        self.by_category = {c: [] for c in config.CATEGORIES}

        # ① 四大玩法分类库
        for cat in config.CATEGORIES:
            folder = os.path.join(config.ACTIVITY_DIR, cat)
            if not os.path.isdir(folder):
                continue
            for fn in sorted(os.listdir(folder)):
                if not fn.lower().endswith(".txt"):
                    continue
                path = os.path.join(folder, fn)
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        text = f.read()
                except Exception:
                    continue

                base = fn[:-4]
                # 适合人群多语言文件：按后缀归档到对应语言
                if base.startswith("适合人群"):
                    lang = "zh"
                    if base.endswith(("_한국어", "_韩文", "_ko")):
                        lang = "ko"
                    elif base.endswith(("_English", "_英文", "_en")):
                        lang = "en"
                    self.audience[lang] += ("\n" if self.audience[lang] else "") + f"[{cat}]\n{text.strip()}"
                    continue

                doc = SpotDoc(base, path, cat)
                doc.raw = text
                doc.fields = IP.parse_fields(text)
                for key in ("景点名称", "韩文名", "英文名", "别名"):
                    m = re.search(rf"{key}\s*[:：]\s*(.+)", text)
                    if m:
                        for a in re.split(r"[,，/、]", m.group(1).strip()):
                            if a.strip():
                                doc.aliases.add(a.strip())
                self.spots[base] = doc
                self.by_category[cat].append(doc)

        # ② 核心数据库 rules.txt
        if os.path.exists(config.RULES_FILE):
            try:
                with open(config.RULES_FILE, "r", encoding="utf-8", errors="ignore") as f:
                    self.rules_text = f.read().strip()
            except Exception:
                self.rules_text = ""

        # ③ docs 下重点景点档案（01 甘川文化村 / 02 多大浦海水浴场）
        for cat, info in config.SPOT_PROFILES.items():
            if not os.path.exists(info["file"]):
                continue
            try:
                with open(info["file"], "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except Exception:
                continue
            m = re.search(r"景点名称\s*[:：]\s*(.+)", text)
            nm = m.group(1).strip() if m else info["names"][0]
            doc = SpotDoc(nm, info["file"], cat)
            doc.raw = text
            doc.fields = IP.parse_fields(text)
            for n in info["names"]:
                doc.aliases.add(n)
            self.spot_profiles[cat] = doc
            self.spots[doc.name] = doc

        self.loaded = True

    def _doc_by_alias(self, alias):
        for doc in self.spots.values():
            if alias in doc.aliases:
                return doc
        return None

    def find_spot(self, query, category=None):
        """识别问题里的景点名：本分类重点档案优先 → 本分类 → 全库；最长匹配优先。"""
        q = (query or "").lower()

        prof = self.spot_profiles.get(category or "")
        if prof:
            for n in sorted(prof.aliases, key=len, reverse=True):
                if n and n.lower() in q:
                    return prof

        if category:
            names = []
            for doc in self.by_category.get(category, []):
                names.extend(doc.aliases)
            for c, doc in self.spot_profiles.items():
                if c == category:
                    names.extend(doc.aliases)
            for n in sorted(set(names), key=len, reverse=True):
                if n and n.lower() in q:
                    return self._doc_by_alias(n)

        all_names = set().union(*[d.aliases for d in self.spots.values()] or [set()])
        for n in sorted(all_names, key=len, reverse=True):
            if len(n) >= 2 and n.lower() in q:
                return self._doc_by_alias(n)
        return None


KB = KnowledgeBase()


# ==================================================================
# 二、检索：本地库 -> 核心库 -> 官网/百科
# ==================================================================
def build_context(spot, field, category, group_type, lang):
    """返回 (context_text, sources, web_hits)"""
    sources, blocks = [], []

    # ① 本地分类资料库 / 重点景点档案
    if spot:
        if field and spot.get(field):
            body, head = spot.get(field), f"【{spot.name} · {field}】"
        else:
            body, head = spot.full_text(), f"【{spot.name} · 全部信息】"
        rel = os.path.relpath(spot.path, config.BASE_DIR).replace("\\", "/")
        is_profile = rel.startswith("docs/")
        blocks.append(f"=== {'重点景点档案' if is_profile else '本地分类资料库'}：{rel} ===\n{head}\n{body}")
        sources.append({
            "type": "profile" if is_profile else "local",
            "label": i18n.t("source_profile") if is_profile else i18n.t("source_local"),
            "detail": rel,
        })

        # 补齐：同分类里同名景点的其它条目（档案缺的字段补上）
        for d in KB.by_category.get(category or "", []):
            if d is spot or not (d.aliases & spot.aliases or d.name == spot.name):
                continue
            miss = [d.get(f) for f in IP.FIELD_ORDER if not spot.get(f) and d.get(f)]
            if miss:
                rel2 = os.path.relpath(d.path, config.BASE_DIR).replace("\\", "/")
                blocks.append(f"=== 本地分类资料库（补充）：{rel2} ===\n" + "\n\n".join(miss))
                sources.append({"type": "local", "label": i18n.t("source_local"), "detail": rel2})

        others = [d.name for d in KB.by_category.get(category, []) if d.name != spot.name]
        if others:
            blocks.append("=== 同分类其它景点（可用于串联推荐） ===\n" + "、".join(others[:12]))
    else:
        docs = KB.by_category.get(category, [])
        if docs:
            lines = [f"- {d.name}：{(d.get('overview') or d.raw)[:260].replace(chr(10), ' ')}" for d in docs[:12]]
            blocks.append(f"=== 本地分类资料库：activity_classified/{category} ===\n" + "\n".join(lines))
            sources.append({"type": "local", "label": i18n.t("source_local"),
                            "detail": f"activity_classified/{category}/"})

    # 适合人群（按回答语言取对应语言版本）
    aud = KB.audience.get(lang) or KB.audience.get("zh")
    if aud:
        blocks.append("=== 适合人群参考 ===\n" + aud[:1500])

    # ② 核心数据库 rules.txt
    if KB.rules_text:
        blocks.append("=== 核心数据库 rules.txt ===\n" + KB.rules_text[:6000])
        sources.append({"type": "core", "label": i18n.t("source_core"), "detail": "docs/rules.txt"})

    # ③ 官网 / 百科在线查询（仅 01 / 02 重点景点，URL 来自 txt「来源网址」段）
    web_hits = []
    profile = KB.spot_profiles.get(category or "")
    if profile and config.ENABLE_WEB_LOOKUP:
        urls = web_lookup.extract_urls(profile.get("source") or profile.raw)
        if spot and spot is not profile:
            urls += web_lookup.extract_urls(spot.get("source") or spot.raw)
        urls = list(dict.fromkeys(urls))
        if urls:
            kw = [spot.name if spot else profile.name]
            if field:
                kw.append(IP.FIELD_LABEL.get(field, {}).get("zh", field))
            web_hits = web_lookup.lookup(urls, keywords=kw, max_pages=3)
            for h in web_hits:
                blocks.append(f"=== 官网/百科在线查询：{h['url']} ===\n{h['snippet'][:2000]}")
                sources.append({"type": "web", "label": i18n.t("source_web"), "detail": h["url"]})
            if not web_hits:
                sources.append({"type": "web", "label": i18n.t("source_web"),
                                "detail": i18n.t("web_failed")})

    return "\n\n".join(blocks), sources, web_hits


# ==================================================================
# 三、Prompt
# ==================================================================
def _system_prompt(lang):
    target = i18n.LLM_LANG_NAME.get(lang, "简体中文")
    return (
        f"你是「釜山 AI 旅行助手」，一位熟悉釜山本地玩法的资深向导。\n"
        f"【语言铁律】必须且只能使用 {target} 输出全部内容：标题、正文、来源说明、预测问题。"
        f"原始资料以中文为主，请自行准确翻译为 {target} 后再回答。\n"
        "【准确性铁律】只能依据<检索到的资料>回答，资料里没有的不要编造；"
        "资料不足时先说明已知信息，再明确告知哪部分需以官方现场公告为准。\n"
        "【个性化】严格按<用户画像>里的玩法骨架与出行策略组织答案，做到因人而异、可照着走。\n"
        "【完整性】用户只给景点名时，必须完整列出介绍、交通、开放信息、来源网址等全部字段，不得只显示前几行。"
        "用户指定了字段时，只聚焦该字段，不堆砌无关内容。\n"
        "【格式】Markdown：小标题 + 短段落 + 要点列表；时间、票价、站点名等关键信息加粗。\n"
        "【结尾】必须包含两部分：\n"
        "1) 资料来源：逐条列出本次实际用到的资料（本地文件路径 / 核心数据库 / 官网或百科链接）；\n"
        "2) 3 个预测用户还会问的后续问题。\n"
        "分隔规则：正文与来源写完后另起一行输出 ###FOLLOWUP###，"
        "随后三行各写一个预测问题（每行一个，不要编号、不要加 - 号以外的内容）。"
    )


def _user_prompt(question, context, category, group_type, field, spot_name, lang):
    cat_name = i18n.I.cat_name(category) if category else "-"
    grp_name = i18n.I.group_name(group_type) if group_type else "-"
    profile_text = RC.build_profile_text(category, group_type, lang)

    if field:
        fname = IP.FIELD_LABEL.get(field, {}).get(lang, field)
        focus = {
            "zh": f"\n【本次聚焦字段】{fname}。只重点回答这一项，不要展开无关内容；不足时说明需查官方公告。",
            "ko": f"\n【집중 필드】{fname}. 이 항목만 중점적으로 답변하고 무관한 내용은 늘어놓지 마세요.",
            "en": f"\n[Focus field] {fname}. Answer only this field; do not pad with unrelated content.",
        }[lang]
    else:
        focus = {
            "zh": "\n【本次聚焦字段】用户只给了景点名称，请完整列出介绍、交通、开放信息、来源网址等全部资料，不要省略。",
            "ko": "\n【집중 필드】사용자가 장소 이름만 입력했습니다. 소개·교통·개방정보·출처 등 모든 자료를 빠짐없이 정리하세요.",
            "en": "\n[Focus field] Only the spot name was given. List ALL details (overview, transportation, "
                  "opening hours, sources) without omitting anything.",
        }[lang]

    return (
        f"<用户画像>\n玩法分类：{cat_name}\n出行人数：{grp_name}\n"
        f"识别到的景点：{spot_name or '（未明确）'}\n"
        f"推荐与呈现要求：{profile_text}\n\n"
        f"<检索到的资料>\n{context}\n\n"
        f"<用户问题>\n{question}\n"
        f"{focus}"
    )


# ==================================================================
# 四、离线兜底（未配置 LLM_API_KEY 时仍可完整演示检索链路）
# ==================================================================
def _local_fallback(spot, field, category, group_type, lang, sources):
    if spot:
        body = spot.get(field) if (field and spot.get(field)) else spot.full_text()
        content = f"**{spot.name}**\n\n{IP.localize_labels(body, lang)}"
    else:
        content = i18n.t("no_result")

    src_lines = "\n".join(f"- {s['label']}：{s['detail']}" for s in sources)
    return (f"{content}\n\n---\n**{i18n.t('sources_label')}**\n{src_lines}"
            f"\n\n_{i18n.t('offline_mode')}_")


# ==================================================================
# 五、主入口
# ==================================================================
def answer(question, category=None, group_type=None, lang=None, username=None, ui_lang=None):
    """
    返回 dict：
        answer / sources / followups / spot / field / lang / offline
    """
    question = (question or "").strip()
    # 回答语言：优先提问语言（lang_detect），识别不出才用界面语言
    ui = ui_lang or i18n.I.lang or config.DEFAULT_LANG
    lang = lang or LD.resolve(question, ui)

    KB.load()

    spot = KB.find_spot(question, category)
    field, _hit = IP.detect_field_detail(question)

    # 只输入景点名 -> 输出全部（显式置为 None）
    if spot and field and IP.is_only_spot_name(question, spot.aliases):
        field = None

    context, sources, _ = build_context(spot, field, category, group_type, lang)

    if not sources:
        return {"answer": i18n.t("no_result"), "sources": [], "followups": [],
                "spot": None, "field": field, "lang": lang, "offline": True}

    def fallback():
        return {
            "answer": _local_fallback(spot, field, category, group_type, lang, sources),
            "sources": sources,
            "followups": RC.suggest_questions(spot.name if spot else "", field, lang,
                                              spot.fields if spot else None),
            "spot": spot.name if spot else None,
            "field": field, "lang": lang, "offline": True,
        }

    if not core_api.is_configured():
        return fallback()

    raw = core_api.chat([
        {"role": "system", "content": _system_prompt(lang)},
        {"role": "user", "content": _user_prompt(question, context, category, group_type,
                                                 field, spot.name if spot else None, lang)},
    ])
    if raw is None:
        return fallback()

    followups, text = [], raw
    if "###FOLLOWUP###" in raw:
        main, tail = raw.split("###FOLLOWUP###", 1)
        text = main.strip()
        for line in tail.strip().splitlines():
            line = line.strip().lstrip("-").strip()
            if line:
                followups.append(line)
            if len(followups) == 3:
                break

    if not followups:
        followups = RC.suggest_questions(spot.name if spot else "", field, lang,
                                         spot.fields if spot else None)

    return {"answer": text, "sources": sources, "followups": followups,
            "spot": spot.name if spot else None, "field": field, "lang": lang, "offline": False}


if __name__ == "__main__":
    KB.load()
    print("已加载景点：", list(KB.spots.keys()))
    print("重点档案：", {c: d.name for c, d in KB.spot_profiles.items()})
    print("rules 长度：", len(KB.rules_text), "\n")
    for q, cat, grp in [
        ("甘川文化村", "01_艺术村落_文化街区", "two_mf"),
        ("甘川文化村 交通", "01_艺术村落_文化街区", "solo_female"),
        ("감천문화마을 개방시간", "01_艺术村落_文化街区", "solo_male"),
        ("多大浦海水浴场 开放时间", "02_海岸休闲_日落夜景", "group_3plus"),
        ("How do I get to Gamcheon Culture Village?", "01_艺术村落_文化街区", "two_ff"),
    ]:
        r = answer(q, category=cat, group_type=grp)
        print("=" * 66)
        print("Q:", q)
        print(f"  spot={r['spot']}  field={r['field']}  lang={r['lang']}  offline={r['offline']}")
        print("  A:", (r["answer"] or "")[:180].replace("\n", " "))
        print("  SRC:", [s["detail"] for s in r["sources"]])
        print("  NEXT:", r["followups"])