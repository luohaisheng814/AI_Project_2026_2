# 釜山 AI 旅行助手 · v2.8 手机版更新日志

- 日期：2026-11-22
- 版本：Android `versionCode 21 / versionName 2.8`，iOS `2.8 / 21`，PWA 缓存 `busan-2.8`
- 上一版：v2.7（右上角天气按钮 + 按时间昼夜）
- 本轮目标：手机 UI 继续完善；**点天气按钮或点“附近”都先要位置权限**，取到坐标后再取天气，再结合手机当前时间做一次综合推荐；全量测试；推送 GitHub 并出安装包与日志

---

## 一、这一版到底改了什么

### 1. 天气按钮与“附近”合成一条链路

以前是两套入口：右上角天气按钮先问权限再取天气（v2.7），底部“附近”按钮则直接静默触发系统定位（v2.3 起的老逻辑），两条链路各自为政，给出的推荐也各算各的。

v2.8 统一成一条：

```
点【天气】或【附近】
   ↓
没有坐标/没授权 → 先给权限卡（写明“要位置是为了取天气+算距离+排顺序”）
   ↓ 用户点“允许定位并继续”
BusanLive.ensure() 触发系统定位授权并等首个坐标
   ↓
WX.refresh() 按这个坐标取当地实况天气（Open-Meteo，免 Key）
   ↓
BusanMix.ranked() 用「时间 × 天气 × 距离 × 星级」打分排序
   ↓
结论卡：三枚胶囊（时间 / 天气 / 距离）+ 三个可点方案 + 一句话建议
```

- 已经有坐标、或权限已是 granted：跳过权限卡，直接算（不再重复打扰授权）。
- 拿不到坐标（拒绝/超时）：仍然给结论，但正文明确写“距离这一项不参与排序”，天气退回釜山市区中心，不假装有定位。
- 天气取不到（断网/接口不可达）：正文明确写“只有时间和距离在起作用”，不编造温度。

### 2. 新增 `mix.js`：综合排序引擎（纯计算，可单测）

排序由四个分量相加，权重刻意做成“距离最重、天气次之、时间第三、星级只做微调”：

| 分量 | 取值 | 说明 |
| --- | --- | --- |
| 距离 `distScore` | 0.5 km 内 +22，之后每 km −4.4，最低 −12 | 直线距离，与 live.js 同口径，不编造车程 |
| 天气 `weatherScore` | 复用 v2.5 的 `BusanWeather.fitOf()`（0–100），压到 ±26 | 雨天室内加分、海边减分；晴天海边/观景加分；高温、低温、大风各有偏置 |
| 时间 `timeScore` | −8 ~ +14 | 用每个景点自带的 `plan.best_time`（morning/afternoon/evening/sunset）和 `vibes`（night/sunset/indoor/food…）判断“这个点现在去合不合适” |
| 星级 `rateScore` | −4 ~ +5 | 只做微调，不让评分盖过时间与天气 |

时间轴（与页面昼夜同口径，19:00–05:59 算夜）：

| 小时 | 段 | 排序偏好 |
| --- | --- | --- |
| 0–3 | 夜间 | 室内、有 night/evening 属性的点位加分；纯户外海边、山景减分 |
| 4–5 | 凌晨 | 基本等同夜间，但下调幅度小一些 |
| 6–10 | 上午 | best_time=morning 的 +11，拍照点 +4；夜市/市场类 −4 |
| 11–13 | 午间 | 室内 +7、市场美食 +5；海边 −3；日落/傍晚类 −5 |
| 14–16 | 午后 | best_time=afternoon +10，sunset +6 |
| 17–18 | 傍晚 | best_time=sunset +12、evening +9，sunset 属性 +6 |
| 19–23 | 夜间 | best_time=evening +10、night 属性 +8、室内 +9；纯户外 −8 |

同一条数据、同一个天气，只换钟点，顺序确实会变（探针实测）：

- 21:00 + 雨 → `南浦洞BIFF广场 / 西面 / 札嘎其市场`（夜味 + 室内）
- 10:00 + 雨 → `札嘎其市场 / 洛东江河口生态中心 / 南浦洞BIFF广场`（上午 + 室内）

### 3. 结论卡的三枚胶囊

`paintBubble()` 新增 `.mixrow` / `.mixchip` 渲染：时间绿、天气橙、距离灰，夜间各有深色版。正文不再重复“几点、什么天气”，只写降级说明和推荐列表，卡片更短、更好扫。

### 4. 气泡第二行补上上下文

`#wxPill` 里新增 `#wxCtx`：`16:20 · 午后 · 最近 龙头山公园 0.2 km`。这样 10 秒的短暂气泡既报天气，也顺带告诉你“现在几点、离最近的景点多远”。
没有天气数据时，按钮图标按本地时间换成 🌙 / 🌤。

### 5. 权限文案改成“三步走”

旧文案只说“要读天气所以需要定位”。新文案把用途讲全：**坐标 → 当地天气 → 手机当前时间**，并明确“只用于取天气、算距离和排顺序，不上传”。被拒绝时仍保留“去系统设置”和“手动选晴/雨/大风”的退路。

### 6. 顺手修的一致性问题

- 结论卡底部原来写死“界面已按手机本地时间切到夜间/保持白天配色”。用户手动锁主题时会自相矛盾，改成只陈述规则：`06:00–18:59 白天，19:00–05:59 夜间`。
- `bandOf(0/2/3 点)` 一开始被判成“上午”（`hour < 11` 分支写太宽），已改为先判 `>=19 || <4` 为夜，再判 4–5 凌晨。

---

## 二、测试（全部可跑项）

| 脚本 | 结果 |
| --- | --- |
| `apk_build/test_v28.js`（本轮新增） | **103 / 0** |
| `apk_build/test_v27.js`（同步 2.8 版本号） | **50 / 0** |
| `apk_build/test_v26.js`（同步 2.8 版本号） | **74 / 0** |
| `apk_build/test_v25.js` | **63 / 0** |
| `apk_build/test_v23.js` | **50 / 0** |
| `apk_build/test_v22.js` | **43 / 0** |
| `apk_build/test_engine.js` | `✅ 离线引擎全部断言通过` |

`test_v28.js` 不是纯 grep：它把 `weather.js` + `mix.js` 放进 Node 沙箱，接上真实的 18 个景点、真实 `fitOf/why`、真实 haversine，真跑排序后断言：

- 时段边界 15 个点（0/2/3/4/5/6/10/11/13/14/16/17/18/19/23 点）
- 夜间判定与页面同口径（18 点昼、19 点夜）
- 距离分单调、无坐标不吃分
- 夜间室内 > 夜间海边；傍晚 `best_time=sunset` ≥ 12
- 雨天室内 > 海边；晴天海边 > 市场；无天气不加不减
- 夜间下雨的 3 个结果：分数降序、都带距离、都带 ≥2 条理由、首选要么室内要么夜味、首选 2 km 内
- 傍晚晴天在多大浦附近，首选必须是 sunset 类（海水浴场/没云台/峨嵋山观景台/夕阳喷泉之一）
- 午间晴天不再把海边堆到第一
- 接线：`mix.js` 被引入、天气按钮与“附近”都先权限卡再 `mixFlow`、`fetchWeather` 支持 `quiet/done`、胶囊渲染与夜间配色、`BusanUI.mix/mixCard/mixAdvice/startMix` 对外暴露
- 版本：APK 21/2.8、UA 2.8、iOS 2.8/21、无 2.7 UA 残留、PWA 缓存 `busan-2.8` 且清单含 `mix.js`
- 不回退：`paintWxBar / wxAdapt / initWeather / wxPanelHtml / ratingHtml / grantWeather / grantNearby / routePermissionCard / renderNearby / locateOnce / BusanLightbox / BusanPlanner` 全部仍在

### 手机视口探针（真 Chrome，390×844，`_v28probe.py`）

```
BOOT        mix=object, fab=true, pillCtx=true, hour=16, night=false
PILL CTX    16:19 · 午后 · 未定位
PERM CARD   permacts=1, grant=true, tag=综合推荐 · 需要定位权限, 三步文案=true
PERM STATE  granted（注入坐标 35.1000,129.0350）
MIX WEATHER tag=天气 · 综合推荐, chips=3, choices=3, 胶囊=[16:20 午后 | ☀️ 晴 8°C | 最近 龙头山公园 0.2 km]
MIX NEARBY  tag=附近 · 综合推荐, chips=3, choices=3, 首选=白浅滩文化村 ★4.2
TIME SHIFT  21点=南浦洞BIFF广场/西面/札嘎其市场  10点=札嘎其市场/洛东江河口生态中心/南浦洞BIFF广场  changed=true
NIGHT MIX   chipBg=rgb(20,49,42) chipColor=rgb(127,224,182) theme=#072e3c
BACK DAY    night=false theme=#0a4e63
CHOICE      点“白浅滩文化村 怎么去”正常进入原有路线问答
ERRORS      []
```

证据截图（`Busan/apk_build/`）：

| 文件 | 内容 |
| --- | --- |
| `v28_home_day.png` | 白天下首屏，右上角天气按钮，无旧天气条 |
| `v28_wx_permission.png` | 点按钮后的权限卡（三步说明 + 允许 / 去系统设置） |
| `v28_mix_chips.png` | 结论卡顶部：三枚胶囊 + 推荐列表 |
| `v28_mix_result.png` | 结论卡全貌（3 个方案 + 一句话建议） |
| `v28_nearby_result.png` | “附近”按钮走的同一套结论（标签为「附近 · 综合推荐」） |
| `v28_night_mix.png` | 夜间模式下的同一张卡（胶囊深色可读） |
| `v28_day_after.png` | 手动切回白天后 |
| `v28_online_pages.png` | GitHub Pages 线上 v2.8 实测 |

---

## 三、构建产物

| 产物 | 大小 | SHA-256 |
| --- | --- | --- |
| `Busan/dist/Busan旅行助手.apk` | 10,602,539 B（10.35 MB） | `55F3A7750384F1755AD90085F4BB464A796E3270BC65686814F10C2A6075301A` |
| `Busan/dist/Busan_iOS_WebApp_v28.zip` | 10,488,265 B | `B182331824730E7BD9EFB0856E3742831BDD2784D7BCF371851B8FBEFA6B4ADA` |

APK 校验：

- `aapt2 dump badging` → `com.busan.tour`，`versionCode='21'`，`versionName='2.8'`，`minSdk 21 / targetSdk 34`，label `釜山旅行助手`
- `apksigner verify --print-certs` → v1+v2 通过，证书 `CN=Busan Travel Assistant`，SHA-256 `9d91ed6b8ffeec5eaf5b597ee19f56bfda6f8663d94ec726390a552224d33356`（与 v2.7 同一把钥匙，可覆盖安装）
- APK 内 `assets/index.html`、`assets/mix.js`、`assets/sw.js` 与仓库源码 **逐字节相同**（sha256 比对）
- `assets` 里只有 180/192/512 三档图标，`icon_raw.png`、`icon-1024.png` 仍在 `apk_build/`、`pwa/`，不塞进安装包

iOS 包：`Busan_iOS_WebApp_v28.zip` 解压后与 `dist/pwa/Busan_Tour_WebApp_v28/` 同内容（21 个顶层条目，`required missing: none`），含 `安装说明.txt`、`manifest.webmanifest`、`sw.js`(busan-2.8)、`icon-180/192/512`。

> 说明：iPhone 端仍然只能给 PWA（Safari「添加到主屏幕」）。本机是 Windows、没有 Xcode，仓库里的 `Build iOS (unsigned ipa)` 也因 macOS runner 不可用连续 cancelled（v2.6 起第 5 次），所以没有签名 `.ipa`。日志与 `ios/README.md` 都如实写了这一点。

---

## 四、改动文件

| 文件 | 改动 |
| --- | --- |
| `Busan/android/assets/mix.js` | **新增**，综合排序引擎（时间/天气/距离/星级） |
| `Busan/android/assets/index.html` | 引入 mix.js；`mixFlow/mixResult/mixPermissionCard/mixChips/wxCtxLine`；`fetchWeather` 支持 `quiet/done`；`.mixrow/.mixchip` 样式与夜间版；`#wxCtx` 第二行；FAB 与“附近”改走统一链路；`BusanUI` 新增 `mix/mixCard/mixContext/mixAdvice/timeBand/startMix` |
| `Busan/android/assets/sw.js` | 缓存名 `busan-2.8`，清单新增 `./mix.js` |
| `Busan/android/AndroidManifest.xml` | `versionCode 21 / 2.8` + v2.8 说明 |
| `Busan/android/java/com/busan/tour/MainActivity.java` | 类注释 v2.8、UA `BusanTour/2.8 (Android)` |
| `Busan/ios/project.yml` | `MARKETING_VERSION 2.8` / `CURRENT_PROJECT_VERSION 21` |
| `Busan/ios/README.md` | 标题与说明升 v2.8 |
| `Busan/pwa/build_pwa.py` | 产物名与说明升 v28 / 2.8 |
| `Busan/apk_build/test_v28.js` | **新增**，103 条断言（含真跑排序） |
| `Busan/apk_build/test_v27.js` / `test_v26.js` | 版本/缓存名断言同步到 2.8/21/busan-2.8 |
| `Busan/apk_build/_v28probe.py` / `_v28live.py` | **新增**，本地视口探针与线上 Pages 探针 |
| `Busan/apk_build/v28_*.png` | 7 张证据截图 |
| `Busan/dist/Busan旅行助手.apk`、`Busan/dist/Busan_iOS_WebApp_v28.zip` | v2.8 产物 |
| `.gitignore` | 忽略 `_inline*.js`、`_chk*`、`_zip*.txt` 等临时文件 |

---

## 五、复跑命令

```powershell
cd D:\AI_Project_2026_2\Busan
node apk_build/test_v28.js
node apk_build/test_v27.js
node apk_build/test_v26.js
node apk_build/test_v25.js
node apk_build/test_v23.js
node apk_build/test_v22.js
node apk_build/test_engine.js
& D:\AI_Project_2026_2\.venv\Scripts\python.exe apk_build/_v28probe.py      # 本地 390×844
& D:\AI_Project_2026_2\.venv\Scripts\python.exe apk_build/_v28live.py       # 线上 Pages
& D:\AI_Project_2026_2\.venv\Scripts\python.exe apk_build/build_apk.py
& D:\AI_Project_2026_2\.venv\Scripts\python.exe pwa/build_pwa.py
```

---

## 六、提交记录

| 提交 | 内容 |
| --- | --- |
| `80e90b5` | feat(mobile): v2.8 天气与附近统一走定位→天气→本地时间综合推荐，双端同步 2.8 |
| `13267d9` | chore(pwa): 触发 Pages 重新发布（首次 deploy-pages 偶发失败，重跑成功） |
| （本条 docs 提交） | 回填线上 Pages 验证、产物哈希与复跑命令 |

推送：`ac9c72d..80e90b5 main -> main` → `https://github.com/luohaisheng814/AI_Project_2026_2`

> Pages 第一次部署（run#3 / `80e90b5`）在 `deploy-pages@v4` 步骤 status=failure，`upload-pages-artifact` 之前全 success；同一份内容再推一次（run#4 / `13267d9`）成功，属平台侧偶发，不是 YAML 或内容问题。

---

## 七、已知限制与下一步

1. **排序权重是经验值**：距离 −4.4/km、天气 ×0.8、时间 ±14 都是本轮自定，未做真实用户验证；用户反馈“太远/太近”时改 `mix.js` 里四个函数即可，`test_v28.js` 会跟着兜住。
2. **不推断营业时间**：`timeScore` 只用景点资料里已有的 `best_time/vibes`，不假设“几点还开着”。海事、市集类点位的实际营业仍需用户自己核对官网。
3. **距离是直线**：和 live.js 同口径，不是步行/公交里程，别把 km 当车程读。
4. **夜间定义仍是固定钟点（19:00–05:59）**，不是当地日落；要更准可接 Open-Meteo 的 `daily.sunrise/sunset`，让夜间随季节漂移。
5. **苹果端仍无 `.ipa`**：Windows 无 Xcode + 仓库 macOS runner 不可用，只能给 PWA 与 Xcode 工程。
6. 未在真机上跑过：系统授权弹窗、夜间配色、GPS 首点延迟都只在 Chromium 模拟视口验证过，实机观感需装 APK 亲测一次。
