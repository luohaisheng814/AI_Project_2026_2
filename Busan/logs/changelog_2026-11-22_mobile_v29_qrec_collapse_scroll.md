# 釜山 AI 旅行助手 · v2.9 手机版更新日志

- 日期：2026-11-22
- 版本：Android `versionCode 22 / versionName 2.9`，iOS `2.9 / 22`，PWA 缓存 `busan-2.9`
- 上一版：v2.8（天气与「附近」统一走定位→天气→本地时间综合推荐）
- 本轮目标：个性化推荐加「收起 / 展开」按钮 + 单行横向滚动，把纵向占地压下来；全量测试；推 GitHub 并出安装包与日志

---

## 一、这一版改了什么

### 1. 个性化推荐从三行变成一条

欢迎语里原来摊着 5 个点子，390px 宽下要换 3 行、约 110px 高，一进来就把首屏占掉一半。v2.9 把它收进一个 `qrec` 组件：

| 状态 | 高度（390×844 实测） | 说明 |
| --- | --- | --- |
| 收起（默认） | **40px**（标题行 38px） | 只剩「个性化推荐 · 5 个点子 · 展开后单行横滑 [展开]」 |
| 展开 | **93px**（正文 45px） | 5 个点子在**同一行**里，左右滑动看 |

也就是说，首屏默认比原来省下约 70px 纵向空间；点开也只占一行的高度。

### 2. 为什么会滑得动

- `.qrec-body .quick` 改 `flex-wrap:nowrap` + `overflow-x:auto`，点子 `flex:0 0 auto`（不被压缩成省略号）。
- 390px 宽实测：可视宽 **286px**，内容宽 **677px** —— 5 个点子确实溢出，必须横滑。
- 加了 `scroll-snap-type:x proximity`（松手吸附到点子边界）、隐藏系统滚动条、`-webkit-overflow-scrolling:touch`（iOS 惯性）。
- 右侧 22px 渐隐（`::after` 渐变色 + `pointer-events:none`），明确提示"右边还有"；夜间渐隐底色跟着换，不会出现一块白边。
- 单个点子最宽 `78vw`，超长自动省略号，避免一个长句把整行挤满。

### 3. 收起 / 展开按钮

- 头部整行都是按钮（38px 高，达到触控下限），右侧胶囊写「展开 / 收起」。
- 摘要位随状态变：收起时「5 个点子 · 展开后单行横滑」，展开时「5 个点子 · 左右滑动看更多」。
- `aria-expanded` 同步，方便读屏；`aria-controls` 指向正文。
- 状态写进 `localStorage.busan_qrec`，下次打开还是上次的样子（默认收起）。
- **点任一个点子会自动收起**，把空间还给对话；同时照旧走原来的问答/天气链路。
- 切语言（中/韩/英）时组件重建但状态不丢：`맞춤 추천 / 5가지 · 좌우로 넘겨 보기 / 접기`。

### 4. 顺手把另外两处也改成单行横滑

- 综合推荐结论卡上的「时间 / 天气 / 距离」三枚胶囊：`flex-wrap:nowrap` + 横滑，窄屏不再折成两行。
- 天气卡里的 8 个手动天气 chip（晴/多云/雨/雪/雾/雷雨/高温/严寒）：原来 3 行，现在 1 行横滑。

### 5. 文案与细节

- 收起态不会让"5 个点子"凭空消失——标题行常驻，摘要明确写了"展开后单行横滑"，用户知道点哪里。
- 展开高度用 `max-height:76px` 封顶（配合 `.26s` 过渡），将来加第 6、7 个点子也不会把首屏撑开。

---

## 二、测试

| 脚本 | 结果 |
| --- | --- |
| `apk_build/test_v29.js`（本轮新增） | **71 / 0** |
| `apk_build/test_v28.js`（版本断言同步 2.9/22） | **103 / 0** |
| `apk_build/test_v27.js` | **50 / 0** |
| `apk_build/test_v26.js` | **74 / 0** |
| `apk_build/test_v25.js` | **63 / 0** |
| `apk_build/test_v23.js` | **50 / 0** |
| `apk_build/test_v22.js` | **43 / 0** |
| `apk_build/test_engine.js` | `✅ 离线引擎全部断言通过` |

`test_v29.js`（71 条）覆盖：

- 结构：`qrec` 容器、`aria-expanded`、三语标题、摘要/动作位、正文里套渐隐层、5 个点子、最后一个仍走天气入口
- 状态机：默认收起、localStorage 读写、`classList.toggle("open")`、`aria-expanded` 同步、三语文案、点点子自动收起（普通点子与天气点子各一条）
- 占地：折叠 `max-height:0`、展开 `max-height:76px`、`.26s` 过渡、标题行 `min-height:38px`
- 横滑：`nowrap` + `overflow-x:auto` + 隐藏滚动条 + 惯性 + `scroll-snap` + 点子不压缩 + `78vw` 上限 + 渐隐层与 `pointer-events:none`
- 配色：夜间推荐条 / 夜间按钮 / 夜间渐隐 / 夜间点子
- 不回退：天气按钮、`#wxCtx`、天气与「附近」的权限卡、`mix.js` 引入与 `ranked`、偏好条折叠、三语按钮、附近按钮、昼夜 19/6、8 个手动天气 chip
- 版本：APK 22/2.9、无 21 残留、UA 2.9、无 2.8 UA、iOS 2.9/22、PWA `busan-2.9`、无 `busan-2.8` 残留、SW 清单含 `mix.js`、PWA 产物 v29

### 真浏览器探针（`_v29probe.py`，390×844，CDP 9232）

```
BOOT     open=false aria=false bodyH=0 boxH=40 headH=38 title=个性化推荐 act=展开 local=null
OPEN     open=true  aria=true  bodyH=45 boxH=93 chips=5 tops=[440,440,440,440,440]
         oneRow=true rowClientW=286 rowScrollW=677 scrollable=true maxChipW=183
SCROLL   maxW=677 clientW=286 after=391          ← 真滑到底了
PICK     甘川文化村 交通 → open=false bots=2 users=1 local="0"
RELOAD   open=false aria=false bodyH=0 act=展开 local="0"   ← 刷新仍保持收起
KO       open=true title=맞춤 추천 act=접기 sum=5가지 · 좌우로 넘겨 보기 chips=5
NIGHT    boxBg=rgb(21,30,38) chipBg=rgb(26,36,45) chipColor=rgb(207,230,239) theme=#072e3c
WX PERM  grant=true tag=综合推荐 · 需要定位权限（权限链路未变）
MIX ROW  chips=3 tops=[49,49,49] oneRow=true choices=3 tag=天气 · 综合推荐
ERRORS   []
```

证据截图（`Busan/apk_build/`）：

| 文件 | 内容 |
| --- | --- |
| `v29_home_collapsed.png` | 默认收起：推荐条只占一行 |
| `v29_qrec_open.png` | 展开：5 个点子同一行，右侧渐隐提示可滑 |
| `v29_qrec_scrolled.png` | 滑到尾部（scrollLeft 391） |
| `v29_qrec_ko.png` | 韩语界面下的同一条 |
| `v29_night_qrec.png` | 夜间配色的推荐条 |
| `v29_mix_row.png` | 综合推荐三枚胶囊也是一行 |
| `v29_online_collapsed.png` / `v29_online_open.png` | 线上 Pages 实拍 |

---

## 三、构建产物

| 产物 | 大小 | SHA-256 |
| --- | --- | --- |
| `Busan/dist/Busan旅行助手.apk` | 10,602,539 B（10.35 MB） | `ABE983F8832477FBAFD82B28131579F1105871F731B1A018B0968ACA42B49DBA` |
| `Busan/dist/Busan_iOS_WebApp_v29.zip` | 10,489,416 B | `BE00A71C175C6E9D30439130EEDA9BF8AFF56DD5805585E83F393702D1BE659B` |

APK 校验：

- `aapt2 dump badging` → `com.busan.tour`，`versionCode='22'`，`versionName='2.9'`，`minSdk 21 / targetSdk 34`，label `釜山旅行助手`
- `apksigner verify --print-certs` → v1+v2 通过，证书 `CN=Busan Travel Assistant`，SHA-256 `9d91ed6b8ffeec5eaf5b597ee19f56bfda6f8663d94ec726390a552224d33356`（与前几版同一把钥匙，可直接覆盖安装）
- 包内 `assets/index.html`、`assets/mix.js`、`assets/sw.js` 与仓库源码逐字节相同（sha256 比对 `same=True`）

iOS 包：`Busan_iOS_WebApp_v29.zip` 21 个条目，`required missing: none`，含 `安装说明.txt`、`manifest.webmanifest`、`sw.js`(busan-2.9)。

> iPhone 端仍只有 PWA（Safari「添加到主屏幕」）。本机 Windows 无 Xcode，仓库 `Build iOS (unsigned ipa)` 因 macOS runner 不可用第 6 次 cancelled，仍无签名 `.ipa`。

---

## 四、改动文件

| 文件 | 改动 |
| --- | --- |
| `Busan/android/assets/index.html` | 新增 `.qrec/.qrec-head/.qrec-body/.qrec-scrollwrap` 样式与夜间配色；`greet()` 改为折叠组件；新增 `qrecPaint/setQrec/initQrec`；点点子自动收起；`.mixrow` 与 `.wxchips` 改单行横滑 |
| `Busan/android/assets/sw.js` | 缓存名 `busan-2.9` |
| `Busan/android/AndroidManifest.xml` | `versionCode 22 / 2.9` + v2.9 说明块 |
| `Busan/android/java/com/busan/tour/MainActivity.java` | 类注释 v2.9、UA `BusanTour/2.9 (Android)` |
| `Busan/ios/project.yml` | `MARKETING_VERSION 2.9` / `CURRENT_PROJECT_VERSION 22` |
| `Busan/ios/README.md` | 标题与说明升 v2.9 |
| `Busan/pwa/build_pwa.py` | 产物 `Busan_Tour_WebApp_v29` / `Busan_iOS_WebApp_v29.zip` |
| `Busan/apk_build/test_v29.js` | **新增**，71 条断言 |
| `Busan/apk_build/test_v28.js` / `test_v27.js` / `test_v26.js` | 版本断言同步 2.9/22/busan-2.9 |
| `Busan/apk_build/_v29probe.py` / `_v29live.py` | **新增**，本地视口探针与线上探针 |
| `Busan/apk_build/v29_*.png` | 7 张证据截图（6 本地 + 2 线上） |
| `Busan/dist/Busan旅行助手.apk`、`Busan/dist/Busan_iOS_WebApp_v29.zip` | v2.9 产物 |

---

## 五、复跑命令

```powershell
cd D:\AI_Project_2026_2\Busan
node apk_build/test_v29.js
node apk_build/test_v28.js
node apk_build/test_v27.js
node apk_build/test_v26.js
node apk_build/test_v25.js
node apk_build/test_v23.js
node apk_build/test_v22.js
node apk_build/test_engine.js
& D:\AI_Project_2026_2\.venv\Scripts\python.exe apk_build/_v29probe.py   # 本地 390×844
& D:\AI_Project_2026_2\.venv\Scripts\python.exe apk_build/_v29live.py    # 线上 Pages
& D:\AI_Project_2026_2\.venv\Scripts\python.exe apk_build/build_apk.py
& D:\AI_Project_2026_2\.venv\Scripts\python.exe pwa/build_pwa.py
```

---

## 六、提交与线上

| 提交 | 内容 |
| --- | --- |
| `8d9e488` | feat(mobile): v2.9 个性化推荐支持收起/展开与单行横滑，双端同步 2.9 |
| （本条 docs 提交） | 回填线上 Pages 实测与产物哈希 |

推送：`422423e..8d9e488`（`main`）→ `https://github.com/luohaisheng814/AI_Project_2026_2`
Pages：`Deploy Web App (PWA)` run#6 对 `8d9e488` **success**。

线上实测（`_v29live.py`，`https://luohaisheng814.github.io/AI_Project_2026_2/`）：

```
URL/SECURE  https 且 isSecureContext=True
V29         qrec=true, open=false, bodyH=0, title=个性化推荐, act=展开, mix=object
SW CACHE    ["busan-2.9"]
展开后      chips=5, oneRow=true, scrollable=true, scrollW=677, clientW=286
ERRORS      []
```

即线上这一份与安装包同一套源码：默认收起只占一行、展开后 5 个点子在一条横滑轨道上。

---

## 七、已知限制与下一步

1. **只改了"点子"这一块**：偏好条（玩法·出行）本来就会 8 秒自动收起，这次没动；如果你的意思是它也一起改成横滑，说一声我再收一轮。
2. **横滑没有"回弹提示"**：目前靠右侧渐隐和 `scroll-snap` 暗示可滑，没有做页码小圆点或箭头。
3. **暂未支持"再展开时记住滚动位置"**：每次展开都从最左边开始。
4. 折叠高度用 `max-height` 过渡，点子数量大幅增加（比如 10 个以上）时需要把 `max-height` 一起调大，否则第二条会被裁掉。
5. 仍无签名 `.ipa`（Windows 无 Xcode + 仓库 macOS runner 不可用）。
6. 只做了 Chromium 手机视口验证，真机的惯性滚动与吸附手感建议装 APK 亲手滑一次。
