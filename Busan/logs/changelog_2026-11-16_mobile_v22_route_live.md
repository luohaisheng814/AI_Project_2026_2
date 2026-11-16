# Busan 手机版 v2.2 开发日志：实时定位 + 最优路线

- 日期：2026-11-16
- 版本：v2.2（versionCode 15 / versionName 2.2）
- 包名：`com.busan.tour`
- 仓库：<https://github.com/luohaisheng814/AI_Project_2026_2>
- 上一版：v2.1（versionCode 14 / 2.1，commit `9abcc1ef9ab83886cefbf89bea09be1f84e5e99c`）

## 一、用户反馈与真实根因

用户上传 17:18 真机截图，输入：

```text
去甘村文化村的路线有几条可以推荐的
```

期望得到“从当前位置去甘川文化村的走法”，实际却返回了“甘川文化村半日艺术拍照行程”。

截图顶部实时条同时显示：

```text
距 长林浦口 4.0 km · 实时 · ±100 m
```

说明 `BusanLive.position()` 已经有坐标，问题不是“完全没定位”，而是：

1. `findSpot()` 没有收录“甘村”这个错字，`spot = null`；
2. v1.9.1 的路线守卫只在“有具体景点，或句子里有当前位置/从我这里”时生效；
3. 地名写错后守卫失效，`intercept()` 的 `strong` 正则包含“路线”，planner 抢先返回半日行程。

v2.2 按“定位存在，但路线问句被 planner 抢答”修复，并补上“没有坐标时”的权限卡路径。

## 二、v2.2 修改内容

### 1. `android/assets/cloud.js`

- `findSpot()` 的归一链新增：
  - `甘村文化村 → 甘川文化村`
  - `甘村 → 甘川`
- 现在以下写法都能命中甘川文化村：
  - `甘川`
  - `看川`
  - `甘村`
  - `甘村文化村`
- `routeTo()` 新增“最优建议”段落，按当前位置到目标的直线距离给出优先级：
  - `km <= 1.2`：步行/无障碍优先；
  - `1.2 < km <= 7`：公共交通优先，打车作为赶时间备选；
  - `km > 7`：公共交通优先 + 打车备选，不建议全程步行。
- 原有内容保留：
  - 3 条可选走法（公共交通 / 打车直达 / 步行·无障碍）；
  - NAVER `nmap://route` 深链；
  - 直线距离、定位精度 `±xx m`、坐标系说明。

### 2. `android/assets/planner.js`

- `intercept()` 新增显式路线问句 `routeAsk` 与规划问句 `planAsk`：
  - 命中“几条路/几条线/有哪几条/怎么去/怎么走/从当前位置/路线可/交通方式”等，且不含“规划/安排/行程/一日游/半日/半天/怎么玩/玩什么”时，直接 `return false`，交给 `ask()` 的定位权限与实时路线流程；
  - 即使地名有错字、`findSpot` 没命中，只要不是规划词，也不会再被 planner 抢走；
  - `甘川文化村路线规划` 仍返回 `true`，保留行程规划能力。

### 3. 版本与 UA

- `android/AndroidManifest.xml`：`versionCode 14 → 15`，`versionName 2.1 → 2.2`；
- `MainActivity.java`：注释更新为 v2.2；云端请求 UA `BusanTour/2.1 (Android) → BusanTour/2.2 (Android)`；
- 版本注释补充 v2.2 修复说明。

## 三、测试结果

### 1. 核心 JS 回归（`Busan/apk_build/test_v22.js`）

命令：

```powershell
cd D:\AI_Project_2026_2\Busan
node apk_build\test_v22.js
```

结果：**43 PASS / 0 FAIL**。覆盖：

- 景点库 18 个点；
- `甘川/看川/甘村/甘村文化村` 别名；
- `routeTo()`：`kind=route`、3 条深链、`4.84 km`、`±38 m`；
- “最优建议”三档阈值：
  - 南浦洞 0.2 km → 步行/无障碍优先；
  - 甘川 4.84 km → 公共交通优先；
  - 海云台 13.54 km → 公共交通优先 + 打车备选；
- 无坐标时回退常规交通；
- 路线问句返回 `kind=route`；
- 门票字段含“免费”；
- 上午推荐 3 个方案；
- 6 类人群识别与推荐：
  - 一人男：甘川 / 海东龙宫寺 / 太宗台
  - 一人女：甘川 / 白浅滩 / 广安里
  - 两人男女：广安里 / 甘川 / 松岛
  - 两人男男：太宗台 / 札嘎其 / 海云台
  - 两人女女：白浅滩 / 广安里 / 甘川
  - 三人以上：海云台 / 松岛 / 札嘎其
- 玩法 + 人群交叉推荐；
- 附近 3 个最近点（模拟坐标 `35.10,129.03`）：
  - 南浦洞 BIFF 广场 / 龙头山公园 / 札嘎其市场；
- planner 拦截矩阵：
  - `去甘村文化村的路线有几条可以推荐的` → `false`
  - `甘川文化村路线规划` → `true`
  - `从当前位置去甘川文化村有几条路线` → `false`
  - `甘川文化村怎么去` → `false`
  - `甘川文化村 门票` → `false`
  - `半天想拍照，少走路，帮我安排` → `true`
- 6 类人群调用 `buildLocal()` 均能返回 ≥2 个选择；
- 离线引擎：
  - 甘川景点回答；
  - `一个人女性 → solo_female`；
  - `甘川文化村 门票 → ticket`。

### 2. 无头 Chrome UI 回归

命令：

```powershell
cd D:\AI_Project_2026_2\Busan
python apk_build\_v22probe2.py
```

页面：`file:///D:/AI_Project_2026_2/Busan/android/assets/index.html`，500×1400，CDP 9224。

结果：

```text
PREFS_OPEN prefs-body|自动 · 自动
PREFS_CLOSED prefs-body|玩法 · 出行
自动 · 自动
展开
PREFS_REOPEN prefs-body

NO_POS_KIND {"perm":true,"route":false,"planner":false,
 "text":"路线 · 需要地图定位权限\n去 甘川文化村 的走法需要你的当前位置。..."}

WITH_POS {"route":true,"best":true,"km":true,"acc":true}

OFFICIAL {"text":"官网核对\nhttps://www.saha.go.kr/tour/contents.do?mId=0101010000 ↗",
 "hasUrl":true,"hasKo":false}

LANG_EN {"title":"Busan AI Travel Assistant","btn":"Send","on":"on"}
LANG_ZH {"title":"釜山 AI 旅行助手","on":"on"}
SPOTS 18
```

覆盖：折叠条自动收起/展开、无坐标路线权限卡、有坐标路线与最优建议、官网只显示 URL、 中/英切换、在线景点数 18。

截图：

- `Busan/apk_build/v22_permission.png` — 无坐标时的路线权限卡；
- `Busan/apk_build/v22_route_fix.png` — 4.8 km、实时 ±38 m、最优建议、3 条走法；
- `Busan/apk_build/v22_official.png` — 官网核对只显示 URL；
- `Busan/apk_build/v22_lang_en.png` — 英文界面。

### 3. 原有回归

命令与结果：

```powershell
node apk_build\test_engine.js      # 离线引擎全部断言通过
node apk_build\test_cloud_round.js # 6 组问答 + 中/韩/英输出正常
python test_scope.py               # 4 组作用域 + 4 组推断，exit 0
python test_lang_policy.py         # ALL LANG-POLICY CHECKS PASSED
```

说明：`test_engine.js` 使用包内 8 个旧点，输出“景点数: 8”属于旧测试数据口径；线上/包内快照路径仍为 18 个点。

### 4. APK / zip 校验

最终产物：

| 文件 | 体积 | SHA-256 |
|---|---:|---|
| `Busan/dist/Busan旅行助手.apk` | 267,676 B | `5A687AA101599EBFB0837C76FF513D6F1D7DF3CEDBA09451A786B77CE0045A6C` |
| `Busan/dist/Busan_Tour_App.zip` | 2,682,512 B | `B4770B76CC7AE7365235AC942657E043BD9C4CDFBEDA0D125C024C000C8FDD4A` |

校验结果：

- `aapt2 dump badging`：`versionCode='15' versionName='2.2'`；
- 签名证书 SHA-256：`9d91ed6b8ffeec5eaf5b597ee19f56bfda6f8663d94ec726390a552224d33356`；
- APK 内 8 个关键资产（`cloud.js` / `planner.js` / `index.html` / `live.js` / `app.js` / `session.js` / `data.js` / `cloud_snapshot.js`）与源码 SHA-256 全部一致；
- APK 内含 `甘村` 别名、`最优建议`、`routeAsk`；
- APK 内 `lib=[]`，无端侧原生库；
- zip 内嵌 APK 的 SHA-256 与 `dist` APK 一致；
- zip 内 `mobile/assets/planner.js` 同样含 `routeAsk`。

## 四、已知限制

1. **真机权限链路未验证**：当前 `adb devices` 为空，没有真机/模拟器；Android 系统定位权限弹窗、授权回传、后台定位节流无法在本轮实测。
2. **NAVER 深链未实际拉起**：只生成 `nmap://route/...` 深链；没有 NAVER Directions API Key，无法抓取具体线路号、班次、末班车和道路级耗时。
3. **“最优路线”是直线距离优先级，不是道路级最优**：`km` 为两点直线距离；实际道路距离、红绿灯、换乘次数由 NAVER 打开后计算。
4. **云端模型本轮未做真实请求验证**：无头测试强制离线；Kilo 匿名接口此前有 HTTP 200 记录，但本轮未重新压测在线模型稳定性。
5. **GitHub raw 可能缓存旧 8 点**：`cloud.js` 仍用包内 18 点快照补齐；线上 raw `main` 的刷新延迟不在 App 控制范围内。
6. **测试脚本 `test_engine.js` 仍基于旧 8 点数据**：只作为历史离线断言，不代表当前 18 点全量库。
7. **未做 Android 仪器测试/Espresso**：没有 Gradle/Android Studio 工程，当前是 `aapt2 + javac + d8 + apksigner` 手工流水线，UI 回归用无头 Chrome 代替 WebView。
8. **`Busan/busan_travel.db` 有未提交修改**：本轮未改动、未提交，避免误提交运行时数据。

## 五、验证清单

- [x] `甘村` / `甘村文化村` / `看川` 归一为甘川文化村
- [x] 原句 `去甘村文化村的路线有几条可以推荐的` 不再进入 planner
- [x] `甘川文化村路线规划` 仍进入 planner
- [x] 无坐标时显示路线权限卡
- [x] 有坐标时显示实时距离、精度、3 条走法
- [x] 最优建议三档阈值（≤1.2 / 1.2–7 / >7 km）
- [x] 3 条 NAVER `nmap://route` 深链
- [x] 附近 3 个最近点
- [x] 6 类人群推荐
- [x] 玩法 + 人群交叉推荐
- [x] 官网核对块只显示 URL、无韩文原文
- [x] 中文 / English 界面切换
- [x] 玩法/出行折叠条 7 秒自动收起、可重新展开
- [x] 18 个景点在线快照
- [x] APK versionCode 15 / versionName 2.2
- [x] APK 内资产与源码哈希一致
- [x] APK 签名校验通过、无 `lib/`
- [x] zip 内嵌 APK 与 dist APK 哈希一致
- [x] `test_v22.js` 43/43
- [x] `test_engine.js` / `test_cloud_round.js` / `test_scope.py` / `test_lang_policy.py` 通过
- [ ] 真机系统权限弹窗与授权回传（无设备，未验证）
- [ ] NAVER App 实际拉起与线路详情（无 Key/设备，未验证）
- [ ] Android 仪器测试（无 Gradle 工程，未验证）

## 六、产物与回滚

- APK：`Busan/dist/Busan旅行助手.apk`
- 分发包：`Busan/dist/Busan_Tour_App.zip`
- 源码：`Busan/android/assets/cloud.js`、`Busan/android/assets/planner.js`
- 版本：`Busan/android/AndroidManifest.xml`、`Busan/android/java/com/busan/tour/MainActivity.java`
- 测试：`Busan/apk_build/test_v22.js`
- 截图：`v22_permission.png`、`v22_route_fix.png`、`v22_official.png`、`v22_lang_en.png`

回滚：将上述 4 个源码/版本文件恢复到 v2.1 commit `9abcc1ef9ab83886cefbf89bea09be1f84e5e99c`，重新执行 `build_apk.py` 与 `make_dist_zip.py` 即可回到 v2.1 的 263,580 B APK。
