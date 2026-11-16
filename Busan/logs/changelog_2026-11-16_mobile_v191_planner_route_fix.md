# Busan 手机版 v1.9.1 开发日志：修掉“有几条路线”被误判成行程规划

- **日期**：2026-11-16
- **版本**：versionCode 12 / versionName 1.9.1
- **触发截图**：15:52，实时定位未开启，问“从当前位置去甘川文化村有几条路线可”，App 返回“自主分析 · 大模型 / 甘川文化村艺术行程”，仍然没有进入定位权限与路线流程。
- **上一版**：v1.9 已加路线权限卡（提交 `2d2a905`），但这次截图证明**问题不在权限卡本身，而在更前面的 planner 分流**。

## 1. 真正根因

`Busan/android/assets/planner.js` 的 `intercept()` 把“路线”当成强规划词：

```js
var strong = /规划|安排|行程|路线|怎么玩|玩什么|.../
```

而第二段排除逻辑又写了：

```js
if (spot && intent !== "overview" && !/规划|安排|行程|路线|.../.test(t)) return false;
```

用户这句话含“**路线**”二字，`! /...路线.../` 直接为 `false`，所以 planner 继续拦截，交给 `BusanPlanner.run()` 生成“甘川文化村艺术行程”。`ask()` 里的 `routeAnswer()`、定位权限检查根本没机会执行。

这解释了为什么 v1.9 明明加了权限卡，真机上却还是“艺术行程”。

## 2. 修复

`planner.js` 的 `intercept()` 最前面新增“明确路线问句”优先分流：

```js
var spot = C.findSpot(t);
if (spot &&
    /几条(路|线)|有哪几条|哪几条|怎么去|怎么走|怎么到|如何到|
     从.{0,8}当前位置|从我(这里|当前位置)?|当前位置.{0,8}(去|到)|
     路线可|交通方式/.test(t) &&
    !/规划|安排|行程|一日游|半日|半天|怎么玩|玩什么|
      带.{0,6}(逛|玩)|itinerary|plan a trip/i.test(t)) {
  return false; // 交给 ask() 的路线权限流程
}
```

规则变成：

- “从当前位置去甘川文化村有几条路线可/可以选” → **不拦截**，进入 `routeAnswer()`；
- “甘川文化村怎么去/怎么走” → **不拦截**，进入路线；
- “甘川文化村路线规划/安排一日游/半天怎么玩” → 仍由 planner 规划；
- “甘川文化村 门票/开放时间” → 事实问答；
- 不再出现“只要含路线二字就做行程”的情况。

## 3. 验证

### 3.1 截图原句

无头 Chrome，模拟 `BusanLive.permission()` 为 `prompt`、无坐标：

- 修复前：`BusanPlanner.intercept("从当前位置去甘川文化村有几条路线可")` = **true**；
- 修复后：**false**；
- 对话最后一条气泡：

```
路线 · 需要地图定位权限
去 甘川文化村 的走法需要你的当前位置。
点“允许定位并继续”，系统会弹一次定位授权；允许后我会读取当前坐标，
再汇总公交 / 打车 / 步行三种走法。
[允许定位并继续] [去系统设置]
```

不再返回“甘川文化村艺术行程”。

### 3.2 planner 分流回归

同一浏览器中直接调用 `BusanPlanner.intercept()`：

| 输入 | 结果 |
| --- | --- |
| `从当前位置去甘川文化村有几条路线可以选` | false（进路线） |
| `甘川文化村怎么去` | false（进路线） |
| `甘川文化村路线规划` | true（进行程规划） |
| `甘川文化村 门票` | false（事实问答） |

### 3.3 权限与坐标链路

沿用 v1.9 已验证的链路：

- 无坐标：先出权限卡；
- 注入 `35.10,129.03` 后：返回甘川文化村、直线约 4.8 km（±38 m）、公交/打车/步行 3 条走法与 3 个 NAVER `nmap://` 深链；
- 权限卡按钮：`BusanLive.ensure()` → `BusanHost.startLocationWatch()`；拒绝后显示“去系统设置”。

## 4. 构建结果

| 产物 | 结果 |
| --- | --- |
| APK | `Busan/dist/Busan旅行助手.apk` |
| APK 体积 | **239,004 B（233.4 KB）** |
| APK SHA-256 | `55909931A8FDEBF7670E8FFE9A2D7C21B3995C2439BB745531F5FCD03128AADD` |
| 版本 | versionCode **12** / versionName **1.9.1** |
| 包名 | `com.busan.tour` |
| 原生库 | `lib = []` |
| 签名证书 SHA-256 | `9d91ed6b8ffeec5eaf5b597ee19f56bfda6f8663d94ec726390a552224d33356` |
| zip | `Busan/dist/Busan_Tour_App.zip` |
| zip 体积 | **2,617,161 B** |
| zip SHA-256 | `3ED86CBBF9F55E97B51632488DC663B9EFECB70D9650E7AC04A07FC6E656BBDE` |

构建链：`aapt2 compile/link` → `javac` → `d8` → `zipalign` → `apksigner`，全部通过。

## 5. 验证清单

- [x] `node --check`：`planner.js`、`cloud.js`、`live.js`、`session.js` 通过。
- [x] 截图原句进入权限卡，不再产生“艺术行程”。
- [x] `BusanPlanner.intercept` 四个分流用例符合预期（路线/路线/规划/门票）。
- [x] 无坐标路线卡与有坐标 3 条走法均验证。
- [x] APK 内 `planner.js` 含 `几条(路|线)` 分流守卫，`live.js` 含 `ensure`。
- [x] `aapt dump badging`：versionCode 12 / versionName 1.9.1；无 `lib/`。
- [x] `apksigner verify`：签名证书 SHA-256 未变。
- [x] 最终 APK/zip SHA-256 已记录。

截图：

- `Busan/apk_build/v191_fixed.png`（干净首屏、截图原句、权限卡）
- `Busan/apk_build/v19b_fixed.png`（带历史状态的复现对照）
- `Busan/apk_build/v19_permission.png` / `v19_route.png`（v1.9 权限卡与路线）

## 6. 已知限制

1. **未真机验证**：`adb devices` 仍为空；无头 Chrome 验证的是网页链路，Android 系统权限弹窗、授权回传、`nmap://` 拉起 NAVER 仍需真机。
2. **权限卡需要一次点击**：未授权时先显示“允许定位并继续”，点击后才发起系统申请；不是静默申请。
3. **NAVER 路线未抓取**：只生成 `nmap://` 深链让 NAVER 算实时路线，App 的摘要基于直线距离和三类走法，不含具体线路号/班次/末班。
4. **历史会话重放**：`rerenderAll()` 重放历史时会走旧的 `cloudAnswer()`，旧路线问题可能显示“还没拿到当前位置”的静态说明；新提问会走权限卡。若需要历史也统一走权限流程，下一轮可改重放分支。
5. **Kilo 匿名额度**：200 请求/小时/IP，模型失败时回退本地。

## 7. 下一步

1. 真机装 v1.9.1，先问截图原句，确认直接出现权限卡；点允许后再看 3 条走法。
2. 再测“甘川文化村路线规划”是否仍走行程，避免把路线问答和行程规划混在一起。
3. 如要真正“总结 NAVER 给的路线”，需申请 NAVER Directions API / ODsay，而不是继续用深链。
