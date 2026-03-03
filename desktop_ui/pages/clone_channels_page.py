import customtkinter as ctk
import threading
import time
import os
import sys
import requests
import json

# ================= CẤU HÌNH ĐƯỜNG DẪN =================
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(PROJECT_ROOT)

TEMP_VOICE_DIR = os.path.join(PROJECT_ROOT, "assets", "temp_voice")
FRAME_DIR = os.path.join(PROJECT_ROOT, "assets", "frame")
LOGO_DIR = os.path.join(PROJECT_ROOT, "assets", "logo")
FONT_DIR = os.path.join(PROJECT_ROOT, "assets", "font")
CREDENTIALS_FILE = os.path.join(PROJECT_ROOT, "config", "credentials.json")
TEMP_WORK_DIR = os.path.join(PROJECT_ROOT, "assets", "temp_downloads")

for d in [TEMP_VOICE_DIR, FRAME_DIR, LOGO_DIR, FONT_DIR, TEMP_WORK_DIR]:
    if not os.path.exists(d): os.makedirs(d)

from services.supabase_api import SupabaseAPI
try:
    from modules.video_handler import download_tiktok_video
    from modules.ai_studio_uploader import upload_worker
    from modules.video_remix import create_video_from_source_video
    from modules.upload_drive import upload_video_to_drive
    from services.sheet_api import get_latest_row_by_id, update_final_result, update_voice_links
    from services.tts_api import generate_voice, check_request_status
except ImportError as e:
    print(f"⚠️ Lỗi Import thư viện: {e}")


def load_credentials():
    if not os.path.exists(CREDENTIALS_FILE): return {}
    try:
        with open(CREDENTIALS_FILE, "r", encoding="utf-8") as f: return json.load(f)
    except: return {}

class CloneChannelsPage:
    def __init__(self, parent_frame):
        self.parent = parent_frame

        self.title = ctk.CTkLabel(self.parent, text="✂️ Trạm Remix Thủ Công (Dán Link)", font=ctk.CTkFont(size=24, weight="bold"))
        self.title.pack(pady=(0, 10), anchor="w")

        self.filter_frame = ctk.CTkFrame(self.parent)
        self.filter_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(self.filter_frame, text="1. Chọn ID Tài khoản:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(10, 5), pady=10)
        self.acc_dropdown = ctk.CTkOptionMenu(self.filter_frame, values=["Đang tải..."], command=self.on_account_select)
        self.acc_dropdown.pack(side="left", padx=5)

        ctk.CTkLabel(self.filter_frame, text="2. Chọn Kênh (Mượn chỉ số Edit):", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(20, 5))
        self.channel_dropdown = ctk.CTkOptionMenu(self.filter_frame, values=["Chọn tài khoản trước"], width=300)
        self.channel_dropdown.pack(side="left", padx=5)

        self.input_frame = ctk.CTkFrame(self.parent)
        self.input_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(self.input_frame, text="3. Dán Link TikTok:", font=ctk.CTkFont(weight="bold"), text_color="cyan").pack(side="left", padx=(10,5), pady=10)

        self.inp_url = ctk.CTkEntry(self.input_frame, width=500, placeholder_text="Nhập link TikTok và nhấn Enter...")
        self.inp_url.pack(side="left", padx=5, expand=True, fill="x")
        self.inp_url.bind("<Return>", self.add_to_queue)

        self.btn_add = ctk.CTkButton(self.input_frame, text="➕ THÊM VÀO HÀNG CHỜ", font=ctk.CTkFont(weight="bold"), fg_color="green", hover_color="darkgreen", command=self.add_to_queue)
        self.btn_add.pack(side="right", padx=10)

        ctk.CTkLabel(self.parent, text="⏳ Hàng đợi xử lý:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(10,0))

        self.scroll_frame = ctk.CTkScrollableFrame(self.parent, width=800, height=400)
        self.scroll_frame.pack(fill="both", expand=True, pady=5)

        self.accounts_data = []
        self.queue = []
        self.is_processing = False

        self.load_initial_data()

    def load_initial_data(self):
        self.accounts_data = SupabaseAPI.get_all_accounts() or []
        acc_ids = [acc.get("tiktok_id") for acc in self.accounts_data if acc.get("tiktok_id")]
        if not acc_ids:
            self.acc_dropdown.configure(values=["Không có dữ liệu"])
            self.channel_dropdown.configure(values=["Không có dữ liệu"])
            return
        self.acc_dropdown.configure(values=acc_ids)
        self.acc_dropdown.set(acc_ids[0])
        self.on_account_select(acc_ids[0])

    def on_account_select(self, selected_id):
        account = next((acc for acc in self.accounts_data if acc.get("tiktok_id") == selected_id), None)
        if not account: return
        channels = account.get("channels", [])
        channel_urls = [chn.get("url") for chn in channels if chn.get("url")]

        if not channel_urls:
            self.channel_dropdown.configure(values=["⚠️ Tài khoản chưa có kênh cấu hình"])
            self.channel_dropdown.set("⚠️ Tài khoản chưa có kênh cấu hình")
            return

        self.channel_dropdown.configure(values=channel_urls)
        self.channel_dropdown.set(channel_urls[0])

    def add_to_queue(self, event=None):
        url = self.inp_url.get().strip()
        if not url: return

        tiktok_id = self.acc_dropdown.get()
        channel_url = self.channel_dropdown.get()

        if not channel_url or "chưa có kênh" in channel_url.lower() or "chọn tài khoản" in channel_url.lower() or "đang tải" in channel_url.lower():
            self._show_temp_error("❌ Vui lòng chọn ID Tài khoản và Kênh cấu hình trước khi dán link!")
            return

        acc_data = next((acc for acc in self.accounts_data if acc.get("tiktok_id") == tiktok_id), None)
        channel_data = next((chn for chn in acc_data.get("channels", []) if chn.get("url") == channel_url), {})

        row = ctk.CTkFrame(self.scroll_frame)
        row.pack(fill="x", pady=2)

        ctk.CTkLabel(row, text="🔗").pack(side="left", padx=5)

        short_url = url if len(url) < 40 else url[:40] + "..."
        ctk.CTkLabel(row, text=short_url, width=250, anchor="w").pack(side="left", padx=5)

        short_channel = channel_url.split('@')[-1] if '@' in channel_url else "Kênh"
        ctk.CTkLabel(row, text=f"👤 {tiktok_id} | ⚙️ Cấu hình: {short_channel}", width=250, anchor="w", text_color="cyan").pack(side="left", padx=5)

        lbl_status = ctk.CTkLabel(row, text="Đang chờ...", text_color="orange", font=ctk.CTkFont(weight="bold"))
        lbl_status.pack(side="right", padx=10)

        item = {
            "url": url,
            "acc_data": acc_data,
            "channel_data": channel_data,
            "lbl_status": lbl_status
        }
        self.queue.append(item)

        self.inp_url.delete(0, 'end')
        self._check_queue()

    def _show_temp_error(self, msg):
        old_color = self.inp_url.cget("border_color")
        self.inp_url.configure(border_color="red")
        self.inp_url.delete(0, 'end')
        self.inp_url.insert(0, msg)
        self.parent.after(2000, lambda: [self.inp_url.delete(0, 'end'), self.inp_url.configure(border_color=old_color)])

    def _update_item_status(self, item, msg, color="orange"):
        try:
            if item["lbl_status"].winfo_exists():
                item["lbl_status"].configure(text=msg, text_color=color)
        except: pass

    # ================= LOGIC XỬ LÝ VIDEO TRUNG TÂM =================
    def _check_queue(self):
        if self.is_processing or not self.queue:
            return

        self.is_processing = True
        item = self.queue.pop(0)

        threading.Thread(target=self._worker_process, args=(item,), daemon=True).start()

    def _worker_process(self, item):
        try:
            acc_data = item["acc_data"]
            channel_data = item["channel_data"]
            vid_url = item["url"]

            self.parent.after(0, self._update_item_status, item, "⏳ Đang tải Setting DB...", "orange")

            # 1. Tải Settings Hệ thống
            settings = SupabaseAPI.get_system_config("app_settings") or {}
            sheet_url = settings.get("sheet_url") or settings.get("google_sheet_url")
            tts_api_key = settings.get("api_key") or settings.get("everai_api_key")
            tts_voice_id = settings.get("voice_id") or settings.get("everai_voice_id", "1")
            folder_id = load_credentials().get("id_folder")

            if not sheet_url or not tts_api_key:
                raise Exception("Thiếu cấu hình Sheet URL hoặc API Key!")

            tiktok_id = acc_data.get("tiktok_id", "")
            clean_tid = tiktok_id.replace("@", "").strip()

            profile_name = "manual_shared_profile"

            self.parent.after(0, self._update_item_status, item, "📥 Đang tải TikTok...", "cyan")
            paths = download_tiktok_video(vid_url, TEMP_WORK_DIR)
            if not paths: raise Exception("Lỗi tải video TikTok.")

            # 3. Up AI Studio (Sẽ sử dụng thư mục Chrome Profile mới)
            self.parent.after(0, self._update_item_status, item, "🤖 Đang up AI Studio...", "cyan")
            acc_payload = {
                "tiktok_id": clean_tid,
                "chrome_profile": profile_name,
                "video_path": paths['ai_studio'],
                "email": acc_data.get("email"),
                "password": acc_data.get("password")
            }
            if not upload_worker(acc_payload): raise Exception("Lỗi Upload AI Studio.")
            time.sleep(10)

            # 4. Đọc Kịch bản từ Sheet
            self.parent.after(0, self._update_item_status, item, "🔎 Đang chờ AI trả Text...", "orange")
            row_data = None
            for _ in range(3):
                row_data = get_latest_row_by_id(sheet_url, clean_tid)
                if row_data: break
                time.sleep(3)
            if not row_data: raise Exception("Không tìm thấy dữ liệu trên Sheet.")

            # 5. Đọc giọng TTS
            self.parent.after(0, self._update_item_status, item, "🗣️ Đang tạo Voice...", "cyan")
            link_ct, local_content = self._handle_tts(tts_api_key, row_data["content_text"], tts_voice_id, row_data['row'], sheet_url, False)
            local_title = None
            if row_data.get("title_text"):
                _, local_title = self._handle_tts(tts_api_key, row_data["title_text"], tts_voice_id, row_data['row'], sheet_url, True)
            if not local_content: raise Exception("Lỗi tạo Voice Content.")

            # 6. Render & Edit Video
            self.parent.after(0, self._update_item_status, item, "🎬 Đang Render Edit...", "yellow")
            render_settings = channel_data.get("render_settings", {})
            assets_conf = render_settings.get("assets", {})

            t_frame_name = assets_conf.get("title_frame_filename")
            c_frame_name = assets_conf.get("content_frame_filename")
            logo_name = assets_conf.get("logo_filename")
            font_name = render_settings.get("text_overlay_settings", {}).get("font_filename")

            t_frame_path = self._download_local_asset("frame", FRAME_DIR, t_frame_name)
            c_frame_path = self._download_local_asset("frame", FRAME_DIR, c_frame_name)
            self._download_local_asset("logo", LOGO_DIR, logo_name)
            self._download_local_asset("font", FONT_DIR, font_name)

            final_path = create_video_from_source_video(
                audio_url=local_content,
                source_video_url=paths['original'],
                title_audio_url=local_title,
                title_tiktok=row_data.get("title_text", "Video Viral"),
                content_text=row_data.get("title_text", ""),
                script_url=sheet_url,
                row_index=row_data['row'],
                tiktok_id=clean_tid,
                override_config=render_settings,
                output_filename=f"manual_{clean_tid}_{int(time.time())}.mp4",
                temp_dir=TEMP_WORK_DIR,
                title_frame_path=t_frame_path,
                content_frame_path=c_frame_path,
                target_channel_url=channel_data.get("url")
            )
            if not final_path: raise Exception("Lỗi ghép Render Video.")

            self.parent.after(0, self._update_item_status, item, "☁️ Đang Up Google Drive...", "cyan")
            drv_link = upload_video_to_drive(final_path, folder_id=folder_id)
            if not drv_link: raise Exception("Lỗi Up Drive.")

            if update_final_result(sheet_url, row_data['row'], drv_link):
                self.parent.after(0, self._update_item_status, item, "✅ Hoàn tất!", "green")
                try: os.remove(final_path)
                except: pass
            else:
                raise Exception("Lỗi ghi link Drive lên Sheet.")

        except Exception as e:
            self.parent.after(0, self._update_item_status, item, f"❌ Lỗi: {str(e)}", "red")

        finally:
            self.is_processing = False
            self.parent.after(1000, self._check_queue)

    def _handle_tts(self, api_key, text, voice_id, row_idx, sheet_url, is_title):
        if not text: return None, None
        try:
            req_id = generate_voice(api_key, text, voice_id, 1.0, 1.0)
            if not req_id: return None, None
            audio_url = None
            for _ in range(60):
                time.sleep(1)
                res = check_request_status(api_key, req_id)
                if res:
                    if isinstance(res, dict) and res.get("audio_link"): audio_url = res["audio_link"]
                    elif isinstance(res, str) and res.startswith("http"): audio_url = res
                    if audio_url: break

            if audio_url:
                if sheet_url and row_idx:
                    if is_title: update_voice_links(sheet_url, row_idx, title_voice_link=audio_url, content_voice_link=None)
                    else: update_voice_links(sheet_url, row_idx, title_voice_link=None, content_voice_link=audio_url)

                local_path = os.path.join(TEMP_VOICE_DIR, f"tts_{row_idx}_{int(time.time())}_{'title' if is_title else 'content'}.mp3")
                try:
                    with open(local_path, 'wb') as f: f.write(requests.get(audio_url).content)
                    return audio_url, local_path
                except: return audio_url, None
            return None, None
        except: return None, None

    def _download_local_asset(self, folder_type, local_dir, file_name):
        if not file_name: return None
        full_path = os.path.join(local_dir, file_name)
        if not os.path.exists(full_path):
            SupabaseAPI.download_asset("assets", folder_type, local_dir, file_name)
        return full_path if os.path.exists(full_path) else None