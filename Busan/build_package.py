# -*- coding: utf-8 -*-
"""
build_package.py —— 把手机版运行时打包成可分发的安装压缩包 Busan_Tour_App.zip

产物：
  dist/Busan_Tour_App.zip
    └── Busan_Tour_App/
          ├── start_windows.bat      Windows 一键启动（自动建 venv、装依赖、起服务、开浏览器）
          ├── start.sh               macOS / Linux 一键启动
          ├── README.txt              使用说明（手机访问 / 离线缓存 / 安装到主屏）
          ├── requirements.txt
          ├── mobile_app.py          手机版服务端
          ├── mobile/index.html       手机版 H5 页面
          ├── 运行所需 .py 模块
          ├── docs/                  核心数据库与重点档案
          └── activity_classified/   四大玩法分类数据库

排除：.env（密钥）、*.db、__pycache__、logs、ppt_work、.lark-slides、日志、测试脚本、PPTX。
用法：
  python build_package.py            # 生成 dist/Busan_Tour_App.zip
"""
import os
import sys
import zipfile

import config

BASE_DIR = config.BASE_DIR
DIST_DIR = os.path.join(BASE_DIR, "dist")
PKG_NAME = "Busan_Tour_App"
ZIP_PATH = os.path.join(DIST_DIR, f"{PKG_NAME}.zip")

# 手机版服务端直接/间接依赖的 Python 模块（不含登录、桌面、后台管理链路）
REQUIRED_MODULES = [
    "mobile_app.py",
    "rag_core.py",
    "official_sites.py",
    "recommend.py",
    "intent_parser.py",
    "lang_detect.py",
    "config.py",
    "i18n.py",
    "core_api.py",
    "web_lookup.py",
    "db_config.py",
]

# 需要整目录打包的数据
DATA_DIRS = ["docs", "activity_classified", "mobile"]

EXCLUDE_DIRS = {"__pycache__", "dist", "logs", "ppt_work", ".lark-slides", ".git", ".venv"}
EXCLUDE_EXT = {".db", ".log", ".pyc", ".pptx", ".zip"}
EXCLUDE_FILES = {".env", "test_scope.py", "test_lang_policy.py", "test_mobile_api.py",
                "run_logic.html", "run_logic.png", "mobile_run_logic.html", "mobile_run_logic.png"}

BAT_LAUNCHER = """@echo off
chcp 65001 >nul
title Busan AI Tour App
cd /d "%~dp0"

echo ============================================
echo   Busan AI 旅行助手 · 手机版一键启动
echo ============================================

where python >nul 2>nul
if errorlevel 1 (
  echo [错误] 未检测到 Python，请先安装 Python 3.9+ 并勾选 Add to PATH。
  pause
  exit /b 1
)

if not exist ".venv" (
  echo [1/3] 正在创建虚拟环境 .venv ...
  python -m venv .venv
)

call ".venv\\Scripts\\activate.bat"

echo [2/3] 正在安装依赖（首次运行需要联网）...
python -m pip install --upgrade pip
pip install -r requirements.txt

echo [3/3] 正在启动手机版服务...
echo 手机与电脑连同一 Wi-Fi，浏览器访问命令行里显示的地址即可。
echo 本窗口保持打开；关闭窗口即停止服务。
start "" http://127.0.0.1:8000/
python mobile_app.py 8000
pause
"""

SH_LAUNCHER = """#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
echo "============================================"
echo "  Busan AI 旅行助手 · 手机版一键启动"
echo "============================================"

if ! command -v python3 >/dev/null 2>&1; then
  echo "[错误] 未检测到 python3，请先安装 Python 3.9+。"; exit 1
fi

if [ ! -d ".venv" ]; then
  echo "[1/3] 创建虚拟环境 .venv ..."
  python3 -m venv .venv
fi

source .venv/bin/activate
echo "[2/3] 安装依赖（首次运行需要联网）..."
pip install --upgrade pip
pip install -r requirements.txt

echo "[3/3] 启动手机版服务 ..."
echo "手机与电脑连同一 Wi-Fi，浏览器访问终端里显示的地址。"
python3 mobile_app.py 8000
"""

README = """Busan AI 旅行助手 · 手机版安装包
======================================

一、包内容
  mobile_app.py            手机版服务端（登录 / 问答 / 附近景点 / 安装包下载）
  mobile/index.html        手机版 H5 页面（聊天、登录、三语、定位、分类与人数选择栏）
  rag_core.py              检索 + 生成（本地资料库 + 景点官网双源）
  official_sites.py        8 个景点的官方入口登记、正文抓取与 10 分钟缓存
  db_config.py             用户库与问答日志（与本项目桌面版 / 网页版共用一套表结构）
  docs/                    核心数据库 rules.txt 与重点景点档案
  activity_classified/     四大玩法分类数据库（01 艺术村落 / 02 海岸日落 / 03 湿地生态 / 04 小众渔港）
  requirements.txt         Python 依赖清单
  start_windows.bat        Windows 一键启动
  start.sh                 macOS / Linux 一键启动

二、在电脑上启动（同一 Wi-Fi 下供手机访问）
  Windows：双击 start_windows.bat
  macOS / Linux：在终端执行 bash start.sh
  启动后终端会打印：
    本机访问： http://127.0.0.1:8000/
    手机访问： http://<电脑局域网IP>:8000/
  手机浏览器打开「手机访问」地址即可使用。

三、账号与联网
  · 首次启动会在包目录生成 busan_travel.db，自动创建默认管理员 admin / admin；
  · 顶部「登录」按钮文案随 中文 / 한국어 / EN 切换，登录后按钮变「退出」；
  · 未登录：只查本地资料库，不抓官网、不调用大模型；
  · 已登录：同时检索各景点官方网站与本地资料库，再由大模型生成答案；
  · 账号与问答日志写在与桌面版、网页版共用的同一套表结构，
    把同一份 busan_travel.db 放到包目录即可延续原有账号。

四、把应用放到手机上
  1) 在线使用：手机浏览器打开上面的地址 → 浏览器菜单选「添加到主屏幕」，
     桌面会生成图标，点开即以独立窗口打开（Service Worker 缓存图标与离线回退页）。
  2) 安装包分发：本 zip 即完整应用压缩包，可传到手机留存备份；
     手机端页面底部「安装包」按钮可直接从服务端下载本压缩包。
  说明：纯网页应用无需在手机上单独安装 APK；问答与景点数据由服务端提供。

五、附近景点与地图 App
  · 点「附近景点」调用手机浏览器定位，服务端按直线距离排序返回最近景点；
  · 每张卡片四个按钮：NAVER 导航（nmap://route/public，以当前位置为起点）、
    NAVER 地点（nmap://place，坐标直给）、网页地图、Google 路线；
  · 装了 NAVER 地图时手机可直接唤起 App 精准导航；
  · 浏览器定位需要 HTTPS 或 localhost；局域网 HTTP 下若拿不到坐标，
    可用 http://<IP>:端口/?lat=35.0972&lng=128.9769 直接按坐标预览附近景点。

六、玩法分类与数据规则
  · 顶部选择玩法后，仅加载该玩法文件夹作为当前唯一主数据源；
  · 切换玩法会立即重载对应分类库并重算结果；
  · 其它玩法的景点只出现在回答末尾「其它玩法补充推荐」中，限量 2 个，
    并标注所属玩法与推荐理由，排在主推荐之后。

七、语言规则（中文 / 한국어 / English）
  · 回答语言只由顶部语言按钮决定，与提问语言、数据来源无关；
  · 无论按钮是哪种语言，后端一律先用中文检索中文数据库、生成中文草稿，
    按钮为中文时跳过翻译；按钮为韩文 / 英文时再把中文草稿整体翻译后输出；
  · 翻译只换语言不换内容：事实数据、条目数量、推荐顺序、Markdown 结构保持不变；
  · 切换语言后会按新按钮语言重新生成全部历史回答，而不是回放旧语言文本。

八、回答形态
  · 只输入景点名（如「甘川文化村」）时给精简回答：一句话定位 + 2–3 个亮点 +
    交通一句 + 门票/开放一句，200 字以内；
  · 指定字段（交通 / 门票 / 开放时间 / 拍照 / 美食 …）时按字段作答；
  · 答案后附「资料来源」（本地档案 / 规则库 / 景点官网）与「你可能还想问」。

九、常见问题
  · 首次启动慢：首次会创建虚拟环境并安装依赖，之后启动会很快。
  · 未配置 LLM_API_KEY（Busan/.env 或环境变量）时为本地检索直出模式，
    回答为中文资料库原文，仍可完整演示问答链路。
  · 服务重启后需重新登录（登录态保存在服务进程内存与会话 Cookie 中）。
"""


def _should_skip_file(name):
    if name in EXCLUDE_FILES:
        return True
    ext = os.path.splitext(name)[1].lower()
    return ext in EXCLUDE_EXT


def collect_files():
    """返回 [(zip_arcname, local_abs_path), ...]。"""
    files = []

    for mod in REQUIRED_MODULES:
        p = os.path.join(BASE_DIR, mod)
        if os.path.exists(p):
            files.append((f"{PKG_NAME}/{mod}", p))

    for d in DATA_DIRS:
        root = os.path.join(BASE_DIR, d)
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [x for x in dirnames if x not in EXCLUDE_DIRS]
            for fn in filenames:
                if _should_skip_file(fn):
                    continue
                local = os.path.join(dirpath, fn)
                arc = os.path.join(PKG_NAME, os.path.relpath(local, BASE_DIR))
                files.append((arc.replace("\\", "/"), local))
    return files


def main():
    os.makedirs(DIST_DIR, exist_ok=True)
    files = collect_files()

    # 清单内补充启动器 / README / requirements
    extra = {
        f"{PKG_NAME}/start_windows.bat": BAT_LAUNCHER,
        f"{PKG_NAME}/start.sh": SH_LAUNCHER,
        f"{PKG_NAME}/README.txt": README,
    }
    req_src = os.path.join(BASE_DIR, "requirements.txt")
    if os.path.exists(req_src):
        extra[f"{PKG_NAME}/requirements.txt"] = open(req_src, encoding="utf-8").read()

    if os.path.exists(ZIP_PATH):
        os.remove(ZIP_PATH)

    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for arc, local in files:
            zf.write(local, arc)
        for arc, content in extra.items():
            zf.writestr(arc, content)

    size_kb = os.path.getsize(ZIP_PATH) / 1024
    print(f"打包完成：{ZIP_PATH}")
    print(f"  包含 {len(files)} 个运行/数据文件 + {len(extra)} 个启动说明文件")
    print(f"  压缩包大小：{size_kb:.1f} KB")


if __name__ == "__main__":
    main()
