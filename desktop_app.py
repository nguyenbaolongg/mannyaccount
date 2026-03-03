import customtkinter as ctk
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.append(PROJECT_ROOT)

from desktop_ui.pages.dashboard import DashboardPage
from desktop_ui.pages.api_settings import ApiSettingsPage
from desktop_ui.pages.account_manager import AccountManagerPage
from desktop_ui.pages.channel_manager import ChannelManagerPage
from desktop_ui.pages.clone_channels_page import CloneChannelsPage

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class MatrixBotApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Matrix Bot")
        self.geometry("1200x750")

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.sidebar_frame = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(7, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text=" MATRIX BOT", font=ctk.CTkFont(size=24, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(30, 20))

        self.btn_dashboard = ctk.CTkButton(self.sidebar_frame, text="Dashboard (Chạy Bot)", command=self.show_dashboard)
        self.btn_dashboard.grid(row=1, column=0, padx=20, pady=10, sticky="ew")

        self.btn_accounts = ctk.CTkButton(self.sidebar_frame, text="Quản lý Tài khoản", command=self.show_accounts)
        self.btn_accounts.grid(row=2, column=0, padx=20, pady=10, sticky="ew")

        self.btn_channels = ctk.CTkButton(self.sidebar_frame, text="Quản lý Kênh", command=self.show_channels)
        self.btn_channels.grid(row=3, column=0, padx=20, pady=10, sticky="ew")

        self.btn_clone_channels = ctk.CTkButton(self.sidebar_frame, text="Làm video qua link", command=self.show_clone_channels)
        self.btn_clone_channels.grid(row=4, column=0, padx=20, pady=10, sticky="ew")

        self.btn_api = ctk.CTkButton(self.sidebar_frame, text="Cấu hình API", command=self.show_api_settings)
        self.btn_api.grid(row=5, column=0, padx=20, pady=10, sticky="ew")

        self.main_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        self.dashboard_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.dashboard_frame.grid(row=0, column=0, sticky="nsew")
        self.dashboard_page = DashboardPage(self.dashboard_frame)

        self.show_dashboard()

    def clear_dynamic_frames(self):
        """Xóa các trang khác nhưng CHỈ ẨN Dashboard để giữ Bot chạy ngầm"""
        for widget in self.main_frame.winfo_children():
            if widget == self.dashboard_frame:
                widget.grid_remove()
            else:
                widget.destroy()

    def show_dashboard(self):
        self.clear_dynamic_frames()
        self.dashboard_frame.grid()

        if hasattr(self.dashboard_page, 'load_accounts'):
            self.dashboard_page.load_accounts()

    def show_accounts(self):
        self.clear_dynamic_frames()
        frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="nsew")
        AccountManagerPage(frame)

    def show_channels(self):
        self.clear_dynamic_frames()
        frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="nsew")
        ChannelManagerPage(frame)

    def show_clone_channels(self):
        self.clear_dynamic_frames()
        frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="nsew")
        CloneChannelsPage(frame)

    def show_api_settings(self):
        self.clear_dynamic_frames()
        frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="nsew")
        ApiSettingsPage(frame)

    def on_closing(self):
        try:
            if hasattr(self, 'dashboard_page') and self.dashboard_page.bot_process is not None:
                self.dashboard_page.stop_bot()
        except Exception as e:
            print(f"Lỗi khi đóng app: {e}")
        finally:
            self.destroy() # Đóng hoàn toàn giao diện

if __name__ == "__main__":
    app = MatrixBotApp()
    app.mainloop()