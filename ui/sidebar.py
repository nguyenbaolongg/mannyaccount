import streamlit as st
import os

def render_sidebar():
    with st.sidebar:
        st.header("⚙️ EVERAI SYSTEM")
        st.divider()

        # MENU CHÍNH
        selected_page = st.radio(
            "DANH MỤC QUẢN LÝ:",
            [
                "🤖 Dashboard (Chạy Bot)",
                "👤 Quản lý Tài khoản TikTok",
                "📺 Quản lý Kênh Clone",
                "🌐 Quản lý Chrome Profile",
                "🔑 Cấu hình API & Hệ thống",
                "🔐 Google Credentials"
            ],
            index=0,
            key="sidebar_main_nav"
        )

        st.divider()
        st.caption("v6.3 - Matrix Mode")

        return selected_page