import streamlit as st
import sys
import os

# Thêm đường dẫn root để import các module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import các trang từ module con
from ui.pages.dashboard import render_dashboard
from ui.pages.account_manager import render_account_manager
from ui.pages.channel_manager import render_channel_manager
from ui.pages.chrome_profile_manager import render_chrome_profile_manager
from ui.pages.api_settings import render_api_settings
from ui.pages.google_auth_manager import render_google_auth_manager
def render_main_ui():
    st.set_page_config(page_title="Auto Clone Bot", layout="wide", page_icon="🤖")

    # Gọi sidebar từ module tách biệt
    from ui.sidebar import render_sidebar
    selection = render_sidebar()

    # Điều hướng trang dựa trên lựa chọn
    if selection == "🤖 Dashboard (Chạy Bot)":
        render_dashboard()
    elif selection == "👤 Quản lý Tài khoản TikTok":
        render_account_manager()
    elif selection == "📺 Quản lý Kênh Clone":
        render_channel_manager()
    elif selection == "🌐 Quản lý Chrome Profile":
        render_chrome_profile_manager()
    elif selection == "🔑 Cấu hình API & Hệ thống":
        render_api_settings()
    elif selection == "🔐 Google Credentials":
        render_google_auth_manager()

if __name__ == "__main__":
    render_main_ui()