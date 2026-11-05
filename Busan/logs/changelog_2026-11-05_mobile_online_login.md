# Changelog — 2026-11-05 手机版登录 / 联网双源作答 / 精简回答 / NAVER 深链（+ 运行逻辑图）

> 本轮承接上一轮「APK 与模拟器实测」的成果，转向**手机网页版（PWA）**：补登录、接官网、改回答策略、加地图深链，并把整套运行逻辑画成图后一并入库。

## 本次目标（用户本轮七项 + 三项交付）

| # | 需求 | 落点 |
|---|------|------|
| ① | 完善手机版 UI，加**登录按钮**（文案随中/韩/英切换，用户库与网页版/桌面版互通） | `mobile/index.html`、`mobile_app.py` |
| ② | **登录后联网**，回答同时引用**各景点官网 + 本地数据库** | `rag_core.build_context`、`official_sites.py` |
| ③ | 优化回答：**只输入景点名时给精简回答** | `rag_core.answer`（`concise` 分支） |
| ④ | 手机版能**调起 NAVER 等地图 App 获取精准位置** | `mobile_app.py` `/api/nearby`、前端 `renderNearby` |
| ⑤ | **创作运行逻辑图表** | `docs/run_logic.html` → `docs/run_logic.png` |
| ⑥ | 推送 GitHub `main` | 本轮提交 |
| ⑦ | 生成本轮日志 | 本文件 |

约束前提（本轮已与用户确认）：登录与联网做在 `main_app.py`（桌面）与手机网页版两边，账号共用 `Busan/busan_travel.db`；**NAVER 精准定位只在手机版**；安卓 APK 本轮**未获授权改动**，维持离线形态（无 INTERNET 权限）。

## 一、官网来源是怎么定下来的

仓库里只有 01/02 两个玩法档案带「来源网址」段，其余 6 个景点没有。于是新建 `Busan/official_sites.py` 手工登记 8 个景点的官方入口：

| 景点 | 官方入口 |
|------|----------|
| 甘川文化村 | `https://www.saha.go.kr/tour/contents.do?mId=0101010000` + `https://www.gamcheon.or.kr/` |
| 多大浦海水浴场 | `mId=0101030000` |
| 没云台 | `mId=0101040000` |
| 乙淑岛候鸟公园 | `mId=0101060000` |
| 长林浦口 | `mId=0101110000`（부네치아 장림항） |
| 多大浦梦之夕阳喷泉 | `mId=0600000000`（낙조분수 运营안내 `0609000000`） |
| 洛东江河口生态中心 | **无独立页**，代用沙下区「철새도래지」`mId=0301050000`，`note` 如实说明 |
| 峨嵋山观景台 | **无独立页**，挂「대표명소」汇总页 `mId=0101000000`，`note` 如实说明 |

采集中确认的两件事：

- 沙下区景点列表页 `attraction/list.do?mId=0501000000` 能抽 `href` 得到「景点 → mId」映射；`pageIndex=1/2/3` 返回完全一致的 7 条代表名所，**不是分页**。
- 详情页正文容器 id 是 **`conts`**（不是 `contents`），`soup.find(id='conts')` 能稳定取到约 724 字纯正文，是可靠锚点。

## 二、官网抓取 403 的根因（本轮最费时的一段）

现象：`official_sites.fetch()` 对 8 个景点**全部返回 0 条**。逐层复现后的决定性结果：

| 请求头 | 结果 |
|--------|------|
| 只带 UA | 200 |
| `Accept-Language: zh-CN,zh;q=0.9,ko;q=0.8,en;q=0.7` | **403**（67 字节 `- BAD REQUEST -`） |
| `Accept-Language: ko-KR,ko;q=0.9,en;q=0.8` | 200 |
| `Accept-Language: en-US,en;q=0.9` | 200 |
| 不带该头 | 200 |

**根因：沙下区官网防火墙把 `Accept-Language` 含 `zh-CN` 的请求判为异常直接 403，与 UA、Cookie、Session 无关。** 改为固定韩文语种头后，8 个景点各抓到 1 条正文（约 169 200 字节）。该坑已写进 `web_lookup._get()` 的注释，避免以后有人「顺手」把语种头改回中文。

被验证为死路、已硬跳过的来源：

- `visitbusan.net`（含 `/index.do`、`/en/index.do`）返回 6 275 字节 JS 壳，正文前端渲染 → 进 `web_lookup._SKIP_HOSTS`；
- `eco.busan.go.kr` 连接失败（443 Max retries）、`www.busan.go.kr` 根域 `ConnectionResetError(10054)`；
- 沙下区 `mId=0101020000 / 0101050000 / 0101070000 / 0101080000 / 0101100000 / 0101120000` 全为空页；
- 沙下区站内检索 `/RSA/front/Search.jsp`（`query=` 与 `searchWord=`）返回固定 21 012 字节无结果。

## 三、`rag_core` 改造（回答双源 + 精简）

- `build_context(..., online=True)` 新增 `online` 形参：先走 `official_sites.fetch(spot.name, extra_keywords=kw[1:], max_pages=2)`，把官网正文以 `=== 官方网站在线查询（portal｜抓取于 时间）：url ===` 注入上下文，`sources` 记 `type="official"`；再对档案里的「来源网址」做 `web_lookup.lookup` 兜底；都没命中记 `web_failed`；`note`（无独立官网的说明）作为 `type="official"` 说明条目输出。
- `_draft_system_prompt(concise=False)` 新增【官网优先】条款：地址 / 电话 / 开放时间 / 票价 / 官网链接一律以官网段为准，官网与本地档案冲突时必须说明差异，**不得虚构官网没给的数字**。
- **精简分支**：`answer()` 里 `only_name = IP.is_only_spot_name(...)`，`concise = only_name`；系统/用户提示词同时分叉，要求「一句话定位 + 2–3 个亮点 + 交通一句 + 门票/开放一句」、全文 200 字内、禁止罗列全字段。无 LLM 时另有 `_concise_local()` 本地精简模板。
- **未登录早退**：`if not online_flag: return fallback()`，不抓官网、不调大模型；`fallback()` 与四个返回点统一补 `online / web_count / concise`。
- 本段新增的四处修复（都由实测暴露）：
  1. `_LEAD_LABEL` 正则扩充（`介绍/简介/概况/소개` 等），`_trim_field()` 循环剥掉「景点名称：…介绍：…」连写标签 —— 修掉离线精简答里的标签残留。
  2. 新增 `KnowledgeBase.find_spot_global(query)`：忽略当前玩法作用域、全库别名匹配。
  3. 非中文提问「先机翻再检索」的坑：LLM 把 `몰운대` 音译成「茂云台」、`Molundae` 译成「毛伦岱」，导致景点识别失败。修法：译文里找不到景点而原文能找到时 `zh_query` 退回原文；`find_spot` 失败后再用 `find_spot_global` 兜一次（关键词推断玩法可能猜错，例如英文 `transport` 误命中渔港类）。
  4. `intent_parser._hit_count` 英文关键词改**整词匹配**（`(?<![a-z0-9])…(?![a-z0-9])`）：原先 `transport` 里的 `port` 命中「小众渔港」、`woman` 里的 `man` 命中 male。
- 离线页脚措辞修正：未登录时不再打印「No LLM_API_KEY set…」这种误导文案，改为「登录后联网」提示（`login_required_online`）；真正缺密钥才显示离线说明。

## 四、手机版服务 `mobile_app.py`（全量重写）

- 会话：`COOKIE_NAME="busan_sid"`、`SESSION_TTL=7×24h`、内存 `SESSIONS` + 锁；`new_session / get_session / drop_session`。
- 端点：`GET /`、`/manifest.json`、`/sw.js`、`/icon-192.png`、`/icon-512.png`、`/api/meta`、`/api/me`、`/download/Busan_Tour_App.zip`；`POST /api/login`（`db.verify_login` → `db.get_user` 取 id 建会话）、`/api/register`（`db.add_user`，注册即登录）、`/api/logout`、`/api/chat`、`/api/nearby`。
- `/api/chat`：`online = bool(sess)`、`username = sess["username"] if sess else "guest"`，出参含 `online / web_count / concise / username`，并 **`db.log_query(...)` 写库**（此前手机端不写 `query_logs`，后台看不到手机端记录）。
- `/api/nearby` 一次给四类链接：
  - `naver_place_url` = `nmap://place?lat=&lng=&name=`（坐标直给，不靠关键词猜点）
  - `naver_route_url` = `nmap://route/public?slat=&slng=&sname=현위치&dlat=&dlng=&dname=`（以浏览器定位为起点直接导航）
  - `naver_web_url` = `https://map.naver.com/p/search/<韩文名>`（没装 App 时兜底）
  - `google_url` 改 `dir` 形态；全部带 `appname=com.busan.tour`，出参 `map_app="naver"`。
- 本段修正：`SPOTS_GEO` / `CAT_LABEL` 的第 3 类名与 `config.CATEGORIES`、实际目录统一为 **`03_湿地生态_自然观景`**（此前误写「自然景观」，导致玩法下拉直接显示原始目录名）。
- `SW_JS` 改为 **v4：页面导航网络优先、图标缓存优先**。原因：v3 的 cache-first 会把旧 `index.html` 一直喂给浏览器，前端改了却看不到效果（本轮排查显示层问题时就被它坑过一次）。

## 五、手机版前端 `mobile/index.html`（全量重写，约 620 行）

结构：`header`（brand + 三语按钮 + 联网指示灯 + **`#authBtn` 登录/退出** + 当前用户）→ 玩法/出行人数两个下拉 → `#turns` 对话区 → 底部工具条（附近景点 / 安装包 / 添加到主屏幕 / 清空）+ 输入框 → 登录弹窗（用户名 / 密码 / 登录 / 注册新账号 / 取消）→ toast。

- `UI_STR` 三语字典覆盖全部文案，**登录按钮 `S.logged ? T("logout") : T("login")`**，切语言即时变「登录 / 로그인 / Log in」或「退出 / 로그아웃 / Log out」。
- `META_LABELS` 三语映射 4 个玩法 + 6 个出行人数；`CHIPS` 三语各 5 条快捷问题；`applyLangUI()` 统一切文案，并**重填两个下拉**（此前切语言后下拉仍显示中文「自动 / 全部」）。
- `setLang()` 落 `localStorage['busan-lang']`，切语言后 `regenerateAll()` 用最后一问重新生成；玩法/人数下拉变更同样落 localStorage 并重算。
- `renderTurn()` 打标（已联网 / 本地 / 精简 / 官网 N 条 + 景点名）、`mdLite()` 轻量 Markdown、来源块把 http 详情渲染成链接、追问渲染成 chip。
- 本段新增 `stripTail(t, data)`：LLM 草稿末尾自带「资料来源 / Sources / 출처」「其它玩法补充推荐 / Other-theme recommendations」清单，而前端已用结构化块单独渲染，正则切掉避免同一份来源出现两遍（只在该类结构化块确实存在时切补充推荐，避免误删正文）。
- 附近卡片四个按钮：**NAVER 导航**（绿色 `#03c75a`，`nmap://route/public`）、**NAVER 地点**（`nmap://place`）、**网页地图**、**Google**。
- 定位体验：geolocation 超时由 12s 收到 **8s**、`maximumAge=60000`，避免权限弹窗未处理时界面一直卡在「正在定位…」；另加 `?lat=&lng=` 预览入口（无定位权限也能按坐标查看附近景点，同时是本轮的验收手段）。

## 六、运行逻辑图（新增交付物）

- `Busan/docs/run_logic.html`：1360 宽的自包含页面，五个分区 —— ①三个入口 ②登录·会话·语言 ③一次问答的完整链路（STEP 01–05）+ 两条分支（只给景点名→精简 / 未登录→本地兜底）④数据来源（本地库 / 官网 / 日志）⑤手机版定位与 NAVER 深链。
- `Busan/docs/run_logic.png`：用 Edge 无头模式 `--headless=new --window-size=1360,1660` 渲染，1360×1660，已逐项目检（无截断、无错字、无重叠）。

## 七、桌面版 `main_app.py`

`answer_question()` 里 `rag_core.answer(...)` 补 `online=True` 显式传参并加注释：桌面版必须先经 `login.py` 登录才进主窗口，等价「登录后才联网」。

## 八、验证清单（本轮已执行）

### 1. `rag_core` 自测（`python rag_core.py`，约 2 分钟，后台任务取回）

| 用例 | 结果 |
|------|------|
| `甘川文化村` online=True | `concise=True`、`online_out=True`、`web=2~3`，回答 200 字内且末尾带官网链接 |
| `甘川文化村` online=False | `offline=True`、`web=0` |
| `甘川文化村 交通` online=True | `field=None`、`concise=False` |
| `没云台` online=True | `web=3` |
| `감천문화마을 개방시간` online=True | `field=hours`、`web=2` |

### 2. 手机版端到端测试（`%TEMP%\busan_mobile_test.py`，服务 `python mobile_app.py 8011`）

20 项全 PASS，摘录：

```
PASS 未登录 /api/me -> False
PASS 未登录问答不联网（online=False, web_count=0）
PASS admin 登录 -> True，下发 Cookie busan_sid
PASS 登录后联网 web_count=2
PASS 只输景点名 -> 精简回答（concise=True）
PASS sources 含 official 类型
PASS zh / ko / en 三语提问均正确命中 spot=没云台
PASS /api/nearby 返回 8 条，每条都有 nmap://route/public 与 nmap://place
PASS 最近：甘川文化村 0.0 km
PASS 首页含登录按钮与三语文案
PASS 退出 /api/logout ok
PASS 注册新账号 role=user
PASS query_logs 已记录 20 条手机端查询
```

### 3. 浏览器视觉验收（`computer_use_tool` plane="bu"，视口 498×654）

| 场景 | 结论 |
|------|------|
| 中文首屏 | 登录按钮「登录」、状态「本地模式」、「未登录 · 本地资料库」 |
| 英文首屏 | `Log in` / `Local mode` / `Not logged in · local database`，下拉也已变 `Auto / all` |
| 登录弹窗（英文） | `Log in / Username / Password / Cancel / Log in / Create account (same account as desktop)` |
| 登录后 | 指示灯 `Online`、按钮 `Log out`、`admin · admin`、`登录成功，已开启联网` |
| 中文提问「甘川文化村」 | 标签「已联网 / 精简 / 官网 2 条」，正文 200 字内，来源含 `saha.go.kr…mId=0101010000` 与 `gamcheon.or.kr`，**正文与结构化来源不再重复** |
| 附近景点（坐标预览 `?lat=35.0972&lng=128.9769`） | 卡片正常：甘川文化村 `0 km` + `NAVER 导航`（绿）/`NAVER 地点`/`网页地图`/`Google` |

### 4. 运行逻辑图

- Edge 无头渲染成功，PNG 375 KB；打开逐项核对：五个分区完整、文字无溢出、底部页脚在画幅内。

## 九、已知限制（如实记录）

1. **桌面 tkinter 版未启动实测**：`main_app.py` 只改了 `online=True` 一行，未跑 `python main_app.py` 走登录→问答；该分支的联网行为与手机版同源（都进 `rag_core.answer(online=True)`），但「窗口层面」未验证。
2. **手机版会话是内存态**：服务进程一重启，`busan_sid` 全失效，需要重新登录（本轮浏览器验收时就复现过一次）。要长期在线需换持久 token 或落库，用户尚未表态。
3. **安卓 APK 未同步本轮能力**：`dist/Busan旅行助手.apk` 仍是离线版（刻意无 INTERNET），登录 / 联网 / NAVER 深链都只在网页版可用。
4. **浏览器定位权限弹窗未做自动化点击**：自动化环境里 `geolocation` 停在授权提示，因此「点按钮→授权→出卡片」这条链路是**用 `?lat=&lng=` 预览入口验证卡片渲染 + 用接口测试验证数据**，没有真的点过一次系统弹窗。
5. **没云台坐标未经 NAVER 精校**：仍为入库值 `35.0510, 128.8820`，`SPOTS_GEO` 全部 8 点均为档案/手工值。
6. **两个景点确实没有独立官网**（洛东江河口生态中心、峨嵋山观景台），回答里靠 `OFFICIAL[...]["note"]` 说明「以所属区厅汇总页代替」，实际呈现只在来源块里体现。
7. **非中文 + 离线时正文仍是中文**：这是既有设计（离线不做在线翻译），页脚已明示；只有登录联网才会得到完整外语正文。
8. **旧版 Service Worker 缓存**：v3 时代打开过页面的设备，第一次刷新仍可能读到旧 HTML，需要再刷一次（v4 起改为导航网络优先，之后不会再犯）。
9. **多大浦喷泉与多大浦海水浴场的别名仍互相包含**（`Dadaepo Beach` / `다대포해수욕장`），靠玩法域消歧，属有意保守。
10. 历史遗留未动：`Busan/mian_app.py`（拼写残留空壳）、`Busan/build.yml`（失效 Kivy workflow）、`Busan/busan-ai-assistant`（空目录）。

## 十、下一步建议

1. 桌面版实跑一遍登录→问答，确认 `online=True` 在 tkinter 线程里不卡 UI（LLM 单次可能 20–40s，需要 thinking 态）。
2. 会话改持久化（token 或 `sessions` 表），避免服务重启掉登录。
3. 是否把登录 / 联网 / NAVER 深链同步进 APK：需要给壳加 INTERNET 权限并改走在线接口，属新形态，需用户拍板。
4. 用 NAVER 地图精校 8 个景点坐标（尤其没云台、长林浦口），把 `SPOTS_GEO` 换成实测值。

## 十一、本轮改动文件

| 文件 | 类型 | 说明 |
|------|------|------|
| `Busan/official_sites.py` | 新增 | 8 景点官方入口登记 + 抓取 + 10 分钟缓存 |
| `Busan/web_lookup.py` | 修改 | 403 预热、`_SKIP_HOSTS`、`Accept-Language` 坑注释 |
| `Busan/rag_core.py` | 修改 | `online` / `concise` / 官网段 / `_trim_field` / `_concise_local` / `find_spot_global` / 翻译兜底 / 离线页脚措辞 |
| `Busan/intent_parser.py` | 修改 | `_hit_count` 英文整词匹配 |
| `Busan/i18n.py` | 修改 | 新增 `source_official`、`online_mode`、`label_transport`、`label_ticket_hours`、`ask_more`、`login_required_online` |
| `Busan/mobile_app.py` | 重写 | 会话 / 登录注册 / 联网问答 / 附近深链 / SW v4 |
| `Busan/mobile/index.html` | 重写 | 手机版 UI、登录弹窗、三语、去重、附近卡片、坐标预览 |
| `Busan/main_app.py` | 修改 | 问答显式 `online=True` |
| `Busan/docs/run_logic.html` | 新增 | 运行逻辑图源文件 |
| `Busan/docs/run_logic.png` | 新增 | 运行逻辑图成品（1360×1660） |
| `Busan/logs/changelog_2026-11-05_mobile_online_login.md` | 新增 | 本文件 |

> `Busan/busan_travel.db` 按惯例不入库（`.gitignore` 含 `*.db`）；`AI团队作业/`、`apk_build/` 下的截图与临时文件、`mobile_std*.log`、仓库根 `ci.txt`/`h*/push_*.txt` 均为本地调试产物，同样不提交。
