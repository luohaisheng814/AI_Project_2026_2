# -*- coding: utf-8 -*-

import os
import re

import config
import i18n
import core_api
import web_lookup
import official_sites
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

        # 重点档案里的韩 / 英别名合并到同名分类档案，保证补充推荐也能取到惯用译名
        for prof in self.spot_profiles.values():
            for doc in self.by_category.get(prof.category, []):
                if doc.name == prof.name or doc.aliases & prof.aliases:
                    doc.aliases |= prof.aliases

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
        # 重载后再次合并重点档案别名（韩 / 英惯用名不丢失）
        prof = self.spot_profiles.get(cat)
        if prof:
            for doc in docs:
                if doc.name == prof.name or doc.aliases & prof.aliases:
                    doc.aliases |= prof.aliases

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

    def find_spot_global(self, query):
        """忽略当前玩法作用域，在全部已加载档案里按别名找景点（用于语言识别/翻译兜底）。"""
        q = (query or "").lower()
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
def build_context(spot, field, category, group_type, lang, online=True):
    """
    返回 (context_text, sources, web_hits, supplements)
    主数据源 = 当前所选分类文件夹内档案；supplements = 其它分类限量补充（仅个性化推荐）。
    online=True（登录后的联网模式）才会访问景点官方网站；未登录时纯本地库。
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

    # ④ 景点官方网站查询（登录后的联网模式；8 个景点全覆盖，不止 01/02 重点档案）
    web_hits = []
    profile = KB.spot_profiles.get(category or "")
    if online and config.ENABLE_WEB_LOOKUP:
        kw = []
        focus_name = spot.name if spot else (profile.name if profile else None)
        if focus_name:
            kw.append(focus_name)
        if field:
            kw.append(IP.FIELD_LABEL.get(field, {}).get("zh", field))
        kw = [k for k in kw if k]

        # ① 官网登记表（official_sites：沙下区文化观光 / 甘川文化村官网等实测可达站点）
        if spot:
            for h in official_sites.fetch(spot.name, extra_keywords=kw[1:], max_pages=2):
                web_hits.append(h)
                blocks.append(
                    f"=== 官方网站在线查询（{h.get('portal')}｜抓取于 {h.get('fetched_at')}）：{h['url']} ===\n"
                    f"{h.get('snippet', '')[:2000]}"
                )
                sources.append({"type": "official", "label": h.get("portal") or i18n.t("source_official"),
                                "detail": h["url"]})
            note = (official_sites.entries(spot.name) or {}).get("note")
            if note and not any(s["type"] == "official" for s in sources):
                sources.append({"type": "official", "label": i18n.t("source_official"), "detail": note})

        # ② 档案「来源网址」段登记的补充链接（重点档案 / 分类 txt 里写明的网址）
        urls = []
        if spot:
            urls += web_lookup.extract_urls(spot.get("source") or spot.raw)
        if profile:
            urls += web_lookup.extract_urls(profile.get("source") or profile.raw)
        urls = [u for u in dict.fromkeys(urls) if not any(u == h["url"] for h in web_hits)]
        if urls:
            for h in web_lookup.lookup(urls, keywords=kw, max_pages=2):
                web_hits.append(h)
                blocks.append(f"=== 官网/百科在线查询：{h['url']} ===\n{h['snippet'][:2000]}")
                sources.append({"type": "web", "label": i18n.t("source_web"), "detail": h["url"]})

        if not web_hits:
            sources.append({"type": "web", "label": i18n.t("source_web"),
                            "detail": i18n.t("web_failed")})

    return "\n\n".join(blocks), sources, web_hits, supplements


# ==================================================================
# 三、Prompt（先中文检索、中文生成草稿，再按按钮语言整体翻译）
# ==================================================================
LANG_NAMES = {"zh": "简体中文", "ko": "한국어 (Korean)", "en": "English"}


def _normalize_lang(lang):
    return lang if lang in ("zh", "ko", "en") else "zh"


def _draft_system_prompt(concise=False):
    """草稿阶段系统提示：始终用简体中文基于中文数据库生成回答。

    concise=True：用户只输入景点名时走精简版，只给 4 行结论，不罗列全部字段。
    """
    base = (
        "你是「釜山 AI 旅行助手」，一位熟悉釜山本地玩法的资深向导。\n"
        "【语言铁律】用户问题可能是简体中文、韩文或英文：先准确理解其意图、景点与字段，"
        "但本轮草稿必须使用简体中文生成：标题、正文、来源说明、预测问题一律用中文。\n"
        "【准确性铁律】只能依据<检索到的资料>回答，资料里没有的不要编造；"
        "资料不足时先说明已知信息，再明确告知哪部分需以官方现场公告为准。\n"
        "【数据源隔离】主回答只能使用「当前玩法分类」文件夹内的资料；"
        "其它玩法的景点不得出现在主推荐、路线、交通、开放信息等主体内容里。\n"
        "【跨类补充规则】跨类景点已由系统在末尾统一补齐，你不要在正文中自行补充其它玩法景点。\n"
        "【个性化】严格按<用户画像>里的玩法骨架与出行策略组织答案，做到因人而异、可照着走。\n"
        "【官网优先】资料中出现「官方网站在线查询」段落时，地址、电话、开放时间、票价、官网链接等"
        "事实性信息以官网段落为准；本地库与官网不一致时，以官网为准并一句话说明差异；"
        "引用官网时标注是哪个站点（如「沙下区文化观光官网」），不要虚构官网未给出的数字。\n"
    )
    if concise:
        base += (
            "【精简回答】用户只输入了景点名称，本次必须给一份「一眼看完」的短答：\n"
            "1) 第一行：**景点名**——一句话定位（不超过 40 字）；\n"
            "2) 第二段：2-3 个「最值得」的亮点，每条不超过 20 字；\n"
            "3) 第三段：交通一句话（地铁/公交主线即可）+ 门票与开放时间一句话（官网有则用官网口径）；\n"
            "4) 最后一行：提示可继续追问（交通细节 / 门票 / 开放时间 / 周边 / 适合人群）。\n"
            "全文控制在 200 字以内，禁止罗列全部字段、禁止成段抄写资料原文、禁止贴多条周边与美食清单；"
            "官方网站在资料中存在时，末尾可带 1 个官网链接。\n"
        )
    else:
        base += (
            "【完整性】用户指定了字段（如交通、门票、开放信息）时，只聚焦该字段并给足细节，不堆砌无关内容；"
            "用户问的是自由问题（非单一字段）时，按问题本身组织答案，不必罗列全部字段。\n"
        )
    base += (
        "【格式】Markdown：小标题 + 短段落 + 要点列表；时间、票价、站点名等关键信息加粗。\n"
        "【结尾】必须包含两部分：\n"
        "1) 资料来源：逐条列出本次实际用到的资料（本地文件路径 / 核心数据库 / 官网或百科链接）；\n"
        "2) 3 个预测用户还会问的后续问题。\n"
        "分隔规则：正文与来源写完后另起一行输出 ###FOLLOWUP###，"
        "随后三行各写一个预测问题（每行一个，不要编号、不要加 - 号以外的内容）。"
    )
    return base


def _draft_user_prompt(question, context, category, group_type, field, spot_name, concise=False):
    cat_name = i18n.I.cat_name(category) if category else "-"
    grp_name = i18n.I.group_name(group_type) if group_type else "-"
    profile_text = RC.build_profile_text(category, group_type, "zh")

    if field:
        fname = IP.FIELD_LABEL.get(field, {}).get("zh", field)
        focus = f"\n【本次聚焦字段】{fname}。只重点回答这一项，不要展开无关内容；不足时说明需查官方公告。"
    elif concise:
        focus = ("\n【本次回答形态】用户只输入了景点名称：按「一句话定位 + 2-3 个亮点 + 交通与门票各一句"
                 "+ 可继续追问提示」输出精简版，全文 200 字以内，不要罗列全部字段。")
    else:
        focus = ("\n【本次回答形态】用户提了开放问题：围绕问题本身回答；只有确实相关时才补充背景信息，不要罗列全部字段。")

    return (
        f"<用户画像>\n玩法分类：{cat_name}\n出行人数：{grp_name}\n"
        f"识别到的景点：{spot_name or '（未明确）'}\n"
        f"推荐与呈现要求：{profile_text}\n\n"
        f"<检索到的资料>\n{context}\n\n"
        f"<用户问题>\n{question}\n"
        f"{focus}"
    )


# ---------------- 翻译阶段（草稿 -> 按钮目标语言；只换语言，不换内容） ----------------
def _glossary(spot, supplements):
    """汇总本次涉及景点的中/韩/英惯用名称，供翻译保持专有名词统一。"""
    entries = []
    docs = [spot] if spot else []
    for s in supplements or []:
        d = s.get("doc")
        if d:
            docs.append(d)
    for doc in docs:
        if not doc:
            continue
        ko = next((a for a in doc.aliases if re.search(r"[가-힣]", a)), "")
        en = next((a for a in doc.aliases if re.fullmatch(r"[A-Za-z\s'\-]+", a)), "")
        entries.append({"zh": doc.name, "ko": ko, "en": en})
    return entries


def _translator_system_prompt(out_lang, glossary):
    target = LANG_NAMES.get(out_lang, "English")
    name_map = ""
    if glossary:
        lines = []
        for g in glossary:
            if g["ko"] or g["en"]:
                lines.append(f"- 中文「{g['zh']}」→ 韩文惯用：{g['ko'] or '（无固定译法，保留中文原名并括注）'}；"
                             f"英文惯用：{g['en'] or '（无固定译法，保留中文原名并括注）'}")
        if lines:
            name_map = "【专有名词对照表，全文必须统一使用】\n" + "\n".join(lines) + "\n\n"
    return (
        f"你是釜山旅行指南的专业 {target} 译者。把下面的中文草稿完整翻译成 {target}。\n"
        "【只换语言，不换内容】\n"
        "1. 严格保留全部事实数据：数字、时间、票价、距离、站名、线路名、网址、列表条数、推荐先后顺序、章节数量"
        "一律不得改动、增删、合并或调换。\n"
        "2. 专有名词优先使用上表给出的目标语言惯用译法，同一名称全文译法必须统一；"
        "没有通用译法时，保留中文原名，并在**首次出现**时于括号内标注目标语言译法，之后沿用同一形式。\n"
        "3. 不得新增草稿中没有的条目、建议或景点，也不得删除草稿中已有的任何条目。\n"
        "4. 原样保留 Markdown 结构：标题层级、**加粗**、项目符号 `-`、`---` 分隔线、URL 不译不改。\n"
        "5. 语气风格与草稿保持一致（亲切、可照着走的向导口吻），不要总结、不要加译者说明。\n"
        f"{name_map}"
        "现在开始翻译，只输出译文正文。"
    )


def _question_to_zh(question, input_lang):
    """非中文提问先转成简体中文，仅用于本地中文库检索 / 字段识别；翻译失败原样返回。"""
    if not core_api.is_configured():
        return None
    lang_name = LD.detect_name(input_lang) or "外语"
    out = core_api.chat([
        {"role": "system", "content": f"把用户的{lang_name}提问翻译成简体中文，只输出中文译文："
                                      "不要解释、不要加引号、不要补写问题；若是景点专有名词，"
                                      "给出中文惯用名称；翻译不了就原样返回。"},
        {"role": "user", "content": question},
    ], timeout=30, retries=1)
    return (out or "").strip() or None


def _translate_to(text, out_lang, glossary=None):
    """把中文草稿翻译成目标语言；失败返回 None（由上层回退中文草稿并标注）。"""
    if not text or out_lang == "zh":
        return text
    system = _translator_system_prompt(out_lang, glossary or [])
    translated = core_api.chat([
        {"role": "system", "content": system},
        {"role": "user", "content": text},
    ], timeout=90, retries=1)
    return translated if translated else None


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


# ---------------- 来源标签按按钮目标语言重标（不依赖全局界面语言） ----------------
SOURCE_KEY = {
    "local": "source_local",
    "profile": "source_profile",
    "core": "source_core",
    "web": "source_web",
    "official": "source_official",
}


def _localized_string(key, lang, fallback=""):
    item = i18n.STRINGS.get(key)
    if not item:
        return fallback or key
    return item.get(lang) or item.get("zh") or fallback


def _localize_sources(sources, lang):
    """把来源标签按 out_lang 本地化；URL / 文件路径 / 详情原文保持不变。"""
    out = []
    for s in sources or []:
        label_key = SOURCE_KEY.get(s.get("type"))
        label = _localized_string(label_key, lang, s.get("label", "")) if label_key else s.get("label", "")
        detail = s.get("detail", "")
        # 在线查询失败的说明语也按目标语言重标
        zh_failed = i18n.STRINGS["web_failed"].get("zh", "")
        if s.get("type") == "web" and detail == zh_failed:
            detail = _localized_string("web_failed", lang, detail)
        out.append({**s, "label": label, "detail": detail})
    return out


_LEAD_LABEL = re.compile(
    r"^[\s\-•·]*(景点名称|韩文名|英文名|别名|介绍|简介|概况|概览|详情|基本信息|"
    r"交通信息|交通|开放信息|开放时间|门票|费用|票价|推荐路线|拍照打卡|美食|"
    r"适合人群|注意事项|来源网址|周边|住宿|소개|교통|요금)\s*[:：]\s*")


def _trim_field(text, max_chars=150):
    """把一个字段压成一行短句：去掉标签行与重复标签前缀、折叠空白、按句号截断。"""
    t = re.sub(r"^[\[【][^\]】]{1,12}[\]】]\s*", "", (text or "").strip())
    t = re.sub(r"\s+", " ", t).strip()
    # 字段原文常是「景点名称：甘川文化村 介绍：位于…」这类连写，循环剥掉开头标签
    for _ in range(4):
        new = _LEAD_LABEL.sub("", t, count=1)
        if new == t:
            break
        t = new
    m = re.search(r"(介绍|简介|概况|소개)\s*[:：]", t[:26])
    if m:
        t = t[m.end():].strip()
    t = re.sub(r"\s+", " ", t).strip()
    if len(t) <= max_chars:
        return t
    cut = t[:max_chars]
    for sep in ("。", "；", ".", ";", "·"):
        pos = cut.rfind(sep)
        if pos > max_chars // 2:
            return cut[:pos + 1]
    return cut.rstrip("，,、 ") + "…"


def _concise_local(spot, out_lang, sources, supplements=None, online=True):
    """只给景点名时的精简本地答（无 LLM 时使用）：一句话定位 + 亮点 + 交通 + 门票/开放。"""
    overview = _trim_field(spot.get("overview"), 70)
    highlights = []
    for key in ("photo", "course", "tips"):
        if spot.get(key):
            for seg in re.split(r"[。；\n]", _trim_field(spot.get(key), 400)):
                seg = seg.strip(" -·")
                if seg and len(seg) >= 4:
                    highlights.append(seg[:40])
        if len(highlights) >= 3:
            break
    transport = _trim_field(spot.get("transport"), 90)
    tickets = _trim_field(spot.get("ticket"), 60)
    hours = _trim_field(spot.get("hours"), 60)

    lines = [f"**{IP.localize_labels(spot.name, out_lang)}** —— {overview}"]
    if highlights:
        lines.append("")
        lines.append("- " + "\n- ".join(highlights[:3]))
    lines.append("")
    lines.append(f"**{_localized_string('label_transport', out_lang)}**：{transport}")
    pay = " ｜ ".join([x for x in (tickets, hours) if x])
    if pay:
        lines.append(f"**{_localized_string('label_ticket_hours', out_lang)}**：{pay}")
    lines.append("")
    lines.append(f"_{_localized_string('ask_more', out_lang)}_")
    content = "\n".join([x for x in lines if x is not None])

    sup_block = render_supplements(supplements or [], out_lang)
    if sup_block:
        content = content + "\n\n" + sup_block

    src_lines = "\n".join(f"- {s['label']}：{s['detail']}" for s in sources)
    footer = f"\n\n---\n**{_localized_string('sources_label', out_lang)}**\n{src_lines}"
    if not online:
        footer += f"\n\n_{_localized_string('login_required_online', out_lang)}_"
    else:
        footer += f"\n\n_{_localized_string('offline_mode', out_lang)}_"
        if out_lang != "zh":
            footer += f"\n_{_localized_string('offline_no_translate', out_lang)}_"
    return content + footer


def _local_fallback(spot, field, category, group_type, out_lang, sources, supplements=None,
                    concise=False, online=True):
    """离线（未登录或未配置 LLM_API_KEY）：无法在线翻译，正文保留中文资料库原文，仅本地化界面标签。"""
    if spot and concise:
        return _concise_local(spot, out_lang, sources, supplements, online=online)
    if spot:
        body = spot.get(field) if (field and spot.get(field)) else spot.full_text()
        content = f"**{spot.name}**\n\n{IP.localize_labels(body, out_lang)}"
    else:
        content = _localized_string("no_result", out_lang)

    # 主回答之后，单独成段给出限量跨类补充（标注玩法 + 理由，目标语言）
    sup_block = render_supplements(supplements or [], out_lang)
    if sup_block:
        content = content + "\n\n" + sup_block

    src_lines = "\n".join(f"- {s['label']}：{s['detail']}" for s in sources)
    footer = f"\n\n---\n**{_localized_string('sources_label', out_lang)}**\n{src_lines}"
    if not online:
        footer += f"\n\n_{_localized_string('login_required_online', out_lang)}_"
    else:
        footer += f"\n\n_{_localized_string('offline_mode', out_lang)}_"
        if out_lang != "zh":
            footer += f"\n_{_localized_string('offline_no_translate', out_lang)}_"
    return content + footer


# ==================================================================
# 五、主入口
# ==================================================================
def answer(question, category=None, group_type=None, lang=None, username=None, ui_lang=None,
           online=None):
    """
    返回 dict：
        answer / sources / followups / spot / field / lang / offline / recognize / supplements
        / online / web_count / concise

    语言策略（本轮重构）：
      - 输出语言只由顶部按钮语言（ui_lang，等价 i18n.I.lang）决定，与提问语言、数据来源无关；
      - 无论按钮是哪种语言，后端一律先用中文检索中文数据库、生成中文草稿；按钮为中文时跳过翻译，
        按钮为韩文 / 英文时再把中文草稿整体翻译后输出；
      - 用户输入语言与按钮不一致时，仍以按钮语言作答；
      - 翻译只换语言不换内容：事实数据、条目数量、推荐顺序、Markdown 结构保持不变。

    联网策略（本轮新增）：
      - online=True：登录后的联网模式，访问各景点官方网站（official_sites）+ 在线 AI 草稿；
      - online=False：未登录，只用本地数据库直出，不访问外网，回答里带离线说明。
    """
    online_flag = True if online is None else bool(online)
    question = (question or "").strip()

    # ① 输出语言 = 按钮语言（显式 lang 参数视为按钮显式指定；不再按提问语言 detect 决定输出）
    out_lang = _normalize_lang(lang or ui_lang or i18n.I.lang or config.DEFAULT_LANG)
    # 提问语言仅用于状态栏识别展示，不影响输出语言
    input_lang = LD.detect(question)

    KB.load()

    # 非中文提问：先转成简体中文用于检索中文库；原问题保留给草稿生成与日志展示
    zh_query = question
    if input_lang and input_lang != "zh" and core_api.is_configured():
        zh_query = _question_to_zh(question, input_lang) or question
        # 机器翻译常把韩文/英文地名音译错（如 몰운대 -> "茂云台"），导致景点名识别失败：
        # 译文里找不到任何景点时，退回用原文（别名表里本就登记了韩文/英文惯用名）重新匹配。
        if not KB.find_spot_global(zh_query) and KB.find_spot_global(question):
            zh_query = question

    # 未显式传分类时，先按中文问题推断玩法（供作用域定位）；spot 命中后以其所属分类为准
    inferred_cat = IP.infer_category(zh_query, category)
    category = category or inferred_cat
    # 未显式传人数时按中文问题推断
    group_type = group_type or IP.infer_group(zh_query)

    # 切换玩法：把所选分类文件夹设为当前唯一主数据源，并立即从磁盘重载、重算
    KB.set_active_category(category)

    spot = KB.find_spot(zh_query, category)
    # 关键词推断的玩法可能猜错（如英文 transport 误命中渔港类），此时用全库别名再兜一次
    if not spot:
        spot = KB.find_spot_global(zh_query)
    # 景点命中后，以景点真实所属分类校正作用域（关键词推断偏差时自动归位）
    if spot and spot.category and spot.category != category:
        category = spot.category
        KB.set_active_category(category)
    field, _hit = IP.detect_field_detail(zh_query)

    # 只输入景点名 -> 置空字段并走精简回答（本轮：不再罗列全部字段）
    only_name = bool(spot and IP.is_only_spot_name(zh_query, spot.aliases))
    if spot and field and only_name:
        field = None
    concise = only_name

    recognize = IP.recognize_summary(question, spot.name if spot else None, field, out_lang,
                                     category, group_type)
    if input_lang and input_lang != out_lang:
        recognize += f" · 提问={LD.detect_name(input_lang)}"

    # ② 检索与草稿一律使用中文上下文（中文数据库）；补充推荐与来源标签随后按 out_lang 重标
    context, sources, web_hits, _supp_zh = build_context(spot, field, category, group_type, "zh",
                                                        online=online_flag)
    supplements = RC.build_cross_supplement(KB, category, group_type, out_lang, limit=RC.CROSS_LIMIT)
    sources = _localize_sources(sources, out_lang)

    if not sources:
        return {"answer": _localized_string("no_result", out_lang), "sources": [], "followups": [],
                "spot": None, "field": field, "lang": out_lang, "offline": True,
                "recognize": recognize, "supplements": [],
                "online": online_flag, "web_count": 0, "concise": concise}

    def fallback():
        return {
            "answer": _local_fallback(spot, field, category, group_type, out_lang,
                                      sources, supplements, concise=concise,
                                      online=online_flag),
            "sources": sources,
            "followups": RC.suggest_questions(spot.name if spot else "", field, out_lang,
                                              spot.fields if spot else None),
            "spot": spot.name if spot else None,
            "field": field, "lang": out_lang, "offline": True,
            "recognize": recognize,
            "supplements": supplements,
            "category": category, "group_type": group_type,
            "online": online_flag, "web_count": len(web_hits), "concise": concise,
        }

    # 未登录 = 纯本地模式：不联网、不调在线 AI
    if not online_flag:
        return fallback()

    if not core_api.is_configured():
        return fallback()

    # ③ 第一段：基于中文资料生成简体中文草稿（系统/用户提示词均固定中文；长上下文给足超时 + 重试）
    raw = core_api.chat([
        {"role": "system", "content": _draft_system_prompt(concise=concise)},
        {"role": "user", "content": _draft_user_prompt(question, context, category, group_type,
                                                      field, spot.name if spot else None,
                                                      concise=concise)},
    ], timeout=90, retries=1)
    if raw is None:
        return fallback()

    followups_zh, draft_text = [], raw
    if "###FOLLOWUP###" in raw:
        main, tail = raw.split("###FOLLOWUP###", 1)
        draft_text = main.strip()
        for line in tail.strip().splitlines():
            line = line.strip().lstrip("-").strip()
            if line:
                followups_zh.append(line)
            if len(followups_zh) == 3:
                break
    # 草稿正文若又自带一个分隔标记，标记之后的内容不进入正文（预测问题只走独立字段）
    draft_text = draft_text.split("###FOLLOWUP###")[0].strip()

    if not followups_zh:
        followups_zh = RC.suggest_questions(spot.name if spot else "", field, "zh",
                                            spot.fields if spot else None)

    glossary = _glossary(spot, supplements)

    # ④ 第二段：按钮为中文跳过翻译；非中文把中文草稿整体翻译（只换语言，不换内容）
    if out_lang == "zh":
        text, followups = draft_text, followups_zh
    else:
        translated = _translate_to(draft_text, out_lang, glossary)
        if translated is None:
            # 翻译服务失败：保留中文草稿并如实标注，不编造译文
            text = draft_text + "\n\n" + _localized_string("translate_failed", out_lang)
            followups = RC.suggest_questions(spot.name if spot else "", field, out_lang,
                                              spot.fields if spot else None)
        else:
            text = translated
            followups = []
            for q in followups_zh:
                tq = _translate_to(q, out_lang, glossary)
                followups.append(tq if tq else q)
            # 预测问题若有翻译失败，整体换成目标语言结构化模板，避免目标语言里夹杂中文问题
            if any(q == f for q, f in zip(followups, followups_zh)):
                followups = RC.suggest_questions(spot.name if spot else "", field, out_lang,
                                                spot.fields if spot else None)

    # 翻译 / 草稿若再次漏入分隔标记，正文只保留标记之前的内容（预测问题独立走 followups）
    text = text.split("###FOLLOWUP###")[0].rstrip()

    # ⑤ 跨类补充段固定排在主回答之后；翻译后的正文不含补充段时用结构化 supplements 补齐
    if supplements and SUPPLEMENT_TITLE.get(out_lang, "") not in text:
        text = text + "\n\n" + render_supplements(supplements, out_lang)

    return {"answer": text, "sources": sources, "followups": followups,
            "spot": spot.name if spot else None, "field": field, "lang": out_lang,
            "offline": False, "recognize": recognize, "supplements": supplements,
            "category": category, "group_type": group_type,
            "online": online_flag, "web_count": len(web_hits), "concise": concise}


if __name__ == "__main__":
    KB.load()
    print("已加载景点：", list(KB.spots.keys()))
    print("重点档案：", {c: d.name for c, d in KB.spot_profiles.items()})
    print("rules 长度：", len(KB.rules_text), "\n")
    for q, cat, grp, on in [
        ("甘川文化村", "01_艺术村落_文化街区", "two_mf", True),
        ("甘川文化村", "01_艺术村落_文化街区", "two_mf", False),
        ("甘川文化村 交通", "01_艺术村落_文化街区", "solo_female", True),
        ("没云台", "02_海岸休闲_日落夜景", "two_ff", True),
        ("감천문화마을 개방시간", "01_艺术村落_文化街区", "solo_male", True),
    ]:
        r = answer(q, category=cat, group_type=grp, online=on)
        print("=" * 66)
        print(f"Q: {q}  online={on}  spot={r['spot']}  field={r['field']}  concise={r.get('concise')}"
              f"  online_out={r.get('online')}  web={r.get('web_count')}  offline={r['offline']}")
        print("  A:", (r["answer"] or "")[:220].replace("\n", " "))
        print("  SRC:", [s["detail"] for s in r["sources"]][:4])
        print("  NEXT:", r["followups"])