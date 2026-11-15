# 手机版 v1.6：三语账户入口、单链接来源与条件化问答

- 日期：2026-11-15
- 版本：Android `versionCode 7` / `versionName 1.6`（上一版 6 / 1.5）
- 仓库：`https://github.com/luohaisheng814/AI_Project_2026_2.git`（分支 `main`）
- 本轮代码提交：`0551844`（`feat(mobile): v1.6 三语账户入口与条件化问答 —— 登录按钮/弹层随中韩英切换、来源收为单链接、按同行与行动限制给针对性推荐，重打APK与分发包`）
- 安装包：`Busan/dist/Busan旅行助手.apk`（226,716 B，v1.6）
- 分发包：`Busan/dist/Busan_Tour_App.zip`（2,593,934 B，已换入 v1.6 APK）
- APK SHA-256：`59174C1F1F083BC39938BF17505AA4A2E42113C840FED5B57D3FCF0D66D55987`
- zip SHA-256：`342564B77DE64BCAE24B6816DC07D17B2A7E4CF3A1CF9660FCA656A954CFC4E8`
- 签名：SHA-256 `9d91ed6b8ffeec5eaf5b597ee19f56bfda6f8663d94ec726390a552224d33356`；SHA-1 `0a5cecc7cbc9c70ca60c6b16b918017276cf97de`

## 一、这轮只做三件事

v1.5 已经把账户、会话、网络、定位、核心词库与本地推演做完。v1.6 不再重做这些，只收口三个用户能直接看到的缺口：

1. **顶部登录按钮跟随中文 / 한국어 / English 切换。**
   - 顶部 `#acctBtn` 在未登录时由 `session.js` 的 `paintAccount()` 按当前语言写文案：`登录` / `로그인` / `Sign in`。
   - 新增 `paintAuthText()`，把登录 / 注册弹层的标题、说明、tab、用户名 / 密码 label 与 placeholder、登录 / 注册按钮、游客入口、本机存储说明、账户面板标题 / 保存偏好 / 保存设置 / 测试连接 / 退出登录一并按语言刷新。
   - `BusanAuth` 新增 `refresh()`；`index.html` 的 `applyUI()` 每次语言切换后调用 `BusanAuth.refresh()`，因此按钮和已经打开的弹层都会立即换语言，不需要关掉重开。
   - 已登录时按钮仍显示用户名或显示名，不因语言切换被覆盖。

2. **回答的信息来源只保留一个简写链接。**
   - `cloud.js` 新增 `sourceUrlFor(s)`：优先 `s.official.url`；没有时从当前语言的 `fields.source` 正则取第一个 `http(s)`；仍然没有时回退 `https://www.saha.go.kr/tour/`。
   - 景点问答 `compose()` 改为返回 `sourceUrl`，不再返回多个 `sources` 标签；`BusanCloud` 公开 `sourceUrl()`，供附近结果复用。
   - `index.html` 的 `paintBubble()` 优先渲染 `result.sourceUrl`，显示为 `资料来源 · saha.go.kr ↗` 的单个可点击链接，完整 URL 放在 `href`，点击交给系统浏览器打开。
   - `fillOfficial()` 删掉原来在官网区块里重复显示的裸 URL；官网正文仍在，但链接只剩气泡底部这一条。
   - `planner.js` 的本地推演和 LLM 重排结果、`app.js` 的离线兜底、`index.html` 的附近结果都补了 `sourceUrl`，避免不同入口的来源样式不一致。

3. **具体景点问题不再只返回一个字段，而是结合景点数据做针对性判断。**
   - `cloud.js` 新增 `contextOf(q)`：从问题中抽孩子 / 婴儿车 / 轮椅 / 少走路 / 拍照 / 日落 / 上午 / 免费 / 安静 / 咖啡 / 艺术 / 湿地 / 半天等条件。
   - 新增 `fitLines(s, c)`：把景点 `plan.walk_level`、`family_score`、`photo_score`、`best_time`、`duration_min/max`、`note`、`ticket`、`tips`、`vibes` 与实时定位距离拼成最多 3 条“针对你的情况”的判断。例如甘川文化村 + 轮椅会直接提示“步行强度 4/5，坡道/阶梯多；轮椅不建议把这里当主行程”。
   - 新增 `alternativeFor(s, c)`：当行动限制、亲子或日落条件与当前景点明显不匹配时，从其它景点按 `(5 - walk_level)`、`family_score`、`best_time` 打分，只补一个更贴合的点，并说明是步行强度、家庭评分还是最佳时段更合适。
   - `intent=overview` 且不是只点景点名时，新增“怎么安排”段：建议停留 2–3 小时、步行强度、最佳时段、拍照 / 亲子评分、室内 / 户外，以及数据里的 `plan.note`；这样“甘川文化村怎么玩”这类问题也会综合时长、体力和时段，而不是只抄概览。
   - 针对性段排在“其它玩法补充推荐”之前，替代点如果已经出现在补充推荐里会被过滤，避免同一个景点重复出现。

## 二、三语对照文案

| 位置 | 中文 | 한국어 | English |
|---|---|---|---|
| 顶部未登录按钮 | 登录 | 로그인 | Sign in |
| 弹层标题 | 登录 / 注册 | 로그인 / 회원가입 | Sign in / Register |
| 登录 tab | 登录 | 로그인 | Sign in |
| 注册 tab | 注册 | 회원가입 | Register |
| 注册提交 | 注册并登录 | 가입 후 로그인 | Register & sign in |
| 游客入口 | 先以游客身份使用 | 비로그인으로 사용 | Continue as guest |
| 账户面板 | 账户与偏好 | 계정과 취향 | Account & preferences |
| 退出 | 退出登录 | 로그아웃 | Sign out |

未登录的欢迎语、顶部标题、玩法 / 出行标签、定位条、底栏仍沿用 v1.5 的 `applyUI()` 三语逻辑，本轮没有改它们的文案。

## 三、可复现的验证

### 浏览器实测

无头 Chrome，`file:///D:/AI_Project_2026_2/Busan/android/assets/index.html`，通过一次性探针页切换语言并打开弹层；探针页验证后已删除，没有打进 APK。

| 截图 | 场景 | 结论 |
|---|---|---|
| `Busan/apk_build/ui_probe_en.png` | 500×900，切到 English 后点登录 | 顶部按钮为 `Sign in`；弹层标题 `Sign in / Register`，tab、label、placeholder、按钮、游客入口全英文 |
| `Busan/apk_build/ui_probe_ko.png` | 500×900，切到 한국어 后点登录 | 顶部按钮为 `로그인`；弹层标题 `로그인 / 회원가입`，tab 与说明全韩文 |
| `Busan/apk_build/ui_probe_qa.png` | 500×1400，问“甘川文化村 轮椅 怎么去” | 底部只有 `资料来源 · saha.go.kr ↗` 一条链接；正文出现“针对你的情况”步行强度 4/5 与替代点“多大浦梦之夕阳喷泉（步行强度 1/5）” |
| `Busan/apk_build/ui_probe_chrome3.png` | 500×900，中文首屏 | 基线未破：标题、三语 + 登录、玩法 / 出行、规划条、定位条、欢迎气泡、底栏完整 |

### 脚本回归

`node --check` 通过：`cloud.js`、`session.js`、`planner.js`、`app.js`。

临时回归脚本 `Busan/apk_build/test_cloud_round.js` 直接加载 `cloud_snapshot.json` 后调用 `BusanCloud.answer()`，覆盖 6 个中文场景 + 韩文 / 英文各 1 个：

- 只点“甘川文化村”：返回单链接 `https://www.saha.go.kr/tour/contents.do?mId=0101010000`，`sources` 为空。
- “甘川文化村 轮椅 怎么去”：单链接不变；出现轮椅判断与替代点。
- “甘川文化村 带孩子 拍照”：出现家庭评分 3/5、拍照评分 5/5 与家庭评分更高的替代点。
- “峨嵋山观景台 门票”：`official.url` 为空，回退到 `https://www.saha.go.kr/tour/`。
- “乙淑岛候鸟公园 日落 免费”：提示该点不是日落主场景，替代点为多大浦梦之夕阳喷泉；同时保留免费门票判断。
- 韩文 `감천문화마을 휠체어`、英文 `Gamcheon wheelchair`：判断段与替代点均为对应语言；非中文时不再显示只有中文的 `plan.note`。

### 构建验证

- `python apk_build/build_apk.py` 编译、zipalign、apksigner 签名成功。
- `aapt dump badging`：`com.busan.tour`，`versionCode 7`，`versionName 1.6`，`sdkVersion 21`，`targetSdkVersion 34`，`application-label 釜山旅行助手`。
- `apksigner verify --print-certs`：签名证书 SHA-256 与 v1.5 相同，覆盖安装不会因换签名失败。
- APK 内 `assets/index.html` / `cloud.js` / `session.js` 的 SHA-256 前 16 位与源文件一致；APK 内没有 `uitest*.html` 探针残留。
- `python apk_build/make_dist_zip.py` 重建 zip，内含 226,716 B 的 v1.6 APK。

## 四、已知限制（如实记录）

1. **没有做 APK 真机 / 模拟器回归。** 当前 `adb devices` 为空，雷电模拟器未连接；本轮 APK 只做了构建、签名、清单、包内资源哈希验证，三语 UI 与问答是在浏览器 500×900 / 500×1400 下验证的。Android WebView 的字体回退、系统浏览器跳转、软键盘顶起弹层这三项仍需真机确认。
2. **来源简写牺牲了“多源并列”。** 现在每个回答只给一个链接，优先景点官网；如果用户想同时看云端库更新时间、NAVER 地图和多个官网子页，需要再点追问或自己搜索。官网抓取失败时仍显示失败提示，但不再提供第二个备用链接。
3. **“简写”显示的是 host，不是完整 URL。** 界面上是 `saha.go.kr`，完整 URL 只在 `href` 里；如果用户希望直接看到 `https://www.saha.go.kr/tour/contents.do?mId=...`，需要把 `hostOf()` 改成长 URL 截断显示。
4. **无官网 URL 的景点只能回退到沙下区旅游首页。** 峨嵋山观景台当前 `official.url` 为空，`fields.source` 里也没有可提取的 URL，所以链接落在 `https://www.saha.go.kr/tour/`，不是该点的精确页面。
5. **条件识别是规则匹配，不是语义理解。** `contextOf()` 覆盖中 / 韩 / 英的常见说法，但“推着宝宝”“腿脚不太利索”“不想爬坡”这类没有命中关键词的表达不会触发针对性段；LLM 通道也没有接入这套条件抽取，模型只重排候选点。
6. **针对性文案的密度受 3 条上限约束。** 同时出现“轮椅 + 孩子 + 日落 + 免费”时只保留前 3 条最相关的判断，避免气泡过长；用户可能觉得某些条件没有逐条回应。
7. **非中文缺少 `plan.note` 翻译。** 景点数据里的 `note` 只有中文，v1.6 在韩文 / 英文下直接不显示这条，避免中英混排；后续应在 `core_keywords.json` 里补 `note_ko` / `note_en`。
8. **30 天 TTL、断网 toast、真实 LLM Key 仍未端到端复测。** 这三项是 v1.5 的遗留限制，本轮没有改账户 TTL、网络回调或 LLM 客户端逻辑，因此没有重新做拨时间、断网、401 / 超时测试。
9. **本轮没有改桌面 tkinter 端和云端数据。** `spots.json`、`core_keywords.json`、`cloud_snapshot` 均未重建；所有改动只在 Android 网页资源、清单版本号、APK / zip 与日志。

## 五、验证清单

- [x] 顶部未登录按钮随中文 / 韩文 / 英文切换为 `登录` / `로그인` / `Sign in`。
- [x] 登录弹层标题、tab、label、placeholder、提交按钮、游客入口随语言切换。
- [x] 语言切换时已打开的弹层同步刷新，不需要关闭重开。
- [x] 登录态下顶部仍显示用户名，不被语言刷新覆盖。
- [x] 景点问答只渲染一个 `sourceUrl` 链接，文案为 `资料来源 · host ↗`。
- [x] 官网区块不再重复输出裸 URL。
- [x] `official.url` 缺失时能从 `fields.source` 取 URL，再缺时回退沙下区旅游首页。
- [x] `planner.js`、`app.js`、附近结果都带 `sourceUrl`，不再走多标签来源。
- [x] 甘川文化村 + 轮椅出现步行强度 4/5 判断与替代点。
- [x] 甘川文化村 + 孩子 + 拍照出现家庭评分 / 拍照评分判断。
- [x] 乙淑岛 + 日落 + 免费出现“不是日落主场景”判断与多大浦替代点。
- [x] 只点景点名时仍保持 concise，不强行塞入针对性段。
- [x] 韩文 / 英文的条件判断、替代点、括号格式均为对应语言。
- [x] `node --check` 四个改动脚本通过。
- [x] `python apk_build/build_apk.py` 构建、签名成功；`aapt` 版本 1.6 / versionCode 7。
- [x] APK 内资源哈希与源文件一致，无探针页残留。
- [x] dist zip 重建，内含 v1.6 APK。
- [ ] APK 真机 / 模拟器安装与三语点击（未做，见限制 1）。
- [ ] Android WebView 外链跳转系统浏览器（未做，见限制 1）。
- [ ] 30 天 TTL、断网 toast、LLM 真实 200 / 401 / 超时（未做，见限制 8）。

## 六、本轮改动文件

- `Busan/android/AndroidManifest.xml`（versionCode 6 → 7，versionName 1.5 → 1.6）
- `Busan/android/assets/session.js`（`paintAuthText()`、`paintAccount()` 内刷新、`BusanAuth.refresh()`）
- `Busan/android/assets/index.html`（`applyUI()` 调 `BusanAuth.refresh()`；`hostOf()`；单链接 `sourceUrl` 渲染；`fillOfficial()` 去重 URL；附近结果 `sourceUrl`）
- `Busan/android/assets/cloud.js`（`P()`、`contextOf()`、`walkWord()`、`fitLines()`、`alternativeFor()`、`sourceUrlFor()`；`compose()` / `answer()` 接入；`BusanCloud.sourceUrl`）
- `Busan/android/assets/planner.js`（本地推演与 LLM 重排结果补 `sourceUrl`）
- `Busan/android/assets/app.js`（离线兜底补 `sourceUrlOf()`）
- `Busan/dist/Busan旅行助手.apk`（226,716 B，v1.6）
- `Busan/dist/Busan_Tour_App.zip`（2,593,934 B）
- `Busan/apk_build/test_cloud_round.js`（本轮临时回归脚本，未加入 APK）
- `Busan/logs/changelog_2026-11-15_mobile_v16_ui_i18n_source_advice.md`（本文件）

## 七、下一步建议

1. 接回雷电模拟器或真机，补 APK 三语首屏、登录弹层、外链跳转、软键盘四项截图。
2. 给 `core_keywords.json` 的 8 个景点补 `note_ko` / `note_en`，让“怎么安排”段在三语下信息量一致。
3. 把 `contextOf()` 的条件抽取接到 `planner.js`，让“轮椅 / 婴儿车 / 孩子 / 日落”在多站推演里也参与打分，而不仅是单点问答。
4. 若用户希望来源显示完整 URL，可把 `hostOf()` 改为“host + 路径前 18 字符”的截断显示，仍保持单链接。
