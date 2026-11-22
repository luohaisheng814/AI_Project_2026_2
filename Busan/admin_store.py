# -*- coding: utf-8 -*-
"""admin_store.py —— v3.1 后台数据层

在原有 busan_travel.db 上扩展：账号（users 增加昵称/邮箱/状态）、
景点内容（spots）、版本（app_versions）、设置（app_settings）、审计（admin_audit）。
账号密码沿用 db_config 的 PBKDF2 方案，默认管理员 admin/admin。
"""
import hashlib
import json
import os
import re
import sqlite3
from datetime import datetime

import config
import db_config

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_JSON = os.path.join(BASE, "android", "assets", "data.json")
MANIFEST = os.path.join(BASE, "android", "AndroidManifest.xml")
STATIC_API_DIR = os.path.join(BASE, "android", "assets", "api")
DIST_APK = os.path.join(BASE, "dist", "Busan旅行助手.apk")
APK_NAME = "Busan旅行助手.apk"

ROLE_ADMIN = "admin"
ROLE_USER = "user"


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _conn():
    return db_config.get_conn()


def init():
    """建表、补列、灌入初始景点与版本。可重复调用。"""
    db_config.init_db()
    conn = _conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS spots (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            name_ko     TEXT,
            name_en     TEXT,
            category    TEXT,
            address     TEXT,
            lat         REAL,
            lng         REAL,
            fields      TEXT,
            aliases     TEXT,
            deleted     INTEGER NOT NULL DEFAULT 0,
            updated_at  TEXT,
            updated_by  TEXT
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            k TEXT PRIMARY KEY,
            v TEXT
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS app_versions (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            version_code INTEGER NOT NULL,
            version_name TEXT NOT NULL,
            notes        TEXT,
            apk_path     TEXT,
            apk_size     INTEGER,
            apk_sha256   TEXT,
            created_at   TEXT,
            created_by   TEXT,
            is_current   INTEGER NOT NULL DEFAULT 1
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS admin_audit (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            actor      TEXT,
            action     TEXT,
            target     TEXT,
            detail     TEXT,
            created_at TEXT
        );
    """)
    # users 补昵称/邮箱/状态列（老库兼容）
    cur.execute("PRAGMA table_info(users)")
    cols = {r[1] for r in cur.fetchall()}
    for col, ddl in (("nickname", "TEXT"), ("email", "TEXT"),
                     ("status", "TEXT DEFAULT 'active'")):
        if col not in cols:
            cur.execute(f"ALTER TABLE users ADD COLUMN {col} {ddl}")
    conn.commit()
    conn.close()

    _seed_settings()
    _seed_spots()
    _seed_version()
    return True


def _get(k, default=None):
    conn = _conn()
    row = conn.execute("SELECT v FROM app_settings WHERE k=?", (k,)).fetchone()
    conn.close()
    return row["v"] if row else default


def _set(k, v, conn=None):
    own = conn is None
    conn = conn or _conn()
    conn.execute(
        "INSERT INTO app_settings(k,v) VALUES(?,?) "
        "ON CONFLICT(k) DO UPDATE SET v=excluded.v", (k, str(v)))
    if own:
        conn.commit()
        conn.close()


def _bump_rev(conn=None):
    own = conn is None
    conn = conn or _conn()
    cur = conn.execute("SELECT v FROM app_settings WHERE k='content_rev'").fetchone()
    rev = int(cur["v"]) + 1 if cur else 1
    _set("content_rev", rev, conn)
    _set("content_updated_at", now(), conn)
    if own:
        conn.commit()
        conn.close()
    return rev


def content_rev():
    return int(_get("content_rev", 0) or 0)


def _seed_settings():
    conn = _conn()
    for k, v in (("content_rev", 1), ("content_updated_at", now()),
                 ("site_title", "釜山 AI 旅行助手 · 后台")):
        if conn.execute("SELECT 1 FROM app_settings WHERE k=?", (k,)).fetchone() is None:
            _set(k, v, conn)
    conn.commit()
    conn.close()


def _seed_spots():
    conn = _conn()
    n = conn.execute("SELECT COUNT(1) AS c FROM spots").fetchone()["c"]
    if n:
        conn.close()
        return
    if not os.path.exists(DATA_JSON):
        conn.close()
        return
    with open(DATA_JSON, encoding="utf-8") as f:
        data = json.load(f)
    for s in data.get("spots", []):
        conn.execute(
            "INSERT INTO spots(id,name,name_ko,name_en,category,address,lat,lng,fields,aliases,"
            "deleted,updated_at,updated_by) VALUES(?,?,?,?,?,?,?,?,?,?,0,?,?)",
            (s.get("id"), s.get("name") or s.get("id"), s.get("name_ko"), s.get("name_en"),
             s.get("category"), s.get("address"), s.get("lat"), s.get("lng"),
             json.dumps(s.get("fields") or {}, ensure_ascii=False),
             json.dumps(s.get("aliases") or [], ensure_ascii=False), now(), "seed"))
    conn.commit()
    conn.close()


def manifest_version():
    try:
        txt = open(MANIFEST, encoding="utf-8").read()
        code = int(re.search(r'android:versionCode="(\d+)"', txt).group(1))
        name = re.search(r'android:versionName="([^"]+)"', txt).group(1)
        return code, name
    except Exception:
        return 23, "3.0"


def _seed_version():
    conn = _conn()
    n = conn.execute("SELECT COUNT(1) AS c FROM app_versions").fetchone()["c"]
    if not n:
        code, name = manifest_version()
        conn.execute(
            "INSERT INTO app_versions(version_code,version_name,notes,created_at,created_by,is_current)"
            " VALUES(?,?,?,?,?,1)",
            (code, name, "历史版本（后台初始化）", now(), "system"))
        conn.commit()
    conn.close()


# ------------------------------------------------------------------
# 审计
# ------------------------------------------------------------------
def audit(actor, action, target, detail=""):
    conn = _conn()
    conn.execute("INSERT INTO admin_audit(actor,action,target,detail,created_at) VALUES(?,?,?,?,?)",
                 (actor, action, str(target), str(detail)[:500], now()))
    conn.commit()
    conn.close()


def list_audit(limit=100):
    conn = _conn()
    rows = conn.execute("SELECT * FROM admin_audit ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ------------------------------------------------------------------
# 账号
# ------------------------------------------------------------------
def list_users():
    conn = _conn()
    rows = conn.execute(
        "SELECT id,username,role,created_at,last_login,nickname,email,status "
        "FROM users ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_user(user_id):
    conn = _conn()
    row = conn.execute(
        "SELECT id,username,role,created_at,last_login,nickname,email,status "
        "FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_name(username):
    conn = _conn()
    row = conn.execute(
        "SELECT id,username,role,created_at,last_login,nickname,email,status "
        "FROM users WHERE username=?", (username,)).fetchone()
    conn.close()
    return dict(row) if row else None


def login(username, password):
    ok, role, msg = db_config.verify_login(username, password)
    if not ok:
        return None, "账号或密码不正确"
    u = get_user_by_name(username)
    if not u:
        return None, "账号不存在"
    if (u.get("status") or "active") != "active":
        return None, "账号已停用，请联系管理员"
    conn = _conn()
    conn.execute("UPDATE users SET last_login=? WHERE id=?", (now(), u["id"]))
    conn.commit()
    conn.close()
    u["last_login"] = now()
    return u, ""


def create_user(username, password, role="user", nickname="", email="", actor="admin"):
    username = (username or "").strip()
    password = (password or "").strip()
    role = role if role in (ROLE_ADMIN, ROLE_USER) else ROLE_USER
    if not username or not password:
        raise ValueError("账号与密码都不能为空")
    if len(password) < 4:
        raise ValueError("密码至少 4 位")
    if db_config.user_exists(username):
        raise ValueError("账号已存在")
    conn = _conn()
    conn.execute(
        "INSERT INTO users(username,password,role,created_at,nickname,email,status)"
        " VALUES(?,?,?,?,?,?, 'active')",
        (username, db_config.hash_password(password), role, now(), nickname, email))
    conn.commit()
    conn.close()
    audit(actor, "user.create", username, f"role={role}")
    return get_user_by_name(username)


def update_user(user_id, patch, actor="admin"):
    cur = get_user(user_id)
    if not cur:
        raise ValueError("账号不存在")
    sets, vals = [], []
    for k in ("nickname", "email", "status", "role"):
        if k in patch:
            v = patch[k]
            if k == "role" and v not in (ROLE_ADMIN, ROLE_USER):
                raise ValueError("角色只能是 admin 或 user")
            if k == "status" and v not in ("active", "disabled"):
                raise ValueError("状态只能是 active 或 disabled")
            sets.append(f"{k}=?")
            vals.append(v)
    if "password" in patch and str(patch["password"]).strip():
        pwd = str(patch["password"]).strip()
        if len(pwd) < 4:
            raise ValueError("密码至少 4 位")
        sets.append("password=?")
        vals.append(db_config.hash_password(pwd))
    if not sets:
        return cur
    if cur["role"] == ROLE_ADMIN and patch.get("role") == ROLE_USER and _admin_count() <= 1:
        raise ValueError("至少要保留一个管理员")
    conn = _conn()
    conn.execute(f"UPDATE users SET {', '.join(sets)} WHERE id=?", (*vals, user_id))
    conn.commit()
    conn.close()
    audit(actor, "user.update", cur["username"], json.dumps(patch, ensure_ascii=False)[:300])
    return get_user(user_id)


def _admin_count():
    conn = _conn()
    n = conn.execute("SELECT COUNT(1) AS c FROM users WHERE role='admin'").fetchone()["c"]
    conn.close()
    return n


def delete_user(user_id, actor="admin"):
    cur = get_user(user_id)
    if not cur:
        raise ValueError("账号不存在")
    if cur["role"] == ROLE_ADMIN and _admin_count() <= 1:
        raise ValueError("至少要保留一个管理员")
    conn = _conn()
    conn.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    audit(actor, "user.delete", cur["username"])


# ------------------------------------------------------------------
# 景点内容
# ------------------------------------------------------------------
def _spot_row(row):
    d = dict(row)
    try:
        d["fields"] = json.loads(d.get("fields") or "{}")
    except Exception:
        d["fields"] = {}
    try:
        d["aliases"] = json.loads(d.get("aliases") or "[]")
    except Exception:
        d["aliases"] = []
    return d


def list_spots(include_deleted=False, q=""):
    conn = _conn()
    sql = "SELECT * FROM spots"
    where = []
    if not include_deleted:
        where.append("deleted=0")
    if q:
        where.append("(name LIKE ? OR name_ko LIKE ? OR name_en LIKE ? OR id LIKE ?)")
    if where:
        sql += " WHERE " + " AND ".join(where)
    rows = conn.execute(sql, tuple([f"%{q}%"] * 4) if q else ()).fetchall()
    conn.close()
    return [_spot_row(r) for r in rows]


def get_spot(spot_id):
    conn = _conn()
    row = conn.execute("SELECT * FROM spots WHERE id=?", (spot_id,)).fetchone()
    conn.close()
    return _spot_row(row) if row else None


def save_spot(data, actor="admin", is_new=False):
    sid = (data.get("id") or data.get("name") or "").strip()
    if not sid:
        raise ValueError("景点 id 不能为空")
    cur = get_spot(sid)
    conn = _conn()
    fields = data.get("fields") or (cur or {}).get("fields") or {}
    aliases = data.get("aliases") if "aliases" in data else (cur or {}).get("aliases") or []
    if cur and is_new and not cur.get("deleted"):
        raise ValueError("景点 id 已存在")
    if cur:
        # 同 id 重新新增 = 恢复软删除的条目，按新内容覆盖
        conn.execute(
            "UPDATE spots SET name=?,name_ko=?,name_en=?,category=?,address=?,lat=?,lng=?,"
            "fields=?,aliases=?,deleted=0,updated_at=?,updated_by=? WHERE id=?",
            (data.get("name") or cur["name"], data.get("name_ko", cur["name_ko"]),
             data.get("name_en", cur["name_en"]), data.get("category", cur["category"]),
             data.get("address", cur["address"]), data.get("lat", cur["lat"]),
             data.get("lng", cur["lng"]), json.dumps(fields, ensure_ascii=False),
             json.dumps(aliases, ensure_ascii=False), now(), actor, sid))
    else:
        if not data.get("name"):
            raise ValueError("景点名称不能为空")
        conn.execute(
            "INSERT INTO spots(id,name,name_ko,name_en,category,address,lat,lng,fields,aliases,"
            "deleted,updated_at,updated_by) VALUES(?,?,?,?,?,?,?,?,?,?,0,?,?)",
            (sid, data.get("name"), data.get("name_ko"), data.get("name_en"),
             data.get("category"), data.get("address"), data.get("lat"), data.get("lng"),
             json.dumps(fields, ensure_ascii=False), json.dumps(aliases, ensure_ascii=False),
             now(), actor))
    conn.commit()
    rev = _bump_rev(conn)
    conn.commit()
    conn.close()
    audit(actor, "spot.save", sid, "rev=%d" % rev)
    return get_spot(sid), rev


def delete_spot(spot_id, actor="admin"):
    cur = get_spot(spot_id)
    if not cur:
        raise ValueError("景点不存在")
    conn = _conn()
    conn.execute("UPDATE spots SET deleted=1,updated_at=?,updated_by=? WHERE id=?",
                 (now(), actor, spot_id))
    conn.commit()
    rev = _bump_rev(conn)
    conn.commit()
    conn.close()
    audit(actor, "spot.delete", spot_id, "rev=%d" % rev)
    return rev


def restore_spot(spot_id, actor="admin"):
    conn = _conn()
    conn.execute("UPDATE spots SET deleted=0,updated_at=?,updated_by=? WHERE id=?",
                 (now(), actor, spot_id))
    conn.commit()
    rev = _bump_rev(conn)
    conn.commit()
    conn.close()
    audit(actor, "spot.restore", spot_id)
    return rev


def categories():
    out = []
    for s in list_spots():
        c = s.get("category") or "未分类"
        if c not in out:
            out.append(c)
    return out


def content_payload():
    spots = []
    for s in list_spots():
        spots.append({k: s[k] for k in ("id", "name", "name_ko", "name_en", "category",
                                        "address", "lat", "lng", "fields", "aliases")})
    return {"rev": content_rev(), "generated_at": now(), "spots": spots,
            "categories": categories()}


# ------------------------------------------------------------------
# 版本
# ------------------------------------------------------------------
def current_version():
    conn = _conn()
    row = conn.execute("SELECT * FROM app_versions WHERE is_current=1 ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    return dict(row) if row else None


def list_versions(limit=20):
    conn = _conn()
    rows = conn.execute("SELECT * FROM app_versions ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def publish_version(version_name, version_code, notes="", actor="admin", apk_path=None):
    version_name = str(version_name).strip()
    version_code = int(version_code)
    if not version_name:
        raise ValueError("版本名不能为空")
    if version_code <= 0:
        raise ValueError("versionCode 必须为正整数")
    apk_path = apk_path or DIST_APK
    size = os.path.getsize(apk_path) if os.path.exists(apk_path) else 0
    sha = _sha256(apk_path) if size else ""
    conn = _conn()
    conn.execute("UPDATE app_versions SET is_current=0")
    conn.execute(
        "INSERT INTO app_versions(version_code,version_name,notes,apk_path,apk_size,apk_sha256,"
        "created_at,created_by,is_current) VALUES(?,?,?,?,?,?,?,?,1)",
        (version_code, version_name, notes, apk_path, size, sha, now(), actor))
    conn.commit()
    conn.close()
    audit(actor, "version.publish", f"{version_name}/{version_code}", notes[:200])
    return current_version()


def state_payload():
    v = current_version() or {}
    return {
        "rev": content_rev(),
        "generated_at": now(),
        "version": {
            "name": v.get("version_name"),
            "code": v.get("version_code") or 0,
            "notes": v.get("notes") or "",
            "published_at": v.get("created_at") or "",
            "size": v.get("apk_size") or 0,
            "sha256": v.get("apk_sha256") or "",
            "download": "https://github.com/luohaisheng814/AI_Project_2026_2/raw/main/Busan/dist/Busan%E6%97%85%E8%A1%8C%E5%8A%A9%E6%89%8B.apk",
        },
    }


def publish_static(actor="admin"):
    """把 state/content 写进 android/assets/api，随 Pages 一起发布。"""
    os.makedirs(STATIC_API_DIR, exist_ok=True)
    stamp = now()
    state = state_payload()
    state["generated_at"] = stamp
    with open(os.path.join(STATIC_API_DIR, "state.json"), "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    with open(os.path.join(STATIC_API_DIR, "content.json"), "w", encoding="utf-8") as f:
        json.dump(content_payload(), f, ensure_ascii=False)
    # 手机端后台地址兜底配置
    with open(os.path.join(BASE, "android", "assets", "admin_base.js"), "w", encoding="utf-8") as f:
        f.write("window.BUSAN_ADMIN_BASE = %s;\n" % json.dumps(""))
    audit(actor, "static.publish", "assets/api", "state+content")
    return state


def stats():
    conn = _conn()
    users = conn.execute("SELECT COUNT(1) AS c FROM users").fetchone()["c"]
    admins = conn.execute("SELECT COUNT(1) AS c FROM users WHERE role='admin'").fetchone()["c"]
    spots = conn.execute("SELECT COUNT(1) AS c FROM spots WHERE deleted=0").fetchone()["c"]
    deleted = conn.execute("SELECT COUNT(1) AS c FROM spots WHERE deleted=1").fetchone()["c"]
    logs = conn.execute("SELECT COUNT(1) AS c FROM admin_audit").fetchone()["c"]
    conn.close()
    return {"users": users, "admins": admins, "spots": spots, "deleted_spots": deleted,
            "audit": logs, "rev": content_rev(), "version": current_version()}


if __name__ == "__main__":
    init()
    print(json.dumps(stats(), ensure_ascii=False, indent=2))
    print("users:", [(u["username"], u["role"]) for u in list_users()])
