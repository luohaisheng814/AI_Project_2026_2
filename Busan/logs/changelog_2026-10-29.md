# Busan AI 旅行助手 · 更新日志

## 2026-10-29 手机版 UI + GPS 定位

### 本次新增
- **mobile_app.py**：零依赖手机版 Web 服务（Python 内置 `http.server`，无需 Flask）
  - `GET /`：移动端 H5 页面
  - `POST /api/chat`：问答接口，透传 `rag_core.answer()`，返回回答/来源/追问/识别摘要
  - `POST /api/nearby`：GPS 附近景点，接收经纬度，用 haversine 公式对 8 个沙下区景点排序返回
- **mobile/index.html**：手机端聊天界面
  - 移动端 viewport、触控友好按钮、深蓝渐变顶栏
  - 「📍 定位附近景点」按钮：调用浏览器 `navigator.geolocation`
  - 定位成功后展示附近景点卡片（名称/韩文/距离 km），点卡片直接发起提问
  - 聊天区支持中/韩/英问题，自动展示识别摘要

### 验证
- `/api/nearby` 以甘川文化村坐标(35.0972,128.9769)测试：甘川 0.0km → 洛东江 1.31km → 乙淑岛 1.39km → 长林浦口 3.08km → 峨嵋山 8.18km，排序正确
- `/api/chat` 测试「没云台怎么去」：识别 = 语言中文 · 意图交通 · 景点没云台，正常返回景点内容
- 启动方式：`python mobile_app.py [端口]`，默认 0.0.0.0:8000，手机与电脑同 Wi-Fi 用局域网 IP 访问
- 注意：浏览器 GPS 需 HTTPS 或 localhost 环境；局域网 IP 访问时部分浏览器会拒绝定位，可用 ngrok/内网穿透或在 localhost 下调试

---

## 2026-10-22 知识库补全 + 识别优化（上一轮）

### 核心数据库 docs/rules.txt（43.5KB → 49.1KB）
补全 3 个沙下区景点完整条目：
- 没云台（몰운대）→ 02 海岸休闲类
- 乙淑岛候鸟公园（을숙도）→ 03 湿地生态类
- 梦之夕阳喷泉（꿈의낙조분수）→ 02 海岸休闲类

### classifier.py 四类分类增强
- 修正 rules.txt 路径，新增 `split_blocks()` 按【】块提取嵌套子景点
- 8 个景点分类文件全部落盘（原 3 个空文件填充 675/741/887 字）

### 问答言语识别优化
- `lang_detect.py`：字符占比判定（≥55% 主导），混排不再误判韩文
- `intent_parser.py`：扩充三语意图词，登记新景点别名，新增 `recognize_summary()`
- `rag_core.py` / `chat_widget.py`：状态栏实时展示「语言=中文 · 意图=交通 · 景点=没云台」
