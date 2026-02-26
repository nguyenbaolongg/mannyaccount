import customtkinter as ctk
from services.supabase_api import SupabaseAPI

class ChannelManagerPage:
    def __init__(self, parent_frame):
        self.parent = parent_frame
        self.editing_index = None # Biến lưu vị trí kênh đang được sửa

        self.title = ctk.CTkLabel(self.parent, text="📺 Quản lý Kênh Clone & Render", font=ctk.CTkFont(size=24, weight="bold"))
        self.title.pack(pady=(0, 10), anchor="w")

        # ================= CHỌN TÀI KHOẢN =================
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

        self.current_account = None

        # ================= FORM THÊM / SỬA KÊNH =================
        self.form_frame = ctk.CTkFrame(self.parent)
        self.form_frame.pack(fill="x", pady=10)

        # Hàng 1: URL & Limit
        row1 = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        row1.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(row1, text="🔗 Link Nguồn:").pack(side="left", padx=5)
        self.inp_url = ctk.CTkEntry(row1, width=300, placeholder_text="https://tiktok.com/@...")
        self.inp_url.pack(side="left", padx=5)

        ctk.CTkLabel(row1, text="Số video/lần:").pack(side="left", padx=5)
        self.inp_limit = ctk.CTkEntry(row1, width=50)
        self.inp_limit.pack(side="left", padx=5)
        self.inp_limit.insert(0, "3")

        # Tabs Cấu hình Render chi tiết
        self.tabs = ctk.CTkTabview(self.form_frame, height=120)
        self.tabs.pack(fill="x", padx=10, pady=5)
        self.tabs.add("Vid Intro")
        self.tabs.add("Vid Content")
        self.tabs.add("Chữ Intro")
        self.tabs.add("Chữ Content")
        self.tabs.add("Assets")

        # 1. Tab Video Intro
        self.inp_intro_st = self._add_field(self.tabs.tab("Vid Intro"), "Start (s):", "2.0")
        self.inp_intro_en = self._add_field(self.tabs.tab("Vid Intro"), "End (s):", "5.0")
        self.inp_intro_x = self._add_field(self.tabs.tab("Vid Intro"), "X Offset:", "0")
        self.inp_intro_y = self._add_field(self.tabs.tab("Vid Intro"), "Y Offset:", "250")

        # 2. Tab Video Content
        self.inp_cont_st = self._add_field(self.tabs.tab("Vid Content"), "Start (s):", "7.0")
        self.inp_cont_en = self._add_field(self.tabs.tab("Vid Content"), "End (s):", "auto")
        self.inp_cont_zm = self._add_field(self.tabs.tab("Vid Content"), "Zoom:", "1.05")
        self.inp_cont_x = self._add_field(self.tabs.tab("Vid Content"), "X Offset:", "0")
        self.inp_cont_y = self._add_field(self.tabs.tab("Vid Content"), "Y Offset:", "0")

        # 3. Tab Chữ Intro
        self.inp_txt_in_y1 = self._add_field(self.tabs.tab("Chữ Intro"), "Y Start (0-1):", "0.73")
        self.inp_txt_in_y2 = self._add_field(self.tabs.tab("Chữ Intro"), "Y End (0-1):", "0.83")
        self.inp_txt_in_w  = self._add_field(self.tabs.tab("Chữ Intro"), "Width % (0-1):", "0.65")
        self.inp_txt_in_sz = self._add_field(self.tabs.tab("Chữ Intro"), "Cỡ chữ (Size):", "45")
        self.inp_txt_in_strk = self._add_field(self.tabs.tab("Chữ Intro"), "Viền chữ (Stroke):", "0") # <-- ĐÃ THÊM

        # 4. Tab Chữ Content
        self.inp_txt_co_y1 = self._add_field(self.tabs.tab("Chữ Content"), "Y Start (0-1):", "0.73")
        self.inp_txt_co_y2 = self._add_field(self.tabs.tab("Chữ Content"), "Y End (0-1):", "0.83")
        self.inp_txt_co_w  = self._add_field(self.tabs.tab("Chữ Content"), "Width % (0-1):", "0.65")
        self.inp_txt_co_sz = self._add_field(self.tabs.tab("Chữ Content"), "Cỡ chữ (Size):", "45")
        self.inp_txt_co_strk = self._add_field(self.tabs.tab("Chữ Content"), "Viền chữ (Stroke):", "0") # <-- ĐÃ THÊM

        # 5. Tab Assets
        self.inp_frame_in = self._add_field(self.tabs.tab("Assets"), "Khung Intro:", "")
        self.inp_frame_co = self._add_field(self.tabs.tab("Assets"), "Khung Content:", "")
        self.inp_font = self._add_field(self.tabs.tab("Assets"), "Tên Font:", "Inter_18pt-Bold.ttf")
        self.inp_logo = self._add_field(self.tabs.tab("Assets"), "Tên Logo:", "")

        # Khung chứa Nút Lưu và Hủy
        self.action_frame = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        self.action_frame.pack(pady=10)

        self.btn_save_chn = ctk.CTkButton(self.action_frame, text="➕ THÊM KÊNH MỚI", command=self.save_channel, fg_color="green", hover_color="darkgreen")
        self.btn_save_chn.pack(side="left", padx=5)

        self.btn_cancel_edit = ctk.CTkButton(self.action_frame, text="❌ HỦY SỬA", command=self.cancel_edit, fg_color="gray", hover_color="darkgray")

        self.lbl_status = ctk.CTkLabel(self.form_frame, text="")
        self.lbl_status.pack()

        # ================= DANH SÁCH KÊNH =================
        ctk.CTkLabel(self.parent, text="📋 Danh sách Kênh đang theo dõi:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(10, 0))
        self.scroll_frame = ctk.CTkScrollableFrame(self.parent, width=800, height=200)
        self.scroll_frame.pack(fill="both", expand=True, pady=5)

        # Load mặc định account đầu tiên
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
        inp_widget.delete(0, 'end')
        inp_widget.insert(0, str(val))

    def on_account_select(self, selected_id):
        self.current_account = next((acc for acc in self.accounts if acc["tiktok_id"] == selected_id), None)
        self.lbl_status.configure(text="")
        self.cancel_edit() # Đổi tài khoản thì reset form
        self.load_channels()

    def load_channels(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        if not self.current_account: return
        channels = self.current_account.get("channels", [])

        if not channels:
            ctk.CTkLabel(self.scroll_frame, text="Chưa có kênh nào.").pack(pady=10)
            return

        for i, chn in enumerate(channels):
            row_frame = ctk.CTkFrame(self.scroll_frame)
            row_frame.pack(fill="x", pady=2)

            ctk.CTkLabel(row_frame, text=chn.get("url", "N/A"), width=400, anchor="w").pack(side="left", padx=10)
            ctk.CTkLabel(row_frame, text=f"Limit: {chn.get('limit', 3)}", width=100).pack(side="left", padx=10)

            btn_del = ctk.CTkButton(row_frame, text="🗑️ Xóa", width=60, fg_color="red", hover_color="darkred", command=lambda idx=i: self.delete_channel(idx))
            btn_del.pack(side="right", padx=10, pady=5)

            btn_edit = ctk.CTkButton(row_frame, text="✏️ Sửa", width=60, fg_color="blue", hover_color="darkblue", command=lambda idx=i, data=chn: self.edit_channel(idx, data))
            btn_edit.pack(side="right", padx=5, pady=5)

    def edit_channel(self, index, chn_data):
        """Đẩy dữ liệu của kênh được chọn lên form để sửa"""
        self.editing_index = index
        self.lbl_status.configure(text="✏️ Chế độ Sửa: Vui lòng thay đổi thông tin và bấm CẬP NHẬT.", text_color="blue")

        self.btn_cancel_edit.pack(side="left", padx=5)
        self.btn_save_chn.configure(text="💾 CẬP NHẬT KÊNH", fg_color="blue", hover_color="darkblue")

        rs = chn_data.get("render_settings", {})
        ts = rs.get("title_settings", {})
        cs = rs.get("content_settings", {})
        txt_in = rs.get("text_overlay_settings", {})
        txt_co = rs.get("text_content_settings", {})
        ast = rs.get("assets", {})

        # Clear form và đẩy data lên
        self._set_val(self.inp_url, chn_data.get("url", ""))
        self._set_val(self.inp_limit, chn_data.get("limit", 3))

        # Vid Intro
        self._set_val(self.inp_intro_st, ts.get("source_start", 2.0))
        self._set_val(self.inp_intro_en, ts.get("source_end", 5.0))
        self._set_val(self.inp_intro_x, ts.get("manual_x_offset", 0))
        self._set_val(self.inp_intro_y, ts.get("manual_y_offset", 250))

        # Vid Content
        self._set_val(self.inp_cont_st, cs.get("source_start", 7.0))
        self._set_val(self.inp_cont_en, cs.get("source_end", "auto"))
        self._set_val(self.inp_cont_zm, cs.get("zoom_factor", 1.05))
        self._set_val(self.inp_cont_x, cs.get("manual_x_offset", 0))
        self._set_val(self.inp_cont_y, cs.get("manual_y_offset", 0))

        # Chữ Intro (ĐÃ BỔ SUNG STROKE)
        self._set_val(self.inp_txt_in_y1, txt_in.get("box_y_start", 0.73))
        self._set_val(self.inp_txt_in_y2, txt_in.get("box_y_end", 0.83))
        self._set_val(self.inp_txt_in_w, txt_in.get("box_width_percentage", 0.65))
        self._set_val(self.inp_txt_in_sz, txt_in.get("font_size", 45))
        self._set_val(self.inp_txt_in_strk, txt_in.get("stroke_width", 0))

        # Chữ Content (ĐÃ BỔ SUNG STROKE)
        self._set_val(self.inp_txt_co_y1, txt_co.get("box_y_start", 0.73))
        self._set_val(self.inp_txt_co_y2, txt_co.get("box_y_end", 0.83))
        self._set_val(self.inp_txt_co_w, txt_co.get("box_width_percentage", 0.65))
        self._set_val(self.inp_txt_co_sz, txt_co.get("font_size", 45))
        self._set_val(self.inp_txt_co_strk, txt_co.get("stroke_width", 0))

        # Assets
        self._set_val(self.inp_frame_in, ast.get("title_frame_filename", ""))
        self._set_val(self.inp_frame_co, ast.get("content_frame_filename", ""))
        self._set_val(self.inp_font, txt_in.get("font_filename", "Inter_18pt-Bold.ttf"))
        self._set_val(self.inp_logo, ast.get("logo_filename", ""))

    def cancel_edit(self):
        """Thoát chế độ sửa, làm trắng form"""
        self.editing_index = None
        self.btn_cancel_edit.pack_forget()
        self.btn_save_chn.configure(text="➕ THÊM KÊNH MỚI", fg_color="green", hover_color="darkgreen")
        self.lbl_status.configure(text="")

        # Khôi phục giá trị mặc định
        self._set_val(self.inp_url, "")
        self._set_val(self.inp_limit, "3")
        self._set_val(self.inp_intro_st, "2.0"); self._set_val(self.inp_intro_en, "5.0")
        self._set_val(self.inp_intro_x, "0"); self._set_val(self.inp_intro_y, "250")
        self._set_val(self.inp_cont_st, "7.0"); self._set_val(self.inp_cont_en, "auto")
        self._set_val(self.inp_cont_zm, "1.05"); self._set_val(self.inp_cont_x, "0"); self._set_val(self.inp_cont_y, "0")

        self._set_val(self.inp_txt_in_y1, "0.73"); self._set_val(self.inp_txt_in_y2, "0.83"); self._set_val(self.inp_txt_in_w, "0.65"); self._set_val(self.inp_txt_in_sz, "45"); self._set_val(self.inp_txt_in_strk, "0")
        self._set_val(self.inp_txt_co_y1, "0.73"); self._set_val(self.inp_txt_co_y2, "0.83"); self._set_val(self.inp_txt_co_w, "0.65"); self._set_val(self.inp_txt_co_sz, "45"); self._set_val(self.inp_txt_co_strk, "0")

        self._set_val(self.inp_frame_in, ""); self._set_val(self.inp_frame_co, "")
        self._set_val(self.inp_font, "Inter_18pt-Bold.ttf"); self._set_val(self.inp_logo, "")

    def save_channel(self):
        url = self.inp_url.get().strip()
        if not url or not self.current_account:
            self.lbl_status.configure(text="❌ Vui lòng nhập Link Kênh!", text_color="red")
            return

        # Hàm trợ giúp ép kiểu an toàn
        def safe_float(val, default=0.0):
            try: return float(val)
            except: return default
        def safe_int(val, default=0):
            try: return int(val)
            except: return default

        c_en_val = self.inp_cont_en.get().strip()
        final_c_en = safe_float(c_en_val) if c_en_val.replace('.','',1).isdigit() else "auto"

        new_chn = {
            "url": url,
            "limit": safe_int(self.inp_limit.get(), 3),
            "render_settings": {
                "title_settings": {
                    "source_start": safe_float(self.inp_intro_st.get(), 2.0),
                    "source_end": safe_float(self.inp_intro_en.get(), 5.0),
                    "manual_x_offset": safe_int(self.inp_intro_x.get(), 0),
                    "manual_y_offset": safe_int(self.inp_intro_y.get(), 250)
                },
                "content_settings": {
                    "source_start": safe_float(self.inp_cont_st.get(), 7.0),
                    "source_end": final_c_en,
                    "zoom_factor": safe_float(self.inp_cont_zm.get(), 1.05),
                    "manual_x_offset": safe_int(self.inp_cont_x.get(), 0),
                    "manual_y_offset": safe_int(self.inp_cont_y.get(), 0)
                },
                "text_overlay_settings": {
                    "font_filename": self.inp_font.get().strip(),
                    "font_size": safe_int(self.inp_txt_in_sz.get(), 45),
                    "text_color": "#FFFFFF",
                    "box_width_percentage": safe_float(self.inp_txt_in_w.get(), 0.65),
                    "box_y_start": safe_float(self.inp_txt_in_y1.get(), 0.73),
                    "box_y_end": safe_float(self.inp_txt_in_y2.get(), 0.83),
                    "stroke_width": safe_int(self.inp_txt_in_strk.get(), 0) # <-- ĐÃ THÊM LƯU STROKE
                },
                "text_content_settings": {
                    "font_filename": self.inp_font.get().strip(),
                    "font_size": safe_int(self.inp_txt_co_sz.get(), 45),
                    "text_color": "#FFFFFF",
                    "box_width_percentage": safe_float(self.inp_txt_co_w.get(), 0.65),
                    "box_y_start": safe_float(self.inp_txt_co_y1.get(), 0.73),
                    "box_y_end": safe_float(self.inp_txt_co_y2.get(), 0.83),
                    "stroke_width": safe_int(self.inp_txt_co_strk.get(), 0) # <-- ĐÃ THÊM LƯU STROKE
                },
                "assets": {
                    "title_frame_filename": self.inp_frame_in.get().strip(),
                    "content_frame_filename": self.inp_frame_co.get().strip(),
                    "logo_filename": self.inp_logo.get().strip()
                }
            }
        }

        channels = self.current_account.get("channels", [])

        if self.editing_index is not None:
            # Chế độ Sửa
            channels[self.editing_index] = new_chn
        else:
            # Chế độ Thêm mới
            found = False
            for i, chn in enumerate(channels):
                if chn.get("url") == url:
                    channels[i] = new_chn
                    found = True
                    break
            if not found: channels.append(new_chn)

        self.current_account["channels"] = channels

        if SupabaseAPI.save_account(self.current_account):
            self.lbl_status.configure(text="✅ Đã lưu kênh thành công!", text_color="green")
            self.cancel_edit() # Lưu xong thì thoát chế độ sửa
            self.load_channels()
        else:
            self.lbl_status.configure(text="❌ Lỗi khi lưu lên Database.", text_color="red")

    def delete_channel(self, index):
        if self.current_account:
            self.current_account["channels"].pop(index)
            if SupabaseAPI.save_account(self.current_account):
                self.load_channels()
                self.cancel_edit()