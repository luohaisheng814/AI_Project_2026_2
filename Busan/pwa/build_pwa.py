# -*- coding: utf-8 -*-
"""打包 iOS 可用的网页版安装包（PWA）。

产物：
  Busan/dist/Busan_iOS_WebApp_v29.zip      整站（含图标/manifest/sw），可放到任意 https 主机
  Busan/dist/pwa/Busan_Tour_WebApp_v29/    展开后的同内容目录

说明：iPhone 上的“安装”= Safari 打开 https 页面后“添加到主屏幕”。
iOS 不允许侧载未签名 .ipa，本机也没有 macOS/Xcode，因此网页版是可选路径里唯一
能在 iPhone 上真正落地图标的形态；Busan/ios 工程仍保留，有 Mac 时可出真 ipa。
"""
import os
import shutil
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "android", "assets")
OUT = os.path.join(ROOT, "dist", "pwa", "Busan_Tour_WebApp_v29")
ZIP = os.path.join(ROOT, "dist", "Busan_iOS_WebApp_v29.zip")

READ_ME = """釜山 AI 旅行助手 v2.9 · iPhone / iPad 安装说明
=====================================================

方式一（推荐，1 分钟）：
  1. iPhone 用 Safari 打开：
     https://luohaisheng814.github.io/AI_Project_2026_2/
  2. 点底部“分享” → “添加到主屏幕” → 添加。
  3. 桌面会出现“釜山助手”图标，全屏运行、断网也能查景点与路线。
     （首次打开请联网一次，让离线缓存装好。）

方式二（自己托管）：把本压缩包解压后的文件放到任意支持 https 的静态空间，
  根目录保持 index.html / manifest.webmanifest / sw.js 同级，再按方式一添加。

注意：
  * 这是 PWA（网页应用），不是 App Store 上架包，也不会出现在 App Store。
  * iOS 只允许安装 App Store 或签名企业/描述文件分发出来的 .ipa；本机是 Windows，
    没有 macOS/Xcode，无法编译签名的 .ipa。仓库里的 Busan/ios 工程是给有 Mac 的
    环境出真包用的，前端 assets 与安卓完全同源，版本号同步 2.9。
  * 定位/天气权限：在 iPhone 上首次点“定位”时按系统弹窗允许即可。
"""

SKIP = {"icon_raw.png"}


def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT, exist_ok=True)
    n = 0
    for name in sorted(os.listdir(SRC)):
        if name in SKIP:
            continue
        src = os.path.join(SRC, name)
        dst = os.path.join(OUT, name)
        if os.path.isdir(src):
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
        n += 1
    with open(os.path.join(OUT, "安装说明.txt"), "w", encoding="utf-8") as f:
        f.write(READ_ME)

    if os.path.exists(ZIP):
        os.remove(ZIP)
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
        for base, _dirs, files in os.walk(OUT):
            for fn in files:
                p = os.path.join(base, fn)
                z.write(p, os.path.relpath(p, OUT).replace("\\", "/"))
    print("entries:", n)
    print("dir:", OUT)
    print("zip:", ZIP, os.path.getsize(ZIP), "bytes")
    need = ["index.html", "manifest.webmanifest", "sw.js", "icon-180.png", "icon-192.png", "icon-512.png"]
    missing = [x for x in need if not os.path.exists(os.path.join(OUT, x))]
    print("required missing:", missing if missing else "none")
    print("pwa ok" if not missing else "pwa FAIL")


if __name__ == "__main__":
    main()
