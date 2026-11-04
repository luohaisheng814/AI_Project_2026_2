# -*- coding: utf-8 -*-
"""gen_res.py —— 生成安装包图标与 res/values/strings.xml（避免手工维护二进制资源）"""
import os
from PIL import Image, ImageDraw

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(BASE, "android", "res")

DPI = {"mdpi": 48, "hdpi": 72, "xhdpi": 96, "xxhdpi": 144, "xxxhdpi": 192}


def icon(size):
    s = size * 4  # 先画 4 倍再缩小，边缘更干净
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # 渐变海蓝底（逐行填充）
    for y in range(s):
        t = y / (s - 1)
        r = int(15 + (10 - 15) * t)
        g = int(110 + (78 - 110) * t)
        b = int(140 + (99 - 140) * t)
        d.line([(0, y), (s, y)], fill=(r, g, b, 255))

    # 圆角遮罩
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, s - 1, s - 1], radius=int(s * 0.22), fill=255)
    img.putalpha(mask)

    # 白色落日圆
    d.ellipse([s * 0.52, s * 0.20, s * 0.86, s * 0.54], fill=(255, 246, 230, 255))

    # 两道海浪
    import math
    for i, y in enumerate((0.62, 0.74, 0.86)):
        amp = s * 0.035
        pts = []
        for x in range(0, s + 1, max(1, s // 40)):
            pts.append((x, s * y + amp * math.sin((x / s) * 6.28 * (1 + i * 0.4))))
        d.line(pts, fill=(255, 255, 255, 235), width=max(2, int(s * 0.022)))

    # 灯塔剪影（左）
    lx = s * 0.20
    d.polygon([(lx - s * 0.05, s * 0.78), (lx + s * 0.05, s * 0.78),
               (lx + s * 0.03, s * 0.40), (lx - s * 0.03, s * 0.40)], fill=(255, 255, 255, 255))
    d.rectangle([lx - s * 0.045, s * 0.355, lx + s * 0.045, s * 0.395], fill=(255, 246, 230, 255))

    return img.resize((size, size), Image.LANCZOS)


def main():
    for dpi, size in DPI.items():
        folder = os.path.join(RES, f"mipmap-{dpi}")
        os.makedirs(folder, exist_ok=True)
        icon(size).save(os.path.join(folder, "ic_launcher.png"))

    values = os.path.join(RES, "values")
    os.makedirs(values, exist_ok=True)
    with open(os.path.join(values, "strings.xml"), "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n'
                "<resources>\n"
                '    <string name="app_name">釜山旅行助手</string>\n'
                "</resources>\n")
    print("已生成 5 组图标与 strings.xml")


if __name__ == "__main__":
    main()
