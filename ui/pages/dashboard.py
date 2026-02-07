import streamlit as st
import time
import subprocess
import sys
import pandas as pd
import os
import glob
from ui.utils import (
    load_json, save_json, normalize_time_input,
    TRACKING_FILE, SCHEDULE_FILE, SESSION_CONFIG_FILE, PROJECT_ROOT,
    ACCOUNTS_DIR
)

def get_all_account_configs():
    """Quét toàn bộ file json trong config/accounts"""
    if not os.path.exists(ACCOUNTS_DIR): os.makedirs(ACCOUNTS_DIR)
    files = glob.glob(os.path.join(ACCOUNTS_DIR, "*.json"))

    acc_list = []
    for f in files:
        data = load_json(f)
        data['_filename'] = os.path.basename(f)
        if "active" not in data: data["active"] = False
        acc_list.append(data)

    acc_list.sort(key=lambda x: x.get("id", ""))
    return acc_list

def update_account_file(filename, data):
    path = os.path.join(ACCOUNTS_DIR, filename)
    save_json(path, data)

def render_dashboard():
    st.markdown("## 🤖 Dashboard Điều khiển (Matrix Mode)")
    st.caption(f"Dữ liệu tài khoản load từ: `{ACCOUNTS_DIR}`")

    all_accounts = get_all_account_configs()
    schedule_data = load_json(SCHEDULE_FILE)

    if "crawl_times" not in schedule_data: schedule_data["crawl_times"] = ["07:00", "12:00"]
    if "nurture_windows" not in schedule_data: schedule_data["nurture_windows"] = []

    # --- KHU VỰC CHÍNH ---
    col_left, col_right = st.columns([1, 1.5], gap="large")
    selected_account_data = None
    selected_filename = None

    # === CỘT TRÁI ===
    with col_left:
        st.subheader("1. Chọn Tài khoản")
        st.info("💡 Click vào một dòng để xem chi tiết Kênh bên phải.")

        if all_accounts:
            df_acc = pd.DataFrame(all_accounts)

            # [FIX 1] Thay use_container_width=True thành width="stretch"
            selection = st.dataframe(
                df_acc,
                column_config={
                    "active": st.column_config.CheckboxColumn("Chạy?", width="small"),
                    "tiktok_id": st.column_config.TextColumn("ID TikTok", width="medium"),
                    "email": "Email",
                    "id": None,
                    "chrome_profile": None,
                    "video_limit_per_run": None,
                    "channels": None,
                    "_filename": None
                },
                width="stretch", # <--- ĐÃ SỬA TẠI ĐÂY
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row"
            )

            if selection.selection.rows:
                idx = selection.selection.rows[0]
                selected_account_data = all_accounts[idx]
                selected_filename = selected_account_data['_filename']
            elif all_accounts:
                selected_account_data = all_accounts[0]
                selected_filename = selected_account_data['_filename']
        else:
            st.warning("📭 Chưa có file cấu hình tài khoản nào.")

    # === CỘT PHẢI ===
    with col_right:
        st.subheader("2. Chi tiết & Kênh Clone")

        if selected_account_data:
            with st.container(border=True):
                c_head1, c_head2 = st.columns([3, 1])
                c_head1.markdown(f"#### 👤 {selected_account_data.get('tiktok_id', 'Unknown')}")
                c_head1.caption(f"Email: {selected_account_data.get('email')}")

                is_active = c_head2.toggle("Kích hoạt chạy", value=selected_account_data.get("active", False))

                if is_active != selected_account_data.get("active", False):
                    selected_account_data["active"] = is_active
                    update_account_file(selected_filename, selected_account_data)
                    st.toast(f"Đã {'BẬT' if is_active else 'TẮT'} tài khoản {selected_account_data['id']}")
                    time.sleep(0.5); st.rerun()

            channels = selected_account_data.get("channels", [])
            st.markdown(f"**Danh sách Kênh Nguồn ({len(channels)})**")

            if channels:
                df_chn = pd.DataFrame(channels)
                if "url" in df_chn.columns:
                    # [FIX 1] Thay use_container_width=True thành width="stretch"
                    st.dataframe(
                        df_chn[["url", "limit"]],
                        column_config={
                            "url": st.column_config.LinkColumn("Link Kênh Nguồn"),
                            "limit": st.column_config.NumberColumn("Số video/lần"),
                        },
                        width="stretch", # <--- ĐÃ SỬA TẠI ĐÂY
                        hide_index=True
                    )
                else:
                    st.info("Cấu trúc kênh chưa đúng.")
            else:
                st.warning("⚠️ Tài khoản này chưa thêm Kênh nguồn nào.")
        else:
            st.info("👈 Hãy chọn một tài khoản bên trái.")

    st.markdown("---")

    # --- ACTION BAR ---
    active_count = sum(1 for acc in all_accounts if acc.get("active"))

    col_act1, col_act2 = st.columns([3, 1])
    col_act1.metric("Số tài khoản đang KÍCH HOẠT chạy:", f"{active_count} / {len(all_accounts)}")

    # st.button vẫn dùng use_container_width được (theo document), nhưng nếu warning báo thì bỏ đi cũng được
    if col_act2.button("🚀 KHỞI ĐỘNG HỆ THỐNG", type="primary", use_container_width=True, disabled=(active_count==0)):
        script_path = os.path.join(PROJECT_ROOT, "scheduler_manager.py")
        if os.path.exists(script_path):
            st.toast("🚀 Đang khởi động Bot...")
            log_box = st.empty()
            try:
                cmd = [sys.executable, "-u", script_path]
                process = subprocess.Popen(cmd, cwd=PROJECT_ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8')
                full_log = ""
                while True:
                    line = process.stdout.readline()
                    if line:
                        full_log += line
                        log_box.code("\n".join(full_log.splitlines()[-10:]), language="bash")
                    if not line and process.poll() is not None: break
                st.success("Bot đã dừng.")
            except Exception as e: st.error(f"Lỗi: {e}")
        else:
            st.error("Không tìm thấy file scheduler_manager.py")