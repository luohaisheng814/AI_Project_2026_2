# Busan 手机版 v1.8 开发日志：取消端侧模型，内置免费云端模型

- **日期**：2026-11-15
- **版本**：versionCode 9 / versionName 1.8
- **范围**：Android 手机版（Busan/android）与打包脚本（Busan/apk_build）
- **本轮结论**：彻底移除 Qwen2.5-0.5B + llama.cpp + 379 MB 应用内下载链路；改为内置 **Kilo Gateway 匿名免费层 + NVIDIA Nemotron 3.5 Super VL**，联网后自动调用，无需用户填 API Key。APK 回到无原生库的 225.4 KB 体量。

## 1. 需求反转

v1.7 的方向是"APK 内置 llama.cpp 运行时 + 应用内下载 Qwen2.5-0.5B GGUF"。本轮用户明确要求：

- 取消本地内置模型；
- 找开源、可免费使用的大模型；
- 直接内置、到云端安装；
- 联网后自动连接云端大模型。

因此 v1.8 不再保留任何端侧推理代码、原生库或模型下载入口，改为在 APK 内预置一个免 Key 的 OpenAI 兼容云端默认配置。

## 2. 免费云端模型选型

目标是"开放权重 / 免费 / 无需用户自己部署 / 最好无需 Key"。实测候选：

| 候选 | 实测结果 | 结论 |
| --- | --- | --- |
| Pollinations AI `text.pollinations.ai` | 返回 **402 Payment Required** / 404 | 不再适合免费使用，排除 |
| OVHcloud AI Endpoints 匿名 `Qwen3.5-9B` | 首次 200，中文问答可用；连续请求很快 **429 Too Many Requests** | 匿名限流明显，仅作备选，不作默认 |
| OpenRouter 免费模型 | `openrouter/free`、`google/gemma-4-26b-a4b-it:free` 等存在，但需要账号/API Key | 不符合"内置即用、无需配置" |
| **Kilo Gateway** | `https://ai-gateway.kilo.ai/api/v1` 匿名可用；文档写明匿名 **200 请求/小时/IP**；`kilo-auto/free` 与显式 `nvidia/nemotron-3.5-super-vl:free` 均返回 200 | **采用** |

最终默认：

- 网关：`https://ai-gateway.kilo.ai/api/v1`
- 完整 chat URL：`https://ai-gateway.kilo.ai/api/v1/chat/completions`
- 默认模型：`nvidia/nemotron-3.5-super-vl:free`
- 备用路由：`kilo-auto/free`
- API Key：不需要；只有用户填了自定义 Key 才加 `Authorization`
- 模型属性：NVIDIA Nemotron 3.5 Super VL，**开放权重 / 免费托管**。本日志没有逐字核验其许可证文件，因此不写成"OSI 开源"。

实测结果：

- 中文事实问答：甘川文化村轮椅问题返回"不方便，因为位于山坡上，多台阶和陡坡"，无额外隐藏推理段。
- 严格 JSON 行程：返回合法 JSON，包含 `title/analysis/stops/tips`；轮椅用户被安排到多大浦梦之夕阳喷泉 + 乙淑岛候鸟公园，避开甘川文化村。
- 返回头 `model=nvidia/nemotron-3.5-super-vl:free`，`finish_reason=stop`。
- 用 JDK `HttpURLConnection` 按 APK 同样的请求体复测：HTTP **200**，`usage.cost=0`，`is_byok=false`，说明匿名免费层可用。

## 3. 代码改动

### 3.1 删除端侧模型链路

| 文件 | 处理 |
| --- | --- |
| `Busan/android/java/com/busan/tour/LocalLlm.java` | 删除 |
| `Busan/android/native/CMakeLists.txt` | 删除 |
| `Busan/android/native/local_llm.cpp` | 删除 |
| `Busan/android/native/logging.h` | 删除 |
| `Busan/apk_build/build_native.ps1` | 删除 |
| `third_party/llama.cpp` | 删除本地源码目录（`third_party/wheels` 的 CMake wheel 保留） |
| `Busan/apk_build/models/qwen2.5-0.5b-instruct-q4_k_m.gguf` | 删除本地 379 MB 缓存 |

`MainActivity.java` 移除 `LOCAL_MODEL_NAME/URL/BYTES`、`modelDownloading`、`supportsArm64`、`modelDir/modelFile/localModelStateJson`、`installLocalModel`、`localChat`、`localDone`、`LocalLlm.release()`，以及 HostBridge 的三个本地包装方法、`File/FileOutputStream` 导入。

`build_apk.py` 移除 native libs 列表、`LocalLlm.java` 编译、`lib/arm64-v8a/*` 写入与 APK 原生库校验。

`AndroidManifest.xml` 移除 `android:extractNativeLibs="true"`，版本改为 versionCode 9 / versionName 1.8。

### 3.2 云端默认配置

`MainActivity.java` 新增：

- `DEFAULT_LLM_ENDPOINT = "https://ai-gateway.kilo.ai/api/v1"`
- `DEFAULT_LLM_MODEL = "nvidia/nemotron-3.5-super-vl:free"`
- `DEFAULT_LLM_PROVIDER = "Kilo Gateway · Free"`
- `llmEndpoint()` / `llmModel()` 在未配置时返回默认值
- `llmBuiltin()` 判断用户是否没有自定义 endpoint/model
- `llmReady()` 不再要求 API Key，只要求 endpoint + model
- `llmConfigJson()` 增加 `provider`、`builtin`
- `llmChat()`：`temperature=0.2`、`max_tokens=900`、`reasoning_effort="none"`（仅内置默认模型）、`User-Agent: BusanTour/1.8 (Android)`、`readTimeout=60s`、仅在用户填了 Key 时加 `Authorization`

**关键修复：** `HostBridge` 之前没有暴露 `getLlmConfig/saveLlmConfig/clearLlmConfig/llmConfigured/llmChat`，网页会走浏览器 `fetch`，在 Android WebView 的 `file://` 页面下容易被 CORS 拦截。v1.8 在 `HostBridge` 内补齐这 5 个 `@JavascriptInterface` 包装方法，云端调用改走 Java `HttpURLConnection`，不再依赖 WebView 的跨域策略。

`session.js` 新增同名默认常量；`loadLlmConfig()` 将空配置归一化为内置默认；`llmChat()` 移除本地分支，直接走 HostBridge 或浏览器 `fetch`；`llmConfigured()` 只判断 endpoint/model，不再判断 Key；新增 `resetLlm()` 与 `BusanLLM.reset`。

`planner.js` 的 `enrichWithLlm()` 改为只要求 `BusanUI.online()`，离线直接保留本地推演结果，不再调用云端。

### 3.3 UI

`index.html`：

- 删除 `#modelStrip`、`#modelBtn`、`paintModelStrip()`、`modelProgress()`、`modelDone()`、启动时 `modelBtn` 绑定，以及 `BusanUI` 的模型导出。
- 账户面板"大模型（可选）"改为"云端大模型"卡片：
  - 标题 `NVIDIA Nemotron 3.5 Super VL`
  - 说明"开放权重 · 免费云端 · 无需 API Key。联网后自动连接，断网自动回退包内规则与快照。"
  - 状态行 `#llmStatus`
  - 按钮"测试云端连接""恢复默认"
  - 可折叠"自定义接口（可选）"：endpoint/model/API Key/保存
- 新增 CSS `.cloudllm`、`.cl-*`、`.llmadv`、`.ai-note`，删除 `.modelstrip/.mstext/.msbar`。
- 具体景点问答在联网时追加一条"云端模型："行动建议；只允许引用原回答、不得新增事实/价格/时间/地点，失败静默保留原回答。该段通过 `addCloudNote()` 追加，不改写原气泡，避免官网核对区被重绘。
- 顶部仍保持"在线不显示状态、只在离线时提示一次"，v1.7 的三方案卡片与单链接来源保持不变。
- 欢迎语从"云端数据库 + 景点官网"改为"云端模型 + 景点官网"（中/韩/英三语）。

### 3.4 本轮涉及文件

| 文件 | 说明 |
| --- | --- |
| `Busan/android/AndroidManifest.xml` | v1.8 / code 9，无 `extractNativeLibs` |
| `Busan/android/java/com/busan/tour/MainActivity.java` | 云端默认配置、移除端侧、补齐 HostBridge |
| `Busan/android/assets/index.html` | 云端卡片、Q&A note、删除模型条 |
| `Busan/android/assets/session.js` | 云端默认/无 Key/重置/桥接 |
| `Busan/android/assets/planner.js` | 仅在线增强 |
| `Busan/android/assets/cloud.js` | 欢迎语改为"云端模型" |
| `Busan/apk_build/build_apk.py` | 移除原生库打包 |
| `Busan/apk_build/ui_smoke.py` | v1.8 截图：首屏、问答、行程、账户面板 |
| `.gitignore` | 保留 `third_party/`、`models/` 本地缓存忽略 |

## 4. 构建结果

| 产物 | 结果 |
| --- | --- |
| APK | `Busan/dist/Busan旅行助手.apk` |
| APK 体积 | **230,812 B（225.4 KB）** |
| APK SHA-256 | `76D563B96CD193E08343017C53AFF25994796B53456BA1C50C63CB986AE93B0B` |
| 版本 | versionCode **9** / versionName **1.8** |
| 包名 | `com.busan.tour` |
| 原生库 | `lib_entries = []`，无 `lib/arm64-v8a` |
| 签名证书 SHA-256 | `9d91ed6b8ffeec5eaf5b597ee19f56bfda6f8663d94ec726390a552224d33356` |
| zip | `Busan/dist/Busan_Tour_App.zip` |
| zip 体积 | **2,600,343 B** |
| zip SHA-256 | `069FD258E70208DE993AD4C2C27A182482B4CB9F65E09E7019A440811BC6CBFB` |

构建链：`aapt2 compile/link` → `javac` → `d8` → `zipalign` → `apksigner`。全部通过；`apksigner verify --print-certs` 证书未变。

## 5. 验证清单

- [x] `node --check`：`cloud.js`、`session.js`、`planner.js`、`app.js` 全部通过。
- [x] `build_apk.py` 构建成功，无 native libs；`aapt dump badging` 显示 `versionCode='9' versionName='1.8'`。
- [x] APK 内 `lib/` 为空；无 `extractNativeLibs`。
- [x] `apksigner verify` 签名通过，证书 SHA-256 与 v1.7 一致。
- [x] `dexdump` 确认 `HostBridge` 暴露 `llmChat` / `getLlmConfig` / `llmConfigured`。
- [x] Java `HttpURLConnection` 按 APK 请求体调用 Kilo：HTTP 200，`usage.cost=0`，`finish_reason=stop`。
- [x] 无头 Chrome 首屏：`#modelStrip=false`；`BusanLLM.config()` 返回内置默认 `endpoint/model/builtin=true`。
- [x] 无头 Chrome 问答：仍渲染 3 个方案（甘川文化村/首选、多大浦梦之夕阳喷泉/省力、乙淑岛候鸟公园/换口味），单来源链接仍为 `saha.go.kr`。
- [x] 无头 Chrome 行程：仍渲染 3 个可选点（甘川文化村/首选、长林浦口/更省力、多大浦梦之夕阳喷泉/换主题）。
- [x] 账户面板截图：云端卡片、状态行、"测试连接""恢复默认"与折叠的自定义接口均正常显示。
- [x] 最终 APK / zip SHA-256 已计算并记录。

截图：

- `Busan/apk_build/v18_probe_home.png`（500×1400，无模型安装条）
- `Busan/apk_build/v18_probe_choices.png`（问答 + 3 方案）
- `Busan/apk_build/v18_probe_plan.png`（行程 + 3 方案）
- `Busan/apk_build/v18_probe_account.png`（账户面板云端卡片）

## 6. 已知限制

1. **未在真机验证**：`adb devices` 为空，没有连接 Android 真机或模拟器。APK 内的 `HttpURLConnection` 调用、TLS 握手、问答气泡追加"云端模型"段、断网回退均未做端到端真机验证。
2. **Kilo 匿名额度**：匿名层为 **200 请求/小时/IP**，不是无限免费；高频使用、多人共享同一出口 IP 或公开分发时可能触发限流。没有做多用户/高并发压测。
3. **不是自建云端**：当前"云端"是 Kilo Gateway 的公共匿名免费层，不是部署在用户自己云服务器上的模型实例。若"到云端安装"指自建实例，本轮未满足，需要在自有服务器上部署 OpenAI 兼容服务后改默认 endpoint。
4. **许可证未逐字核验**：Nemotron 3.5 Super VL 按"开放权重 / 免费托管"描述；没有逐字核对许可证文件，不能据此声称 OSI 开源。
5. **云端回答仍可能不稳定**：Q&A 的"云端模型"段是二次调用，受网关限流、网络抖动、模型输出长度影响；失败时静默保留原回答，不阻断主流程。
6. **官网核对区依赖外网**：`C.fetchOfficial()` 抓取韩国官网仍可能被拦截或超时；失败时显示"官网没取到内容"，不影响包内答案。
7. **浏览器 `file://` 冒烟看不到云端 note**：无头 Chrome 直接打开 `file://` 页面时，跨域请求 `ai-gateway.kilo.ai` 失败，未出现"云端模型"段；Android 走 HostBridge 的 Java 通道，不受该 CORS 限制，但仍需真机确认。
8. **论文未同步**：HCI2026 中英论文的蓝色评审意见（摘要/关键词/章节压缩、与 VisitBusan/Google Maps 对比等）仍未落到 docx；本轮只改 App。
9. **v1.7 的 379 MB 下载链路已删除**：仓库不再提供模型下载；如果用户仍需要完全离线的大模型，需要另行恢复端侧方案。

## 7. 下一步建议

1. 连真机（或模拟器）安装 v1.8，验证：首屏无模型条、账户云端卡片、具体景点问答是否出现"云端模型"段、断网是否保留本地答案。
2. 如"到云端安装"指自建，部署一个 OpenAI 兼容服务（vLLM / Ollama / llama.cpp server），把 `DEFAULT_LLM_ENDPOINT` 指向自己的域名。
3. 如公开分发，给 Kilo 匿名层加一个可选的用户自填 Key 入口（当前已保留"自定义接口"折叠区）。
4. 处理论文蓝色评审意见，补一版与 v1.8 云端架构一致的论文/答辩材料。

## 8. Git 提交与推送

- 仓库：`https://github.com/luohaisheng814/AI_Project_2026_2.git`
- 分支：`main`
- v1.8 代码提交：`5ba36e62ba46fd0cffd236cee0c44e13dc2f04d8`
- 提交信息：`feat(mobile): v1.8 取消端侧模型，内置免费云端 Nemotron`
- 推送结果：`2ce8965..5ba36e6 main -> main`，随后日志补充提交也已推送；v1.8 代码、APK/zip 与日志均已进入 `main`。
- 未提交：`Busan/busan_travel.db`（本轮未改数据库结构，保持本地未暂存状态）；旧截图、`_chk*`、`AI团队作业/*` 等未跟踪文件未批量加入。

