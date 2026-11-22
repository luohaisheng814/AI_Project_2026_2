# 釜山 AI 旅行助手 · v2.6 更新日志

- 日期：2026-11-22
- 版本：**v2.6**（Android `versionCode 19 / versionName 2.6`，iOS `MARKETING_VERSION 2.6 / CURRENT_PROJECT_VERSION 19`）
- 上一版：v2.5（weather / 星级 / iOS 壳工程）
- 分支：`main` → `https://github.com/luohaisheng814/AI_Project_2026_2`

---

## 一、本轮做了什么

### 1. 手机版 UI 收口（不删信息，只补细节）

| 项 | 变化 | 为什么 |
| --- | --- | --- |
| 深色模式 | `@media (prefers-color-scheme: dark)` 整套变量重定义，覆盖顶栏、选择条、状态条、气泡、卡片、选项卡、评分块、天气卡、输入区、弹层 | 夜里在户外看路线不刺眼；跟随系统，不用额外开关 |
| 平板/宽屏 | `>=700px` 时 `body` 限宽 560px 居中，气泡 86%，聊天区内边距 14px | 平板上原来一行太长，读起来费眼 |
| 窄屏 | `<=360px` 收 header/聊天区内边距，气泡 92%，图片条缩到 112×76 | 小屏不再左右挤爆 |
| 触控尺寸 | 发送/图标按钮 40px，`.choice` 44px，chip 37px，`.pick` 34px，状态条“实时/天气”34×56px，星级按钮 28px | 手指点得准；同时满足 iOS 44pt 主操作底线 |
| 输入框 | `#q` 字号固定 16px | iOS Safari 聚焦不再自动放大页面 |
| 页面回弹 | `overscroll-behavior-y:none`、`-webkit-text-size-adjust:100%` | 全屏 PWA 里不露白、不抖 |
| 入口 | 欢迎语新增「今天天气适合去哪」，直接拉起天气卡 | 让天气能力一眼可见 |

> 上一轮计划过的“实时/天气两条状态合并成一行”**已放弃**：360px 机型每段只剩约 180px，
> 会把“实时定位未开启 · 开启后显示到景点距离”截断，属于信息损失。

### 2. PWA：iPhone 上真正能“装”的形态

新增：

- `Busan/android/assets/manifest.webmanifest`（name / short_name / standalone / 主题色 / 3 个图标）
- `Busan/android/assets/sw.js`（离线缓存；**导航与 HTML 走网络优先**，保证发版即时生效；
  跨域请求（Open-Meteo 天气、云端库）不缓存）
- `index.html` 的 `<head>` 增加 `theme-color`、`apple-mobile-web-app-*`、`apple-touch-icon`、
  `manifest`、`format-detection`
- 应用图标 180 / 192 / 512（1024 只留在 `Busan/pwa/`，不进 APK，避免安装包白胖 1.7MB）
- `.github/workflows/pages.yml`：把 `Busan/android/assets` 发布到 GitHub Pages

安装路径（iPhone / iPad）：Safari 打开
`https://luohaisheng814.github.io/AI_Project_2026_2/` → 分享 → **添加到主屏幕**。
得到带图标、全屏、断网可用的 App，前端与 APK 同一套代码、同一版本号。

### 3. iOS 工程同步升到 2.6

- `project.yml`：`MARKETING_VERSION 2.6`、`CURRENT_PROJECT_VERSION 19`
- 新增 `Assets.xcassets/AppIcon.appiconset`（1024 图标）+ `CFBundleIconName=AppIcon`，
  有 Mac 编译时桌面图标不再是空白
- `Info.plist` 版本号仍走 `$(MARKETING_VERSION)/$(CURRENT_PROJECT_VERSION)`，与 Android 同源

### 4. Android 安装包

- `AndroidManifest.xml`：`versionCode 19 / versionName 2.6`，顶部补 v2.6 变更注释
- `MainActivity.java`：类注释升 2.6，`User-Agent: BusanTour/2.6 (Android)`
- 重建签名 APK：`Busan/dist/Busan旅行助手.apk`

---

## 二、交付物

| 产物 | 路径 | 大小 | SHA-256 |
| --- | --- | --- | --- |
| Android 安装包 | `Busan/dist/Busan旅行助手.apk` | 10,590,192 B | `0F09737FD12FE5131EE31A5C65440307444796B5B07E370AEB604597607D1477` |
| iOS 网页安装包 | `Busan/dist/Busan_iOS_WebApp_v26.zip` | 10,477,199 B | `F8AF9F4E118CCF82291AB443985A5F0A47A55EE94CCD19A723F2C3D9D8BF97CF` |
| PWA 在线地址 | `https://luohaisheng814.github.io/AI_Project_2026_2/` | — | Pages 流水线发布 |

APK 校验：`apksigner verify` 通过（v1+v2 签名），证书 `CN=Busan Travel Assistant`，
SHA-256 `9d91ed6b…33356`；`aapt2 dump badging` 读出 `versionCode='19' versionName='2.6'`、
`minSdk 21 / targetSdk 34`、`package com.busan.tour`。
包内 `assets/index.html`、`sw.js`、`manifest.webmanifest`、`icon-*.png` 与源码**逐字节一致**。

### 关于 iOS “安装包”，必须说清楚

- `.ipa` 只能由 macOS + Xcode 编译并签名；本机是 Windows，**编不出来**。
- 仓库里 `Build iOS (unsigned ipa)` 这条 macOS 流水线，本轮之前已连续 3 次
  `completed / cancelled`、`steps=0`（`936d2f0`、`a929440` 两次 push + 一次手动 dispatch），
  是账号侧 macOS runner 不可用，不是 YAML 写错。所以 CI 也产不出 ipa。
- 因此本轮给的是 **PWA**：iPhone 上可安装、有图标、可离线，代码与 APK 完全同源；
  同时 `Busan/ios` 工程升到 2.6，等有 Mac 或 macOS runner 恢复时，直接
  `xcodegen generate && ./build_ipa.sh` 就能出未签名 ipa（自签安装 7 天有效）。

---

## 三、测试

### 1. 静态断言（新增 `apk_build/test_v26.js`）

```
PASS 74 / FAIL 0
```

覆盖：PWA 元信息与 manifest 字段、图标真实像素（180/192/512/1024）、sw 预缓存清单逐文件存在、
深色/宽屏/窄屏/触控 CSS、天气快捷入口、SW 注册条件、双端版本号、旧版本残留、v2.5 能力保留。

### 2. 历史套件回归

| 套件 | 结果 |
| --- | --- |
| `test_engine.js` | ✅ 离线引擎全部断言通过 |
| `test_v22.js` | 43 pass / 0 fail |
| `test_v23.js` | 50 pass / 0 fail |
| `test_v25.js` | 63 pass / 0 fail |
| `test_cloud_round.js` | 正常产出（步行难度 4/5、改荐“多大浦梦之夕阳喷泉”） |

### 3. 真机视口探针（`apk_build/_v26probe.py`，本地 http 起服务，CDP 驱动 Chrome）

```
MODULES   ui/wx/rt/live 全部 true，快捷入口 5 个
MANIFEST  200 application/manifest+json
          name=釜山 AI 旅行助手 short=釜山助手 display=standalone icons=3
SW        registered scoped http://127.0.0.1:8791/
CACHE     keys=["busan-2.6"]   index cached
ICONS     180/192/512 全部 200
WXCHIP    clicked 今天天气适合去哪
WXCARD2   chips=8 choices=3  bar=🌧 雨 · 14°C · 降水 85% · 手动
SPOT      rating=true  ★4.3 值得一去
GEOM      bubble[12,334] choice[24,322] cgo[273,313]  scrollW=390 clientW=390 scrollX=0（无横向溢出）
DARK      bubble rgb(24,33,42) / ink rgb(232,239,244) / input rgb(26,35,44) / #q 16px
WIDE      bodyW=560 screenW=820 left=130（居中生效）
NARROW    screenW=360 scrollW=360 chatPad=9px choiceH=51 sendH=40
TOUCH     send 40 / chip 37 / pick 34 / live 34 / wx 34
LIVE      Open-Meteo 釜山实况 2026-11-22 16:15 → 7.4°C，code 0，风 6 m/s
ERRORS    []
```

截图（`Busan/apk_build/`）：

- `v26_home_iphone.png` — 390×844 iPhone 首屏（新快捷入口）
- `v26_weather_card.png` — 天气卡按时段推荐 + 8 个手动 chip
- `v26_dark.png` — 深色模式（官网链接、选项卡对比度已修）
- `v26_wide_tablet.png` — 820×1180 平板单列居中
- `v26_narrow_360.png` — 360×740 窄屏不横向溢出

### 4. 未测到的部分（如实说明）

- 未在真 Android 机 / 真 iPhone 上跑（本机无设备、无 Xcode）。APK 只做了构建产物级校验
  （签名、版本、包内资源一致性），安装与定位权限的实际表现需在手机上验证。
- PWA 的“添加到主屏幕”需在 iOS Safari 里手动确认一次；Chrome 侧已验证 manifest、SW、
  离线缓存与图标齐全，iOS 侧行为按 Apple 的 PWA 规范实现（`apple-mobile-web-app-capable` 等）。

---

## 四、改动文件

```
.github/workflows/pages.yml                        新增：发布 GitHub Pages
Busan/android/AndroidManifest.xml                  19 / 2.6 + 注释
Busan/android/assets/index.html                    深色/宽屏/窄屏/触控/输入框 + PWA head + SW 注册 + 天气快捷入口 + 深色链接色
Busan/android/assets/sw.js                         新增：离线缓存（HTML 网络优先）
Busan/android/assets/manifest.webmanifest           新增
Busan/android/assets/icon-180/192/512.png           新增
Busan/android/java/com/busan/tour/MainActivity.java 注释 2.6、UA 2.6
Busan/ios/project.yml                              2.6 / 19 + AppIcon
Busan/ios/BusanTour/Info.plist                     CFBundleIconName
Busan/ios/BusanTour/Assets.xcassets/…              新增 AppIcon 资源集（1024）
Busan/ios/README.md                                2.6 + PWA 安装说明
Busan/apk_build/test_v26.js                        新增 74 条断言
Busan/apk_build/_v26probe.py                       新增 UI/PWA 探针
Busan/apk_build/make_icon.py                      图标输出路径调整（1024 移出 assets）
Busan/pwa/build_pwa.py                             新增：打 iOS 网页安装包
Busan/dist/Busan旅行助手.apk                        v2.6 重建
Busan/dist/Busan_iOS_WebApp_v26.zip                新增
```

## 五、复跑命令

```powershell
cd D:\AI_Project_2026_2\Busan
node apk_build/test_v26.js                     # 74 条静态断言
node apk_build/test_v25.js                     # 天气/星级回归 63 条
node apk_build/test_v23.js                     # 50 条
node apk_build/test_v22.js                     # 43 条
node apk_build/test_engine.js                  # 离线引擎
& D:\AI_Project_2026_2\.venv\Scripts\python.exe apk_build/_v26probe.py   # 出 5 张截图 + 控制台指标
& D:\AI_Project_2026_2\.venv\Scripts\python.exe apk_build/build_apk.py   # 重建 APK
& D:\AI_Project_2026_2\.venv\Scripts\python.exe pwa/build_pwa.py         # 重打 iOS 网页包
```

## 六、下一步（可选）

1. 借一台 Mac（或恢复 macOS runner）跑 `Busan/ios/build_ipa.sh`，出未签名 ipa 并用 AltStore 自签。
2. 若要把 PWA 变成“像原生一样”的入口，可在 Pages 域名上继续加 `apple-touch-startup-image`，
   去掉启动白屏。
3. iOS CI 若一直 cancelled，可考虑换到 `macos-13` 或自建 runner 再试一次；本轮未再消耗次数。
