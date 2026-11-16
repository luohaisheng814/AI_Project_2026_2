# Busan 手机版 v1.8.1 开发日志：用云端意图解析修掉“库里没有这个地点”

- **日期**：2026-11-16
- **版本**：versionCode 10 / versionName 1.8.1
- **范围**：Android 手机版问答链路、路线回答、意图解析与构建产物
- **触发问题**：用户上传的两张真机截图里，
  1. “白天上午去哪里比较好啊” → “库里没有这个地点。沙下区目前收录：……”；
  2. “从我当前位置去看川文化村都有哪几条路可以选” → 同样报“库里没有这个地点”。

## 1. 根因

两个问题都不是“数据库没有景点”，而是问答入口只做了**字面匹配**：

- `findSpot()` 只做名称包含判断，`看川文化村` 的“看川”不是“甘川”，直接匹配失败；
- `answer()` 在匹配不到景点时直接返回 `notFound`，没有“上午推荐”这一类意图；
- 即使认出甘川文化村，`compose()` 的交通字段是“从金海机场/土城站”的静态说明，不会用 `BusanLive.position()` 的实时坐标；
- 页面没有“从当前位置出发”的路线模式，也没有把 NAVER 路线深链暴露出来。

因此本轮把“先理解真实意图，再决定查景点/做推荐/算路线”放到云端模型，同时保留本地兜底，避免断网时再次报错。

## 2. 改动

### 2.1 云端意图解析（新增）

`Busan/android/assets/index.html` 新增 `aiIntent()` / `parseIntent()` / `answerWithIntent()`：

- 联网且云端可用时，先把用户原话发给模型，要求只输出一行 JSON：
  `intent=recommend|route|spot|unknown`、`spot=正式景点名`、`time=morning|afternoon|evening|any`、`from_current`。
- system prompt 里带全部收录景点名，明确允许纠正错字/口语；并说明“实时定位只是状态，提问里没有目的地时不要判 route”。
- 模型返回后用 `C.findSpot(intent.spot)` 再校验，避免模型编造不存在的景点。
- 15 秒未返回或模型失败时自动走本地规则，不把用户卡在加载气泡里。
- 具体景点问答仍复用原来的 `C.answer()`，只在 `spotId` 存在时追加官网核对与“云端模型”短建议。

实测 Kilo `nvidia/nemotron-3.5-super-vl:free` 对两条原话分别返回：

```json
{"intent":"recommend","spot":"","time":"morning","from_current":false}
{"intent":"route","spot":"甘川文化村","time":"any","from_current":true}
```

HTTP **200**，`model=nvidia/nemotron-3.5-super-vl:free`，没有 Key。

### 2.2 上午推荐（本地也能用）

`Busan/android/assets/cloud.js` 新增：

- `timeOf(q)`：识别上午/下午/傍晚/白天；
- `isRecommendQuestion(q)`：识别“去哪/哪里/推荐/玩什么/白天/上午”等没有明确景点的问法；
- `recommend(time, q)`：按最佳时段、步行强度和看头排 3 个点：
  - 上午：甘川文化村（首选）、洛东江河口生态中心（更省力，步行 2/5）、乙淑岛候鸟公园（换口味）；
  - 下午：长林浦口、甘川文化村、乙淑岛候鸟公园；
  - 傍晚：多大浦梦之夕阳喷泉、多大浦海水浴场、峨嵋山观景台。
- 每个推荐都带 `choices` 3 张卡，点进去才查具体交通/门票/官网，不把推荐当成“已选景点”。

`answer()` 在找不到景点但识别出推荐意图时，直接返回 `recommend()`，不再返回 `notFound`。

### 2.3 从当前位置到景点（3 条走法）

`cloud.js` 新增 `routeTo(s, pos)`：

- 读取 `BusanLive.position()` 的实时经纬度与精度；
- 用 haversine 算直线距离，文案明确写“直线距离，实际道路更长”；
- 生成 3 类可执行走法：
  1. 公共交通（推荐）：NAVER 路线深链，按实时地铁/巴士换乘；
  2. 打车直达：按直线距离估算时间，注明“以计价器和实时路况为准”；
  3. 步行/无障碍：按 4.2 km/h 估算；超过 3 km 明确提示“不建议全程走，走到最近站点再换乘”；
- 每条都带 `nmap://route/public|car|walk` 深链，`slat/slng` 用当前坐标，`dlat/dlng` 用目标坐标；
- 不编造班次、末班时间、具体线路号，正文写明“具体线路/班次/末班以 NAVER 实时结果为准”。

`index.html` 的 `paintBubble()` 新增 `result.links` 渲染：每个走法一个可点击的路线卡，样式 `.routes/.routeopt`；Android `handleUrl()` 会把 `nmap://` 交给地图 App，没有 App 时提示“请用网页地图”。

`findSpot()` 同时加了口语兜底：`看川 → 甘川`、`甘川文化 → 甘川文化村`、`乙淑岛 → 乙淑岛候鸟公园`、`长林浦 → 长林浦口`，并把“景点名包含问题”反向匹配补回来；即使云端失败也能认出“看川文化村”。

### 2.4 配置与版本

- `AndroidManifest.xml`：versionCode **10** / versionName **1.8.1**；仍无原生库、无 `extractNativeLibs`。
- `MainActivity.java`：注释改为 v1.8.1；`User-Agent` 改为 `BusanTour/1.8.1 (Android)`。
- `session.js`：修正 `loadLlmConfig()` 的 `builtin` 判断。此前原生返回的是“已归一化的默认 endpoint/model”，网页按“字段非空”算，导致内置模型被误显示为 custom；现在优先采用原生返回的 `rawCfg.builtin`，账户卡片才会正确显示“Kilo Gateway · Free / Nemotron”。

### 2.5 本轮涉及文件

| 文件 | 说明 |
| --- | --- |
| `Busan/android/assets/index.html` | 意图解析、加载气泡、`answerWithIntent`、路线卡渲染、样式 |
| `Busan/android/assets/cloud.js` | 错字归一、上午/下午/傍晚推荐、当前位置路线、3 条深链 |
| `Busan/android/assets/session.js` | `builtin` 配置修复 |
| `Busan/android/AndroidManifest.xml` | v1.8.1 / code 10 |
| `Busan/android/java/com/busan/tour/MainActivity.java` | 版本注释与 UA |
| `Busan/dist/Busan旅行助手.apk` | 重打包 |
| `Busan/dist/Busan_Tour_App.zip` | 重打包 |

## 3. 构建结果

| 产物 | 结果 |
| --- | --- |
| APK | `Busan/dist/Busan旅行助手.apk` |
| APK 体积 | **234,908 B（229.4 KB）** |
| APK SHA-256 | `EAF45D7B57D75755DCD78D584E3D51C90A1ECB5FE805BA6C724A49AF6DB1C279` |
| 版本 | versionCode **10** / versionName **1.8.1** |
| 包名 | `com.busan.tour` |
| 原生库 | `lib_entries = []` |
| 签名证书 SHA-256 | `9d91ed6b8ffeec5eaf5b597ee19f56bfda6f8663d94ec726390a552224d33356` |
| zip | `Busan/dist/Busan_Tour_App.zip` |
| zip 体积 | **2,609,783 B** |
| zip SHA-256 | `D119E9426F46A8955F11295CA57BE1A860D767F951F605097D53ECD573262F8F` |

构建链：`aapt2 compile/link` → `javac` → `d8` → `zipalign` → `apksigner`，全部通过。

## 4. 验证清单

- [x] `node --check`：`cloud.js`、`session.js`、`planner.js`、`app.js`、`live.js` 全部通过。
- [x] 实际 Kilo API：两条原话都返回 200；意图分别是 `recommend`（morning）与 `route`（甘川文化村，from_current=true）。
- [x] 本地兜底：模拟实时定位后问“白天上午去哪里比较好啊”，气泡返回“上午·3 个更合适的选择”，3 张卡为甘川文化村/洛东江河口生态中心/乙淑岛候鸟公园。
- [x] 本地兜底：问“从我当前位置去看川文化村都有哪几条路可以选”，错字被纠成甘川文化村，返回直线距离、公交/打车/步行 3 条走法和 3 个 NAVER 深链，不再出现 `notFound`。
- [x] 回归：`甘川文化村 轮椅 怎么去` 仍返回 3 个方案（甘川/多大浦喷泉/乙淑岛），来源仍为 `saha.go.kr`。
- [x] 回归：按当前选择规划仍返回 3 个可选点。
- [x] 回归：账户面板仍显示云端卡片、测试连接、恢复默认与折叠自定义接口。
- [x] `aapt dump badging`：versionCode 10 / versionName 1.8.1；APK 内无 `lib/`。
- [x] `apksigner verify`：证书 SHA-256 未变。
- [x] 最终 APK/zip SHA-256 已计算并记录。

截图：

- `Busan/apk_build/v18b_morning.png`（上午推荐 3 个点）
- `Busan/apk_build/v18b_route.png`（当前位置到甘川文化村 3 条走法）
- 旧回归图：`v18_probe_home.png`、`v18_probe_choices.png`、`v18_probe_plan.png`、`v18_probe_account.png`

## 5. 已知限制

1. **未真机验证**：`adb devices` 仍为空。两条新链路只在无头 Chrome + 模拟坐标 + 真实 Kilo 意图接口上验证；Android WebView 内 `nmap://` 拉起 NAVER、GPS 真实精度、断网回退仍需真机确认。
2. **路线是“模式级”而非逐段导航**：只给公交/打车/步行 3 类走法，具体地铁线路、巴士编号、班次与末班时间交给 NAVER 实时结果；正文明确写了这个边界。
3. **打车时间/步行时间是估算**：按直线距离和固定速度算，不是路况 ETA；实际以计价器/地图为准。
4. **依赖 NAVER 地图 App**：`nmap://` 深链在未安装 NAVER 地图时会提示“请用网页地图”，本轮没有内置网页版路线页。
5. **LLM 意图解析可能误判**：已用 `C.findSpot()` 二次校验与 15 秒本地兜底降低风险，但没有做大规模问法评测；模型把“当前位置”状态误读成路线意图的风险已通过 prompt 约束，但仍需真机观察。
6. **Kilo 匿名额度**：仍是 200 请求/小时/IP，高频使用可能 429；模型回答失败会静默回退本地规则。
7. **论文未同步**：HCI2026 中英论文的蓝色评审意见仍未处理；本轮只改 App。

## 6. 验证建议

1. 真机安装 v1.8.1，重复截图里的两条问题，确认不再出现“库里没有这个地点”。
2. 在甘川文化村页面点路线卡，确认能拉起 NAVER 地图并带当前坐标。
3. 关闭网络重问“白天上午去哪里”，确认仍返回 3 个本地推荐；重问“看川文化村路线”，确认错字仍能被本地兜底识别。
4. 若需要逐段公交，下一步接 NAVER/ODsay 等实时路径 API，而不是继续用直线估算。
