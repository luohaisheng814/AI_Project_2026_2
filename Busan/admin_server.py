# -*- coding: utf-8 -*-
"""admin_server.py —— v3.1 后台服务

一套标准库 HTTP 服务，同时提供：
  /admin                后台管理界面（账号 / 内容 / 版本 / 审计）
  /api/*                手机端与后台共用的 JSON 接口
  /api/download         当前安装包（APK）

启动：
    D:\\AI_Project_2026_2\\.venv\\Scripts\\python.exe Busan\\admin_server.py
默认端口 8765，可用 --port 指定。手机与电脑在同一 Wi‑Fi 时，
用打印出来的 http://<局域网IP>:8765/admin 打开后台。
"""
import argparse
import json
import os
import socket
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import admin_store as store

BASE = os.path.dirname(os.path.abspath(__file__))
UI_FILE = os.path.join(BASE, "admin_ui.html")
SESSIONS = {}
SESSION_TTL = 12 * 3600
LOCK = threading.Lock()


def lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.3)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def _token(user):
    tok = os.urandom(24).hex()
    with LOCK:
        SESSIONS[tok] = {"user": user, "exp": time.time() + SESSION_TTL}
    return tok


def _session(handler):
    auth = handler.headers.get("Authorization") or ""
    if auth.startswith("Bearer "):
        tok = auth[7:].strip()
    else:
        tok = handler.headers.get("X-Token") or ""
    with LOCK:
        s = SESSIONS.get(tok)
        if not s:
            return None
        if s["exp"] < time.time():
            SESSIONS.pop(tok, None)
            return None
        return s


class Handler(BaseHTTPRequestHandler):
    server_version = "BusanAdmin/3.1"

    # ---------------- 基础 ----------------
    def log_message(self, fmt, *args):
        if self.path.startswith("/api/") and "state" in self.path:
            return
        print("[%s] %s" % (time.strftime("%H:%M:%S"), fmt % args))

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type,Authorization,X-Token")
        self.send_header("Cache-Control", "no-store")

    def _json(self, obj, code=200):
        raw = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._cors()
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _err(self, msg, code=400):
        self._json({"ok": False, "error": msg}, code)

    def _body(self):
        try:
            n = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(n) if n else b"{}"
            return json.loads(raw.decode("utf-8") or "{}")
        except Exception:
            return {}

    def _user(self):
        s = _session(self)
        return s["user"] if s else None

    def _require(self, role="user"):
        u = self._user()
        if not u:
            self._err("未登录或登录已过期", 401)
            return None
        if role == "admin" and u.get("role") != "admin":
            self._err("需要管理员权限", 403)
            return None
        return u

    # ---------------- 路由 ----------------
    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)

        if path in ("/", "/admin", "/admin/"):
            return self._file(UI_FILE, "text/html; charset=utf-8")
        if path == "/api/health":
            return self._json({"ok": True, "ts": store.now(), "rev": store.content_rev()})
        if path in ("/api/state", "/api/state.json"):
            return self._json(store.state_payload())
        if path in ("/api/content", "/api/content.json"):
            return self._json(store.content_payload())
        if path == "/api/download":
            apk = store.DIST_APK
            if not os.path.exists(apk):
                return self._err("安装包不存在", 404)
            self.send_response(200)
            self.send_header("Content-Type", "application/vnd.android.package-archive")
            self._cors()
            self.send_header("Content-Disposition",
                             'attachment; filename="Busan-Travel-Assistant-3.1.apk"')
            self.send_header("Content-Length", str(os.path.getsize(apk)))
            self.end_headers()
            with open(apk, "rb") as f:
                while True:
                    chunk = f.read(1 << 20)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
            return

        if path == "/api/me":
            u = self._require()
            if not u:
                return
            return self._json({"ok": True, "user": store.get_user(u["id"])})
        if path == "/api/users":
            u = self._require()
            if not u:
                return
            users = store.list_users()
            if u.get("role") != "admin":
                users = [{k: x[k] for k in ("id", "username", "role", "nickname")} for x in users]
            return self._json({"ok": True, "items": users})
        if path == "/api/spots":
            u = self._require()
            if not u:
                return
            items = store.list_spots(include_deleted=qs.get("deleted", ["0"])[0] == "1",
                                     q=qs.get("q", [""])[0])
            return self._json({"ok": True, "items": items, "rev": store.content_rev()})
        if path.startswith("/api/spots/"):
            uid = urllib.parse.unquote(path.split("/api/spots/", 1)[1])
            if not self._user():
                return self._err("未登录", 401)
            s = store.get_spot(uid)
            return self._json({"ok": True, "item": s}) if s else self._err("景点不存在", 404)
        if path == "/api/versions":
            u = self._require()
            if not u:
                return
            return self._json({"ok": True, "items": store.list_versions()})
        if path == "/api/audit":
            u = self._require("admin")
            if not u:
                return
            return self._json({"ok": True, "items": store.list_audit(200)})
        if path == "/api/stats":
            u = self._require()
            if not u:
                return
            return self._json({"ok": True, "stats": store.stats()})
        return self._err("接口不存在", 404)

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        data = self._body()

        if path == "/api/login":
            username = (data.get("username") or "").strip()
            password = (data.get("password") or "").strip()
            if not username or not password:
                return self._err("请输入账号与密码")
            user, msg = store.login(username, password)
            if not user:
                return self._err(msg, 401)
            tok = _token(user)
            store.audit(username, "login", "admin-ui", "ip=%s" % self.client_address[0])
            return self._json({"ok": True, "token": tok, "user": user})
        if path == "/api/logout":
            auth = self.headers.get("Authorization") or ""
            if auth.startswith("Bearer "):
                with LOCK:
                    SESSIONS.pop(auth[7:].strip(), None)
            return self._json({"ok": True})
        if path == "/api/users":
            u = self._require("admin")
            if not u:
                return
            try:
                item = store.create_user(data.get("username"), data.get("password"),
                                         data.get("role") or "user", data.get("nickname") or "",
                                         data.get("email") or "", actor=u["username"])
            except ValueError as e:
                return self._err(str(e))
            return self._json({"ok": True, "item": item})
        if path == "/api/spots":
            u = self._require("admin")
            if not u:
                return
            try:
                item, rev = store.save_spot(data, actor=u["username"], is_new=True)
            except ValueError as e:
                return self._err(str(e))
            return self._json({"ok": True, "item": item, "rev": rev})
        if path == "/api/versions":
            u = self._require("admin")
            if not u:
                return
            try:
                v = store.publish_version(data.get("version_name"), data.get("version_code"),
                                          data.get("notes") or "", actor=u["username"])
            except (ValueError, TypeError) as e:
                return self._err(str(e))
            store.publish_static(u["username"])
            return self._json({"ok": True, "version": v, "rev": store.content_rev()})
        if path == "/api/publish":
            u = self._require("admin")
            if not u:
                return
            return self._json({"ok": True, "state": store.publish_static(u["username"])})
        return self._err("接口不存在", 404)

    def do_PUT(self):
        path = urllib.parse.urlparse(self.path).path
        data = self._body()
        u = self._require("admin")
        if not u:
            return
        if path.startswith("/api/users/"):
            uid = path.split("/api/users/", 1)[1]
            try:
                item = store.update_user(int(uid), data, actor=u["username"])
            except ValueError as e:
                return self._err(str(e))
            return self._json({"ok": True, "item": item})
        if path.startswith("/api/spots/"):
            sid = urllib.parse.unquote(path.split("/api/spots/", 1)[1])
            if store.get_spot(sid) is None:
                return self._err("景点不存在", 404)
            try:
                item, rev = store.save_spot(dict(data, id=sid), actor=u["username"])
            except ValueError as e:
                return self._err(str(e))
            return self._json({"ok": True, "item": item, "rev": rev})
        return self._err("接口不存在", 404)

    def do_DELETE(self):
        path = urllib.parse.urlparse(self.path).path
        u = self._require("admin")
        if not u:
            return
        if path.startswith("/api/users/"):
            uid = int(path.split("/api/users/", 1)[1])
            if uid == u["id"]:
                return self._err("不能删除当前登录的账号")
            try:
                store.delete_user(uid, actor=u["username"])
            except ValueError as e:
                return self._err(str(e))
            return self._json({"ok": True})
        if path.startswith("/api/spots/"):
            sid = urllib.parse.unquote(path.split("/api/spots/", 1)[1])
            try:
                rev = store.delete_spot(sid, actor=u["username"])
            except ValueError as e:
                return self._err(str(e))
            return self._json({"ok": True, "rev": rev})
        return self._err("接口不存在", 404)

    def _file(self, fp, ctype):
        if not os.path.exists(fp):
            return self._err("文件不存在: " + os.path.basename(fp), 404)
        raw = open(fp, "rb").read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self._cors()
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--host", default="0.0.0.0")
    args = ap.parse_args()
    store.init()
    ip = lan_ip()
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    print("=" * 64)
    print("Busan 后台已启动")
    print("  本机后台:   http://127.0.0.1:%d/admin" % args.port)
    print("  手机可访问: http://%s:%d/admin  （手机与电脑同一 Wi‑Fi）" % (ip, args.port))
    print("  手机端接口: http://%s:%d/api/state" % (ip, args.port))
    print("  默认管理员: admin / admin")
    print("=" * 64)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("已停止")


if __name__ == "__main__":
    main()
