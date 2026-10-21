# -*- coding: utf-8 -*-

import os
import sys

# ------------------------------------------------------------------
# 基础路径
# ------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DOCS_DIR = os.path.join(BASE_DIR, "docs")                     # 核心数据库（rules.txt + 重点景点档案）
ACTIVITY_DIR = os.path.join(BASE_DIR, "activity_classified")  # 四大玩法分类数据库
DATA_DIR = os.path.join(BASE_DIR, "data")                     # 其它数据（预留）
LOG_DIR = os.path.join(BASE_DIR, "logs")

for _d in (DOCS_DIR, ACTIVITY_DIR, DATA_DIR, LOG_DIR):
    os.makedirs(_d, exist_ok=True)

# DB_PATH 见下方「环境变量」段（支持 BUSAN_DB_PATH 覆盖）

# ------------------------------------------------------------------
# 四大玩法分类（文件夹名 -> 排序号）
# 文件夹名与你本地 activity_classified 中的目录名保持一致
# ------------------------------------------------------------------
CATEGORIES = [
    "01_艺术村落_文化街区",
    "02_海岸休闲_日落夜景",
    "03_湿地生态_自然观景",
    "04_小众渔港_文艺拍照",
]

# 重点景点档案（命中 01 / 02 时会额外走"本地库 -> 核心库 -> 官网/百科在线查询"三步）
SPOT_PROFILES = {
    "01_艺术村落_文化街区": {
        "file": os.path.join(DOCS_DIR, "gamcheon.txt"),
        "names": ["甘川文化村", "甘川洞文化村", "감천문화마을", "Gamcheon Culture Village"],
    },
    "02_海岸休闲_日落夜景": {
        "file": os.path.join(DOCS_DIR, "dadaepo.txt"),
        "names": ["多大浦海水浴场", "多大浦", "多大浦梦之夕阳喷泉", "다대포해수욕장", "Dadaepo Beach"],
    },
}

RULES_FILE = os.path.join(DOCS_DIR, "rules.txt")

# ------------------------------------------------------------------
# 环境变量（.env）
# ------------------------------------------------------------------
def _load_env():
    """极简 .env 解析器：不依赖 python-dotenv，键不存在时回退到真实环境变量。"""
    env = dict(os.environ)
    path = os.path.join(BASE_DIR, ".env")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip().strip('"').strip("'")
        except Exception:
            pass
    return env


ENV = _load_env()

# 数据库文件路径（可用环境变量 BUSAN_DB_PATH 覆盖）
DB_PATH = ENV.get("BUSAN_DB_PATH") or os.path.join(BASE_DIR, "busan_travel.db")


def env_get(key, default=""):
    return ENV.get(key, default)


# ------------------------------------------------------------------
# LLM 配置（OpenAI 兼容协议）
# 兼容两套变量名，你原有的 .env 不用改：
#   通义千问 DashScope：DASHCOPE_API_KEY / DASHCOPE_BASE_URL
#   通用写法          ：LLM_API_KEY      / LLM_BASE_URL
# ------------------------------------------------------------------
DASHSCOPE_COMPAT_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

_env_key = env_get("DASHCOPE_API_KEY", "") or env_get("LLM_API_KEY", "")
_env_url = env_get("DASHCOPE_BASE_URL", "") or env_get("LLM_BASE_URL", "")
_env_model = env_get("LLM_MODEL", "")

USING_DASHSCOPE = bool(env_get("DASHCOPE_API_KEY", "")) or "dashscope" in _env_url.lower()

# 地址：通义旧版 /api/v1 不是 OpenAI 兼容端点，自动换成 compatible-mode/v1
if _env_url:
    if "dashscope" in _env_url.lower() and "compatible-mode" not in _env_url.lower():
        _env_url = DASHSCOPE_COMPAT_URL
elif USING_DASHSCOPE:
    _env_url = DASHSCOPE_COMPAT_URL

LLM_API_KEY = _env_key
LLM_BASE_URL = _env_url or "https://api.openai.com/v1"
LLM_MODEL = _env_model or ("qwen-plus" if USING_DASHSCOPE else "gpt-4o-mini")
LLM_TIMEOUT = int(env_get("LLM_TIMEOUT", "60") or 60)
LLM_TEMPERATURE = float(env_get("LLM_TEMPERATURE", "0.3") or 0.3)

# 是否在重点景点问答时联网抓取官网 / 百科（1 开启，0 关闭）
ENABLE_WEB_LOOKUP = env_get("ENABLE_WEB_LOOKUP", "1") not in ("0", "false", "False", "")
WEB_TIMEOUT = int(env_get("WEB_TIMEOUT", "8") or 8)

# 默认管理员账号
DEFAULT_ADMIN = env_get("DEFAULT_ADMIN", "admin")
DEFAULT_ADMIN_PWD = env_get("DEFAULT_ADMIN_PWD", "admin")
RESET_PASSWORD = env_get("RESET_PASSWORD", "123456")

# ------------------------------------------------------------------
# 默认语言：zh / ko / en
# ------------------------------------------------------------------
DEFAULT_LANG = env_get("DEFAULT_LANG", "zh")
SUPPORTED_LANGS = ["zh", "ko", "en"]

# 回答语言取值策略（配合 lang_detect.py）：
#   question（默认）：以用户提问语言为准，识别不出才用界面语言
#   ui           ：始终跟随界面右上角切换按钮的语言
ANSWER_LANG_MODE = env_get("ANSWER_LANG_MODE", "question")

# ------------------------------------------------------------------
# 人数分组（内部 key，显示名由 i18n 负责翻译）
# ------------------------------------------------------------------
GROUP_TYPES = [
    "solo_male",
    "solo_female",
    "two_mf",
    "two_mm",
    "two_ff",
    "group_3plus",
]


def ensure_runtime():
    """把项目根目录加入 sys.path，保证各模块可独立运行。"""
    if BASE_DIR not in sys.path:
        sys.path.insert(0, BASE_DIR)
    return BASE_DIR