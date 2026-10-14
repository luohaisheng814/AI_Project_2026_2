"""
CustomTkinter 桌面版 UI
只调用 core_api.ask()，适配字典格式
"""

import customtkinter as ctk
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core_api import ask, reset_session

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class BusanQADesktop(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("釜山沙下区文旅智能问答 V2.0")
        self.geometry("800x600")
        self.session_id = "desktop_user_001"
        
        # 标题
        self.title_label = ctk.CTkLabel(
            self, 
            text="🍊 釜山沙下区文旅智能问答", 
            font=ctk.CTkFont(size=22, weight="bold")
        )
        self.title_label.pack(pady=(15, 5))
        
        # 输入框
        self.input_frame = ctk.CTkFrame(self)
        self.input_frame.pack(pady=10, padx=20, fill="x")
        
        self.user_input = ctk.CTkEntry(
            self.input_frame, 
            placeholder_text="输入问题（如：甘川文化村 概况）...", 
            height=40
        )
        self.user_input.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.send_btn = ctk.CTkButton(
            self.input_frame, 
            text="发送", 
            command=self.send_message, 
            height=40,
            width=80
        )
        self.send_btn.pack(side="right")
        
        # 绑定回车键
        self.user_input.bind("<Return>", self.send_message_event)
        
        # 聊天记录显示框
        self.chatbox = ctk.CTkTextbox(self, wrap="word", font=ctk.CTkFont(size=14))
        self.chatbox.pack(pady=10, padx=20, fill="both", expand=True)
        self.chatbox.configure(state="disabled") # 默认不可编辑
        
        # 清空按钮
        self.clear_btn = ctk.CTkButton(
            self, 
            text="清空记录", 
            command=self.clear_history, 
            fg_color="transparent", 
            border_width=1
        )
        self.clear_btn.pack(pady=10)

    def send_message(self):
        user_text = self.user_input.get().strip()
        if not user_text:
            return
            
        # 显示用户消息
        self.update_chatbox(f"你: {user_text}\n")
        self.user_input.delete(0, "end")
        
        # 调用 core_api 获取回复（确保返回的是纯字符串）
        bot_reply = ask(user_text, self.session_id)
        
        # 显示机器人回复
        self.update_chatbox(f"🤖: {bot_reply}\n\n")

    def send_message_event(self, event):
        self.send_message()

    def update_chatbox(self, message):
        self.chatbox.configure(state="normal")
        self.chatbox.insert("end", message)
        self.chatbox.configure(state="disabled")
        self.chatbox.see("end") # 自动滚动到底部

    def clear_history(self):
        self.chatbox.configure(state="normal")
        self.chatbox.delete("1.0", "end")
        self.chatbox.configure(state="disabled")
        reset_session(self.session_id)

if __name__ == "__main__":
    app = BusanQADesktop()
    app.mainloop()