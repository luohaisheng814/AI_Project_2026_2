# -*- coding: utf-8 -*-
"""admin_tests.py —— v3.1 后台 HTTP 接口测试

覆盖：公开接口 / 登录与令牌 / 管理员与普通用户权限 / 账号增改删 /
景点增改删（rev 自增与内容下发）/ 版本发布 / 安装包下载 / 静态发布包 / CORS。

跑法（项目根已备好 .venv）：
    .venv\\Scripts\\python.exe Busan\\admin_tests.py
默认在 127.0.0.1:8790 起一个临时服务，测完自动关掉。
"""
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
PORT = 8790
HOST = "127.0.0.1"
ROOT = f"http://{HOST}:{PORT}"

pass_n = 0
fail_n = 0
failed = []


def ok(name, cond, extra=""):
    global pass_n, fail_n
    if cond:
        pass_n += 1
        print("PASS  " + name)
    else:
        fail_n += 1
        failed.append(name + ((" -> " + str(extra)) if extra else ""))
        print("FAIL  " + name + ((" -> " + str(extra)) if extra else ""))


def req(path, method="GET", body=None, token=None, raw=False):
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    r = urllib.request.Request(ROOT + path, data=data, method=method)
    if data is not None:
        r.add_header("Content-Type", "application/json")
    if token:
        r.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(r, timeout=10) as resp:
            payload = resp.read()
            return resp.status, (payload if raw else json.loads(payload.decode("utf-8") or "{}")), dict(resp.headers)
    except urllib.error.HTTPError as e:
        payload = e.read()
        try:
            j = json.loads(payload.decode("utf-8") or "{}")
        except Exception:
            j = {"raw": payload[:200]}
        return e.code, j, dict(e.headers)


def wait_up(timeout=20):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            s, j, _ = req("/api/health")
            if s == 200 and j.get("ok"):
                return True
        except Exception:
            pass
        time.sleep(0.35)
    return False


def main():
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    proc = subprocess.Popen([sys.executable, os.path.join(BASE, "admin_server.py"),
                             "--port", str(PORT), "--host", HOST],
                            cwd=BASE, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        if not wait_up():
            print("服务未启动，输出：")
            print(proc.stdout.read().decode("utf-8", "ignore") if proc.stdout else "")
            raise SystemExit(2)

        # 1. 公开接口与 CORS
        s, j, h = req("/api/health")
        ok("公开: /api/health 200", s == 200 and j.get("ok") is True, s)
        s, j, h = req("/api/state")
        ok("公开: /api/state 带 rev 与 version", s == 200 and "rev" in j and j.get("version", {}).get("code"), j)
        ok("CORS: 允许任意来源（手机跨域网关）", h.get("Access-Control-Allow-Origin") == "*", h.get("Access-Control-Allow-Origin"))
        s, j, h = req("/api/state.json")
        ok("别名: /api/state.json 与 /api/state 等价", s == 200 and j.get("rev") == req("/api/state")[1].get("rev"), s)
        s, j, _ = req("/api/content")
        ok("公开: /api/content 有 18 个景点", s == 200 and len(j.get("spots", [])) >= 18, len(j.get("spots", [])))
        s, j, _ = req("/admin", raw=True)
        ok("后台页面: /admin 返回管理台 HTML", s == 200 and "釜山 AI 旅行助手 · 后台" in j.decode("utf-8", "ignore"), s)

        # 2. 登录
        s, j, _ = req("/api/login", "POST", {"username": "admin", "password": "wrong"})
        ok("登录: 错误密码 401", s == 401 and j.get("ok") is False, s)
        s, j, _ = req("/api/login", "POST", {"username": "admin", "password": "admin"})
        ok("登录: 默认管理员 admin/admin 通过", s == 200 and j.get("ok") and j.get("token"), s)
        tok = j.get("token")
        ok("登录: 返回角色 admin", j.get("user", {}).get("role") == "admin", j.get("user"))
        s, j, _ = req("/api/me")
        ok("鉴权: 无令牌 401", s == 401, s)
        s, j, _ = req("/api/me", token=tok)
        ok("鉴权: Bearer 令牌可取当前账号", s == 200 and j.get("user", {}).get("username") == "admin", j)

        # 3. 账号 CRUD + 权限
        uname = "probe_%d" % int(time.time() % 100000)
        s, j, _ = req("/api/users", "POST", {"username": uname, "password": "probe123",
                                             "role": "user", "nickname": "测试账号"}, token=tok)
        ok("账号: 管理员可新建普通用户", s == 200 and j.get("item", {}).get("username") == uname, j)
        uid = j.get("item", {}).get("id")
        s, j, _ = req("/api/users", "POST", {"username": uname, "password": "probe123"}, token=tok)
        ok("账号: 重名被拒", s == 400 and "已存在" in j.get("error", ""), j)
        s, j, _ = req("/api/users/%d" % uid, "PUT", {"nickname": "改名了", "email": "p@x.com"}, token=tok)
        ok("账号: 改昵称/邮箱", s == 200 and j.get("item", {}).get("nickname") == "改名了", j)

        s, j, _ = req("/api/login", "POST", {"username": uname, "password": "probe123"})
        utok = j.get("token")
        ok("账号: 新建用户可登录", s == 200 and utok, s)
        s, j, _ = req("/api/spots", token=utok)
        ok("权限: 普通用户可读内容", s == 200 and len(j.get("items", [])) >= 18, s)
        s, j, _ = req("/api/spots", "POST", {"id": "probe_x", "name": "越权"}, token=utok)
        ok("权限: 普通用户不能改内容 403", s == 403, (s, j))
        s, j, _ = req("/api/users", "POST", {"username": "x2", "password": "x1234"}, token=utok)
        ok("权限: 普通用户不能建账号 403", s == 403, (s, j))
        s, j, _ = req("/api/audit", token=utok)
        ok("权限: 普通用户看不到审计 403", s == 403, s)

        # 4. 景点 CRUD + rev（用带时间戳的 id，保证可反复跑）
        pid = "probe_spot_%d" % int(time.time())
        rev0 = req("/api/state")[1]["rev"]
        s, j, _ = req("/api/spots", "POST", {
            "id": pid, "name": "探针景点", "name_ko": "프로브", "name_en": "Probe",
            "category": "测试", "address": "Busan", "lat": 35.1, "lng": 129.0,
            "fields": {"zh": {"overview": "第一版"}, "ko": {}, "en": {}}, "aliases": ["探针"]}, token=tok)
        ok("内容: 新增景点成功", s == 200 and j.get("item", {}).get("id") == pid, j)
        rev1 = j.get("rev")
        ok("内容: 新增后 rev 自增", rev1 == rev0 + 1, (rev0, rev1))
        s, j, _ = req("/api/spots/" + pid, "PUT", {
            "name": "探针景点2", "fields": {"zh": {"overview": "第二版"}}}, token=tok)
        ok("内容: 修改景点成功", s == 200 and j.get("item", {}).get("name") == "探针景点2", j)
        rev2 = j.get("rev")
        ok("内容: 修改后 rev 再 +1", rev2 == (rev1 or 0) + 1, (rev1, rev2))
        s, j, _ = req("/api/content")
        hit = [x for x in j.get("spots", []) if x["id"] == pid]
        ok("内容: 前端拉取能看到新条目", s == 200 and hit and hit[0]["name"] == "探针景点2", hit)
        ok("内容: 前端拉到的 rev 与后台一致", j.get("rev") == rev2, (j.get("rev"), rev2))
        s, j, _ = req("/api/spots/" + pid, "DELETE", token=tok)
        ok("内容: 删除景点成功", s == 200 and j.get("rev") == (rev2 or 0) + 1, j)
        s, j, _ = req("/api/content")
        ok("内容: 删除后前端不再下发", not [x for x in j.get("spots", []) if x["id"] == pid], j.get("rev"))
        s, j, _ = req("/api/spots/" + pid, token=tok)
        ok("内容: 已删除条目仍可按 id 取到（软删除可恢复）", s == 200 and j.get("item", {}).get("deleted") == 1, j)
        s, j, _ = req("/api/spots", "POST", {
            "id": pid, "name": "探针景点3", "fields": {"zh": {"overview": "恢复版"}}}, token=tok)
        ok("内容: 同 id 再新增 = 恢复软删除条目", s == 200 and j.get("item", {}).get("deleted") == 0, j)
        req("/api/spots/" + pid, "DELETE", token=tok)
        ok("内容: 探针景点清理完毕", not [x for x in req("/api/content")[1].get("spots", []) if x["id"] == pid])

        # 5. 版本与安装包
        s, j, _ = req("/api/versions", token=tok)
        ok("版本: 历史列表可读", s == 200 and len(j.get("items", [])) >= 1, s)
        s, j, _ = req("/api/versions", "POST", {"version_name": "9.9", "version_code": 0}, token=tok)
        ok("版本: 非法版本号被拒", s == 400, j)
        s, j, h = req("/api/download", raw=True)
        if s == 200:
            ok("下载: /api/download 返回 APK", h.get("Content-Type", "").endswith("android.package-archive"), h.get("Content-Type"))
            ok("下载: 带附件文件名", "attachment" in h.get("Content-Disposition", ""), h.get("Content-Disposition"))
        else:
            ok("下载: 安装包存在（先构建 APK）", False, s)

        # 6. 静态发布包
        s, j, _ = req("/api/publish", "POST", {}, token=tok)
        ok("发布: 生成静态包", s == 200 and j.get("ok"), j)
        api = os.path.join(BASE, "android", "assets", "api")
        ok("发布: state.json 落盘", os.path.exists(os.path.join(api, "state.json")))
        ok("发布: content.json 落盘", os.path.exists(os.path.join(api, "content.json")))
        with open(os.path.join(api, "state.json"), encoding="utf-8") as f:
            st = json.load(f)
        ok("发布: 静态 state 的 rev 与接口一致", st.get("rev") == req("/api/state")[1].get("rev"), st.get("rev"))

        # 7. 收尾：删测试账号
        s, j, _ = req("/api/users/%d" % uid, "DELETE", token=tok)
        ok("账号: 删除测试账号", s == 200, j)
        s, j, _ = req("/api/users", "POST", {"username": uname + "b", "password": "x1234", "role": "user"}, token=tok)
        ok("账号: 再造一个用于管理员保护测试", s == 200, s)
        s, j, _ = req("/api/users", "POST", {"username": uname + "c", "password": "x1234", "role": "admin"}, token=tok)
        ok("账号: 可创建第二个管理员", s == 200, s)
        aid = j.get("item", {}).get("id")
        s, j, _ = req("/api/users/%d" % aid, "DELETE", token=tok)
        ok("账号: 可删除非当前管理员", s == 200, s)
        s, j, _ = req("/api/users", token=tok)
        leftover = [x for x in j.get("items", []) if x["username"].startswith(uname)]
        for x in leftover:
            req("/api/users/%d" % x["id"], "DELETE", token=tok)
        ok("账号: 测试账号清理干净", not [x for x in req("/api/users", token=tok)[1].get("items", [])
                                    if x["username"].startswith(uname)])

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()

    print("\n结果: %d 通过 / %d 失败" % (pass_n, fail_n))
    if failed:
        print("失败项:")
        for f in failed:
            print("  - " + f)
    return 1 if fail_n else 0


if __name__ == "__main__":
    sys.exit(main())
