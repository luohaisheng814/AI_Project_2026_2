# Changelog — 2026-11-01 语言链路修复：按钮语言决定回复 · 中文检索生成后 AI 翻译 · 补充名 / 理由 / 下拉标签本地化

## 本次目标
1. 主程序按用户输入作答；**回复语言只由顶部语言切换按钮（中文 / 한국어 / English）决定**，与提问语言、数据来源无关；
2. 数据库只有中文：无论按钮为何种语言，后端一律先用**中文检索中文数据库、生成中文草稿**；按钮为中文时直通，按钮为韩文 / 英文时由 AI 把中文结果**整体翻译**后输出；
3. 用户输入语言与按钮不一致时，仍以按钮语言作答；非中文提问先由 AI 译成简体中文，再用于本地中文库检索与字段识别；
4. 翻译只换语言不换内容：保留全部事实数据、条目数量、推荐顺序与 Markdown 结构；专有名词采用目标语言惯用译法，无通用译法时保留中文原名；
5. 输入占位符、界面文案、玩法 / 人数下拉标签跟随按钮语言；补充推荐的景点名、分类名、理由全部按按钮语言本地化；
6. 完成离线 / 在线回归测试、重新打包，推送 GitHub 仓库并生成本日志。

## 根因（本轮首要修复）
上一轮代码骨架已就位，但桌面韩文按钮下**正文仍是中文**。排查 `.env` 与 `config.py` 后定位到直接根因：
- `.env` 中实际配置的是 `DASHSCOPE_API_KEY`（`sk-w` 前缀，117 字符）与 `DASHSCOPE_BASE_URL`（阿里云 maas 兼容端点）、`LLM_MODEL=qwen-plus`；
- 而 `config.py` 读取时把键名误拼成 `DASHCOPE_API_KEY`（少一个 `S`），`USING_DASHSCOPE` 判断同样拼错；
- 结果 `LLM_API_KEY` 恒为空、`core_api.is_configured()` 恒为 `False`，`answer()` 每次都在「未配置 LLM」分支走**离线中文兜底**，两段式草稿 → 翻译链路从未真正执行，这正是截图里正文不翻译、补充理由出现 `None` 的直接原因。

## 改动文件
| 文件 | 改动 |
|------|------|
| `Busan/config.py` | 修正环境变量键名拼写：`DASHCOPE_API_KEY/BASE_URL` → `DASHSCOPE_API_KEY/BASE_URL`；`USING_DASHSCOPE` 判断同步改正；注释里的旧拼写一并更正。修复后 `is_configured()=True`、`USING_DASHSCOPE=True`，密钥真正加载。 |
| `Busan/core_api.py` | 抽出 `_once()` 单次调用；`chat(..., retries=1)` 在网络瞬时失败 / 超时 / 非 200 时间隔 1.5 秒自动重试一次，全部失败才返回 `None` 由上层降级；避免大上下文首轮草稿被误判为离线。 |
| `Busan/rag_core.py` | ① 草稿系统提示词允许理解中 / 韩 / 英提问，但**草稿一律简体中文**；② 新增 `_question_to_zh()`：在线时先把非中文提问译成简体中文，`zh_query` 用于玩法 / 人数推断、景点检索、字段识别；原始问题保留给草稿提示词、状态栏与日志；③ `KB.load()` 与 `reload_category()` 把重点档案的韩 / 英别名合并到同名分类档案，补充推荐也能取到惯用译名；④ 草稿拆分 `###FOLLOWUP###` 后再次裁剪标记之后内容，翻译结束后、补充段拼接前对正文再裁一次；翻译提示词删除「保留 `###FOLLOWUP###` 分隔标记」要求；⑤ 草稿与翻译调用 `timeout=90, retries=1`；⑥ 非中文翻译失败时保留中文草稿并标注 `translate_failed`，预测问题回退目标语言结构化模板。 |
| `Busan/recommend.py` | ① `_group_label()` 在人数未识别（`group_type=None`）时返回中性称呼（zh「各类出行者」/ ko「누구나」/ en「any traveler」），修复模板里出现 `None 방문도 무난합니다` 的问题；② 新增 `_localized_name(doc, lang)`：韩文别名 → 英文别名 → 保留中文原名；补充出参新增 `zh_name` 供跨语言顺序比较与回退；③ 补充理由只保留三语 `CROSS_REASON` 模板 + 本地化人数称呼，**去掉**混入理由的 `CATEGORY_STYLE.style_brief`（那是写给 LLM 的答案组织要求，不进入用户可见理由）；`CATEGORY_STYLE` 仍保留给 `build_profile_text()` 注入草稿提示词（内部指导，不外露）。 |
| `Busan/mobile/index.html` | 新增 `META_LABELS` 三语映射（4 个玩法分类、6 个出行人数，key 与 `config.CATEGORIES` / `GROUP_TYPES` 一致）与 `refreshMetaLabels()`；`loadMeta()` 按当前 `uiLang` 渲染下拉选项文本，`applyLangUI()` 切语言时刷新选项标签；后端 `/api/meta` 仅提供 key，不再依赖后端中文硬编码标签。欢迎语、占位符、发送 / 定位 / 下载按钮等界面文案沿用上一轮 `UI_STR` 三语字典。 |
| `Busan/test_lang_policy.py` | 重构为**确定性离线口径**：测试内强制 `core_api.is_configured = lambda: False`，回归测试不依赖网络；断言覆盖输出语言 == 按钮语言、提问语言状态栏标注、来源标签本地化、补充数量 ≤2、补充 `name/cat_label/reason` 不含 `None`、理由不含元话术关键词（타임라인 / timeline / 관찰 포인트 / observation points / Structure the answer / 답변은）、补充顺序按 `zh_name` 跨语言稳定、中文直通；在线两段式翻译由 `test_mobile_api.py` 三语用例在线覆盖。 |
| `Busan/test_mobile_api.py` | 在线 / 离线两用：请求超时由 15 秒放宽到 GET 30 秒、POST 120 秒，匹配长上下文草稿 + 翻译的真实耗时；三语按钮用例断言返回 `lang` 等于按钮语言。 |
| `Busan/dist/Busan_Tour_App.zip` | 用最终代码重新打包：37 个条目，81.9 KB，无测试脚本 / `.env` / `*.db` / `__pycache__`。 |
| `Busan/logs/changelog_2026-11-01_lang_fix.md` | 本日志。 |

## 核心规则落地说明
### 1. 输出语言 = 按钮语言（唯一裁决者）
- `answer()` 中 `out_lang = _normalize_lang(lang or ui_lang or i18n.I.lang or DEFAULT_LANG)`；`lang_detect.detect(question)` 的结果只用于状态栏「提问=…」展示，**不参与**输出语言决策。
- 桌面 `main_app.py` / `ui_desktop.py`、手机 `index.html`、CLI `app.py` 都把当前按钮语言作为 `ui_lang` 传入；韩文提问 + 中文按钮 → 中文作答，中文提问 + 韩文按钮 → 韩文作答。

### 2. 两段式：中文检索生成 → 按按钮语言整体翻译
- **检索 / 推断**：非中文提问先转 `zh_query`，玩法推断、`find_spot`、字段识别全部基于中文问题与中文库；`build_context(..., "zh")` 固定提供中文上下文。
- **第一段草稿**：系统 / 用户提示词固定简体中文，基于中文资料生成中文草稿，事实条目、推荐顺序在这一阶段确定。
- **第二段翻译**：`out_lang == "zh"` 直通；`ko / en` 调用独立翻译调用整体翻译正文，预测问题逐条翻译；补充段本身已按目标语言结构化生成，固定排在主回答之后。
- 翻译提示词强制：数字 / 时间 / 票价 / 距离 / 站名 / 线路 / URL 不译不改；标题层级、`**加粗**`、`-` 列表、`---` 分隔线、条目数量、推荐顺序、Markdown 结构保持不变；不新增或删除条目；同一专有名词全文统一。

### 3. 专有名词与补充推荐本地化
- `_glossary()` 汇总命中景点与补充景点的中 / 韩 / 英惯用名注入翻译对照表；补充景点名由 `_localized_name()` 直接取目标语言惯用名（韩文别名优先、其次英文别名，无通用译法保留中文原名）。
- 补充段分类名、人数称呼、理由均按 `out_lang` 本地化；补充数量上限 `CROSS_LIMIT=2`，只出现在主推荐之后，并标注所属玩法与理由。
- 重点档案（甘川 / 多大浦）里的韩 / 英别名已合并到同名分类档案，修复了补充推荐只取到中文文件夹名的问题。

### 4. 非中文提问的中文检索链路
- 在线且已配置 LLM 时，`_question_to_zh()` 先把韩文 / 英文提问译成简体中文；翻译失败或离线时回退原问题，不阻断检索。
- 原始非中文问题仍进入草稿提示词（模型理解意图）与状态栏展示，`zh_query` 只服务本地中文库匹配。

### 5. 切换语言 = 重新生成，不回放旧文本
- **桌面**：语言按钮循环切换 → `i18n.I.notify()` → `refresh_ui()` 重建界面 → `chat.regenerate()`：丢弃旧语言 bot 结果，按历史提问顺序在后台线程逐条重新问答；玩法 / 人数选择保持；重新生成不重复写查询日志。
- **手机**：点击三语按钮 → 更新 `uiLang` 并持久化到 `localStorage` → `regenerateAll()` 清空聊天区，按 `historyQ` 顺序带新 `ui_lang` 逐条重新请求后端并渲染；下拉标签随新语言刷新。

### 6. 降级口径
- **在线翻译失败**：保留中文草稿，正文末尾追加目标语言 `translate_failed` 提示；预测问题回退目标语言结构化模板，避免目标语言界面夹杂中文问题。
- **离线（未配置密钥）**：正文保留中文资料库原文，界面标签 / 来源标签 / 补充分类名 / 理由 / 预测问题按按钮语言本地化；非中文按钮追加 `offline_no_translate` 如实说明，不编造译文。

## 使用方式
```
cd Busan

# 桌面版（顶部 🌐 按钮循环切换 中文 → 한국어 → English，切换后自动重新生成）
python main_app.py
# 桌面测试入口
python ui_desktop.py

# 命令行版（/lang 切换按钮语言）
python app.py

# 手机版（顶部三语按钮切换，切换后重新生成历史回答）
python mobile_app.py 8000

# 回归测试
python test_lang_policy.py     # 语言策略离线确定性回归
python test_scope.py           # 作用域隔离 / 跨类补充 / 推断联动
python test_mobile_api.py      # 先启动 python mobile_app.py 8011，再跑本脚本

# 重新生成手机版安装压缩包
python build_package.py
```

## 已知限制（如实记录）
- 桌面 Tkinter 切换重生成完成了后端接口、线程逻辑与接口层验证，未做图形界面实机点击录屏；手机端三语切换在本地 HTTP 接口层验证，浏览器实机切换效果需在手机 / 浏览器中确认。
- `/api/meta` 后端返回的分类 / 人数标签仍是中文硬编码；本轮已由手机前端 `META_LABELS` 按按钮语言覆盖显示，后端未改动该接口。桌面侧边栏标签由 `i18n` 三语字典提供，已本地化。
- 档案未收录韩 / 英惯用名的景点（如长林浦口、峨嵋山观景台、洛东江河口生态中心）在 ko / en 下保留中文原名；在线译文里模型偶发把本地文件夹路径名译成目标语言，结构化 `sources` 列表仍保留原始路径，不受影响。
- 浏览器定位 API 仍要求 HTTPS 或 localhost；局域网 HTTP 下可改用景点卡片上的 Naver / Google 导航手动选点（沿用上一轮限制）。
- 离线状态下非中文按钮只能做到「界面标签本地化 + 中文正文 + 不可翻译标注」，无法在本地完成整段翻译；整段翻译需要在线 LLM 可用。

## 验证清单（本轮已执行）
- `python -m py_compile` 本轮全部后端与测试模块 → 通过（exit 0）。
- `test_lang_policy.py`（强制离线确定性口径）→ `ALL LANG-POLICY CHECKS PASSED`：
  - 韩文提问 + 中文按钮 → `lang=zh`；中文提问 + 韩文按钮 → `lang=ko`；英文提问 + 英文按钮 → `lang=en`；韩文提问 + 英文按钮 → `lang=en`；
  - 来源标签、补充分类名 / 理由分别为中 / 韩 / 英；补充数量 ≤ 2；补充字段无 `None`；理由无内部写作元话术；同一分类补充顺序跨语言不变；中文直通、离线非中文翻译安全返回 `None`。
- `test_scope.py` 复跑：四分类主来源跨类泄漏均为 `[]`；补充 2 个并带 `cat_label`；四组推断联动（海边日落 / 独自拍照 / 闺蜜文创 / 一家三口候鸟）分类与人数解析正确，上一轮作用域规则未被本轮语言改造破坏。
- `test_mobile_api.py`（本地 8011 端口）：首页 / manifest / meta / chat / nearby / zip 下载全部 200；三语按钮用例返回 `lang` 与按钮一致；韩文来源 `주요 명소 아카이브 / 로컬 분류 자료 …`、英文来源 `Spot Profile / Local category database …`；补充名本地化（`다대포해수욕장 / 을숙도 / Sunset Fountain of Dream / Eulsukdo`）；附近景点返回 8 个；zip 为 `PK` 魔数。
- 在线两段式实测：韩文 / 英文按钮均 `offline=False`，正文为目标语言，补充名本地化、理由干净，预测问题独立成行、无 `###FOLLOWUP###` 标记泄漏、无中文预测问题残留。
- 压缩包清单核对：37 个条目，无 `test_*.py`、`.env`、`*.db`、`__pycache__`；`rag_core.py` / `recommend.py` / `config.py` / `core_api.py` / `mobile/index.html` 等关键模块均为最新代码；81.9 KB。
