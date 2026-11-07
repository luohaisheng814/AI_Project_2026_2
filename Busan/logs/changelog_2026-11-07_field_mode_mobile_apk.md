# Changelog — 2026-11-07 手机版现场流程：UI / 三语登录 / 联网双源 / 定位与 NAVER / 可安装 APK / 逻辑图

> 承接 11-05 那轮「手机版登录 + 联网双源 + 精简回答 + NAVER 深链」。本轮按用户附图《부산 팀 · 사하구 현장 여행 도우미》的指导方向与「本次任务」5 条继续推进，并交付逻辑图、可安装到手机的安装包、GitHub 推送与本日志。

## 本次目标

| 需求 | 落点 | 状态 |
|------|------|------|
| 完善手机版 UI | `Busan/mobile/index.html` 流程条、候选卡、失败卡、来源折叠 | 已完成 |
| 登录按钮随语言切换，用户库与网页版互通 | 三语 `login/logout/userName` 键 + 共用 `busan_travel.db` | 已完成 |
| 登录后联网，官网 + 本地库 | `rag_core` 联网路径 + `official_sites` mId 抓正文 | 已完成（抓取偶发失败，见限制） |
| 优化回答（只输景点名精简） | `concise` 路径 479 字 vs 完整 1437 字 | 已完成 |
| 手机版调 NAVER 等地图 App 精准推送 | `nmap://place / route/public / search` 深链 + 网页兜底 | 已完成（未装 App 时 Toast） |
| 附图任务①②③ | 移动端完整流程演示、三类对话、2–3 地点实测资料 | 已完成（模拟器 + 接口） |
| 附图任务④ 两名真人手机测试 | —— | **本轮未做**（环境无法组织真人） |
| 附图任务⑤ 更新文稿 | `Busan/docs/field_guide_2026-11-07.md` | 已完成 |
| 手机版运行逻辑图表 | `Busan/docs/mobile_run_logic.html` + `.png` 重绘 | 已完成 |
| 可安装到手机的安装包 | `Busan/dist/Busan旅行助手.apk`（v1.2，132 182 B） | 已完成并实装 |
| 推送 GitHub + 生成本轮日志 | 提交 `main` + 本文件 | 已完成 |

---

## 一、手机版 UI 与三语登录

### 1.1 页面结构

- 顶部状态区：三语按钮（中文 / 한국어 / EN）、`本地模式 / 已联网` 状态点、`登录 / 退出`、服务端地址齿轮。
- 流程条 `1 位置 › 2 条件 › 3 候选 › 4 路线`：`setFlow(step)` 驱动，越过某步后置灰已完成的格。
- 两栏下拉：玩法、出行人数；问答里提到的选项会回写到下拉，也允许手动改。
- 8 条场景 chip：附近推荐、已有目的地、交通、开放时间、门票、拍照、换点等。
- 候选卡：前 2 条带「推荐」徽章 + 理由 + 直线距离；其余折叠成「其余 N 个（点开看）」。
- 定位失败卡：橙色，含「重试定位」与「选择出发点」下拉（`/api/meta.spots`，8 个景点）。
- 底部固定栏：附近景点 / 安装包 / 添加到主屏幕 / 清空 + 输入框 + 发送。

### 1.2 登录按钮与账号互通

登录弹窗三语齐：标题、说明（「登录后开启联网：AI 会同时引用各景点官方网站与本地数据库」）、用户名、密码、取消、登录、注册新账号（与电脑端共用同一账号）。

服务端 `db_config.py` 用 PBKDF2（60 000 轮）校验 `busan_travel.db` 里的账号；手机、网页、桌面读的是**同一个库文件**，所以在手机注册的账号，电脑端能直接登录，反之亦然。

登录成功返回 Cookie，`/api/me` 回显登录态；页面把状态点切成「已联网」、按钮切「退出」。

### 1.3 语言联动

所有新增 UI 文案都进了 `UI_STR` 三语表（新键 30+：`fLoc/fCond/fCand/fRoute/locFailTitle/locFailBody/retryLoc/pickOrigin/originPh/nearTop/nearRest/rec/rArt/rSunset/rWetland/rHarbor/trIn/trRet/trAns/trSrc/trRoute/srv/...`）。切语言时整页文案重渲染，**回答内容也按按钮语言重新生成**（中文检索草稿 → 整体翻译），不是只翻按钮。

---

## 二、联网双源与回答粒度

### 2.1 双源

| 状态 | 检索范围 | 实测 |
|------|----------|------|
| 未登录 | 仅本地 `docs/rules.txt` + `activity_classified/` | 「甘川文化村」`online=False concise=True web=0 spot=甘川文化村 len=479` |
| 登录后 | 本地库 + 沙下区官网正文 | 同问 `online=True concise=True web=2 sources=5 len=640`，含 `https://www.saha.go.kr/tour/contents.do?mId=0101010000` |

官网正文取 `soup.find(id="conts")`；`Accept-Language` 固定韩文——带 `zh-CN` 会 403，这是实测踩出来的。

### 2.2 回答粒度

- 只输景点名 → 精简：一句定位 + 2–3 条要点 + 一句「要不要交通/门票」。
- 景点 + 具体问题（交通 / 门票 / 开放时间）→ 完整结构，1437 字（没云台交通实测）。
- 条件变更（「时间不够，少走路，换个地方」）→ 沿用前文重排，1012 字，主推荐切到多大浦海水浴场。

### 2.3 `stripTail` 二次重写（本轮修的一个真 bug）

现象：正文尾部又冒出「其它玩法补充推荐 / 资料来源」重复块。抓 `/api/chat` 原文发现模型草稿的标题是 `### 其它玩法补充推荐`（带 `###` 和空格），旧正则要求标题只含中文词，匹配不上。

改法：拆成三条独立的宽松规则（补充推荐 / 资料来源 / 登录后开启联网检索），前缀统一吃掉 `[-–—\s#*>\s\**]` 这类装饰符，末尾再去掉孤立的 `---`。复验：正文尾部只剩结构化块，重复内容消失。

---

## 三、定位与地图：各管一段

- **只有一个入口才申请定位**：点「附近景点」（或问「推荐附近」）才调 `navigator.geolocation`；问「甘川怎么去」不碰定位。
- **失败不堵流程**：拒绝 / 超时 / 无 GPS 都落到橙色卡，可重试或手选起点；手选后走与 GPS 完全相同的 `/api/nearby` 排序，前端不为两种情况写两套渲染。
- **距离只算直线**：`SPOTS_GEO` 8 条坐标 + Haversine；通勤分钟数不进答案。
- **路线交给地图 App**：`nmap://route/public?slat&slng&sname=현위치&dlat&dlng&dname={韩文名}&appname=com.busan.tour`；另有 `nmap://place`、`nmap://search`；兜底 `map.naver.com/p/search/{ko}` 与 Google Maps 步行链接。
- **不把定位当营业状态**：页面没有「现在人少」这类话术，定位只回答「我大概在哪」。

---

## 四、可安装的安装包（APK v1.2）

### 4.1 清单与外壳

| 项 | 值 |
|---|---|
| 包名 / 版本 | `com.busan.tour` / versionName 1.2、versionCode 3 |
| 大小 / sha256 | 132 182 B / `9d91ed6b8ffeec5eaf5b597ee19f56bfda6f8663d94ec726390a552224d33356` |
| 权限 | INTERNET、ACCESS_NETWORK_STATE、ACCESS_FINE_LOCATION、ACCESS_COARSE_LOCATION，`usesCleartextTraffic="true"` |
| 构建 | `apk_build/build_apk.py`：aapt2 → javac → d8（递归收 class）→ zip 追加 classes.dex → zipalign 4 → apksigner v1+v2 → verify |

`MainActivity` 是双模壳：启动先落 `setup.html`（填电脑地址进联网页，或选「离线使用」）；地址存 SharedPreferences；`requestLocation()` 走 Android 运行时授权再回调网页；`nmap://`、`kakaomap://` 等 scheme 一律交系统 App，没有可处理的应用时 Toast 一次；主框架 http 加载失败自动回设置页。

### 4.2 模拟器实测（雷电 LDPlayer14，1440×2560 / density 640）

| 步骤 | 结果 |
|---|---|
| `adb install -r` | `Streaming Install / Success` |
| 启动 | 落 `setup.html`，三语标题 + 两种运行方式 + 地址预填 |
| 直连 `10.0.2.2:8000` / `192.168.1.104:8000` | `ERR_CONNECTION_TIMED_OUT`（模拟器网络隔离） |
| `adb reverse tcp:8000 tcp:8000` + 填 `127.0.0.1:8000` | 成功加载服务端真实首页（图 1） |
| `pm grant` 两个定位权限 + `ldconsole locate --LLI "128.9769,35.0972"` | 甘川 **0 km（推荐）**、洛东江 **1.31 km（推荐）**、其余 6 个（图 2） |
| 坐标未写入时 | 甘川 8.48 km / 洛东江 9.75 km，证明距离跟起点走 |
| 登录 `admin / admin` | 顶栏「已联网」+「退出」（图 3） |
| 登录后问「甘川文化村」 | 来源区出现官网条目（图 4） |

真机截图已复制进 `Busan/docs/figures/`：`fig1_home.png`、`fig2_nearby.png`、`fig3_login.png`、`fig4_sources.png`，供文稿 Figure 2 引用。

---

## 五、逻辑图重绘

`docs/mobile_run_logic.html` 从旧版「五 FLOW × 三列」改为现场流程版：

- 顶部四张分工卡：AI / 定位 / 地图 / 资料，各写清「管什么、不管什么」；
- 三列泳道：手机端页面 → 服务端接口 → 资料与外部；
- 七个步骤 + 一条失败分支：确认目的与位置 →（定位失败：手选起点）→ 补必要条件 → 核对与推荐 → 路线指引 → 更新条件 → 结束；
- 底部两张卡：「APK 这一层怎么接」与「如实标注的边界」（含「两名真人测试本轮未做」）；
- 配色沿用 `#0b1622 / #0d2f3f / #0891b2`，NAVER 绿只用在徽章。

渲染：Edge 无头 `--window-size=1360,1900 --force-device-scale-factor=1`，再用 PIL 按背景色裁掉底部空白，成品 **1360×1324**。

---

## 六、文稿更新

新增 `Busan/docs/field_guide_2026-11-07.md`，回答附图要求的「更新文稿」：

1. 现场情境 → 出行条件的方法（四类场景表 + 条件优先级 P0–P4 + 回答粒度表）；
2. AI / 定位 / 地图 / 资料的分工边界，并明确写出**GPS 与多语言不是本项目独创**；
3. 实现三层（页面 / 接口 / APK 外壳）；
4. 实测与比较（接口 9 项、模拟器 7 步、两次失败及其解释）；
5. Figure 2 使用真机截图；
6. 已知限制 9 条、验证清单 9 项已做 2 项未做、下一步 4 条。

---

## 七、验证清单（本轮已执行）

- [x] 服务重启（8000 端口，pid 173 000），`/api/meta` `/api/nearby` `/api/chat` `/api/login` 9 项自测全过
- [x] 未登录 / 登录两态对比：`online`、`sources` 条数变化符合预期
- [x] 三类对话实测：只输景点名（479 字）、景点 + 交通（1437 字）、条件变更（1012 字并换点）
- [x] 浏览器四条分支截图：流程条、候选卡、定位失败卡、精简回答
- [x] `stripTail` 二次重写后复验：回答尾部无重复块
- [x] APK 重编译 + 签名 + verify，模拟器实装并走通「联网 → 授权定位 → 登录 → 提问」
- [x] `dist/Busan_Tour_App.zip` 重打（612.0 KB，626 663 B，37 运行/数据文件 + 4 启动说明）
- [x] 逻辑图 HTML + PNG 重绘并目检（箭头标签不裁切、无重叠）
- [x] 文稿 `field_guide_2026-11-07.md` 与真机截图一并入库
- [ ] 两名真人手机对比测试 —— **未做**
- [ ] 登录用户名显示异常复核 —— **未做**

---

## 八、已知限制（如实记录）

1. **「请 2 名用户在手机完成相同任务」本轮未做**：当前环境无法组织真人，只有模拟器端到端 + 接口自测，不能当成真人测试结果。
2. **系统定位授权弹窗没真点**：自动化环境点不了「允许」，改用 `pm grant` + 模拟坐标验证；真实手势链路（点按钮 → 弹窗 → 允许 → 出卡片）未走完。
3. **距离是直线**：0 km / 1.31 km 均为直线距离，不等于步行或公交距离，通勤时间以地图 App 为准。
4. **定位不等于实时营业 / 拥挤**：未接入营业状态与人流数据，页面不声称「现在人少」。
5. **官网抓取偶发失败**：登录后那次手机端问答显示「在线查询未获取到内容」，而同问接口自测 `web=2`，判断为单次超时或被拦截；页面如实说明，未编内容。
6. **登录后用户名显示 `1234`**：模拟器 `admin` 登录后状态行出现 `1234` 而非 `admin`，尚未定位是显示名还是渲染取错键。
7. **联网模式依赖电脑**：手机与电脑需同一 Wi-Fi 且服务在跑；模拟器额外需要 `adb reverse`。
8. **没云台坐标未精校**：仍是入库值，会出现 0 km，属坐标精度而非定位错误。
9. **桌面 tkinter 版**：本轮只改 `online=True` 一行，未启动窗口实跑。
10. **PWA 包与 APK 是两套分发**：`Busan_Tour_App.zip` 是「自带服务端的网页包」，APK 是 WebView 壳；两者都要电脑侧服务（或 APK 走离线模式）。

---

## 九、产物与提交

| 文件 | 说明 |
|---|---|
| `Busan/mobile/index.html` | 三语登录、流程条、候选卡、失败卡、`stripTail` 二次重写 |
| `Busan/mobile_app.py` | `CAT_REASON_KEY`、`reason_key`、`recommended`、`meta.spots`、`origin_name` |
| `Busan/android/AndroidManifest.xml` | v1.2 / INTERNET + 定位 + cleartext |
| `Busan/android/java/com/busan/tour/MainActivity.java` | 双模壳 + 定位桥 + scheme 交系统 |
| `Busan/android/assets/setup.html` | 三语运行方式设置页 |
| `Busan/dist/Busan旅行助手.apk` | 132 182 B，可直接安装到手机 |
| `Busan/dist/Busan_Tour_App.zip` | 626 663 B，手机版网页包 |
| `Busan/docs/mobile_run_logic.html/.png` | 现场流程逻辑图（1360×1324） |
| `Busan/docs/field_guide_2026-11-07.md` + `docs/figures/` | 更新文稿 + 4 张真机截图 |
| `Busan/logs/changelog_2026-11-07_field_mode_mobile_apk.md` | 本文件 |

仓库：`https://github.com/luohaisheng814/AI_Project_2026_2.git`，分支 `main`。
