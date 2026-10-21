# -*- coding: utf-8 -*-
"""
随机验证码组件（放大版）
--------------------------------------------------
改动要点（解决"验证码太小看不清"）：
  1. 图片尺寸 110x42 -> 180x60，字符字号 26 -> 38，字符间距同步拉大
  2. 【根因修复】字体查找失败会退化为极小的默认字体 —— 现在改为
     多平台候选字体列表 + 逐级降字号 + Pillow 新版 load_default(size=) 兜底，
     保证任何机器上都是"大号粗体"
  3. 噪点减少、干扰线变淡，字符颜色加深，对比度更高
  4. 点击验证码图片本身也能刷新（不必非点 ⟳ 按钮）
  5. 无 PIL 环境的文字降级模式：字号 18 -> 30，并加宽留白

用法（调用处无需改动）：
    cap = CaptchaWidget(parent, side="right")
    cap.code            -> 当前验证码字符串
    cap.refresh()       -> 刷新
    cap.check(text)     -> 校验（忽略大小写）
布局：[ 验证码图片 ] [ ⟳ 刷新 ]
"""

import os
import random
import string

try:
    from PIL import Image, ImageDraw, ImageFont, ImageTk
    HAS_PIL = True
except Exception:
    HAS_PIL = False

import tkinter as tk
from tkinter import ttk


# 容易混淆的字符剔除：0/O/1/I/l/L
_ALPHABET = "".join(c for c in (string.ascii_uppercase + string.digits) if c not in "01OIolL")

# ---- 尺寸参数（想再大就改这里）----
IMG_W = 180          # 验证码图片宽
IMG_H = 60           # 验证码图片高
FONT_SIZE = 38       # 字符字号
CHAR_GAP = 40        # 字符间距
CHAR_X0 = 16         # 起始横坐标
CODE_LEN = 4         # 验证码位数


def gen_code(n=CODE_LEN):
    return "".join(random.choice(_ALPHABET) for _ in range(n))


# ------------------------------------------------------------------
# 字体：按平台给出候选，逐级降级，确保拿到"大号粗体"
# ------------------------------------------------------------------
def _font_candidates():
    """返回 (路径, 备选字号列表) 的候选序列，按优先级排列。"""
    win = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
    cands = [
        # Windows
        os.path.join(win, "arialbd.ttf"),      # Arial Bold
        os.path.join(win, "arial.ttf"),
        os.path.join(win, "segoeuib.ttf"),     # Segoe UI Bold
        os.path.join(win, "consolab.ttf"),     # Consolas Bold
        os.path.join(win, "verdanab.ttf"),
        # macOS
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        # Linux / 通用
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        # 交给 PIL 自己按名字找
        "arialbd.ttf", "Arial Bold.ttf", "arial.ttf", "DejaVuSans-Bold.ttf",
    ]
    return cands


def _load_font(target=FONT_SIZE):
    """尽量加载 target 大小的真字体；全部失败时用 PIL 新版 load_default(size=)。"""
    sizes = [target, target - 4, target - 8, 28, 24, 20]
    for path in _font_candidates():
        for size in sizes:
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue

    # 兜底：Pillow >= 9.2 支持指定大小的默认字体（比老版 load_default 大得多）
    try:
        return ImageFont.load_default(size=target)
    except TypeError:
        return ImageFont.load_default()


def _make_image(code, w=IMG_W, h=IMG_H):
    """生成验证码图片；无 PIL 时返回 None。"""
    if not HAS_PIL:
        return None

    img = Image.new("RGB", (w, h), (248, 250, 252))
    d = ImageDraw.Draw(img)

    # 干扰线（放在字符下层，颜色淡，不遮挡）
    for _ in range(3):
        d.line(
            [(random.randint(0, w), random.randint(4, h - 4)),
             (random.randint(0, w), random.randint(4, h - 4))],
            fill=(random.randint(198, 225),) * 3, width=1,
        )
    # 噪点（减少数量，避免糊成一团）
    for _ in range(45):
        d.point((random.randint(0, w), random.randint(0, h)),
                fill=(random.randint(185, 222),) * 3)

    font = _load_font()

    x = CHAR_X0
    for ch in code:
        # 轻微旋转/上下抖动，但幅度小，保证可读
        d.text((x, random.randint(8, 14)), ch,
               fill=(random.randint(10, 60), random.randint(10, 60), random.randint(10, 90)),
               font=font)
        x += CHAR_GAP

    # 边框
    d.rectangle([0, 0, w - 1, h - 1], outline=(176, 186, 199), width=2)
    return ImageTk.PhotoImage(img)


class CaptchaWidget(tk.Frame):
    """
    参数：
        master    父容器
        side      "right" -> 验证码在输入框右侧（默认）
                  "left"  -> 验证码在输入框左侧
        scale     整体缩放倍率（1.0 = 180x60，想更大传 1.3）
    """

    def __init__(self, master, side="right", scale=1.0, **kwargs):
        super().__init__(master, **kwargs)
        self.code = gen_code()
        self._img = None
        self.scale = scale

        self.canvas = tk.Label(
            self, relief="ridge", bg="#f8fafc",
            bd=2, padx=4, pady=4, cursor="hand2",
        )
        # 点击验证码图片本身也能刷新
        self.canvas.bind("<Button-1>", lambda e: self.refresh())

        self.btn = ttk.Button(self, text="⟳", width=4, command=self.refresh, takefocus=0)

        if side == "right":
            self.canvas.pack(side="left", padx=(0, 6))
            self.btn.pack(side="left", fill="y")
        else:
            self.btn.pack(side="left", fill="y", padx=(0, 6))
            self.canvas.pack(side="left")

        self.refresh()

    def refresh(self):
        self.code = gen_code()
        if HAS_PIL:
            try:
                self._img = _make_image(self.code,
                                        int(IMG_W * self.scale),
                                        int(IMG_H * self.scale))
                self.canvas.configure(image=self._img, text="")
                self.canvas.image = self._img     # 防止被 GC
                return
            except Exception:
                pass
        # 降级：直接把验证码显示为大号文字
        self.canvas.configure(
            image="", text=" " + " ".join(self.code) + " ",
            font=("Consolas", int(30 * self.scale), "bold"),
            fg="#111827", bg="#f8fafc", padx=18, pady=12,
        )

    def check(self, user_input):
        """校验（忽略大小写与首尾空格）。"""
        return str(user_input or "").strip().upper() == self.code.upper()


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Captcha Test")
    c = CaptchaWidget(root, side="right")
    c.pack(padx=20, pady=20)
    print("code =", c.code)
    root.mainloop()