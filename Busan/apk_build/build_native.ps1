# 构建 arm64 端侧推理库（llama.cpp JNI）
# 依赖：NDK 26.1.10909125、CMake、Ninja（PyPI 版即可）
$ErrorCode = 0
$Root = Split-Path -Parent $PSScriptRoot
$Native = Join-Path $Root "android\native"
$Build = Join-Path $Native "build-arm64"
$Llama = Join-Path (Split-Path -Parent $Root) "third_party\llama.cpp"
$SDK = if ($env:ANDROID_SDK_ROOT) { $env:ANDROID_SDK_ROOT } else { "D:\AndroidBuild\sdk" }
$NDK = Join-Path $SDK "ndk\26.1.10909125"
$CMake = (Get-Command cmake -ErrorAction SilentlyContinue).Source
$Ninja = (Get-Command ninja -ErrorAction SilentlyContinue).Source

if (-not $CMake) { $CMake = "C:\Users\43763\AppData\Local\Doubao\User Data\sandbox_runtime\bases\fa694f517e5995233c80a9a8db5212c2\python\Scripts\cmake.EXE" }
if (-not $Ninja) { $Ninja = "C:\Users\43763\AppData\Local\Doubao\User Data\sandbox_runtime\bases\fa694f517e5995233c80a9a8db5212c2\python\Scripts\ninja.EXE" }

if (-not (Test-Path -LiteralPath (Join-Path $Llama "CMakeLists.txt"))) {
  Write-Host "third_party/llama.cpp 不存在，正在浅克隆…"
  & "C:\Program Files\Git\cmd\git.exe" clone --depth 1 https://github.com/ggml-org/llama.cpp $Llama
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

& $CMake -S $Native -B $Build -G Ninja `
  "-DCMAKE_TOOLCHAIN_FILE=$NDK/build/cmake/android.toolchain.cmake" `
  -DANDROID_ABI=arm64-v8a -DANDROID_PLATFORM=android-23 -DCMAKE_BUILD_TYPE=Release `
  "-DCMAKE_MAKE_PROGRAM=$Ninja"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $CMake --build $Build --target busanllm -j 4
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$Strip = Join-Path $NDK "toolchains\llvm\prebuilt\windows-x86_64\bin\llvm-strip.exe"
Get-ChildItem -LiteralPath (Join-Path $Build "bin") -Filter "*.so" | ForEach-Object { & $Strip --strip-unneeded $_.FullName }
& $Strip --strip-unneeded (Join-Path $Build "libbusanllm.so")
exit $LASTEXITCODE
