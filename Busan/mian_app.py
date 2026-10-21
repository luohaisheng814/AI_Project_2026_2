# -*- coding: utf-8 -*-
"""
mian_app.py —— 主程序入口（先登录 -> 主页面）
--------------------------------------------------
运行 python mian_app.py：先跳 login.py 登录，登录成功后进入 main_app.py 主页面。
"""

from main_app import launch, open_main, MainApp  # noqa: F401

if __name__ == "__main__":
    launch()