import streamlit as st
import time
import os
from ui.utils import (
    load_json, save_json, save_frame_image, safe_show_image,
    RENDER_CONFIG_FILE, FRAME_DIR, TRACKING_FILE, ACCOUNTS_FILE
)

def render_channel_manager():
    st.markdown("## 📺 Quản lý Kênh Nguồn & Config")
    st.caption("Cấu hình edit riêng biệt cho từng cặp: **[Kênh Nguồn]** ➡️ **[Nick TikTok Đích]**")

    # Load dữ liệu
    tracking_data = load_json(TRACKING_FILE)
    chn_list = tracking_data if isinstance(tracking_data, list) else tracking_data.get("channels", [])

    render_data = load_json(RENDER_CONFIG_FILE)
    render_list = render_data if isinstance(render_data, list) else []

    # Load danh sách tài khoản để gợi ý
    acc_data = load_json(ACCOUNTS_FILE)
    available_accs = [acc.get("tiktok_id", "") for acc in acc_data.get("accounts", []) if acc.get("tiktok_id")]
    if "" not in available_accs: available_accs.insert(0, "")

    # ==========================================================================
    # 1. FORM THÊM CẤU HÌNH MỚI
    # ==========================================================================
    with st.expander("➕ Thêm Cấu hình Edit Mới", expanded=False):
        with st.form("add_channel_config_v5"):
            st.info("Thiết lập thông số Edit khi lấy video từ Kênh Nguồn về đăng lên Nick Đích.")

            c_src, c_dst = st.columns([2, 1])
            new_url = c_src.text_input("🔗 Link Kênh Nguồn (TikTok/Douyin...):", placeholder="https://www.tiktok.com/@kenhnguon")

            # Cho phép chọn từ danh sách hoặc nhập tay
            c_dst_sel, c_dst_inp = c_dst.columns([1, 1])
            sel_tid = c_dst_sel.selectbox("Chọn Nick có sẵn:", available_accs, key="sel_new_tid")
            inp_tid = c_dst_inp.text_input("Hoặc nhập Nick Đích:", value=sel_tid if sel_tid else "", placeholder="@nickcuaban", key="inp_new_tid")

            final_new_tid = inp_tid.strip() # Ưu tiên giá trị nhập/chỉnh sửa cuối cùng

            c_limit_row, _ = st.columns([1, 2])
            new_limit = c_limit_row.number_input("Số lượng video quét mỗi lần:", 1, 50, 5)

            st.divider()
            st.write("🎛️ **Thông số Edit Video**")

            t1, t2, t3, t4 = st.tabs(["Intro (Đầu)", "Content (Giữa)", "Text Overlay", "Assets (Ảnh/Logo)"])

            with t1:
                col_a, col_b = st.columns(2)
                t_start = col_a.number_input("Cắt từ giây thứ (Intro):", 0.0, 60.0, 2.0)
                t_end = col_a.number_input("Đến giây thứ (Intro):", 0.0, 60.0, 7.0)
                t_zoom = col_b.number_input("Zoom Intro:", 1.0, 3.0, 1.0)
                t_off = col_b.text_input("Dịch chuyển Y (Intro):", "300")

            with t2:
                col_c, col_d = st.columns(2)
                c_start = col_c.number_input("Cắt từ giây thứ (Content):", 0.0, 300.0, 9.0)
                c_end = col_c.text_input("Đến giây thứ (Content):", "auto")
                c_zoom = col_d.number_input("Zoom Content:", 1.0, 3.0, 1.05)
                c_off = col_d.text_input("Dịch chuyển Y (Content):", "20")

            with t3:
                c_txt1, c_txt2 = st.columns(2)
                f_name = c_txt1.text_input("Font chữ (.ttf):", "Inter_18pt-Bold.ttf")
                f_size = c_txt1.number_input("Cỡ chữ:", 10, 200, 45)
                c_intro = c_txt2.color_picker("Màu chữ Intro:", "#FFFFFF")
                c_cont = c_txt2.color_picker("Màu chữ Content:", "#FFFFFF")

            with t4:
                c7, c8 = st.columns(2)
                with c7:
                    st.write("🖼️ Khung Intro")
                    up_fri = st.file_uploader("Upload ảnh Intro", key="new_up_fri")
                    val_fri = save_frame_image(up_fri) if up_fri else "nfdkj.png"
                    fr_i = st.text_input("Tên file Intro:", val_fri)
                with c8:
                    st.write("🖼️ Khung Content")
                    up_frc = st.file_uploader("Upload ảnh Content", key="new_up_frc")
                    val_frc = save_frame_image(up_frc) if up_frc else "vdfbd.png"
                    fr_c = st.text_input("Tên file Content:", val_frc)

                lg_f = st.text_input("Logo (.png) - Để trống nếu không dùng:", "")

            if st.form_submit_button("💾 LƯU CẤU HÌNH", type="primary"):
                if "http" in new_url and final_new_tid:
                    clean_url = new_url.strip()
                    clean_tid = final_new_tid.strip()

                    # 1. Update Tracking (Đảm bảo kênh nguồn được theo dõi)
                    # Tracking list chỉ quan tâm kênh nguồn, không quan tâm đích
                    if not any(c.get('channel_url') == clean_url for c in chn_list):
                        chn_list.append({
                            "channel_url": clean_url,
                            "last_video_url": "",
                            "scan_limit": new_limit,
                            "active": True
                        })
                        save_json(TRACKING_FILE, {"channels": chn_list})

                    # 2. Tạo Object Config Mới
                    new_cfg = {
                        "channel_url": clean_url,
                        "tiktok_id": clean_tid, # Quan trọng: Mapping 1-1
                        "title_settings": {
                            "source_start": t_start, "source_end": t_end,
                            "zoom_factor": t_zoom,
                            "manual_x_offset": 0,
                            "manual_y_offset": int(t_off) if t_off.lstrip('-').isdigit() else 0
                        },
                        "content_settings": {
                            "source_start": c_start,
                            "source_end": float(c_end) if c_end.replace('.','',1).isdigit() else "auto",
                            "zoom_factor": c_zoom,
                            "manual_x_offset": 0,
                            "manual_y_offset": int(c_off) if c_off.lstrip('-').isdigit() else 0
                        },
                        "text_overlay_settings": {
                            "font_filename": f_name, "font_size": f_size, "text_color": c_intro,
                            "box_width_percentage": 0.65, "box_y_start": 0.73, "box_y_end": 0.83
                        },
                        "text_content_settings": {
                            "font_filename": f_name, "font_size": f_size, "text_color": c_cont,
                            "box_width_percentage": 0.65, "box_y_start": 0.73, "box_y_end": 0.83
                        },
                        "assets": {
                            "title_frame_filename": fr_i, "content_frame_filename": fr_c,
                            "font_filename": f_name, "logo_filename": lg_f
                        }
                    }

                    # 3. Upsert (Cập nhật nếu cặp URL + ID đã tồn tại)
                    found = False
                    for idx, r in enumerate(render_list):
                        if r.get("channel_url") == clean_url and r.get("tiktok_id") == clean_tid:
                            render_list[idx] = new_cfg
                            found = True
                            break

                    if not found:
                        render_list.append(new_cfg)

                    save_json(RENDER_CONFIG_FILE, render_list)
                    st.success(f"✅ Đã lưu cấu hình: {clean_url} ➡️ {clean_tid}")
                    time.sleep(1); st.rerun()
                else:
                    st.error("⚠️ Vui lòng nhập đầy đủ Link Kênh Nguồn và Nick TikTok Đích.")

    # ==========================================================================
    # 2. DANH SÁCH CẤU HÌNH
    # ==========================================================================
    st.divider()
    st.subheader(f"📋 Danh sách Cấu hình ({len(render_list)})")

    if not render_list:
        st.info("Chưa có cấu hình nào.")

    # Duyệt qua từng config để hiển thị
    for i, cfg in enumerate(render_list):
        url = cfg.get('channel_url', 'Unknown')
        tid = cfg.get('tiktok_id', 'Chưa gán ID')

        # Tiêu đề hiển thị rõ cặp Nguồn -> Đích
        label = f"⚙️ {tid} ⬅️ {url}"

        ts = cfg.get("title_settings", {})
        cs = cfg.get("content_settings", {})
        tx = cfg.get("text_overlay_settings", {})
        tx2 = cfg.get("text_content_settings", {})
        ast = cfg.get("assets", {})

        with st.expander(label):
            # Cho phép sửa ID và Link ngay tại đây
            col_info1, col_info2 = st.columns(2)
            e_url = col_info1.text_input(f"Link Nguồn ##{i}", url)
            e_tid = col_info2.text_input(f"Nick Đích ##{i}", tid)

            et1, et2, et3, et4 = st.tabs(["Intro", "Content", "Text", "Assets"])

            with et1:
                ec1, ec2 = st.columns(2)
                e_t_st = ec1.number_input(f"Intro Start ##{i}", 0.0, 60.0, float(ts.get("source_start", 2.0)))
                e_t_en = ec1.number_input(f"Intro End ##{i}", 0.0, 60.0, float(ts.get("source_end", 7.0)))
                e_t_zm = ec2.number_input(f"Intro Zoom ##{i}", 1.0, 3.0, float(ts.get("zoom_factor", 1.0)))
                e_t_off = ec2.text_input(f"Intro Off Y ##{i}", str(ts.get("manual_y_offset", 300)))

            with et2:
                ec3, ec4 = st.columns(2)
                e_c_st = ec3.number_input(f"Cont Start ##{i}", 0.0, 300.0, float(cs.get("source_start", 9.0)))
                e_c_en = ec3.text_input(f"Cont End ##{i}", str(cs.get("source_end", "auto")))
                e_c_zm = ec4.number_input(f"Cont Zoom ##{i}", 1.0, 3.0, float(cs.get("zoom_factor", 1.05)))
                e_c_off = ec4.text_input(f"Cont Off Y ##{i}", str(cs.get("manual_y_offset", 20)))

            with et3:
                e_font = st.text_input(f"Font ##{i}", str(tx.get("font_filename", "Inter_18pt-Bold.ttf")))
                e_size = st.number_input(f"Size ##{i}", 10, 200, int(tx.get("font_size", 45)))
                c1, c2 = st.columns(2)
                e_col1 = c1.color_picker(f"Màu Intro ##{i}", str(tx.get("text_color", "#FFFFFF")))
                e_col2 = c2.color_picker(f"Màu Cont ##{i}", str(tx2.get("text_color", "#FFFFFF")))

            with et4:
                ac1, ac2 = st.columns(2)
                with ac1:
                    st.caption("🖼️ Intro Frame")
                    cur_fri = str(ast.get("title_frame_filename", ""))
                    safe_show_image(os.path.join(FRAME_DIR, cur_fri))

                    up_fri_edit = st.file_uploader("Đổi Intro:", key=f"up_fri_{i}")
                    if up_fri_edit:
                        cur_fri = save_frame_image(up_fri_edit)
                        st.success("Đã chọn ảnh mới!")
                    e_fri = st.text_input(f"File Intro ##{i}", cur_fri)

                with ac2:
                    st.caption("🖼️ Content Frame")
                    cur_frc = str(ast.get("content_frame_filename", ""))
                    safe_show_image(os.path.join(FRAME_DIR, cur_frc))

                    up_frc_edit = st.file_uploader("Đổi Content:", key=f"up_frc_{i}")
                    if up_frc_edit:
                        cur_frc = save_frame_image(up_frc_edit)
                        st.success("Đã chọn ảnh mới!")
                    e_frc = st.text_input(f"File Content ##{i}", cur_frc)

                e_lg = st.text_input(f"Logo File ##{i}", str(ast.get("logo_filename", "")))

            st.write("")
            col_save, col_del = st.columns([1, 1])

            if col_save.button("💾 CẬP NHẬT", key=f"btn_save_{i}"):
                # Cập nhật giá trị vào list
                render_list[i]["channel_url"] = e_url.strip()
                render_list[i]["tiktok_id"] = e_tid.strip()

                render_list[i]["title_settings"] = {
                    "source_start": e_t_st, "source_end": e_t_en, "zoom_factor": e_t_zm,
                    "manual_x_offset": 0,
                    "manual_y_offset": int(e_t_off) if e_t_off.lstrip('-').isdigit() else 0
                }
                render_list[i]["content_settings"] = {
                    "source_start": e_c_st,
                    "source_end": float(e_c_en) if e_c_en.replace('.','',1).isdigit() else "auto",
                    "zoom_factor": e_c_zm,
                    "manual_x_offset": 0,
                    "manual_y_offset": int(e_c_off) if e_c_off.lstrip('-').isdigit() else 0
                }
                render_list[i]["text_overlay_settings"] = {
                    "font_filename": e_font, "font_size": e_size, "text_color": e_col1,
                    "box_width_percentage": 0.65, "box_y_start": 0.73, "box_y_end": 0.83
                }
                render_list[i]["text_content_settings"] = {
                    "font_filename": e_font, "font_size": e_size, "text_color": e_col2,
                    "box_width_percentage": 0.65, "box_y_start": 0.73, "box_y_end": 0.83
                }
                render_list[i]["assets"] = {
                    "title_frame_filename": e_fri, "content_frame_filename": e_frc,
                    "font_filename": e_font, "logo_filename": e_lg
                }

                save_json(RENDER_CONFIG_FILE, render_list)

                # Cập nhật cả Tracking file nếu link nguồn thay đổi
                if e_url.strip() and e_url.strip() != url:
                    tracking_data = load_json(TRACKING_FILE)
                    chns = tracking_data.get("channels", [])
                    if not any(c['channel_url'] == e_url.strip() for c in chns):
                        chns.append({"channel_url": e_url.strip(), "last_video_url": "", "active": True})
                        save_json(TRACKING_FILE, {"channels": chns})

                st.toast("✅ Đã cập nhật thành công!"); time.sleep(1); st.rerun()

            if col_del.button("🗑️ XÓA CẤU HÌNH", key=f"btn_del_{i}", type="primary"):
                render_list.pop(i)
                save_json(RENDER_CONFIG_FILE, render_list)
                st.rerun()