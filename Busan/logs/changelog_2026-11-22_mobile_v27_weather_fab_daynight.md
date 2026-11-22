# 釜山 AI 旅行助手 · v2.7 更新日志

- 日期：2026-11-22
- 版本：**v2.7**（Android `versionCode 20 / versionName 2.7`，iOS `MARKETING_VERSION 2.7 / CURRENT_PROJECT_VERSION 20`）
- 上一版：v2.6（UI 收口 + PWA 安装）
- 分支：`main` → `https://github.com/luohaisheng814/AI_Project_2026_2`

---

## 一、本轮改了什么

### 1. 天气入口搬到右上角，点一下才问权限

- 旧版是内容区里单独一行「天气：未获取 · 点右侧获取 + 天气按钮」，占掉一整行高度。
- 新版收成页头右上角一枚胶囊按钮：**图标 + 温度**（没数据时显示「🌤 天气」），与标题同一行，
  不再挤占正文。实测位置 `[312,10] → [376,44]`（390×844 视口），完全落在页头内。
- 点击逻辑（按权限分三种情况）：
  | 当前状态 | 点击后 |
  | --- | --- |
  | 还没有天气数据、未授权 | 先在对话里给一张说明卡：为什么天气要定位、数据只用在本机；点「允许定位并继续」才触发系统授权弹窗 |
  | 已授权但没有数据 | 直接申请定位 → 取天气 → 显示气泡 |
  | 已有天气数据 | 不再打扰权限，只把天气气泡露出来 |

  被拒绝过的情况，卡片里仍保留「去系统设置」按钮，直达应用权限页。

### 2. 天气只显示一段时间，离开首页就自己收

- 取到天气后弹出一条短气泡（页头下方、右对齐）：`🌧 雨 · 14°C · 降水 85% · 手动 · 更新 15:54`。
- **10 秒**后自动收起；手动查看时 8 秒。
- 三种“不在主页面”的情况会立刻收起：
  1. 聊天区往上翻、离开最新消息超过 140px（等于去读旧内容了）；
  2. 打开账户/设置等弹层（`.modal` / `.sheet` 可见）；
  3. 切到后台（`document.hidden`）。
- 气泡本身 `pointer-events:none`，盖住的按钮照样能点，不会挡操作。

### 3. 页面按时间分昼夜

- 白天（07:00–18:59）用原配色；夜间（**19:00–06:00**）自动切深色。
- 不是跟随系统，而是按手机本地时间判断；每分钟复判一次，切回前台也复判，跨点自动切换。
- 夜间是整套换色，不只是背景：页头渐变变深、选择条/状态条/气泡/选项卡/评分块/官网资料/输入区/弹层同套；
  顺手修了两处夜间对比度：官网长链接由浏览器默认深蓝改成 `#7fc9de`，权限卡的「去系统设置」不再发白。
- 顶部状态栏 `theme-color` 同步：白天 `#0a4e63`，夜间 `#072e3c`，PWA 全屏时状态栏不跳色。
- 也留了口子：`BusanUI.setThemeMode('day'|'night'|'auto')`，需要时能手动锁定。

### 4. 双端同步

- Android：`versionCode 20 / versionName 2.7`，`User-Agent: BusanTour/2.7 (Android)`，注释块补 v2.7。
- iOS：`MARKETING_VERSION 2.7 / CURRENT_PROJECT_VERSION 20`，共用同一套 `android/assets`，无需另改逻辑。
- PWA：`sw.js` 缓存名升到 `busan-2.7`（HTML 仍是网络优先，发版即时生效）。

---

## 二、交付物

| 产物 | 路径 | 大小 | SHA-256 |
| --- | --- | --- | --- |
| Android 安装包 | `Busan/dist/Busan旅行助手.apk` | 10,590,192 B | `057298DAE52BE3039B04CC3CF5EFB23743935C00561E16C2FC0AA1788946E0C7` |
| iOS 网页安装包 | `Busan/dist/Busan_iOS_WebApp_v27.zip` | 10,478,981 B | `875610FD2C7D40F93F58C797838AC5DC327DDB3416E08AA1E7271A6844A1BD4A` |
| PWA 在线地址 | `https://luohaisheng814.github.io/AI_Project_2026_2/` | — | Pages 流水线发布 |

APK 校验：`aapt2 dump badging` → `versionCode='20' versionName='2.7'`；`apksigner verify` 通过（v1+v2），
证书 `CN=Busan Travel Assistant` / SHA-256 `9d91ed6b…33356`；包内 `index.html`、`sw.js`、`manifest` 与源码逐字节一致。

iPhone 安装：Safari 打开 Pages 地址 → 分享 → 添加到主屏幕（前端与 APK 同源）。
真 `.ipa` 仍需 macOS + Xcode；仓库的 macOS runner 本轮之前连续 3 次 `cancelled / 0 steps`，未再消耗次数。

---

## 三、测试

### 1. 静态断言

| 套件 | 结果 |
| --- | --- |
| `test_v27.js`（新增） | **PASS 50 / FAIL 0** |
| `test_v26.js`（回归，版本号已同步） | PASS 74 / FAIL 0 |

`test_v27` 覆盖：按钮在页头右上角、旧天气条/旧按钮已移除、气泡默认隐藏与 8/10 秒超时、
滚动与弹层/后台自动收起、三种权限分支、19–06 点判夜、每分钟复判、theme-color 同步、
`setThemeMode` 手动覆盖、双端 2.7/20、无 2.6 残留、既有天气/星级能力不回退。

### 2. 历史套件

| 套件 | 结果 |
| --- | --- |
| `test_engine.js` | ✅ 离线引擎全部断言通过 |
| `test_v22.js` | 43 pass / 0 fail |
| `test_v23.js` | 50 pass / 0 fail |
| `test_v25.js` | 63 pass / 0 fail |

### 3. 视口探针（`apk_build/_v27probe.py`，本地 http + CDP，390×844）

```
BOOT       fab=true pill=true oldStrip=false  fabText="🌤 天气"  night=false theme=#0a4e63
FAB RECT   fab[312,10,376,44]  header[0,0,390,86]  vw=390  fabH=34
PILL HIDDEN True
PERM CARD  permacts=1 grant=true  head="天气 · 需要定位权限…"  pillHidden=true
PILL SHOWN hidden=false text="🌧 雨 · 14°C · 降水 85% · 手动 · 更新 15:55"
           fab="🌧 14°" on=true aria-expanded=true
AUTO HIDE  hidden=true aria-expanded=false（1.2 秒后）
SCROLL AWY beforeScroll=false → hiddenAfter=true（滚回顶部即收）
NIGHT      night=true theme=#072e3c body=rgb(13,19,25) header=linear-gradient(135deg,#0d5a70,#072e3c)
           bubble=rgb(24,33,42) ink=rgb(232,239,244)
DAY        night=false theme=#0a4e63 body=rgb(246,241,231)
AUTO       mode=auto hour=15 night=false
LIVE       Open-Meteo 釜山 2026-11-22 16:45 → 7.0°C / code 0 / 风 4.8 m/s
ERRORS     []
```

截图（`Busan/apk_build/`）：

- `v27_home_day.png` — 白天首屏，右上角「🌤 天气」
- `v27_wx_permission.png` — 点按钮后的权限说明卡（允许定位 / 去系统设置）
- `v27_wx_pill.png` — 有数据后点开：右上角「🌧 14°」+ 天气气泡
- `v27_night.png` — 夜间模式（19:00 后自动生效）
- `v27_day_after.png` — 手动切回白天

### 4. 线上验证（GitHub Pages，真实 https）

```
URL        https://luohaisheng814.github.io/AI_Project_2026_2/
SECURE     true
V27        fab=true pillHidden=true fabText="🌤 天气" oldStrip=false
           night=false hour=15 theme=#0a4e63
MANIFEST   200 application/manifest+json; charset=utf-8
SW         registered https://luohaisheng814.github.io/AI_Project_2026_2/
CACHE      ["busan-2.7"]
PERM CARD  permacts=1 grant=true（点右上角按钮 → 线上真实弹出权限说明卡）
NIGHT CSS  true
LIVE       7.0°C / code 0 / 风 4.8 m/s
ERRORS     []
```

截图 `Busan/apk_build/v27_online_pages.png`。发布流水线 `Deploy Web App (PWA)`
run `f9f2978` → **success**；同一次 push 的 `Build iOS` 仍是 `cancelled`（macOS runner 不可用）。

### 5. 未测到的部分

- 没在真 Android 机 / 真 iPhone 上跑（本机无设备、无 Xcode）：APK 只做构建产物级校验，
  系统定位授权弹窗、真机夜间切换的实际观感需装到手机确认一次。
- 探针里用 `BusanUI.setWeather('rain',14)` 模拟“已授权 + 已有天气”的分支，避免依赖无头浏览器定位；
  真机走的是 `BusanHost.requestLocation → CLLocationManager/LocationManager` 这条真实链路（v2.5 起未改动）。

---

## 四、改动文件

```
Busan/android/AndroidManifest.xml            20 / 2.7 + v2.7 注释
Busan/android/java/.../MainActivity.java     注释与 UA 升 2.7
Busan/android/assets/index.html              右上角 #wxFab + #wxPill、权限分支、自动收起、昼夜主题、夜间配色修补
Busan/android/assets/sw.js                   缓存名 busan-2.7
Busan/ios/project.yml                        2.7 / 20
Busan/ios/README.md                          版本说明 2.7
Busan/apk_build/test_v27.js                  新增 50 条断言
Busan/apk_build/test_v26.js                  版本号与天气按钮断言同步
Busan/apk_build/_v27probe.py                 新增 UI/权限/昼夜探针
Busan/apk_build/_v27live.py                  新增线上 Pages 验证脚本
Busan/apk_build/v27_online_pages.png         线上首页截图
Busan/apk_build/_nightfix.py                 夜间样式块一次性生成脚本（留存）
Busan/apk_build/v27_*.png                    5 张证据截图
Busan/pwa/build_pwa.py                       产物名与说明升 v27
Busan/dist/Busan旅行助手.apk                  v2.7 重建
Busan/dist/Busan_iOS_WebApp_v27.zip          新增
```

## 五、复跑命令

```powershell
cd D:\AI_Project_2026_2\Busan
node apk_build/test_v27.js
node apk_build/test_v26.js
node apk_build/test_v25.js
node apk_build/test_v23.js
node apk_build/test_v22.js
node apk_build/test_engine.js
& D:\AI_Project_2026_2\.venv\Scripts\python.exe apk_build/_v27probe.py
& D:\AI_Project_2026_2\.venv\Scripts\python.exe apk_build/_v27live.py      # 验证线上 Pages
& D:\AI_Project_2026_2\.venv\Scripts\python.exe apk_build/build_apk.py
& D:\AI_Project_2026_2\.venv\Scripts\python.exe pwa/build_pwa.py
```

## 六、提交记录

| 提交 | 内容 |
| --- | --- |
| `f9f2978` | feat(mobile): v2.7 天气入口移到右上角 + 按时间昼夜，Android/iOS 同步 2.7 |
| `（本条 docs 提交）` | 回填线上 Pages 验证、截图与复跑命令 |

推送：`62975a2..f9f2978 main -> main` → `https://github.com/luohaisheng814/AI_Project_2026_2`

## 六、下一步（可选）

1. 夜间阈值目前写死 19:00–06:00；若想按季节日出日落走，可接 Open-Meteo 的 `daily.sunrise/sunset`。
2. 气泡 10 秒可按用户习惯在设置里调（已有 `showWeatherPill(ms)` 接口，缺一个入口）。
3. 有 Mac 时用 `Busan/ios/build_ipa.sh` 出未签名 ipa，配合 AltStore 自签安装。
