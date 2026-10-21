# -*- coding: utf-8 -*-
"""
数据库层（SQLite）
--------------------------------------------------
users      : id / username / password(PBKDF2 加盐哈希) / role(user|admin) / created_at / last_login
query_logs : 每位用户的详细查询（玩法、人数、问题、答案、来源、语言、时间）
对外只暴露函数，UI 层不直接写 SQL。
"""

import os
import sqlite3
import hashlib
import secrets
from datetime import datetime

import config


# ------------------------------------------------------------------
# 连接：SQLite 在个别文件系统（网络盘 / 容器挂载盘 / 部分 virtiofs）上无法加写锁，
# 这里做三级降级：首选路径 -> 系统临时目录 -> 常驻内存库，保证任何环境都能跑起来。
# ------------------------------------------------------------------
_FALLBACK_PATH = None
_MEM_CONN = None


class _SharedConnection:
    """内存库专用包装：忽略业务代码的 close()，保持连接常驻。"""

    def __init__(self, conn):
        self._conn = conn

    def close(self):
        pass

    def __getattr__(self, name):
        return getattr(self._conn, name)


def _tmp_dir():
    import tempfile
    d = os.path.join(tempfile.gettempdir(), "busan_ai")
    os.makedirs(d, exist_ok=True)
    return d


def get_conn():
    global _FALLBACK_PATH, _MEM_CONN
    candidates = [config.DB_PATH]
    if _FALLBACK_PATH:
        candidates = [_FALLBACK_PATH]
    else:
        candidates.append(os.path.join(_tmp_dir(), "busan_travel.db"))
        candidates.append(":memory:")

    last_err = None
    for path in candidates:
        try:
            if path == ":memory:":
                if _MEM_CONN is None:
                    raw = sqlite3.connect(":memory:", check_same_thread=False)
                    raw.row_factory = sqlite3.Row
                    _MEM_CONN = _SharedConnection(raw)
                _MEM_CONN.execute("SELECT 1;")
                _FALLBACK_PATH = path
                return _MEM_CONN

            conn = sqlite3.connect(path, timeout=10, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            # 先探测"可写"：部分挂载盘能连上但写不进去
            conn.execute("PRAGMA journal_mode=MEMORY;")
            conn.execute("SELECT 1;")
            conn.execute("CREATE TABLE IF NOT EXISTS __probe(a);")
            conn.execute("DROP TABLE __probe;")
            conn.commit()
            if path != config.DB_PATH:
                _FALLBACK_PATH = path
            return conn
        except Exception as e:      # noqa: BLE001
            last_err = e
            try:
                conn.close()
            except Exception:
                pass

    raise RuntimeError(f"无法打开数据库（已尝试 {candidates}）：{last_err}")


def db_path_in_use():
    """当前实际使用的数据库文件路径（后台页面底部展示）。"""
    try:
        conn = get_conn()
        conn.close()
    except Exception:
        return config.DB_PATH
    return _FALLBACK_PATH or config.DB_PATH


# ------------------------------------------------------------------
# 密码工具
# ------------------------------------------------------------------
def hash_password(password: str, salt: str = None):
    """PBKDF2-HMAC-SHA256，返回 "salt$hash"。"""
    if salt is None:
        salt = secrets.token_hex(12)
    h = hashlib.pbkdf2_hmac("sha256", str(password).encode("utf-8"), salt.encode("utf-8"), 60000)
    return f"{salt}${h.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, _ = str(stored).split("$", 1)
    except Exception:
        return False
    return hash_password(password, salt) == stored


# ------------------------------------------------------------------
# 初始化
# ------------------------------------------------------------------
def init_db():
    """建表 + 写入默认管理员 admin/admin。已存在则不会破坏原有数据。"""
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT UNIQUE NOT NULL,
            password    TEXT NOT NULL,
            role        TEXT NOT NULL DEFAULT 'user',   -- user / admin
            created_at  TEXT,
            last_login  TEXT
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS query_logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER,
            username    TEXT,
            category    TEXT,
            group_type  TEXT,
            question    TEXT,
            answer      TEXT,
            sources     TEXT,
            lang        TEXT,
            created_at  TEXT
        );
    """)

    cur.execute("SELECT id FROM users WHERE username=?", (config.DEFAULT_ADMIN,))
    if cur.fetchone() is None:
        cur.execute(
            "INSERT INTO users (username, password, role, created_at) VALUES (?,?,?,?)",
            (config.DEFAULT_ADMIN, hash_password(config.DEFAULT_ADMIN_PWD), "admin", _now()),
        )

    conn.commit()
    conn.close()


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ------------------------------------------------------------------
# 用户操作
# ------------------------------------------------------------------
def user_exists(username) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    conn.close()
    return row is not None


def add_user(username, password, role="user"):
    """注册新用户。返回 (ok: bool, msg_key: str)"""
    if not username or not password:
        return False, "empty_fields"
    if user_exists(username):
        return False, "user_exists"
    try:
        conn = get_conn()
        conn.execute(
            "INSERT INTO users (username, password, role, created_at) VALUES (?,?,?,?)",
            (username, hash_password(password), role, _now()),
        )
        conn.commit()
        conn.close()
        return True, "register_ok"
    except Exception:
        return False, "register_fail"


def get_user(username):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def verify_login(username, password):
    """连接数据库比对信息。返回 (ok, role, msg_key)"""
    user = get_user(username)
    if not user:
        return False, None, "user_not_found"
    if not verify_password(password, user["password"]):
        return False, None, "login_fail"
    try:
        conn = get_conn()
        conn.execute("UPDATE users SET last_login=? WHERE id=?", (_now(), user["id"]))
        conn.commit()
        conn.close()
    except Exception:
        pass
    return True, user["role"], "login_ok"


def list_users():
    """后台管理用：返回全部用户（不返回密码明文，UI 用 ****** 代替）。"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, username, role, created_at, last_login FROM users ORDER BY id ASC")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def set_role(user_id, role):
    if role not in ("user", "admin"):
        return False
    conn = get_conn()
    conn.execute("UPDATE users SET role=? WHERE id=?", (role, user_id))
    conn.commit()
    conn.close()
    return True


def reset_password(user_id, new_pwd=None):
    """重置密码，默认 123456"""
    new_pwd = new_pwd or config.RESET_PASSWORD
    conn = get_conn()
    conn.execute("UPDATE users SET password=? WHERE id=?", (hash_password(new_pwd), user_id))
    conn.commit()
    conn.close()
    return True


def delete_user(user_id):
    conn = get_conn()
    conn.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.execute("DELETE FROM query_logs WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()
    return True


# ------------------------------------------------------------------
# 查询日志（每位用户的详细查询 -> 对应用户数据库）
# ------------------------------------------------------------------
def log_query(user_id, username, category, group_type, question, answer, sources, lang="zh"):
    try:
        conn = get_conn()
        conn.execute(
            """INSERT INTO query_logs
               (user_id, username, category, group_type, question, answer, sources, lang, created_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (user_id, username, category, group_type, question, answer, sources, lang, _now()),
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def get_user_logs(username, limit=50):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM query_logs WHERE username=? ORDER BY id DESC LIMIT ?", (username, limit))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def count_logs_by_user():
    """后台管理用：{username: 查询次数}"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT username, COUNT(*) AS c FROM query_logs GROUP BY username")
    rows = {r["username"]: r["c"] for r in cur.fetchall()}
    conn.close()
    return rows


def get_all_logs(limit=200):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM query_logs ORDER BY id DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


# 首次导入即确保表存在
init_db()