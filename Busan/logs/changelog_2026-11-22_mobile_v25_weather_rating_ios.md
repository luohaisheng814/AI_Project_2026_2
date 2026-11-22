# Busan 手机版 v2.5 更新日志

- 日期：2026-11-22
- 版本：`versionCode 18` / `versionName 2.5`
- 包名：`com.busan.tour`
- 基线：v2.4（commit `a84ea420fd6905f0119d847257674a3a757c0759`）
- 仓库：<https://github.com/luohaisheng814/AI_Project_2026_2.git>

## 一、本次目标

继续完善 Busan 手机端的 UI 与玩法，做四件事：

1. 加“查看手机天气”的授权与实况天气，并按天气推荐更合适的景点；
2. 天气发生变化时，主动给用户建议；
3. 把玩法、看法这类评级统一改成星级；
4. 补苹果（iOS）的安装包；
5. 全量测试后推 GitHub 并写日志。

## 二、实现内容

### 2.1 天气权限与实况天气

Android / iOS 都**没有单独的“天气权限”**：天气是按经纬度查的，所以真正要申请的是定位权限。
本轮把这层关系在界面上讲清楚，而不是加一个没有系统意义的自定义权限。

- 顶部实时定位条下面新增天气条 `#wxStrip`：图标 + `🌧 雨 · 18°C · 降水 85% · 手动` + 「天气」按钮。
- 首次点「天气」且未授权：先出权限卡（`tag` = `天气 · 需要定位权限`），说明
  “天气按经纬度取，需要定位授权，仅用于天气与距离”；
  - 「允许定位并查看天气」→ 走既有 `BusanLive.ensure`，系统弹一次授权；
  - 「去系统设置」→ `BusanHost.openAppSettings()`。
- 拒绝授权不摆烂：自动退回釜山市区坐标（35.18, 129.08），卡片明确标注“默认位置”；
  也可以完全离线用手动天气。
- 数据源：Open-Meteo（免 API Key）
  ```
  https://api.open-meteo.com/v1/forecast?latitude=…&longitude=…
    &current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m
    &hourly=precipitation_probability,temperature_2m,weather_code
    &daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max
    &timezone=Asia%2FSeoul&forecast_days=2
  ```
- 取数走既有 `fetchText` 桥（APK 内是原生 `HttpURLConnection`，iOS 是 `URLSession`），
  失败时明确提示“现在拿不到天气”，**不伪造实时温度**。
- WMO 天气码归一成 7 类：晴 / 多云 / 小雨 / 雨 / 雪 / 雾 / 雷雨，并给出图标与中韩英三语文案。
- 每 20 分钟自动刷新一次（页面隐藏时跳过）；坐标变化或重新打开页面也会刷新。

### 2.2 按天气推荐：18 个景点都有了天气画像

`weather.js` 给每个景点补了 `env`（户外/半室内/室内）、`coast`、`view`（依赖能见度）、
`stairs`（台阶强度）、`shade`（遮阴）、`rain`（躲雨能力）六个维度，再按当前天气算 0–100 的适配分：

| 天气 | 加权方向 | 例子 |
|---|---|---|
| 晴 | 户外 +10、海边 +7、观景 +5；>27°C 且无遮阴 −6 | 多大浦、海云台、广安里排前 |
| 雨/雷雨 | 室内 +22、半室内 +9、户外 −14；海边再 −9、台阶多再 −3 | 洛东江河口生态中心、西面 100 分；海云台 32 分 |
| 高温 ≥30°C | 海边 +10、遮阴 +6、台阶多 −7 | 湿地/室内优先，甘川降分 |
| 低温 ≤2°C | 室内 +12、海边 −12 | 西面、生态中心优先 |
| 大风 ≥9 m/s | 海边 −15、观景 −6、室内 +8 | 海边让位给街区 |
| 雪/雾 | 雪：台阶多 −6/级；雾：观景 −16 | 雪天别爬甘川台阶；雾天别上观景台 |

天气卡内容：

```
当前天气 · 🌧 雨 18°C
体感 18°C · 风 6.0 m/s · 降水概率 85%
按这个天气，更推荐
1. 洛东江河口生态中心 ★★★★☆ 4.3 — 室内为主，下雨也能逛
2. 西面 ★★★★☆ 4.2 — 室内为主，下雨也能逛
3. 札嘎其市场 ★★★★☆ 4.1 — 有店铺和屋檐可躲雨
提醒 · 带伞或轻便雨衣 · 石板路和台阶湿滑，鞋底要防滑
玩法星级 · 海岸休闲/日落夜景 4.4★ · 艺术村落/文化街区 4.3★ …
```

推荐类回答（`recommend / general / group`）会在气泡顶部多一行天气提示，
例如 `☀️ 晴 24°C · 天气影响不大，原方案可以照走`，
恶劣天气则写 `这个天气更适合：洛东江河口生态中心、西面`。

**不改动原有 3 个方案的顺序与正文**，避免“正文说 A、按钮却是 B”的不一致；
天气驱动的完整三选放在天气卡里。

### 2.3 天气变化主动建议

`weather.js` 保存上一次天气（本机 `localStorage`，6 小时内有效），
对以下变化做检测：

| 变化 | 触发条件 |
|---|---|
| 天气类型 | 晴 → 雨、多云 → 雷雨等跨类 |
| 气温 | 变化 ≥ 5°C |
| 降水 | 降水概率从 <60% 升到 ≥60% |
| 风 | 风速从 <9 m/s 升到 ≥9 m/s |

命中后同时做两件事：

- 底部 `BusanToast` 弹一条短提醒；
- 对话里插入一条 `天气提醒` 气泡：变化清单 + “现在更适合”3 个点 + 2 条提醒。

### 2.4 星级评级（玩法 / 看法）

新增 `ratings.js`，18 个景点都有四项 1–5 分：

- **玩法**（可玩性/内容密度）
- **景观**（视野/拍照）
- **便利**（体力、台阶、交通）
- **性价比**（门票与体验比）

综合分 = 玩法 35% + 景观 30% + 便利 20% + 性价比 15%，保留 1 位小数，5 星制显示。
例如甘川文化村：玩法 4.7 / 景观 4.6 / 便利 3.1 / 性价比 4.4 → **4.3★ 值得一去**。

UI 上：

- 景点回答气泡里插一块 `rating`：金色星条（CSS 双层裁切做半星）+ 数字 + 评级词
  （强烈推荐 / 值得一去 / 可以一看 / 看时间安排 / 可以跳过）+ 四项明细；
- 「我的评分」5 颗可点星，再点同值取消；只存本机 `busan_rating_user`，不改官方基线；
- 每个推荐按钮的景点名前加小星级 `★4.3`；
- 天气卡底部给 4 个玩法大类的平均星级（海岸休闲 4.4★ / 艺术村落 4.3★ /
  湿地生态 4.2★ / 小众渔港 4.1★）。

三语文案全部跟随顶部语言按钮（中文 / 한국어 / English）。

### 2.5 iOS 安装包

iOS 端和 Android 共用同一套 `android/assets/`：新增 `Busan/ios/` 的 WKWebView 壳。

| 文件 | 作用 |
|---|---|
| `ios/project.yml` | XcodeGen 工程，`../android/assets` 以 folder reference 引入（54 张图、子目录都在） |
| `ios/BusanTour/AppDelegate.swift` | 启动窗口 |
| `ios/BusanTour/BusanViewController.swift` | WKWebView + `BusanHost` 桥（fetchText / 定位 / 设置）+ 外链跳转 |
| `ios/BusanTour/Info.plist` | 定位用途说明、ATS、`nmap` scheme、版本 2.5 / 18 |
| `ios/build_ipa.sh` | macOS 一键：xcodegen → xcodebuild → `Payload/` → 未签名 ipa |
| `.github/workflows/ios.yml` | macOS-14 流水线，推送后自动出 `Busan-unsigned.ipa` |
| `ios/README.md` | 编译、签名、与 Android 的差异、校验清单 |

桥的实现方式：`WKUserScript` 在 `documentStart` 注入同名 `window.BusanHost`，
把调用转成 `webkit.messageHandlers.busan.postMessage`；原生侧用 `CLLocationManager`
回传 `window.__busanLocUpdate`，用 `URLSession` 回传 `window.__busanHttpDone`。
网页侧不需要为 iOS 分支。

**本轮没有产出可安装的 `.ipa`**：`.ipa` 必须 macOS + Xcode 编译并签名，本机是 Windows，
也没有 macOS 环境。交付的是“可编译工程 + 一键脚本 + CI”，不伪造包体。
三条落地路径写在 `ios/README.md`：Xcode 免费签名（7 天）、CI 未签名包 + AltStore 自签、
付费账号 TestFlight。

## 三、测试结果

### 3.1 自动化回归

| 测试 | 命令 | 结果 |
|---|---|---|
| v2.5 天气 / 星级 | `node apk_build/test_v25.js` | **63 PASS / 0 FAIL** |
| v2.3 引擎回归 | `node apk_build/test_v23.js` | **50 PASS / 0 FAIL** |
| v2.2 引擎回归 | `node apk_build/test_v22.js` | **43 PASS / 0 FAIL** |
| 离线引擎 | `node apk_build/test_engine.js` | `✅ 离线引擎全部断言通过` |
| 云端问答（离线回放） | `node apk_build/test_cloud_round.js` | 正常（含轮椅/日落等 6 组） |
| HTML 内联脚本 | `node --check`（抽出末尾 `<script>`） | 通过（66,620 B） |
| `weather.js` / `ratings.js` | `node --check` | 通过 |
| iOS 工程 | YAML 解析 + `plistlib` + 括号配平 | 通过（未在 macOS 编译） |

`test_v25.js` 覆盖：

- 18 个景点全部有四项评分，综合分 3.5–5.0；`starsText(4.5) == ★★★★☆`；
- 四个玩法大类都有平均星级；
- 用户自评写入 / 读取 / 清除；
- WMO 码映射（0/2/45/61/71/95）；
- 晴→海边靠前、雨→室内 100 分且海边 32 分、高温→遮阴优先、低温/大风→室内；
- 雨天提醒含“伞”、雷雨提醒含“避开海边”；
- 变化检测：晴→雨（类型 + 降水）、24→31°C（+7）、风速 11 m/s；
- Open-Meteo 返回样例的解析（温度 / 分类 / 今日最高最低）；
- 手动天气的中英文横幅。

### 3.2 v2.5 UI 探针

脚本：`apk_build/_v25probe.py`（CDP 9225，500×1500，移动视口）

| 检查 | 结果 |
|---|---|
| `MODULES` | `ui/wx/rt = true`，天气条与按钮存在 |
| `WXBAR`（手动雨） | `🌧 雨 · 18°C · 降水 85% · 手动` |
| `WXCARD` | `chips=8`、`choices=3`、标题以 `天气 当前天气 · 🌧 雨 18°C` 开头 |
| `WXCLEAR`（切晴） | 天气条变 `☀️ 晴 · 24°C`，首选变 `多大浦梦之夕阳喷泉` |
| `SPOT` | 评分块存在，`★★★★☆ 4.3 值得一去`，5 个自评按钮，四项明细齐全 |
| `RATED` | 点第 5 星 → `saved=5`，`localStorage={"甘川文化村":5}`，1 个按钮点亮 |
| `WXNOTE` | 推荐回答带 `☀️ 晴 24°C · 天气影响不大，原方案可以照走` |
| `LIVE FETCH` | 真实接口返回 `temperature_2m=7.6, weather_code=0, wind=7.0` |
| `ERRORS` | `[]`（无 JS 报错） |

截图：

- `Busan/apk_build/v25_weather_rain.png`：雨天天气卡 + 3 个室内向推荐 + 8 个手动天气
- `Busan/apk_build/v25_weather_clear.png`：切晴后重排，首选多大浦
- `Busan/apk_build/v25_rating.png`：甘川 4.3★ 与四项明细、我的评分已记录 5 星
- `Busan/apk_build/v25_recommend.png`：推荐回答顶部的天气提示行

### 3.3 真实天气接口

2026-11-22 15:45（釜山时间）实测：

```json
{"time":"2026-11-22T15:45","temperature_2m":7.6,"relative_humidity_2m":47,
 "apparent_temperature":4.1,"precipitation":0.0,"weather_code":0,"wind_speed_10m":7.0}
```

今日 `max=7.7 / min=-0.8`，说明接口字段与解析路径都真实可用。

## 四、构建产物

### 4.1 APK

- 路径：`D:\AI_Project_2026_2\Busan\dist\Busan旅行助手.apk`
- 大小：`10,233,514 B`（约 9.76 MiB）
- SHA-256：`AB4A91F63415474A65CB4FBAE23294596468B2D02DAFACEC807764AB2F6B7965`
- 版本：`versionCode 18` / `versionName 2.5`；包名 `com.busan.tour`
- 签名证书 SHA-256：`9d91ed6b8ffeec5eaf5b597ee19f56bfda6f8663d94ec726390a552224d33356`（与 v2.4 同一 keystore，可覆盖升级）
- APK 内已校验：`assets/index.html`、`assets/weather.js`、`assets/ratings.js`、`assets/photos/` 54 张
- dex 内已校验：`Lcom/busan/tour/MainActivity;` 及其匿名内部类

### 4.2 iOS

- 工程：`Busan/ios/`（XcodeGen 定义 + Swift 源码 + Info.plist）
- 一键脚本：`Busan/ios/build_ipa.sh`
- CI：`.github/workflows/ios.yml`（`workflow_dispatch` 或推送 `Busan/**` 触发）
- 产物：**无本地 `.ipa`**（本机无 macOS）；CI 跑完后在 Actions 里下载 `Busan-unsigned-ipa`

## 五、已知限制

1. **iOS 未在真机/模拟器编译**：本机 Windows 无 Xcode。已做 YAML / plist / 括号配平静态校验，
   首次 macOS 构建时若 Xcode 版本或 XcodeGen 字段报警，需要按报错微调。
2. **无 Android 真机**：`adb devices` 为空。天气权限弹窗、WebView 内 `fetch` 的实际表现、
   覆盖安装只做了 WebView 层与 APK 结构校验。
3. **“天气权限”是产品概念**：系统没有该权限，本轮是把“定位 + 网络”的授权链路讲清楚，
   Android 侧没有新增 `<uses-permission>`（也不需要）。
4. **手动天气不是实况**：离线/拒绝授权时用的是用户选的晴/雨/大风，卡片上明确标注“手动”。
5. **天气只用于推荐排序与建议**：不预测营业状态、不推断拥挤程度，也不改官方资料中的事实。
6. **评分为编辑基线**：四项分数是人工设定（按景点类型与体力强度），不是平台真实点评聚合；
   用户自评只存本机，换设备不跟随。
7. **iOS 无原生大模型桥**：`session.js` 在没有 `BusanHost.llmChat` 时会直接用网页 `fetch` 调同一端点，
   功能可达但少了 Android 侧的原生超时/重试封装。

## 六、验证清单（可复跑）

- [x] `AndroidManifest.xml` 为 `versionCode=18` / `versionName=2.5`
- [x] `MainActivity` UA 为 `BusanTour/2.5 (Android)`
- [x] 天气条存在，未取到天气时显示“未获取”
- [x] 未授权点「天气」出权限卡；允许后取实况；拒绝后按默认坐标
- [x] 手动 8 种天气可切，卡片随之重排
- [x] 雨天首选室内（洛东江 / 西面），晴天首选海岸
- [x] 天气变化（类型/温度/降水/风）弹提醒 + 对话建议
- [x] 景点气泡显示 5 星综合分 + 四项明细 + 评级词
- [x] 用户自评 1–5 星写入 `localStorage`，刷新保留
- [x] 推荐按钮带 `★4.x`
- [x] 中 / 韩 / 英三语跟随语言按钮
- [x] v2.5（63）/ v2.3（50）/ v2.2（43）/ 离线引擎 / 云端回放全部通过
- [x] APK 含 `weather.js`、`ratings.js`、54 张图，签名校验通过
- [x] iOS 工程 YAML / plist / Swift 结构校验通过
- [ ] Android 真机安装与权限弹窗（无设备）
- [ ] macOS 上 `xcodegen` + `xcodebuild` 实编译（无环境）
- [ ] iOS 真机安装与 NAVER 跳转（无设备）

## 七、提交与推送

- 代码与产物提交：`e4c0c4f118ab48111161ed4dbc6192d8620a11ff`
- 远端：`https://github.com/luohaisheng814/AI_Project_2026_2.git`，分支 `main`
- 上一版 v2.4：`a84ea420fd6905f0119d847257674a3a757c0759`
- 推送结果：`ea97d01..936d2f0  main -> main`（含紧随其后的 docs 提交）
- 对比页：<https://github.com/luohaisheng814/AI_Project_2026_2/compare/a84ea420fd6905f0119d847257674a3a757c0759...e4c0c4f118ab48111161ed4dbc6192d8620a11ff>

> 日志回填提交为紧随其后的 `docs` 提交；代码与产物的正式提交是上面这条 `feat(mobile): v2.5 …`。
