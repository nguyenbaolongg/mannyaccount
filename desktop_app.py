import customtkinter as ctk
import os
import sys

# Đảm bảo import được các module trong dự án
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.append(PROJECT_ROOT)

from desktop_ui.pages.dashboard import DashboardPage
from desktop_ui.pages.api_settings import ApiSettingsPage
from desktop_ui.pages.account_manager import AccountManagerPage
from desktop_ui.pages.channel_manager import ChannelManagerPage
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class MatrixBotApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.geometry("1200x750")

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.sidebar_frame = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(7, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text=" MATRIX BOT", font=ctk.CTkFont(size=24, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(30, 20))

        # Các nút Menu
        # Các nút Menu
        self.btn_dashboard = ctk.CTkButton(self.sidebar_frame, text="Dashboard (Chạy Bot)", command=self.show_dashboard)
        self.btn_dashboard.grid(row=1, column=0, padx=20, pady=10, sticky="ew")

        # [ĐÃ SỬA] Kích hoạt lệnh cho nút Tài khoản
        self.btn_accounts = ctk.CTkButton(self.sidebar_frame, text="Quản lý Tài khoản", command=self.show_accounts)
        self.btn_accounts.grid(row=2, column=0, padx=20, pady=10, sticky="ew")

        # [ĐÃ SỬA] Kích hoạt lệnh cho nút Kênh
        self.btn_channels = ctk.CTkButton(self.sidebar_frame, text="Quản lý Kênh", command=self.show_channels)
        self.btn_channels.grid(row=3, column=0, padx=20, pady=10, sticky="ew")

        self.btn_api = ctk.CTkButton(self.sidebar_frame, text="Cấu hình API", command=self.show_api_settings)
        self.btn_api.grid(row=4, column=0, padx=20, pady=10, sticky="ew")

        # ================= MAIN FRAME =================
        self.main_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")

        self.show_dashboard()

    def clear_main_frame(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()

    def show_dashboard(self):
        self.clear_main_frame()
        DashboardPage(self.main_frame)

    def show_api_settings(self):
        self.clear_main_frame()
        ApiSettingsPage(self.main_frame)

    def show_accounts(self):
        self.clear_main_frame()
        AccountManagerPage(self.main_frame)

    def show_channels(self):
        self.clear_main_frame()
        ChannelManagerPage(self.main_frame)

if __name__ == "__main__":
    app = MatrixBotApp()
    app.mainloop()