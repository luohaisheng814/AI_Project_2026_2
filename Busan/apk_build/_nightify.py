# -*- coding: utf-8 -*-
"""把 v2.6 的 prefers-color-scheme 深色块改写成 body.night 作用域（v2.7 按时间切换）。"""
import io
import re

P = r"D:\AI_Project_2026_2\Busan\android\assets\index.html"
src = io.open(P, encoding="utf-8").read()
lines = src.split("\n")

start = None
for i, ln in enumerate(lines):
    if "@media (prefers-color-scheme: dark){" in ln:
        start = i
        break
if start is None:
    raise SystemExit("dark block not found")

end = None
for j in range(start + 1, len(lines)):
    if lines[j].strip() == "}" and lines[j].startswith("  }"):
        end = j
        break
if end is None:
    raise SystemExit("block end not found")

body = lines[start + 1:end]
out = []
for ln in body:
    s = ln.strip()
    if not s:
        continue
    if s.endswith("{"):
        sel = s[:-1].strip()
        parts = [p.strip() for p in sel.split(",")]
        scoped = []
        for p in parts:
            if p in (":root", "body", "html"):
                scoped.append("body.night")
            else:
                scoped.append("body.night " + p)
        out.append("  " + ",".join(scoped) + "{")
    elif s == "}":
        out.append("  }")
    else:
        out.append("    " + s)

new_block = ["  /* 夜间模式：按本地时间 19:00–06:00 自动切换（v2.7） */"] + out
# 原注释行（start-1）替换
lines[start - 1: end + 1] = new_block
io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
print("done, block lines:", len(new_block))
