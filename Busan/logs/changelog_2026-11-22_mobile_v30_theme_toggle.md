# 釜山 AI 旅行助手 · v3.0 手机版更新日志

- 日期：2026-11-22
- 版本：Android `versionCode 23 / versionName 3.0`，iOS `3.0 / 23`，PWA 缓存 `busan-3.0`
- 上一版：v2.9（个性化推荐收起/展开 + 单行横滑）
- 本轮目标：昼夜配色加手动切换按钮；分析还能加哪些功能；全量测试；推 GitHub 并出安装包与日志

---

## 一、昼夜切换按钮（本轮唯一的功能改动）

### 1. 长什么样

页头右上角、天气按钮左边，多了一枚 34×34 的圆形按钮：

| 当前模式 | 图标 | 按钮底色 | 点一下变成 |
| --- | --- | --- | --- |
| 自动（默认） | 🌓 | 半透明玻璃（跟随页头） | 白天 |
| 白天（手动） | ☀️ | 浅黄 `#fde9b8` | 夜间 |
| 夜间（手动） | 🌙 | 深蓝 `#12232d` | 自动 |

按「自动 → 白天 → 夜间 → 自动」循环，图标和底色直接告诉你现在是什么模式，不用记。

### 2. 为什么是三态而不是两态

原来（v2.7 起）只有自动：19:00–05:59 判夜，没有任何手动入口，白天想试夜间配色只能开控制台。这次如果只做"白天/夜间"两态，就会把自动能力弄丢——所以做成三态：**自动仍是默认，手动是临时覆盖，再点一下回到自动**。

### 3. 行为与状态

- 手动选择写进 `localStorage.busan_theme`（`auto` / `day` / `night`），下次打开照旧。
- 实测：17:00（白天钟点）手动切夜间 → 刷新页面 → 仍是夜间（`mode=night, night=true, theme=#072e3c`）。
- 自动模式下仍严格按手机钟点：`h >= 19 || h < 6`；每 60 秒复判一次，回到前台也复判（手动模式下复判不会覆盖你的选择，实测 `visibilitychange` 后仍是 `night`）。
- 切语言后按钮文案跟着变：韩语 `주야: 자동 · 눌러 전환`。
- `aria-pressed` 在夜间为 `true`，`aria-label` / `title` 都写明当前状态（读屏可读）。
- 点一下给 1.8 秒一次性提示，2.4 秒后实测已隐藏：
  - `🌓 自动：仍按手机时间切昼夜`
  - `☀️ 已切到白天配色（手动）`
  - `🌙 已切到夜间配色（手动）`
- 结论卡里那句规则同步补了一句「右上角按钮可手动切（自动 / 白天 / 夜间）」，不再和手动模式打架。

### 4. 布局没被挤坏

- 390 宽：按钮 `x=270`、天气按钮 `x=312`，`noOverlap=true`，页头高 86px（和 v2.9 一样）。
- 360 宽：`scrollWidth=360 = innerWidth`，无横向溢出，标题仍有 226px，按钮不重叠。

---

## 二、测试

| 脚本 | 结果 |
| --- | --- |
| `apk_build/test_v30.js`（本轮新增） | **59 / 0** |
| `apk_build/test_v29.js` | **71 / 0** |
| `apk_build/test_v28.js` | **103 / 0** |
| `apk_build/test_v27.js` | **50 / 0** |
| `apk_build/test_v26.js` | **74 / 0** |
| `apk_build/test_v25.js` | **63 / 0** |
| `apk_build/test_v23.js` | **50 / 0** |
| `apk_build/test_v22.js` | **43 / 0** |
| `apk_build/test_engine.js` | `✅ 离线引擎全部断言通过` |

`test_v30.js`（59 条）覆盖：按钮结构（位置在天气按钮左侧、图标位、`data-mode`）、34px 触控下限与圆形样式、白天/夜间两套底色、提示条（位置、1.8s 淡出、`pointer-events:none`）、三态顺序与取模循环、持久化键、非法值回落 auto、`paintThemeBtn` 同步 `data-mode/aria-pressed/aria-label`、启动读回、`applyUI` 后重画、`BusanUI.cycleTheme`、自动判定 19/6 与 `theme-color` 双色、三语提示文案、结论卡规则句、以及 v2.9/v2.8/v2.7/v2.6 能力不回退与 3.0/23 版本同步。

### 真浏览器探针（`_v30probe.py`，390×844，CDP 9234）

```
BOOT            mode=auto  dataMode=auto  icon=🌓  night=false  theme=#0a4e63  hour=17
TAP1(day)       mode=day   icon=☀️  night=false  bg=rgb(255,233,184)
                toast="☀️ 已切到白天配色（手动）"
TAP2(night)     mode=night icon=🌙  night=true   bg=rgb(18,35,45)  theme=#072e3c
                pressed=true  toast="🌙 已切到夜间配色（手动）"
TOAST 2.4s      hidden=true
RELOAD(night)   mode=night night=true theme=#072e3c   ← 白天钟点也保持手动夜间
TAP3(auto)      mode=auto  icon=🌓  night=false theme=#0a4e63
                toast="🌓 自动：仍按手机时间切昼夜"
KO              title=주야: 자동 · 눌러 전환
LAYOUT          theme x=270 y=10 34×34 | fab x=312 | noOverlap=true | headerH=86
NARROW 360      innerW=360 scrollW=360 noOverlap=true titleW=226
WX PERM         grant=true tag=综合推荐 · 需要定位权限
QREC            open=true chips=5 scrollable=true
AFTER VISIBILITY mode=night night=true theme=#072e3c icon=🌙
ERRORS          []
```

证据截图（`Busan/apk_build/`）：`v30_theme_auto.png`、`v30_theme_day.png`、`v30_theme_night.png`、`v30_theme_ko.png`、`v30_theme_360.png`，线上另出 `v30_online_*.png`。

---

## 三、构建产物

| 产物 | 大小 | SHA-256 |
| --- | --- | --- |
| `Busan/dist/Busan旅行助手.apk` | 10,602,539 B（10.35 MB） | `5186C1933A011AB8F3DD701589513B34426021CCE2C7FED96BDA5A98F04F9DF8` |
| `Busan/dist/Busan_iOS_WebApp_v30.zip` | 10,490,749 B | `1CE92509A393573035B50F682102697465C5797ACFB2EBD051F6EB0BA0EE6E77` |

APK 校验：`versionCode='23' / versionName='3.0'`、`com.busan.tour`、label `釜山旅行助手`；签名 v1+v2 通过，证书不变（`CN=Busan Travel Assistant`，SHA-256 `9d91ed6b…356`）；包内 `index.html / mix.js / sw.js` 与源码逐字节一致（`same=True`）。
iOS 包 21 条目、`required missing: none`。

> iPhone 仍只有 PWA（无签名 `.ipa`）：Windows 无 Xcode，仓库 macOS runner 第 7 次 cancelled。

---

## 四、改动文件

| 文件 | 改动 |
| --- | --- |
| `Busan/android/assets/index.html` | 页头新增 `#themeBtn`/`#themeIcon`；`.theme-btn` 三态样式；`#themeToast` + `.ui-toast`；`themeMeta/paintThemeBtn/themeToast/setThemeMode(mode,fromUser)/cycleTheme`；`initDayNight` 读回 `busan_theme` 并绑定按钮、复判时同步重画；`applyUI` 里重画；`BusanUI.cycleTheme`；结论卡规则句补手动切换 |
| `Busan/android/assets/sw.js` | 缓存名 `busan-3.0` |
| `Busan/android/AndroidManifest.xml` | `versionCode 23 / 3.0` + v3.0 说明块 |
| `Busan/android/java/com/busan/tour/MainActivity.java` | 类注释 v3.0、UA `BusanTour/3.0 (Android)` |
| `Busan/ios/project.yml` / `ios/README.md` | `3.0 / 23` |
| `Busan/pwa/build_pwa.py` | 产物 v30 |
| `Busan/apk_build/test_v30.js` | **新增** 59 条 |
| `Busan/apk_build/test_v29/v28/v27/v26.js` | 版本断言同步 3.0/23、昼夜复判写法同步 |
| `Busan/apk_build/_v30probe.py` / `_v30live.py` | **新增** 本地与线上探针 |
| `Busan/dist/*` | v3.0 APK 与 iOS 网页包 |

---

## 五、复跑命令

```powershell
cd D:\AI_Project_2026_2\Busan
node apk_build/test_v30.js
node apk_build/test_v29.js
node apk_build/test_v28.js
node apk_build/test_v27.js
node apk_build/test_v26.js
node apk_build/test_v25.js
node apk_build/test_v23.js
node apk_build/test_v22.js
node apk_build/test_engine.js
& D:\AI_Project_2026_2\.venv\Scripts\python.exe apk_build/_v30probe.py
& D:\AI_Project_2026_2\.venv\Scripts\python.exe apk_build/_v30live.py
& D:\AI_Project_2026_2\.venv\Scripts\python.exe apk_build/build_apk.py
& D:\AI_Project_2026_2\.venv\Scripts\python.exe pwa/build_pwa.py
```

---

## 六、提交与线上

| 提交 | 内容 |
| --- | --- |
| `f40fcb9` | feat(mobile): v3.0 页头新增昼夜切换按钮（自动/白天/夜间循环 + 本机记忆），双端同步 3.0 |
| （本条 docs 提交） | v3.0 日志、功能分析与线上实测 |

推送：`e7177ae..f40fcb9`（`main`）→ `https://github.com/luohaisheng814/AI_Project_2026_2`

---

## 七、还能加什么：现有底子与优先级

先把"手上已经有什么"说清楚，后面的建议才是可落地的：

- 18 个景点（含 `plan{最佳时段/步行强度/室内外/拍照/家庭}`、`vibes`、星级、图片、官网链接）
- 离线检索引擎 + 三语预翻译（断网可用）
- 定位、天气（Open-Meteo，免 Key）、按「时间×天气×距离×星级」排序
- 账户/会话、行程规划器、问答链路、PWA 离线缓存、APK 原生壳

### P1 · 不用接新服务，1–3 天能做完

1. **营业时间与休息日字段** —— 现在只按 `best_time` 推，半夜也会推札嘎其。加 `open/close/closed_on`，"现在能去吗"就能回答，`mix.js` 只需改 `timeScore`。**这是投入产出比最高的一项**。
2. **收藏 + 我的行程（本地保存/导出）** —— 存 `localStorage`/IndexedDB，列表可导出成一张分享图或一段文本；现在行程规划完关掉就没了。
3. **逐小时天气 + 降水时间轴** —— 同一个 Open-Meteo 接口加 `hourly`，把"16:00 之后会不会下雨"画成一条 6 小时小条。
4. **韩语场景短语卡** —— 点餐/问路/打车/退税/医院，三语对照 + 一键朗读，离线可用；对留学生和短期游客都直接有用。
5. **语音输入与朗读** —— Web Speech API + TTS；边走边问、骑车免看屏。
6. **无障碍与单手** —— 字号三档（现在固定 14px）、对比度检查、把"附近/天气/昼夜"三个高频入口保持在拇指区。

### P2 · 需要一个轻后端或第三方 API

7. **步行/公交真实可达性** —— 现在是直线距离，km 被误读成车程。接 NAVER/Kakao Directions 或釜山公交 API，给"步行 12 分钟 / 地铁 2 站"。
8. **实时到站与班次** —— 公交到站倒计时、末班车时间（夜里尤其关键）。
9. **人流/排队提示** —— 热门点（海云台、甘川）节假日拥挤度，配合"换个近的"建议。
10. **评价与投稿** —— 现有星级是内置的；做用户评分/照片要先有存储、审核与滥用防护。
11. **账户云同步** —— 收藏、行程、语言稿跨设备同步（现在账户只保留少量状态）。
12. **门票/预约深链 + 支付提示** —— Skyline Luge、Sea Life、展览预约，以及 T-money / 支付宝 / 微信可用性标注。
13. **汇率换算** —— 韩元→人民币/美元实时换算，配合"这顿大概多少钱"。

### P3 · 工程与体验

14. **一分钟规划向导** —— 三个问题（几点出门/走多远/想看什么）替代现在手点玩法+出行条，转化更直接。
15. **桌面小组件 / 本地通知** —— 天气突变、出发前 30 分钟提醒（APK 侧要加 AlarmManager 与通知权限）。
16. **首屏性能与包体** —— 10.35 MB 主要是图片；可转 WebP/按需加载，`mix.js` 等非首屏脚本延后。
17. **质量体系** —— jsdom 级 DOM 单测替代部分正则断言、截图 diff 视觉回归、崩溃日志上报。
18. **iOS 真包** —— 要么找一台 Mac，要么接受长期只有 PWA；这是目前唯一"功能齐但缺交付形态"的缺口。
19. **第四语言（日语）** —— 釜山日本客占比高，数据已有三语结构，加一栏成本可控。

**如果只做三件**：① 营业时间字段（让推荐"真的能去"）② 收藏与行程保存（让一次规划有沉淀）③ 步行路线/到站（把直线距离换成真实可达性）。前两件不依赖任何新服务，第三件需要地图 API。
