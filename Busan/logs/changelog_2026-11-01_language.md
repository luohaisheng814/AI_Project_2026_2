# Changelog — 2026-11-01 语言策略重构：按钮语言决定回复 · 中文检索生成后整体翻译 · 切换即重生成

## 本次目标
1. 顶部语言切换按钮（中文 / 한국어 / English）**决定回复语言**，与数据来源、与用户输入语言均无关；
2. 无论按钮是哪种语言，后端一律先用**中文检索中文数据库、生成中文草稿**；按钮为中文时跳过翻译，按钮为韩文 / 英文时再把中文草稿**整体翻译**后输出；
3. 用户输入语言与按钮不一致时，**仍以按钮语言作答**；
4. 翻译只换语言不换内容：保留全部事实数据；专有名词采用目标语言惯用译法，无通用译法时保留中文原名并首次括注意译，全文译法统一；不得增删条目、不得改变推荐顺序；
5. 语言切换后**重新生成完整回答**（重新调用后端，而不是回放旧语言文本）；
6. 推送 GitHub 仓库并生成本日志。

## 改动文件
| 文件 | 改动 |
|------|------|
| `Busan/rag_core.py` | **本轮主战场**。`answer()` 输出语言改为只取按钮语言（`lang` 显式值或 `ui_lang` / `i18n.I.lang`），不再调用 `lang_detect.resolve(question, ui)` 按提问语言决定输出；提问语言仅通过 `LD.detect(question)` 用于状态栏「提问=…」展示。检索与草稿阶段固定使用中文上下文；新增两段式流程：第一段 `_draft_system_prompt()` / `_draft_user_prompt()` 固定中文生成草稿；第二段 `_translate_to(text, out_lang, glossary)` 按按钮语言整体翻译。新增 `_glossary()` 汇总本次景点中 / 韩 / 英惯用名称；`_translator_system_prompt()` 内置「只换语言不换内容、事实 / 数字 / 时间 / 票价 / 站名 / URL / 条目数 / 推荐顺序 / Markdown 结构不变、专有名词惯用译法统一、无通用译法保留中文原名并首次括注、不增删条目」等铁律。新增 `_localize_sources()` 按按钮语言重标来源标签（不依赖全局界面语言）；补充推荐在 `answer()` 内按 `out_lang` 重新构建；翻译失败时保留中文草稿并追加 `translate_failed` 提示；离线非中文保留中文资料库原文、仅本地化界面标签并追加 `offline_no_translate` 说明 |
| `Busan/i18n.py` | 新增 `translate_failed`（翻译服务不可用）与 `offline_no_translate`（离线无法在线翻译）三语文案 |
| `Busan/recommend.py` | `build_cross_supplement` 的分类名 / 人数名改为按传入 `lang` 从 `STRINGS` 取本地化译名（不再读全局 `i18n.I.lang`），保证补充段语言与按钮语言一致；新增 `_group_label` / `_cat_label` 辅助函数 |
| `Busan/intent_parser.py` | `recognize_summary` 的玩法名 / 人数名按传入 `lang` 本地化，不再跟随全局界面语言 |
| `Busan/chat_widget.py` | `ChatView` 新增 `user_questions()`、`regenerate()`、`_regen_worker()`、`_render_regen_bot()`：语言切换后清空画布、回放 welcome 与用户提问，再在后台线程逐条调用 `on_send` 用**当前按钮语言重新生成** bot 回答；重新生成时 `record=False` 不重复写查询日志；旧语言 bot 结果不再回放 |
| `Busan/main_app.py` | `refresh_ui()` 重建界面后调用 `self.chat.regenerate()` 触发全量重新生成；`answer_question(question, record=True)` 增加 `record` 开关，重新生成时不重复记录查询日志；注释更新为「输出语言只由顶部按钮语言决定」 |
| `Busan/ui_desktop.py` | 与 `main_app.py` 对称：`refresh_ui()` 保留已选玩法 / 人数后触发 `chat.regenerate()`；`answer_question` 增加 `record` 参数；输出语言跟随按钮 |
| `Busan/app.py` | CLI 状态栏回答语言显示改为按钮语言 `i18n.I.lang`，不再用 `LD.resolve` 按提问语言判定 |
| `Busan/mobile/index.html` | 顶部新增中文 / 한국어 / English 三语切换按钮；新增 `uiLang` 状态并持久化到 `localStorage`；`/api/chat` 请求体由写死 `ui_lang:'zh'` 改为跟随 `uiLang`；新增界面文案三语字典 `UI_STR` 与 `applyLangUI()`（欢迎语、占位符、发送 / 定位 / 下载按钮、选择栏标签、附近标题、补充标题随按钮语言切换）；`historyQ` 记录历史提问，`setLang()` → `regenerateAll()` 清空对话后按新语言逐条重新生成；补充段标题、附近景点「问介绍」措辞随语言切换 |
| `Busan/build_package.py` | 排除新测试脚本 `test_lang_policy.py` / `test_mobile_api.py`；README 新增「五、语言规则」一节说明按钮语言策略与切换重生成 |
| `Busan/test_lang_policy.py` | **新增**后端语言策略离线回归测试：按钮语言覆盖提问语言、来源 / 补充标签按按钮语言本地化、补充数量 ≤2 且同分类顺序跨语言稳定、离线非中文标注不可翻译、翻译辅助函数中文直通 / 离线非中文安全返回 `None` |
| `Busan/test_mobile_api.py` | 新增三语接口用例：韩文提问 + 中文按钮、中文提问 + 韩文按钮、英文提问 + 英文按钮，断言返回 `lang` 等于按钮语言，来源与补充标签为目标语言 |
| `Busan/dist/Busan_Tour_App.zip` | 用最新代码重新打包（37 个条目，约 80.1 KB） |
| `Busan/logs/changelog_2026-11-01_language.md` | 本日志 |

## 核心规则落地说明
### 1. 按钮语言 = 唯一输出语言
- `answer()` 内 `out_lang = normalize(lang or ui_lang or i18n.I.lang or DEFAULT_LANG)`；`lang_detect.detect(question)` 的结果只用于状态栏展示「提问=…」，**不参与**输出语言决策。
- 桌面 `main_app` / `ui_desktop`、手机 `index.html`、CLI `app.py` 全部把当前按钮语言作为 `ui_lang` 传入；用户用韩文提问而按钮是中文，回答仍是中文；按钮是韩文而用户用中文提问，回答仍按韩文流程处理。

### 2. 两段式：先中文草稿，再整体翻译
- **第一段（草稿）**：系统 / 用户提示词固定简体中文，基于中文数据库上下文生成中文草稿，结构、条目、推荐顺序在这一阶段确定。
- **第二段（翻译）**：`out_lang == "zh"` 直接采用草稿；`ko / en` 调用独立翻译 LLM 调用，把草稿**整体**翻译；预测问题逐条翻译；补充推荐段本身已按目标语言结构化生成，排在主回答之后。
- 翻译提示词强制：数字 / 时间 / 票价 / 距离 / 站名 / 线路 / URL 不译不改；`**加粗**`、标题层级、`-` 列表、`---` 分隔线、`###FOLLOWUP###` 标记原样保留；不新增或删除条目；推荐先后顺序不变；同一专有名词全文统一。

### 3. 专有名词处理
- `_glossary()` 从命中景点与补充景点的别名集合中提取韩文 / 英文惯用名，注入翻译提示词对照表；翻译时优先使用对照表译法。
- 对照表未给出固定译法的名称，要求译者保留中文原名，并在**首次出现**时于括号内标注目标语言译法，之后沿用同一形式，保证全文统一。

### 4. 切换语言 = 重新生成，不回放旧文本
- **桌面**：`LangButton` 循环切换 → `i18n.I.notify()` → `refresh_ui()` 重建界面 → `chat.regenerate()`：丢弃旧语言 bot 结果，按历史用户提问顺序在后台线程逐条重新问答并渲染；玩法 / 人数选择保持不变；重新生成不重复写查询日志。
- **手机**：点击三语按钮 → 更新 `uiLang` 并持久化 → `regenerateAll()` 清空聊天区，按 `historyQ` 顺序逐条带新 `ui_lang` 重新请求后端并渲染。

### 5. 降级与离线口径
- **在线翻译失败**：保留中文草稿，正文末尾追加 `translate_failed` 目标语言提示；预测问题回退到目标语言结构化模板，避免目标语言界面里夹杂中文问题。
- **离线（未配置 `LLM_API_KEY`）**：无法发起翻译调用，正文保留中文资料库原文；界面标签、来源标签、补充分类名 / 理由、预测问题按按钮语言本地化；非中文按钮时正文末尾追加 `offline_no_translate` 如实说明。

## 使用方式
```
cd Busan
# 桌面版（顶部 🌐 按钮循环切换 中文 → 한국어 → English，切换后自动重新生成）
python main_app.py

# 测试桌面版
python ui_desktop.py

# 手机版（顶部三语按钮切换，切换后重新生成历史回答）
python mobile_app.py 8000

# 重新生成安装压缩包
python build_package.py
```

## 已知限制（如实记录）
- 当前环境**未配置 `LLM_API_KEY`**，本轮在线两段式（中文草稿 → 翻译）链路已按代码路径实现并通过离线降级测试；接入有效 `LLM_API_KEY` 后，韩文 / 英文回答会自动走独立翻译段。离线状态下非中文按钮只能做到「界面标签本地化 + 中文正文 + 不可翻译标注」，无法在本地完成整段翻译。
- 桌面 Tkinter 切换重生成完成了后端接口与线程逻辑验证，未做图形界面实机点击录屏；手机端三语切换在本地 HTTP 接口层验证，浏览器实机切换效果需在手机 / 浏览器中确认。
- 专有名词对照表来自档案别名中已有的韩文 / 英文名称；档案未收录惯用译法的名称，按「保留中文原名 + 首次括注意译」规则处理。
- 浏览器定位 API 仍要求 HTTPS 或 localhost；局域网 HTTP 下可改用 Naver / Google 导航手动选点（沿用上一轮限制）。

## 验证清单（本轮已执行）
- `python -m py_compile` 本轮全部改动 `.py` 文件 → 通过；`import main_app, ui_desktop, chat_widget, app, mobile_app` → 通过。
- `test_lang_policy.py`（离线）四组混合语言用例全部通过：
  - 韩文提问 + 中文按钮 → `lang=zh`；中文提问 + 韩文按钮 → `lang=ko`；英文提问 + 英文按钮 → `lang=en`；韩文提问 + 英文按钮 → `lang=en`；
  - 来源标签、补充分类名 / 理由分别为中 / 韩 / 英；补充数量 ≤ 2；同一分类补充顺序跨语言不变；
  - 非中文离线回答含 `offline_no_translate` 标注，中文回答不含；`_translate_to` 中文直通、离线非中文返回 `None`。
- `test_scope.py` 复跑：四分类主来源跨类泄漏均为 `[]`，补充 2 个带 `cat_label`，推断联动保持正确（上一轮作用域规则未被本轮语言改造破坏）。
- `test_mobile_api.py`（本地 8011 端口）：首页 / manifest / meta / chat / nearby / zip 下载全部 200；新增三语用例返回 `lang` 与按钮一致，韩文来源 `주요 명소 아카이브 / 로컬 분류 자료 …`、英文来源 `Spot Profile / Local category database …`，补充标签分别为韩文 / 英文；zip 为 `PK` 魔数。
- 压缩包清单核对：37 个条目，无 `test_*.py`、`.env`、`*.db`、`__pycache__`；`rag_core.py` / `index.html` / `i18n.py` / `recommend.py` / `intent_parser.py` 均为最新代码；约 80.1 KB。
