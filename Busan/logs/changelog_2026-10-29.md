# Changelog — 2026-10-29 手机版 PWA 增强

## 本次目标
完善 `mobile_app.py` 手机版，增强 GPS 能力，做成可"安装到手机桌面"的 PWA，并推送到 GitHub。

## 改动文件
| 文件 | 改动 |
|------|------|
| `Busan/mobile_app.py` | 重写：新增 PWA 路由（manifest.json / sw.js / icon）、地图导航链接、局域网 IP 自动打印、nearby 返回导航 URL 与分类标签 |
| `Busan/mobile/index.html` | 升级：PWA manifest 注入 + Service Worker 注册、「安装 App」按钮（beforeinstallprompt）、GPS 权限错误分级提示、附近景点卡片加 Naver/Google 导航按钮与分类徽章、安全区适配 |
| `Busan/logs/changelog_2026-10-29.md` | 本日志 |

## 新增能力
1. **PWA 可安装**
   - 后端内联提供 `/manifest.json`、`/sw.js`、`/icon-192.png`、`/icon-512.png`（图标用 PIL 现场生成，无二进制依赖）。
   - 前端注册 Service Worker，缓存首屏；监听 `beforeinstallprompt`，用户点「⤓ 安装 App」即可添加到主屏幕，像原生 App 一样全屏启动。
2. **GPS 增强**
   - 保留 `navigator.geolocation.getCurrentPosition` 一次性定位；错误码分级提示（权限拒绝 / 超时 / HTTP 非 HTTPS 限制）。
   - `/api/nearby` 返回每个景点的 `naver_url`（`nmap://` 唤起 Naver Map）与 `google_url`（Google Maps 网页版），卡片直接点按钮跳转导航。
   - 定位成功后状态栏显示当前经纬度。
3. **启动信息**：启动时自动探测局域网 IP（如 `http://192.168.1.104:8000/`），方便手机同 Wi-Fi 访问。

## 使用方式
```
cd Busan
python mobile_app.py          # 默认 8000 端口
# 手机连同一 Wi-Fi，浏览器访问 http://<电脑IP>:8000/
# 浏览器菜单 → 添加到主屏幕 / 点页面上的「安装 App」按钮
```

## 已知限制
- 浏览器定位 API 要求 **HTTPS 或 localhost**；局域网 HTTP 下部分手机浏览器会拒绝定位，此时可：
  - 用隧道（cloudflared / ngrok）暴露为 HTTPS；
  - 或直接点景点卡片上的「Naver 导航」手动选点。
- nmap:// 链接需手机安装 Naver Map App；未安装时回退 Google Maps 网页链接。

## 验证
- `GET /` → 200（10KB HTML）
- `GET /manifest.json` → 200
- `GET /sw.js` → 200
- `GET /icon-192.png` / `icon-512.png` → 200（PIL 生成）
- `POST /api/nearby` → 8 个景点按距离排序，含 naver_url / google_url / cat_label
- `POST /api/chat`（"没云台怎么去"）→ 识别 `语言=中文 · 意图=交通 · 景点=没云台`，回答 931 字
