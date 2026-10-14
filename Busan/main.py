"""
釜山沙下区文旅问答系统 - 手机 App 版
基于 KivyMD（Material Design）
"""

import sys
import os
import threading

# 确保能导入项目模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kivy.lang import Builder
from kivy.clock import Clock
from kivy.utils import platform
from kivymd.app import MDApp
from kivymd.uix.list import OneLineListItem, TwoLineListItem
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDRaisedButton, MDIconButton, MDFlatButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.navigationdrawer import MDNavigationDrawer, MDNavigationDrawerMenu
from kivymd.toast import toast

# 导入核心逻辑（完全复用，不用改）
from core_api import ask, list_all_spots, list_categories, reset_session

# ============ KV 布局 ============
KV = '''
<ChatBubble@MDCard>:
    size_hint_y: None
    height: self.minimum_height
    padding: dp(12)
    radius: dp(12)
    elevation: 1
    md_bg_color: app.theme_cls.primary_color if root.is_user else app.theme_cls.bg_light
    
    MDLabel:
        text: root.message_text
        theme_text_color: "Custom" if root.is_user else "Primary"
        text_color: 1,1,1,1 if root.is_user else app.theme_cls.text_color
        font_style: "Body1"
        size_hint_y: None
        height: self.texture_size[1]
        text_size: (root.width - dp(40), None)

ScreenManager:
    Screen:
        name: "chat"
        BoxLayout:
            orientation: "vertical"
            
            # 顶部导航栏
            MDTopAppBar:
                title: "釜山沙下区文旅问答"
                elevation: 4
                left_action_items: [["menu", lambda x: nav_drawer.set_state("open")]]
                right_action_items: [["refresh", lambda x: app.reset_chat()]]
            
            # 聊天区域
            ScrollView:
                id: scroll_view
                MDBoxLayout:
                    id: chat_container
                    orientation: "vertical"
                    size_hint_y: None
                    height: self.minimum_height
                    padding: dp(10)
                    spacing: dp(8)
            
            # 底部输入栏
            BoxLayout:
                orientation: "horizontal"
                size_hint_y: None
                height: dp(60)
                padding: dp(8)
                spacing: dp(8)
                md_bg_color: app.theme_cls.bg_light
                
                MDTextField:
                    id: input_field
                    hint_text: "输入景点名 + 需求..."
                    mode: "round"
                    size_hint_x: 0.8
                    on_text_validate: app.send_message()
                
                MDRaisedButton:
                    text: "发送"
                    size_hint_x: 0.2
                    on_release: app.send_message()

MDNavigationDrawer:
    id: nav_drawer
    MDNavigationDrawerMenu:
        ScrollView:
            MDBoxLayout:
                orientation: "vertical"
                size_hint_y: None
                height: self.minimum_height
                padding: dp(16)
                spacing: dp(8)
                
                MDLabel:
                    text: "🗺️ 景点导航"
                    font_style: "H6"
                    size_hint_y: None
                    height: dp(40)
                
                Widget:
                    size_hint_y: None
                    height: dp(8)
                
                # 景点按钮由 Python 动态生成
                MDLabel:
                    id: nav_spots
                    size_hint_y: None
                    height: self.texture_size[1]
'''

# ============ 聊天气泡组件 ============
class ChatBubble(MDCard):
    is_user = False
    message_text = ""
    
    def __init__(self, text="", is_user=False, **kwargs):
        self.message_text = text
        self.is_user = is_user
        super().__init__(**kwargs)
        
        self.orientation = "vertical"
        self.size_hint_y = None
        self.padding = (12, 10, 12, 10)
        self.radius = [12, 12, 12, 12]
        self.elevation = 1
        
        label = MDLabel(
            text=text,
            font_style="Body1",
            size_hint_y=None,
            height=self._get_label_height(text),
            text_size=(None, None),
            theme_text_color="Custom" if is_user else "Primary",
            text_color=(1, 1, 1, 1) if is_user else (0, 0, 0, 1),
        )
        self.add_widget(label)
    
    def _get_label_height(self, text):
        # 估算文本高度
        lines = max(1, len(text) // 25 + text.count('\n'))
        return dp(20) * lines + dp(10)

# ============ 主 App ============
class BusanApp(MDApp):
    dialog = None
    
    def build(self):
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.theme_style = "Light"
        self.session_id = "mobile_user_001"
        return Builder.load_string(KV)
    
    def on_start(self):
        """App 启动后初始化"""
        # 添加欢迎消息
        self.add_bot_message(
            "👋 欢迎使用釜山沙下区文旅问答系统！\n\n"
            "试试输入：\n"
            "• 甘川文化村 概况\n"
            "• 多大浦海水浴场 怎么去\n"
            "• 沙下区有哪些景点"
        )
        
        # 在导航抽屉中填充景点按钮
        self._populate_nav_drawer()
    
    def _populate_nav_drawer(self):
        """在侧边栏填充景点快捷按钮"""
        nav_label = self.root.ids.nav_spots
        # 由于 KV 中 nav_spots 是 MDLabel，我们动态创建按钮
        # 获取导航抽屉的 menu 容器
        drawer = self.root.ids.nav_drawer
        menu = drawer.children[0] if drawer.children else None
        
        categories = list_categories()
        for cat_name, spots in categories.items():
            # 分类标题
            label = MDLabel(
                text=cat_name,
                font_style="Subtitle1",
                bold=True,
                size_hint_y=None,
                height=dp(36),
            )
            drawer.add_widget(label)
            
            for spot in spots:
                btn = MDFlatButton(
                    text=spot,
                    size_hint_y=None,
                    height=dp(40),
                    on_release=lambda x, s=spot: self.quick_ask(s),
                )
                drawer.add_widget(btn)
    
    def quick_ask(self, spot_name):
        """侧边栏快捷提问"""
        self.root.ids.input_field.text = f"{spot_name} 概况"
        self.root.ids.nav_drawer.set_state("close")
        self.send_message()
    
    def send_message(self):
        """发送消息"""
        text = self.root.ids.input_field.text.strip()
        if not text:
            return
        
        # 显示用户消息
        self.add_user_message(text)
        self.root.ids.input_field.text = ""
        
        # 滚动到底部
        self._scroll_to_bottom()
        
        # 在新线程中调用核心逻辑（避免 UI 卡顿）
        threading.Thread(
            target=self._get_reply,
            args=(text,),
            daemon=True
        ).start()
    
    def _get_reply(self, text):
        """后台获取回复"""
        try:
            reply = ask(text, session_id=self.session_id)
        except Exception as e:
            reply = f"❌ 出错了：{str(e)}"
        
        # 回到主线程更新 UI
        Clock.schedule_once(lambda dt: self._on_reply_ready(reply), 0)
    
    def _on_reply_ready(self, reply):
        """回复准备好后显示"""
        self.add_bot_message(reply)
        self._scroll_to_bottom()
    
    def add_user_message(self, text):
        """添加用户消息气泡"""
        bubble = ChatBubble(text=text, is_user=True)
        self.root.ids.chat_container.add_widget(bubble)
    
    def add_bot_message(self, text):
        """添加机器人消息气泡"""
        bubble = ChatBubble(text=text, is_user=False)
        self.root.ids.chat_container.add_widget(bubble)
    
    def _scroll_to_bottom(self):
        """滚动到底部"""
        Clock.schedule_once(lambda dt: setattr(
            self.root.ids.scroll_view, 'scroll_y', 0
        ), 0.1)
    
    def reset_chat(self):
        """重置对话"""
        self.root.ids.chat_container.clear_widgets()
        reset_session(self.session_id)
        self.add_bot_message("🔄 会话已重置。重新提问吧！")


# ============ 入口 ============
if __name__ == "__main__":
    BusanApp().run()