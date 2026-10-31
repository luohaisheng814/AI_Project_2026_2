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
    """
    全量常驻内存 + 作用域隔离：
      - load() 一次性把四个分类文件夹、重点档案、rules.txt、适合人群全部读入；
      - set_active_category(cat) 把所选玩法文件夹设为「当前唯一主数据源」，
        并立即从磁盘重载该文件夹（切换玩法即重算）；
      - 主回答只允许使用当前分类内的档案；其它分类仅在「个性化推荐补充」中限量出现。
    """

    def __init__(self):
        self.spots = {}
        self.by_category = {c: [] for c in config.CATEGORIES}
        self.rules_text = ""
        self.audience = {"zh": "", "ko": "", "en": ""}
        self.spot_profiles = {}     # 分类 -> docs 下重点档案（甘川 / 多大浦）
        self.active_category = None  # 当前唯一主数据源分类
        self.loaded = False

    # ---------- 单分类文件夹读取 ----------
    def _read_category_folder(self, cat):
        """读取某分类文件夹，返回该分类的 SpotDoc 列表。"""
        docs = []
        folder = os.path.join(config.ACTIVITY_DIR, cat)
        if not os.path.isdir(folder):
            return docs
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
            # 适合人群多语言文件：按后缀归档到对应语言（跨分类共享参考）
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
            docs.append(doc)
        return docs

    def load(self, force=False):
        if self.loaded and not force:
            return
        self.spots.clear()
        self.by_category = {c: [] for c in config.CATEGORIES}
        self.audience = {"zh": "", "ko": "", "en": ""}

        # ① 四大玩法分类库（全量载入，供跨类补充推荐使用）
        for cat in config.CATEGORIES:
            docs = self._read_category_folder(cat)
            self.by_category[cat] = docs
            for doc in docs:
                self.spots[doc.name] = doc

        # ② 核心数据库 rules.txt（仅作为通用规则/格式参考，不作为具体景点事实来源）
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

    # ---------- 作用域切换：选定玩法 -> 该文件夹成为唯一主数据源 ----------
    def set_active_category(self, cat):
        """切换玩法：设置当前分类并立即从磁盘重载该分类文件夹，重算主数据源。"""
        if cat == self.active_category:
            return
        self.active_category = cat
        if cat:
            self.reload_category(cat)

    def reload_category(self, cat):
        """从磁盘重新读取指定分类文件夹，刷新主数据源（不影响其它分类补充池）。"""
        if not cat:
            return
        # 先移除旧的该分类条目，避免改名/删文件后残留
        for old in list(self.by_category.get(cat, [])):
            self.spots.pop(old.name, None)
        docs = self._read_category_folder(cat)
        self.by_category[cat] = docs
        for doc in docs:
            self.spots[doc.name] = doc

    def active_docs(self):
        """当前唯一主数据源内的档案。"""
        if not self.active_category:
            return []
        return self.by_category.get(self.active_category, [])

    def _doc_by_alias(self, alias, scope=None):
        """在指定作用域内按别名找档案；scope=None 时全库查找。"""
        pool = self.active_docs() if scope == "active" else list(self.spots.values())
        for doc in pool:
            if alias in doc.aliases:
                return doc
        return None

    def find_spot(self, query, category=None):
        """
        识别问题里的景点名（主回答作用域）：
          当前分类重点档案优先 -> 当前分类档案 -> 当前分类内别名；
          若已选定分类，不在其它分类里找主景点（其它分类只进补充推荐）。
        """
        q = (query or "").lower()
        scope_cat = category or self.active_category

        prof = self.spot_profiles.get(scope_cat or "")
        if prof:
            for n in sorted(prof.aliases, key=len, reverse=True):
                if n and n.lower() in q:
                    return prof

        if scope_cat:
            names = []
            for doc in self.by_category.get(scope_cat, []):
                names.extend(doc.aliases)
            for c, doc in self.spot_profiles.items():
                if c == scope_cat:
                    names.extend(doc.aliases)
            for n in sorted(set(names), key=len, reverse=True):
                if n and n.lower() in q:
                    return self._doc_by_alias(n, scope="active")

        # 未选定分类时才允许全库兜底（保证主回答仍可命中）
        if not scope_cat:
            all_names = set().union(*[d.aliases for d in self.spots.values()] or [set()])
            for n in sorted(all_names, key=len, reverse=True):
                if len(n) >= 2 and n.lower() in q:
                    return self._doc_by_alias(n)
        return None

    def cross_category_docs(self, category, limit=2):
        """个性化推荐补充池：当前分类之外的档案，跨其它分类轮询取点、限量返回。"""
        others = [c for c in config.CATEGORIES if c != category]
        pools = {c: list(self.by_category.get(c, [])) for c in others}
        out, idx = [], 0
        # 轮询：每个其它分类轮流出一个，保证补充点来自不同玩法
        while len(out) < limit:
            progressed = False
            for c in others:
                if idx < len(pools[c]):
                    out.append(pools[c][idx])
                    progressed = True
                    if len(out) >= limit:
                        return out
            if not progressed:
                break
            idx += 1
        return out


KB = KnowledgeBase()


# ==================================================================
# 二、检索：本地库 -> 核心库 -> 官网/百科
# ==================================================================
def build_context(spot, field, category, group_type, lang):
    """
    返回 (context_text, sources, web_hits, supplements)
    主数据源 = 当前所选分类文件夹内档案；supplements = 其它分类限量补充（仅个性化推荐）。
    """
    sources, blocks = [], []

    # ① 主数据源：仅当前所选分类文件夹 / 重点档案
    if spot:
        if field and spot.get(field):
            body, head = spot.get(field), f"【{spot.name} · {field}】"
        else:
            body, head = spot.full_text(), f"【{spot.name} · 全部信息】"
        rel = os.path.relpath(spot.path, config.BASE_DIR).replace("\\", "/")
        is_profile = rel.startswith("docs/")
        blocks.append(f"=== {'重点景点档案' if is_profile else '本地分类资料库（当前玩法）'}：{rel} ===\n{head}\n{body}")
        sources.append({
            "type": "profile" if is_profile else "local",
            "label": i18n.t("source_profile") if is_profile else i18n.t("source_local"),
            "detail": rel,
        })

        # 补齐：仅限当前分类里同名景点的其它条目（档案缺的字段补上）
        for d in KB.by_category.get(category or "", []):
            if d is spot or not (d.aliases & spot.aliases or d.name == spot.name):
                continue
            miss = [d.get(f) for f in IP.FIELD_ORDER if not spot.get(f) and d.get(f)]
            if miss:
                rel2 = os.path.relpath(d.path, config.BASE_DIR).replace("\\", "/")
                blocks.append(f"=== 本地分类资料库（当前玩法·补充）：{rel2} ===\n" + "\n\n".join(miss))
                sources.append({"type": "local", "label": i18n.t("source_local"), "detail": rel2})

        others = [d.name for d in KB.by_category.get(category, []) if d.name != spot.name]
        if others:
            blocks.append("=== 当前玩法其它景点（可用于串联推荐，仅限本分类） ===\n" + "、".join(others[:12]))
    else:
        docs = KB.by_category.get(category, [])
        if docs:
            lines = [f"- {d.name}：{(d.get('overview') or d.raw)[:260].replace(chr(10), ' ')}" for d in docs[:12]]
            blocks.append(f"=== 本地分类资料库（当前玩法）：activity_classified/{category} ===\n" + "\n".join(lines))
            sources.append({"type": "local", "label": i18n.t("source_local"),
                            "detail": f"activity_classified/{category}/"})

    # 适合人群（按回答语言取对应语言版本）
    aud = KB.audience.get(lang) or KB.audience.get("zh")
    if aud:
        blocks.append("=== 适合人群参考 ===\n" + aud[:1500])

    # ② 核心数据库 rules.txt：仅作为通用规则/格式参考，不作为具体景点事实来源
    if KB.rules_text:
        blocks.append("=== 核心数据库 rules.txt（通用规则参考，景点事实以当前玩法文件夹为准） ===\n" + KB.rules_text[:6000])
        sources.append({"type": "core", "label": i18n.t("source_core"), "detail": "docs/rules.txt"})

    # ③ 其它玩法补充推荐：限量、标注所属玩法与理由，仅供个性化推荐，排在主推荐之后
    supplements = RC.build_cross_supplement(KB, category, group_type, lang, limit=RC.CROSS_LIMIT)
    if supplements:
        sup_lines = [f"- {s['name']}（{s['cat_label']}）：{s['reason']}" for s in supplements]
        blocks.append(
            "=== 其它玩法补充推荐（仅限「个性化推荐」末尾使用，排在主推荐之后，最多 "
            f"{RC.CROSS_LIMIT} 个；必须标注所属玩法与推荐理由） ===\n" + "\n".join(sup_lines)
        )

    # ④ 官网 / 百科在线查询（仅 01 / 02 重点景点，URL 来自 txt「来源网址」段）
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

    return "\n\n".join(blocks), sources, web_hits, supplements


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
        "【数据源隔离】主回答只能使用「当前玩法分类」文件夹内的资料；"
        "其它玩法的景点不得出现在主推荐、路线、交通、开放信息等主体内容里。\n"
        "【跨类补充规则】只有在末尾的「个性化推荐」环节，才允许引用资料中"
        "「其它玩法补充推荐」列出的景点：数量不得超过给定上限（默认 2 个），"
        "必须逐条标注其所属玩法分类与推荐理由，且必须排在主推荐之后，"
        "单独成段，标题为「其它玩法补充推荐」。资料未列出的跨类景点不要自行补充。\n"
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
SUPPLEMENT_TITLE = {
    "zh": "### 其它玩法补充推荐",
    "ko": "### 다른 테마 추천 (주 추천 이후)",
    "en": "### Other-theme recommendations",
}


def render_supplements(supplements, lang):
    """把跨类补充排成「主推荐之后」的独立段落；空列表返回空字符串。"""
    if not supplements:
        return ""
    lines = [SUPPLEMENT_TITLE.get(lang, SUPPLEMENT_TITLE["zh"]), ""]
    for s in supplements:
        lines.append(f"- {s['name']}（{s['cat_label']}）：{s['reason']}")
    return "\n".join(lines)


def _local_fallback(spot, field, category, group_type, lang, sources, supplements=None):
    if spot:
        body = spot.get(field) if (field and spot.get(field)) else spot.full_text()
        content = f"**{spot.name}**\n\n{IP.localize_labels(body, lang)}"
    else:
        content = i18n.t("no_result")

    # 主回答之后，单独成段给出限量跨类补充（标注玩法 + 理由）
    sup_block = render_supplements(supplements or [], lang)
    if sup_block:
        content = content + "\n\n" + sup_block

    src_lines = "\n".join(f"- {s['label']}：{s['detail']}" for s in sources)
    return (f"{content}\n\n---\n**{i18n.t('sources_label')}**\n{src_lines}"
            f"\n\n_{i18n.t('offline_mode')}_")


# ==================================================================
# 五、主入口
# ==================================================================
def answer(question, category=None, group_type=None, lang=None, username=None, ui_lang=None):
    """
    返回 dict：
        answer / sources / followups / spot / field / lang / offline / recognize / supplements
    数据源规则：选定玩法后，该分类文件夹为唯一主数据源；切换即重载；
    跨分类景点仅出现在 supplements（个性化推荐补充，限量、标注玩法与理由、排在主推荐之后）。
    """
    question = (question or "").strip()
    # 回答语言：优先提问语言（lang_detect），识别不出才用界面语言
    ui = ui_lang or i18n.I.lang or config.DEFAULT_LANG
    lang = lang or LD.resolve(question, ui)

    KB.load()

    # 未显式传分类时，先按问题推断玩法（供作用域定位）；spot 命中后以其所属分类为准
    inferred_cat = IP.infer_category(question, category)
    category = category or inferred_cat
    # 未显式传人数时按问题推断
    group_type = group_type or IP.infer_group(question)

    # 切换玩法：把所选分类文件夹设为当前唯一主数据源，并立即从磁盘重载、重算
    KB.set_active_category(category)

    spot = KB.find_spot(question, category)
    # 景点命中后，以景点真实所属分类校正作用域（关键词推断偏差时自动归位）
    if spot and spot.category and spot.category != category:
        category = spot.category
        KB.set_active_category(category)
    field, _hit = IP.detect_field_detail(question)

    # 只输入景点名 -> 输出全部（显式置为 None）
    if spot and field and IP.is_only_spot_name(question, spot.aliases):
        field = None

    recognize = IP.recognize_summary(question, spot.name if spot else None, field, lang,
                                     category, group_type)
    context, sources, _, supplements = build_context(spot, field, category, group_type, lang)

    if not sources:
        return {"answer": i18n.t("no_result"), "sources": [], "followups": [],
                "spot": None, "field": field, "lang": lang, "offline": True,
                "recognize": recognize, "supplements": []}

    def fallback():
        return {
            "answer": _local_fallback(spot, field, category, group_type, lang, sources, supplements),
            "sources": sources,
            "followups": RC.suggest_questions(spot.name if spot else "", field, lang,
                                              spot.fields if spot else None),
            "spot": spot.name if spot else None,
            "field": field, "lang": lang, "offline": True,
            "recognize": recognize,
            "supplements": supplements,
            "category": category, "group_type": group_type,
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

    # 在线模型未输出跨类补充段时，用结构化 supplements 在前端补齐（保持限量与标注规则）
    if supplements and SUPPLEMENT_TITLE.get(lang, "") not in text:
        text = text + "\n\n" + render_supplements(supplements, lang)

    return {"answer": text, "sources": sources, "followups": followups,
            "spot": spot.name if spot else None, "field": field, "lang": lang,
            "offline": False, "recognize": recognize, "supplements": supplements,
            "category": category, "group_type": group_type}


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