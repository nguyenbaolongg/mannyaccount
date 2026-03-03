import customtkinter as ctk
from services.supabase_api import SupabaseAPI

class ChannelManagerPage:
    def __init__(self, parent_frame):
        self.parent = parent_frame
        self.editing_index = None

        self.title = ctk.CTkLabel(self.parent, text="📺 Quản lý Kênh Clone & Render", font=ctk.CTkFont(size=24, weight="bold"))
        self.title.pack(pady=(0, 10), anchor="w")

        self.accounts = SupabaseAPI.get_all_accounts() or []
        self.acc_ids = [acc.get("tiktok_id") for acc in self.accounts if acc.get("tiktok_id")]

        if not self.acc_ids:
            ctk.CTkLabel(self.parent, text="⚠️ Chưa có tài khoản nào. Vui lòng thêm tài khoản trước.").pack()
            return

        self.sel_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        self.sel_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(self.sel_frame, text="👉 Chọn Tài khoản:").pack(side="left", padx=5)
        self.acc_dropdown = ctk.CTkOptionMenu(self.sel_frame, values=self.acc_ids, command=self.on_account_select)
        self.acc_dropdown.pack(side="left", padx=10)

        # Hiển thị giới hạn tổng của tài khoản (video_limit_per_run)
        self.lbl_acc_limit = ctk.CTkLabel(self.sel_frame, text="Giới hạn tối đa/lần chạy: --", text_color="orange")
        self.lbl_acc_limit.pack(side="left", padx=20)

        self.current_account = None

        self.form_frame = ctk.CTkFrame(self.parent)
        self.form_frame.pack(fill="x", pady=10)

        row1 = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        row1.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(row1, text="🔗 Link Nguồn:").pack(side="left", padx=5)
        self.inp_url = ctk.CTkEntry(row1, width=300, placeholder_text="https://tiktok.com/@...")
        self.inp_url.pack(side="left", padx=5)

        ctk.CTkLabel(row1, text="Số video lấy từ kênh này:").pack(side="left", padx=5)
        self.inp_limit = ctk.CTkEntry(row1, width=50)
        self.inp_limit.pack(side="left", padx=5)
        self.inp_limit.insert(0, "3")

        # Tabs cấu hình Render chi tiết
        self.tabs = ctk.CTkTabview(self.form_frame, height=150)
        self.tabs.pack(fill="x", padx=10, pady=5)
        self.tabs.add("Vid Intro")
        self.tabs.add("Vid Content")
        self.tabs.add("Chữ Intro")
        self.tabs.add("Chữ Content")
        self.tabs.add("Assets")

        self.inp_intro_st = self._add_field(self.tabs.tab("Vid Intro"), "Start (s):", "2.0")
        self.inp_intro_en = self._add_field(self.tabs.tab("Vid Intro"), "End (s):", "5.0")
        self.inp_intro_zm = self._add_field(self.tabs.tab("Vid Intro"), "Zoom:", "1.0")
        self.inp_intro_x  = self._add_field(self.tabs.tab("Vid Intro"), "X Offset:", "0")
        self.inp_intro_y  = self._add_field(self.tabs.tab("Vid Intro"), "Y Offset:", "100")

        self.inp_cont_st = self._add_field(self.tabs.tab("Vid Content"), "Start (s):", "10.0")
        self.inp_cont_en = self._add_field(self.tabs.tab("Vid Content"), "End (s):", "auto")
        self.inp_cont_zm = self._add_field(self.tabs.tab("Vid Content"), "Zoom:", "1.05")
        self.inp_cont_x  = self._add_field(self.tabs.tab("Vid Content"), "X Offset:", "0")
        self.inp_cont_y  = self._add_field(self.tabs.tab("Vid Content"), "Y Offset:", "-11")

        self.inp_txt_in_y1   = self._add_field(self.tabs.tab("Chữ Intro"), "Y Start:", "0.73")
        self.inp_txt_in_y2   = self._add_field(self.tabs.tab("Chữ Intro"), "Y End:", "0.83")
        self.inp_txt_in_w    = self._add_field(self.tabs.tab("Chữ Intro"), "Width %:", "0.65")
        self.inp_txt_in_sz   = self._add_field(self.tabs.tab("Chữ Intro"), "Size:", "45")
        self.inp_txt_in_clr  = self._add_field(self.tabs.tab("Chữ Intro"), "Màu (Hex):", "#ffffff")
        self.inp_txt_in_strk = self._add_field(self.tabs.tab("Chữ Intro"), "Stroke:", "0")

        self.inp_txt_co_y1   = self._add_field(self.tabs.tab("Chữ Content"), "Y Start:", "0.73")
        self.inp_txt_co_y2   = self._add_field(self.tabs.tab("Chữ Content"), "Y End:", "0.83")
        self.inp_txt_co_w    = self._add_field(self.tabs.tab("Chữ Content"), "Width %:", "0.65")
        self.inp_txt_co_sz   = self._add_field(self.tabs.tab("Chữ Content"), "Size:", "45")
        self.inp_txt_co_clr  = self._add_field(self.tabs.tab("Chữ Content"), "Màu (Hex):", "#ffffff")
        self.inp_txt_co_strk = self._add_field(self.tabs.tab("Chữ Content"), "Stroke:", "0")

        self.inp_frame_in = self._add_field(self.tabs.tab("Assets"), "Khung Intro:", "")
        self.inp_frame_co = self._add_field(self.tabs.tab("Assets"), "Khung Content:", "")
        self.inp_font     = self._add_field(self.tabs.tab("Assets"), "Tên Font:", "Inter_18pt-Bold.ttf")
        self.inp_logo     = self._add_field(self.tabs.tab("Assets"), "Tên Logo:", "")

        self.action_frame = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        self.action_frame.pack(pady=10)
        self.btn_save_chn = ctk.CTkButton(self.action_frame, text="➕ THÊM KÊNH MỚI", command=self.save_channel, fg_color="green")
        self.btn_save_chn.pack(side="left", padx=5)
        self.btn_cancel_edit = ctk.CTkButton(self.action_frame, text="❌ HỦY SỬA", command=self.cancel_edit, fg_color="gray")

        self.lbl_status = ctk.CTkLabel(self.form_frame, text="")
        self.lbl_status.pack()

        header_list = ctk.CTkFrame(self.parent, fg_color="transparent")
        header_list.pack(fill="x", pady=(10, 0))

        ctk.CTkLabel(header_list, text="📋 Danh sách Kênh đang theo dõi:", font=ctk.CTkFont(weight="bold")).pack(side="left")

        # Hiển thị Tổng video dự kiến (tổng limit của các kênh con)
        self.lbl_total_expected = ctk.CTkLabel(header_list, text="📊 Tổng video dự kiến: 0", font=ctk.CTkFont(weight="bold"), text_color="cyan")
        self.lbl_total_expected.pack(side="right", padx=10)

        self.scroll_frame = ctk.CTkScrollableFrame(self.parent, width=800, height=200)
        self.scroll_frame.pack(fill="both", expand=True, pady=5)

        self.on_account_select(self.acc_ids[0])

    def _add_field(self, parent, label_text, default_val):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(side="left", padx=8, pady=5)
        ctk.CTkLabel(frame, text=label_text).pack(anchor="w")
        inp = ctk.CTkEntry(frame, width=95)
        inp.pack()
        inp.insert(0, default_val)
        return inp

    def _set_val(self, inp_widget, val):
        inp_widget.configure(state="normal") # Đảm bảo mở khóa trước khi ghi
        inp_widget.delete(0, 'end')
        inp_widget.insert(0, str(val))

    def on_account_select(self, selected_id):
        self.current_account = next((acc for acc in self.accounts if acc["tiktok_id"] == selected_id), None)
        if self.current_account:
            limit_run = self.current_account.get("video_limit_per_run", "N/A")
            self.lbl_acc_limit.configure(text=f"Giới hạn tối đa/lần chạy: {limit_run}")

        self.lbl_status.configure(text="")
        self.cancel_edit()
        self.load_channels()

    def load_channels(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        if not self.current_account: return
        channels = self.current_account.get("channels", [])

        total_limit = 0

        if not channels:
            ctk.CTkLabel(self.scroll_frame, text="Chưa có kênh nào.").pack(pady=10)
            self.lbl_total_expected.configure(text="📊 Tổng video dự kiến: 0", text_color="cyan")
            return

        for i, chn in enumerate(channels):
            c_limit = chn.get('limit', 0)
            total_limit += c_limit

            row_frame = ctk.CTkFrame(self.scroll_frame)
            row_frame.pack(fill="x", pady=2)
            ctk.CTkLabel(row_frame, text=chn.get("url", "N/A"), width=400, anchor="w").pack(side="left", padx=10)
            ctk.CTkLabel(row_frame, text=f"Limit: {c_limit}", width=100).pack(side="left", padx=10)

            btn_del = ctk.CTkButton(row_frame, text="🗑️", width=30, fg_color="red", command=lambda idx=i: self.delete_channel(idx))
            btn_del.pack(side="right", padx=10)
            btn_edit = ctk.CTkButton(row_frame, text="✏️", width=30, command=lambda idx=i, data=chn: self.edit_channel(idx, data))
            btn_edit.pack(side="right", padx=5)

        self.lbl_total_expected.configure(text=f"📊 Tổng video dự kiến: {total_limit}")

        acc_max = self.current_account.get("video_limit_per_run", 999)
        if total_limit > acc_max:
            self.lbl_total_expected.configure(text_color="red")
        else:
            self.lbl_total_expected.configure(text_color="cyan")

    def edit_channel(self, index, chn_data):
        self.editing_index = index
        self.lbl_status.configure(text="✏️ Chế độ Sửa (Đã khóa chỉnh sửa Link)", text_color="orange")
        self.btn_cancel_edit.pack(side="left", padx=5)
        self.btn_save_chn.configure(text="💾 CẬP NHẬT KÊNH", fg_color="blue")

        rs = chn_data.get("render_settings", {})
        ts, cs = rs.get("title_settings", {}), rs.get("content_settings", {})
        txt_in, txt_co = rs.get("text_overlay_settings", {}), rs.get("text_content_settings", {})
        ast = rs.get("assets", {})

        self._set_val(self.inp_url, chn_data.get("url", ""))
        self.inp_url.configure(state="disabled")
        self._set_val(self.inp_limit, chn_data.get("limit", 3))

        self._set_val(self.inp_intro_st, ts.get("source_start", 2.0))
        self._set_val(self.inp_intro_en, ts.get("source_end", 5.0))
        self._set_val(self.inp_intro_zm, ts.get("zoom_factor", 1.0))
        self._set_val(self.inp_intro_x, ts.get("manual_x_offset", 0))
        self._set_val(self.inp_intro_y, ts.get("manual_y_offset", 100))

        self._set_val(self.inp_cont_st, cs.get("source_start", 10.0))
        self._set_val(self.inp_cont_en, cs.get("source_end", "auto"))
        self._set_val(self.inp_cont_zm, cs.get("zoom_factor", 1.05))
        self._set_val(self.inp_cont_x, cs.get("manual_x_offset", 0))
        self._set_val(self.inp_cont_y, cs.get("manual_y_offset", -11))

        self._set_val(self.inp_txt_in_y1, txt_in.get("box_y_start", 0.73))
        self._set_val(self.inp_txt_in_y2, txt_in.get("box_y_end", 0.83))
        self._set_val(self.inp_txt_in_w, txt_in.get("box_width_percentage", 0.65))
        self._set_val(self.inp_txt_in_sz, txt_in.get("font_size", 45))
        self._set_val(self.inp_txt_in_clr, txt_in.get("text_color", "#ffffff"))
        self._set_val(self.inp_txt_in_strk, txt_in.get("stroke_width", 0))

        self._set_val(self.inp_txt_co_y1, txt_co.get("box_y_start", 0.73))
        self._set_val(self.inp_txt_co_y2, txt_co.get("box_y_end", 0.83))
        self._set_val(self.inp_txt_co_w, txt_co.get("box_width_percentage", 0.65))
        self._set_val(self.inp_txt_co_sz, txt_co.get("font_size", 45))
        self._set_val(self.inp_txt_co_clr, txt_co.get("text_color", "#ffffff"))
        self._set_val(self.inp_txt_co_strk, txt_co.get("stroke_width", 0))

        self._set_val(self.inp_frame_in, ast.get("title_frame_filename", ""))
        self._set_val(self.inp_frame_co, ast.get("content_frame_filename", ""))
        self._set_val(self.inp_font, txt_in.get("font_filename", "Inter_18pt-Bold.ttf"))
        self._set_val(self.inp_logo, ast.get("logo_filename", ""))

    def save_channel(self):
        self.inp_url.configure(state="normal")
        url = self.inp_url.get().strip()

        if not url or not self.current_account: return

        new_chn = {
            "url": url,
            "limit": int(self.inp_limit.get() or 3),
            "render_settings": {
                "title_settings": {
                    "source_start": float(self.inp_intro_st.get()),
                    "source_end": float(self.inp_intro_en.get()),
                    "zoom_factor": float(self.inp_intro_zm.get()),
                    "manual_x_offset": int(self.inp_intro_x.get()),
                    "manual_y_offset": int(self.inp_intro_y.get())
                },
                "text_overlay_settings": {
                    "text_color": self.inp_txt_in_clr.get().strip(),
                    "stroke_width": int(self.inp_txt_in_strk.get() or 0),
                    "font_size": int(self.inp_txt_in_sz.get() or 45),
                    "box_y_start": float(self.inp_txt_in_y1.get()),
                    "box_y_end": float(self.inp_txt_in_y2.get()),
                    "box_width_percentage": float(self.inp_txt_in_w.get()),
                    "font_filename": self.inp_font.get().strip()
                },
                "text_content_settings": {
                    "text_color": self.inp_txt_co_clr.get().strip(),
                    "stroke_width": int(self.inp_txt_co_strk.get() or 0),
                    "font_size": int(self.inp_txt_co_sz.get() or 45),
                    "box_y_start": float(self.inp_txt_co_y1.get()),
                    "box_y_end": float(self.inp_txt_co_y2.get()),
                    "box_width_percentage": float(self.inp_txt_co_w.get()),
                    "font_filename": self.inp_font.get().strip()
                },
                "assets": {
                    "title_frame_filename": self.inp_frame_in.get().strip(),
                    "content_frame_filename": self.inp_frame_co.get().strip(),
                    "logo_filename": self.inp_logo.get().strip()
                },
                "content_settings": {
                    "source_start": float(self.inp_cont_st.get()),
                    "source_end": self.inp_cont_en.get(),
                    "zoom_factor": float(self.inp_cont_zm.get()),
                    "manual_x_offset": int(self.inp_cont_x.get()),
                    "manual_y_offset": int(self.inp_cont_y.get())
                }
            }
        }

        channels = self.current_account.get("channels", [])
        is_new_channel = False

        if self.editing_index is not None:
            channels[self.editing_index] = new_chn
        else:
            found = False
            for i, chn in enumerate(channels):
                if chn.get("url") == url:
                    channels[i] = new_chn
                    found = True
                    break
            if not found:
                channels.append(new_chn)
                is_new_channel = True

        self.current_account["channels"] = channels
        tiktok_id = self.current_account.get("tiktok_id")

        if is_new_channel:
            SupabaseAPI.update_channel_videos_db(tiktok_id, url, [])

        if SupabaseAPI.save_account(self.current_account):
            self.lbl_status.configure(text="✅ Lưu thành công!", text_color="green")
            self.cancel_edit()
            self.load_channels()

    def cancel_edit(self):
        self.editing_index = None
        self.btn_cancel_edit.pack_forget()
        self.btn_save_chn.configure(text="➕ THÊM KÊNH MỚI", fg_color="green")
        self.inp_url.configure(state="normal") # Mở khóa lại
        self._set_val(self.inp_url, "")
        self.lbl_status.configure(text="")

    def delete_channel(self, index):
        if self.current_account:
            channel_to_delete = self.current_account["channels"][index]
            tiktok_id = self.current_account.get("tiktok_id")
            channel_url = channel_to_delete.get("url")
            self.current_account["channels"].pop(index)
            if tiktok_id and channel_url:
                SupabaseAPI.delete_channel_videos_db(tiktok_id, channel_url)
            if SupabaseAPI.save_account(self.current_account):
                self.load_channels()