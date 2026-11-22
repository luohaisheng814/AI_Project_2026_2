# iOS 版（v3.1）构建与安装说明

iOS 版和 Android 版共用**同一套前端**：`Busan/android/assets/`（`index.html`、`app.js`、`cloud.js`、
`weather.js`、`ratings.js`、`photos.js`、54 张实景图等）。壳只是把这份资源装进 WKWebView，
并把网页需要的 `BusanHost` 桥补齐（取网络文本、定位授权与坐标回传、打开系统设置）。

## 现在能装的两个形态

| 形态 | 需要什么 | 说明 |
| --- | --- | --- |
| **PWA（推荐，立即可用）** | iPhone + Safari | 打开 `https://luohaisheng814.github.io/AI_Project_2026_2/` → 分享 → “添加到主屏幕”。有图标、全屏、可离线，前端与 APK 完全同源 |
| **真 `.ipa`** | macOS + Xcode（或能跑 macOS runner 的 CI） | 用本目录工程编译；未签名包需 AltStore / Sideloadly 自签 |

> iOS 不允许侧载未签名 App，Windows 上也编不出 `.ipa`；本仓库的 macOS Actions runner
> 实测三次都是 `cancelled / 0 steps`（账号侧不可用），所以本轮交付 PWA 作为可安装产物，
> 同时把 Xcode 工程升到 3.1 等有 Mac 时直接出包。


## 目录

```
Busan/ios/
├── project.yml                  # XcodeGen 工程定义（引用 ../android/assets 作为 folder reference）
├── build_ipa.sh                 # macOS 一键：生成工程 → 编译 → 打未签名 ipa
├── BusanTour/
│   ├── AppDelegate.swift
│   ├── BusanViewController.swift   # WKWebView + BusanHost 桥 + CLLocationManager
│   └── Info.plist                  # 定位用途说明、ATS、nmap scheme
└── README.md
```

## 为什么这里没有现成的 `.ipa`

`.ipa` 必须用 Xcode（macOS）编译并签名。本机是 Windows，**没有 macOS / Xcode**，
所以这一轮交付的是「可直接编译的 iOS 工程 + 一键脚本 + GitHub Actions macOS 流水线」，
而不是伪造一个装不上的包。产出方式有三条：

1. **Xcode 免费签名（最常用）**：在 macOS 上 `xcodegen generate`，打开 `BusanTour.xcodeproj`，
   选真机运行，用 Apple ID 免费签名，7 天后重签。
2. **未签名 ipa（CI 产出）**：推送后到 GitHub Actions 的 `Build iOS (unsigned ipa)` 下载
   `Busan-unsigned-ipa`；未签名包要装需 AltStore / Sideloadly 自签（免费账号 7 天）。
3. **上架 / TestFlight**：需要付费 Apple Developer 账号，在 Xcode 里配 Team 后 Archive。

本机只做了静态校验（工程 YAML 可解析、Swift 源码结构检查），未在真机编译；
第一次在 macOS 上跑 CI 时若 Xcode 版本报警，按报错调整即可（工程只依赖 UIKit / WebKit / CoreLocation）。

## 编译

```bash
cd Busan/ios
brew install xcodegen        # 只需一次
./build_ipa.sh               # 产出 build/Busan旅行助手-unsigned.ipa
```

或手动：

```bash
xcodegen generate
xcodebuild -project BusanTour.xcodeproj -scheme BusanTour -configuration Release \
  -sdk iphoneos -derivedDataPath build/DerivedData \
  CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO CODE_SIGN_IDENTITY="" build
```

## 与 Android 的行为差异

| 能力 | Android | iOS |
| --- | --- | --- |
| 天气 | 定位 + Open-Meteo | 同（`fetchText` 走 URLSession 桥） |
| 定位 | LocationManager 每 3 秒/12 米 | CLLocationManager，同参数 |
| 星级 / 自评 | localStorage | localStorage |
| 云端大模型 | 原生桥直连 | 网页 `fetch` 直连（同一免费端点） |
| NAVER 深链 | `nmap://` Intent | `UIApplication.open(nmap://)`，未装则落浏览器 |

天气在 iOS 上和 Android 一样：系统没有“天气权限”，读天气需要定位授权；
拒绝授权时按釜山市区坐标取，或在天气卡里手动选晴/雨/大风。

## 校验清单（macOS 首次构建时）

- [ ] `assets/index.html` 在 bundle 的 `assets/` 目录下（folder reference 生效）
- [ ] 首次进入弹出定位授权，允许后天气条出现温度
- [ ] 拒绝定位 → 天气条显示“默认位置”，天气卡仍能手动选天气
- [ ] 景点回答出现星级块，点星后刷新仍保留
- [ ] 点 NAVER 路线按钮能跳到 NAVER Map

