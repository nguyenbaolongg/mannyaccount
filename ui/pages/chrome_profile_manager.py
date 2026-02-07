import streamlit as st
import os
import shutil
import time
import sys
import asyncio
import json
from ui.utils import AI_STUDIO_DIR
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USER_SETTINGS_FILE = os.path.join(PROJECT_ROOT, "user_settings.json")

def load_user_settings():
    """Đọc file user_settings.json"""
    if not os.path.exists(USER_SETTINGS_FILE): return {}
    try:
        with open(USER_SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except: return {}
settings = load_user_settings()
ai_studio_url = settings.get("ai_studio_url")
def launch_chrome_for_profile(profile_name):
    """Mở trình duyệt Chrome với profile được chọn để người dùng thao tác"""

    # [FIX] SỬA LỖI NotImplementedError TRÊN WINDOWS
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    from playwright.sync_api import sync_playwright

    profile_path = os.path.join(AI_STUDIO_DIR, profile_name)
    if not os.path.exists(profile_path):
        os.makedirs(profile_path)

    status_placeholder = st.empty()
    status_placeholder.info(f"⏳ Đang khởi động Chrome cho profile: **{profile_name}**...")

    try:
        with sync_playwright() as p:
            # [FIX QUAN TRỌNG] Cấu hình để Google không phát hiện Bot
            # 1. ignore_default_args: Tắt dòng "Chrome is being controlled..."
            # 2. args: Tắt blink features báo hiệu automation

            browser = p.chromium.launch_persistent_context(
                user_data_dir=profile_path,
                headless=False,
                channel="chrome",
                args=[
                    "--start-maximized",
                    "--disable-blink-features=AutomationControlled", # Quan trọng nhất để lách Google
                    "--no-sandbox",
                    "--disable-infobars",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--no-first-run"
                ],
                ignore_default_args=["--enable-automation"], # Ẩn thanh thông báo automation
                viewport=None
            )

            page = browser.pages[0]

            # [FIX BỔ SUNG] Chạy script JS để xóa dấu vết navigator.webdriver
            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)

            page.goto("https://ai.studio/apps/drive/19hSBlGZnlzgyM87oebek8LaI64-346kK?fullscreenApplet=true")

            status_placeholder.success(f"🟢 **Chrome đang chạy ({profile_name})!**")
            st.warning("👉 Hãy Đăng nhập Google/AI Studio trên cửa sổ Chrome đó.\n\n❌ **SAU KHI XONG, HÃY TẮT CỬA SỔ CHROME ĐỂ LƯU.**")

            # Vòng lặp chờ đóng trình duyệt
            while True:
                try:
                    if not browser.pages: break
                    page.wait_for_timeout(1000)
                except: break

            status_placeholder.success(f"✅ Đã lưu Profile: **{profile_name}**")
            time.sleep(2)

    except Exception as e:
        st.error(f"❌ Lỗi mở Chrome: {e}")
        st.caption("Gợi ý: Hãy tắt hết các cửa sổ Chrome đang chạy ngầm rồi thử lại.")

def render_chrome_profile_manager():
    st.markdown("## 🌐 Quản lý Chrome Profiles")
    st.caption("Tạo, Sửa (Đăng nhập lại) hoặc Xóa các Profile Chrome.")

    # --- KHU VỰC 1: TẠO MỚI ---
    with st.expander("➕ **Thêm Profile Mới (Đăng nhập Google)**", expanded=True):
        c1, c2 = st.columns([3, 1])
        new_profile_name = c1.text_input("Đặt tên Profile mới (VD: Acc_Main):", key="in_new_pro_name")

        if c2.button("🚀 Tạo & Mở Chrome", type="primary", use_container_width=True):
            if new_profile_name:
                clean_name = "".join([c for c in new_profile_name if c.isalnum() or c in (' ', '_', '-')]).strip()
                if clean_name:
                    full_path = os.path.join(AI_STUDIO_DIR, clean_name)
                    if os.path.exists(full_path):
                        st.error("⚠️ Tên Profile này đã tồn tại!")
                    else:
                        launch_chrome_for_profile(clean_name)
                        st.rerun()
                else: st.error("Tên không hợp lệ.")
            else: st.warning("Vui lòng nhập tên Profile.")

    st.divider()

    # --- KHU VỰC 2: DANH SÁCH ---
    st.subheader("📂 Danh sách Profile hiện có")

    if not os.path.exists(AI_STUDIO_DIR): os.makedirs(AI_STUDIO_DIR)
    profiles = [d for d in os.listdir(AI_STUDIO_DIR) if os.path.isdir(os.path.join(AI_STUDIO_DIR, d))]
    profiles.sort()

    if not profiles:
        st.info("📭 Chưa có Profile nào.")
    else:
        for p in profiles:
            col_info, col_action1, col_action2 = st.columns([3, 1.5, 1])
            with col_info:
                st.markdown(f"👤 **{p}**")
            with col_action1:
                if st.button(f"🔧 Mở Login", key=f"edit_{p}"):
                    launch_chrome_for_profile(p)
            with col_action2:
                if st.button("🗑️ Xóa", key=f"del_{p}"):
                    try:
                        shutil.rmtree(os.path.join(AI_STUDIO_DIR, p))
                        st.success(f"Đã xóa: {p}")
                        time.sleep(1); st.rerun()
                    except PermissionError:
                        st.error("❌ Profile đang mở!")
                    except Exception as e:
                        st.error(f"Lỗi: {e}")
            st.markdown("---")