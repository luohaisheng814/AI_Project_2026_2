# -*- coding: utf-8 -*-
"""
mobile_app.py —— Busan AI 旅行助手 · 手机版（零依赖，内置 http.server + PWA）

功能：
  GET  /                移动端 H5 页面（聊天 + GPS 定位附近景点）
  GET  /manifest.json   PWA 清单（可"添加到主屏幕"安装到手机）
  GET  /sw.js           Service Worker（离线缓存）
  GET  /icon-192.png    应用图标
  GET  /icon-512.png
  POST /api/chat        问答接口（复用 rag_core.answer）
  POST /api/nearby      GPS 附近景点（浏览器经纬度 -> haversine 距离排序）
  GET  /api/navigate    生成地图导航链接（Naver / Google Maps）

启动：
  python mobile_app.py            # 默认 0.0.0.0:8000
  python mobile_app.py 8080       # 自定义端口
手机与电脑连同一 Wi-Fi，手机浏览器访问 http://<电脑局域网IP>:8000/，
浏览器菜单选"添加到主屏幕"即可像 App 一样使用。
注意：浏览器定位 API 要求 HTTPS 或 localhost；局域网 HTTP 下定位可能被拒，
此时可手动长按地图选点，或用隧道（如 cloudflared）暴露为 HTTPS。
"""
import json
import math
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import quote

import config
import rag_core

config.ensure_runtime()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MOBILE_DIR = os.path.join(BASE_DIR, "mobile")
HTML_FILE = os.path.join(MOBILE_DIR, "index.html")

# 沙下区景点坐标（与 rules.txt 一致，近似坐标）
SPOTS_GEO = [
    {"name": "甘川文化村",       "ko": "감천문화마을",        "lat": 35.0972, "lng": 128.9769, "cat": "01_艺术村落_文化街区"},
    {"name": "多大浦海水浴场",   "ko": "다대포해수욕장",      "lat": 35.0550, "lng": 128.8910, "cat": "02_海岸休闲_日落夜景"},
    {"name": "没云台",           "ko": "몰운대",              "lat": 35.0510, "lng": 128.8820, "cat": "02_海岸休闲_日落夜景"},
    {"name": "梦之夕阳喷泉",     "ko": "꿈의낙조분수",        "lat": 35.0550, "lng": 128.8920, "cat": "02_海岸休闲_日落夜景"},
    {"name": "洛东江河口生态中心","ko": "낙동강하구에코센터",  "lat": 35.1065, "lng": 128.9680, "cat": "03_湿地生态_自然观景"},
    {"name": "乙淑岛候鸟公园",   "ko": "을숙도 철새도래지",    "lat": 35.1060, "lng": 128.9660, "cat": "03_湿地生态_自然观景"},
    {"name": "峨嵋山观景台",     "ko": "아미산전망대",        "lat": 35.0620, "lng": 128.8980, "cat": "03_湿地生态_自然观景"},
    {"name": "长林浦口",         "ko": "장림포구",            "lat": 35.0880, "lng": 128.9450, "cat": "04_小众渔港_文艺拍照"},
]

CAT_LABEL = {
    "01_艺术村落_文化街区": "🎨 艺术村落",
    "02_海岸休闲_日落夜景": "🌅 海岸日落",
    "03_湿地生态_自然观景": "🏞️ 湿地生态",
    "04_小众渔港_文艺拍照": "📸 小众渔港",
}


def haversine_km(lat1, lng1, lat2, lng2):
    """两点间球面距离（公里）。"""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def nearby(lat, lng, limit=8):
    items = []
    for s in SPOTS_GEO:
        d = haversine_km(lat, lng, s["lat"], s["lng"])
        items.append({
            **s,
            "cat_label": CAT_LABEL.get(s["cat"], s["cat"]),
            "distance_km": round(d, 2),
            # 地图导航链接：Naver Map（韩国本地体验最好）+ Google Maps 兜底
            "naver_url": f"nmap://search?query={quote(s['ko'])}&lat={s['lat']}&lng={s['lng']}",
            "google_url": f"https://www.google.com/maps/search/?api=1&query={s['lat']},{s['lng']}",
        })
    items.sort(key=lambda x: x["distance_km"])
    return items[:limit]


# PWA 静态资源（内联，避免多文件依赖）
MANIFEST_JSON = json.dumps({
    "name": "Busan AI 旅行助手",
    "short_name": "Busan Tour",
    "description": "釜山沙下区 AI 旅行助手：问答 + GPS 附近景点",
    "start_url": "/",
    "display": "standalone",
    "orientation": "portrait",
    "background_color": "#0f172a",
    "theme_color": "#0f172a",
    "icons": [
        {"src": "/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
        {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
    ],
}, ensure_ascii=False, indent=2)

SW_JS = """
// Busan Tour service worker: 简单缓存首屏
const CACHE = 'busan-tour-v1';
const ASSETS = ['/', '/manifest.json'];
self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  e.respondWith(
    caches.match(e.request).then(hit => hit || fetch(e.request).then(resp => {
      const copy = resp.clone();
      caches.open(CACHE).then(c => c.put(e.request, copy));
      return resp;
    }).catch(() => caches.match('/')))
  );
});
"""


def make_icon(size):
    """生成一个简易应用图标（蓝色圆角底 + 白色 B 字），返回 PNG bytes。"""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        return None
    img = Image.new("RGBA", (size, size), (15, 23, 42, 255))
    d = ImageDraw.Draw(img)
    # 斜切色块
    d.polygon([(0, size), (size, size * 0.55), (size, size), (0, size)], fill=(14, 165, 233, 255))
    # 字母 B
    try:
        font = ImageFont.truetype("arialbd.ttf", int(size * 0.55))
    except Exception:
        font = ImageFont.load_default()
    try:
        bbox = d.textbbox((0, 0), "B", font=font)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        d.text(((size - w) / 2 - bbox[0], (size - h) / 2 - bbox[1] - size * 0.05), "B",
               fill=(255, 255, 255, 255), font=font)
    except Exception:
        pass
    import io
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json; charset=utf-8", cache=False):
        data = body if isinstance(body, (bytes, bytearray)) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        if cache:
            self.send_header("Cache-Control", "max-age=3600")
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length == 0:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            return {}

    def do_OPTIONS(self):
        self._send(200, "ok")

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            try:
                with open(HTML_FILE, "r", encoding="utf-8") as f:
                    self._send(200, f.read(), "text/html; charset=utf-8")
            except FileNotFoundError:
                self._send(500, "mobile/index.html 缺失", "text/plain; charset=utf-8")
        elif path == "/manifest.json":
            self._send(200, MANIFEST_JSON, "application/manifest+json; charset=utf-8", cache=True)
        elif path == "/sw.js":
            self._send(200, SW_JS, "application/javascript; charset=utf-8", cache=True)
        elif path in ("/icon-192.png", "/icon-512.png"):
            size = 192 if "192" in path else 512
            png = make_icon(size)
            if png:
                self._send(200, png, "image/png", cache=True)
            else:
                self._send(404, "icon unavailable (pip install pillow)", "text/plain; charset=utf-8")
        else:
            self._send(404, "not found", "text/plain; charset=utf-8")

    def do_POST(self):
        if self.path == "/api/chat":
            body = self._read_json()
            q = (body.get("question") or "").strip()
            cat = body.get("category") or ""
            grp = body.get("group_type") or ""
            ui = body.get("ui_lang") or "zh"
            if not q:
                self._send(200, json.dumps({"answer": "", "sources": [], "followups": [], "recognize": ""}, ensure_ascii=False))
                return
            r = rag_core.answer(q, category=cat or None, group_type=grp or None,
                                 lang=None, ui_lang=ui, username="mobile_user")
            self._send(200, json.dumps({
                "answer": r.get("answer", ""),
                "sources": r.get("sources", []),
                "followups": r.get("followups", []),
                "spot": r.get("spot"),
                "field": r.get("field"),
                "lang": r.get("lang"),
                "recognize": r.get("recognize", ""),
                "offline": r.get("offline", True),
            }, ensure_ascii=False))
            return

        if self.path == "/api/nearby":
            body = self._read_json()
            try:
                lat = float(body.get("lat"))
                lng = float(body.get("lng"))
            except (TypeError, ValueError):
                self._send(400, json.dumps({"error": "需提供 lat/lng"}, ensure_ascii=False))
                return
            items = nearby(lat, lng)
            self._send(200, json.dumps({"user_lat": lat, "user_lng": lng, "spots": items}, ensure_ascii=False))
            return

        self._send(404, "not found", "text/plain; charset=utf-8")

    def log_message(self, fmt, *args):
        sys.stdout.write("[mobile] %s\n" % (fmt % args))


def print_lan_ip():
    """尝试打印本机局域网 IP，方便手机访问。"""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    host = "0.0.0.0"
    rag_core.KB.load()
    ip = print_lan_ip()
    print("🚗 Busan 手机版（PWA）已启动：", flush=True)
    print(f"   本机访问：   http://127.0.0.1:{port}/", flush=True)
    print(f"   手机访问：   http://{ip}:{port}/", flush=True)
    print("   浏览器菜单选「添加到主屏幕」即可安装到手机桌面。", flush=True)
    print("   提示：浏览器定位要求 HTTPS 或 localhost；局域网 HTTP 下可用隧道暴露。", flush=True)
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    main()
