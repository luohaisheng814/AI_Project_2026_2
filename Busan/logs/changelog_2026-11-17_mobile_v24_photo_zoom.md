# Busan 手机版 v2.4 更新日志

- 日期：2026-11-17
- 版本：`versionCode 17` / `versionName 2.4`
- 包名：`com.busan.tour`
- 基线：v2.3（commit `8d7e195238f109bc0cf3ba75d6632fd893e06f5d`）
- 仓库：<https://github.com/luohaisheng814/AI_Project_2026_2.git>

## 一、本次目标

给景点回答上方的实景图增加“点按放大”能力，让用户能查看更清楚的细节，同时不影响原有聊天、路线、定位和语言切换。

## 二、实现内容

### 2.1 缩略图入口

- 每个 `.photostrip` 缩略图右下角增加圆形 `+` 标识，提示可点开。
- 缩略图 `cursor:zoom-in`，点击整张图打开大图层。
- 通过事件委托绑定 `document`，动态生成的回答（包括云端回填、历史重绘）都能打开，不需要每次重新绑定。

### 2.2 全屏查看层

新增 `#lightbox`，结构：

```html
<div id="lightbox" class="lightbox" hidden>
  <div class="lb-top">1 / 3 <button id="lbClose">×</button></div>
  <div class="lb-stage" id="lbStage">
    <div class="lb-canvas" id="lbCanvas"><img id="lbImg"></div>
    <button id="lbPrev">‹</button><button id="lbNext">›</button>
  </div>
  <div class="lb-bottom"><div id="lbCap"></div><div id="lbHint"></div></div>
</div>
```

能力：

- 打开时显示当前序号 `1 / 3`；
- 全屏黑底，图片按屏幕宽高 `object-fit:contain` 显示；
- 左右按钮切换同一画廊的图片，切换后自动复位缩放；
- 底部显示图片标题、作者和许可，例如 `甘川文化村 · Basile Morin · CC BY-SA 4.0`；
- `body.lb-open` 锁定背景滚动；
- `×`、`Esc` 关闭；桌面端 `←/→` 切换；
- 图片来源仍为 APK 内置的 `assets/photos/*`，离线可用。

### 2.3 缩放与拖动

| 操作 | 行为 |
|---|---|
| 双指捏合 | 以 1×–4× 缩放 |
| 双击 / 双触 | 在 1× 与 2.4× 之间切换，并以点按位置为中心 |
| 放大后单指拖动 | 平移查看局部 |
| 鼠标滚轮 | 桌面端缩放 |
| 缩放边界 | 自动钳制，不会拖出空白；回到 1× 时自动居中 |

实现要点：

- `touch-action:none` + Pointer Events，避免 WebView 把触摸解释成页面滚动；
- `lb-canvas` 整体做 `translate3d(...) scale(...)`，图片本身不变形；
- `pointerdown/move/up/cancel` 统一处理单指拖动与双指缩放；
- 双击使用 320ms / 42px 阈值，避免和拖动冲突；
- 切换图片时 `lbReset()`，不会把上一张的缩放带到下一张。

## 三、测试结果

### 3.1 自动化回归

| 测试 | 命令 | 结果 |
|---|---|---|
| v2.3 引擎回归 | `node apk_build/test_v23.js` | **50 PASS / 0 FAIL** |
| v2.2 引擎回归 | `node apk_build/test_v22.js` | **43 PASS / 0 FAIL** |
| 离线引擎 | `node apk_build/test_engine.js` | 全部断言通过 |
| 云端问答（离线模式） | `node apk_build/test_cloud_round.js` | 6 组问答 + 中/韩/英正常 |
| 作用域/推断 | `.venv\Scripts\python.exe test_scope.py` | exit 0 |
| 语言策略 | `.venv\Scripts\python.exe test_lang_policy.py` | `ALL LANG-POLICY CHECKS PASSED` |
| HTML 内联脚本 | `node --check apk_build/_index_inline.js` | 通过（51,599 B） |
| `cloud.js` / `live.js` / `photos.js` | `node --check` | 全部通过 |

### 3.2 v2.4 大图 UI 探针

脚本：`apk_build/_v24probe.py`（CDP 9227，500×1400，触摸模拟）

| 检查 | 结果 |
|---|---|
| `THUMBS` | `count=3, loaded=true` |
| `OPEN` | `open=true, index=0, count=3, scale=1, imgLoaded=true, counter="1 / 3", bodyLock=true` |
| `OPEN.cap` | `甘川文化村 · Basile Morin · CC BY-SA 4.0` |
| `ZOOM` | `scale=2.4`，`transform="translate3d(-14px, 204.4px, 0px) scale(2.4)"` |
| `NEXT` | `index=1, counter="2 / 3", scale=1, loaded=true` |
| `PINCH` | CDP 双指触摸后 `scale=1.7142857142857142` |
| `PAN` | 放大后单指拖动 `x=60, y=60` |
| `PREV` | 回到 `index=0, counter="1 / 3"` |
| `CLOSE` | `open=false, src=null, bodyLock=false` |

截图：

- `Busan/apk_build/v24_lightbox.png`：点开甘川第 1 张，全屏显示 `1 / 3` + 标题/许可
- `Busan/apk_build/v24_lightbox_zoom.png`：双指/双击放大到 2.4×，可看清屋顶细节

### 3.3 旧功能复测

`apk_build/_v23probe.py` 复跑通过：

- 路线 3 条走法 + 3 张甘川图 + `NAVER 地图` 标题/按钮；
- 景点回答 3 张图；
- 地点卡 `NAVER 导航 / NAVER 地点 / NAVER 网页地图 / Google 地图`；
- 中英文界面切换；
- 18 个景点 / 54 张图。

## 四、构建产物

### 4.1 APK

- 路径：`D:\AI_Project_2026_2\Busan\dist\Busan旅行助手.apk`
- 大小：`10,217,004 B`（约 9.74 MiB）
- SHA-256：`AA73474A0206F14C8305DCAF49C11CB4F7F7FA7D76D9BA0E60B98A18472AB511`
- 版本：`versionCode 17` / `versionName 2.4`
- 包名：`com.busan.tour`
- 签名证书 SHA-256：`9d91ed6b8ffeec5eaf5b597ee19f56bfda6f8663d94ec726390a552224d33356`
- 已校验 APK 内：
  - `assets/photos.js`：存在
  - `assets/photos/`：54 个文件
  - `assets/index.html`：含 `lightbox` 查看层

### 4.2 完整分发包

- 路径：`D:\AI_Project_2026_2\Busan\dist\Busan_Tour_App.zip`
- 大小：`22,509,145 B`（约 21.47 MiB）
- SHA-256：`0F775CE5B374B8175502FBE38B1DBC2B0EF1D0522AF577E3DA67846E70FF633F`
- 已校验 zip 内：
  - `Busan_Tour_App/mobile/index.html`：含 `lightbox` 查看层
  - `Busan_Tour_App/mobile/assets/photos.js`
  - `Busan_Tour_App/mobile/assets/photos/`：54 个文件
  - `Busan_Tour_App/Busan旅行助手.apk`：v2.4 APK

## 五、已知限制

1. **真机未验证**：`adb devices` 为空，没有真机或模拟器。以下只有无头 Chrome 触摸模拟：
   - Android WebView 的 Pointer Events 兼容性；
   - 真机双指捏合的实际手感与边界；
   - 系统返回键在放大层打开时的行为（当前只提供 `×` 与 `Esc`，未拦截 Android 返回键）；
   - APK 安装、覆盖升级、签名校验。
2. **双击/滚轮只做了逻辑验证**：`BusanLightbox.zoom()` 已验证到 2.4×；真机双击与桌面滚轮仍建议手动点一次确认。
3. **只放大当前画廊的图片**：每个回答最多展示 4 张，因此大图切换范围是这 4 张，不是全部 54 张。
4. **图片版权仍是来源标注级**：未逐张做再分发法律审查。
5. **APK 体积维持约 10.2 MB**：54 张图全部内置，未改为按需下载。

## 六、验证清单（可复跑）

- [x] `AndroidManifest.xml` 为 `versionCode=17` / `versionName=2.4`
- [x] `MainActivity` UA 为 `BusanTour/2.4 (Android)`
- [x] 缩略图点击打开 `#lightbox`
- [x] 全屏图 `naturalWidth > 0`
- [x] 序号 `1 / 3`、标题/作者/许可显示
- [x] 放大到 2.4×
- [x] 双指缩放后 `scale=1.714`
- [x] 放大后单指拖动 `x=60,y=60`
- [x] 左右切换并自动复位
- [x] `×` 关闭、背景滚动解锁
- [x] v2.3 / v2.2 / 离线引擎 / 云端问答 / 作用域 / 语言策略全部通过
- [x] APK 含 `assets/photos.js` + 54 张图 + `lightbox`
- [x] ZIP 含 `mobile/assets/photos.js` + 54 张图 + `lightbox`
- [ ] 真机双指/双击/Android 返回键（无设备，未做）
- [ ] 图片再分发许可逐张法律复核（未做）

## 七、提交与推送

- 代码与产物提交：`a84ea420fd6905f0119d847257674a3a757c0759`
- 远端：`https://github.com/luohaisheng814/AI_Project_2026_2.git`，分支 `main`
- 上一版 v2.3：`8d7e195238f109bc0cf3ba75d6632fd893e06f5d`
- 推送结果：`8d7e195..a84ea42  main -> main`
- 对比页：<https://github.com/luohaisheng814/AI_Project_2026_2/compare/8d7e195238f109bc0cf3ba75d6632fd893e06f5d...a84ea420fd6905f0119d847257674a3a757c0759>

> 日志回填提交为紧随其后的 `docs` 提交；代码与产物的正式提交是 `a84ea420fd6905f0119d847257674a3a757c0759`。
