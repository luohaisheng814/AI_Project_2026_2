# -*- coding: utf-8 -*-

import re
import threading
import tkinter as tk
from tkinter import ttk

import i18n
import ui_style as S


def insert_md(text_widget, md):
    """把简易 Markdown 写入 Text 组件：#/##/### 标题、**加粗**、- 列表、--- 分隔线"""
    text_widget.configure(state="normal")
    for line in (md or "").splitlines():
        stripped = line.strip()

        if stripped in ("---", "***", "___"):
            text_widget.insert("end", "─" * 60 + "\n", "line")
            continue

        m = re.match(r"^(#{1,6})\s*(.*)$", stripped)
        if m:
            tag = "h1" if len(m.group(1)) <= 2 else "h2"
            text_widget.insert("end", m.group(2) + "\n", tag)
            continue

        if re.match(r"^([-*]|\d+\.)\s+", stripped):
            content = re.sub(r"^([-*]|\d+\.)\s+", "", stripped)
            text_widget.insert("end", "  • ", "bullet")
            _insert_bold(text_widget, content)
            text_widget.insert("end", "\n")
            continue

        _insert_bold(text_widget, line)
        text_widget.insert("end", "\n")
    text_widget.configure(state="disabled")
    text_widget.see("end")


def _insert_bold(text_widget, line):
    """处理 **加粗** 与 `code`"""
    pos = 0
    for m in re.finditer(r"(\*\*|__)(.+?)\1|`([^`]+)`", line):
        text_widget.insert("end", line[pos:m.start()])
        if m.group(2):
            text_widget.insert("end", m.group(2), "bold")
        else:
            text_widget.insert("end", m.group(3), "code")
        pos = m.end()
    text_widget.insert("end", line[pos:])


class LangButton(ttk.Button):
    """
    语言切换按钮：点击循环切换 中文 -> 한국어 -> English。
    只通过 i18n.I.notify() 触发一次统一刷新，避免页面重复重建、输入框被清空。
    """

    def __init__(self, master, on_change=None, **kw):
        self.on_change = on_change
        super().__init__(master, command=self._click, **kw)
        self.refresh()

    def _click(self):
        i18n.I.cycle()
        i18n.I.notify()      # 统一入口：由各页面注册的 listener 负责重绘
        self.refresh()

    def refresh(self):
        self.configure(text=f"🌐 {i18n.I.current_name}")


class ChatView(tk.Frame):
    """on_send(question) -> dict，由外部处理问答并返回结果。"""

    def __init__(self, master, on_send=None, on_state=lambda *a: None, **kw):
        super().__init__(master, bg=S.BG, **kw)
        self.on_send = on_send
        self.on_state = on_state
        self._pending_followups = []
        # 对话历史：切语言重建界面后用它回放
        # 元素: ("welcome", text) / ("user", text) / ("bot", result_dict)
        self.history = []

        # ---- 对话区 ----
        wrap = tk.Frame(self, bg=S.BG)
        wrap.pack(fill="both", expand=True)

        self.text = tk.Text(
            wrap, wrap="word", bg=S.BG, fg=S.TEXT, insertbackground=S.TEXT,
            relief="flat", font=S.F, padx=14, pady=12, spacing1=2, spacing3=4,
        )
        sb = ttk.Scrollbar(wrap, command=self.text.yview)
        self.text.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.text.pack(side="left", fill="both", expand=True)

        self.status = tk.Label(self, text="", bg=S.BG, fg=S.SUB, font=S.F_SMALL, anchor="w")
        self.status.pack(fill="x", padx=16, pady=(0, 2))

        self.text.tag_configure("h1", font=S.F_H1, foreground="#7dd3fc", spacing1=10)
        self.text.tag_configure("h2", font=(S.FAMILY, 10, "bold"), foreground="#a5b4fc", spacing1=6)
        self.text.tag_configure("bold", font=S.F_BOLD, foreground="#fde68a")
        self.text.tag_configure("code", font=("Consolas", 9), foreground="#86efac")
        self.text.tag_configure("bullet", foreground=S.ACCENT)
        self.text.tag_configure("line", foreground=S.BORDER)
        self.text.tag_configure("user", foreground="#ffffff", font=S.F_BOLD)
        self.text.tag_configure("src", foreground=S.SUB, font=S.F_SMALL)
        self.text.tag_configure("src_title", foreground="#7dd3fc", font=(S.FAMILY, 9, "bold"))
        self.text.configure(state="disabled")

        # ---- 输入区 ----
        bottom = tk.Frame(self, bg=S.PANEL)
        bottom.pack(fill="x", padx=8, pady=(6, 10))

        self.entry = tk.Entry(bottom, bg=S.PANEL2, fg=S.TEXT, insertbackground=S.TEXT,
                              relief="flat", font=S.F)
        self.entry.pack(side="left", fill="x", expand=True, ipady=7, padx=(8, 6))
        self.entry.bind("<Return>", lambda e: self.send())

        self.btn_send = ttk.Button(bottom, text=i18n.t("send"), style="Accent.TButton", command=self.send)
        self.btn_send.pack(side="left", padx=(0, 6))
        self.btn_clear = ttk.Button(bottom, text=i18n.t("clear"), command=self.clear)
        self.btn_clear.pack(side="left")

        self.follow_frame = tk.Frame(self, bg=S.BG)
        self.follow_frame.pack(fill="x", padx=12, pady=(0, 4))

        self._placeholder = i18n.t("input_placeholder")
        self.entry.insert(0, self._placeholder)
        self.entry.configure(fg=S.SUB)
        self.entry.bind("<FocusIn>", self._clear_placeholder)
        self.entry.bind("<FocusOut>", self._restore_placeholder)

    # ---------- 占位提示 ----------
    def _clear_placeholder(self, _=None):
        if self.entry.get() == self._placeholder:
            self.entry.delete(0, "end")
            self.entry.configure(fg=S.TEXT)

    def _restore_placeholder(self, _=None):
        if not self.entry.get().strip():
            self.entry.insert(0, self._placeholder)
            self.entry.configure(fg=S.SUB)

    def refresh_texts(self):
        self.btn_send.configure(text=i18n.t("send"))
        self.btn_clear.configure(text=i18n.t("clear"))
        self._placeholder = i18n.t("input_placeholder")
        self._restore_placeholder()

    # ---------- 发送（异步，界面不卡顿） ----------
    def send(self, preset=None):
        q = (preset or self.entry.get()).strip()
        if not q or q == self._placeholder:
            return
        self.entry.delete(0, "end")
        self._clear_followups()
        self.add_user(q)
        self.set_status(i18n.t("searching"), busy=True)
        self.update_idletasks()
        threading.Thread(target=self._worker, args=(q,), daemon=True).start()

    def _worker(self, q):
        try:
            result = self.on_send(q) if self.on_send else None
        except Exception as e:
            result = {"answer": f"[Error] {e}", "sources": [], "followups": []}
        if result is None:
            result = {"answer": "", "sources": [], "followups": []}
        self.after(0, lambda: self._render(result))

    def _render(self, result):
        self.set_status("", busy=False)
        self.add_bot(result)

    def set_status(self, text, busy=False):
        try:
            self.status.configure(text=text or "")
            self.btn_send.state(["disabled"] if busy else ["!disabled"])
        except Exception:
            pass

    # ---------- 消息渲染 ----------
    def add_user(self, text):
        self.history.append(("user", text))
        self._render_user(text)

    def _render_user(self, text):
        self.text.configure(state="normal")
        self.text.insert("end", "🧑 " + text + "\n", "user")
        self.text.configure(state="disabled")
        self.text.see("end")

    def add_bot(self, result):
        self.history.append(("bot", result or {}))
        self._render_bot(result or {})

    def _render_bot(self, result):
        self.text.configure(state="normal")
        self.text.insert("end", "🤖 ")
        self.text.configure(state="disabled")

        insert_md(self.text, result.get("answer", ""))

        sources = result.get("sources") or []
        if sources:
            self.text.configure(state="normal")
            self.text.insert("end", "\n")
            self.text.insert("end", "📚 " + i18n.t("sources_label") + "\n", "src_title")
            for s in sources:
                self.text.insert("end", f"   - {s.get('label','')}：{s.get('detail','')}\n", "src")
            self.text.insert("end", "\n")
            self.text.configure(state="disabled")

        followups = result.get("followups") or []
        if followups:
            self.text.configure(state="normal")
            self.text.insert("end", "💡 " + i18n.t("suggest_label") + "\n", "src_title")
            self.text.configure(state="disabled")
            self._show_followups(followups)

        self.text.see("end")

    def _show_followups(self, items):
        self._clear_followups()
        for q in items[:3]:
            b = ttk.Button(self.follow_frame, text=q, command=lambda x=q: self.send(x))
            b.pack(side="left", padx=(0, 8), pady=2)
            self._pending_followups.append(b)

    def _clear_followups(self):
        for b in self._pending_followups:
            try:
                b.destroy()
            except Exception:
                pass
        self._pending_followups = []

    def welcome(self, text):
        self.history.append(("welcome", text))
        self._render_welcome(text)

    def _render_welcome(self, text):
        self.text.configure(state="normal")
        self.text.insert("end", "🤖 " + text + "\n\n")
        self.text.configure(state="disabled")

    # ---------- 语言切换后回放历史 ----------
    def restore(self):
        """清空画布并按 history 重绘全部对话（含来源与最后一轮的预测问题）。"""
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled")
        self._clear_followups()
        for kind, payload in self.history:
            if kind == "welcome":
                self._render_welcome(payload)
            elif kind == "user":
                self._render_user(payload)
            elif kind == "bot":
                self._render_bot(payload)
        self.text.see("end")

    def clear(self):
        self.history = []
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled")
        self._clear_followups()