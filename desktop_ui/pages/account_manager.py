import customtkinter as ctk
import os
import shutil
import threading
import time
import undetected_chromedriver as uc
from services.supabase_api import SupabaseAPI

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AI_STUDIO_DIR = os.path.join(PROJECT_ROOT, "assets", "ai_studio_data")

class AccountManagerPage:
    def __init__(self, parent_frame):
        self.parent = parent_frame
        self.editing_tiktok_id = None

        self.title = ctk.CTkLabel(self.parent, text="👤 Quản lý Tài khoản & Profile", font=ctk.CTkFont(size=24, weight="bold"))
        self.title.pack(pady=(0, 10), anchor="w")

        # ================= FORM THÊM / SỬA TÀI KHOẢN =================
        self.form_frame = ctk.CTkFrame(self.parent)
        self.form_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(self.form_frame, text="➕ Thêm / Sửa Tài khoản", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=10, pady=10, sticky="w")

        # --- ROW 1 ---
        ctk.CTkLabel(self.form_frame, text="TikTok Handle (@abc):").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.inp_tiktok_id = ctk.CTkEntry(self.form_frame, width=200, placeholder_text="@...")
        self.inp_tiktok_id.grid(row=1, column=1, padx=10, pady=5)

        ctk.CTkLabel(self.form_frame, text="Email Google:").grid(row=1, column=2, padx=10, pady=5, sticky="w")
        self.inp_email = ctk.CTkEntry(self.form_frame, width=250, placeholder_text="email@gmail.com")
        self.inp_email.grid(row=1, column=3, padx=10, pady=5)

        # --- ROW 2 ---
        ctk.CTkLabel(self.form_frame, text="Mật khẩu Email:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.inp_password = ctk.CTkEntry(self.form_frame, width=200, show="*")
        self.inp_password.grid(row=2, column=1, padx=10, pady=5)

        ctk.CTkLabel(self.form_frame, text="Giao cho Máy số:").grid(row=2, column=2, padx=10, pady=5, sticky="w")
        self.inp_machine_id = ctk.CTkEntry(self.form_frame, width=100, placeholder_text="Ví dụ: 1")
        self.inp_machine_id.grid(row=2, column=3, padx=10, pady=5, sticky="w")
        self.inp_machine_id.insert(0, "1")

        # --- ROW 3: KHU VỰC NÚT BẤM ---
        self.action_frame = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        self.action_frame.grid(row=3, column=0, columnspan=4, padx=10, pady=15, sticky="w")

        self.btn_save = ctk.CTkButton(self.action_frame, text="🚀 TẠO TÀI KHOẢN", command=self.save_account, fg_color="green", hover_color="darkgreen")
        self.btn_save.pack(side="left", padx=5)

        self.btn_cancel = ctk.CTkButton(self.action_frame, text="❌ HỦY", command=self.cancel_edit, fg_color="gray", hover_color="darkgray")

        # --- ROW 4: TRẠNG THÁI ---
        self.lbl_status = ctk.CTkLabel(self.form_frame, text="")
        self.lbl_status.grid(row=4, column=0, columnspan=4, padx=15, pady=(0, 10), sticky="w")

        # ================= DANH SÁCH TÀI KHOẢN =================
        ctk.CTkLabel(self.parent, text="📋 Danh sách Tài khoản & Quản lý Profile:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(10, 0))
        self.scroll_frame = ctk.CTkScrollableFrame(self.parent, width=1000, height=300)
        self.scroll_frame.pack(fill="both", expand=True, pady=5)

        self.load_accounts()

    # ================= LOGIC FORM & DANH SÁCH =================
    def save_account(self):
        tiktok_id = self.inp_tiktok_id.get().strip()
        email = self.inp_email.get().strip()
        password = self.inp_password.get().strip()
        machine_id = self.inp_machine_id.get().strip() or "1"

        if not tiktok_id or not email:
            self.lbl_status.configure(text="❌ Vui lòng nhập TikTok ID và Email!", text_color="red")
            return

        clean_id = "".join(x for x in tiktok_id if x.isalnum() or x in "_-")
        profile_name = f"{clean_id}_profile"

        if self.editing_tiktok_id:
            # --- CHẾ ĐỘ CẬP NHẬT ---
            existing_acc = SupabaseAPI.get_account_by_id(self.editing_tiktok_id)
            if existing_acc:
                existing_acc["email"] = email
                existing_acc["password"] = password
                existing_acc["machine_id"] = machine_id

                if SupabaseAPI.save_account(existing_acc):
                    self.lbl_status.configure(text=f"✅ Đã cập nhật thông tin cho {tiktok_id}", text_color="green")
                    self.cancel_edit()
                    self.load_accounts()
                else:
                    self.lbl_status.configure(text="❌ Lỗi khi cập nhật lên Supabase.", text_color="red")
        else:
            # --- CHẾ ĐỘ THÊM MỚI ---
            account_data = {
                "tiktok_id": tiktok_id,
                "email": email,
                "password": password,
                "chrome_profile": profile_name,
                "active": True,
                "channels": [],
                "machine_id": machine_id,
            }

            if SupabaseAPI.save_account(account_data):
                os.makedirs(os.path.join(AI_STUDIO_DIR, profile_name), exist_ok=True)
                self.lbl_status.configure(text=f"✅ Đã thêm tài khoản & tạo Profile {profile_name}", text_color="green")
                self.cancel_edit()
                self.load_accounts()
            else:
                self.lbl_status.configure(text="❌ Lỗi khi lưu lên Supabase.", text_color="red")

    def edit_account(self, acc_data):
        self.editing_tiktok_id = acc_data.get("tiktok_id") or ""

        self.inp_tiktok_id.configure(state="normal")
        self.inp_tiktok_id.delete(0, 'end')
        self.inp_tiktok_id.insert(0, self.editing_tiktok_id)
        self.inp_tiktok_id.configure(state="disabled")

        self.inp_email.delete(0, 'end')
        self.inp_email.insert(0, acc_data.get("email") or "")

        self.inp_password.delete(0, 'end')
        self.inp_password.insert(0, acc_data.get("password") or "")

        self.inp_machine_id.delete(0, 'end')
        self.inp_machine_id.insert(0, acc_data.get("machine_id") or "1")

        self.btn_save.configure(text="💾 CẬP NHẬT", fg_color="blue", hover_color="darkblue")
        self.btn_cancel.pack(side="left", padx=5)
        self.lbl_status.configure(text="✏️ Chế độ sửa: Không thể đổi tên TikTok ID gốc.", text_color="blue")

    def cancel_edit(self):
        self.editing_tiktok_id = None

        self.inp_tiktok_id.configure(state="normal")
        self.inp_tiktok_id.delete(0, 'end')

        self.inp_email.delete(0, 'end')
        self.inp_password.delete(0, 'end')
        self.inp_machine_id.delete(0, 'end')
        self.inp_machine_id.insert(0, "1")

        self.btn_save.configure(text="🚀 TẠO TÀI KHOẢN", fg_color="green", hover_color="darkgreen")
        self.btn_cancel.pack_forget()
        self.lbl_status.configure(text="")

    def load_accounts(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        accounts = SupabaseAPI.get_all_accounts()
        if not accounts: return

        def truncate_text(text, max_len):
            if not text: return ""
            return text if len(text) <= max_len else text[:max_len-3] + "..."

        for acc in accounts:
            row_frame = ctk.CTkFrame(self.scroll_frame)
            row_frame.pack(fill="x", pady=2)

            # Đã tăng độ rộng cắt text để khớp với Streamlit
            display_id = truncate_text(acc.get("tiktok_id", ""), 20)
            display_email = truncate_text(acc.get("email", ""), 35)
            display_profile = truncate_text(f"Profile: {acc.get('chrome_profile', '')}", 30)
            display_machine = f"Máy: {acc.get('machine_id', '1')}"

            # Tăng width của Label tương ứng
            ctk.CTkLabel(row_frame, text=display_id, width=150, anchor="w", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=10)
            ctk.CTkLabel(row_frame, text=display_email, width=280, anchor="w").pack(side="left", padx=10)
            ctk.CTkLabel(row_frame, text=display_profile, width=220, anchor="w").pack(side="left", padx=10)
            ctk.CTkLabel(row_frame, text=display_machine, width=60, anchor="w", text_color="orange").pack(side="left", padx=10)

            btn_del = ctk.CTkButton(row_frame, text="Xóa", width=60, fg_color="red", hover_color="darkred", command=lambda a=acc: self.delete_account(a))
            btn_del.pack(side="right", padx=10, pady=5)

            btn_edit = ctk.CTkButton(row_frame, text="Sửa", width=60, fg_color="orange", hover_color="darkorange", command=lambda a=acc: self.edit_account(a))
            btn_edit.pack(side="right", padx=5, pady=5)

            btn_chrome = ctk.CTkButton(row_frame, text="Mở Chrome", width=100, fg_color="blue", hover_color="darkblue", command=lambda p=acc.get("chrome_profile"): self.open_chrome_profile(p))
            btn_chrome.pack(side="right", padx=5, pady=5)

    def delete_account(self, acc_data):
        tiktok_id = acc_data.get("tiktok_id")
        profile_name = acc_data.get("chrome_profile")

        if SupabaseAPI.delete_account(tiktok_id):
            profile_path = os.path.join(AI_STUDIO_DIR, profile_name)
            if os.path.exists(profile_path):
                try: shutil.rmtree(profile_path)
                except: pass
            self.lbl_status.configure(text=f"✅ Đã xóa {tiktok_id}", text_color="green")
            self.cancel_edit()
            self.load_accounts()

    def open_chrome_profile(self, profile_name):
        if not profile_name: return
        self.lbl_status.configure(text=f"⏳ Đang khởi động Chrome cho {profile_name}...", text_color="blue")
        threading.Thread(target=self._launch_browser_thread, args=(profile_name,), daemon=True).start()

    def _launch_browser_thread(self, profile_name):
        profile_path = os.path.join(AI_STUDIO_DIR, profile_name)
        if not os.path.exists(profile_path):
            os.makedirs(profile_path)

        options = uc.ChromeOptions()
        options.add_argument(f"--user-data-dir={profile_path}")
        options.add_argument("--no-first-run")
        options.add_argument("--no-service-autorun")
        options.add_argument("--password-store=basic")
        options.add_argument("--start-maximized")

        driver = None
        try:
            driver = uc.Chrome(options=options, use_subprocess=True)
            driver.get("https://accounts.google.com/")
            self.lbl_status.configure(text=f"🟢 Đang mở Chrome: {profile_name}. Đăng nhập Google xong hãy TẮT TRÌNH DUYỆT để lưu.", text_color="green")
            while True:
                if driver.service.process.poll() is not None:
                    break
                time.sleep(1)
        except Exception as e:
            print(f"Lỗi khởi động Chrome: {e}")
            self.lbl_status.configure(text=f"❌ Lỗi mở Chrome (Hãy cập nhật undetected-chromedriver hoặc tắt Chrome ẩn).", text_color="red")
        finally:
            if driver:
                try: driver.quit()
                except: pass
            self.lbl_status.configure(text=f"✅ Đã đóng và lưu dữ liệu Profile {profile_name}.", text_color="green")