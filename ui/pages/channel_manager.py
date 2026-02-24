import streamlit as st
import time
import os
import glob
from ui.utils import (
    load_json, save_json, save_frame_image, safe_show_image,
    FRAME_DIR, ACCOUNTS_DIR
)

def get_all_account_files():
    """Lấy danh sách file và mapping tiktok_id -> filename"""
    if not os.path.exists(ACCOUNTS_DIR): os.makedirs(ACCOUNTS_DIR)
    files = glob.glob(os.path.join(ACCOUNTS_DIR, "*.json"))

    acc_map = {}
    for f in files:
        data = load_json(f)
        # Ưu tiên lấy ID làm key, nếu không có thì lấy filename
        key = data.get("id", os.path.basename(f).replace(".json", ""))
        acc_map[key] = os.path.basename(f)
    return acc_map

def update_account_channels(filename, action="add", channel_data=None, index=None):
    """
    Hàm xử lý Thêm/Sửa/Xóa kênh chuẩn logic
    action: "add" | "update" | "delete"
    [SỬA MỚI] Nếu action="add" mà kênh đã tồn tại -> Tự động Ghi đè (Update)
    """
    path = os.path.join(ACCOUNTS_DIR, filename)
    data = load_json(path)

    if "channels" not in data: data["channels"] = []

    if action == "add" and channel_data:
        # Kiểm tra trùng lặp URL
        found = False
        for i, chn in enumerate(data["channels"]):
            if chn.get("url") == channel_data.get("url"):
                # [QUAN TRỌNG] GHI ĐÈ LUÔN THAY VÌ BÁO LỖI
                data["channels"][i] = channel_data
                found = True
                break

        # Nếu chưa có thì thêm mới
        if not found:
            data["channels"].append(channel_data)

    elif action == "delete" and index is not None:
        if 0 <= index < len(data["channels"]):
            data["channels"].pop(index)

    elif action == "update" and index is not None and channel_data:
        if 0 <= index < len(data["channels"]):
            data["channels"][index] = channel_data

    save_json(path, data)
    return True, "Success"

def render_channel_manager():
    st.markdown("## 📺 Quản lý Kênh Nguồn (Matrix Mode)")
    st.caption("Chế độ thêm/sửa nhanh kênh nguồn cho từng tài khoản.")

    # 1. Load danh sách tài khoản
    acc_map = get_all_account_files()
    available_ids = sorted(list(acc_map.keys()))

    if not available_ids:
        st.warning("⚠️ Chưa có tài khoản nào. Vui lòng tạo tài khoản ở menu Quản lý Tài khoản trước.")
        return

    # 2. Chọn tài khoản để làm việc
    col_sel, _ = st.columns([1, 1])
    selected_id = col_sel.selectbox("👉 Chọn Tài khoản (ID):", available_ids)

    if not selected_id: return

    # Load dữ liệu của tài khoản đang chọn
    selected_filename = acc_map[selected_id]
    current_acc_data = load_json(os.path.join(ACCOUNTS_DIR, selected_filename))
    current_channels = current_acc_data.get("channels", [])

    st.divider()

    # ==========================================================================
    # FORM THÊM CẤU HÌNH MỚI
    # ==========================================================================
    with st.expander(f"➕ Thêm Kênh Nguồn Mới cho [{selected_id}]", expanded=False):
        with st.form("add_chn_form"):
            c_url, c_lim = st.columns([3, 1])
            new_url = c_url.text_input("🔗 Link Kênh Nguồn (TikTok/Douyin...):")
            new_limit = c_lim.number_input("Số video/lần:", 1, 50, 3)

            st.write("🎛️ **Thông số Edit Video**")
            t1, t2, t3, t4 = st.tabs(["Intro (Đầu)", "Content (Thân)", "Text (Chữ)", "Assets (Ảnh)"])

            with t1:
                c1, c2 = st.columns(2)
                t_st = c1.number_input("Intro Start:", 0.0, 60.0, 2.0)
                t_en = c1.number_input("Intro End:", 0.0, 60.0, 5.0)
                t_zm = c2.slider("Intro Zoom:", 1.0, 3.0, 1.0, 0.05)
                t_x = c2.number_input("Intro X Offset:", -500, 500, 0)
                t_y = c2.number_input("Intro Y Offset:", -500, 500, 250)

            with t2:
                c3, c4 = st.columns(2)
                c_st = c3.number_input("Content Start:", 0.0, 300.0, 7.0)
                c_en = c3.text_input("Content End (auto/giây):", "auto")
                c_zm = c4.slider("Content Zoom:", 1.0, 3.0, 1.05, 0.05)
                c_x = c4.number_input("Content X Offset:", -500, 500, 0)
                c_y = c4.number_input("Content Y Offset:", -500, 500, 0)

            with t3:
                # Cấu hình chung Font
                c5, c6 = st.columns(2)
                f_name = c5.text_input("Font File:", "Inter_18pt-Bold.ttf")
                f_size = c5.number_input("Font Size:", 10, 200, 45)
                col_in = c6.color_picker("Màu Intro:", "#FFFFFF")
                col_co = c6.color_picker("Màu Content:", "#FFFFFF")

                st.markdown("---")
                # Cấu hình Vị trí Text (Box Layout)
                st.caption("📍 Căn chỉnh vị trí khung chữ (0.0 - 1.0)")
                c_bx1, c_bx2 = st.columns(2)

                with c_bx1:
                    st.write("**Intro Text Layout**")
                    t_box_w = st.slider("Width % (Intro)", 0.1, 1.0, 0.65, 0.05)
                    t_box_ystart = st.slider("Y Start (Intro)", 0.0, 1.0, 0.73, 0.01)
                    t_box_yend = st.slider("Y End (Intro)", 0.0, 1.0, 0.83, 0.01)

                with c_bx2:
                    st.write("**Content Text Layout**")
                    c_box_w = st.slider("Width % (Content)", 0.1, 1.0, 0.65, 0.05)
                    c_box_ystart = st.slider("Y Start (Content)", 0.0, 1.0, 0.73, 0.01)
                    c_box_yend = st.slider("Y End (Content)", 0.0, 1.0, 0.83, 0.01)

            with t4:
                frame_files = [""] + ([f for f in os.listdir(FRAME_DIR) if f.lower().endswith(('.png', '.jpg'))] if os.path.exists(FRAME_DIR) else [])

                # [ĐÃ SỬA] Chia cột để hiển thị ảnh preview ngay bên dưới
                c7, c8 = st.columns(2)
                with c7:
                    fri_txt = st.selectbox("Khung Intro:", frame_files)
                    if fri_txt: safe_show_image(os.path.join(FRAME_DIR, fri_txt), caption="Preview Intro")

                with c8:
                    frc_txt = st.selectbox("Khung Content:", frame_files)
                    if frc_txt: safe_show_image(os.path.join(FRAME_DIR, frc_txt), caption="Preview Content")

                lg = st.text_input("Logo:", "")

            if st.form_submit_button("💾 THÊM KÊNH NGAY", type="primary"):
                if new_url:
                    new_chn_obj = {
                        "url": new_url.strip(),
                        "limit": new_limit,
                        "render_settings": {
                            "title_settings": {"source_start": t_st, "source_end": t_en, "zoom_factor": t_zm, "manual_x_offset": t_x, "manual_y_offset": t_y},
                            "content_settings": {"source_start": c_st, "source_end": float(c_en) if c_en.replace('.','',1).isdigit() else "auto", "zoom_factor": c_zm, "manual_x_offset": c_x, "manual_y_offset": c_y},
                            "text_overlay_settings": {
                                "font_filename": f_name, "font_size": f_size, "text_color": col_in,
                                "box_width_percentage": t_box_w, "box_y_start": t_box_ystart, "box_y_end": t_box_yend
                            },
                            "text_content_settings": {
                                "font_filename": f_name, "font_size": f_size, "text_color": col_co,
                                "box_width_percentage": c_box_w, "box_y_start": c_box_ystart, "box_y_end": c_box_yend
                            },
                            "assets": {"title_frame_filename": fri_txt, "content_frame_filename": frc_txt, "logo_filename": lg}
                        }
                    }

                    ok, msg = update_account_channels(selected_filename, action="add", channel_data=new_chn_obj)
                    if ok:
                        st.toast(f"✅ Đã thêm kênh vào {selected_id}"); time.sleep(1); st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.error("❌ Thiếu Link kênh nguồn.")

    # ==========================================================================
    # DANH SÁCH KÊNH HIỆN TẠI (EDIT MODE)
    # ==========================================================================
    st.subheader(f"📋 Danh sách Kênh hiện tại ({len(current_channels)})")

    if not current_channels:
        st.info("Tài khoản này chưa có kênh nguồn nào.")

    for i, chn in enumerate(current_channels):
        rs = chn.get("render_settings", {})
        ts = rs.get("title_settings", {})
        cs = rs.get("content_settings", {})
        tx = rs.get("text_overlay_settings", {})
        tx2 = rs.get("text_content_settings", {})
        ast = rs.get("assets", {})

        label = chn.get('url', f'Kênh #{i+1}')
        if not label: label = f"Kênh Trống #{i+1}"

        with st.expander(f"🛠️ {label}", expanded=False):
            with st.form(key=f"edit_chn_{selected_id}_{i}"):
                c_e_url, c_e_lim = st.columns([3, 1])
                e_url = c_e_url.text_input(f"Link Nguồn", chn.get("url", ""))
                e_lim = c_e_lim.number_input(f"Limit", 1, 50, chn.get("limit", 3))

                et1, et2, et3, et4 = st.tabs(["Intro", "Content", "Text", "Assets"])

                with et1:
                    ec1, ec2 = st.columns(2)
                    e_t_st = ec1.number_input(f"Intro Start ##{i}", 0.0, 60.0, float(ts.get("source_start", 2.0)))
                    e_t_en = ec1.number_input(f"Intro End ##{i}", 0.0, 60.0, float(ts.get("source_end", 5.0)))
                    e_t_zm = ec2.slider(f"Intro Zoom ##{i}", 1.0, 3.0, float(ts.get("zoom_factor", 1.0)), 0.05)
                    e_t_x = ec2.number_input(f"Intro X Offset ##{i}", -500, 500, int(ts.get("manual_x_offset", 0)))
                    e_t_y = ec2.number_input(f"Intro Y Offset ##{i}", -500, 500, int(ts.get("manual_y_offset", 250)))

                with et2:
                    ec3, ec4 = st.columns(2)
                    e_c_st = ec3.number_input(f"Content Start ##{i}", 0.0, 300.0, float(cs.get("source_start", 7.0)))
                    e_c_en = ec3.text_input(f"Content End ##{i}", str(cs.get("source_end", "auto")))
                    e_c_zm = ec4.slider(f"Content Zoom ##{i}", 1.0, 3.0, float(cs.get("zoom_factor", 1.05)), 0.05)
                    e_c_x = ec4.number_input(f"Content X Offset ##{i}", -500, 500, int(cs.get("manual_x_offset", 0)))
                    e_c_y = ec4.number_input(f"Content Y Offset ##{i}", -500, 500, int(cs.get("manual_y_offset", 0)))

                with et3:
                    # 1. Font & Màu sắc
                    e_font = st.text_input(f"Font ##{i}", str(tx.get("font_filename", "Inter_18pt-Bold.ttf")))
                    e_size = st.number_input(f"Size ##{i}", 10, 200, int(tx.get("font_size", 45)))
                    ec5, ec6 = st.columns(2)
                    e_col1 = ec5.color_picker(f"Màu Intro ##{i}", str(tx.get("text_color", "#FFFFFF")))
                    e_col2 = ec6.color_picker(f"Màu Content ##{i}", str(tx2.get("text_color", "#FFFFFF")))

                    st.markdown("---")
                    # 2. Box Layout cho Text (Vị trí)
                    st.caption("📍 Căn chỉnh vị trí chữ (Box Layout: 0.0 - 1.0)")

                    ec_bx1, ec_bx2 = st.columns(2)
                    with ec_bx1:
                        st.write("**Intro Text Position**")
                        e_t_box_w = st.slider(f"Width% (In) ##{i}", 0.1, 1.0, float(tx.get("box_width_percentage", 0.65)), 0.05)
                        e_t_box_yst = st.slider(f"Y Start (In) ##{i}", 0.0, 1.0, float(tx.get("box_y_start", 0.73)), 0.01)
                        e_t_box_yend = st.slider(f"Y End (In) ##{i}", 0.0, 1.0, float(tx.get("box_y_end", 0.83)), 0.01)

                    with ec_bx2:
                        st.write("**Content Text Position**")
                        e_c_box_w = st.slider(f"Width% (Co) ##{i}", 0.1, 1.0, float(tx2.get("box_width_percentage", 0.65)), 0.05)
                        e_c_box_yst = st.slider(f"Y Start (Co) ##{i}", 0.0, 1.0, float(tx2.get("box_y_start", 0.73)), 0.01)
                        e_c_box_yend = st.slider(f"Y End (Co) ##{i}", 0.0, 1.0, float(tx2.get("box_y_end", 0.83)), 0.01)

                with et4:
                    frame_files = [""] + ([f for f in os.listdir(FRAME_DIR) if f.lower().endswith(('.png', '.jpg'))] if os.path.exists(FRAME_DIR) else [])

                    cur_fri = str(ast.get("title_frame_filename", ""))
                    cur_frc = str(ast.get("content_frame_filename", ""))

                    idx_fri = frame_files.index(cur_fri) if cur_fri in frame_files else 0
                    idx_frc = frame_files.index(cur_frc) if cur_frc in frame_files else 0

                    ec7, ec8 = st.columns(2)
                    with ec7:
                        e_fri = st.selectbox(f"Intro Frame ##{i}", frame_files, index=idx_fri)
                        # [SỬA] Thêm width=150 để ảnh nhỏ lại
                        if e_fri:
                            safe_show_image(os.path.join(FRAME_DIR, e_fri), width=150, caption="Preview Intro")

                    with ec8:
                        e_frc = st.selectbox(f"Content Frame ##{i}", frame_files, index=idx_frc)
                        # [SỬA] Thêm width=150 để ảnh nhỏ lại
                        if e_frc:
                            safe_show_image(os.path.join(FRAME_DIR, e_frc), width=150, caption="Preview Content")

                    e_lg = st.text_input(f"Logo ##{i}", str(ast.get("logo_filename", "")))

                col_btn1, col_btn2 = st.columns([1, 1])
                is_update = col_btn1.form_submit_button("💾 CẬP NHẬT KÊNH")

            # Xử lý Logic Update
            if is_update:
                updated_chn = {
                    "url": e_url.strip(),
                    "limit": e_lim,
                    "render_settings": {
                        "title_settings": {"source_start": e_t_st, "source_end": e_t_en, "zoom_factor": e_t_zm, "manual_x_offset": e_t_x, "manual_y_offset": e_t_y},
                        "content_settings": {"source_start": e_c_st, "source_end": float(e_c_en) if e_c_en.replace('.','',1).isdigit() else "auto", "zoom_factor": e_c_zm, "manual_x_offset": e_c_x, "manual_y_offset": e_c_y},

                        # Cập nhật thông số Text
                        "text_overlay_settings": {
                            "font_filename": e_font, "font_size": e_size, "text_color": e_col1,
                            "box_width_percentage": e_t_box_w, "box_y_start": e_t_box_yst, "box_y_end": e_t_box_yend
                        },
                        "text_content_settings": {
                            "font_filename": e_font, "font_size": e_size, "text_color": e_col2,
                            "box_width_percentage": e_c_box_w, "box_y_start": e_c_box_yst, "box_y_end": e_c_box_yend
                        },

                        "assets": {"title_frame_filename": e_fri, "content_frame_filename": e_frc, "logo_filename": e_lg}
                    }
                }
                ok, msg = update_account_channels(selected_filename, action="update", channel_data=updated_chn, index=i)
                if ok: st.toast("✅ Cập nhật thành công!"); time.sleep(0.5); st.rerun()
                else: st.error(msg)

            if st.button("🗑️ XÓA KÊNH NÀY", key=f"del_{selected_id}_{i}"):
                update_account_channels(selected_filename, action="delete", index=i)
                st.rerun()