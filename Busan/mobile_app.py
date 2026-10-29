# -*- coding: utf-8 -*-
"""
mobile_app.py —— Busan AI 旅行助手 · 手机版（零依赖，内置 http.server）

功能：
  GET  /            移动端 H5 页面（聊天 + GPS 定位附近景点）
  POST /api/chat    问答接口（复用 rag_core.answer）
  POST /api/nearby  GPS 附近景点（浏览器经纬度 -> haversine 距离排序）

启动：
  python mobile_app.py            # 默认 0.0.0.0:8000，手机与电脑同网段即可访问
  python mobile_app.py 8080       # 自定义端口
"""
import json
import math
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import config
import rag_core
import lang_detect as LD

config.ensure_runtime()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_FILE = os.path.join(BASE_DIR, "mobile", "index.html")

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


def haversine_km(lat1, lng1, lat2, lng2):
    """两点间球面距离（公里）。"""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def nearby(lat, lng, limit=5):
    items = []
    for s in SPOTS_GEO:
        d = haversine_km(lat, lng, s["lat"], s["lng"])
        items.append({**s, "distance_km": round(d, 2)})
    items.sort(key=lambda x: x["distance_km"])
    return items[:limit]


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
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
        if self.path in ("/", "/index.html"):
            try:
                with open(HTML_FILE, "r", encoding="utf-8") as f:
                    html = f.read()
                self._send(200, html, "text/html; charset=utf-8")
            except FileNotFoundError:
                self._send(500, "mobile/index.html 缺失", "text/plain; charset=utf-8")
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


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    host = "0.0.0.0"
    rag_core.KB.load()
    print(f"🚗 Busan 手机版已启动： http://{host}:{port}/", flush=True)
    print("   手机与电脑连同一 Wi-Fi，用电脑局域网 IP 访问即可（如 http://192.168.x.x:8000/）")
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    main()
