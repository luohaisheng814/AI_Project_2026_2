# -*- coding: utf-8 -*-
"""
mobile_app.py —— Busan AI 旅行助手 · 手机版（内置 http.server，零第三方 Web 框架）

功能：
  GET  /                     移动端 H5 页面（聊天 + GPS 附近景点 + 玩法/人数选择栏 + 登录）
  GET  /manifest.json       PWA 清单（可"添加到主屏幕"安装到手机）
  GET  /sw.js                Service Worker（离线缓存，点开即用）
  GET  /icon-192.png         应用图标
  GET  /icon-512.png
  GET  /api/meta             玩法分类 / 出行人数选项（供手机端选择栏初始化）
  GET  /api/me               当前登录态（用户名 / 角色 / 是否联网）
  GET  /download/Busan_Tour_App.zip   下载完整安装压缩包（含一键启动器与离线资源）
  POST /api/login            登录（与桌面版、网页版共用 busan_travel.db 的 users 表）
  POST /api/register         注册（同一张 users 表，PC 端可看到同一个账号）
  POST /api/logout           退出登录（清会话）
  POST /api/chat             问答接口（登录=联网检索景点官网；未登录=纯本地库直出）
  POST /api/nearby           GPS 附近景点（浏览器经纬度 -> haversine 距离排序 + NAVER 深链）

登录与联网规则（本轮新增）：
  · 登录按钮文案随中文 / 韩文 / 英文界面切换；
  · 用户库与桌面版、网页版互通（同一个 db_config.users / query_logs，不另建表）；
  · 只有登录后才访问景点官方网站（official_sites）并调用在线 AI，未登录时纯本地直出；
  · 每次问答都写入 query_logs（桌面后台可按账号查看）。

启动：
  python mobile_app.py            # 默认 0.0.0.0:8000
  python mobile_app.py 8080       # 自定义端口
手机与电脑连同一 Wi-Fi，手机浏览器访问 http://<电脑局域网IP>:8000/：
  · 可直接在页面问答、定位附近景点；
  · 点「下载安装包」获取 Busan_Tour_App.zip，解压后一键启动即可使用；
  · 浏览器菜单选「添加到主屏幕」可像 App 一样放到桌面离线打开。
注意：浏览器定位 API 要求 HTTPS 或 localhost；局域网 HTTP 下定位可能被拒，
此时可点景点卡片上的「NAVER / Google 导航」手动选点，或用隧道暴露为 HTTPS。
"""
import json
import math
import os
import secrets
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import quote

import config
import db_config as db
import rag_core

config.ensure_runtime()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MOBILE_DIR = os.path.join(BASE_DIR, "mobile")
HTML_FILE = os.path.join(MOBILE_DIR, "index.html")
DIST_DIR = os.path.join(BASE_DIR, "dist")
PACKAGE_ZIP = os.path.join(DIST_DIR, "Busan_Tour_App.zip")

# 沙下区景点坐标（与 rules.txt 一致，近似坐标）
SPOTS_GEO = [
    {"name": "甘川文化村",        "ko": "감천문화마을",       "lat": 35.0972, "lng": 128.9769, "cat": "01_艺术村落_文化街区"},
    {"name": "多大浦海水浴场",    "ko": "다대포해수욕장",     "lat": 35.0550, "lng": 128.8910, "cat": "02_海岸休闲_日落夜景"},
    {"name": "没云台",            "ko": "몰운대",             "lat": 35.0510, "lng": 128.8820, "cat": "02_海岸休闲_日落夜景"},
    {"name": "多大浦梦之夕阳喷泉", "ko": "다대포 꿈의 낙조분수", "lat": 35.0550, "lng": 128.8920, "cat": "02_海岸休闲_日落夜景"},
    {"name": "洛东江河口生态中心", "ko": "낙동강하구에코센터", "lat": 35.1065, "lng": 128.9680, "cat": "03_湿地生态_自然观景"},
    {"name": "乙淑岛候鸟公园",    "ko": "을숙도 철새도래지",   "lat": 35.1060, "lng": 128.9660, "cat": "03_湿地生态_自然观景"},
    {"name": "峨嵋山观景台",      "ko": "아미산 전망대",       "lat": 35.0620, "lng": 128.8980, "cat": "03_湿地生态_自然观景"},
    {"name": "长林浦口",          "ko": "장림포구",           "lat": 35.0880, "lng": 128.9450, "cat": "04_小众渔港_文艺拍照"},
]

CAT_LABEL = {
    "01_艺术村落_文化街区": "艺术村落",
    "02_海岸休闲_日落夜景": "海岸日落",
    "03_湿地生态_自然观景": "湿地生态",
    "04_小众渔港_文艺拍照": "小众渔港",
}

GROUP_LABEL = {
    "solo_male": "一人（男）",
    "solo_female": "一人（女）",
    "two_mf": "两人（男女）",
    "two_mm": "两人（男男）",
    "two_ff": "两人（女女）",
    "group_3plus": "三人及以上",
}

# ------------------------------------------------------------------
# 会话：内存会话表 + Cookie（与数据库里的 users 表解耦，只记录「谁登录了」）
# 三端共用同一个 busan_travel.db，账号在手机、桌面、网页之间互通。
# ------------------------------------------------------------------
COOKIE_NAME = "busan_sid"
SESSION_TTL = 7 * 24 * 3600
SESSIONS = {}
_SESSION_LOCK = threading.Lock()


def new_session(username, role, user_id):
    sid = secrets.token_hex(16)
    with _SESSION_LOCK:
        SESSIONS[sid] = {"username": username, "role": role, "user_id": user_id,
                         "created": time.time()}
    return sid


def get_session(sid):
    if not sid:
        return None
    with _SESSION_LOCK:
        s = SESSIONS.get(sid)
        if not s:
            return None
        if time.time() - s["created"] > SESSION_TTL:
            SESSIONS.pop(sid, None)
            return None
        return s


def drop_session(sid):
    with _SESSION_LOCK:
        SESSIONS.pop(sid, None)


def haversine_km(lat1, lng1, lat2, lng2):
    """两点间球面距离（公里）。"""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def nearby(lat, lng, limit=8):
    """
    GPS 附近景点：haversine 升序 + NAVER 地图深链。
    深链分两种（NAVER Map 官方 URL Scheme）：
      · nmap://place?lat=&lng=&name=   精确定位到该景点（带坐标，不靠关键词搜索）
      · nmap://route/public?slat=&slng=&dlat=&dlng=  用「我的位置」直接规划到景点
    浏览器/WebView 里唤不起 App 时，前端会回退到 NAVER 网页地图与 Google Maps。
    """
    items = []
    app_tag = "appname=com.busan.tour"
    for s in SPOTS_GEO:
        d = haversine_km(lat, lng, s["lat"], s["lng"])
        ko = quote(s["ko"])
        items.append({
            **s,
            "cat_label": CAT_LABEL.get(s["cat"], s["cat"]),
            "distance_km": round(d, 2),
            # ① 精确定位（坐标直给，NAVER 不需要再猜地点）
            "naver_place_url": (f"nmap://place?lat={s['lat']}&lng={s['lng']}&name={ko}&{app_tag}"),
            # ② 从当前位置导航到景点（手机版独有：用浏览器定位做起点）
            "naver_route_url": (f"nmap://route/public?slat={lat}&slng={lng}&sname={quote('현위치')}"
                                f"&dlat={s['lat']}&dlng={s['lng']}&dname={ko}&{app_tag}"),
            # ③ 兼容旧前端的搜索式深链
            "naver_url": f"nmap://search?query={ko}&lat={s['lat']}&lng={s['lng']}&{app_tag}",
            # ④ 兜底：网页版地图（唤不起 App 时用）
            "naver_web_url": f"https://map.naver.com/p/search/{ko}",
            "google_url": f"https://www.google.com/maps/dir/?api=1&destination={s['lat']},{s['lng']}",
        })
    items.sort(key=lambda x: x["distance_km"])
    return items[:limit]


# PWA 静态资源（内联，避免多文件依赖）
MANIFEST_JSON = json.dumps({
    "name": "Busan AI 旅行助手",
    "short_name": "Busan Tour",
    "description": "釜山沙下区 AI 旅行助手：问答 + GPS 附近景点 + 景点官网联网检索",
    "start_url": "/",
    "display": "standalone",
    "orientation": "portrait",
    "background_color": "#0b1622",
    "theme_color": "#0b1622",
    "icons": [
        {"src": "/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
        {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
    ],
}, ensure_ascii=False, indent=2)

SW_JS = """
// Busan Tour service worker: 页面网络优先（前端改动即时生效），静态图标缓存优先
const CACHE = 'busan-tour-v4';
const ASSETS = ['/manifest.json', '/icon-192.png', '/icon-512.png'];
self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  const url = e.request.url;
  if (url.includes('/api/') || url.includes('/download/') || url.includes('/sw.js')) return; // 接口/安装包/脚本不缓存
  if (e.request.mode === 'navigate') {   // 页面：网络优先，断网回退缓存
    e.respondWith(fetch(e.request).catch(() => caches.match('/')));
    return;
  }
  e.respondWith(
    caches.match(e.request).then(hit => hit || fetch(e.request).then(resp => {
      const copy = resp.clone();
      caches.open(CACHE).then(c => c.put(e.request, copy));
      return resp;
    }))
  );
});
"""


def make_icon(size):
    """生成一个简易应用图标（蓝色底 + 白色 B 字），返回 PNG bytes。"""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        return None
    img = Image.new("RGBA", (size, size), (11, 22, 34, 255))
    d = ImageDraw.Draw(img)
    d.polygon([(0, size), (size, size * 0.55), (size, size), (0, size)], fill=(8, 145, 178, 255))
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
    def _send(self, code, body, ctype="application/json; charset=utf-8", cache=False, extra=None):
        data = body if isinstance(body, (bytes, bytearray)) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        if cache:
            self.send_header("Cache-Control", "max-age=3600")
        if extra:
            for k, v in extra.items():
                self.send_header(k, v)
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

    # ---------- 会话 ----------
    def _sid(self):
        cookie = self.headers.get("Cookie", "") or ""
        for part in cookie.split(";"):
            part = part.strip()
            if part.startswith(COOKIE_NAME + "="):
                return part.split("=", 1)[1]
        return ""

    def _session(self):
        return get_session(self._sid())

    def _cookie_header(self, sid):
        base = f"{COOKIE_NAME}={sid}; Path=/; Max-Age={SESSION_TTL}; SameSite=Lax"
        return {"Set-Cookie": base}

    def _me_payload(self, sess=None):
        s = sess if sess is not None else self._session()
        if not s:
            return {"logged_in": False, "username": "", "role": "", "user_id": None,
                    "online": False, "db": db.db_path_in_use()}
        return {"logged_in": True, "username": s["username"], "role": s["role"],
                "user_id": s["user_id"], "online": True, "db": db.db_path_in_use()}

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

        elif path == "/api/meta":
            self._send(200, json.dumps({
                "categories": [{"key": c, "label": CAT_LABEL.get(c, c)} for c in config.CATEGORIES],
                "groups": [{"key": g, "label": GROUP_LABEL.get(g, g)} for g in config.GROUP_TYPES],
            }, ensure_ascii=False))

        elif path == "/api/me":
            self._send(200, json.dumps(self._me_payload(), ensure_ascii=False))

        elif path == "/download/Busan_Tour_App.zip":
            if os.path.exists(PACKAGE_ZIP):
                with open(PACKAGE_ZIP, "rb") as f:
                    data = f.read()
                self._send(200, data, "application/zip", extra={
                    "Content-Disposition": 'attachment; filename="Busan_Tour_App.zip"',
                })
            else:
                self._send(404, json.dumps({
                    "error": "安装包尚未生成，请先在电脑上运行 python build_package.py"
                }, ensure_ascii=False), "application/json; charset=utf-8")

        else:
            self._send(404, "not found", "text/plain; charset=utf-8")

    def do_POST(self):
        if self.path == "/api/login":
            body = self._read_json()
            u = (body.get("username") or "").strip()
            p = (body.get("password") or "").strip()
            ok, role, msg_key = db.verify_login(u, p)
            if not ok:
                self._send(200, json.dumps({"ok": False, "msg_key": msg_key}, ensure_ascii=False))
                return
            user = db.get_user(u) or {}
            sid = new_session(u, role, user.get("id"))
            payload = self._me_payload(get_session(sid))
            payload["ok"] = True
            payload["msg_key"] = msg_key
            self._send(200, json.dumps(payload, ensure_ascii=False), extra=self._cookie_header(sid))
            return

        if self.path == "/api/register":
            body = self._read_json()
            u = (body.get("username") or "").strip()
            p = (body.get("password") or "").strip()
            ok, msg_key = db.add_user(u, p)
            if not ok:
                self._send(200, json.dumps({"ok": False, "msg_key": msg_key}, ensure_ascii=False))
                return
            user = db.get_user(u) or {}
            sid = new_session(u, user.get("role", "user"), user.get("id"))
            payload = self._me_payload(get_session(sid))
            payload["ok"] = True
            payload["msg_key"] = msg_key
            self._send(200, json.dumps(payload, ensure_ascii=False), extra=self._cookie_header(sid))
            return

        if self.path == "/api/logout":
            drop_session(self._sid())
            payload = self._me_payload()
            payload["ok"] = True
            self._send(200, json.dumps(payload, ensure_ascii=False),
                       extra=self._cookie_header(""))
            return

        if self.path == "/api/chat":
            body = self._read_json()
            q = (body.get("question") or "").strip()
            cat = body.get("category") or ""
            grp = body.get("group_type") or ""
            ui = body.get("ui_lang") or "zh"
            sess = self._session()
            online = bool(sess)
            username = sess["username"] if sess else "guest"
            if not q:
                self._send(200, json.dumps({
                    "answer": "", "sources": [], "followups": [], "recognize": "",
                    "supplements": [], "category": None, "group_type": None,
                    "online": online, "web_count": 0, "concise": False,
                }, ensure_ascii=False))
                return
            r = rag_core.answer(q, category=cat or None, group_type=grp or None,
                                lang=None, ui_lang=ui, username=username, online=online)
            # supplements 内含内部 SpotDoc 对象，出参前只保留可序列化字段
            supplements = [
                {"name": s.get("name"), "category": s.get("category"),
                 "cat_label": s.get("cat_label"), "reason": s.get("reason")}
                for s in r.get("supplements", [])
            ]
            # 与桌面版 / 网页版共用 query_logs：后台按账号能看到手机端的提问
            try:
                db.log_query(sess["user_id"] if sess else None, username,
                             r.get("category"), r.get("group_type"), q,
                             (r.get("answer") or "")[:2000],
                             json.dumps(r.get("sources", [])[:8], ensure_ascii=False),
                             r.get("lang") or ui)
            except Exception:
                pass
            self._send(200, json.dumps({
                "answer": r.get("answer", ""),
                "sources": r.get("sources", []),
                "followups": r.get("followups", []),
                "spot": r.get("spot"),
                "field": r.get("field"),
                "lang": r.get("lang"),
                "recognize": r.get("recognize", ""),
                "offline": r.get("offline", True),
                "supplements": supplements,
                "category": r.get("category"),
                "group_type": r.get("group_type"),
                "online": r.get("online", online),
                "web_count": r.get("web_count", 0),
                "concise": r.get("concise", False),
                "username": username,
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
            self._send(200, json.dumps({"user_lat": lat, "user_lng": lng, "spots": items,
                                        "map_app": "naver"}, ensure_ascii=False))
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
    print("🚗 Busan 手机版已启动：", flush=True)
    print(f"   本机访问：   http://127.0.0.1:{port}/", flush=True)
    print(f"   手机访问：   http://{ip}:{port}/", flush=True)
    print(f"   用户数据库： {db.db_path_in_use()}（与桌面版 / 网页版共用）", flush=True)
    print("   登录后开启联网检索（景点官网 + 在线 AI）；未登录为纯本地库直出。", flush=True)
    print("   提示：浏览器定位要求 HTTPS 或 localhost；局域网 HTTP 下可用隧道暴露。", flush=True)
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    main()
