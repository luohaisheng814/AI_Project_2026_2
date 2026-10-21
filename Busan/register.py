# -*- coding: utf-8 -*-


import tkinter as tk
from tkinter import ttk, messagebox

import config
import db_config as db
import i18n
import ui_style as S
from captcha import CaptchaWidget

config.ensure_runtime()


class RegisterApp:
    def __init__(self, root, on_success=None):
        self.root = root
        self.on_success = on_success
        self.body = tk.Frame(root, bg=S.BG)
        self.body.pack(fill="both", expand=True)
        i18n.I.on_change(self.refresh_ui)
        self.build()
        self.root.bind("<Return>", lambda e: self.do_register())

    def build(self):
        # 切换语言重建页面时保留已输入内容
        keep_user = self._val("e_user")
        keep_pwd = self._val("e_pwd")
        keep_pwd2 = self._val("e_pwd2")

        for w in self.body.winfo_children():
            w.destroy()

        top = tk.Frame(self.body, bg=S.BG)
        top.pack(fill="x", padx=18, pady=(14, 0))
        ttk.Label(top, text=i18n.t("register_title"), style="Title.TLabel").pack(side="left")
        from chat_widget import LangButton
        LangButton(top, on_change=self.refresh_ui).pack(side="right")

        card = tk.Frame(self.body, bg=S.PANEL, padx=18, pady=18)
        card.pack(fill="x", padx=18, pady=18)

        ttk.Label(card, text=i18n.t("new_username"), background=S.PANEL).pack(anchor="w")
        self.e_user = ttk.Entry(card, font=S.F)
        self.e_user.pack(fill="x", pady=(4, 12), ipady=6)
        if keep_user:
            self.e_user.insert(0, keep_user)

        ttk.Label(card, text=i18n.t("new_password"), background=S.PANEL).pack(anchor="w")
        self.e_pwd = ttk.Entry(card, show="•", font=S.F)
        self.e_pwd.pack(fill="x", pady=(4, 12), ipady=6)
        if keep_pwd:
            self.e_pwd.insert(0, keep_pwd)

        ttk.Label(card, text=i18n.t("confirm_password"), background=S.PANEL).pack(anchor="w")
        self.e_pwd2 = ttk.Entry(card, show="•", font=S.F)
        self.e_pwd2.pack(fill="x", pady=(4, 12), ipady=6)
        if keep_pwd2:
            self.e_pwd2.insert(0, keep_pwd2)

        ttk.Label(card, text=i18n.t("captcha"), background=S.PANEL).pack(anchor="w")
        row = tk.Frame(card, bg=S.PANEL)
        row.pack(fill="x", pady=(4, 12))
        self.e_code = ttk.Entry(row, font=S.F)
        self.e_code.pack(side="left", fill="x", expand=True, ipady=6)
        self.cap = CaptchaWidget(row, side="right")
        self.cap.pack(side="left", padx=(10, 0))

        ttk.Button(card, text=i18n.t("register_btn"), style="Accent.TButton",
                   command=self.do_register).pack(fill="x", ipady=8, pady=(4, 6))

        ttk.Button(card, text=i18n.t("back_to_login"),
                   command=self.back_to_login).pack(fill="x", ipady=4)

        if not keep_user:
            self.e_user.focus_set()

    def _val(self, attr):
        w = getattr(self, attr, None)
        try:
            if w is not None and w.winfo_exists():
                return w.get()
        except Exception:
            pass
        return ""

    def refresh_ui(self):
        self.build()

    # ---------------- 注册 ----------------
    def do_register(self):
        username = self.e_user.get().strip()
        pwd = self.e_pwd.get().strip()
        pwd2 = self.e_pwd2.get().strip()
        code = self.e_code.get().strip()

        if not username or not pwd or not pwd2 or not code:
            messagebox.showwarning(i18n.t("warning"), i18n.t("empty_fields"))
            self.cap.refresh()
            return
        if not self.cap.check(code):
            messagebox.showwarning(i18n.t("warning"), i18n.t("captcha_wrong"))
            self.e_code.delete(0, "end")
            self.cap.refresh()
            return
        if len(pwd) < 4:
            messagebox.showwarning(i18n.t("warning"), i18n.t("pwd_too_short"))
            return
        if pwd != pwd2:
            messagebox.showwarning(i18n.t("warning"), i18n.t("pwd_mismatch"))
            self.e_pwd.delete(0, "end")
            self.e_pwd2.delete(0, "end")
            self.cap.refresh()
            return

        ok, msg = db.add_user(username, pwd, role="user")
        if not ok:
            messagebox.showerror(i18n.t("error"), i18n.t(msg))
            self.cap.refresh()
            return

        messagebox.showinfo(i18n.t("success"), i18n.t(msg))
        if self.on_success:
            self.root.destroy()
            self.on_success(username)
        else:
            self.back_to_login()

    # ---------------- 返回登录 ----------------
    def back_to_login(self):
        self.root.destroy()
        import login
        login.launch()


def launch(on_success=None):
    root = tk.Tk()
    S.apply(root, i18n.t("register_title"))
    S.center(root, 430, 540)
    RegisterApp(root, on_success=on_success)
    root.mainloop()


if __name__ == "__main__":
    launch()