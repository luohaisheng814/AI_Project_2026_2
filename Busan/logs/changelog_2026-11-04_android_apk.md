# Changelog — 2026-11-04 Busan 独立安卓安装包（APK）：无 SDK 环境下自建工具链 · 离线三语问答引擎

## 本次目标
1. 把 Busan 从「必须开电脑、跑 Python 服务、手机连同一 WiFi 才能用」的形态，做成**单独的手机软件**：装到安卓手机上点开就能用，不依赖电脑、不依赖网络；
2. 当前机器**没有** Android SDK、没有 Gradle、没有 Android Studio，只有 JRE 无 JDK —— 需要先在本地把构建工具链装配起来，并且不引入 Gradle/AGP 这种联网依赖很重的方案；
3. 桌面版的三大规则必须原样保留在安装包里：**回复语言只由顶部中文 / 한국어 / English 按钮决定**；**选定玩法后该玩法文件夹是唯一主数据源，其它玩法只在补充推荐里出现且限 2 条、标玩法与理由、排主推荐之后**；**GPS 附近景点按距离升序**；
4. 生成可安装的 APK（含图标、应用名、签名），推送 GitHub 仓库，并生成本日志。

## 环境现实与方案选择
| 现状 | 影响 | 本轮做法 |
|------|------|----------|
| `java` 只有 JRE（`...\Oracle\Java\javapath\java.exe`），`javac` / `gradle` / `adb` / `sdkmanager` 全部 NOT_FOUND | 无法编译 Java 源码，Gradle 方案也起不来 | 下载 Adoptium **Temurin JDK 17** 到 `D:\AndroidBuild\jdk17`，只在本项目脚本里注入 `JAVA_HOME` / `PATH`，不改系统环境变量 |
| `ANDROID_HOME` / `ANDROID_SDK_ROOT` 为空 | aapt2 / d8 / zipalign / apksigner 都不存在 | 下载 `commandlinetools-win-11076708`，用 `sdkmanager` 装 `platforms;android-34`、`build-tools;34.0.0`、`platform-tools`，全部接受 license |
| 仓库里原有 `build.yml` 是 Kivy/Buildozer 的 APK workflow | 它放在仓库根目录（不在 `.github/workflows/`），且 `workdir: 釜山` 指向不存在的目录 —— **从来没生效过**，不能当 APK 方案 | 放弃该方案，改用 build-tools 自带工具的手工流水线（见下），并保留该文件不动（避免误删历史产物） |
| WebView `file://` 下 `fetch('data.json')` 被 CORS 拦 | 装到手机上后页面读不到数据 | 数据同时导出为 `data.js`（`window.BUSAN_DATA=...`）由 `<script>` 注入，`data.json` 仅作可读备份 |
| 桌面版靠 LLM 读整篇景点 txt 再作答 | 手机上不能联网调 LLM | 新增离线解析器把每篇 txt 拆成独立字段，问题命中字段后直接输出；三语内容**预先翻译好**内置进包 |

## 构建流水线（APK 怎么来的）
`apk_build/build_apk.py` 一条命令跑完，不依赖 Gradle：

```
aapt2 compile  →  aapt2 link（-A assets / --java 生成 R.java）
               →  javac（-source 8 -target 8，classpath android.jar）
               →  d8（--min-api 21，产出 classes.dex，写回 base.apk）
               →  zipalign -f -p 4
               →  apksigner sign（v1 + v2）
               →  apksigner verify --print-certs
```

关键点：`d8.bat` / `apksigner.bat` / `keytool` 都是 JDK 的封装，脚本启动时先把 `JAVA_HOME` 和 `JDK\bin` 注入 `os.environ`，否则会报「找不到 java」。首次构建自动用 `keytool` 生成签名证书（RSA 2048、有效期 10000 天），之后复用同一证书，保证同一台机器上覆盖升级安装不被拒。

## 改动文件
| 文件 | 改动 |
|------|------|
| `Busan/apk_build/setup_toolchain.ps1` | 新增。一键装配 JDK 17 + commandline-tools + `android-34` / `build-tools;34.0.0` / `platform-tools`，装到 `D:\AndroidBuild`（可用 `-Root` 改盘），装完逐个 `Test-Path` 校验；换机器时照此复现，不用再摸索一遍。 |
| `Busan/apk_build/export_assets.py` | 新增。用 `rag_core.KnowledgeBase` 汇总 8 个景点，自建 `parse_offline_fields()` + 约 60 条 `OFFLINE_LABEL_MAP` 把原始 txt 拆成字段（原始文件混用「标签：」「标签」「标签：内容」三种写法，不补映射就只剩 1~3 个字段）；逐条调 `core_api.complete()` 预翻译成韩 / 英文，按 `sha1(lang|text)` 缓存到 `apk_build/cache/translate.json`，重跑只翻新增文本；产出 `data.json` + `data.js`；新增 `NAME_FIX` 人工校订表兜底景点三语名。 |
| `Busan/apk_build/gen_res.py` | 新增。PIL 生成 5 组 `mipmap-*/ic_launcher.png`（48/72/96/144/192，逐行渐变海蓝 + 圆角 + 落日 + 三道浪 + 灯塔剪影）与 `res/values/strings.xml`（`app_name=釜山旅行助手`）。 |
| `Busan/apk_build/build_apk.py` | 新增。上述流水线；带 `--export` 可先重新导出数据再打包；缺工具时直接报出具体缺失路径。 |
| `Busan/apk_build/test_engine.js` | 新增。Node 直接加载 `android/assets/data.js` + `app.js`，12 组断言覆盖三语字段键一致、意图识别（含新增 highlights）、景点匹配、玩法作用域、跨类补充上限与跨语言顺序稳定、GPS 排序、未知景点清单、后续问题不重复。 |
| `Busan/android/AndroidManifest.xml` | 新增。`package com.busan.tour`、versionCode 1 / versionName 1.0、minSdk 21 / targetSdk 34、`Theme.NoTitleBar`；**只申请 `ACCESS_FINE_LOCATION` + `ACCESS_COARSE_LOCATION`，刻意不申请 `INTERNET`**，让「离线」成为系统级事实而不是宣传语。 |
| `Busan/android/java/com/busan/tour/MainActivity.java` | 新增。纯 WebView 壳：加载 `file:///android_asset/index.html`，开 JS / DOMStorage / fileAccess / geolocation，`onGeolocationPermissionsShowPrompt` 直接授予定位；http(s) 交给 WebView，其余 scheme 交系统；返回键先 `canGoBack()` 再退出；`onDestroy` 销毁 WebView。 |
| `Busan/android/assets/app.js` | 新增（约 400 行，UMD：`module.exports` + `window.BusanEngine`）。移植 `intent_parser.py` 的 13 条意图规则（三语关键词）、玩法 / 人数关键词、停用词、问题模板与追问顺序；实现 `detectField / inferCategory / inferGroup / matchSpot / crossSupplements（上限 2、跨玩法轮询）/ answer / nearby（Haversine，≤15km 升序）/ setLang / getState / setState`。手动锁定玩法后问其它玩法的景点时**不越界作答**，返回 `switchTo` 交给界面弹「切换玩法」按钮。 |
| `Busan/android/assets/index.html` | 新增。移动端单页：海蓝渐变头部 + 三语按钮 + 玩法 chip 行（含「自动」）+ 出行人数 chip 行（含「自动」）+ 状态栏 + 聊天气泡 + 后续问题 chip + 底部输入框 /「附近」/「发送」。语言或选择变化时 `rerenderAll()` 清空对话并按历史提问顺序用新设定逐条重生成；`md()` 负责 `### / ** / --- / - ` 的最小 Markdown 渲染。 |
| `Busan/android/assets/data.json` / `data.js` | 新增（各 72.3 KB）。8 个景点 × 三语字段 + 4 玩法三语名 + 6 人数三语名 + 三语字段名 / 字段顺序 + 全量界面文案 + 分类级「适合人群」。 |
| `Busan/android/res/**` | 新增。5 组启动图标 + `strings.xml`。 |
| `Busan/dist/Busan旅行助手.apk` | 新增，**125.0 KB**，已签名并校验（明细见「验证清单」）。 |
| `.gitignore` | 追加 `Busan/apk_build/build/`、`cache/`、`keystore/`、`*.idsig`：中间产物与**签名私钥不进仓库**，避免公开仓库泄露签名密钥。 |
| `Busan/logs/changelog_2026-11-04_android_apk.md` | 本日志。 |

## 核心实现说明
### 1. 为什么必须是「离线」而不是「连电脑」
上一轮的 `Busan_Tour_App.zip` 方案是：手机浏览器打开 `mobile_app.py` 起的服务，电脑必须开机、手机必须同网段。这一轮改成**真安装包**：所有景点资料、三语译文、界面文案都压进 APK 的 `assets/`，运行时只读本地文件，`AndroidManifest.xml` 里连 `INTERNET` 权限都没申请 —— 装上之后飞行模式也能问。

### 2. 离线问答引擎如何对齐桌面版规则
- **语言**：`state.lang` 只由顶部按钮改变，`answer(question, {lang})` 的 `lang` 就是按钮语言；检索永远用中文数据（`fields.zh` 才是唯一事实源），输出时按按钮语言取 `fields[lang]`。因此「中文按钮 + 韩文提问」会命中同一个景点、用中文作答，和桌面版口径一致。
- **玩法作用域**：`state.autoCategory=false` 时，主回答只在当前分类的景点里找；问到的景点属于别的玩法时返回 `switchTo`，界面给「切换到 XX 玩法」按钮，不偷偷用别的玩法的数据作答。
- **跨类补充**：`crossSupplements` 轮询其它三个分类，最多 2 条，一定排在本体回答之后，并标注所属玩法与理由（理由按人数档位变化，未选人数时用中性称呼）。
- **GPS**：`nearby(lat, lng, 15km)` 用 Haversine 算直线距离并按升序输出；坐标取自景点档案，见「已知限制」。

### 3. 数据解析为什么要自己写一套
桌面版可以把整篇 txt 塞给 LLM，让模型自己找答案；离线版没有模型，必须让程序知道「这句话属于哪个字段」。原始 txt 的标签写法并不统一：
- `标签：` 后接多行块（主流写法）；
- `标签` 单独一行、无冒号（如 04 长林浦口的「基本概况 / 游玩亮点 / 周边配套 / 交通」）；
- `标签：内容` 全在一行（如 `docs/gamcheon.txt` 的 介绍 / 交通 / 开放信息 / 来源网址）。

第一次导出按旧解析器只拿到 3 个（没云台）到 1 个（长林浦口）字段，补 `OFFLINE_LABEL_MAP` 之后变成：甘川 9 / 梦之夕阳喷泉 6 / 海水浴场 9 / 没云台 8 / 乙淑岛 9 / 峨嵋山 8 / 洛东江 9 / 长林浦口 4。桌面端 13 个字段之外，离线端额外加了 `highlights（游玩亮点）`，因为档案里「游玩亮点」是独立块，硬塞进 overview 会丢掉结构。

### 4. 预翻译而不是运行时翻译
手机上不联网，所以韩 / 英内容必须是**构建期**生成的。`export_assets.py` 对每个景点的每个字段各调用一次批量翻译（一次请求翻一整篇的字段，不是一字段一次），并把结果按 `sha1(lang|文本)` 缓存，重跑不会重复花钱；翻译失败会明确打印「翻译 N 段，成功 M 段」，本轮 8 个景点全部 100% 成功、每景点三语字段数与中文完全一致。

## 使用方式
```powershell
# 一、装配工具链（换机器时只需一次；本机已装好）
powershell -ExecutionPolicy Bypass -File Busan\apk_build\setup_toolchain.ps1

# 二、（可选）改完景点 txt 后重新导出数据与译文
python Busan\apk_build\export_assets.py

# 三、回归测试离线引擎
node Busan\apk_build\test_engine.js

# 四、打包（产出 Busan\dist\Busan旅行助手.apk）
python Busan\apk_build\build_apk.py
```

装到手机：
1. 把 `Busan\dist\Busan旅行助手.apk` 传到手机（微信文件传输 / 数据线 / 网盘均可）；
2. 点击安装，系统提示「未知来源应用」时允许一次（这是自签名应用，未上应用商店）；
3. 打开「釜山旅行助手」，首次点「附近」会弹定位授权，允许后按距离列出景点。

## 验证清单（本轮已执行）
| 项目 | 方法 | 结果 |
|------|------|------|
| JDK 可用 | `java -version` / `javac -version` | Temurin 17.0.21 / javac 17.0.21 |
| SDK 三件套 | `Test-Path` 逐个确认 | `android.jar`、`aapt2.exe`、`adb.exe` 均存在 |
| 数据字段完整性 | 导出日志逐景点打印字段名 | 8 景点，字段 4~9 个，三语键完全一致 |
| 预翻译成功率 | 导出日志 `[ko]/[en] 翻译 N 段，成功 N 段` | 全部 N/N |
| 离线引擎回归 | `node apk_build\test_engine.js` | 12 组断言全绿：三语命中、玩法不越界、补充 ≤2 且跨语言顺序一致、GPS 升序（没云台 0.0km / 海水浴场 0.9km / 峨嵋山 1.9km / 乙淑岛 9.8km / 洛东江 10.0km） |
| 包信息 | `aapt2 dump badging` | `com.busan.tour` v1 / 1.0，minSdk 21，targetSdk 34，label「釜山旅行助手」，仅两条定位权限、**无 INTERNET** |
| 包内容 | `zipfile` 逐条列出 + `testzip` | 15 条目；`classes.dex` 头 `dex\n035`；`assets/{index.html,app.js,data.js,data.json}` 齐全；zip 完整性 OK |
| 签名 | `apksigner verify --print-certs` | v1+v2 通过；`CN=Busan Travel Assistant, OU=Local, O=Busan, L=Busan, C=KR`；SHA-256 `9d91ed6b8ffeec5eaf5b597ee19f56bfda6f8663d94ec726390a552224d33356` |
| 界面渲染与交互 | 浏览器打开 `android/assets/index.html`（同一套资源）实跑 | 中文首屏正常；提问「没云台 怎么去」→ 自动切到 02 玩法、输出交通小节、补充推荐 2 条；切 한국어 → 整段重生成为韩文（한글景点名、교통 小节）；切 English → 英文景点名与 Transportation 小节，补充推荐显示 `Gamcheon Culture Village (01 …)` |
| 排版修正 | 同上，截图复核 | 修掉了正文连续空行撑出的空档、后续问题 chip 挤压截断（改为自动换行 + 可滚动）、韩文里混入的中文全角括号 |

## 已知限制（如实记录）
1. **未在真机 / 模拟器上安装运行**。本机 `adb devices` 为空（没有连接安卓设备），也没有安装模拟器。已做的验证是：APK 结构、签名、权限、资源表全部静态校验通过，且**界面与引擎在同源资源上的浏览器实跑通过**。真机上仍可能存在单纯 WebView 才暴露的问题（如 `file://` 下定位回调时机、系统字体导致的排版差异），首次安装后建议实测一次。
2. **没云台的坐标未精校**。`没云台.txt` 原文自带「坐标：35.0510, 128.8820（入库前请用 Naver 精校）」，本轮直接用了这个值做 GPS 距离排序，没有去 Naver 复核。若坐标有偏差，「附近」列表的距离数值会跟着偏。
3. **只有 8 个景点**。离线包内置的就是 `activity_classified` 里已有的 8 个景点（甘川 / 梦之夕阳喷泉 / 海水浴场 / 没云台 / 乙淑岛 / 峨嵋山 / 洛东江 / 长林浦口）。库里没有的景点会返回「当前玩法收录景点」清单，不会编造。
4. **离线版没有自由文本生成能力**。桌面版能靠 LLM 组织语言、跨字段综述；安装包是「字段命中 + 模板拼装」，问法超出 13 条意图规则时会落到 overview 或全字段输出，不会像 LLM 那样灵活改写。
5. **签名私钥不进仓库**。`apk_build/keystore/busan-release.jks` 已在 `.gitignore` 中。仓库里的 APK 可正常安装，但别人重新构建会生成自己的证书；**换证书后无法覆盖安装旧版本，必须先卸载**。
6. **`Busan/build.yml`（Kivy/Buildozer）仍在仓库里，且依然是失效状态**。本轮没有删它（属于历史文件），但不要再指望它产出 APK。
7. **不支持 iOS**。本轮只做安卓 APK。
