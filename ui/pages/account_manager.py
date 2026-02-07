import streamlit as st
import os
import glob
import json
import time
from ui.utils import ACCOUNTS_DIR, load_json, save_json, FRAME_DIR, save_frame_image, safe_show_image, CONFIG_DIR

# Đường dẫn file tổng hợp
ACCOUNTS_LIST_FILE = os.path.join(CONFIG_DIR, "tiktok_accounts.json")

def get_account_files():
    """Lấy danh sách các file .json trong folder accounts"""
    if not os.path.exists(ACCOUNTS_DIR):
        os.makedirs(ACCOUNTS_DIR)
    files = glob.glob(os.path.join(ACCOUNTS_DIR, "*.json"))
    return sorted([os.path.basename(f) for f in files])

def load_account_data(filename):
    """Load dữ liệu của 1 account cụ thể"""
    path = os.path.join(ACCOUNTS_DIR, filename)
    return load_json(path)

def save_account_data(filename, data):
    """Lưu dữ liệu vào file json riêng biệt"""
    path = os.path.join(ACCOUNTS_DIR, filename)
    save_json(path, data)

def sync_to_main_accounts_file(email, password, profile, active=True):

    if not os.path.exists(ACCOUNTS_LIST_FILE):
        # Nếu chưa có file, tạo mới
        main_data = {"current_index": 0, "accounts": []}
    else:
        main_data = load_json(ACCOUNTS_LIST_FILE)
        if "accounts" not in main_data: main_data["accounts"] = []

    accounts = main_data["accounts"]

    # Kiểm tra xem email đã tồn tại chưa
    found = False
    for acc in accounts:
        if acc.get("email") == email:
            # Cập nhật thông tin mới nhất
            acc["password"] = password
            acc["chrome_profile"] = profile
            acc["active"] = active
            found = True
            break

    if not found:
        # Thêm mới
        accounts.append({
            "email": email,
            "password": password,
            "active": active,
            "chrome_profile": profile
        })

    save_json(ACCOUNTS_LIST_FILE, main_data)

def remove_from_main_accounts_file(email):
    """Xóa tài khoản khỏi file tổng"""
    if not os.path.exists(ACCOUNTS_LIST_FILE): return

    main_data = load_json(ACCOUNTS_LIST_FILE)
    accounts = main_data.get("accounts", [])

    # Lọc bỏ tài khoản có email tương ứng
    new_accounts = [acc for acc in accounts if acc.get("email") != email]

    main_data["accounts"] = new_accounts
    save_json(ACCOUNTS_LIST_FILE, main_data)

def render_account_manager():
    st.markdown("## 👤 Quản lý Tài khoản & Kênh Clone (Matrix Mode)")
    st.caption(f"Dữ liệu lưu tại: `{ACCOUNTS_DIR}`. Đồng bộ với: `{ACCOUNTS_LIST_FILE}`")

    # --- SIDEBAR: DANH SÁCH TÀI KHOẢN ---
    files = get_account_files()

    with st.sidebar:
        st.subheader("📂 Danh sách Tài khoản")
        options = ["➕ Tạo Tài khoản Mới"] + files
        selected_option = st.radio("Chọn file cấu hình:", options)

    # --- LOGIC GIAO DIỆN ---
    if selected_option == "➕ Tạo Tài khoản Mới":
        render_create_new()
    else:
        render_edit_account(selected_option)

def render_create_new():
    st.subheader("🆕 Tạo File Cấu hình Mới")
    with st.form("create_acc_form"):
        new_id = st.text_input("Nhập ID (Tên file config, viết liền không dấu):", placeholder="empowercongdongthammy20")

        c1, c2 = st.columns(2)
        tiktok_id = c1.text_input("TikTok Handle (@abc):", placeholder="@...")
        email = c2.text_input("Email quản trị (Dùng để login Google):", placeholder="email@domain.com")

        c3, c4 = st.columns(2)
        password = c3.text_input("Mật khẩu Email (Để login tự động):", type="password")
        profile = c4.text_input("Chrome Profile Folder Name:", placeholder="Profile_01")

        if st.form_submit_button("🚀 Tạo ngay", type="primary"):
            if new_id and email:
                clean_id = "".join(x for x in new_id if x.isalnum() or x in "_-")
                filename = f"{clean_id}.json"

                # 1. Lưu file config chi tiết
                default_data = {
                    "id": clean_id,
                    "tiktok_id": tiktok_id,
                    "email": email,
                    "password": password, # Lưu pass vào đây để tiện hiển thị lại
                    "chrome_profile": profile,
                    "video_limit_per_run": 3,
                    "channels": []
                }

                full_path = os.path.join(ACCOUNTS_DIR, filename)
                if os.path.exists(full_path):
                    st.error("⚠️ File cấu hình ID này đã tồn tại!")
                else:
                    save_json(full_path, default_data)

                    # 2. Đồng bộ sang file accounts.json tổng
                    sync_to_main_accounts_file(email, password, profile)

                    st.success(f"Đã tạo: {filename} và đồng bộ vào danh sách tổng.")
                    time.sleep(1); st.rerun()
            else:
                st.warning("Vui lòng nhập ID và Email.")

def render_edit_account(filename):
    data = load_account_data(filename)

    st.divider()
    col_title, col_del = st.columns([4, 1])
    with col_title:
        st.subheader(f"🛠️ Đang sửa: `{filename}`")
    with col_del:
        if st.button("🗑️ Xóa File", key="del_file", type="primary"):
            # Xóa file chi tiết
            os.remove(os.path.join(ACCOUNTS_DIR, filename))
            # Xóa khỏi file tổng
            if "email" in data:
                remove_from_main_accounts_file(data["email"])

            st.success("Đã xóa file và đồng bộ lại danh sách tổng."); time.sleep(1); st.rerun()

    # --- PHẦN 1: THÔNG TIN CƠ BẢN ---
    with st.expander("ℹ️ Thông tin Tài khoản (Basic Info)", expanded=True):
        c1, c2 = st.columns(2)
        data["tiktok_id"] = c1.text_input("TikTok Handle:", data.get("tiktok_id", ""))
        data["email"] = c2.text_input("Email:", data.get("email", ""))

        c3, c4 = st.columns(2)
        data["password"] = c3.text_input("Password:", data.get("password", ""), type="password")
        data["chrome_profile"] = c4.text_input("Chrome Profile:", data.get("chrome_profile", ""))

        data["video_limit_per_run"] = st.number_input("Số video clone mỗi lần chạy:", 1, 50, data.get("video_limit_per_run", 3))

    # --- PHẦN 2: QUẢN LÝ KÊNH (CHANNELS) ---
    st.write("")
    st.subheader(f"📺 Danh sách Kênh Nguồn ({len(data.get('channels', []))})")

    if st.button("➕ Thêm Kênh Nguồn Mới"):
        new_channel_template = {
            "url": "",
            "limit": 3,
            "render_settings": {
                "title_settings": {"source_start": 2.0, "source_end": 7.0, "zoom_factor": 1.0, "manual_y_offset": 250},
                "content_settings": {"source_start": 9.0, "source_end": "auto", "zoom_factor": 1.05, "manual_y_offset": 0},
                "text_overlay_settings": {"font_filename": "Inter_18pt-Bold.ttf", "font_size": 45, "text_color": "#ffffff"},
                "text_content_settings": {"font_filename": "Inter_18pt-Bold.ttf", "font_size": 45, "text_color": "#ffffff"},
                "assets": {"title_frame_filename": "", "content_frame_filename": "", "logo_filename": ""}
            }
        }
        data.setdefault("channels", []).append(new_channel_template)
        save_account_data(filename, data)
        st.rerun()

    channels = data.get("channels", [])
    for i, chn in enumerate(channels):
        chn_url = chn.get("url", "Chưa nhập Link")
        label = f"#{i+1}: {chn_url}"

        with st.expander(label, expanded=False):
            c_url, c_lim, c_del_chn = st.columns([3, 1, 0.5])
            chn["url"] = c_url.text_input(f"Link Kênh Nguồn #{i+1}", chn.get("url", ""))
            chn["limit"] = c_lim.number_input(f"Limit #{i+1}", 1, 20, chn.get("limit", 3))

            if c_del_chn.button("❌", key=f"del_chn_{i}"):
                channels.pop(i)
                save_account_data(filename, data)
                st.rerun()

            st.markdown("🎛️ **Cấu hình Render**")
            rs = chn.get("render_settings", {})

            t1, t2, t3, t4 = st.tabs(["Intro", "Content", "Text", "Assets"])

            with t1:
                ts = rs.get("title_settings", {})
                tc1, tc2 = st.columns(2)
                ts["source_start"] = tc1.number_input(f"In.Start #{i}", 0.0, 60.0, float(ts.get("source_start", 2.0)))
                ts["source_end"] = tc1.number_input(f"In.End #{i}", 0.0, 60.0, float(ts.get("source_end", 7.0)))
                ts["zoom_factor"] = tc2.number_input(f"In.Zoom #{i}", 1.0, 3.0, float(ts.get("zoom_factor", 1.0)))
                ts["manual_y_offset"] = tc2.number_input(f"In.Y-Off #{i}", -500, 500, int(ts.get("manual_y_offset", 250)))
                rs["title_settings"] = ts

            with t2:
                cs = rs.get("content_settings", {})
                cc1, cc2 = st.columns(2)
                cs["source_start"] = cc1.number_input(f"Co.Start #{i}", 0.0, 300.0, float(cs.get("source_start", 9.0)))
                val_end = cs.get("source_end", "auto")
                str_end = cc1.text_input(f"Co.End #{i}", str(val_end))
                cs["source_end"] = float(str_end) if str_end.replace('.','',1).isdigit() else "auto"
                cs["zoom_factor"] = cc2.number_input(f"Co.Zoom #{i}", 1.0, 3.0, float(cs.get("zoom_factor", 1.05)))
                cs["manual_y_offset"] = cc2.number_input(f"Co.Y-Off #{i}", -500, 500, int(cs.get("manual_y_offset", 0)))
                rs["content_settings"] = cs

            with t3:
                tx = rs.get("text_overlay_settings", {})
                c_tx1, c_tx2 = st.columns(2)
                tx["font_filename"] = c_tx1.text_input(f"Font #{i}", tx.get("font_filename", "Inter_18pt-Bold.ttf"))
                tx["font_size"] = c_tx1.number_input(f"Size #{i}", 10, 100, int(tx.get("font_size", 45)))
                tx["text_color"] = c_tx2.color_picker(f"Color #{i}", tx.get("text_color", "#ffffff"))
                rs["text_overlay_settings"] = tx

                txc = rs.get("text_content_settings", {})
                txc["font_filename"] = tx["font_filename"]
                txc["font_size"] = tx["font_size"]
                txc["text_color"] = tx["text_color"]
                rs["text_content_settings"] = txc

            with t4:
                ast = rs.get("assets", {})
                ca1, ca2 = st.columns(2)
                with ca1:
                    cur_fri = ast.get("title_frame_filename", "")
                    if cur_fri: safe_show_image(os.path.join(FRAME_DIR, cur_fri))
                    up_fri = st.file_uploader("Up Intro", key=f"up_fri_{i}_{filename}")
                    if up_fri:
                        fname = save_frame_image(up_fri)
                        if fname: ast["title_frame_filename"] = fname
                    else: ast["title_frame_filename"] = st.text_input(f"File Intro #{i}", cur_fri)

                with ca2:
                    cur_frc = ast.get("content_frame_filename", "")
                    if cur_frc: safe_show_image(os.path.join(FRAME_DIR, cur_frc))
                    up_frc = st.file_uploader("Up Content", key=f"up_frc_{i}_{filename}")
                    if up_frc:
                        fname = save_frame_image(up_frc)
                        if fname: ast["content_frame_filename"] = fname
                    else: ast["content_frame_filename"] = st.text_input(f"File Content #{i}", cur_frc)

                ast["logo_filename"] = st.text_input(f"Logo #{i}", ast.get("logo_filename", ""))
                rs["assets"] = ast

            chn["render_settings"] = rs
            st.markdown("---")

    st.divider()
    if st.button("💾 LƯU TOÀN BỘ CẤU HÌNH TÀI KHOẢN", type="primary", use_container_width=True):
        data["channels"] = channels

        # 1. Lưu file chi tiết
        save_account_data(filename, data)

        # 2. Đồng bộ file tổng
        if "email" in data and "password" in data:
            sync_to_main_accounts_file(
                data["email"],
                data["password"],
                data.get("chrome_profile", ""),
                active=True # Mặc định active khi vừa lưu
            )

        st.success(f"✅ Đã lưu cấu hình vào: config/accounts/{filename} và đồng bộ file tổng.")
        time.sleep(1)