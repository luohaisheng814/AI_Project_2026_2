# -*- coding: utf-8 -*-
"""
build_apk.py —— 用「aapt2 + javac + d8 + zipalign + apksigner」手工流水线构建独立 APK

为什么不用 Gradle：本机没有 Android Studio / Gradle，也不需要联网拉 AGP。
build-tools 34 里已经自带 aapt2 / d8 / zipalign / apksigner，配合 JDK 的 javac 即可完成构建。

用法：
  python apk_build/build_apk.py                # 用现有 assets 构建
  python apk_build/build_apk.py --export       # 先重新导出数据（会调用 LLM 翻译）

环境变量：
  ANDROID_SDK_ROOT / ANDROID_HOME   SDK 目录（默认 D:\\AndroidBuild\\sdk）
  JAVA_HOME                          JDK 目录（默认 D:\\AndroidBuild\\jdk17）
"""
import os
import shutil
import subprocess
import sys
import zipfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANDROID_DIR = os.path.join(BASE, "android")
BUILD_DIR = os.path.join(BASE, "apk_build", "build")
KEYSTORE_DIR = os.path.join(BASE, "apk_build", "keystore")
KEYSTORE = os.path.join(KEYSTORE_DIR, "busan-release.jks")
OUT_APK = os.path.join(BASE, "dist", "Busan旅行助手.apk")

SDK = os.environ.get("ANDROID_SDK_ROOT") or os.environ.get("ANDROID_HOME") or r"D:\AndroidBuild\sdk"
JDK = os.environ.get("JAVA_HOME") or r"D:\AndroidBuild\jdk17"
BUILD_TOOLS = os.path.join(SDK, "build-tools", "34.0.0")
PLATFORM_JAR = os.path.join(SDK, "platforms", "android-34", "android.jar")

KS_PASS = "busan2026"
KS_ALIAS = "busan"

# d8 / apksigner / keytool 都是对 JDK 的封装，必须让子进程能找到 java
os.environ["JAVA_HOME"] = JDK
os.environ["PATH"] = os.path.join(JDK, "bin") + os.pathsep + os.environ.get("PATH", "")
os.environ["ANDROID_SDK_ROOT"] = SDK


def run(cmd, cwd=None, check=True):
    printable = " ".join(f'"{c}"' if " " in str(c) else str(c) for c in cmd)
    print(f"$ {printable}")
    p = subprocess.run(cmd, cwd=cwd)
    if check and p.returncode != 0:
        raise SystemExit(f"命令失败（退出码 {p.returncode}）：{printable}")
    return p.returncode


def need_tools():
    missing = []
    for path in (PLATFORM_JAR,
                 os.path.join(BUILD_TOOLS, "aapt2.exe"),
                 os.path.join(BUILD_TOOLS, "d8.bat"),
                 os.path.join(BUILD_TOOLS, "zipalign.exe"),
                 os.path.join(BUILD_TOOLS, "apksigner.bat"),
                 os.path.join(JDK, "bin", "javac.exe"),
                 os.path.join(JDK, "bin", "keytool.exe")):
        if not os.path.exists(path):
            missing.append(path)
    if missing:
        raise SystemExit("缺少构建工具：\n  " + "\n  ".join(missing) +
                         "\n请先运行 apk_build/setup_toolchain.ps1 装配 JDK 与 Android SDK。")
    os.makedirs(os.path.join(BUILD_DIR, "gen"), exist_ok=True)
    os.makedirs(os.path.join(BUILD_DIR, "classes"), exist_ok=True)
    os.makedirs(os.path.join(BUILD_DIR, "dex"), exist_ok=True)
    os.makedirs(KEYSTORE_DIR, exist_ok=True)
    os.makedirs(os.path.join(BASE, "dist"), exist_ok=True)


def ensure_keystore():
    """首次构建生成签名证书；之后复用，保证同一台机器上的升级安装可覆盖。"""
    if os.path.exists(KEYSTORE):
        return
    run([os.path.join(JDK, "bin", "keytool.exe"), "-genkeypair", "-v",
         "-keystore", KEYSTORE, "-alias", KS_ALIAS,
         "-keyalg", "RSA", "-keysize", "2048", "-validity", "10000",
         "-storepass", KS_PASS, "-keypass", KS_PASS,
         "-dname", "CN=Busan Travel Assistant, OU=Local, O=Busan, L=Busan, C=KR"])


def clean():
    for sub in ("gen", "classes", "dex"):
        p = os.path.join(BUILD_DIR, sub)
        if os.path.isdir(p):
            shutil.rmtree(p)
        os.makedirs(p, exist_ok=True)
    for name in ("res.flata", "base.apk", "aligned.apk"):
        p = os.path.join(BUILD_DIR, name)
        if os.path.exists(p):
            os.remove(p)


def build():
    if "--export" in sys.argv:
        run([sys.executable, os.path.join(BASE, "apk_build", "export_assets.py")])

    need_tools()
    clean()
    ensure_keystore()

    assets = os.path.join(ANDROID_DIR, "assets")
    for f in ("index.html", "app.js", "data.js", "cloud.js", "cloud_snapshot.json", "cloud_snapshot.js"):
        if not os.path.exists(os.path.join(assets, f)):
            raise SystemExit(f"assets 缺少 {f}，先运行 cloud_build.py / export_assets.py")

    # ① 编译资源
    run([os.path.join(BUILD_TOOLS, "aapt2.exe"), "compile", "--dir",
         os.path.join(ANDROID_DIR, "res"), "-o", os.path.join(BUILD_DIR, "res.flata")])

    # ② 链接资源并打包 assets，生成 R.java
    run([os.path.join(BUILD_TOOLS, "aapt2.exe"), "link",
         "-o", os.path.join(BUILD_DIR, "base.apk"),
         "-I", PLATFORM_JAR,
         "--manifest", os.path.join(ANDROID_DIR, "AndroidManifest.xml"),
         "-R", os.path.join(BUILD_DIR, "res.flata"),
         "-A", assets,
         "--java", os.path.join(BUILD_DIR, "gen"),
         "--min-sdk-version", "21",
         "--target-sdk-version", "34",
         "--auto-add-overlay"])

    # ③ 编译 Java
    java_files = [os.path.join(BUILD_DIR, "gen", "com", "busan", "tour", "R.java"),
                  os.path.join(ANDROID_DIR, "java", "com", "busan", "tour", "MainActivity.java")]
    run([os.path.join(JDK, "bin", "javac.exe"), "-source", "8", "-target", "8",
         "-encoding", "UTF-8", "-classpath", PLATFORM_JAR,
         "-d", os.path.join(BUILD_DIR, "classes")] + java_files)

    # ④ 转 dex（必须收集全部 class：WebViewClient / WebChromeClient 等匿名内部类
    #    会编译成 MainActivity$1.class，只传 MainActivity.class 会在真机上
    #    抛 ClassNotFoundException: com.busan.tour.MainActivity$1 而闪退）
    class_files = []
    for root, _dirs, files in os.walk(os.path.join(BUILD_DIR, "classes")):
        for f in files:
            if f.endswith(".class"):
                class_files.append(os.path.join(root, f))
    if not class_files:
        raise SystemExit("javac 未产出 class 文件")
    run([os.path.join(BUILD_TOOLS, "d8.bat"), "--lib", PLATFORM_JAR, "--min-api", "21",
         "--output", os.path.join(BUILD_DIR, "dex")] + class_files,
        cwd=BUILD_TOOLS)

    dex_src = os.path.join(BUILD_DIR, "dex", "classes.dex")
    if not os.path.exists(dex_src):
        raise SystemExit("d8 未产出 classes.dex")
    with zipfile.ZipFile(os.path.join(BUILD_DIR, "base.apk"), "a", zipfile.ZIP_DEFLATED) as z:
        z.write(dex_src, "classes.dex")

    # ⑤ 4 字节对齐 + 签名
    run([os.path.join(BUILD_TOOLS, "zipalign.exe"), "-f", "-p", "4",
         os.path.join(BUILD_DIR, "base.apk"), os.path.join(BUILD_DIR, "aligned.apk")])

    run([os.path.join(BUILD_TOOLS, "apksigner.bat"), "sign",
         "--ks", KEYSTORE, "--ks-pass", "pass:" + KS_PASS,
         "--ks-key-alias", KS_ALIAS, "--key-pass", "pass:" + KS_PASS,
         "--v1-signing-enabled", "true", "--v2-signing-enabled", "true",
         "--out", OUT_APK, os.path.join(BUILD_DIR, "aligned.apk")],
        cwd=BUILD_TOOLS)

    run([os.path.join(BUILD_TOOLS, "apksigner.bat"), "verify", "--print-certs", OUT_APK],
        cwd=BUILD_TOOLS)

    with zipfile.ZipFile(OUT_APK) as z:
        names = z.namelist()
        for must in ("classes.dex", "assets/index.html", "assets/app.js", "assets/data.js",
                     "assets/cloud.js", "assets/cloud_snapshot.json", "assets/cloud_snapshot.js"):
            if must not in names:
                raise SystemExit(f"APK 缺少 {must}")

    # 确认 dex 里真的包含每一个 class（含匿名内部类），避免装到手机上才闪退
    dexdump = os.path.join(BUILD_TOOLS, "dexdump.exe")
    if os.path.exists(dexdump):
        out = subprocess.run([dexdump, "-f", dex_src], capture_output=True, text=True,
                             encoding="utf-8", errors="replace").stdout
        for cf in class_files:
            rel = os.path.relpath(cf, os.path.join(BUILD_DIR, "classes"))[:-6]
            descriptor = "L" + rel.replace("\\", "/") + ";"
            if descriptor not in out:
                raise SystemExit(f"dex 缺少类 {descriptor}（d8 传入的 class 列表不完整）")

    size = os.path.getsize(OUT_APK)
    print(f"\n构建完成：{OUT_APK}\n体积：{size / 1024:.1f} KB")


if __name__ == "__main__":
    build()
