# Changelog — 2026-11-01 玩法作用域隔离 · 双栏联动 · 手机版安装压缩包

## 本次目标
1. 主程序左侧「玩法分类 / 出行人数」两栏随用户提问**实时联动**，同时保留用户手动点选；
2. 选定玩法后，**该分类文件夹成为当前唯一主数据源**；切换玩法立即重载对应数据库并重算全部结果；
3. 其它玩法景点**仅**允许出现在「个性化推荐」补充段：标注所属玩法与推荐理由、数量受限、排在主推荐之后；推荐逻辑 / 输出格式 / 语气风格保持不变；
4. 手机版下载方式改为**压缩包（内含一键启动器与离线资源）**，页面内提供下载入口；
5. 推送 GitHub 仓库并生成本日志。

## 改动文件
| 文件 | 改动 |
|------|------|
| `Busan/intent_parser.py` | 新增四类三语关键词表 `CATEGORY_KEYWORDS`、人数关键词表 `GROUP_KEYWORDS` 与 `SOLO/MALE/FEMALE_WORDS`；新增 `infer_category(question, hint)`（手动 hint 优先，关键词打分命中才联动，无把握返回 `None` 保持手动选择）、`infer_group(question)`（先判两人/团体，再判 solo 男女，仅说"一个人"未指明性别返回 `None`）；`recognize_summary` 扩参 `category/group`，状态栏摘要追加「玩法=… · 人数=…」 |
| `Busan/rag_core.py` | 知识库作用域重构：`active_category` 状态、`set_active_category(cat)`（分类变化才触发重载）、`reload_category(cat)`（先清旧条目再从磁盘重读该文件夹，不影响其它分类补充池）、`active_docs()`、`find_spot` 限定当前分类内找主景点、`cross_category_docs`（跨其它分类**轮询**取点，保证补充点来自不同玩法）；`build_context` 改为四元组返回 `(context, sources, web_hits, supplements)`，主数据源只取当前分类档案，rules.txt 标注为"通用规则参考，景点事实以当前玩法文件夹为准"；`answer()` 流程：未传分类/人数先推断 → `set_active_category` 重载 → 景点命中后用 `spot.category` 校正作用域 → 在线模型未输出补充段时用结构化 supplements 前端补齐；系统提示词新增【数据源隔离】【跨类补充规则】两条铁律；离线兜底 `_local_fallback` 增参 `supplements` 并新增 `render_supplements` 在主回答之后单独成段渲染 |
| `Busan/recommend.py` | 新增 `CROSS_LIMIT=2`、三语 `CROSS_REASON` 理由模板、`build_cross_supplement(kb, category, group_type, lang, limit)`：跨类限量取点，理由结合该景点**自身玩法骨架**一句提炼 + 人数适配，逐条携带 `name/category/cat_label/reason/doc` |
| `Busan/main_app.py` | 引入 `intent_parser as IP`；`_apply_scope()` 调 `KB.set_active_category` 立即重载；`answer_question` 发送前先 `infer_category/infer_group` 回写两个 `StringVar`，再应用作用域；拿到结果后用返回的 `category/group_type` 回写选择栏并刷新标签；手动点选 `_on_select` 同样触发重载 |
| `Busan/ui_desktop.py` | 与 `main_app.py` 对称改造：双栏推断联动、作用域重载、结果回写；语言切换后保留已选玩法/人数 |
| `Busan/mobile_app.py` | 新增 `/api/meta`（返回 4 个玩法、6 个人数选项供手机端选择栏初始化）；新增 `GET /download/Busan_Tour_App.zip` 安装包下载路由（`Content-Disposition` 附件下载）；`/api/chat` 回传解析后的 `category/group_type` 与**可序列化** supplements（剥离内部 `SpotDoc` 对象）；Service Worker 缓存版本升到 v2，接口与安装包不进缓存；启动提示改为安装包下载说明 |
| `Busan/mobile/index.html` | 顶部新增「玩法分类 / 出行人数」两个下拉框（可手动改，问答结果自动回写联动）；新增绿色「⤓ 下载安装包」按钮直链 zip；新增跨类补充推荐卡片（标题注明限量、逐条标注玩法徽章 + 理由，排在主回答之后）；附近景点「问介绍」会先把该景点分类同步到选择栏 |
| `Busan/build_package.py` | 新增打包脚本：收集手机版运行所需 9 个 Python 模块 + `docs/` + `activity_classified/` + `mobile/`，生成 Windows 一键启动器 `start_windows.bat`（自动建 venv、装依赖、起服务、开浏览器）、`start.sh`（macOS/Linux）、三语 README、`requirements.txt`，打成 `dist/Busan_Tour_App.zip`；排除 `.env`、`*.db`、`__pycache__`、日志、PPTX、测试脚本 |
| `Busan/test_scope.py` | 新增后端作用域离线回归测试（4 分类主来源泄漏检查 + 补充限量标注 + 推断用例） |
| `Busan/test_mobile_api.py` | 新增手机版接口冒烟测试（首页 / manifest / meta / chat / nearby / 安装包下载） |
| `Busan/logs/changelog_2026-11-01.md` | 本日志 |

## 核心规则落地说明
### 1. 双栏实时联动（手动选择保留）
- 用户提问 → `infer_category` / `infer_group` 按三语关键词打分；**用户已手动选定的玩法优先**，推断只在未手动锁定或识别更明确时覆盖；推断无把握返回 `None`，不破坏手动选择。
- 问答返回后，再用后端最终解析出的 `category/group_type` 回写选择栏，保证界面与实际作用域一致。
- 手动点选任意选项同样立即触发 `KB.set_active_category` 重载。

### 2. 选定文件夹 = 唯一主数据源
- 主回答的本地档案、同分类串联推荐、字段补齐**全部限定在当前分类文件夹**内；`find_spot` 在已选分类时不会到其它分类里找主景点。
- 切换玩法 → `set_active_category` 先删除旧分类内存条目，再从磁盘重读新分类文件夹，**重算**当前主数据源；未选分类时才允许全库兜底。
- 关键词推断偏差时，景点命中后用 `spot.category` 自动校正作用域归位。

### 3. 跨类补充（仅个性化推荐、限量、标注、后置）
- 补充池 `cross_category_docs` 从**当前分类之外**轮询取点（01 → 02、03 各一个，避免两个补充点同属一类），上限 `CROSS_LIMIT = 2`。
- 每条补充携带 `cat_label`（所属玩法）与 `reason`（自身玩法骨架提炼 + 人数适配），在主回答之后单独成段，标题为「其它玩法补充推荐」。
- 系统提示词两条铁律：主回答不得混入其它玩法事实；资料未列出的跨类景点不得自行补充。

### 4. 手机版安装压缩包
- 产物：`Busan/dist/Busan_Tour_App.zip`（约 76 KB，37 个条目）。
- 包内结构：
  ```
  Busan_Tour_App/
    start_windows.bat      Windows 一键启动（自动 venv + 依赖 + 服务 + 浏览器）
    start.sh               macOS / Linux 一键启动
    README.txt              使用说明（手机访问 / 离线缓存 / 安装到主屏 / 数据规则）
    requirements.txt
    mobile_app.py + 8 个运行模块
    mobile/index.html
    docs/                  核心数据库 rules.txt + 重点档案
    activity_classified/   四大玩法分类数据库
  ```
- 手机浏览器打开页面 → 点「⤓ 下载安装包」获取 zip；也可「添加到主屏幕」把 H5 放到桌面，首载后 Service Worker 缓存页面框架，断网可打开页面。

## 使用方式
```
cd Busan
# 桌面版（双栏联动 + 作用域隔离）
python main_app.py

# 手机版（局域网访问 + 安装包下载）
python mobile_app.py 8000

# 重新生成安装压缩包
python build_package.py
```

## 已知限制（如实记录）
- **环境内无 Android SDK / APK 构建工具链**，本轮交付的"安装包"是**完整应用压缩包 + 一键启动器 + 离线 H5**，不是原生 APK：手机端通过浏览器访问 H5、添加到主屏幕获得独立窗口；实时问答依赖服务在线，离线仅能查看已缓存页面框架。若后续需要真正可独立安装的 `.apk`，需另行搭建 Android 构建环境（或用 Capacitor / PWA Builder 把现有 H5 套壳打包）。
- 浏览器定位 API 要求 **HTTPS 或 localhost**；局域网 HTTP 下部分手机浏览器拒绝定位，可改用景点卡片 Naver / Google 导航手动选点，或用隧道暴露 HTTPS。
- 未配置 `LLM_API_KEY` 时为本地检索直出模式；补充段由结构化数据在前端补齐，保持限量与标注规则。
- 桌面 Tkinter 联动本轮完成静态导入与后端接口验证，未做图形界面实机点击验证。

## 验证清单（本轮已执行）
- `python -m py_compile` 本轮全部改动 `.py` 文件 → 通过；`import main_app, ui_desktop` → 通过。
- `test_scope.py` 四个分类用例：主来源 `cross-category leak in main sources: []`（01/02/03/04 均无跨类泄漏）；补充均为 2 个且带 `cat_label`；识别摘要含玩法 + 人数。
- 推断用例：
  - 「情侣去海边看日落」→ `02_海岸休闲_日落夜景` / `two_mf`
  - 「一个男生独自拍照」→ `04_小众渔港_文艺拍照` / `solo_male`
  - 「闺蜜两人逛文创小巷」→ `01_艺术村落_文化街区` / `two_ff`
  - 「一家三口看候鸟」→ `03_湿地生态_自然观景` / `group_3plus`
- `test_mobile_api.py`（本地 8011 端口）：
  - `GET /` → 200，页面含 `catSel` 选择栏；`GET /manifest.json` → 200；`GET /api/meta` → 4 分类 / 6 人数；
  - `POST /api/chat`（02 多大浦）→ 作用域 02、主来源无跨类泄漏、补充来自 01 + 03；
  - `POST /api/chat`（自动推断 04 长林浦口）→ 正确归位 04；
  - `POST /api/nearby` → 8 个景点按距离排序；
  - `GET /download/Busan_Tour_App.zip` → 200，`PK` zip 魔数正确，77.5 KB。
- 压缩包清单核对：无 `.env`、`*.db`、`__pycache__` 泄漏；启动器 / README / 前端 / 数据齐全。
