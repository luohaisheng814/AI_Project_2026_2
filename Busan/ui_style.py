# -*- coding: utf-8 -*-
"""统一 UI 主题：深色配色 + 跨平台中韩英字体。"""

import platform
import tkinter as tk
from tkinter import ttk

BG = "#0f1115"
PANEL = "#171a21"
PANEL2 = "#1e222b"
ACCENT = "#3b82f6"
ACCENT_HOVER = "#2563eb"
TEXT = "#e6e9ef"
SUB = "#9aa4b2"
BORDER = "#2a2f3a"
SUCCESS = "#22c55e"
DANGER = "#ef4444"
BUBBLE_USER = "#1f6feb"
BUBBLE_BOT = "#1b2029"


def _pick_family():
    sysname = platform.system()
    if sysname == "Windows":
        return "Microsoft YaHei UI"
    if sysname == "Darwin":
        return "PingFang SC"
    for f in ("Noto Sans CJK SC", "WenQuanYi Micro Hei", "Noto Sans KR", "DejaVu Sans"):
        try:
            import tkinter.font as tkfont
            root = tk._default_root
            if root is not None and f in tkfont.families():
                return f
        except Exception:
            continue
    return "DejaVu Sans"


FAMILY = _pick_family()
F = (FAMILY, 10)
F_BOLD = (FAMILY, 10, "bold")
F_TITLE = (FAMILY, 16, "bold")
F_H1 = (FAMILY, 12, "bold")
F_SMALL = (FAMILY, 9)


def apply(root, title=""):
    """应用主题到根窗口。"""
    try:
        root.configure(bg=BG)
        if title:
            root.title(title)
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure(".", background=BG, foreground=TEXT, fieldbackground=PANEL2, font=F)
        style.configure("TFrame", background=BG)
        style.configure("Panel.TFrame", background=PANEL)
        style.configure("TLabel", background=BG, foreground=TEXT, font=F)
        style.configure("Sub.TLabel", background=BG, foreground=SUB, font=F_SMALL)
        style.configure("Title.TLabel", background=BG, foreground=TEXT, font=F_TITLE)
        style.configure("TButton", background=PANEL2, foreground=TEXT, borderwidth=0, padding=6, font=F)
        style.map("TButton", background=[("active", ACCENT), ("pressed", ACCENT_HOVER)])
        style.configure("Accent.TButton", background=ACCENT, foreground="#ffffff", font=F_BOLD, padding=6)
        style.map("Accent.TButton", background=[("active", ACCENT_HOVER)])
        style.configure("TRadiobutton", background=PANEL, foreground=TEXT, font=F, padding=4)
        style.map("TRadiobutton", background=[("active", PANEL)])
        style.configure("TEntry", fieldbackground=PANEL2, foreground=TEXT, insertcolor=TEXT, padding=5)
        style.configure("TCheckbutton", background=BG, foreground=TEXT, font=F)
        style.configure("Treeview", background=PANEL2, fieldbackground=PANEL2, foreground=TEXT,
                        borderwidth=0, rowheight=28, font=F)
        style.configure("Treeview.Heading", background=PANEL, foreground=TEXT, font=F_BOLD)
        style.map("Treeview", background=[("selected", ACCENT)], foreground=[("selected", "#ffffff")])
        style.configure("TScrollbar", background=PANEL, troughcolor=BG, borderwidth=0)
    except Exception:
        pass
    return root


def center(root, w=1000, h=680):
    """居中并设置初始大小。"""
    try:
        root.geometry(f"{w}x{h}")
        root.update_idletasks()
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        root.geometry(f"{w}x{h}+{(sw - w)//2}+{(sh - h)//3}")
    except Exception:
        pass
    return root