# Busan 手机版 v2.1 开发日志

- 日期：2026-11-16
- 版本：versionCode **14** / versionName **2.1**
- 主题：玩法/出行折叠条、官网只给网址、按出行组合差异化推荐

## 一、本次改动

### 1. 玩法 + 出行合并为可折叠条

原界面是两行常驻选项，占用首屏空间。v2.1 改为一个 `玩法 · 出行` 折叠条：

- 默认展开，显示玩法、出行、当前摘要和“按当前选择规划”。
- 页面打开后 **7 秒无操作自动收起**，只保留一行摘要，例如 `自动 · 一人（女）`。
- 点击折叠条重新展开；点击选项或“按当前选择规划”会把自动收起计时重置为 **10 秒**。
- 收起时仍保留当前选择，摘要不会丢；再次点开可以继续改。
- 玩法/出行的“自动”仍然保留：问题里出现“一个人女/两个男/三人以上”等词时，摘要会同步显示识别到的人群。

实现位置：`android/assets/index.html`

- 新增 `.prefs-head / .prefs-body` 与 `.selectors.open` 过渡。
- 新增 `paintPrefs / schedulePrefs / setPrefs / initPrefs`。
- 收起状态只隐藏选项，不隐藏当前摘要与规划入口的语义。

### 2. 资料来源只给官网网址

原来 `.official` 块会显示最多 4 行官网韩文原文，并带“官网原文（韩文）/抓取时间”。v2.1 改成：

```text
官网核对
https://www.saha.go.kr/tour/contents.do?mId=0101010000 ↗
```

- 不再调用 `C.fetchOfficial()` 抓正文，也不渲染 `note.lines`。
- 只保留可点击官网 URL；没有官网地址的景点不显示该块。
- 直接回答、重绘历史消息、路线回答统一走 `fillOfficial(..., url)`，不会再出现“官网没取到内容”的原文块。

### 3. 按出行组合给差异化推荐

新增 6 类组合，全部可在“出行”里选择：

| 组合 | 默认 3 个点 | 推荐逻辑 |
|---|---|---|
| 一人（男） | 甘川文化村、海东龙宫寺、太宗台 | 巷子/海岸线，步行节奏可以紧一点 |
| 一人（女） | 甘川文化村、白浅滩文化村、广安里海水浴场 | 彩色巷子、咖啡店、日落拍照，减少台阶和长距离 |
| 两人（男女） | 广安里、甘川、松岛 | 桥灯、咖啡街、缆车，兼顾拍照和省力 |
| 两人（男男） | 太宗台、札嘎其市场、海云台 | 悬崖步道、海鲜市场、海滩，节奏直接 |
| 两人（女女） | 白浅滩、广安里、甘川 | 海景巷子、咖啡店、日落，拍照优先 |
| 三人及以上 | 海云台、松岛、札嘎其 | 集合方便、空间开阔、多人吃饭好安排 |

代码位置：`android/assets/cloud.js`

- 新增 `GROUP_PICKS / GROUP_WHY / groupOf / groupLabel / groupRecommend`。
- 问题里出现“一个人男性/女性、两个人男女/男男/女女、三个人以上”时自动识别，不要求用户先点选项。
- 如果问题里列了 2–3 个具体景点，按这些景点给组合理由；如果没有列，按组合默认点位推荐。
- 选择“玩法”时，先保证所选玩法有 2 个点，再用该组合默认点补第 3 个；例如“艺术村落 + 一人男”得到甘川、南浦洞 BIFF、海东龙宫寺。
- 下雨/室内问题会切换到札嘎其、西面、龙头山，不让组合偏好压过现场条件。

`android/assets/planner.js`

- `partyOf()` 不再把 `solo_male/solo_female/two_mf/two_mm/two_ff` 粗暴合并成 `solo/two`，保留完整组合。
- 新增 `PARTY_CATS`：按组合给类别加权（例如一人女偏艺术村落/海岸，二人男偏海岸/渔港）。
- `partyWord()` 输出“一个人（男）/一个人（女）/两人（男男）/两人（女女）/三人以上”，行程条件行能看出差异。

### 4. 动态联动

- `ask()` 开头识别问题中的组合，写入当前状态并刷新摘要；紧接着点“按当前选择规划”会沿用这句话的组合。
- `answerWithIntent()` 的 `recommend / nearby / general / route` 分支都带上组合与所选玩法。
- 问题里没有组合词时，沿用上一次识别到的组合；点“自动”会清空。
- 云端意图仍保持 6 类：`recommend | route | spot | general | nearby | unknown`。

## 二、验证结果

### 折叠条

```text
PREFS_INIT          selectors open | 自动 · 自动
PREFS_AFTER_IDLE    selectors | 展开
PREFS_AFTER_CLICK   selectors open | 收起
```

- 7.8 秒无操作后确实收起；点击后重新展开。

### 六类组合识别

```text
一个人，男性 → solo_male
一个人，女性 → solo_female
两个人，男女 → two_mf
两个男生 → two_mm
两个女生 → two_ff
三个人以上 → group_3plus
```

### 推荐结果

```text
solo_male   甘川文化村 / 海东龙宫寺 / 太宗台
solo_female 甘川文化村 / 白浅滩文化村 / 广安里海水浴场
two_mf      广安里海水浴场 / 甘川文化村 / 松岛海水浴场
two_mm      太宗台 / 札嘎其市场 / 海云台海水浴场
two_ff      白浅滩文化村 / 广安里海水浴场 / 甘川文化村
group_3plus 海云台海水浴场 / 松岛海水浴场 / 札嘎其市场
```

### 玩法 + 出行组合

```text
solo_male + 01_艺术村落_文化街区
→ 甘川文化村 / 南浦洞BIFF广场 / 海东龙宫寺
```

### 官网块

```text
官网核对
https://www.saha.go.kr/tour/contents.do?mId=0101010000 ↗
```

- 不再出现韩文原文和抓取时间。
- 云端库在线模式验证为 18 个点，`mergeSnapshotSpots()` 仍保留，防止 raw 缓存回退到 8 个点。

## 三、构建与产物

| 项目 | 值 |
|---|---|
| APK | `Busan/dist/Busan旅行助手.apk` |
| APK 体积 | **263,580 B（257.4 KB）** |
| APK SHA-256 | `234E5AEBE32E260736FE14F81DE96166C1CD38EA94518B4CD2AE1B342EB29B6E` |
| APK 版本 | versionCode **14** / versionName **2.1** |
| 原生库 | `lib=[]`，无端侧模型 |
| zip | `Busan/dist/Busan_Tour_App.zip` |
| zip 体积 | **2,681,167 B** |
| zip SHA-256 | `B58EE903270976D773CE990AE937A814C189EF39E3AF230F8D2F8A5E9F1B364B` |
| 包名 | `com.busan.tour` |
| 签名证书 SHA-256 | `9d91ed6b8ffeec5eaf5b597ee19f56bfda6f8663d94ec726390a552224d33356` |
| 云端 UA | `BusanTour/2.1 (Android)` |

## 四、已知限制

1. 组合推荐是“旅行偏好启发式”，不是对性别或人数做绝对判断；用户可以用“少走/亲子/下雨/拍照”等条件覆盖默认排序。
2. 官网只显示网址，不再抓正文；官网正文是否可访问、是否有韩文更新，以用户点开后的页面为准。
3. 新景点仍使用近似坐标算直线距离；道路级路线、公交线路号、班次、末班时间由 NAVER 实时结果决定，App 只生成 `nmap://` 深链。
4. 当前 `adb devices` 为空，没有真机和模拟器；折叠动画、系统定位权限弹窗、授权回传、NAVER 拉起仍需真机确认。
5. 折叠条 7 秒自动收起是固定节奏；如果用户正在阅读长选项，可点条重新展开，不会丢失已选状态。
6. 云端 raw 的 `main` 分支可能还有 CDN 缓存；APK 启动会用包内 18 个点补齐，不保证远端 raw 立即返回 18 个。

## 五、验证清单

- [x] `node --check android/assets/cloud.js`
- [x] `node --check android/assets/planner.js`
- [x] 无头 Chrome：折叠条默认展开，7.8 秒后收起，点击后展开
- [x] 无头 Chrome：六类组合识别全部正确
- [x] 无头 Chrome：六类组合各返回 3 个不同点位
- [x] 无头 Chrome：玩法 + 组合交叉返回所选玩法点位
- [x] 无头 Chrome：官网块只显示 URL，不显示韩文原文
- [x] 无头 Chrome：在线模式 18 个点
- [x] APK 内 `lib=[]`，`versionCode=14 / versionName=2.1`
- [x] APK 内含 `groupRecommend` 与 `mergeSnapshotSpots`
- [ ] 真机验证（当前无设备）
- [ ] NAVER App 深链真机拉起（当前无设备）
