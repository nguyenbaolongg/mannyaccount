import streamlit as st
import os
import glob
import json
import time
import shutil

# --- IMPORT CÁC HÀM TỪ UTILS ---
from ui.utils import (
    ACCOUNTS_DIR, CONFIG_DIR, AI_STUDIO_DIR, FRAME_DIR,
    load_json, save_json, safe_show_image
)

# Đường dẫn file tổng hợp (QUAN TRỌNG)
ACCOUNTS_LIST_FILE = os.path.join(CONFIG_DIR, "tiktok_accounts.json")

# ================= CÁC HÀM HỖ TRỢ =================

def get_account_files():
    """Lấy danh sách các file .json trong folder accounts"""
    if not os.path.exists(ACCOUNTS_DIR):
        os.makedirs(ACCOUNTS_DIR)
    files = glob.glob(os.path.join(ACCOUNTS_DIR, "*.json"))
    return sorted([os.path.basename(f) for f in files])

def load_account_data(filename):
    path = os.path.join(ACCOUNTS_DIR, filename)
    return load_json(path)

def save_account_data(filename, data):
    path = os.path.join(ACCOUNTS_DIR, filename)
    save_json(path, data)

# --- [ĐÃ SỬA] Hàm đồng bộ file tổng ---
def sync_to_main_accounts_file(email, password, profile, tiktok_id, active=True):
    # Load file gốc hoặc tạo cấu trúc mới nếu chưa có
    if not os.path.exists(ACCOUNTS_LIST_FILE):
        main_data = {"accounts": []}
    else:
        main_data = load_json(ACCOUNTS_LIST_FILE)
        # Đảm bảo key "accounts" luôn tồn tại và là list
        if "accounts" not in main_data or not isinstance(main_data["accounts"], list):
            main_data["accounts"] = []

    accounts = main_data["accounts"]
    found = False

    # Tìm xem email đã tồn tại chưa để cập nhật
    # Ưu tiên tìm theo email, nếu không có thì tìm theo tiktok_id để tránh trùng lặp nếu đổi email
    target_index = -1
    for i, acc in enumerate(accounts):
        if acc.get("email") == email:
            target_index = i
            break
        # Fallback: tìm theo tiktok_id nếu email thay đổi nhưng id giữ nguyên (tùy logic business)
        # Ở đây ta bám sát email làm khóa chính như code cũ

    new_entry = {
        "email": email,
        "tiktok_id": tiktok_id,
        "password": password,
        "active": active,
        "chrome_profile": profile
    }

    if target_index >= 0:
        # Cập nhật entry cũ
        accounts[target_index] = new_entry
    else:
        # Thêm mới
        accounts.append(new_entry)

    save_json(ACCOUNTS_LIST_FILE, main_data)

def remove_from_main_accounts_file(email):
    """Xóa tài khoản khỏi file tổng"""
    if not os.path.exists(ACCOUNTS_LIST_FILE): return
    main_data = load_json(ACCOUNTS_LIST_FILE)
    if "accounts" not in main_data: return

    accounts = main_data["accounts"]
    new_accounts = [acc for acc in accounts if acc.get("email") != email]
    main_data["accounts"] = new_accounts
    save_json(ACCOUNTS_LIST_FILE, main_data)

def create_chrome_profile_folder(profile_name):
    """Tự động tạo thư mục Profile rỗng"""
    profile_path = os.path.join(AI_STUDIO_DIR, profile_name)
    if not os.path.exists(profile_path):
        os.makedirs(profile_path)
        return True
    return False

def delete_chrome_profile_folder(profile_name):
    if not profile_name: return False
    profile_path = os.path.join(AI_STUDIO_DIR, profile_name)
    if os.path.exists(profile_path):
        try:
            shutil.rmtree(profile_path)
            return True
        except Exception as e:
            return False
    return False

def rename_chrome_profile_folder(old_name, new_name):
    old_path = os.path.join(AI_STUDIO_DIR, old_name)
    new_path = os.path.join(AI_STUDIO_DIR, new_name)

    if os.path.exists(old_path):
        if not os.path.exists(new_path):
            try:
                os.rename(old_path, new_path)
                return True, "Success"
            except Exception as e:
                return False, str(e)
        else:
            return False, "Tên Profile mới đã tồn tại."
    return False, "Profile cũ không tồn tại."

# ================= RENDER UI =================

def render_account_manager():
    st.markdown("## 👤 Quản lý Tài khoản & Kênh Clone (Matrix Mode)")
    st.caption(f"Dữ liệu config chi tiết: `{ACCOUNTS_DIR}` | File tổng: `{ACCOUNTS_LIST_FILE}`")

    files = get_account_files()

    with st.container(border=True):
        col_sel1, col_sel2 = st.columns([3, 1])
        with col_sel1:
            options = ["➕ Tạo Tài khoản Mới"] + files
            selected_option = st.selectbox("👉 Chọn File Cấu hình Tài khoản:", options, index=0)
        with col_sel2:
            st.write("")
            st.write("")
            if st.button("🔄 Refresh", use_container_width=True):
                st.rerun()

    if selected_option == "➕ Tạo Tài khoản Mới":
        render_create_new()
    else:
        render_edit_account(selected_option)

def render_create_new():
    st.subheader("🆕 Tạo File Cấu hình Mới")
    st.info("Nhập thông tin bên dưới để tạo tài khoản. Hệ thống sẽ **TỰ ĐỘNG TẠO** Chrome Profile mới tương ứng.")

    with st.form("create_acc_form"):
        new_id = st.text_input("Nhập ID (Tên file config, viết liền không dấu):", placeholder="empowercongdongthammy20")

        c1, c2 = st.columns(2)
        tiktok_id = c1.text_input("TikTok Handle (@abc):", placeholder="@...")
        email = c2.text_input("Email quản trị (Dùng để login Google):", placeholder="email@domain.com")

        c3, c4 = st.columns(2)
        password = c3.text_input("Mật khẩu Email (Để login tự động):", type="password")

        profile_preview = ""
        if new_id:
            clean_id = "".join(x for x in new_id if x.isalnum() or x in "_-")
            profile_preview = f"{clean_id}_profile"

        c4.text_input("Chrome Profile (Tự động tạo):", value=profile_preview, disabled=True)

        if st.form_submit_button("🚀 Tạo ngay", type="primary"):
            if new_id and email:
                clean_id = "".join(x for x in new_id if x.isalnum() or x in "_-")
                filename = f"{clean_id}.json"
                auto_profile_name = f"{clean_id}_profile"

                is_created = create_chrome_profile_folder(auto_profile_name)

                # Dữ liệu lưu vào file chi tiết (config/accounts/xyz.json)
                default_data = {
                    "id": clean_id,
                    "tiktok_id": tiktok_id,
                    "email": email,
                    "password": password,
                    "chrome_profile": auto_profile_name,
                    "video_limit_per_run": 3,
                    "channels": []
                }

                full_path = os.path.join(ACCOUNTS_DIR, filename)
                if os.path.exists(full_path):
                    st.error("⚠️ File cấu hình ID này đã tồn tại!")
                else:
                    # 1. Lưu file config riêng
                    save_json(full_path, default_data)

                    # 2. Đồng bộ vào file tổng tiktok_accounts.json
                    sync_to_main_accounts_file(email, password, auto_profile_name, tiktok_id)

                    msg = f"✅ Đã tạo tài khoản: **{filename}**"
                    if is_created:
                        msg += f"\n✅ Đã tạo folder Chrome: **{auto_profile_name}**"
                    msg += f"\n✅ Đã cập nhật vào file tổng: **tiktok_accounts.json**"

                    st.success(msg)
                    time.sleep(1.5); st.rerun()
            else:
                st.warning("Vui lòng nhập ID và Email.")

def render_edit_account(filename):
    data = load_account_data(filename)
    old_id = data.get("id", filename.replace(".json", ""))
    old_profile = data.get("chrome_profile", "")

    st.divider()
    col_title, col_del = st.columns([3, 1.5])
    with col_title:
        st.subheader(f"🛠️ Đang sửa: `{filename}`")
    with col_del:
        if st.button("🗑️ Xóa Tài khoản", key="del_acc_btn", type="primary", use_container_width=True):
            profile_to_delete = data.get("chrome_profile", "")
            try:
                os.remove(os.path.join(ACCOUNTS_DIR, filename))
            except: pass

            if "email" in data:
                remove_from_main_accounts_file(data["email"])

            if profile_to_delete:
                delete_chrome_profile_folder(profile_to_delete)

            st.success("✅ Đã xóa hoàn toàn.")
            time.sleep(1); st.rerun()

    # --- INFO ---
    with st.expander("ℹ️ Thông tin Tài khoản", expanded=True):
        c_id, c_prof = st.columns(2)
        new_id_input = c_id.text_input("ID Định danh:", value=old_id)
        new_profile_input = c_prof.text_input("Chrome Profile Folder:", value=old_profile)

        c1, c2 = st.columns(2)
        new_tiktok_id = c1.text_input("TikTok Handle:", value=data.get("tiktok_id", ""))
        new_email = c2.text_input("Email:", value=data.get("email", ""))

        c3, c4 = st.columns(2)
        new_password = c3.text_input("Password:", value=data.get("password", ""), type="password")
        new_limit = c4.number_input("Limit Video:", min_value=1, max_value=50, value=data.get("video_limit_per_run", 3))

    # --- CHANNELS ---
    st.write("")
    st.subheader(f"📺 Danh sách Kênh Nguồn ({len(data.get('channels', []))})")

    if st.button("➕ Thêm Kênh Nguồn Mới"):
        new_channel_template = {
            "url": "", "limit": 3,
            "render_settings": {
                "title_settings": {"source_start": 2.0, "source_end": 7.0, "zoom_factor": 1.0, "manual_x_offset": 0, "manual_y_offset": 250},
                "content_settings": {"source_start": 9.0, "source_end": "auto", "zoom_factor": 1.05, "manual_x_offset": 0, "manual_y_offset": 0},
                "text_overlay_settings": {"font_filename": "Inter_18pt-Bold.ttf", "font_size": 45, "text_color": "#ffffff"},
                "text_content_settings": {"font_filename": "Inter_18pt-Bold.ttf", "font_size": 45, "text_color": "#ffffff"},
                "assets": {"title_frame_filename": "", "content_frame_filename": "", "logo_filename": ""}
            }
        }
        data.setdefault("channels", []).append(new_channel_template)
        save_account_data(filename, data)
        st.rerun()

    channels = data.get("channels", [])
    channels_to_remove = []

    for i, chn in enumerate(channels):
        channel_label = chn.get('url', f'Kênh #{i+1}')
        if not channel_label: channel_label = f"Kênh Trống #{i+1}"
        with st.expander(f"📡 {channel_label}", expanded=False):
            c_url, c_lim, c_del = st.columns([3, 1, 0.5])
            chn["url"] = c_url.text_input(f"Link TikTok #{i+1}", value=chn.get("url", ""))
            chn["limit"] = c_lim.number_input(f"Số lượng #{i+1}", 1, 20, value=chn.get("limit", 3))

            if c_del.button("❌", key=f"del_chn_{i}"): channels_to_remove.append(i)

            st.caption("⚙️ Cấu hình Render (Dùng Menu 'Quản lý Kênh' để sửa chi tiết)")
            chn["render_settings"] = chn.get("render_settings", {})

    if channels_to_remove:
        for idx in sorted(channels_to_remove, reverse=True): channels.pop(idx)
        save_account_data(filename, data)
        st.rerun()

    st.divider()

    # --- SAVE BUTTON ---
    if st.button("💾 Cập nhật Tài khoản", type="primary", use_container_width=True):
        data["id"] = new_id_input
        data["tiktok_id"] = new_tiktok_id
        data["email"] = new_email
        data["password"] = new_password
        data["video_limit_per_run"] = new_limit
        data["channels"] = channels

        final_profile_name = old_profile
        if new_profile_input and new_profile_input != old_profile:
            success, msg = rename_chrome_profile_folder(old_profile, new_profile_input)
            if success:
                st.toast(f"✅ Đã đổi tên folder Chrome: {new_profile_input}")
                final_profile_name = new_profile_input
            else:
                st.error(f"❌ Lỗi đổi tên Profile: {msg}"); return

        data["chrome_profile"] = final_profile_name

        final_filename = filename
        if new_id_input and new_id_input != old_id:
            new_filename = f"{new_id_input}.json"
            new_path = os.path.join(ACCOUNTS_DIR, new_filename)
            old_path = os.path.join(ACCOUNTS_DIR, filename)

            if os.path.exists(new_path):
                st.error(f"❌ ID '{new_id_input}' đã tồn tại!"); return
            else:
                try:
                    os.rename(old_path, new_path)
                    final_filename = new_filename
                    st.toast(f"✅ Đã đổi tên File Config: {new_filename}")
                except Exception as e:
                    st.error(f"Lỗi đổi tên file: {e}"); return

        save_account_data(final_filename, data)

        if new_email:
            # [QUAN TRỌNG] Đồng bộ file tổng mỗi khi cập nhật
            sync_to_main_accounts_file(
                new_email,
                new_password,
                final_profile_name,
                new_tiktok_id,
                active=True
            )

        st.success(f"✅ Đã cập nhật thành công!"); time.sleep(1.5); st.rerun()