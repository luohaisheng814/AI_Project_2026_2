# -*- coding: utf-8 -*-


import tkinter as tk
from tkinter import ttk

import config
import i18n
import rag_core
import ui_style as S
from chat_widget import ChatView, LangButton

config.ensure_runtime()


class DesktopApp:
    def __init__(self, root):
        self.root = root
        self.category = tk.StringVar(value=config.CATEGORIES[0])
        self.group = tk.StringVar(value=config.GROUP_TYPES[0])

        self.body = tk.Frame(root, bg=S.BG)
        self.body.pack(fill="both", expand=True)

        i18n.I._listeners.clear()
        i18n.I.on_change(self.refresh_ui)
        self.build()

    def build(self):
        for w in self.body.winfo_children():
            w.destroy()

        top = tk.Frame(self.body, bg=S.PANEL, height=52)
        top.pack(fill="x")
        ttk.Label(top, text=i18n.t("desktop_title"), style="Title.TLabel",
                  background=S.PANEL).pack(side="left", padx=16, pady=10)
        ttk.Button(top, text=i18n.t("clear"), command=lambda: self.chat.clear()).pack(side="right", padx=10)
        LangButton(top, on_change=self.refresh_ui).pack(side="right", padx=(0, 6))

        main = tk.Frame(self.body, bg=S.BG)
        main.pack(fill="both", expand=True)

        nav = tk.Frame(main, bg=S.PANEL, width=250)
        nav.pack(side="left", fill="y")
        nav.pack_propagate(False)

        ttk.Label(nav, text=i18n.t("nav_play"), background=S.PANEL,
                  font=S.F_BOLD).pack(anchor="w", padx=14, pady=(14, 6))
        for cat in config.CATEGORIES:
            ttk.Radiobutton(nav, text=i18n.I.cat_name(cat), value=cat,
                            variable=self.category, style="TRadiobutton",
                            command=self._on_select).pack(anchor="w", padx=14, pady=2)

        tk.Frame(nav, bg=S.BORDER, height=1).pack(fill="x", padx=12, pady=12)

        ttk.Label(nav, text=i18n.t("nav_people"), background=S.PANEL,
                  font=S.F_BOLD).pack(anchor="w", padx=14, pady=(0, 6))
        for g in config.GROUP_TYPES:
            ttk.Radiobutton(nav, text=i18n.I.group_name(g), value=g,
                            variable=self.group, style="TRadiobutton",
                            command=self._on_select).pack(anchor="w", padx=14, pady=2)

        self.lbl_sel = ttk.Label(nav, text="", background=S.PANEL,
                                 foreground=S.SUB, font=S.F_SMALL, wraplength=220)
        self.lbl_sel.pack(anchor="w", padx=14, pady=14)
        self._update_sel_label()

        right = tk.Frame(main, bg=S.BG)
        right.pack(side="left", fill="both", expand=True)
        prev_history = getattr(self, "_chat_history", None)
        self.chat = ChatView(right, on_send=self.answer_question)
        self.chat.pack(fill="both", expand=True, padx=8, pady=(8, 0))
        self._chat_history = prev_history if prev_history is not None else self.chat.history
        self.chat.history = self._chat_history
        if self._chat_history:
            self.chat.restore()
        else:
            self.chat.welcome(i18n.t("chat_welcome"))

    def _update_sel_label(self):
        cat = i18n.I.cat_name(self.category.get()) if self.category.get() else i18n.t("please_select")
        grp = i18n.I.group_name(self.group.get()) if self.group.get() else i18n.t("please_select")
        self.lbl_sel.configure(text=f"{i18n.t('current_selection')}：\n· {cat}\n· {grp}")

    def _on_select(self):
        self._update_sel_label()

    def refresh_ui(self):
        keep_cat, keep_grp = self.category.get(), self.group.get()
        if getattr(self, "_chat_history", None) and self._chat_history[0][0] == "welcome":
            self._chat_history[0] = ("welcome", i18n.t("chat_welcome"))
        self.build()
        self.category.set(keep_cat)
        self.group.set(keep_grp)
        self._update_sel_label()

    def answer_question(self, question):
        # lang=None -> 由 lang_detect 按提问语言自动决定回答语言
        return rag_core.answer(
            question,
            category=self.category.get(),
            group_type=self.group.get(),
            lang=None,
            ui_lang=i18n.I.lang,
            username="desktop_tester",
        )


def launch():
    root = tk.Tk()
    S.apply(root, i18n.t("desktop_title"))
    S.center(root, 1180, 740)
    DesktopApp(root)
    root.mainloop()


if __name__ == "__main__":
    launch()