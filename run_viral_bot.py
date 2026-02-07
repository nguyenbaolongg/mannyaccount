import os
import sys
import json
import time
import requests
import shutil
# ================= CẤU HÌNH ĐƯỜNG DẪN =================
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.append(PROJECT_ROOT)

# Import Modules xử lý
from modules.video_handler import get_channel_videos, download_tiktok_video
from modules.video_remix import create_video_from_source_video
from modules.upload_drive import upload_video_to_drive

# [QUAN TRỌNG] Import từ services/tts_api.py (File chứa logic EverAI bạn đã cung cấp)
from services.tts_api import generate_voice, check_request_status

# [QUAN TRỌNG] Import từ services/sheet_api.py (Để tránh lỗi Import vòng tròn)
from services.sheet_api import (
    get_data_from_sheet,
    save_audio_link_to_sheet,
    save_title_audio_to_sheet,
    get_last_row_index
)

# Các file config
RENDER_CONFIG_FILE = os.path.join(PROJECT_ROOT, "config", "render_config.json")
TRACKING_FILE = os.path.join(PROJECT_ROOT, "config", "channels_tracking.json")
USER_SETTINGS_FILE = os.path.join(PROJECT_ROOT, "user_settings.json")

# Thư mục tạm lưu voice (Giữ nguyên như code cũ của bạn)
TEMP_VOICE_DIR = os.path.join(PROJECT_ROOT, "assets", "temp_voice")
if not os.path.exists(TEMP_VOICE_DIR): os.makedirs(TEMP_VOICE_DIR)
TEMP_DOWNLOADS_DIR = os.path.join(PROJECT_ROOT, "assets", "temp_downloads")
# ID Folder Drive cố định (hoặc lấy từ config nếu muốn)
FOLDER_ID = "1VgkkbUJ82kxzWXJH8cfn7UFMMFBKQkzS"

# [MỚI] Hàm đọc cấu hình trực tiếp từ file (để lấy Sheet URL/API Key mới nhất)
def load_live_settings():
    if not os.path.exists(USER_SETTINGS_FILE): return {}
    try:
        with open(USER_SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except: return {}
SHEET_URL = load_live_settings().get("sheet_url")
# ================= HÀM HỖ TRỢ =================

def get_best_render_config(source_channel_url, target_tiktok_id=None):
    """Tìm cấu hình render phù hợp nhất"""
    if not os.path.exists(RENDER_CONFIG_FILE): return None
    try:
        with open(RENDER_CONFIG_FILE, "r", encoding="utf-8") as f:
            configs = json.load(f)

        if target_tiktok_id:
            for cfg in configs:
                if cfg.get("channel_url") == source_channel_url and cfg.get("tiktok_id") == target_tiktok_id:
                    print(f"   ✨ Dùng cấu hình RIÊNG cho {target_tiktok_id}")
                    return cfg

        for cfg in configs:
            if cfg.get("channel_url") == source_channel_url and not cfg.get("tiktok_id"):
                return cfg

        for cfg in configs:
            if cfg.get("channel_url") == source_channel_url:
                return cfg
    except: pass
    return None

def update_channel_last_video(channel_url, video_url):
    """Cập nhật tracking video"""
    if os.path.exists(TRACKING_FILE):
        try:
            with open(TRACKING_FILE, "r", encoding="utf-8") as f: data = json.load(f)
            channels = data if isinstance(data, list) else data.get("channels", [])
            for ch in channels:
                if ch.get("channel_url") == channel_url:
                    ch["last_video_url"] = video_url
                    break
            with open(TRACKING_FILE, "w", encoding="utf-8") as f:
                json.dump({"channels": channels}, f, indent=4)
        except: pass

def update_sheet_full_status(sheet_url, row_idx, drive_link, tiktok_id, status="Chưa đăng"):
    """
    [CHỨC NĂNG CŨ + MỚI]
    Cập nhật Link Drive (cũ) VÀ thêm TikTok ID + Status (mới)
    """
    payload = {
        "action": "update_file_path",
        "row": row_idx,
        "file_path": drive_link,
        "tiktok_id": tiktok_id,
        "status": status
    }
    try:
        requests.post(sheet_url, json=payload, timeout=10)
        print(f"   📝 Đã cập nhật Sheet: Link Drive + Status='{status}'")
        return True
    except Exception as e:
        print(f"   ❌ Lỗi cập nhật Sheet: {e}")
        return False

def handle_tts_process(api_key, text, voice_id, prefix, row_idx):
    """
    [CHỨC NĂNG CŨ] Tạo Voice -> Tải về máy -> Trả về Link & Path
    Đã tích hợp load api_key động.
    """
    if not text: return None, None
    print(f"   🔊 Creating Voice ({prefix})...")

    try:
        # Gọi hàm từ services/tts_api.py (Code EverAI)
        req_id = generate_voice(api_key, text, voice_id, 1.1, 1.0)

        if req_id:
            for _ in range(60):
                time.sleep(1)
                # Gọi hàm check từ services/tts_api.py
                res = check_request_status(api_key, req_id)

                if res and res.get("audio_link"):
                    audio_url = res["audio_link"]

                    # [CHỨC NĂNG CŨ] Tải file về máy
                    local_filename = f"{prefix}_{row_idx}_{int(time.time())}.mp3"
                    local_path = os.path.join(TEMP_VOICE_DIR, local_filename)

                    try:
                        audio_content = requests.get(audio_url).content
                        with open(local_path, 'wb') as f:
                            f.write(audio_content)
                        return audio_url, local_path # Trả về cả 2
                    except Exception as e:
                        print(f"   ⚠️ Lỗi tải file mp3: {e}")
                        return audio_url, None

        print(f"   ❌ TTS Timeout: Không tạo được voice cho {prefix}")

    except Exception as e:
        print(f"   ❌ Lỗi xử lý TTS: {e}")

    return None, None

def clean_temp_downloads():
    print("   🧹 Đang dọn dẹp thư mục tải về tạm thời...")
    if os.path.exists(TEMP_DOWNLOADS_DIR):
        try:
            # Xóa tất cả các file trong folder
            for filename in os.listdir(TEMP_DOWNLOADS_DIR):
                file_path = os.path.join(TEMP_DOWNLOADS_DIR, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    print(f"   ⚠️ Không xóa được {file_path}: {e}")
            print("   ✅ Đã xóa sạch folder temp_downloads.")
        except Exception as e:
            print(f"   ❌ Lỗi dọn dẹp: {e}")


# ================= CORE LOGIC (Process Row) =================
# Hàm này thay thế cho vòng lặp trong code cũ, được Scheduler gọi tới

def process_viral_row(row_idx, local_video_path, current_channel_link, current_tiktok_id=None):
    # 1. Load Settings (Để lấy URL Sheet/API Key mới nhất)
    settings = load_live_settings()
    sheet_url = settings.get("sheet_url", "")
    api_key = settings.get("api_key", "")
    voice_id = settings.get("voice_id", "vi_female_kieunhi_mn")

    if not sheet_url or not api_key:
        print("   ❌ Lỗi: Thiếu Sheet URL hoặc API Key.")
        return False

    print(f"\n⚙️ [PROCESS] Đang hậu kỳ dòng {row_idx} | User: {current_tiktok_id}")

    try:
        # 2. Đọc Sheet (Lấy kịch bản)
        resp = requests.post(sheet_url, json={"action": "read", "row": row_idx}).json()
        script_title = resp.get("title_text", "")
        script_content = resp.get("content_text", "")

        if not script_content:
            print("   ⚠️ Chưa có nội dung kịch bản.")
            return False

        # 3. Tạo TTS (Giữ nguyên logic cũ: tạo và tải về)
        t_link, t_path = handle_tts_process(api_key, script_title, voice_id, "Title", row_idx)
        c_link, c_path = handle_tts_process(api_key, script_content, voice_id, "Content", row_idx)

        # Kiểm tra an toàn
        if not c_link and not c_path:
            print("   ⛔ DỪNG: Lỗi tạo giọng đọc nội dung.")
            return False

        final_t_source = t_path if t_path else t_link
        final_c_source = c_path if c_path else c_link

        # [CHỨC NĂNG CŨ] Lưu Link Voice lên Sheet
        if t_link: save_title_audio_to_sheet(sheet_url, row_idx, t_link)
        if c_link: save_audio_link_to_sheet(sheet_url, row_idx, c_link)

        # 4. Render Video (Edit)
        print("   🎬 Rendering Video...")
        output_name = f"viral_{current_tiktok_id}_{row_idx}.mp4" if current_tiktok_id else f"viral_{row_idx}.mp4"

        final_video_path = create_video_from_source_video(
            audio_url=final_c_source,
            source_video_url=local_video_path,
            title_audio_url=final_t_source,
            title_tiktok=script_title,
            content_text=script_title,
            target_channel_url=current_channel_link,
            output_filename=output_name,
            tiktok_id=current_tiktok_id
        )

        # 5. Upload Drive & Update Sheet
        if final_video_path and os.path.exists(final_video_path):
            print(f"   ☁️ Uploading {output_name} to Drive...")

            # [CHỨC NĂNG CŨ] Upload lên Drive
            drive_link = upload_video_to_drive(final_video_path, FOLDER_ID)

            if drive_link:
                print(f"   ✅ Upload Drive thành công: {drive_link}")

                # [CHỨC NĂNG CŨ + MỚI] Update Sheet (Link Drive + Status)
                update_sheet_full_status(sheet_url, row_idx, drive_link, current_tiktok_id, status="Chưa đăng")

                # Dọn dẹp
                try: os.remove(final_video_path)
                except: pass
                try:
                    if t_path: os.remove(t_path)
                    if c_path: os.remove(c_path)
                except: pass
                clean_temp_downloads()
                return True
            else:
                print("   ❌ Lỗi: Không lấy được Link Drive.")
        else:
            print("   ❌ Lỗi: Render thất bại (Không thấy file output).")

    except Exception as e:
        print(f"   ❌ Lỗi quy trình hậu kỳ: {e}")
        import traceback; traceback.print_exc()

    return False

# Không cần main_loop vì Scheduler sẽ lo việc lặp
if __name__ == "__main__":
    print("Vui lòng chạy file scheduler_manager.py để khởi động hệ thống.")