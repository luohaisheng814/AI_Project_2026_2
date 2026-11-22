#!/usr/bin/env bash
# 在 macOS 上生成 Xcode 工程并打出未签名 ipa（无需 Apple 开发者账号即可产出包体；
# 真机安装仍需签名：Xcode 免费签名 / AltStore / 企业证书）。
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v xcodegen >/dev/null 2>&1; then
  echo "未找到 xcodegen，尝试用 Homebrew 安装…"
  brew install xcodegen
fi

xcodegen generate

xcodebuild \
  -project BusanTour.xcodeproj \
  -scheme BusanTour \
  -configuration Release \
  -sdk iphoneos \
  -derivedDataPath build/DerivedData \
  CODE_SIGNING_ALLOWED=NO \
  CODE_SIGNING_REQUIRED=NO \
  CODE_SIGN_IDENTITY="" \
  build

APP="build/DerivedData/Build/Products/Release-iphoneos/BusanTour.app"
if [ ! -d "$APP" ]; then
  echo "构建产物不存在：$APP"
  exit 1
fi

rm -rf build/Payload
mkdir -p build/Payload
cp -R "$APP" build/Payload/
(
  cd build
  rm -f "Busan旅行助手-unsigned.ipa"
  zip -qr "Busan旅行助手-unsigned.ipa" Payload
)
echo "完成：$(pwd)/build/Busan旅行助手-unsigned.ipa"
echo "安装说明：未签名包不能直接双击安装。用 Xcode 打开工程选真机运行（免费账号 7 天有效），或用 AltStore / Sideloadly 自签。"
