# -*- coding: utf-8 -*-
"""把 v2.7 夜间块替换成完整的 body.night 作用域规则（含单行规则）。"""
import io
import re

P = r"D:\AI_Project_2026_2\Busan\android\assets\index.html"
src = io.open(P, encoding="utf-8").read()

RULES = [
    (["body.night"], "--sand:#0d1319; --ink:#e8eff4; --muted:#93a1ad; --line:#28343f; --bubble:#18212a;\n    --sea:#3aa6c4; --sea-dark:#9ad8e8; --user:#176d86; --ok:#39b98a; --off:#d08a58;\n    background:#0d1319; color:var(--ink)"),
    (["header"], "background:linear-gradient(135deg,#0d5a70,#072e3c)"),
    ([".selectors", ".livebar", "#followups", "footer"], "background:#111a21; border-color:var(--line)"),
    ([".selectors"], "border-bottom:1px solid var(--line)"),
    ([".livebar"], "border-bottom:1px solid var(--line)"),
    ([".chip"], "background:#1a242d; border-color:#2b3844; color:var(--ink)"),
    ([".chip.on"], "background:var(--sea); border-color:var(--sea); color:#08131a"),
    (["#liveBtn"], "background:#1b252e; border-color:#2c3a46; color:#cfe6ef"),
    (["#q"], "background:#1a232c; border-color:#2b3844; color:var(--ink)"),
    ([".icon-btn"], "background:#1e2a34; color:#bfe2ee"),
    ([".bubble"], "background:#18212a; box-shadow:0 1px 3px rgba(0,0,0,.45)"),
    ([".bubble h3", ".bubble strong", ".bubble .foot .src"], "color:#a9dcec"),
    ([".badge"], "background:#20313c; color:#a9dcec"),
    ([".badge.off"], "background:#3a2a1d; color:#e8b083"),
    ([".pick"], "background:#1b252e; border-color:#2c3a46; color:#bfe2ee"),
    ([".card", ".choice", ".routeopt", ".official", ".rating", ".lastplan", ".cloudllm"], "background:#1a242d; border-color:#2b3844; color:var(--ink)"),
    ([".choice:active"], "background:#22303b"),
    ([".card .cn", ".choice .cname", ".routeopt b"], "color:#bfe2ee"),
    ([".rating .rtop b"], "color:#f0c072"),
    ([".rating .rsub", ".rating .rmine"], "color:#aab6c0"),
    ([".rating .rmine button"], "background:#222d37; border-color:#33424f; color:#f0c072"),
    ([".wxchips button"], "background:#1e2a34; border-color:#2c3a46; color:#c9d6e0"),
    ([".wxchips button.on"], "background:#f0a94c; border-color:#f0a94c; color:#241a08"),
    ([".wxnote"], "background:#18242d; border-left-color:var(--sea); color:#b9cad6"),
    ([".official .ol"], "color:#98a6b2"),
    ([".official .ol a", ".card .cb a", ".bubble a"], "color:#7fc9de"),
    ([".choice .ctag"], "background:#1d3a46; color:#8fd0e2"),
    ([".field input", ".field select"], "background:#1a232c; border-color:#2b3844; color:var(--ink)"),
    ([".sheet"], "background:#141d25"),
    ([".sheet .desc", ".fine", ".llmnote", ".prefs-title"], "color:#9aa8b4"),
    ([".tabs"], "background:#1a242d"),
    ([".tabs button.on"], "background:#243240; color:#dbe9f1; box-shadow:none"),
    ([".ghost"], "background:#1a242d; border-color:#2b3844; color:#c4d2dc"),
    ([".modal"], "background:rgba(0,0,0,.62)"),
    ([".photostrip img"], "background:#22303a; border-color:#2a3742"),
    ([".hint"], "color:#8794a0"),
    ([".stars .sbg"], "color:#3c4854"),
    ([".wx-fab"], "background:rgba(18,44,54,.5); border-color:rgba(255,255,255,.32)"),
]

lines = ["  /* 夜间模式：按本地时间 19:00–06:00 自动切换（v2.7） */"]
for sels, decls in RULES:
    scoped = []
    for s in sels:
        scoped.append(s if s.startswith("body.night") else "body.night " + s)
    lines.append("  " + ",".join(scoped) + "{")
    for d in decls.split("\n"):
        lines.append("    " + d.strip() if d.strip().startswith("--") or ":" in d else "    " + d)
    lines.append("  }")

block = "\n".join(lines)

pat = re.compile(r"  /\* 夜间模式：按本地时间.*?(\n</style>)", re.S)
if not pat.search(src):
    raise SystemExit("night block not found")
src = pat.sub(block + r"\1", src, count=1)
io.open(P, "w", encoding="utf-8", newline="\n").write(src)
print("rewritten, lines:", len(lines))
