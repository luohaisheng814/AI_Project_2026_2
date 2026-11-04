# setup_toolchain.ps1 —— 在没有 Android Studio / Gradle 的 Windows 上装配 APK 构建工具链
#
# 只用官方下载源，装在非系统盘（默认 D:\AndroidBuild），不动系统环境变量：
#   1) Adoptium Temurin JDK 17（提供 javac / keytool）
#   2) Android commandline-tools（提供 sdkmanager）
#   3) platforms;android-34、build-tools;34.0.0、platform-tools
#
# 用法（PowerShell）：
#   powershell -ExecutionPolicy Bypass -File Busan\apk_build\setup_toolchain.ps1
#   powershell -ExecutionPolicy Bypass -File Busan\apk_build\setup_toolchain.ps1 -Root "E:\AndroidBuild"
#
# 装完直接跑：python Busan\apk_build\build_apk.py

param(
    [string]$Root = "D:\AndroidBuild"
)

$ErrorActionPreference = "Stop"
$dl = Join-Path $Root "dl"
$jdk = Join-Path $Root "jdk17"
$sdk = Join-Path $Root "sdk"
foreach ($d in @($Root, $dl, $sdk)) {
    if (-not (Test-Path -LiteralPath $d)) { New-Item -ItemType Directory -Path $d | Out-Null }
}

# ① JDK 17
if (-not (Test-Path -LiteralPath (Join-Path $jdk "bin\javac.exe"))) {
    $jdkZip = Join-Path $dl "jdk17.zip"
    if (-not (Test-Path -LiteralPath $jdkZip)) {
        Write-Host "下载 JDK 17 ..."
        & curl.exe -L --retry 3 -o $jdkZip "https://api.adoptium.net/v3/binary/latest/17/ga/windows/x64/jdk/hotspot/normal/eclipse?project=jdk"
        if ($LASTEXITCODE -ne 0) { throw "JDK 下载失败" }
    }
    Write-Host "解压 JDK ..."
    $tmp = Join-Path $Root "_jdk_tmp"
    if (Test-Path -LiteralPath $tmp) { Remove-Item -LiteralPath $tmp -Recurse -Force }
    Expand-Archive -LiteralPath $jdkZip -DestinationPath $tmp -Force
    $inner = Get-ChildItem -LiteralPath $tmp -Directory | Select-Object -First 1
    Move-Item -LiteralPath $inner.FullName -Destination $jdk -Force
    Remove-Item -LiteralPath $tmp -Recurse -Force
}

# ② commandline-tools
$sdkmanager = Join-Path $sdk "cmdline-tools\latest\bin\sdkmanager.bat"
if (-not (Test-Path -LiteralPath $sdkmanager)) {
    $cmdZip = Join-Path $dl "cmdline-tools.zip"
    if (-not (Test-Path -LiteralPath $cmdZip)) {
        Write-Host "下载 commandline-tools ..."
        & curl.exe -L --retry 3 -o $cmdZip "https://dl.google.com/android/repository/commandlinetools-win-11076708_latest.zip"
        if ($LASTEXITCODE -ne 0) { throw "commandline-tools 下载失败" }
    }
    Write-Host "解压 commandline-tools ..."
    $tmp = Join-Path $Root "_cmd_tmp"
    if (Test-Path -LiteralPath $tmp) { Remove-Item -LiteralPath $tmp -Recurse -Force }
    Expand-Archive -LiteralPath $cmdZip -DestinationPath $tmp -Force
    $latest = Join-Path $sdk "cmdline-tools\latest"
    if (-not (Test-Path -LiteralPath $latest)) { New-Item -ItemType Directory -Path $latest -Force | Out-Null }
    Move-Item -LiteralPath (Join-Path $tmp "cmdline-tools\*") -Destination $latest -Force
    Remove-Item -LiteralPath $tmp -Recurse -Force
}

# ③ SDK 包（license 需先接受，否则静默装不上）
$env:JAVA_HOME = $jdk
$env:ANDROID_SDK_ROOT = $sdk
Write-Host "接受 SDK licenses ..."
$yes = ("y`n" * 40)
$yes | & $sdkmanager --sdk_root=$sdk --licenses | Out-Null

Write-Host "安装 platform-tools / android-34 / build-tools 34.0.0 ..."
& $sdkmanager --sdk_root=$sdk "platform-tools" "platforms;android-34" "build-tools;34.0.0"

# ④ 校验
$checks = @(
    (Join-Path $sdk "platforms\android-34\android.jar"),
    (Join-Path $sdk "build-tools\34.0.0\aapt2.exe"),
    (Join-Path $sdk "build-tools\34.0.0\zipalign.exe"),
    (Join-Path $sdk "build-tools\34.0.0\apksigner.bat"),
    (Join-Path $sdk "platform-tools\adb.exe"),
    (Join-Path $jdk "bin\javac.exe")
)
foreach ($c in $checks) {
    if (Test-Path -LiteralPath $c) { Write-Host "OK  $c" } else { throw "缺失：$c" }
}

Write-Host ""
Write-Host "工具链就绪。构建时如未设置环境变量，脚本默认使用 $jdk 与 $sdk："
Write-Host "    python Busan\apk_build\build_apk.py"
