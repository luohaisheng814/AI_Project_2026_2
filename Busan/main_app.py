# -*- coding: utf-8 -*-
"""
main_app.py —— UI 电脑桌面版主程序（成果展示）
--------------------------------------------------
启动顺序：login.py 登录 -> 登录成功进入本主页面
主页面布局：
    顶部：标题 / 当前用户 / 语言切换（中文·한국어·English）/ 退出登录
    左侧导航栏（分上下）：
        上：玩法分类四选一  01 艺术村落·文化街区 / 02 海岸休闲·日落夜景
                          03 湿地生态·自然观景 / 04 小众渔港·文艺拍照
        下：出行人数选其一  一人(男) 一人(女) 两人(男女) 两人(男男) 两人(女女) 三人及以上
    右侧：AI 智能问答区（回答 + 资料来源 + 预测下一问）
问答流程：
    用户问题 -> 检索关键词/字段 -> 本地分类库 -> 核心库 rules.txt
             -> 01/02 追加官网与百科在线查询 -> 交 LLM -> 展示回答与来源
    每位用户的每次详细查询都会记录到数据库（query_logs）
"""

import json
import tkinter as tk
from tkinter import ttk

import config
import db_config as db
import i18n
import rag_core
import ui_style as S
from chat_widget import ChatView, LangButton

config.ensure_runtime()


class MainApp:
    def __init__(self, root, username="guest", role="user", user_id=None):
        self.root = root
        self.username = username
        self.role = role
        self.user_id = user_id

        self.category = tk.StringVar(value="")
        self.group = tk.StringVar(value="")

        self.body = tk.Frame(root, bg=S.BG)
        self.body.pack(fill="both", expand=True)

        i18n.I._listeners.clear()
        i18n.I.on_change(self.refresh_ui)
        self.build()

    # ================= 界面 =================
    def build(self):
        for w in self.body.winfo_children():
            w.destroy()

        # ---------- 顶部栏 ----------
        top = tk.Frame(self.body, bg=S.PANEL, height=52)
        top.pack(fill="x")
        ttk.Label(top, text=i18n.t("main_title"), style="Title.TLabel",
                  background=S.PANEL).pack(side="left", padx=16, pady=10)
        ttk.Label(top, text=f"👤 {self.username}", background=S.PANEL,
                  foreground=S.SUB, font=S.F_SMALL).pack(side="left")

        ttk.Button(top, text=i18n.t("logout"), command=self.logout).pack(side="right", padx=10)
        LangButton(top, on_change=self.refresh_ui).pack(side="right", padx=(0, 6))

        # ---------- 主体 ----------
        main = tk.Frame(self.body, bg=S.BG)
        main.pack(fill="both", expand=True)

        # 左侧导航
        nav = tk.Frame(main, bg=S.PANEL, width=250)
        nav.pack(side="left", fill="y")
        nav.pack_propagate(False)

        # 上：玩法
        ttk.Label(nav, text=i18n.t("nav_play"), background=S.PANEL,
                  font=S.F_BOLD).pack(anchor="w", padx=14, pady=(14, 6))
        for cat in config.CATEGORIES:
            ttk.Radiobutton(nav, text=i18n.I.cat_name(cat), value=cat,
                            variable=self.category, style="TRadiobutton",
                            command=self._on_select).pack(anchor="w", padx=14, pady=2)

        tk.Frame(nav, bg=S.BORDER, height=1).pack(fill="x", padx=12, pady=12)

        # 下：人数
        ttk.Label(nav, text=i18n.t("nav_people"), background=S.PANEL,
                  font=S.F_BOLD).pack(anchor="w", padx=14, pady=(0, 6))
        for g in config.GROUP_TYPES:
            ttk.Radiobutton(nav, text=i18n.I.group_name(g), value=g,
                            variable=self.group, style="TRadiobutton",
                            command=self._on_select).pack(anchor="w", padx=14, pady=2)

        # 当前选择
        self.lbl_sel = ttk.Label(nav, text="", background=S.PANEL,
                                 foreground=S.SUB, font=S.F_SMALL, wraplength=220)
        self.lbl_sel.pack(anchor="w", padx=14, pady=14)
        self._update_sel_label()

        # 右侧问答（切换语言重建界面时，用 _chat_history 原样回放对话）
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
        # 语言切换后：玩法/人数选择保持，欢迎语换成新语言，对话历史原样保留
        if getattr(self, "_chat_history", None) and self._chat_history[0][0] == "welcome":
            self._chat_history[0] = ("welcome", i18n.t("chat_welcome"))
        self.build()

    # ================= 问答 =================
    def answer_question(self, question):
        """（在子线程中调用）检索 -> LLM -> 记录日志 -> 返回结果"""
        cat = self.category.get()
        if not cat:
            return {"answer": i18n.t("need_theme"), "sources": [], "followups": []}

        grp = self.group.get()

        self.chat.after(0, lambda: self.chat.set_status(i18n.t("thinking"), busy=True))
        # lang 传 None：由 lang_detect 按提问语言决定（中文问中文答 / 韩文问韩文答 / 英文问英文答）
        result = rag_core.answer(question, category=cat, group_type=grp, lang=None,
                                 ui_lang=i18n.I.lang, username=self.username)

        # 记录本次详细查询（写入对应用户数据库 query_logs）
        try:
            db.log_query(
                self.user_id, self.username, cat, grp, question,
                (result.get("answer") or "")[:4000],
                json.dumps(result.get("sources") or [], ensure_ascii=False),
                result.get("lang") or i18n.I.lang,
            )
        except Exception:
            pass

        return result

    # ================= 退出 =================
    def logout(self):
        self.root.destroy()
        import login
        login.launch()


# ==================================================================
# 启动入口
# ==================================================================
def open_main(username, role="user", user_id=None):
    root = tk.Tk()
    S.apply(root, i18n.t("app_name"))
    S.center(root, 1180, 740)
    MainApp(root, username=username, role=role, user_id=user_id)
    root.mainloop()


def launch(username=None, role="user", user_id=None):
    """直接启动主界面；未登录时先跳 login.py 登录页。"""
    if not username:
        import login
        login.launch(on_success=lambda u: open_main(u["username"], u["role"], u["id"]))
        return
    open_main(username, role, user_id)


if __name__ == "__main__":
    launch()