# -*- coding: utf-8 -*-
"""把生成的应用图标裁成满幅正方形，并导出 iOS / PWA 需要的尺寸。"""
from PIL import Image, ImageDraw

SRC = r"D:\AI_Project_2026_2\Busan\apk_build\icon_raw.png"
OUT = r"D:\AI_Project_2026_2\Busan\android\assets"\nBIG = r"D:\AI_Project_2026_2\Busan\pwa"

im = Image.open(SRC).convert("RGB")
w, h = im.size

# 找非白区域（生成图带白边）
px = im.load()
minx, miny, maxx, maxy = w, h, 0, 0
step = 4
for y in range(0, h, step):
    for x in range(0, w, step):
        r, g, b = px[x, y]
        if not (r > 245 and g > 245 and b > 245):
            if x < minx: minx = x
            if y < miny: miny = y
            if x > maxx: maxx = x
            if y > maxy: maxy = y
pad = 6
box = (max(0, minx - pad), max(0, miny - pad), min(w, maxx + pad), min(h, maxy + pad))
sq = im.crop(box)
side = max(sq.size)
canvas = Image.new("RGB", (side, side), (255, 255, 255))
canvas.paste(sq, ((side - sq.width) // 2, (side - sq.height) // 2))

# 圆角处的白角用邻近的青色填满，避免 iOS 圆角遮罩后出现白边
corner = canvas.getpixel((2, 2))
teal = (15, 126, 151)
if corner[0] > 240 and corner[1] > 240 and corner[2] > 240:
    for pt in ((0, 0), (side - 1, 0), (0, side - 1), (side - 1, side - 1)):
        ImageDraw.floodfill(canvas, pt, teal, thresh=26)

out1024 = canvas.resize((1024, 1024), Image.LANCZOS)
out1024.save(BIG + r"\icon-1024.png", "PNG")
for size in (512, 192, 180):
    out1024.resize((size, size), Image.LANCZOS).save(OUT + rf"\icon-{size}.png", "PNG")
print("icon ok", canvas.size, "-> 1024, 512, 192, 180  corner", corner)
