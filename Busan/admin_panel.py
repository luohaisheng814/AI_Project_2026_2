# -*- coding: utf-8 -*-


import tkinter as tk
from tkinter import ttk, messagebox

import config
import db_config as db
import i18n
import ui_style as S
from captcha import CaptchaWidget

config.ensure_runtime()
MASK = "*" * 6


class AdminLoginApp:
    def __init__(self, root):
        self.root = root
        self.body = tk.Frame(root, bg=S.BG)
        self.body.pack(fill="both", expand=True)
        i18n.I.on_change(self.refresh_ui)
        self.build()
        self.root.bind("<Return>", lambda e: self.do_login())

    def build(self):
        keep_user = self._val("e_user")
        keep_pwd = self._val("e_pwd")

        for w in self.body.winfo_children():
            w.destroy()

        top = tk.Frame(self.body, bg=S.BG)
        top.pack(fill="x", padx=18, pady=(14, 0))
        ttk.Label(top, text=i18n.t("admin_login_title"), style="Title.TLabel").pack(side="left")
        from chat_widget import LangButton
        LangButton(top, on_change=self.refresh_ui).pack(side="right")

        card = tk.Frame(self.body, bg=S.PANEL, padx=18, pady=18)
        card.pack(fill="x", padx=18, pady=18)

        ttk.Label(card, text=i18n.t("admin_account"), background=S.PANEL).pack(anchor="w")
        self.e_user = ttk.Entry(card, font=S.F)
        self.e_user.insert(0, keep_user or config.DEFAULT_ADMIN)
        self.e_user.pack(fill="x", pady=(4, 12), ipady=6)

        ttk.Label(card, text=i18n.t("admin_password"), background=S.PANEL).pack(anchor="w")
        self.e_pwd = ttk.Entry(card, show="•", font=S.F)
        self.e_pwd.pack(fill="x", pady=(4, 12), ipady=6)
        if keep_pwd:
            self.e_pwd.insert(0, keep_pwd)

        ttk.Label(card, text=i18n.t("captcha"), background=S.PANEL).pack(anchor="w")
        row = tk.Frame(card, bg=S.PANEL)
        row.pack(fill="x", pady=(4, 12))
        self.e_code = ttk.Entry(row, font=S.F)
        self.e_code.pack(side="left", fill="x", expand=True, ipady=6)
        self.cap = CaptchaWidget(row, side="right")
        self.cap.pack(side="left", padx=(10, 0))

        ttk.Button(card, text=i18n.t("admin_login_btn"), style="Accent.TButton",
                   command=self.do_login).pack(fill="x", ipady=8)

        ttk.Label(self.body, text=i18n.t("admin_default_hint"), style="Sub.TLabel").pack(pady=10)
        if not keep_pwd:
            self.e_pwd.focus_set()

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

    def do_login(self):
        u = self.e_user.get().strip()
        p = self.e_pwd.get().strip()
        c = self.e_code.get().strip()
        if not u or not p or not c:
            messagebox.showwarning(i18n.t("warning"), i18n.t("empty_fields"))
            self.cap.refresh()
            return
        if not self.cap.check(c):
            messagebox.showwarning(i18n.t("warning"), i18n.t("captcha_wrong"))
            self.e_code.delete(0, "end")
            self.cap.refresh()
            return

        ok, role, msg = db.verify_login(u, p)
        if not ok:
            messagebox.showerror(i18n.t("error"), i18n.t(msg))
            self.cap.refresh()
            self.e_code.delete(0, "end")
            return
        if role != "admin":
            messagebox.showerror(i18n.t("error"), i18n.t("admin_only"))
            self.cap.refresh()
            self.e_code.delete(0, "end")
            return

        self.root.destroy()
        open_panel()


class AdminPanelApp:
    def __init__(self, root):
        self.root = root
        self.body = tk.Frame(root, bg=S.BG)
        self.body.pack(fill="both", expand=True)
        i18n.I.on_change(self.refresh_ui)
        self.build()
        self.load_data()

    def build(self):
        for w in self.body.winfo_children():
            w.destroy()

        top = tk.Frame(self.body, bg=S.BG)
        top.pack(fill="x", padx=16, pady=(12, 6))
        ttk.Label(top, text=i18n.t("admin_panel_title"), style="Title.TLabel").pack(side="left")
        from chat_widget import LangButton
        LangButton(top, on_change=self.refresh_ui).pack(side="right")

        self.tree_frame = tk.Frame(self.body, bg=S.BG)
        self.tree_frame.pack(fill="both", expand=True, padx=16, pady=6)

        ops = tk.Frame(self.body, bg=S.PANEL, padx=12, pady=10)
        ops.pack(fill="x", padx=16, pady=(0, 6))
        ttk.Button(ops, text=i18n.t("set_as_admin"), command=lambda: self.set_role("admin")).pack(side="left", padx=4)
        ttk.Button(ops, text=i18n.t("set_as_user"), command=lambda: self.set_role("user")).pack(side="left", padx=4)
        ttk.Button(ops, text=i18n.t("reset_pwd"), command=self.reset_pwd).pack(side="left", padx=4)
        ttk.Button(ops, text=i18n.t("view_logs"), command=self.view_logs).pack(side="left", padx=4)
        ttk.Button(ops, text=i18n.t("refresh"), command=self.load_data).pack(side="left", padx=4)

        self.lbl_count = ttk.Label(self.body, text="", style="Sub.TLabel")
        self.lbl_count.pack(anchor="w", padx=18, pady=(0, 12))

    # ---------------- 数据表 ----------------
    def _make_tree(self):
        for w in self.tree_frame.winfo_children():
            w.destroy()
        cols = ("id", "username", "password", "role", "logs", "created")
        self.tree = ttk.Treeview(self.tree_frame, columns=cols, show="headings", height=12)
        heads = {
            "id": i18n.t("col_id"), "username": i18n.t("col_username"),
            "password": i18n.t("col_password"), "role": i18n.t("col_role"),
            "logs": i18n.t("col_logs"), "created": i18n.t("col_created"),
        }
        widths = {"id": 60, "username": 180, "password": 110, "role": 110, "logs": 90, "created": 180}
        for c in cols:
            self.tree.heading(c, text=heads[c])
            self.tree.column(c, width=widths[c], anchor="center")
        sb = ttk.Scrollbar(self.tree_frame, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)

    def load_data(self):
        self._make_tree()
        users = db.list_users()
        try:
            counts = db.count_logs_by_user()
        except Exception:
            counts = {}
        for row in users:
            role_text = i18n.t("role_admin") if row["role"] == "admin" else i18n.t("role_user")
            self.tree.insert("", "end", iid=str(row["id"]),
                             values=(row["id"], row["username"], MASK, role_text,
                                     counts.get(row["username"], 0), row["created_at"] or ""))
        self.lbl_count.configure(
            text=f"{i18n.t('user_count')}：{len(users)}    {i18n.t('db_path_label')}：{db.db_path_in_use()}"
        )

    def _selected_id(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning(i18n.t("warning"), i18n.t("need_select_user"))
            return None
        try:
            return int(sel[0])
        except Exception:
            return None

    # ---------------- 操作 ----------------
    def set_role(self, role):
        uid = self._selected_id()
        if uid is None:
            return
        if db.set_role(uid, role):
            messagebox.showinfo(i18n.t("success"), i18n.t("role_updated"))
            self.load_data()

    def reset_pwd(self):
        uid = self._selected_id()
        if uid is None:
            return
        if db.reset_password(uid, config.RESET_PASSWORD):
            messagebox.showinfo(i18n.t("success"), i18n.t("pwd_reset_done"))
            self.load_data()

    # ---------------- 查看该用户的查询记录 ----------------
    def view_logs(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning(i18n.t("warning"), i18n.t("need_select_user"))
            return
        username = self.tree.item(sel[0])["values"][1]

        win = tk.Toplevel(self.root)
        win.transient(self.root)
        win.configure(bg=S.BG)
        win.title(f"{i18n.t('logs_title')} - {username}")
        S.center(win, 900, 520)

        top = tk.Frame(win, bg=S.BG)
        top.pack(fill="x", padx=14, pady=(12, 6))
        ttk.Label(top, text=f"{i18n.t('logs_title')}：{username}", style="Title.TLabel").pack(side="left")

        body = tk.Frame(win, bg=S.BG)
        body.pack(fill="both", expand=True, padx=14, pady=(0, 12))

        txt = tk.Text(body, wrap="word", bg=S.PANEL2, fg=S.TEXT, insertbackground=S.TEXT,
                      relief="flat", font=S.F, padx=12, pady=10)
        sb = ttk.Scrollbar(body, command=txt.yview)
        txt.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        txt.pack(side="left", fill="both", expand=True)

        logs = db.get_user_logs(username, limit=200)
        if not logs:
            txt.insert("end", i18n.t("no_logs"))
        else:
            for lg in logs:
                cat = i18n.I.cat_name(lg["category"]) if lg["category"] else "-"
                grp = i18n.I.group_name(lg["group_type"]) if lg["group_type"] else "-"
                txt.insert("end", f"[{lg['created_at']}] ({cat} / {grp} / {lg['lang']})\n", "h")
                txt.insert("end", f"Q: {lg['question']}\n")
                ans = (lg["answer"] or "").replace("\n", " ")
                txt.insert("end", f"A: {ans[:300]}{'...' if len(ans) > 300 else ''}\n")
                txt.insert("end", "─" * 80 + "\n", "line")
        txt.tag_configure("h", foreground="#7dd3fc", font=S.F_BOLD)
        txt.tag_configure("line", foreground=S.BORDER)
        txt.configure(state="disabled")

        ttk.Button(win, text=i18n.t("close"), command=win.destroy).pack(pady=(0, 12))

    def refresh_ui(self):
        self.build()
        self.load_data()


def open_panel():
    root = tk.Tk()
    S.apply(root, i18n.t("admin_panel_title"))
    S.center(root, 820, 560)
    AdminPanelApp(root)
    root.mainloop()


def launch():
    root = tk.Tk()
    S.apply(root, i18n.t("admin_login_title"))
    S.center(root, 430, 460)
    AdminLoginApp(root)
    root.mainloop()


if __name__ == "__main__":
    launch()