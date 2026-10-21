# -*- coding: utf-8 -*-
"""
login.py —— UI 登录界面（可独立运行）
--------------------------------------------------
功能：
  * 用户名 + 密码 + 随机验证码（图片右侧 ⟳ 可点击刷新）
  * 右上角语言切换按钮：中文 / 한국어 / English，切换后整页文字立即更新
  * 校验顺序：验证码 -> 查询数据库 -> 比对密码
  * 「没有账号？立即注册」跳转到 register.py
  * 登录成功跳转 mian_app.py 主界面
"""

import tkinter as tk
from tkinter import ttk, messagebox

import config
import db_config as db
import i18n
import ui_style as S
from captcha import CaptchaWidget

config.ensure_runtime()


class LoginApp:
    def __init__(self, root, on_success=None):
        self.root = root
        self.on_success = on_success
        self.body = tk.Frame(root, bg=S.BG)
        self.body.pack(fill="both", expand=True)
        i18n.I.on_change(self.refresh_ui)
        self.build()
        try:
            self.root.bind("<Return>", lambda e: self.do_login())
        except Exception:
            pass

    # ---------------- 构建界面 ----------------
    def build(self):
        # 切换语言会重建整页：先把已输入的用户名/密码保存下来，重建后回填
        keep_user = self._val("e_user")
        keep_pwd = self._val("e_pwd")

        for w in self.body.winfo_children():
            w.destroy()

        top = tk.Frame(self.body, bg=S.BG)
        top.pack(fill="x", padx=18, pady=(14, 0))
        ttk.Label(top, text=i18n.t("login_title"), style="Title.TLabel").pack(side="left")
        from chat_widget import LangButton
        LangButton(top, on_change=self.refresh_ui).pack(side="right")

        card = tk.Frame(self.body, bg=S.PANEL, padx=18, pady=18)
        card.pack(fill="x", padx=18, pady=18)

        # 用户名
        ttk.Label(card, text=i18n.t("username"), background=S.PANEL).pack(anchor="w")
        self.e_user = ttk.Entry(card, font=S.F)
        self.e_user.pack(fill="x", pady=(4, 12), ipady=6)
        if keep_user:
            self.e_user.insert(0, keep_user)

        # 密码
        ttk.Label(card, text=i18n.t("password"), background=S.PANEL).pack(anchor="w")
        self.e_pwd = ttk.Entry(card, show="•", font=S.F)
        self.e_pwd.pack(fill="x", pady=(4, 12), ipady=6)
        if keep_pwd:
            self.e_pwd.insert(0, keep_pwd)

        # 验证码
        ttk.Label(card, text=i18n.t("captcha"), background=S.PANEL).pack(anchor="w")
        row = tk.Frame(card, bg=S.PANEL)
        row.pack(fill="x", pady=(4, 12))
        self.e_code = ttk.Entry(row, font=S.F)
        self.e_code.pack(side="left", fill="x", expand=True, ipady=6)
        self.cap = CaptchaWidget(row, side="right")
        self.cap.pack(side="left", padx=(10, 0))

        # 登录按钮
        ttk.Button(card, text=i18n.t("login_btn"), style="Accent.TButton",
                   command=self.do_login).pack(fill="x", ipady=8, pady=(4, 6))

        # 去注册
        ttk.Button(card, text=i18n.t("goto_register"),
                   command=self.goto_register).pack(fill="x", ipady=4)

        # 注：后台管理是独立入口（admin_panel.py），登录页不放任何后台跳转按钮

        if not keep_user:
            self.e_user.focus_set()
        else:
            self.e_code.focus_set()

    def _val(self, attr):
        """安全读取旧控件内容（控件可能已被销毁）。"""
        w = getattr(self, attr, None)
        try:
            if w is not None and w.winfo_exists():
                return w.get()
        except Exception:
            pass
        return ""

    def refresh_ui(self):
        self.build()

    # ---------------- 登录 ----------------
    def do_login(self):
        username = self.e_user.get().strip()
        password = self.e_pwd.get().strip()
        code = self.e_code.get().strip()

        if not username or not password or not code:
            messagebox.showwarning(i18n.t("warning"), i18n.t("empty_fields"))
            self.cap.refresh()
            return
        if not self.cap.check(code):
            messagebox.showwarning(i18n.t("warning"), i18n.t("captcha_wrong"))
            self.e_code.delete(0, "end")
            self.cap.refresh()
            return

        ok, role, msg = db.verify_login(username, password)
        if not ok:
            messagebox.showerror(i18n.t("error"), i18n.t(msg))
            self.cap.refresh()
            self.e_code.delete(0, "end")
            return

        user = db.get_user(username)
        messagebox.showinfo(i18n.t("success"), i18n.t(msg))

        if self.on_success:
            self.root.destroy()
            self.on_success(user)
        else:
            self.goto_main(user)

    def goto_main(self, user):
        """登录成功 -> 跳转 mian_app.py 主页面（电脑桌面版成果展示）"""
        self.root.destroy()
        import mian_app
        mian_app.open_main(username=user["username"], role=user["role"], user_id=user["id"])

    # ---------------- 跳转注册 ----------------
    def goto_register(self):
        self.root.destroy()
        import register
        register.launch()


def launch(on_success=None):
    root = tk.Tk()
    S.apply(root, i18n.t("login_title"))
    S.center(root, 430, 480)
    LoginApp(root, on_success=on_success)
    root.mainloop()


if __name__ == "__main__":
    launch()