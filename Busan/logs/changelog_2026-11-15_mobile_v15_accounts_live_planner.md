# 手机版 v1.5：账户化、实时定位、核心词推演与大模型通道

- 日期：2026-11-15
- 版本：Android `versionCode 6` / `versionName 1.5`（上一版 5 / 1.4）
- 仓库：`https://github.com/luohaisheng814/AI_Project_2026_2.git`（分支 `main`）
- 本轮代码提交：`9118ad0`（`feat(mobile): v1.5 账户化与现场推演 —— 本机登录/注册与30天会话、网络波动提示、实时定位距离、核心词库扩容与行程推演、可选LLM通道，重打APK与分发包`）
- 安装包：`Busan/dist/Busan旅行助手.apk`（218,524 B）
- 分发包：`Busan/dist/Busan_Tour_App.zip`（2,581,997 B，已换入 v1.5 APK、`mobile/assets/` 与新版 `spots.json`）
- 签名：SHA-256 `9d91ed6b8ffeec5eaf5b597ee19f56bfda6f8663d94ec726390a552224d33356`；SHA-1 `0a5cecc7cbc9c70ca60c6b16b918017276cf97de`

## 一、这轮把手机版从“查询工具”推到“可账户化的现场助手”

v1.4 已经把联网 / 离线判定收回手机侧：`netAllowed()` 同时要求 `NET_CAPABILITY_INTERNET` 与 `NET_CAPABILITY_VALIDATED`，云端库直读 GitHub raw，取不到就落包内快照。v1.5 不改这条分界，补的是“人”和“现场”：

1. **账户与状态**：本机账户、登录 / 注册、手动退出、30 天不活跃自动退出；登录后按用户保存玩法、出行、偏好与上一次推演；未登录启动即 `resetGuest()`，每次都是全新界面。
2. **网络波动提示**：`ConnectivityManager.NetworkCallback` 监听 `INTERNET` 能力，250 ms 防抖后回调网页 `__busanNetChanged(bool)`；顶部状态条 + 3.8 s 浮层提示，恢复后自动 `reloadCloud()`。
3. **实时定位**：GPS + NETWORK_PROVIDER，3 s / 12 m 更新；定位条显示“距某景点 x.x km · 实时 · ±n m”，并按最近景点自动切换目标；`onPause` 停、`onResume` 若用户仍开启则重启。
4. **说出想法 → 核心词 → 自主推演**：`planner.js` 先抽时间 / 节奏 / 预算 / 同行 / 行动限制 / 兴趣，再用 `core / vibes / plan` 元数据打分、按距离排序、按时间预算裁行程，输出“分析 + 行程 + 提示 + 来源 + 追问”。
5. **核心词库扩容**：新增 `core_keywords.json`，8 个景点每个 20–40 个中 / 韩 / 英核心词，附 `vibes`、时长、最佳时段、步行强度、拍照 / 亲子分、室内标记、规划备注；`cloud_build.py` 合并进 `spots.json`，schema 由 2 升到 3。
6. **大模型通道（可选）**：账户面板内填 OpenAI 兼容 `endpoint / model / key`，Key 只存原生 `SharedPreferences`，不进入网页；有配置且在线时，模型只在本地候选池（前 8 个景点）内重排与写理由，严格 JSON，失败 / 超预算 / 名字不匹配立即回退本地结果。

## 二、账户与会话口径

- 用户名 2–24 字符，密码至少 6 位；密码用 `PBKDF2WithHmacSHA1` 100,000 轮、256-bit、随机 16 B salt，不存明文。
- 用户表写 `SharedPreferences("busan_auth").users`；会话 token 为 UUID，存 `session_user` / `session_token`。
- `SESSION_TTL_MS = 30 天`：`authCurrent` 每次校验 `lastActive`，超时清 session 并返回 `expired`；前台 `visibilitychange` 也会重新校验。
- 手动退出只清 session，不删用户；卸载重装才清空账户（应用私有目录）。
- 按用户状态写 `state_<sha256(username)>`，上限 200 KB；未登录不读写任何账户状态。
- 网页环境的 `localStorage` 账户只用于浏览器预览，弱哈希、非安全实现；Android 原生走 PBKDF2，两者不要混用。

## 三、核心词与推演规则

`core_keywords.json` 的 8 个景点：甘川文化村、多大浦梦之夕阳喷泉、多大浦海水浴场、没云台、乙淑岛候鸟公园、峨嵋山观景台、洛东江东口生态中心、长林浦口。每个景点的 `core` 覆盖中 / 韩 / 英叫法、别名、玩法词（拍照、日落、候鸟、彩色房子、阶梯、喷泉等），`plan` 给时长区间与步行强度。

`planner.js` 的可见规则：

- 时间词：半小时 / 半天 / 一天 / N 小时 / 上午 / 中午 / 下午 / 傍晚 / 日落 / 晚上；未写时间默认半天（240 min）。
- 节奏：`轻松` → relaxed，时长取区间 25% 偏上；`紧凑` → packed，取区间下限；其余 balanced 取中值。
- 行动限制：`少走路 / 老人 / 轮椅 / 婴儿车` 会降低 `walk_level` 高的点，并给 ≤2 的点加分。
- 时段：上午型点加分；傍晚型点加分。若当前已过 15:00 且用户没写“傍晚”，白天型行程从**次日 09:30**起算，并在提示里写明；半日行程会排除 `best_time=evening` 的点，避免把喷泉排到正午。
- 距离：有实时定位时按 `haversine` 算起点到首站、站间距离，并做最近邻排序；没有定位时按景点相对位置排序。
- 标题：按入选点的类别组合，例如“小众渔港·文艺拍照 + 湿地生态·自然观景 · 半天”，不再用单点类别概括整条线。

大模型只在本地结果之后增强，不替换事实源：候选池固定为本地打分前 8 个景点；模型返回的 stop 必须精确匹配候选名，总时长不得超过预算 +60 min；任何一项不满足就整段丢弃，保留本地结果。

## 四、UI 这轮改了什么

- 顶部：标题行不再塞三语按钮；第二行放“中文 / 한국어 / English / 登录（用户名）”，窄屏下四个按钮同排不挤出屏幕。
- 账户弹层：登录 / 注册两个 tab；注册有显示名、密码、确认密码；账户面板含节奏 / 预算 / 同行行动 / 兴趣 / 备注，支持保存偏好、配置大模型、测试连接、退出登录。
- 联网条：状态点 + 文案 + “重试”；网络变化时弹 3.8 s 浮层，文案区分“已恢复联网，正在切回云端库”和“当前未联网，已使用包内数据”。
- 实时定位条：默认“实时定位未开启 · 开启后显示到景点距离”；开启后显示“距某景点 x.x km · 实时 · ±n m”，右侧按钮变“停止”。
- 规划条：“按当前选择规划” + 说明“结合账户偏好与实时位置”；自由输入命中“想看 / 想拍 / 半天 / 傍晚 / 路线 / 安排”等会进入推演，不再误判为普通景点查询。
- 气泡 markdown：支持 `###` / `**` / `---` / 任意缩进的 `- ` 列表，并剥掉数据里已有的 `•`，避免出现“• •”双点。
- 未登录欢迎语保留“登录后可保存玩法、偏好与上次推演”；登录后首条变成“欢迎回来，用户名。上次的条件我已经记下，可以直接接着规划”。

## 五、本轮实测

模拟器为雷电 LDPlayer14 index 0，物理 1920×1080，切竖屏后截图 1080×1920；APK 安装命令 `adb -s emulator-5554 install -r --no-incremental` 返回 `Success`。

| 截图 | 场景 | 结论 |
|---|---|---|
| `apk_build/apk52.png` | v1.5 首启（竖屏） | 标题、三语 + 登录、玩法 / 出行、规划条、定位条、欢迎气泡、底栏完整；无右侧裁切 |
| `apk_build/apk53.png` | 点“登录” | 登录 / 注册弹层从底部升起，用户名、密码、登录、游客入口可见 |
| `apk_build/apk55.png` | 填写并注册 `demo_user` | 注册成功，顶部按钮变 `demo_user`，提示“已登录 / 之后的玩法、偏好与推演会保存在这台手机上” |
| `apk_build/apk56.png` | 点“半天想拍照，少走路，帮我安排” | 进入本地推演：核心词“拍照、半天、少走路”，条件“半天·轻松·正常·一人·少走路”，行程 09:30 长林浦口 + 10:38 洛东江东口生态中心，来源“云端库 2026-11-08 · 核心词库 · 景点坐标” |
| `apk_build/apk57.png` | 点“实时” | 定位条变“距长林浦口 3.1 km · 实时 · ±0 m”，按钮变“停止”，原生定位回调打通 |
| `apk_build/apk58.png` | 强制停止后重开 / 覆盖安装 | 仍是 `demo_user`，上次推演自动重绘；账户状态跨进程、跨覆盖安装保留 |
| `apk_build/v15_fullwidth.png` | 浏览器 500×900 首屏 | 完整版式基线，用于核对 390 / 540 宽度下的压缩表现 |
| `apk_build/v15_plan4.png` | 浏览器半日推演 | 核心词补齐后输出长林浦口 + 洛东江，标题按两类组合 |
| `apk_build/v15_evening2.png` | 浏览器“傍晚想看海边日落” | 16:30 多大浦海水浴场 → 18:21 喷泉 → 19:23 峨嵋山，按日落 / 夜间时段排 |
| `apk_build/v15_auth_register2.png` | 浏览器注册页 | 登录 / 注册 tab、显示名、密码、确认密码、游客入口完整 |
| `apk_build/v15_auth_flow.png` | 浏览器注册后账户面板 | 偏好、兴趣 chip、大模型设置、退出登录全部可见 |
| `apk_build/v15_auth_reload.png` | 浏览器复用配置重开 | 仍显示用户名，验证浏览器演示层的会话保留 |

命令级验证：

- `node --check` 通过：`planner.js`、`session.js`、`cloud.js`、`live.js`、`app.js`、`data.js`。
- `python cloud_build.py` 重生成：`spots.json` 63,028 B，8 个景点，schema 3；`assets/cloud_snapshot.json` / `.js` 同步。
- `python apk_build/build_apk.py` 编译 + 签名成功；APK 内含 `index.html`、`cloud.js`、`live.js`、`session.js`、`planner.js`、两份 snapshot。
- 云端旧库兼容：联网读到 schema 2 的 raw 时，`mergeLocalLexicon()` 会用包内词库补齐 `core / vibes / plan` 与 `lexicon`，避免核心词和时长退回默认值。

## 六、已知限制（如实记录）

1. **30 天自动退出分支没有实跑**：代码里 `SESSION_TTL_MS` 与 `authCurrent` 的 `expired` 分支已写，但没有把模拟器时间拨 30 天做端到端验证；目前只验证了“手动退出”与“跨进程 / 覆盖安装保留”。
2. **网络波动浮层没有截到图**：执行 `svc wifi disable` / `svc data disable` 后 adb 连接掉线，模拟器至今 `offline`，未能抓取断网 / 恢复的 toast；回调与防抖逻辑只做了代码走查。飞行模式在雷电上会直接切断 adb，这条分支以后应换真机或模拟器网络限速工具验证。
3. **大模型没有真实 Key**：只验证了“未配置时账户面板显示未配置、推演走本地规则”；没有用真实 OpenAI 兼容服务跑通 200 / 401 / 超时三种响应。Key 的存储与读取路径已在原生壳里实现，但未做真机抓包确认。
4. **账户是本机账户**：没有云端用户库，换手机 / 卸载重装不迁移；同一台手机覆盖安装保留。用户名大小写不敏感（统一转小写做 key）。
5. **定位精度依赖设备**：模拟器注入的是固定坐标，3.1 km 只说明链路通，不代表真实步行距离；定位不等于实时营业、拥挤、天气。
6. **官网抓取仍是启发式**：`id="conts"` + 前 12 行；官网改版可能抓不到。推演里的时长是区间估算，实际交通仍以 NAVER 地图为准。
7. **大模型只重排候选，不写事实**：距离、票价、营业时间、时长仍来自景点库；模型返回超预算 / 名字不匹配会整段回退。模型不可用时用户看不到“模型失败”的明确提示，只会看到本地结果。
8. **多语言覆盖不均**：中文核心词最全，韩文 / 英文核心词主要覆盖景点名与高频玩法；韩文语法助词、英文复数变体还没有做词形还原。
9. **APK 只有 213.4 KB**：因为包内只带 `cloud_snapshot` 与核心词库，不带完整官网正文；离线时回答深度仍低于联网。
10. **桌面 tkinter 端本轮未改**：v1.5 只动 Android 壳、网页资源、云端库与构建脚本。

## 七、验证清单

- [x] `cloud_build.py` 合并 `core_keywords.json`，schema 2 → 3，8 个景点 `core / vibes / plan` 全部落库。
- [x] `spots.json` 63,028 B；`cloud_snapshot.json` / `.js` 与之一致。
- [x] `node --check` 六个前端脚本通过。
- [x] APK 编译、zipalign、apksigner 签名；versionCode 6 / versionName 1.5；签名 SHA-256 未变。
- [x] 模拟器安装、启动、竖屏首屏截图（`apk52`）。
- [x] 原生登录弹层（`apk53`）、注册成功（`apk55`）、顶部用户名与已登录 toast。
- [x] 原生自由文本推演（`apk56`）：核心词、条件、行程、来源完整。
- [x] 原生实时定位（`apk57`）：`__busanLocUpdate` → 距离条 3.1 km / ±0 m。
- [x] 账户状态跨 `force-stop` 与覆盖安装保留（`apk58`）。
- [x] 浏览器注册 → 账户面板 → 重开保留会话（`v15_auth_flow` / `v15_auth_reload`）。
- [x] 浏览器傍晚日落推演按时段排序（`v15_evening2`）。
- [x] 云端旧 schema 2 自动补齐（`mergeLocalLexicon`），浏览器实测核心词不再丢。
- [x] dist zip 重建，含 v1.5 APK、`mobile/assets/`、新版 `spots.json`。
- [ ] 30 天 TTL 端到端（未做，见限制 1）。
- [ ] 断网 / 恢复 toast 截图（未做，见限制 2）。
- [ ] LLM 真实 200 / 401 / 超时（未做，见限制 3）。
- [ ] 两台真人手机对比（未做）。
- [ ] 卸载重装后账户清空（逻辑上会清空，未截图）。

## 八、本轮改动文件

原生与网页：

- `Busan/android/AndroidManifest.xml`（versionCode 5 → 6，versionName 1.4 → 1.5）
- `Busan/android/java/com/busan/tour/MainActivity.java`（账户 / 会话 / 用户状态 / 网络回调 / 实时定位 / LLM 通道）
- `Busan/android/assets/index.html`（账户按钮、规划条、定位条、网络提示、账户弹层、markdown 列表修复）
- `Busan/android/assets/session.js`（新增：账户 UI、偏好、会话、LLM 设置、toast；`BusanAuth` 别名）
- `Busan/android/assets/live.js`（新增：实时定位、距离、目标切换）
- `Busan/android/assets/planner.js`（新增：核心词、约束、打分、排序、行程、LLM 重排）
- `Busan/android/assets/cloud.js`（新增 `mergeLocalLexicon`，旧 schema 自动补齐）
- `Busan/android/assets/cloud_snapshot.json` / `.js`（schema 3 重生成）

数据与构建：

- `Busan/mobile/cloud/core_keywords.json`（新增：8 景点核心词 / 玩法 / 规划元数据）
- `Busan/mobile/cloud/spots.json`（63,028 B，schema 3）
- `Busan/cloud_build.py`（合并词库、schema 3、更新时间 2026-11-15）
- `Busan/apk_build/build_apk.py`（assets 必检加入 `live.js` / `session.js` / `planner.js`）
- `Busan/apk_build/make_dist_zip.py`（新增：重建 dist zip）
- `Busan/dist/Busan旅行助手.apk`（218,524 B，v1.5）
- `Busan/dist/Busan_Tour_App.zip`（2,581,997 B）

## 九、下一步建议

1. 用真机或可限速的模拟器补“断网 → 恢复”两种 toast 截图，并把 `__busanNetChanged` 的防抖时间做成可配置。
2. 把 30 天 TTL 改成可注入的测试时钟（debug 构建），跑一次 `expired` 端到端。
3. 给大模型返回加“模型未启用 / 已回退”的轻提示，避免用户误以为本地结果就是模型结果。
4. 账户若要跨设备，下一版再引入云端用户库；当前本机账户先保证隐私与离线可用。
5. 韩文 / 英文核心词补词形变体（助词、复数、常见拼写），并把 `core_keywords.json` 做成可增量合并的独立数据源。
