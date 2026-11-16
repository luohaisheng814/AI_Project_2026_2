# Busan 手机版 v2.3 更新日志

- 日期：2026-11-17
- 版本：`versionCode 16` / `versionName 2.3`
- 包名：`com.busan.tour`
- 基线：v2.2（commit `27932a70e08de409b69f4440e04ec4a7f7405c87`）
- 仓库：<https://github.com/luohaisheng814/AI_Project_2026_2.git>

## 一、本次要解决的三个问题

1. **没有实时定位，导致无法做“从我当前位置到景点”的最优路线推荐。**
2. **地图入口没有标明归属哪个地图软件**，用户不知道点的是 NAVER 还是 Google。
3. **景点回答上方没有实景图片**，回答只有文字，缺少直观参考。

## 二、实时定位链路修正

### 2.1 原链路的问题

| 位置 | 原行为 | 问题 |
|---|---|---|
| `live.js` 原生 `LocationManager` | 每 3 秒 / 12 米回传坐标 | 部分 ROM 授权后重启 App，实时条仍显示“未开启”，用户以为定位坏了 |
| `index.html` 的“附近”按钮 | `navigator.geolocation.getCurrentPosition` | 部分 WebView 不回传坐标，按钮一直转圈或静默失败 |
| 路线问答 | `BusanLive.ensure()` | 未授权时直接进入等待，没有明确的“已授权但没坐标”提示 |
| `MainActivity` 权限回调 `1001` | 授权与否都调用 `__busanLocReady()` | 用户拒绝后仍走“等待坐标”，可能重复弹授权或空等 |

### 2.2 v2.3 的修正

- `BusanLive.init()`：启动时若 `BusanHost.hasLocationPermission()` 为 true，800ms 后自动 `start()`，不再要求用户每次手动点“实时”。
- 原生 `startLocationWatch()` 返回 true 后增加 **15 秒 watchdog**：
  - 15 秒仍无坐标 → 文案提示“已开启定位，但 15 秒还没拿到坐标：室内或 GPS 弱时可走到窗边/室外，或点停止后重试”。
- 原生返回 false（等待系统授权）时，8 秒后提示：
  - “等待定位授权…如已允许，请确认手机定位开关已打开”。
- `stop()` / `__busanLocError()` 清理 `waitTimer`，避免旧定时器覆盖新状态。
- `MainActivity.onRequestPermissionsResult` 的 `1001` 分支：
  - 授权成功 → 继续 `__busanLocReady()`；
  - 拒绝 → `__busanLocError(1, 'permission_denied')`，不再空等。
- `index.html` 的 `locateOnce()`：
  - 优先 `BusanLive.ensure(done, 15000)`，统一走 Android 原生 `LocationManager`；
  - 只有 `BusanLive` 不存在时才退回 `navigator.geolocation.getCurrentPosition`。
- “附近”按钮、路线问句、实时距离条现在共用同一份坐标，不再出现“实时条有坐标、附近按钮拿不到”的分裂状态。

### 2.3 最优路线推荐

坐标拿到后，`cloud.js` 的 `routeTo()` 按直线距离分三档给出“最优建议”：

| 直线距离 | 建议 |
|---|---|
| ≤ 1.2 km | 步行 / 无障碍优先 |
| 1.2–7 km | 公共交通优先，打车备选 |
| > 7 km | 公共交通优先 + 打车备选 |

同时保留 3 条可点走的实时路线（公共交通 / 打车 / 步行·无障碍），每条都挂 NAVER 深链。无坐标时显示“路线 · 需要地图定位权限”卡片，不再用半日行程抢答路线问题。

## 三、地图软件归属标注

`cloud.js` 三语文案统一改为明确带地图品牌：

| key | 中文 | 韩文 | 英文 |
|---|---|---|---|
| `jump` | `NAVER 导航` | `NAVER 길찾기` | `NAVER Directions` |
| `place` | `NAVER 地点` | `NAVER 장소` | `NAVER Place` |
| `webmap` | `NAVER 网页地图` | `NAVER 웹 지도` | `NAVER Web Map` |
| `google` | `Google 地图` | `Google 지도` | `Google Maps` |

`index.html` 路线区块：

- 标题：`NAVER 地图 · 选一条实时路线 / NAVER 지도 · 실시간 경로 선택 / NAVER Map · pick a live route`
- 每条走法右侧：`NAVER 地图 › / NAVER 지도 › / NAVER Map ›`

地点卡的四个外链现在分别显示 `NAVER 导航 / NAVER 地点 / NAVER 网页地图 / Google 地图`，不再出现“打开 ›”这种不说明归属的按钮。

## 四、景点实景图片

### 4.1 图片来源与数量

- 主来源：Wikimedia Commons API（900px 缩略图），保留 `title / credit / license / sourceUrl / alt`。
- 补充来源：韩国观光公社、釜山观光公社、VisitBusan、Trip.com 等公开旅游页面，标记为“公共机构旅游宣传图（来源标注）”。
- 抓取脚本遇到 Commons `HTTP 429` 时退避重试，并过滤 `station / subway / entrance / platform / sand art / avatar` 等坏标题；必要时用维基百科首图兜底。
- 最终 **18 个景点、54 张图**，每个景点至少 2 张：

| 景点 | 张数 |
|---|---:|
| 甘川文化村 | 3 |
| 多大浦梦之夕阳喷泉 | 3 |
| 多大浦海水浴场 | 4 |
| 没云台 | 3 |
| 乙淑岛候鸟公园 | 3 |
| 峨嵋山观景台 | 3 |
| 洛东江河口生态中心 | 2 |
| 长林浦口 | 3 |
| 海云台海水浴场 | 3 |
| 广安里海水浴场 | 3 |
| 太宗台 | 3 |
| 札嘎其市场 | 3 |
| 南浦洞BIFF广场 | 3 |
| 松岛海水浴场 | 3 |
| 白浅滩文化村 | 3 |
| 龙头山公园 | 3 |
| 海东龙宫寺 | 3 |
| 西面 | 3 |

### 4.2 前端展示

- `android/assets/photos.js`：`window.BUSAN_PHOTOS = {景点名: [{src, caption, credit, license, sourceUrl, title, alt}, ...]}`，离线可用。
- `android/assets/photos_manifest.json`：54 张图的来源、许可、标题、alt 清单。
- `index.html` 新增 `.photos / .photostrip / .photocredit`：
  - 3–4 张 128×86 圆角图横向滑动，不挤压正文；
  - 优先读 `result.photos`，没有则按 `result.spotId` / `result.spot.id` 从 `window.BUSAN_PHOTOS` 取；
  - 每张 `alt / title` 带 caption、credit、license；
  - 底部显示“实景图片 · Wikimedia Commons / Wikipedia / 公共机构旅游宣传图 · 许可”。
- `paintBubble()` 在 badge/tag 之后、正文之前插入 `photosHtml(result)`，实现“景点回答上方先看图”。
- `index.html` 在 `cloud_snapshot.js` 之后加载 `photos.js`，保证 `cloud.js` 运行时 `window.BUSAN_PHOTOS` 已存在。

## 五、构建与产物

### 5.1 构建命令

```powershell
cd D:\AI_Project_2026_2\Busan
& 'D:\AI_Project_2026_2\.venv\Scripts\python.exe' apk_build\build_apk.py
& 'D:\AI_Project_2026_2\.venv\Scripts\python.exe' apk_build\make_dist_zip.py
```

### 5.2 APK

- 路径：`D:\AI_Project_2026_2\Busan\dist\Busan旅行助手.apk`
- 大小：`10,212,908 B`（约 9.74 MiB）
- SHA-256：`9E129F228DB70A8FC7A3A05113CBDA41192B5C8D2A813C88A687C78C4A39A82D`
- 版本：`versionCode 16` / `versionName 2.3`
- 包名：`com.busan.tour`
- 签名证书 SHA-256：`9d91ed6b8ffeec5eaf5b597ee19f56bfda6f8663d94ec726390a552224d33356`
- 已校验 APK 内含：
  - `assets/photos.js`：存在
  - `assets/photos/`：54 个文件
  - `assets/index.html` 含 `photos.js` 引用与 `NAVER 地图` 文案

> 体积说明：v2.2 为 267,676 B；v2.3 因内置 54 张实景图增至 10,212,908 B。所有图片随 APK 离线可用。

### 5.3 完整分发包

- 路径：`D:\AI_Project_2026_2\Busan\dist\Busan_Tour_App.zip`
- 大小：`22,503,222 B`（约 21.46 MiB）
- SHA-256：`A3CAE30822C41E926905C694E486E9E75516C616B927D7D38E0BCC7AD4F2A73B`
- 已校验 zip 内：
  - `Busan_Tour_App/mobile/index.html`
  - `Busan_Tour_App/mobile/assets/photos.js`
  - `Busan_Tour_App/mobile/assets/photos/`：54 个文件
  - `Busan_Tour_App/Busan旅行助手.apk`：v2.3 APK
  - `mobile/index.html` 含 `photos.js` 引用与 `NAVER 地图` 文案

## 六、测试结果

### 6.1 自动化回归

| 测试 | 命令 | 结果 |
|---|---|---|
| v2.3 引擎回归 | `node apk_build/test_v23.js` | **50 PASS / 0 FAIL** |
| v2.2 引擎回归 | `node apk_build/test_v22.js` | **43 PASS / 0 FAIL** |
| 离线引擎 | `node apk_build/test_engine.js` | 全部断言通过 |
| 云端问答（离线模式） | `node apk_build/test_cloud_round.js` | 6 组问答 + 中/韩/英正常 |
| 作用域/推断 | `.venv\Scripts\python.exe test_scope.py` | exit 0 |
| 语言策略 | `.venv\Scripts\python.exe test_lang_policy.py` | `ALL LANG-POLICY CHECKS PASSED` |
| JS 语法 | `node --check`（`_index_inline.js`、`cloud.js`、`live.js`、`photos.js`） | 全部通过 |

v2.3 新增断言（节选）：

- 18 个景点每个至少 2 张图；
- 总图片数 = 54；
- `route.photos` = 3；
- 景点回答 `photos` = 3；
- `jump / webmap / google` 文案含 `NAVER` / `Google`。

### 6.2 UI 无头 Chrome 探针

脚本：`apk_build/_v23probe.py`（CDP 9225，500×1400）

| 检查 | 结果 |
|---|---|
| `PHOTOS_READY` | `{"spots":18,"photos":54}` |
| `NO_POS_CARD` | `perm=true, route=false`，无坐标显示路线权限卡 |
| `ROUTE` | `route=true, best=true, km=true, acc=true, photos=3, loaded=true, navH=true, navBtn=true` |
| `SPOT_PHOTOS` | `photos=3, loaded=true, credit="实景图片 · Wikimedia Commons · CC BY-SA 4.0 / CC0"` |
| `MAP_LABELS` | `["NAVER 导航","NAVER 地点","NAVER 网页地图","Google 地图"]`，NAVER 3 个 / Google 1 个 |
| `LANG_EN` | 标题 `Busan AI Travel Assistant`、按钮 `Send`、英文按钮 `on` |
| `LANG_ZH` | 标题 `釜山 AI 旅行助手`、中文按钮 `on` |
| `SPOTS` | `18` |

截图：

- `Busan/apk_build/v23_permission.png`：无坐标路线权限卡
- `Busan/apk_build/v23_route.png`：4.8 km / ±38 m / 3 张甘川图 / `NAVER 地图 · 选一条实时路线` / 3 条走法
- `Busan/apk_build/v23_spot_photos.png`：甘川回答上方 3 张图 + 图片来源
- `Busan/apk_build/v23_map_labels.png`：地点卡四链接 `NAVER 导航 / NAVER 地点 / NAVER 网页地图 / Google 地图`
- `Busan/apk_build/v23_lang_en.png`：英文界面
- `Busan/apk_build/v23_live_auto.png`：已授权时自动进入“正在获取位置…”并显示实时距离

### 6.3 实时定位专项探针

脚本：`apk_build/_v23liveprobe.py`

| 检查 | 结果 |
|---|---|
| 已授权 → 自动恢复 | `watching=true`，状态文案 `正在获取位置…`，按钮变为 `停止` |
| 坐标回传 | 文案 `最近 南浦洞BIFF广场 0.2 km · 实时 · ±38 m`，状态点 `ldot on` |

> 说明：探针通过注入 `BusanHost` 模拟 Android 原生桥接；真机系统权限弹窗与 GPS 冷启动仍需设备验证，见“已知限制”。

## 七、已知限制

1. **真机未验证**：`adb devices` 为空，没有连接真机或模拟器。以下项目只有无头 Chrome / Node 验证，没有设备级验证：
   - 系统定位权限弹窗文案与“拒绝后不重复弹窗”；
   - Android `LocationManager` 首次冷启动坐标时延；
   - 室内/GPS 弱信号下 15 秒 watchdog 的实际表现；
   - 点击 `NAVER 导航` 能否拉起 NAVER Map / NAVER 导航 App；
   - APK 安装、升级覆盖、签名校验。
2. **在线模型未重新压测**：v2.3 回归强制离线，未对 `https://ai-gateway.kilo.ai/api/v1/chat/completions`（`nvidia/nemotron-3.5-super-vl:free`）做在线延迟/限流压测。
3. **图片授权未做法律级审查**：图片均标注来源与许可，但未逐张核验再分发条款；商用/公开发行前建议逐张复核。
4. **图片质量仍有瑕疵**：
   - `dadaepo-beach-01` 偏灰；
   - `nakdong-estuary-02` 是 Daejeo 生态公园农田，不是河口生态中心主体；
   - `jangnim-03` 右下有小水印图标；
   - `dadaepo-fountain-01` 分辨率偏低；
   - `eulsukdo-02` 是远景全景。
5. **APK 体积增至约 10.2 MB**：所有 54 张图内置，换取离线可用；如更在意体积，可后续改为按需下载或压缩到 720px。
6. **无坐标时的路线卡依赖用户授权**：首次安装不会自动弹系统权限，需点“实时”或路线卡的“允许定位并继续”。

## 八、验证清单（可复跑）

- [x] `AndroidManifest.xml` 为 `versionCode=16` / `versionName=2.3`
- [x] `MainActivity` UA 为 `BusanTour/2.3 (Android)`
- [x] `node apk_build/test_v23.js` → 50 PASS / 0 FAIL
- [x] `node apk_build/test_v22.js` → 43 PASS / 0 FAIL
- [x] `node apk_build/test_engine.js` → 全部通过
- [x] `node apk_build/test_cloud_round.js` → 6 组问答正常
- [x] `python test_scope.py` → exit 0
- [x] `python test_lang_policy.py` → ALL PASS
- [x] `_index_inline.js` / `cloud.js` / `live.js` / `photos.js` → `node --check` 通过
- [x] `apk_build/_v23probe.py` → 路线 3 条 + 3 张图 + NAVER 标注 + 中英切换
- [x] `apk_build/_v23liveprobe.py` → 已授权自动恢复 + 实时距离
- [x] APK 内含 `assets/photos.js` 与 54 张 `assets/photos/*`
- [x] ZIP 内含 `mobile/assets/photos.js` 与 54 张 `mobile/assets/photos/*`
- [x] APK 签名校验通过，证书 SHA-256 与历史版本一致
- [ ] 真机安装 / 系统定位授权 / NAVER App 拉起（无设备，未做）
- [ ] 图片再分发许可逐张法律复核（未做）

## 九、复现命令

```powershell
cd D:\AI_Project_2026_2\Busan

# 回归
node apk_build\test_v23.js
node apk_build\test_v22.js
node apk_build\test_engine.js
node apk_build\test_cloud_round.js
& 'D:\AI_Project_2026_2\.venv\Scripts\python.exe' test_scope.py
& 'D:\AI_Project_2026_2\.venv\Scripts\python.exe' test_lang_policy.py

# UI 探针
python apk_build\_v23probe.py
python apk_build\_v23liveprobe.py

# 构建
& 'D:\AI_Project_2026_2\.venv\Scripts\python.exe' apk_build\build_apk.py
& 'D:\AI_Project_2026_2\.venv\Scripts\python.exe' apk_build\make_dist_zip.py
```

## 十、提交与推送

- 本次提交：`<待填>`（代码 + 图片资产 + 构建脚本 + 日志）
- 远端：`https://github.com/luohaisheng814/AI_Project_2026_2.git`，分支 `main`
- 上一版 v2.2：`27932a70e08de409b69f4440e04ec4a7f7405c87`

> 日志中的提交哈希在 push 后回填；如出现第二个 docs 提交，以 `git log` 最新一条为准。
