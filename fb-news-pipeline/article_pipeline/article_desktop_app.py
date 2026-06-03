#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════════
#  Facebook News Auto Remix — Ứng dụng Desktop độc lập
#  Chạy độc lập, không phụ thuộc vào tool TikTok (mannyAccount)
# ═══════════════════════════════════════════════════════════════════

import customtkinter as ctk
import threading
import subprocess
import os
import sys
import json
from datetime import datetime

# ═══════════════════════════════════════════════════════════
#  CẤU HÌNH
# ═══════════════════════════════════════════════════════════
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_FILE = os.path.join(APP_DIR, ".env")

# Đọc .env thủ công (không cần python-dotenv cho GUI)
def load_env():
    env = {}
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    env[key.strip()] = val.strip()
    return env

ENV = load_env()
SUPABASE_URL = ENV.get("SUPABASE_URL", "")
SUPABASE_KEY = ENV.get("SUPABASE_KEY", "")

# Khởi tạo Supabase client
supabase_client = None
try:
    from supabase import create_client
    if SUPABASE_URL and SUPABASE_KEY:
        supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
except ImportError:
    print("⚠️ Chưa cài supabase: pip install supabase")
except Exception as e:
    print(f"⚠️ Lỗi kết nối Supabase: {e}")

# ═══════════════════════════════════════════════════════════
#  THEME
# ═══════════════════════════════════════════════════════════
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

COLORS = {
    "primary": "#7c3aed",
    "primary_hover": "#6d28d9",
    "success": "#16a34a",
    "success_hover": "#15803d",
    "danger": "#dc2626",
    "danger_hover": "#b91c1c",
    "info": "#2563eb",
    "info_hover": "#1d4ed8",
    "muted": "#6b7280",
    "muted_hover": "#4b5563",
    "bg_card": "#1e1e2e",
    "text_dim": "#888888",
}


class FBNewsApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("📰 Tool Đọc Báo Mạng Tự Động")
        self.geometry("1100x780")
        self.minsize(900, 650)

        self.is_running = False
        self.process = None
        self.worker_thread = None
        self.sources_data = []

        self._build_ui()
        self._load_sources()

    # ═══════════════════════════════════════════════════════
    #  GIAO DIỆN CHÍNH
    # ═══════════════════════════════════════════════════════
    def _build_ui(self):
        # Grid layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=3)  # Tabview co giãn
        self.grid_rowconfigure(2, weight=2)  # Log co giãn

        # ── HEADER ──
        header = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=12)
        header.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 5))

        ctk.CTkLabel(
            header,
            text="📰 Hệ Thống Dựng Video Từ Báo Mạng",
            font=ctk.CTkFont(size=26, weight="bold"),
        ).pack(side="left", padx=20, pady=15)

        self.status_badge = ctk.CTkLabel(
            header,
            text="  ⚪ SẴN SÀNG  ",
            font=ctk.CTkFont(size=13, weight="bold"),
            corner_radius=8,
            fg_color="#374151",
            text_color="#9ca3af",
        )
        self.status_badge.pack(side="right", padx=20, pady=15)

        # ── TABVIEW CHÍNH ──
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=15, pady=5)
        
        self.tabview.add("📰 Chạy Pipeline")
        self.tabview.add("🖼️ Quản lý Frame & Logo")
        
        tab_pipeline = self.tabview.tab("📰 Chạy Pipeline")
        tab_assets = self.tabview.tab("🖼️ Quản lý Frame & Logo")

        # ═══════════════════════════════════════════════════════
        #  TAB 1: PIPELINE RUNNER
        # ═══════════════════════════════════════════════════════
        
        # ── THÊM NGUỒN ──
        add_frame = ctk.CTkFrame(tab_pipeline, fg_color=COLORS["bg_card"], corner_radius=12)
        add_frame.pack(fill="x", padx=15, pady=5)

        ctk.CTkLabel(
            add_frame,
            text="➕ Thêm danh mục Báo Mạng mới",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).grid(row=0, column=0, columnspan=6, sticky="w", padx=15, pady=(12, 8))

        ctk.CTkLabel(add_frame, text="ID TikTok:", font=ctk.CTkFont(size=13)).grid(row=1, column=0, padx=(15, 5), pady=8)
        self.input_name = ctk.CTkEntry(add_frame, width=200, placeholder_text="VD: adsupnew", height=35)
        self.input_name.grid(row=1, column=1, padx=5, pady=8)

        ctk.CTkLabel(add_frame, text="URL Danh mục:", font=ctk.CTkFont(size=13)).grid(row=1, column=2, padx=(15, 5), pady=8)
        self.input_url = ctk.CTkEntry(add_frame, width=380, placeholder_text="VD: https://kenh14.vn/doi-song.chn", height=35)
        self.input_url.grid(row=1, column=3, padx=5, pady=8)

        self.btn_add = ctk.CTkButton(
            add_frame, text="✅ Thêm", width=80, height=35,
            fg_color=COLORS["info"], hover_color=COLORS["info_hover"],
            font=ctk.CTkFont(weight="bold"),
            command=self._add_source,
        )
        self.btn_add.grid(row=1, column=4, padx=(10, 15), pady=8)

        # ── DANH SÁCH NGUỒN ──
        list_frame = ctk.CTkFrame(tab_pipeline, fg_color=COLORS["bg_card"], corner_radius=12)
        list_frame.pack(fill="x", padx=15, pady=5)

        list_header = ctk.CTkFrame(list_frame, fg_color="transparent")
        list_header.pack(fill="x", padx=15, pady=(12, 5))

        ctk.CTkLabel(
            list_header,
            text="📋 Nguồn đang theo dõi",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(side="left")

        btn_row = ctk.CTkFrame(list_header, fg_color="transparent")
        btn_row.pack(side="right")

        self.btn_refresh = ctk.CTkButton(
            btn_row, text="🔄", width=40, height=32,
            fg_color=COLORS["muted"], hover_color=COLORS["muted_hover"],
            command=self._load_sources,
        )
        self.btn_refresh.pack(side="left", padx=3)

        self.btn_delete = ctk.CTkButton(
            btn_row, text="🗑️ Xóa", width=70, height=32,
            fg_color=COLORS["danger"], hover_color=COLORS["danger_hover"],
            command=self._delete_selected,
        )
        self.btn_delete.pack(side="left", padx=3)

        self.source_list = ctk.CTkTextbox(list_frame, height=110, state="disabled", font=ctk.CTkFont(family="monospace", size=12))
        self.source_list.pack(fill="x", padx=15, pady=(0, 5))

        self.selected_source_var = ctk.StringVar(value="-- Chọn nguồn để xóa --")
        self.source_dropdown = ctk.CTkOptionMenu(
            list_frame, variable=self.selected_source_var,
            values=["-- Chọn nguồn để xóa --"], width=500,
            fg_color="#374151", button_color=COLORS["muted"],
        )
        self.source_dropdown.pack(padx=15, pady=(0, 12))

        # ── QUẢN LÝ CHROME CHATGPT ──
        chrome_frame = ctk.CTkFrame(tab_pipeline, fg_color=COLORS["bg_card"], corner_radius=12)
        chrome_frame.pack(fill="x", padx=15, pady=5)
        
        ctk.CTkLabel(
            chrome_frame,
            text="🌐 Quản lý Trình duyệt ChatGPT",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=15, pady=(12, 5))
        
        self.selected_chrome_var = ctk.StringVar(value="-- Chọn kênh để đăng nhập ChatGPT --")
        self.chrome_dropdown = ctk.CTkOptionMenu(
            chrome_frame, variable=self.selected_chrome_var,
            values=["-- Chọn kênh để đăng nhập ChatGPT --"], width=300,
            fg_color="#374151", button_color=COLORS["muted"],
        )
        self.chrome_dropdown.grid(row=1, column=0, padx=15, pady=(0, 12), sticky="w")
        
        self.btn_login = ctk.CTkButton(
            chrome_frame, text="🔑 Mở Chrome Đăng Nhập", width=160, height=32,
            fg_color=COLORS["success"], hover_color=COLORS["success_hover"],
            command=self._login_selected,
        )
        self.btn_login.grid(row=1, column=1, padx=5, pady=(0, 12), sticky="w")

        # ── NÚT ĐIỀU KHIỂN ──
        ctrl_frame = ctk.CTkFrame(tab_pipeline, fg_color="transparent")
        ctrl_frame.pack(fill="x", padx=15, pady=5)

        self.btn_start = ctk.CTkButton(
            ctrl_frame,
            text="▶️   BẮT ĐẦU CHẠY PIPELINE",
            font=ctk.CTkFont(size=20, weight="bold"),
            fg_color=COLORS["success"], hover_color=COLORS["success_hover"],
            height=55,
            corner_radius=12,
            command=self._toggle_pipeline,
        )
        self.btn_start.pack(side="left", expand=True, fill="x", padx=(0, 5))

        self.btn_run_once = ctk.CTkButton(
            ctrl_frame,
            text="🔂 Chạy 1 lần",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"],
            height=55,
            width=150,
            corner_radius=12,
            command=self._run_once,
        )
        self.btn_run_once.pack(side="right", padx=(5, 0))


        # ═══════════════════════════════════════════════════════
        #  TAB 2: FRAME & LOGO MANAGER
        # ═══════════════════════════════════════════════════════
        tab_assets.grid_columnconfigure(0, weight=1)
        tab_assets.grid_columnconfigure(1, weight=1)
        tab_assets.grid_rowconfigure(0, weight=1)

        # Cột trái: Chọn kênh & Upload files
        left_frame = ctk.CTkFrame(tab_assets, fg_color=COLORS["bg_card"], corner_radius=12)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(15, 10), pady=15)
        
        ctk.CTkLabel(
            left_frame,
            text="🖼️ Quản lý tài nguyên (PNG)",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(15, 10))

        # Dropdown chọn kênh
        ctk.CTkLabel(left_frame, text="Chọn kênh TikTok:", font=ctk.CTkFont(size=13)).pack(anchor="w", padx=20, pady=(5, 2))
        
        self.asset_channel_var = ctk.StringVar(value="-- Chọn kênh --")
        self.asset_channel_dropdown = ctk.CTkOptionMenu(
            left_frame,
            variable=self.asset_channel_var,
            values=["-- Chọn kênh --"],
            command=self._on_asset_channel_select,
            fg_color="#374151",
            button_color=COLORS["muted"],
            width=250,
        )
        self.asset_channel_dropdown.pack(anchor="w", padx=20, pady=(0, 15))

        # Status & Upload cho Frame
        frame_box = ctk.CTkFrame(left_frame, fg_color="transparent")
        frame_box.pack(fill="x", padx=20, pady=5)
        
        ctk.CTkLabel(frame_box, text="Khung viền (Frame.png):", font=ctk.CTkFont(weight="bold")).pack(anchor="w")
        self.lbl_frame_status = ctk.CTkLabel(frame_box, text="Chưa chọn kênh", text_color=COLORS["text_dim"])
        self.lbl_frame_status.pack(anchor="w", pady=(0, 5))
        
        btn_frame_row = ctk.CTkFrame(frame_box, fg_color="transparent")
        btn_frame_row.pack(anchor="w")
        
        self.btn_up_frame = ctk.CTkButton(
            btn_frame_row, text="📤 Tải lên Frame", width=120, height=32,
            fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"],
            command=self._upload_frame
        )
        self.btn_up_frame.pack(side="left", padx=(0, 5))
        
        self.btn_del_frame = ctk.CTkButton(
            btn_frame_row, text="🗑️ Xóa", width=70, height=32,
            fg_color=COLORS["danger"], hover_color=COLORS["danger_hover"],
            command=self._delete_frame,
            state="disabled"
        )
        self.btn_del_frame.pack(side="left")

        # Status & Upload cho Logo
        logo_box = ctk.CTkFrame(left_frame, fg_color="transparent")
        logo_box.pack(fill="x", padx=20, pady=15)
        
        ctk.CTkLabel(logo_box, text="Logo (Logo.png):", font=ctk.CTkFont(weight="bold")).pack(anchor="w")
        self.lbl_logo_status = ctk.CTkLabel(logo_box, text="Chưa chọn kênh", text_color=COLORS["text_dim"])
        self.lbl_logo_status.pack(anchor="w", pady=(0, 5))
        
        btn_logo_row = ctk.CTkFrame(logo_box, fg_color="transparent")
        btn_logo_row.pack(anchor="w")
        
        self.btn_up_logo = ctk.CTkButton(
            btn_logo_row, text="📤 Tải lên Logo", width=120, height=32,
            fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"],
            command=self._upload_logo
        )
        self.btn_up_logo.pack(side="left", padx=(0, 5))
        
        self.btn_del_logo = ctk.CTkButton(
            btn_logo_row, text="🗑️ Xóa", width=70, height=32,
            fg_color=COLORS["danger"], hover_color=COLORS["danger_hover"],
            command=self._delete_logo,
            state="disabled"
        )
        self.btn_del_logo.pack(side="left")

        # Cột phải: Cấu hình toạ độ Logo
        right_frame = ctk.CTkFrame(tab_assets, fg_color=COLORS["bg_card"], corner_radius=12)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 15), pady=15)
        
        ctk.CTkLabel(
            right_frame,
            text="⚙️ Tọa độ & Tỷ lệ Logo",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(15, 10))

        # Tọa độ X
        ctk.CTkLabel(right_frame, text="Tọa độ X (Cách lề trái - px):", font=ctk.CTkFont(size=13)).pack(anchor="w", padx=20, pady=(5, 2))
        self.input_logo_x = ctk.CTkEntry(right_frame, width=120, height=32)
        self.input_logo_x.pack(anchor="w", padx=20, pady=(0, 10))
        
        # Tọa độ Y
        ctk.CTkLabel(right_frame, text="Tọa độ Y (Cách lề trên - px):", font=ctk.CTkFont(size=13)).pack(anchor="w", padx=20, pady=(5, 2))
        self.input_logo_y = ctk.CTkEntry(right_frame, width=120, height=32)
        self.input_logo_y.pack(anchor="w", padx=20, pady=(0, 10))
        
        # Tỷ lệ scale
        ctk.CTkLabel(right_frame, text="Kích thước Logo (Chiều rộng - px):", font=ctk.CTkFont(size=13)).pack(anchor="w", padx=20, pady=(5, 2))
        self.input_logo_scale = ctk.CTkEntry(right_frame, width=120, height=32)
        self.input_logo_scale.pack(anchor="w", padx=20, pady=(0, 20))

        # Nút Lưu Cấu Hình
        self.btn_save_config = ctk.CTkButton(
            right_frame, text="💾 Lưu cấu hình Logo", width=180, height=38,
            fg_color=COLORS["success"], hover_color=COLORS["success_hover"],
            font=ctk.CTkFont(weight="bold"),
            command=self._save_asset_config
        )
        self.btn_save_config.pack(anchor="w", padx=20, pady=10)


        # ═══════════════════════════════════════════════════════
        #  LOG AREA (BÊN NGOÀI TABVIEW - LUÔN HIỂN THỊ)
        # ═══════════════════════════════════════════════════════
        log_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=12)
        log_frame.grid(row=2, column=0, sticky="nsew", padx=15, pady=(5, 15))
        log_frame.grid_rowconfigure(1, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)

        log_header = ctk.CTkFrame(log_frame, fg_color="transparent")
        log_header.grid(row=0, column=0, sticky="ew", padx=15, pady=(12, 5))

        ctk.CTkLabel(
            log_header,
            text="📋 Nhật ký hoạt động",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(side="left")

        ctk.CTkButton(
            log_header, text="🧹 Xóa log", width=80, height=28,
            fg_color=COLORS["muted"], hover_color=COLORS["muted_hover"],
            command=self._clear_log,
        ).pack(side="right")

        self.log_textbox = ctk.CTkTextbox(
            log_frame, state="disabled",
            font=ctk.CTkFont(family="monospace", size=12),
        )
        self.log_textbox.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 15))

        self.log("🟢 Hệ thống Auto Báo Mạng đã sẵn sàng!")
        self.log(f"📂 Thư mục pipeline: {APP_DIR}")
        if supabase_client:
            self.log("✅ Đã kết nối Supabase thành công.")
        else:
            self.log("❌ Chưa kết nối Supabase! Kiểm tra file .env")

    # ═══════════════════════════════════════════════════════
    #  CÁC HÀM QUẢN LÝ ASSETS (FRAME/LOGO)
    # ═══════════════════════════════════════════════════════
    # ═══════════════════════════════════════════════════════
    #  CÁC HÀM QUẢN LÝ ASSETS (FRAME/LOGO)
    # ═══════════════════════════════════════════════════════
    def _on_asset_channel_select(self, selected_channel):
        if not selected_channel or selected_channel.startswith("--"):
            self.lbl_frame_status.configure(text="Chưa chọn kênh", text_color=COLORS["text_dim"])
            self.lbl_logo_status.configure(text="Chưa chọn kênh", text_color=COLORS["text_dim"])
            self.input_logo_x.delete(0, "end")
            self.input_logo_y.delete(0, "end")
            self.input_logo_scale.delete(0, "end")
            return
            
        channel_dir = os.path.join(APP_DIR, "assets", "channels", selected_channel)
        os.makedirs(channel_dir, exist_ok=True)
        
        frame_path = os.path.join(channel_dir, "frame.png")
        logo_path = os.path.join(channel_dir, "logo.png")
        config_path = os.path.join(channel_dir, "config.json")
        
        # 1. Kiểm tra trạng thái trên Supabase Storage & Đồng bộ về local
        has_cloud_frame = False
        has_cloud_logo = False
        has_cloud_config = False
        
        if supabase_client:
            try:
                res = supabase_client.storage.from_("assets").list(f"channels/{selected_channel}")
                if isinstance(res, list):
                    cloud_files = [f.get("name") for f in res if isinstance(f, dict) and f.get("name")]
                    
                    if "frame.png" in cloud_files:
                        has_cloud_frame = True
                        try:
                            data = supabase_client.storage.from_("assets").download(f"channels/{selected_channel}/frame.png")
                            with open(frame_path, "wb") as f:
                                f.write(data)
                        except Exception as e:
                            self.log(f"⚠️ Lỗi đồng bộ Frame từ Cloud: {e}")
                            
                    if "logo.png" in cloud_files:
                        has_cloud_logo = True
                        try:
                            data = supabase_client.storage.from_("assets").download(f"channels/{selected_channel}/logo.png")
                            with open(logo_path, "wb") as f:
                                f.write(data)
                        except Exception as e:
                            self.log(f"⚠️ Lỗi đồng bộ Logo từ Cloud: {e}")
                            
                    if "config.json" in cloud_files:
                        has_cloud_config = True
                        try:
                            data = supabase_client.storage.from_("assets").download(f"channels/{selected_channel}/config.json")
                            with open(config_path, "wb") as f:
                                f.write(data)
                        except Exception as e:
                            self.log(f"⚠️ Lỗi đồng bộ cấu hình từ Cloud: {e}")
            except Exception as e:
                self.log(f"⚠️ Không kiểm tra được storage Cloud: {e}")
                
        # 2. Cập nhật UI dựa trên sự hiện diện của file (ưu tiên Cloud, nếu ko có thì check local)
        frame_exists = has_cloud_frame or os.path.exists(frame_path)
        if frame_exists:
            self.lbl_frame_status.configure(text="✅ Đã có file frame.png (Từ Cloud)", text_color=COLORS["success"])
            self.btn_del_frame.configure(state="normal")
        else:
            self.lbl_frame_status.configure(text="❌ Chưa có file frame.png (Dùng mặc định)", text_color="orange")
            self.btn_del_frame.configure(state="disabled")
            
        logo_exists = has_cloud_logo or os.path.exists(logo_path)
        if logo_exists:
            self.lbl_logo_status.configure(text="✅ Đã có file logo.png (Từ Cloud)", text_color=COLORS["success"])
            self.btn_del_logo.configure(state="normal")
        else:
            self.lbl_logo_status.configure(text="❌ Chưa có file logo.png (Dùng mặc định)", text_color="orange")
            self.btn_del_logo.configure(state="disabled")
            
        # Đọc cấu hình config.json (đã được đồng bộ ở trên)
        cfg = {"logo_x": 50, "logo_y": 50, "logo_scale": 150}
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg.update(json.load(f))
            except:
                pass
                
        self.input_logo_x.delete(0, "end")
        self.input_logo_x.insert(0, str(cfg.get("logo_x", 50)))
        
        self.input_logo_y.delete(0, "end")
        self.input_logo_y.insert(0, str(cfg.get("logo_y", 50)))
        
        self.input_logo_scale.delete(0, "end")
        self.input_logo_scale.insert(0, str(cfg.get("logo_scale", 150)))

    def _upload_frame(self):
        channel = self.asset_channel_var.get()
        if not channel or channel.startswith("--"):
            self.log("⚠️ Hãy chọn 1 kênh trước khi tải lên Frame.")
            return
            
        if not supabase_client:
            self.log("❌ Lỗi: Chưa kết nối Supabase, không thể upload lên Storage.")
            return
            
        from tkinter import filedialog
        import shutil
        
        file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.png")])
        if not file_path:
            return
            
        channel_dir = os.path.join(APP_DIR, "assets", "channels", channel)
        os.makedirs(channel_dir, exist_ok=True)
        dest = os.path.join(channel_dir, "frame.png")
        
        try:
            # Lưu local trước
            shutil.copy(file_path, dest)
            
            # Upload lên Supabase Storage
            storage_path = f"channels/{channel}/frame.png"
            with open(dest, "rb") as f:
                try:
                    supabase_client.storage.from_("assets").upload(storage_path, f, file_options={"upsert": True})
                except Exception:
                    supabase_client.storage.from_("assets").update(storage_path, f)
                    
            self.log(f"✅ Đã tải lên Frame mới cho kênh {channel} lên Supabase Storage.")
            self._on_asset_channel_select(channel)
        except Exception as e:
            self.log(f"❌ Lỗi khi upload Frame lên Supabase: {e}")

    def _upload_logo(self):
        channel = self.asset_channel_var.get()
        if not channel or channel.startswith("--"):
            self.log("⚠️ Hãy chọn 1 kênh trước khi tải lên Logo.")
            return
            
        if not supabase_client:
            self.log("❌ Lỗi: Chưa kết nối Supabase, không thể upload lên Storage.")
            return
            
        from tkinter import filedialog
        import shutil
        
        file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.png")])
        if not file_path:
            return
            
        channel_dir = os.path.join(APP_DIR, "assets", "channels", channel)
        os.makedirs(channel_dir, exist_ok=True)
        dest = os.path.join(channel_dir, "logo.png")
        
        try:
            # Lưu local trước
            shutil.copy(file_path, dest)
            
            # Upload lên Supabase Storage
            storage_path = f"channels/{channel}/logo.png"
            with open(dest, "rb") as f:
                try:
                    supabase_client.storage.from_("assets").upload(storage_path, f, file_options={"upsert": True})
                except Exception:
                    supabase_client.storage.from_("assets").update(storage_path, f)
                    
            self.log(f"✅ Đã tải lên Logo mới cho kênh {channel} lên Supabase Storage.")
            self._on_asset_channel_select(channel)
        except Exception as e:
            self.log(f"❌ Lỗi khi upload Logo lên Supabase: {e}")

    def _delete_frame(self):
        channel = self.asset_channel_var.get()
        if not channel or channel.startswith("--"):
            return
            
        if not supabase_client:
            return
            
        storage_path = f"channels/{channel}/frame.png"
        try:
            supabase_client.storage.from_("assets").remove([storage_path])
        except Exception as e:
            self.log(f"⚠️ Lỗi xóa Frame trên Cloud: {e}")
            
        channel_dir = os.path.join(APP_DIR, "assets", "channels", channel)
        frame_path = os.path.join(channel_dir, "frame.png")
        if os.path.exists(frame_path):
            try:
                os.remove(frame_path)
            except Exception as e:
                pass
                
        self.log(f"🗑️ Đã xóa file Frame của kênh {channel}")
        self._on_asset_channel_select(channel)

    def _delete_logo(self):
        channel = self.asset_channel_var.get()
        if not channel or channel.startswith("--"):
            return
            
        if not supabase_client:
            return
            
        storage_path = f"channels/{channel}/logo.png"
        try:
            supabase_client.storage.from_("assets").remove([storage_path])
        except Exception as e:
            self.log(f"⚠️ Lỗi xóa Logo trên Cloud: {e}")
            
        channel_dir = os.path.join(APP_DIR, "assets", "channels", channel)
        logo_path = os.path.join(channel_dir, "logo.png")
        if os.path.exists(logo_path):
            try:
                os.remove(logo_path)
            except Exception as e:
                pass
                
        self.log(f"🗑️ Đã xóa file Logo của kênh {channel}")
        self._on_asset_channel_select(channel)

    def _save_asset_config(self):
        channel = self.asset_channel_var.get()
        if not channel or channel.startswith("--"):
            self.log("⚠️ Hãy chọn 1 kênh trước khi lưu cấu hình.")
            return
            
        if not supabase_client:
            self.log("❌ Lỗi: Chưa kết nối Supabase, không thể lưu cấu hình lên Cloud.")
            return
            
        try:
            lx = int(self.input_logo_x.get().strip() or "50")
            ly = int(self.input_logo_y.get().strip() or "50")
            lscale = int(self.input_logo_scale.get().strip() or "150")
        except ValueError:
            self.log("❌ Các thông số X, Y, Tỷ lệ phải là số nguyên!")
            return
            
        channel_dir = os.path.join(APP_DIR, "assets", "channels", channel)
        os.makedirs(channel_dir, exist_ok=True)
        config_path = os.path.join(channel_dir, "config.json")
        
        cfg = {
            "logo_x": lx,
            "logo_y": ly,
            "logo_scale": lscale
        }
        
        try:
            # Lưu local trước
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
                
            # Upload lên Supabase Storage
            storage_path = f"channels/{channel}/config.json"
            with open(config_path, "rb") as f:
                try:
                    supabase_client.storage.from_("assets").upload(storage_path, f, file_options={"upsert": True})
                except Exception:
                    supabase_client.storage.from_("assets").update(storage_path, f)
                    
            self.log(f"💾 Đã lưu cấu hình Logo cho kênh {channel} lên Supabase Storage (X: {lx}, Y: {ly}, Rộng: {lscale}px)")
        except Exception as e:
            self.log(f"❌ Lỗi lưu cấu hình lên Cloud: {e}")

    # ═══════════════════════════════════════════════════════
    #  THÊM NGUỒN
    # ═══════════════════════════════════════════════════════
    def _add_source(self):
        id_tiktok = self.input_name.get().strip()
        category_url = self.input_url.get().strip()

        if not id_tiktok or not category_url:
            self.log("❌ Vui lòng điền đầy đủ ID TikTok và URL Danh mục.")
            return

        if not supabase_client:
            self.log("❌ Chưa kết nối Supabase!")
            return

        category_url = category_url.rstrip("/")

        try:
            result = supabase_client.table("article_sources").insert({
                "id_tiktok": id_tiktok,
                "category_url": category_url,
                "is_active": True
            }).execute()

            if result.data:
                self.log(f"✅ Đã thêm nguồn Báo cho: {id_tiktok} → {category_url}")
                self.input_name.delete(0, "end")
                self.input_url.delete(0, "end")
                self._load_sources()
            else:
                self.log("❌ Thêm nguồn thất bại!")
        except Exception as e:
            err = str(e)
            if "duplicate" in err.lower() or "23505" in err:
                self.log(f"⚠️ Nguồn báo đã tồn tại: {category_url}")
            else:
                self.log(f"❌ Lỗi: {e}")

    # ═══════════════════════════════════════════════════════
    #  LOAD DANH SÁCH NGUỒN
    # ═══════════════════════════════════════════════════════
    def _load_sources(self):
        if not supabase_client:
            return

        try:
            result = supabase_client.table("article_sources").select("*").order("created_at").execute()
            sources = result.data or []
            self.sources_data = sources

            self.source_list.configure(state="normal")
            self.source_list.delete("1.0", "end")

            if not sources:
                self.source_list.insert("end", "  📭 Chưa có nguồn nào. Thêm nguồn Báo Mạng ở phía trên.\n")
            else:
                header = f"  {'#':<4} {'ID TikTok':<22} {'URL Danh mục':<50} {'On':<5}\n"
                self.source_list.insert("end", header)
                self.source_list.insert("end", "  " + "─" * 90 + "\n")

                for i, s in enumerate(sources, 1):
                    active = "✅" if s.get("is_active") else "❌"
                    id_tiktok = (s.get("id_tiktok") or "")[:21]
                    url = (s.get("category_url") or "")[:49]
                    
                    line = f"  {i:<4} {id_tiktok:<22} {url:<50} {active:<5}\n"
                    self.source_list.insert("end", line)

            self.source_list.configure(state="disabled")

            # Cập nhật dropdown xóa và chrome
            dropdown_vals = ["-- Chọn nguồn để xóa --"]
            chrome_vals = ["-- Chọn kênh để đăng nhập ChatGPT --"]
            asset_vals = []
            
            for s in sources:
                label = f"{s.get('id_tiktok', '')} | {s.get('category_url', '')}"
                dropdown_vals.append(label)
                chrome_vals.append(s.get('id_tiktok', ''))
                if s.get('id_tiktok'):
                    asset_vals.append(s.get('id_tiktok'))
                
            self.source_dropdown.configure(values=dropdown_vals)
            self.selected_source_var.set(dropdown_vals[0])
            
            self.chrome_dropdown.configure(values=chrome_vals)
            self.selected_chrome_var.set(chrome_vals[0])

            # Cập nhật dropdown quản lý assets
            if not asset_vals:
                asset_vals = ["-- Chọn kênh --"]
            self.asset_channel_dropdown.configure(values=asset_vals)
            
            # Cập nhật chọn kênh assets mặc định nếu kênh cũ bị xóa hoặc chưa chọn gì
            current_asset_sel = self.asset_channel_var.get()
            if current_asset_sel not in asset_vals:
                self.asset_channel_var.set(asset_vals[0])
                self._on_asset_channel_select(asset_vals[0])

        except Exception as e:
            self.log(f"❌ Lỗi load nguồn: {e}")

    # ═══════════════════════════════════════════════════════
    #  XÓA NGUỒN
    # ═══════════════════════════════════════════════════════
    def _delete_selected(self):
        selected = self.selected_source_var.get()
        if selected.startswith("--"):
            self.log("⚠️ Chọn nguồn cần xóa từ dropdown trước.")
            return

        try:
            category_url = selected.split(" | ")[-1].strip()
            matched = [s for s in self.sources_data if s.get("category_url") == category_url]
            if matched:
                sid = matched[0]["id"]
                supabase_client.table("article_sources").delete().eq("id", sid).execute()
                self.log(f"🗑️ Đã xóa nguồn: {category_url}")
                self._load_sources()
            else:
                self.log("⚠️ Không tìm thấy nguồn này.")
        except Exception as e:
            self.log(f"❌ Lỗi xóa: {e}")

    # ═══════════════════════════════════════════════════════
    #  ĐĂNG NHẬP CHATGPT
    # ═══════════════════════════════════════════════════════
    def _login_selected(self):
        selected = self.selected_chrome_var.get()
        if selected.startswith("--"):
            self.log("⚠️ Hãy chọn 1 kênh từ mục Quản lý Trình duyệt trước.")
            return

        id_tiktok = selected.strip()
        self.log(f"🔑 Đang mở trình duyệt đăng nhập ChatGPT cho kênh: {id_tiktok}...")
        self.log("👉 Vui lòng thao tác trên cửa sổ Chrome vừa bật lên!")

        def run_login():
            try:
                python_exe = sys.executable
                cmd = [python_exe, "article_pipeline/article_chatgpt_automator.py", "login", id_tiktok]
                subprocess.run(cmd, cwd=APP_DIR)
                self.log(f"✅ Đã đóng cửa sổ đăng nhập ChatGPT của {id_tiktok}.")
            except Exception as e:
                self.log(f"❌ Lỗi khi mở Chrome: {e}")
                
        threading.Thread(target=run_login, daemon=True).start()

    # ═══════════════════════════════════════════════════════
    #  ĐIỀU KHIỂN PIPELINE
    # ═══════════════════════════════════════════════════════
    def _toggle_pipeline(self):
        if self.is_running:
            self._stop_pipeline()
        else:
            self._start_pipeline(loop=True)

    def _run_once(self):
        if self.is_running:
            self.log("⚠️ Pipeline đang chạy!")
            return
        self._start_pipeline(loop=False)

    def _start_pipeline(self, loop=True):
        # Kiểm tra có nguồn active không
        active_sources = [s for s in self.sources_data if s.get("is_active")]
        if not active_sources:
            self.log("⚠️ Chưa có nguồn Facebook active! Thêm nguồn trước.")
            return

        self.is_running = True
        mode = "start" if loop else "run-once"

        self.btn_start.configure(
            text="⏸️   DỪNG PIPELINE",
            fg_color=COLORS["danger"],
            hover_color=COLORS["danger_hover"],
        )
        self.btn_run_once.configure(state="disabled")
        self.status_badge.configure(
            text="  🟢 ĐANG CHẠY  ",
            fg_color="#166534",
            text_color="#4ade80",
        )

        self.log("")
        self.log("═" * 55)
        self.log(f"🚀 BẮT ĐẦU PIPELINE {'(Liên tục)' if loop else '(1 lần)'}")
        self.log(f"📡 {len(active_sources)} nguồn active")
        self.log("═" * 55)
        self.log("")

        self.worker_thread = threading.Thread(
            target=self._pipeline_worker,
            args=(mode,),
            daemon=True,
        )
        self.worker_thread.start()

    def _stop_pipeline(self):
        self.is_running = False
        if self.process:
            try:
                self.process.terminate()
                self.process.kill()
            except:
                pass
            self.process = None

        self.btn_start.configure(
            text="▶️   BẮT ĐẦU CHẠY PIPELINE",
            fg_color=COLORS["success"],
            hover_color=COLORS["success_hover"],
        )
        self.btn_run_once.configure(state="normal")
        self.status_badge.configure(
            text="  ⚪ SẴN SÀNG  ",
            fg_color="#374151",
            text_color="#9ca3af",
        )
        self.log("🛑 Đã dừng pipeline.")

    def _pipeline_worker(self, mode):
        """Chạy pipeline Bài báo bằng subprocess"""
        try:
            # Dùng cùng Python interpreter đang chạy GUI
            python_exe = sys.executable
            # Gọi file điều phối chính của Báo (Sẽ viết sau)
            cmd = [python_exe, "-u", "article_pipeline/article_pipeline_core.py", mode]
            self.log(f"🖥️ Lệnh: {' '.join(cmd)}")

            self.process = subprocess.Popen(
                cmd,
                cwd=APP_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                encoding="utf-8",
                bufsize=1,
            )

            for line in iter(self.process.stdout.readline, ""):
                if not self.is_running:
                    break
                line = line.rstrip()
                if line:
                    self.log(line)

            code = 0
            if self.process:
                self.process.wait()
                code = self.process.returncode

            if code == 0:
                self.log("\n✅ Pipeline hoàn thành!")
            elif code is not None:
                self.log(f"\n⚠️ Pipeline thoát: code {code}")

        except Exception as e:
            self.log(f"❌ Lỗi: {e}")
        finally:
            self.process = None
            self.after(0, self._stop_pipeline)

    # ═══════════════════════════════════════════════════════
    #  LOG
    # ═══════════════════════════════════════════════════════
    def log(self, message):
        ts = datetime.now().strftime("%H:%M:%S")
        full = f"[{ts}] {message}\n"
        print(full.strip())
        self.after(0, self._write_log, full)

    def _write_log(self, msg):
        try:
            if self.log_textbox.winfo_exists():
                self.log_textbox.configure(state="normal")
                self.log_textbox.insert("end", msg)
                self.log_textbox.see("end")
                self.log_textbox.configure(state="disabled")
        except:
            pass

    def _clear_log(self):
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        self.log_textbox.configure(state="disabled")
        self.log("🧹 Đã xóa log.")

    # ═══════════════════════════════════════════════════════
    #  ĐÓNG APP
    # ═══════════════════════════════════════════════════════
    def on_closing(self):
        if self.is_running:
            self._stop_pipeline()
        self.destroy()


# ═══════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = FBNewsApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
