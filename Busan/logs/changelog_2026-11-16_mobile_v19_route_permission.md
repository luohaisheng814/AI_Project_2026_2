# Busan 手机版 v1.9 开发日志：路线问题先申请地图定位权限，再汇总走法

- **日期**：2026-11-16
- **版本**：versionCode 11 / versionName 1.9
- **范围**：Android 手机版路线问答、定位权限、云端意图与数据库查询、构建产物
- **需求**：用户询问路线时，先确认 App 是否已允许地图定位权限；没有就申请，有就读取当前位置，再把地图给出的走法总结给用户；同时根据问题实时查数据库、猜测真实想法。

## 1. 这轮解决的问题

前两版路线回答直接调用 `BusanLive.position()`，但没有先确认权限状态：

- 未授权时只是“没有当前位置”，用户不知道要开权限；
- 已授权但还没首个坐标时，没有等待机制，容易直接回退成静态交通；
- 权限弹窗和问答气泡没有连接，拒绝后也没有“去系统设置”的入口；
- 路线结果只有三类走法，没有把“为什么这样选”用模型总结出来。

v1.9 把路线问答改成三步：**确认权限 → 申请/等待定位 → 汇总路线**。

## 2. 改动

### 2.1 定位权限状态与等待

`Busan/android/assets/live.js`：

- 新增 `st.permission` 与 `BusanLive.permission()`，返回 `granted / denied / prompt / unknown`；
- 原生优先调用 `BusanHost.hasLocationPermission()`；浏览器用 `navigator.permissions.query({name:'geolocation'})`；
- 新增 `BusanLive.ensure(cb, timeoutMs)`：有坐标立即返回；没有就调用 `start()`，每 400ms 轮询坐标，授权拒绝立即结束，默认 18 秒超时；
- 收到坐标时把权限置为 `granted`；`__busanLocError(1)` 置为 `denied`；浏览器 `watchPosition` 错误码 1 同样置为 `denied`；
- 原有顶部“实时/停止”按钮、`__busanLocUpdate`、`__busanLocError` 保持兼容。

`Busan/android/java/com/busan/tour/MainActivity.java`：

- `HostBridge` 新增并暴露：
  - `hasLocationPermission()`：查询 `ACCESS_FINE_LOCATION` / `ACCESS_COARSE_LOCATION`；
  - `startLocationWatch()` / `stopLocationWatch()`：原来只在外层类里，WebView 实际调不到，这次补上桥接方法；
  - `openAppSettings()`：跳到本应用的系统设置页，供拒绝后恢复权限；
- `startLocationWatch()` 未授权时仍走 `requestPermissions(..., 1002)`，授权成功自动 `startLocationInternal()`，拒绝回调 `window.__busanLocError(1,'permission_denied')`；
- 保留 `requestLocation()`（1001）给旧“附近”按钮使用。

### 2.2 路线问答先出权限卡

`Busan/android/assets/index.html`：

- 新增 `wantsRoute(text)`：只有“有明确目的地 + 怎么去/路线/几条路/交通/地铁/公交/打车/从我/当前位置”才进路线流程；普通“门票/开放时间/亮点”仍是景点事实问答。
- 新增 `routePermissionCard()`：未授权时不再硬算路线，先在对话里显示：
  - 标题“路线 · 需要地图定位权限”；
  - 说明“去某景点需要当前位置”；
  - “允许定位并继续”与“去系统设置”两个按钮。
- 新增 `grantRoute()`：点击后新建加载气泡，调用 `BusanLive.ensure(..., 18000)`；授权成功用实时坐标出路线；拒绝/超时则给原因 + 常规交通。
- 新增 `routeAnswer()`：
  - 已有坐标：直接 `C.routeTo`；
  - `permission=granted` 但没有首个坐标：自动等 GPS，不要求用户再点；
  - `permission=denied`：给出“定位被拒绝”的原因、系统设置按钮与常规交通；
  - `permission=prompt/unknown`：显示权限卡，由用户点击申请。
- `ask()` 的 `settle()` 先判断路线意图：LLM 返回 `route` 或本地 `wantsRoute` 命中，就走 `routeAnswer()`；如果模型判断为路线但没抽到具体景点，且已有实时坐标，则用 `C.nearby()` 在数据库里找最近收录点，避免又回到“未找到”。
- `paintBubble()` 支持 `permissionPrompt / permissionDenied` 两种状态与按钮绑定；按钮在重绘后仍可用。
- 路线结果保留 `nmap://route/public|car|walk` 三条深链，点开由 Android `handleUrl()` 交给 NAVER 地图。

### 2.3 路线总结

`Busan/android/assets/cloud.js`：

- `routeTo()` 返回值新增 `routeMeta`：
  - `spotId / name / km / accuracy / taxiMin / walkMin / at`；
  - 让模型只在“已知直线距离、精度、三种走法”范围内总结，不凭空编线路。
- 原有三类走法：
  - 公共交通（推荐）：NAVER 实时换乘；
  - 打车直达：直线距离估算时间；
  - 步行/无障碍：4.2 km/h 估算；超过 3 km 明确不建议全程走。

`index.html` 的 `finishAnswer()`：

- 当 `res.kind === "route"` 且有 `routeMeta` 时，单独调用云端模型生成 2–3 句路线摘要；
- system prompt 明确禁止编造公交/地铁线路号、票价、班次、末班时间、到达时间；
- 必须说明“直线距离不是道路距离”“具体换乘以 NAVER 实时结果为准”；
- 摘要显示在气泡底部“云端模型：”短注里。

### 2.4 云端意图与数据库

保留 v1.8.1 的 `aiIntent()`：

- 先让模型只输出一行 JSON：`intent=recommend|route|spot|unknown`、`spot`、`time`、`from_current`；
- 模型可纠正“看川文化村→甘川文化村”这类错字；
- 返回后用 `C.findSpot()` 二次校验，避免模型编造景点；
- 模型失败或 15 秒超时，仍走本地 `findSpot + recommend + routeTo`。

本轮把 `from_current` 和 `wantsRoute` 接到权限流程；本地数据库查询仍以包内 `busan_travel.db` 快照为准，当前坐标只用于算距离和最近点，不伪造实时营业/拥挤数据。

### 2.5 版本

- `AndroidManifest.xml`：versionCode **11** / versionName **1.9**；
- `MainActivity.java`：注释、`User-Agent` 改为 `BusanTour/1.9 (Android)`；
- 仍无原生库、无端侧模型。

## 3. 构建结果

| 产物 | 结果 |
| --- | --- |
| APK | `Busan/dist/Busan旅行助手.apk` |
| APK 体积 | **239,004 B（233.4 KB）** |
| APK SHA-256 | `A632214E409EEF2900EE151C5BFDD4A494C1A78349DCB21A533F01A8E108DFB1` |
| 版本 | versionCode **11** / versionName **1.9** |
| 包名 | `com.busan.tour` |
| 原生库 | `lib = []` |
| 签名证书 SHA-256 | `9d91ed6b8ffeec5eaf5b597ee19f56bfda6f8663d94ec726390a552224d33356` |
| zip | `Busan/dist/Busan_Tour_App.zip` |
| zip 体积 | **2,616,640 B** |
| zip SHA-256 | `21E3914D06D0EC6836A747C3D00F3FEC767F7C2FE6EDEFFE7584D634FB81CA63` |

构建链：`aapt2 compile/link` → `javac` → `d8` → `zipalign` → `apksigner`，全部通过。

## 4. 验证清单

- [x] `node --check`：`cloud.js`、`session.js`、`live.js` 通过。
- [x] `index.html` 内联脚本单独抽取后 `node --check` 通过。
- [x] 无坐标、权限 `prompt` 时问“从我当前位置去看川文化村都有哪几条路可以选”，气泡返回“路线 · 需要地图定位权限”，含“允许定位并继续 / 去系统设置”，不再直接给静态路线。
- [x] 注入模拟坐标 `35.10,129.03` 后问同一句，返回甘川文化村、直线约 4.8 km（±38 m）、公交/打车/步行 3 条走法与 3 个 NAVER 深链。
- [x] 未授权时不再出现“库里没有这个地点”。
- [x] 真实 Kilo 模型（HTTP 200，`nvidia/nemotron-3.5-super-vl:free`）路线摘要返回中文 2–3 句，明确写了“直线距离不是道路距离，具体换乘以 NAVER 实时结果为准”，没有编造线路号/班次。
- [x] `aapt dump badging`：versionCode 11 / versionName 1.9；APK 内无 `lib/`。
- [x] `dexdump` 确认 `MainActivity$HostBridge` 内存在 `hasLocationPermission`、`startLocationWatch`、`stopLocationWatch`、`openAppSettings`。
- [x] `apksigner verify`：签名证书 SHA-256 未变。
- [x] 最终 APK / zip SHA-256 已记录。

截图：

- `Busan/apk_build/v19_permission.png`（无权限时的路线权限卡）
- `Busan/apk_build/v19_route.png`（已定位后的 3 条走法）
- 旧回归图：`v18_probe_home.png`、`v18_probe_choices.png`、`v18_probe_plan.png`、`v18_probe_account.png`

## 5. 已知限制

1. **未真机验证**：`adb devices` 为空。已用无头 Chrome + 模拟坐标验证前台链路，并确认 DEX 里桥接方法存在；但 Android 系统权限弹窗、授权回传、`nmap://` 拉起 NAVER、真实 GPS 精度仍需真机验收。
2. **NAVER 路线没有抓取**：App 生成 `nmap://` 深链让 NAVER 自己算实时路线；没有 NAVER Directions API Key，因此无法读取 NAVER 返回的具体线路号/班次，再把原文总结。当前“总结”只基于本地的直线距离与三类走法，正文明确标注这一点。
3. **“地图权限”指本 App 的定位权限**：无法检查或修改 NAVER 地图 App 自己的权限；NAVER 未安装/未授权时只能提示用网页地图。
4. **没有逆地理编码**：只显示坐标与到景点直线距离，不显示“你现在在某某洞/某某路”。
5. **实时数据库是包内快照 + 云端意图**：没有接景点实时营业/客流 API；“实时”指实时定位与当前问题查询，不是实时票价/排队。
6. **权限申请需要一次点击**：为避免用户没看到系统弹窗就跳过，未授权时先显示权限卡，点“允许定位并继续”才发起系统申请；不是静默申请。
7. **Kilo 匿名额度**：200 请求/小时/IP；模型摘要失败时只显示本地路线，不阻塞主回答。
8. **论文未同步**：HCI2026 中英论文的蓝色评审意见仍未处理。

## 6. 下一轮建议

1. 真机安装 v1.9，完整走一遍：首次路线问题 → 权限卡 → 系统允许 → 路线 → 点 NAVER 深链。
2. 若需要“NAVER 具体线路总结”，申请 NAVER Maps Directions API 或接 ODsay，替换当前估算；不要继续用直线距离冒充道路距离。
3. 在权限被永久拒绝时补“再次申请”与“跳转设置”双路径的真机回归。
4. 补逆地理编码，把“当前位置”显示成可读地名。
