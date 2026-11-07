# 手机版 v1.4：联网 / 离线分界改由手机决定，UI 与回答一起收口

- 日期：2026-11-08
- 版本：Android `versionCode 5` / `versionName 1.4`（上一版 4 / 1.3）
- 仓库：`https://github.com/luohaisheng814/AI_Project_2026_2.git`（分支 `main`）
- 本轮代码提交：`d7dd440`（`feat(mobile): v1.3 云端直连 —— 联网/离线改由手机网络状态决定，回答只依赖云端库与景点官网`）
- 本轮文档 / 安装包 / 压缩包：随 `logs/`、`docs/mobile_run_logic.*`、`dist/` 一起提交，见文末「本轮改动文件」

## 一、这轮改的是什么口径

第 3 轮用户已经把分界讲清楚了，这轮继续按同一口径收口，不再保留「填电脑地址 + 同 Wi-Fi + 电脑跑服务」的旧路径：

> 联网与离线的分界线是手机本身允不允许软件访问手机所连接的网络以及手机本身联不联网，联网版的回答可以不依赖本电脑，只依赖云端数据库和景点网站进行回答。

落到代码里就是两条判定，两个都要满足才算「联网」：

1. `ConnectivityManager` 当前网络具备 `NET_CAPABILITY_INTERNET`（系统允许本 App 访问所连网络）；
2. 该网络还具备 `NET_CAPABILITY_VALIDATED`（系统实测能出网）。

任何一条不满足 → `netAllowed()` 返回 false → 直接离线，不发出任何网络请求。允许联网但云端库两个 endpoint 都取不到 → 也算离线（`reason="cloudFail"`），顶部状态条会说明原因并给「重试」。

`setup.html` 已删除，`MainActivity` 启动即 `loadUrl("file:///android_asset/index.html")`，App 不再需要知道任何电脑地址。

## 二、云端回答从哪来

- 云端数据库：`Busan/mobile/cloud/spots.json`（55,724 B，`schema 2`，`updated_at 2026-11-08`，8 个景点的中/韩/英档案 + 别名 + 坐标 + 官网 `url/mId/host`）。App 联网时直接读 GitHub raw，已验证 HTTP 200。
- 景点官方网站：沙下区 `https://www.saha.go.kr/tour/contents.do?mId=<mId>`、甘川 `https://www.gamcheon.or.kr/` 等；抓正文锚点 `id="conts"`，取前 12 行，记录抓取时间，按 `spot.id` 缓存。`saha.go.kr` 带 `Referer`，`Accept-Language: ko-KR,ko;q=0.9,en;q=0.6`。
- 组装规则：同一套 `compose()` 按意图取字段（交通 / 门票 / 开放时间 / 拍照点 / 概览），正文压到 3–5 条；只输入景点名时走精简版（概览 3 条以内 + 2 条看点 + 一句「想看交通/门票/开放时间点追问」）。官网正文不进主答案，单独放在「官网核对」区块里，失败就标「未取到正文」。

离线不再降级版式：包内 `cloud_snapshot.js` 把同一份 JSON 同步挂到 `window.BUSAN_CLOUD_SNAPSHOT`（避开 `file://` 下 `fetch` 被拒），`useSnapshot()` 塞进同一 `db` 后仍走 `compose()`，只把徽章换成「离线 · 包内数据」。附近景点、直线距离、NAVER 深链在离线也能用。

## 三、UI 这轮改了什么

- 顶部：三语按钮 + 状态点（绿=联网 / 橙=离线，取数时 pulse）+「重试」；状态条文案统一由 `applyUI()` / `paintStatus()` 渲染，不再出现上下两条重复提示。
- 头部标题允许换行，英文长标题不再被裁成 `Busan AI Travel A…`；「重试 / 附近 / 发送」三个按钮加 `flex:0 0 auto; white-space:nowrap`，修掉窄屏下竖排成「附\n近」的问题。
- 两个 chip 行：玩法 / 出行，首项「自动」；类别标签去掉 `01_` 这类前缀噪音，直接显示「艺术村落·文化街区」「海岸休闲·日落夜景」。
- 回答气泡：状态徽章移到气泡顶部（不再挤在正文最后一行）；轻量 markdown（`###` / `**` / `---` / `- `）；来源行按语言本地化（`云端数据库 spots.json（日期）` / `Cloud DB spots.json (date)` / `클라우드 DB spots.json (date)`）。
- 官网核对块：`官网核对 · 官网原文（韩文） · 抓取时间 23:26`，正文清洗掉 `id="conts">` 这类标签残片；未取到时显示「核对中」占位，不假装读过。
- 附近景点：前 2 个带「推荐」徽章 + 公里数 + 四个按钮（导航 / 地点 / 网页地图 / Google），其余折叠进「其余 N 个（点开看）」；定位被拒或超时会给 3 个已收录景点当起点，点一下即算距离。
- 追问 chip 在空结果时隐藏；加载气泡带脉冲省略号。

## 四、本轮实测（雷电模拟器 index 0，1440×2560 / density 640）

| 截图 | 场景 | 结论 |
|---|---|---|
| `apk_build/apk30.png` | 首启，云端库未发布（404） | 橙点 +「云端数据库暂时取不到，已切到包内最近快照。」+ 重试；暴露出底栏按钮竖排 |
| `apk_build/apk31.png` | 修底栏布局后 | 「附近 / 发送」横排；提示只剩顶部一条，底部为通用说明 |
| `apk_build/apk32.png` | 离线旧引擎回答 | 版式旧、带「其它玩法补充推荐（主推荐之后）」与裸 URL，促成本轮改用 `C.answer()` |
| `apk_build/apk33.png` | 离线走 `C.answer()` | 甘川交通 4 条要点 + 橙徽章「离线 · 包内数据」+ 4 个短追问 |
| `apk_build/apk34.png` | 定位到甘川后点「附近」 | 甘川 0.0 公里（推荐）+ 洛东江 1.3 公里 +「其余 2 个（点开看）」+ 四按钮 |
| `apk_build/apk35.png` | 云端库发布会话 | 绿点「联网 · 云端库 · 2026-11-08 · 官网实时」，chip 已去序号 |
| `apk_build/apk36.png` | 联网点「甘川文化村 交通」 | 与离线同结构的 4 条要点，徽章变为「联网 · 云端库」 |
| `apk_build/apk37.png` | 联网滚到回答底部 | 来源行 + 「官网核对」块，抓到沙下区韩文原文（位置 / 电话 / 主页） |
| `apk_build/apk38.png` | 清洗正文后复测 | 官网块首行不再是 `id="conts">`；来源行只留 `官网 saha.go.kr` |
| `apk_build/apk41.png` | 新安装包首启 | 联网状态、底栏横排、离线提示条正常 |
| `apk_build/apk42_ko.png` | 切韩文 | 全站韩文、状态「온라인 · 클라우드 · 2026-11-08 · 공식 사이트…」，暴露出「다시 시도」竖排 |
| `apk_build/apk43_en.png` | 切英文 | 英文首屏，标题被裁成 `Busan AI Travel A…`（本版已修） |
| `apk_build/apk44_en.png` | 标题允许换行后 | 英文标题两行完整显示，`Retry` 单行 |
| `apk_build/apk45_ko.png` | 韩文复测 | 「다시 시도」单行，状态条尾部省略号正常 |
| `apk_build/apk46.png` | 中文联网回答 | 徽章位于气泡顶部，标题 + 交通要点结构稳定 |
| `apk_build/apk47_concise.png` | 英文 `Gamcheon` | 命中景点，但概览偏长、来源行仍是中文（本版已修） |
| `apk_build/apk48.png` | 修来源行语言后 | `Cloud DB spots.json (2026-11-08) · Official site saha.go.kr` |
| `apk_build/apk49.png` | 概览压到 3 条 | 不再出现整段地址/电话堆叠，无「Other themes」尾块 |

其它命令级验证：

- 云端库 raw：`https://raw.githubusercontent.com/luohaisheng814/AI_Project_2026_2/main/Busan/mobile/cloud/spots.json` → HTTP 200，55,724 B。
- APK 安装：`adb -s 127.0.0.1:5555 install -r …` 先报 `Incremental installation not allowed`，随后 `Performing Streamed Install / Success`，属雷电的已知提示。
- 定位：`ldconsole locate --index 0 --LLI "128.9769,35.0972"` 后「附近」返回甘川 0.0 km / 洛东江 1.3 km，与坐标表一致。
- JS 语法：`node --check android/assets/cloud.js` 通过。

## 五、已知限制（如实记录）

1. APK 内没有大模型成稿链路。联网回答是「云端库字段 + 官网上文摘要」的规则组装，不是 LLM 生成；官网正文抽取是锚点启发式（`id="conts"` + 前 12 行），版式改版可能抽不到。
2. 官网只覆盖已录入 `mId` 的景点（沙下区 8 条 + 甘川官网）；其它区、其它景点没有官网入口时只给云端库内容。
3. 云端数据库是 GitHub raw，靠公网直读；GitHub 被墙/断网就落到包内快照，不会自动重试到别的镜像。
4. 「手机不给网络权限」这一分支（`netAllowed=false`）只做了代码走查，没有截图：本轮用飞行模式模拟时切断了 adb（`127.0.0.1:5555` 变 offline），模拟器只能稳定复现「有网但云端库取不到」这一条。
5. 验证只在雷电模拟器完成，**两名真人手机的对比测试仍未做**；真机厂商 ROM 对 `NET_CAPABILITY_VALIDATED` 的判定可能有差异。
6. 没云台观景台的坐标仍未精校（沿用 `35.0620/128.8980`），附近距离只能当量级参考。
7. 登录按钮在删除 `setup.html` 时一并移除（v1.3 起无登录）；用户本轮只要求完善 UI，未再提登录，是否恢复待定。
8. 桌面 tkinter 端本轮未改动、未实跑。
9. keystore（`apk_build/keystore/busan-release.jks`，含私钥）维持 gitignore，不入库；APK 用同一把 key 签名，SHA-256 `9d91ed…d33356`。

## 六、验证清单（本轮已执行）

- [x] `python cloud_build.py` 生成三份同内容产物（`mobile/cloud/spots.json`、`assets/cloud_snapshot.json`、`assets/cloud_snapshot.js`）。
- [x] 云端库发布后 raw 地址 HTTP 200（55,724 B）。
- [x] `node --check` 校验 `cloud.js` 与内联脚本。
- [x] `python apk_build/build_apk.py` 重编译 + apksigner 签名，产物落 `dist/Busan旅行助手.apk`。
- [x] 模拟器安装、启动、三语切换、问答、附近、官网抓取、来源行与徽章逐项截图核对（`apk30`–`apk49`）。
- [x] 联网态实测：状态点变绿、云端库读取成功、沙下区官网正文抓到并显示抓取时间。
- [x] 离线态实测（云端库 404 时）：自动落包内快照、橙点 + 原因 + 重试，回答与联网同结构。
- [x] 定位校准后「附近」距离与坐标表一致（0.0 km / 1.3 km）。
- [x] git 逐文件 `add` → `commit` → `push origin main`，`HEAD` 与 `origin/main` 均为 `d7dd440`。
- [ ] 「无网络权限」分支截图（见已知限制 4）。
- [ ] 两名真人手机对比测试（未做）。
- [ ] 真机 ROM 上的 `VALIDATED` 行为验证（未做）。

## 七、本轮改动文件

代码与数据（已随 `d7dd440` 入库）：

- `Busan/cloud_build.py`（新增：生成云端库三份产物）
- `Busan/mobile/cloud/spots.json`（新增：55,724 B 云端数据库）
- `Busan/android/assets/cloud.js`（新增：`window.BusanCloud` 云端引擎）
- `Busan/android/assets/cloud_snapshot.json` / `cloud_snapshot.js`（新增：包内快照两种加载形式）
- `Busan/android/assets/index.html`（重写：无 setup 页，新 UI）
- `Busan/android/assets/setup.html`（删除）
- `Busan/android/java/com/busan/tour/MainActivity.java`（重写：`netAllowed` / `fetchText` / `requestLocation` 三个 JS 接口）
- `Busan/android/AndroidManifest.xml`（v1.3 → v1.4，`versionCode 4 → 5`）
- `Busan/apk_build/build_apk.py`（把 `cloud_snapshot.js` 加入必备 assets 与校验清单）
- `Busan/dist/Busan旅行助手.apk`（重编译签名）

本轮收尾（文档 / 安装包 / 压缩包）：

- `Busan/docs/mobile_run_logic.html` / `.png`（按新分界重绘，v1.4）
- `Busan/logs/changelog_2026-11-08_mobile_v14_cloud_direct.md`（本文件）
- `Busan/dist/Busan_Tour_App.zip`（重新打包，含 `mobile/cloud/` 与 `cloud_build.py`）
- `Busan/dist/Busan旅行助手.apk`（最终构建）

## 八、下一步建议

1. 找两台真机（一台给网络、一台断网/关权限）做一次对比测试，重点看 `VALIDATED` 判定和官网抓取耗时。
2. 把官网正文摘要做得更稳：按 `mId` 存一份「上次成功正文」到包内，抓取失败时显示上次核对时间，而不是只说未取到。
3. 云端库加一个 `updated_at` 变更检测：启动时比对日期，只在变更新时才重新拉取，省流量。
4. 若要恢复登录，把「用户库」与云端库分开，登录只影响个性化，不影响联网/离线判定。
