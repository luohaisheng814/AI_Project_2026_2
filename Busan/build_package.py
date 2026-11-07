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
    "cloud_build.py",
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

README = """Busan AI 旅行助手 · v1.4（手机直装版）

一、最快用法：直接装 APK
  1) 把 Busan旅行助手.apk 传到手机（微信 / 数据线 / 网盘都行）；
  2) 手机上点开安装，允许「安装未知来源应用」；
  3) 打开 App 即可用，不需要电脑、不需要填任何服务器地址。

二、联网与离线的分界
  · 只看手机本身：① 系统是否允许本 App 访问当前网络；② 当前网络是否真的能出网。
    两条都满足才算「联网」，否则一律走离线；
  · 联网：回答来自云端数据库（GitHub 上的 spots.json）+ 各景点官方网站；
    云端库取不到时也会自动落到包内快照，并在顶部说明原因；
  · 离线：用安装包里自带的 cloud_snapshot（同一份数据），附近景点、距离、
    NAVER 导航链接照常可用；
  · 全程不依赖任何一台电脑，也不需要手机和电脑在同一个 Wi-Fi。

三、回答里有什么
  · 只输入景点名：一句话定位 + 最多 3 条概览 + 2 条看点 + 一句追问提示；
  · 问交通 / 门票 / 开放时间 / 拍照点：按字段给 3–5 条要点，不整段复制资料；
  · 联网时额外给「官网核对」区块：官网原文（多为韩文）+ 抓取时间 + 官网链接；
    抓不到就写「未取到正文」，不假装读过；
  · 每条回答下方标来源：云端库 + 更新日期，或包内数据（离线）。

四、语言
  · 顶部 中文 / 한국어 / English 三个按钮决定回答语言，与提问语言无关；
  · 切换后历史回答会按新语言重排，事实、条目、顺序都不变；
  · 地名用当地惯用译名，没有通用译名时保留原名。

五、附近景点与地图
  · 点「附近」会请求定位；授予后按直线距离排序，最近的标「推荐」；
  · 每张卡四个按钮：NAVER 导航、NAVER 地点、网页地图、Google 路线；
  · 定位被拒或超时时，会给 3 个已收录景点当起点，点一下就算距离。

六、包里还有什么
  Busan旅行助手.apk        Android 安装包（v1.4，versionCode 5）
  mobile/cloud/spots.json  云端数据库（与 App 内快照同内容）
  cloud_build.py           由 docs 数据重新生成云端库的脚本
  docs/                    核心资料库与重点景点档案
  activity_classified/     四大玩法分类数据
  mobile_app.py 等         旧网页版服务端（需要电脑，已不推荐，仅留作对照）

七、旧网页版（可选，需要电脑）
  Windows 双击 start_windows.bat，macOS / Linux 执行 bash start.sh，
  终端会打印 http://<电脑IP>:8000/，手机与电脑同一 Wi-Fi 时可用浏览器打开。
  这条链路属于 v1.2 方案，和上面的 APK 是两套东西；日常请直接用 APK。

八、已知限制
  · App 内没有大模型成稿，联网回答是「云端库字段 + 官网上文摘要」的规则组装；
  · 官网只覆盖已登记 mId 的景点（沙下区 8 条 + 甘川官网）；
  · 云端库走 GitHub raw，被墙或断网时只能落包内快照；
  · 没云台观景台坐标未精校，距离只当量级参考；
  · 仅在模拟器验证过，真机厂商 ROM 对「网络已验证」的判定可能不同。
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
    apk = os.path.join(DIST_DIR, "Busan旅行助手.apk")
    if os.path.exists(apk):
        files.append((f"{PKG_NAME}/Busan旅行助手.apk", apk))

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
