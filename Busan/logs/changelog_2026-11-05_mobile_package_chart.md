# Changelog — 2026-11-05 手机版运行逻辑图 + 最新安装包（Busan_Tour_App.zip 重打并实测）

> 承接同日「手机版登录 / 联网双源 / 精简回答 / NAVER 深链」那一轮。本轮用户要三件：**手机版专属的运行逻辑图**、**推到 GitHub**、**手机版最新安装包**，另加一份日志。

## 本次目标

| 需求 | 落点 |
|------|------|
| 手机版程序运行的逻辑图表 | 新建 `Busan/docs/mobile_run_logic.html` + `.png` |
| 上传到 `https://github.com/luohaisheng814/AI_Project_2026_2.git` | 本轮提交推送 `main` |
| 生成本轮日志 | 本文件 |
| 手机版最新安装包 | `Busan/dist/Busan_Tour_App.zip` 重打（旧包是 11-01 的 83 860 字节） |

## 一、旧安装包为什么必须重打

`dist/Busan_Tour_App.zip` 停在 2026-11-01 14:23，83 860 字节。本轮手机版已经全量重写，旧包的三个硬伤：

1. **清单缺模块**：`build_package.py` 的 `REQUIRED_MODULES` 只有 9 个，缺 `official_sites.py`（本轮 `rag_core` 的联网路径已 `import` 它）与 `db_config.py`（`mobile_app.py` 的登录/日志要用）。按旧清单打出来的包，**服务一启动就 ImportError**。
2. **前端是旧版**：旧包里的 `mobile/index.html` 没有登录按钮、没有三语切换的新文案、没有 `stripTail` 去重，也没有 NAVER 按钮。
3. **说明文档过期**：README 还写着「纯网页应用不需要在手机上单独安装 APK」「按 /6000 端口 → 8000」，一个字没提登录、联网、官网来源、NAVER 深链。

### 改法

| 文件 | 改动 |
|------|------|
| `Busan/build_package.py` | `REQUIRED_MODULES` 补 `official_sites.py`、`db_config.py`（现 11 个）；`EXCLUDE_FILES` 追加 `run_logic.*` 与 `mobile_run_logic.*`，避免把 300 KB+ 的说明图打进应用包；README.txt 整体重写为九节（包内容 / 启动 / 账号与联网 / 放到手机 / 附近景点与地图 App / 玩法规则 / 语言规则 / 回答形态 / 常见问题） |

README 现在明确写清了三件此前没有的事：

- 首次启动自动建库并生成默认管理员 `admin / admin`；把桌面版/网页版正在用的 `busan_travel.db` 放到包目录即可延续原有账号；
- 未登录只查本地库，登录后同时抓景点官网 + 本地库并由大模型成稿；
- 装了 NAVER 地图时，卡片上的 `nmap://route/public` / `nmap://place` 可直接唤起 App 精准定位与导航；局域网 HTTP 拿不到坐标时用 `?lat=&lng=` 直接预览。

### 重打结果

```
打包完成：D:\AI_Project_2026_2\Busan\dist\Busan_Tour_App.zip
  包含 35 个运行/数据文件 + 4 个启动说明文件
  压缩包大小：99.2 KB（101 585 字节，2026-11-05 20:25）
```

包内 Python 与前端文件已逐个核对存在：`mobile_app.py / rag_core.py / official_sites.py / recommend.py / intent_parser.py / lang_detect.py / config.py / i18n.py / core_api.py / web_lookup.py / db_config.py / mobile/index.html`，另有 `docs/`、`activity_classified/`、`requirements.txt`、`start_windows.bat`、`start.sh`、`README.txt`。

## 二、新安装包实测（不是「打出来就算」）

把 zip 解压到 `%TEMP%\busan_pkg_test\Busan_Tour_App`（一个干净的、没有 `.env`、没有 `busan_travel.db` 的目录），用它自带的代码起服务：

```
本机访问：   http://127.0.0.1:8021/
用户数据库： ...\busan_pkg_test\Busan_Tour_App\busan_travel.db（与桌面版 / 网页版共用）
登录后开启联网检索（景点官网 + 在线 AI）；未登录为纯本地库直出。
```

端到端结果（`%TEMP%\busan_pkg_test.py`）：

| 检查 | 结果 |
|------|------|
| `GET /api/meta` | 200，4 个玩法：艺术村落 / 海岸日落 / 湿地生态 / 小众渔港 |
| `GET /api/me`（未登录） | `logged_in=False, online=False` |
| `POST /api/chat`「甘川文化村」（未登录） | `online=False`、`web_count=0`、`concise=True`、479 字（本地精简模板） |
| `POST /api/login` admin/admin | 200，`role=admin`、`online=True`，下发 Cookie `busan_sid` |
| `GET /api/me`（登录后） | `logged_in=True`、`online=True` |
| `POST /api/chat`「甘川文化村」（登录，韩文按钮） | `online=True`、`web_count=2`、`concise=True`、`spot=甘川文化村`、586 字 |
| `POST /api/nearby` | 200，8 条，首条带 `nmap://route/public?slat=35.0972&…` |

登录后 `web_count=2` 说明**官网抓取这条链路在解压后的干净目录里也是通的**；因为包里按设计排除了 `.env`，没有 LLM 密钥，所以正文是「抓了官网之后由本地成稿」的降级形态（586 字，不是纯资料库原文的 479 字）。

## 三、手机版运行逻辑图

- 与上一张「三端全局图」不同，这张只讲**手机版一条链**：手机浏览器（前端）→ 局域网 Python 服务 → 数据与外部服务（DB / 官网 / LLM / 地图）。
- 五条流程横向铺开，每条按「前端 → 服务端 → 数据/外部」三列对应，箭头标出实际动作：

| FLOW | 前端 | 服务端 | 数据/外部 |
|------|------|--------|-----------|
| 01 打开 | 进首页 / 添加到主屏幕 | `GET /`、`/manifest.json`、`/sw.js`、`/api/meta` | `config.CATEGORIES`、人数枚举 |
| 02 登录 | 点登录弹窗提交 | `db.verify_login` → 建会话 → `Set-Cookie: busan_sid` | `users` 表（与桌面/网页共用，`admin/admin`） |
| 03 提问 | `POST /api/chat` + 结构化渲染 | `rag_core.answer(online=True)`：本地 + `official_sites` → 中文草稿 → 翻译 → 写 `query_logs` | 沙下区官网（`#conts`）、甘川官网、`activity_classified/`、qwen-plus |
| 04 附近景点 | `geolocation`（8s 超时） | 8 点球面距离排序 + 四类链接 | `nmap://place`、`nmap://route/public`、网页地图、Google |
| 05 分发 | 「安装包」/「添加到主屏幕」 | `GET /download/Busan_Tour_App.zip` | 解压即起、首次自动建库 |

- 底部两块如实标注「状态与降级」与「边界」：未登录=纯本地、已登录无密钥=抓官网后本地成稿、定位被拒=提示 + 坐标预览、旧缓存由 SW v4 导航网络优先兜住；边界写明内存会话、局域网 HTTP 定位限制、APK 仍是离线版。

渲染方式（可复用）：

```powershell
& "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --headless=new --disable-gpu --hide-scrollbars `
  --force-device-scale-factor=1 --window-size=1360,1140 `
  --screenshot="D:\AI_Project_2026_2\Busan\docs\mobile_run_logic.png" `
  "file:///D:/AI_Project_2026_2/Busan/docs/mobile_run_logic.html"
```

窗口高度试了三次：1620 底部大片空白 → 1010 把「状态与降级 / 边界」和页脚切掉 → **1140 刚好**。成品 1360×1140、约 301 KB，已逐项看过：五条流程箭头与三列对齐、无文字溢出、无截断。

## 四、验证清单（本轮已执行）

1. `build_package.py` 重打成功，`Get-Item` 复核：101 585 字节 / 2026-11-05 20:25（旧包 83 860 字节 / 11-01）。
2. 用 `System.IO.Compression` 读包内条目，逐条确认 11 个 `.py` + `mobile/index.html` 在内，且不含 `run_logic*`、`.db`、`.env`。
3. 解压到干净临时目录独立启动（8021），7 项 API 检查全部符合预期（见上表）；启动日志里没有 `ImportError`、没有 `ModuleNotFoundError`。
4. 图渲染后用图像工具逐块目检（1360×1140）。
5. `git add` 逐文件（`build_package.py`、`dist/Busan_Tour_App.zip`、`docs/mobile_run_logic.html`、`docs/mobile_run_logic.png`、本日志）→ 提交 → `push origin main` → `git fetch` + `rev-parse` 比对。

## 五、已知限制（如实记录）

1. **包里没有 `.env`**（按设计排除密钥）：别人拿到包后要用大模型，需要自己配 `LLM_API_KEY`（或把 `Busan/.env` 放进包目录），否则只能是「抓官网 + 本地成稿」。
2. **包不带 `busan_travel.db`**：首次启动新建一个只有 `admin/admin` 的库；想延续旧账号得自己拷 db 进去（README 已写）。
3. **登录态在内存**：包里的服务重启即掉登录，这一轮没有改成持久 token。
4. **安卓 APK 仍离线**：本轮交付的「最新安装包」是手机网页版的 `Busan_Tour_App.zip`，APK 二进制未变（无 INTERNET、无登录、无官网、无 NAVER 深链）。
5. **桌面 tkinter 版仍未实跑**：本轮只动了打包脚本和文档图，桌面分支没有新改动。
6. **默认端口 8000**：启动器写死 `python mobile_app.py 8000`，占用时需手动改；本轮测试用的是 8021，仅验证代码不依赖端口。
7. **定位覆盖依赖系统授权**：局域网 HTTP 下多数手机会直接拒绝 `geolocation`，实际体验要么上 HTTPS 隧道，要么用 `?lat=&lng=`。
8. **图是静态说明**：`mobile_run_logic.png` 由 HTML 渲染，不随代码自动更新；改了端点或文案要重跑上面的 Edge 命令。

## 六、下一步建议

1. 给打包脚本加「是否包含 .env / db」的显式参数，避免每次手工拷密钥。
2. 会话持久化（token 落 `sessions` 表），让包重启不掉登录。
3. 若要 APK 具备登录与联网：给壳加 `INTERNET` 权限、允许明文 HTTP 到局域网服务、把 `index.html` 指向服务地址——这是新形态，需要单独一轮。
4. 用 NAVER 地图精校 8 个景点坐标，替换 `SPOTS_GEO` 里的手工值。

## 七、本轮改动文件

| 文件 | 类型 | 说明 |
|------|------|------|
| `Busan/build_package.py` | 修改 | 模块清单补 2 个、排除图文件、README 重写九节 |
| `Busan/dist/Busan_Tour_App.zip` | 重打 | 101 585 字节，含官网模块与新版前端 |
| `Busan/docs/mobile_run_logic.html` | 新增 | 手机版运行逻辑图源文件（五条流程 × 三列） |
| `Busan/docs/mobile_run_logic.png` | 新增 | 成品图 1360×1140 |
| `Busan/logs/changelog_2026-11-05_mobile_package_chart.md` | 新增 | 本文件 |
