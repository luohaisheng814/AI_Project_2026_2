# Changelog — 2026-11-05 安卓模拟器实测：修掉三个真机才暴露的致命问题 · 数据与排版收口

## 本次目标
上一轮交付了 APK，但**没有在真机 / 模拟器上跑过**（当时 `adb devices` 为空）。本轮用雷电模拟器把它装上、点开、逐个功能点验，把「真机上才暴露」的问题修掉，再重新打包、推送 GitHub、生成日志与 PPT。

1. 用雷电模拟器 14 当作手机端测试环境，把 APK 装上并走通三语问答、附近定位、追问 chip、返回键；
2. 修掉模拟器上暴露的全部问题（闪退 / 定位必失败 / 重复渲染 / 界面文案污染）；
3. 数据侧收口：景点短名匹配、概览与各字段里的「中文名 / 韩文名 / 坐标」元信息清理；
4. 重新导出数据、重新打包、静态校验，再在模拟器上复测；
5. 推送 GitHub 仓库并生成本日志。

## 测试环境（本轮实机口径）
| 项目 | 值 |
|------|-----|
| 模拟器 | 雷电模拟器 14（`D:\leidian\LDPlayer14`，`ldconsole.exe`） |
| 实例 | index 0，`adb` 序列号 `127.0.0.1:5555` |
| 分辨率 / 密度 | 1080×1920，320 dpi（竖屏，用 `--resolution 1080,1920,320` 三段式改写后 `quit` → `modify` → `launch` 才生效） |
| 系统 | Android 14（SDK 34），x86_64 |
| 安装 / 启动 | `adb install -r`（会先打印 `IllegalArgumentException: Incremental installation not allowed` 再 `Success`，属正常）→ `am start -W -n com.busan.tour/.MainActivity` |
| 虚拟定位 | `ldconsole locate --index 0 --LLI 129.0510,35.0510`（**经度在前**） |

## 真机暴露的问题与根因
### 问题 1：装得上、点开就闪退
- 现象：安装成功后点图标，桌面停留一瞬又退回，界面根本没出现。
- 根因：`build_apk.py` 的 `d8` 只把 `MainActivity.class` 与 `R.class` 显式喂给 dexer，`WebViewClient` / `WebChromeClient` 的匿名内部类被编译成 `MainActivity$1.class`、`MainActivity$2.class`，**没有进 dex**；运行时 `ClassNotFoundException: com.busan.tour.MainActivity$1` → `Force finishing activity`。
- 上一轮为什么没发现：当时只做了包结构、签名、权限的静态校验，浏览器里跑的是 HTML/JS，压根走不到这段 Java 代码。
- 修复：`d8` 改为 `os.walk` 递归收集全部 `*.class`；签名后再用 `dexdump -f` 把 class 逐个换算成 `Lcom/busan/tour/Xxx;` 描述符比对，缺一个就 `SystemExit`。现在 d8 实际吃进 8 个 class（`MainActivity`、`MainActivity$1`、`MainActivity$2`、`MainActivity$LocationBridge`、`MainActivity$LocationBridge$1`、`R`、`R$string`、`R$mipmap`）。

### 问题 2：点「附近」必定失败，且不弹授权框
- 现象：点「附近」→「定位不可用：请在系统设置里允许定位…」，系统授权弹窗一次都没出现。
- 根因：`AndroidManifest.xml` 里只**声明**了 `ACCESS_FINE_LOCATION` / `ACCESS_COARSE_LOCATION`，Android 6+ 还必须在运行时 `requestPermissions`。壳里只有 `WebChromeClient.onGeolocationPermissionsShowPrompt`（那只管 WebView 内部的站点授权策略），所以 `navigator.geolocation` 直接拿到 `PERMISSION_DENIED`。
- 修复（`MainActivity.java`）：新增 `LocationBridge`（`@JavascriptInterface public void requestLocation()`，在 `runOnUiThread` 里判断 `hasLocationPermission()`，没授权就 `requestPermissions(..., REQ_LOCATION=1001)`）；`hasLocationPermission()` 对 SDK<23 直接放行、否则 `checkSelfPermission` 任一已授予即通过；`onRequestPermissionsResult` 无论通过还是拒绝都回调 `notifyLocReady()`；`notifyLocReady()` 用 `web.evaluateJavascript("window.__busanLocReady && window.__busanLocReady();")` 把控制权交回页面；`addJavascriptInterface(new LocationBridge(), "BusanHost")`。
- 修复（`index.html`）：抽出 `locateOnce()`（`timeout=10000`、`maximumAge` 由 600000 收到 60000），新增 `window.__busanLocReady`；「附近」按钮优先走 `window.BusanHost.requestLocation()`，2 秒没等到回调再兜底 `locateOnce()`；桌面浏览器没有桥时直接 `locateOnce()`。
- 复测：授权弹窗正常出现（「要允许"釜山旅行助手"获取此设备的位置信息吗？」），允许后能拿到坐标。

### 问题 3：「附近」重复渲染 + 没近处景点只给一句「没有」
- 现象 A：同一次点击出现**两条完全相同**的「附近景点（按直线距离）」列表 —— 兜底 `setTimeout(locateOnce)` 与授权回调 `__busanLocReady` 各触发了一次取坐标。
- 现象 B：模拟器初始定位在北京，15km 内没有任何收录景点，界面只剩一句「附近 15 公里内没有收录的景点」，等于没有可用信息。
- 修复：用 `locBusy`（正在取坐标）+ `locWaiting`（等授权回调）两个标志；`__busanLocReady` 只在 `locWaiting` 为真时处理一次并置 false；按钮点击时若二者任一为真直接 return。
- 修复：渲染抽成 `renderNearby(lat,lng)`；15km 内无结果时降级调用新增的 `E.nearestAny(lat,lng,3)`，三语文案 `nearbyFar`（「15 公里内没有收录景点，按直线距离最近的 N 个是：」）；失败回调按 `err.code === 1` 区分「权限被拒」与「超时」，不再统一吞成一句「定位不可用」。
- 复测：只出一条；按 `ldconsole locate` 设定的坐标排序正确 —— 甘川 8.5 / 洛东江河口生态中心 9.8 / 乙淑岛 9.9 / 峨嵋山 14.0 / 多大浦 14.6 公里。

### 问题 4：韩文回答里残留中文类别标题
- 现象：切「한국어」问 `Molundae sunset`，整篇韩文正常，但「추천 대상」下面残留中文标题「🏝 海岸休闲 & 日落夜景类」。
- 根因：`activity_classified/<分类>/适合人群_한국어.txt`、`_English.txt` 第一行沿用中文标题行，`export_assets.py` 的 audience 正则把整块取走。
- 修复：audience 提取后剔掉同时含「类」与「&」的行，再去掉 `适合人群|추천 대상|Target audience` 前缀（`re.I`）。复测「추천 대상」为纯韩文「커플, 가족, 바다·야경 선호 관광객」。

### 问题 5：英文界面只打半截景点名匹配不到
- 现象：切 `English` 问 `Gamcheon admission`，答的不是甘川门票，而是当前玩法「02 Coastal Leisure · Sunset」的景点清单。
- 根因：`aliases` 里只有全名 `Gamcheon Culture Village`，没有 `Gamcheon` 这种短名；`matchSpot` / `matchSpotAnywhere` 都是整串包含匹配，于是「景点不存在」，落到列表兜底分支；同时 8 个景点里有 3 个（峨嵋山 / 洛东江 / 长林浦口）的别名**完全没有英文名**，英文用户按正式名也问不到。
- 修复（`export_assets.py`）：① 三语正式名（`name_ko` / `name_en`）一律并入 `aliases`；② 新增 `add_short_aliases()`，为每个景点推导「短名候选」——英文名首词（长度 ≥5 且不是 Sunset / Beach / Park 这类通用词）、韩文名首词、中文名前 2~3 字 —— 并且**只在不会指向别的景点时才采用**（用全库前缀比对去重）。
- 结果：甘川新增 `Gamcheon`、`甘川`；乙淑岛新增 `Eulsukdo`、`乙淑`；峨嵋山补上 `Amisan` / `Amisan Observatory`；洛东江补上 `Nakdong`；长林补上 `Jangnim` / `장림포구`。复测 `Gamcheon admission` → 命中甘川、自动切到 01 玩法、输出 Tickets & Fees 小节。

### 问题 6：列表与详情里混进「中文名 / 韩文名 / 类别 / 地址 / 坐标」元信息
- 现象：英文列表项显示 `Sunset Fountain of Dream: Chinese Name: Dream Sunset Fountain (…)`、`Molundae: Chinese Name: Meiyun Terrace`。
- 根因：源档案每篇都有「基本信息：」块（中文名 / 韩文名 / 类别 / 地址 / 坐标 / 电话 / 官网 / 距离金海机场），解析时整块并入 `overview`；翻译后变成 `Chinese Name:` / `Korean Name:` / `Category:` 等英文标签行，而列表首行、详情首段都取 `overview` 第一行。
- 修复：`overview` 只保留地址 / 电话 / 官网 / 机场距离（`clean_overview`）；新增 `strip_meta_lines()` 把名字 / 别名 / 类别 / 坐标这几类标签行从**所有字段、所有语言**里剔掉（含 `중문명 / 한글명 / Chinese Name / Korean Name / Category / Coordinates` 等），保留地址类信息。子景点块（如「Sub-site: The Little Prince House」）因此只留 Address，不再出现「Chinese Name: …」。
- 配套：列表首行简介改用「游玩亮点」优先（`highlights → course → overview`），因为概览清理后只剩地址电话，当简介不好看。

### 问题 7：追问 chip 区在竖屏下被输入栏压住、显示不全
- 现象：英文回答后，底部追问 chip 出现 4~5 行，最后一行被裁在输入栏上沿，看起来像界面坏了。
- 根因：`#followups` 固定 `max-height:104px`，1080×1920 竖屏下只够 3 行多，第 4 行被裁在边界上且与页脚没有视觉分隔。
- 修复：改为 `max-height:27vh` + 白底 + 上边框，独立成一块可滚动区域；复测 4 行 chip 全部完整可见。

## 改动文件
| 文件 | 改动 |
|------|------|
| `Busan/apk_build/build_apk.py` | `d8` 由「显式 2 个 class」改为 `os.walk` 递归收集全部 `*.class`；签名后新增 `dexdump -f` 逐类校验（缺类直接 `SystemExit`），把「装得上但点开闪退」这类问题在构建期拦住。 |
| `Busan/android/java/com/busan/tour/MainActivity.java` | 新增运行时定位授权：`LocationBridge`（`@JavascriptInterface requestLocation()`）、`hasLocationPermission()`、`notifyLocReady()`（`evaluateJavascript` 回调 `window.__busanLocReady`）、`onRequestPermissionsResult`、`REQ_LOCATION=1001`、`addJavascriptInterface(..., "BusanHost")`。 |
| `Busan/android/assets/index.html` | ① 定位链路重写：`locateOnce()` / `renderNearby()` / `locBusy` / `locWaiting` 防重复、`maximumAge=60000`、`timeout=10000`；② 「附近」优先走系统授权桥，2 秒兜底；③ 15km 无结果时降级 `E.nearestAny()` + `nearbyFar` 文案；④ 追问 chip 区改 `max-height:27vh` + 白底上边框。 |
| `Busan/android/assets/app.js` | ① 新增 `nearestAny(lat,lng,limit)`；② 新增三语 `nearbyDenied` / `nearbyTimeout` / `nearbyFar`；③ 列表首行简介改为 `highlights → course → overview`，并剥掉行首 `·/•/-`；④ 早前几轮已落的 `highlights` 意图、补充推荐括号按语言区分、`md()` 压空行一并保留。 |
| `Busan/apk_build/export_assets.py` | ① `clean_overview()` 只留地址 / 电话 / 官网 / 机场距离；② `strip_meta_lines()` 清理所有字段所有语言的名字 / 别名 / 类别 / 坐标标签行；③ `add_short_aliases()` 推导唯一短名；④ 三语正式名并入 `aliases`；⑤ 上一轮的 audience 中文标题清理保留。 |
| `Busan/android/assets/data.json` / `data.js` | 重新导出：各 **65.6 KB**（上一版 66.5 KB，元信息行被清掉），8 个景点 × 三语字段，别名已补齐短名与三语正式名。 |
| `Busan/dist/Busan旅行助手.apk` | 重新打包：**125.0 KB**，签名与 `dexdump` 校验通过，已装进模拟器复测。 |
| `Busan/logs/changelog_2026-11-05_emulator_test.md` | 本日志 |

## 规则落地说明（本轮没有改动已锁定的规则）
- **语言**：回复语言仍只由顶部三语按钮决定，与提问语言、数据来源无关。本轮实测：英文按钮下提问 `Gamcheon admission`、`Gamcheon show me around`，正文、小节标题、补充推荐、追问 chip 全为英文；中文按钮下同一问题整段中文。
- **玩法作用域**：选定玩法后该文件夹仍是唯一主数据源。本轮实测 `Gamcheon admission` 在「自动」模式下由景点名把玩法自动切到 01，回答只出甘川自己的字段；补充推荐 2 条来自 02 / 03，标注玩法与理由、排在主回答之后。
- **附近**：仍按直线距离升序、15km 过滤；只在「过滤后为空」时才降级给最近 3 个，并明确写出「15 公里内没有收录景点」这一前提，不伪装成 15km 内的结果。
- **离线**：`AndroidManifest.xml` 仍未申请 `INTERNET`，所有问答只读包内 `assets/`。

## 使用方式
```powershell
# 一、（可选）改完景点 txt 后重新导出数据与译文
cd D:\AI_Project_2026_2\Busan
python apk_build\export_assets.py

# 二、离线引擎回归
node apk_build\test_engine.js

# 三、打包（含 dexdump 逐类校验）
python apk_build\build_apk.py

# 四、装到模拟器 / 真机
D:\leidian\LDPlayer14\ldconsole.exe launch --index 0
D:\leidian\LDPlayer14\adb.exe connect 127.0.0.1:5555
D:\leidian\LDPlayer14\adb.exe -s 127.0.0.1:5555 install -r "dist\Busan旅行助手.apk"
D:\leidian\LDPlayer14\adb.exe -s 127.0.0.1:5555 shell am start -W -n com.busan.tour/.MainActivity
```

## 验证清单（本轮已执行）
| 项目 | 方法 | 结果 |
|------|------|------|
| 闪退修复 | 装进模拟器 → `am start` → 抓 `logcat` | 首屏正常出现；不再出现 `ClassNotFoundException`；返回键回桌面无 `AndroidRuntime` 异常 |
| dex 完整性 | `build_apk.py` 内 `dexdump -f` 逐类比对 | 8 个 class 全部存在（含 `MainActivity$1/$2/LocationBridge/$LocationBridge$1`） |
| 运行时定位授权 | 点「附近」 | 系统弹窗「仅在使用该应用时允许 / 仅限这一次 / 不允许」；允许后成功取到坐标 |
| 重复渲染 | 修复后连点「附近」 | 只输出一条「附近景点（按直线距离）」列表 |
| 距离排序 | `ldconsole locate --LLI 129.0510,35.0510` 后点「附近」 | 甘川 8.5 / 洛东江 9.8 / 乙淑岛 9.9 / 峨嵋山 14.0 / 多大浦 14.6 公里，升序正确 |
| 空白近处降级 | 未设置虚拟定位（定位在北京） | 输出「15 公里内没有收录景点，按直线距离最近的 N 个是：」+ 3 个最近景点，不再是单句「没有」 |
| 韩文 i18n | 切 한국어 问 `Molundae sunset` | 「추천 대상」为纯韩文，无中文类别标题残留 |
| 英文短名 | 切 English 问 `Gamcheon admission` | 命中甘川文化村、自动切 01、输出 Tickets & Fees、补充 2 条、追问 chip 英文 |
| 三语文案 | 中文 / 한국어 / English 各切一次 | 标题、玩法 / 出行 chip、状态栏、按钮、提示语全部随语言切换并重生成 |
| 元信息清理 | 读回 `data.json` 全字段扫描 | `Chinese Name` / `중문명` / `Category` / `Coordinates` 命中数 0 |
| 追问 chip | 点「甘川文化村 怎么去?」/ `Is there an entrance fee…?` | 正常追加提问并出对应小节 |
| 追问区排版 | 英文 4 行 chip 竖屏截图 | 4 行全部完整可见，不再被输入栏裁切 |
| 返回键 | `adb shell input keyevent 4` | 回到桌面（`topResumedActivity=com.android.launcher3/.Launcher`），无崩溃 |
| 离线引擎回归 | `node apk_build\test_engine.js` | 12 组断言全绿（含新增短名 `Gamcheon` 用例） |
| 包内资源 | `zipfile` 读回 APK 内 `assets/index.html`、`assets/data.js` | 含新 CSS（`27vh`）+ 短名 `Gamcheon` + 无 `Chinese Name` |

## 已知限制（如实记录）
1. **只在雷电模拟器（Android 14 / x86_64）上验证过，未在真实手机上装过**。模拟器能证明 WebView 壳、运行时授权、dex、布局都正常，但真实机型的 WebView 版本、系统字体、厂商省电策略仍可能带来差异，首次在真机安装后建议再点一遍「附近」。
2. **模拟器的定位是虚拟坐标，不是真实 GPS**。本轮用 `ldconsole locate --LLI 129.0510,35.0510` 造的坐标验证距离排序；`dumpsys location` 里的 `last location` 是缓存（长期停在 `39.915001,116.403999` 北京），**不能**用它判断定位是否生效，只能反推 App 里算出的距离。
3. **没云台坐标仍未精校**（`35.0510,128.8820`，档案原文就标注「入库前请用 Naver 精校」）。「附近」的距离数值会随该坐标偏差而偏，本轮没有联网复核。
4. **仍是 8 个景点、13 条意图规则**。超出规则的问法会落到概览或全字段输出，不会像桌面版 LLM 那样自由改写。
5. **短名去重是按「前缀是否指向别的景点」判断的**，因此像 `Dadaepo`（同时是海水浴场与梦之夕阳喷泉的前缀）这种真有歧义的短名**故意不加**，输入它仍会落到列表兜底 —— 这是有意保守，不是漏配。
6. **签名私钥不进仓库**（`apk_build/keystore/` 已 gitignore）。仓库里的 APK 可直接安装；换证书重建后无法覆盖升级，需先卸载旧版。
7. **不支持 iOS**，仍只做安卓 APK。
