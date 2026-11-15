# v1.7 手机版：离线提示、每问三方案、端侧大模型安装

日期：2026-11-15
版本：versionCode 8 / versionName 1.7
基线：v1.6（提交 `e4a0284`）

## 一、本轮只做三件事

本轮对应附件第一页顶部的三条 app 级要求：

1. **不要常驻“在线/离线”按钮或状态控件，只在离线时提示。**
2. **每个对话主题的答案扩展为 2–3 个，固定给 3 个可选方案。**
3. **用开源免费的大模型来跑问答，并直接内置安装。**

论文评审意见（4 页、4 节、作者块、关键词、与 VisitBusan/Google Maps 对比等）本轮未改论文，只记录为待确认项。

## 二、离线提示

### 改了什么

- 顶部 `#statusbar`、`#netText`、`#retry` 这组常驻状态控件不再渲染；在线时页面没有任何“在线/离线”字样或重试按钮。
- 启动时不再弹“当前已联网”提示。`session.js` 的 `startupNetToast()` 在 `BusanUI.online()` 为真时直接 `return`。
- 只有离线时才出现一次底部提示：
  - 启动即离线：`当前未联网` + “已自动改用包内数据；恢复网络后会自动切回云端库，不需要手动切换。”
  - 使用中掉线：`window.__busanNetChanged(false)` → `showOfflineNotice()`，同一轮只弹一次；恢复在线后清空 `offlineNotified`，下次再掉线才重新提示。
- `index.html` 的 `paintStatus()` 改为空实现，避免启动早期云端库尚未加载完成时误判为离线并重复弹提示。

### 验证

- 无头 Chrome 500×900 首屏截图：不再出现“当前已联网/当前离线”常驻条或重试按钮。
- 离线状态由原生 `ConnectivityManager` 回调和 `BusanUI.online()` 双通道判定；页面不提供手动切换开关。

## 三、每条回答固定 3 个可选方案

### 具体景点问答

`cloud.js` 新增：

- `choiceOf(x, tag, reason)`：把候选景点转成“方案卡”。
- `choicesFor(s, ctx)`：固定输出 3 个方案：
  1. 当前景点：`首选`（经典走法、停留时长、一句话理由）；
  2. 步行强度最低、亲子分最高的另一个点：`省力`；
  3. 不同类别的补充点：`换口味`；
  4. 数据不足时用剩余景点补齐，保证 `slice(0,3)` 一定三条。
- `compose()` 返回 `choices`；`index.html` 的 `paintBubble()` 渲染为 3 个带序号的按钮，按钮 `data-q` 就是下一轮问题，点一下继续追问。

### 行程推演

`planner.js` 新增 `planChoices(list, ctx)`：

- 第一方案来自本次行程的第一个点，标 `首选`；
- 第二方案标 `更省力`；
- 第三方案从全量景点补一个不同主题的点，标 `换主题`；
- `buildLocal()` 与 `fromLlm()` 都返回 `choices`。

### 验证

- `node --check cloud.js / planner.js / session.js / app.js` 全部通过。
- `node apk_build/test_cloud_round.js` 跑 6 个中文场景 + 韩文/英文各 1 个，单链接来源与条件化推荐保持正常。
- 无头 Chrome CDP 冒烟：问“甘川文化村 轮椅 怎么去”，气泡底部出现 `3 个可选方案`，三条分别是甘川文化村（首选）、多大浦梦之夕阳喷泉（省力）、乙淑岛候鸟公园（换口味）。
- 点“按当前选择规划”后，行程气泡底部同样出现三条方案：甘川文化村、长林浦口、多大浦梦之夕阳喷泉。

## 四、端侧开源大模型

### 选型

| 项 | 值 |
|---|---|
| 模型 | Qwen2.5-0.5B-Instruct |
| 量化 | GGUF Q4_K_M |
| 许可证 | Apache-2.0（可免费商用/修改） |
| 文件大小 | 397,808,192 字节（约 379 MiB） |
| 下载地址 | `https://huggingface.co/bartowski/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/Qwen2.5-0.5B-Instruct-Q4_K_M.gguf` |
| 运行时 | llama.cpp（MIT），官方 JNI + 自建 `local_llm.cpp` |
| ABI | arm64-v8a（当前手机主流；x86 模拟器不启用） |
| 上下文 | 2048 token，4 线程 |

选择理由：

- 0.5B 是目前能在手机 CPU 上以可接受速度跑起来、同时保留中文/韩文基本能力的尺寸；
- Q4_K_M 在体积与质量之间平衡，约 379 MiB；
- Apache-2.0 没有商用限制，可直接随 app 分发；
- 不依赖云端 API Key，装好后断网也能问答。

### 安装方式

用户要求“直接内置安装”。本轮实现为 **app 内安装器**，不是把 379 MiB 模型直接塞进 APK：

- APK 仍只有 4.8 MB，避免安装包膨胀到数百 MB、也避免 GitHub 100 MB 单文件限制；
- 首次进入页面，顶部出现一条轻量安装条：
  `离线大模型 · Qwen2.5-0.5B（Apache-2.0）· 379 MB，一次性安装后不用联网也能问答。`
- 点“安装”后由原生 `MainActivity.installLocalModel()` 后台下载到应用私有外部目录
  `getExternalFilesDir("models")/qwen2.5-0.5b-instruct-q4_k_m.gguf`；
- 支持 `.part` 断点续传（HTTP Range，服务器返回 206），进度回调到 `window.__busanModelProgress()`；
- 下载完成校验字节数必须等于 397,808,192，否则不落盘；
- 装好后安装条自动隐藏，`BusanLLM.localReady()` 变真。

### 推理链路

- 新增 `LocalLlm.java`：`System.loadLibrary("busanllm")`，JNI 方法
  `native_init / native_load / native_prepare / native_processSystemPrompt / native_processUserPrompt / native_generateNextToken / native_unload / native_shutdown`。
- 新增 `Busan/android/native/local_llm.cpp`（基于 llama.cpp 官方 Android 示例改造）：
  - 加载 GGUF；
  - 读取模型自带 chat template；
  - system / user 分段编码；
  - 逐 token 生成，UTF-8 校验后回调。
- 新增 `Busan/android/native/logging.h`，把 llama.cpp 日志接到 Android logcat（tag `BusanLLM`）。
- `MainActivity.HostBridge` 暴露三个 JS 方法：
  - `localModelState()`：返回 `{supported, installed, bytes, expected, name, license}`；
  - `installLocalModel(cbId)`：后台下载；
  - `localChat(messagesJson, cbId)`：后台推理，结果回 `window.__busanLocalDone(id, status, text)`。
- `session.js` 的 `BusanLLM.chat()` 改为 **端侧优先**：本地模型已安装就走 `HOST.localChat`，否则才回退到原有的 OpenAI 兼容远程通道。
- `planner.js` 的 `enrichWithLlm()` 不再要求在线：本地模型可用时，离线也会用模型重排候选点与时间；模型输出仍受“只能从候选点里选”约束，距离/票价/营业状态继续取自景点库。

### 原生库打包

`build_apk.py` 新增：

- 检查并打包 6 个 `.so`：
  `libbusanllm.so`、`libllama.so`、`libllama-common.so`、`libggml.so`、`libggml-base.so`、`libggml-cpu.so`；
- 写入 `lib/arm64-v8a/`；
- APK 必须包含 `libbusanllm.so` 与 `libllama.so`；
- `AndroidManifest.xml` 增加 `android:extractNativeLibs="true"`，保证安装时解压原生库，`System.loadLibrary` 能按 SONAME 找到依赖。

`apk_build/build_native.ps1` 固化构建流程：

1. NDK 26.1.10909125；
2. CMake + Ninja；
3. `-DANDROID_ABI=arm64-v8a -DANDROID_PLATFORM=android-23`；
4. 启用 `LLAMA_BUILD_COMMON`；
5. `llvm-strip --strip-unneeded` 剥离符号（未剥离时 145 MB，剥离后约 11 MB）。

`third_party/` 已加入 `.gitignore`，仓库不提交 llama.cpp 源码；脚本首次运行会浅克隆 `https://github.com/ggml-org/llama.cpp`。

## 五、构建与验证清单

### 静态检查

- [x] `node --check cloud.js`
- [x] `node --check session.js`
- [x] `node --check planner.js`
- [x] `node --check app.js`
- [x] `node apk_build/test_cloud_round.js`：6 中文 + 韩文/英文各 1，全部正常
- [x] `javac` 编译 `MainActivity.java` + `LocalLlm.java` 通过
- [x] `llvm-nm -D libbusanllm.so` 确认 8 个 `Java_com_busan_tour_LocalLlm_*` 导出
- [x] `llvm-readelf -d` 确认 `libbusanllm.so` 的 NEEDED 包含 `libllama-common.so`、`libllama.so`、`libggml*.so`

### UI 冒烟

- [x] 500×900 首屏：无在线/离线常驻状态、无重试按钮
- [x] 500×1400 问“甘川文化村 轮椅 怎么去”：3 个方案卡可见，单链接来源仍为 `资料来源 · saha.go.kr ↗`
- [x] 点“按当前选择规划”：行程气泡底部 3 个方案卡可见
- [x] 模拟 `BusanHost.localModelState()` 返回未安装：顶部安装条可见，文案含 379 MB / Apache-2.0 / 安装按钮

### APK

- [x] `versionCode 8 / versionName 1.7`
- [x] `native-code: 'arm64-v8a'`
- [x] 6 个 `.so` 全部进入 `lib/arm64-v8a/`
- [x] `android:extractNativeLibs=true`
- [x] 签名证书 SHA-256：`9d91ed6b8ffeec5eaf5b597ee19f56bfda6f8663d94ec726390a552224d33356`（与 v1.6 相同，可覆盖安装）
- [x] APK 体积 4,945,750 字节
- [x] APK SHA-256：`FB63529BBD1CB59E434E19056CFC583E7B3E535CEDD39FDB1CB294EC3B79F669`
- [x] `Busan_Tour_App.zip` 体积 7,291,524 字节
- [x] ZIP SHA-256：`F4DF5D337820CFC6E2D61FA6F30CE2E3DE266AAF534C014C1CDBED6053E9E97B`

### 未在真机验证

- `adb devices` 为空，本轮没有连接真机或模拟器。
- 因此以下三项是**代码/构建级验证**，不是真机实测：
  1. 379 MB 模型的实际下载速度与断点续传；
  2. 0.5B 模型在目标手机 CPU 上的生成速度；
  3. `libbusanllm.so` 在 Android 13/14 上的实际加载。

## 六、已知限制

1. **模型不随 APK 打包**：APK 4.8 MB，首次需要联网下载 379 MB。若需要“完全离线开箱即用”，可以把 `.gguf` 放进 `assets` 或 `Busan_Tour_App.zip`，但安装包会到约 400 MB，且 GitHub 普通仓库无法直接托管。
2. **只构建 arm64-v8a**：32 位 arm 与 x86 模拟器会显示“不支持”，安装条隐藏，问答回退到规则引擎。
3. **模型质量未实测**：Qwen2.5-0.5B 是 0.5B 级小模型，中文/韩文可用但不如 7B；`planner.js` 仍用严格 JSON 约束 + 候选点白名单，模型输出不合格时自动保留本地推演结果，不会把错误事实写进气泡。
4. **上下文 2048 token**：候选点多、问题长时会截断早期 token；当前只给 6–8 个候选点，实际够用。
5. **首次推理有加载延迟**：GGUF 首次 `mmap` + 初始化约数秒，之后复用；没有做预加载。
6. **没有 GPU/NPU 加速**：纯 CPU（4 线程），生成速度取决于手机；没有做性能基准。
7. **模型下载源为 Hugging Face**：如果目标网络访问不了 `huggingface.co`，需要自建镜像或把模型放到自己的对象存储；当前没有加镜像 fallback。
8. **论文未改**：附件里的蓝色评审意见（4 页、4 节、作者块、关键词、对比对象等）没有落到论文 docx；本轮只改 app。若要把论文同步到 v1.7，需要重写“not a generative model product”这一句与方法段，避免与“接入了 LLM”自相矛盾。

## 七、涉及文件

| 文件 | 变更 |
|---|---|
| `Busan/android/assets/index.html` | 移除常驻状态条；新增 `#modelStrip` 安装条、`paintModelStrip()`、`modelProgress()`、`modelDone()`；渲染 3 个方案卡 |
| `Busan/android/assets/session.js` | 启动提示仅离线；新增 `refreshLocalModelState()`、`installLocalModel()`、`__busanLocalDone`；`BusanLLM` 端侧优先 |
| `Busan/android/assets/cloud.js` | `choiceOf()`、`choicesFor()`、`compose()` 返回 `choices`；`compose()` 函数头修复 |
| `Busan/android/assets/planner.js` | `planChoices()`；本地与 LLM 结果都带 `choices`；离线允许本地模型增强 |
| `Busan/android/java/com/busan/tour/MainActivity.java` | 模型状态/下载/推理桥；`HostBridge` 包装；`extractNativeLibs` 配套 |
| `Busan/android/java/com/busan/tour/LocalLlm.java` | 新增 JNI 包装 |
| `Busan/android/native/local_llm.cpp` | 新增 llama.cpp Android JNI 实现 |
| `Busan/android/native/CMakeLists.txt` | 新增 arm64 构建配置，启用 `LLAMA_BUILD_COMMON` |
| `Busan/android/native/logging.h` | 新增 Android 日志宏 |
| `Busan/android/AndroidManifest.xml` | 版本 1.7 / 8；`extractNativeLibs=true` |
| `Busan/apk_build/build_apk.py` | 打包 6 个 `.so`，加入 `LocalLlm.java` |
| `Busan/apk_build/build_native.ps1` | 新增原生库构建与剥离脚本 |
| `Busan/apk_build/ui_smoke.py` | 新增无头 Chrome CDP 冒烟脚本 |
| `.gitignore` | 忽略 `third_party/`、`build-arm64/`、Chrome 探针目录 |

## 八、产物

- APK：`Busan/dist/Busan旅行助手.apk`（4,945,750 B，v1.7）
- 分发包：`Busan/dist/Busan_Tour_App.zip`（7,291,524 B）
- 截图：
  - `Busan/apk_build/v17_probe_home2.png`（首屏，无在线状态）
  - `Busan/apk_build/v17_probe_choices.png`（3 个方案 + 模型安装条）
  - `Busan/apk_build/v17_probe_plan.png`（行程 3 个方案）
