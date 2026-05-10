import sys
import os
import time
import json
import requests
import re

# =========================================================================
# 1. THIẾT LẬP ĐƯỜNG DẪN HỆ THỐNG TRƯỚC TIÊN (Để chống lỗi ModuleNotFoundError)
# =========================================================================
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

# Đảm bảo các thư mục assets tồn tại
TEMP_VOICE_DIR = os.path.join(PROJECT_ROOT, "assets", "temp_voice")
FRAME_DIR = os.path.join(PROJECT_ROOT, "assets", "frame")
LOGO_DIR = os.path.join(PROJECT_ROOT, "assets", "logo")
FONT_DIR = os.path.join(PROJECT_ROOT, "assets", "font")
CREDENTIALS_FILE = os.path.join(PROJECT_ROOT,"config",'credentials.json')

for d in [TEMP_VOICE_DIR, FRAME_DIR, LOGO_DIR, FONT_DIR]:
    if not os.path.exists(d): os.makedirs(d)

# =========================================================================
# 2. BÂY GIỜ MỚI IMPORT CÁC MODULE NỘI BỘ
# =========================================================================
try:
    from services.tele_reporter import TeleReporter
    from core.context import AccountContext
    from modules.video_handler import download_tiktok_video, get_channel_videos
    from modules.ai_studio_uploader import upload_worker
    from modules.video_remix import create_video_from_source_video
    from modules.upload_drive import upload_video_to_drive
    from services.sheet_api import get_latest_row_by_id, update_final_result, update_voice_links
    from services.tts_api import create_voice_default, create_voice_clone, create_voice_full_pipeline
    from services.supabase_api import SupabaseAPI
except ImportError as e:
    print(f"❌ Lỗi Import thư viện: {e}")
    sys.exit(1)


def is_valid_vietnamese(text):
    if not text: return False
    vn_chars_pattern = re.compile(r'[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]', re.IGNORECASE)
    return bool(vn_chars_pattern.search(text))

def load_credentials():
    if not os.path.exists(CREDENTIALS_FILE): return {}
    try:
        with open(CREDENTIALS_FILE, "r", encoding="utf-8") as f: return json.load(f)
    except: return {}

def handle_tts_and_update_sheet(api_key, text, voice_id, row_idx, sheet_url, is_title=False, save_dir=None):
    if not text: return None, None

    label = "Tiêu đề" if is_title else "Nội dung"
    actual_save_dir = save_dir if save_dir else TEMP_VOICE_DIR
    file_name = f"tts_{row_idx}_{int(time.time())}_{'title' if is_title else 'content'}.wav"

    print(f"   🔊 Đang xử lý TTS {label} (Gọi qua VieNeu Server)...")

    try:
        local_path = create_voice_full_pipeline(
            text=text,
            save_dir=actual_save_dir,
            filename=file_name,
            profile_id="viterbox",
            rvc_model=voice_id if ".pth" in str(voice_id) else "models/my_voice.pth",
            rvc_pitch=0,
            emotion="binh_thuong"
        )

        if local_path and os.path.exists(local_path):
            print(f"   ✅ TTS Server Thành công: {local_path}")

            if sheet_url and row_idx:
                if is_title: update_voice_links(sheet_url, row_idx, title_voice_link="local_file", content_voice_link=None)
                else: update_voice_links(sheet_url, row_idx, title_voice_link=None, content_voice_link="local_file")

            return "local_file", local_path

        return None, None

    except Exception as e:
        print(f"   ❌ Lỗi tạo TTS Local: {e}", flush=True)
        return None, None

def run_worker_process(account_id):
    ctx = AccountContext(account_id)
    ctx.logger.info(f"🚀 WORKER STARTED: {account_id}")

    cfg = ctx.config
    if not cfg:
        ctx.logger.error("❌ Không lấy được config từ Supabase. Dừng worker.")
        return

    tiktok_id = cfg.get("tiktok_id")
    profile_name = cfg.get("chrome_profile")
    acc_email = cfg.get("email")
    acc_password = cfg.get("password")
    setting_folder = load_credentials()
    folder_id = setting_folder.get("id_folder")
    settings = SupabaseAPI.get_system_config("app_settings") or {}
    sheet_url = settings.get("sheet_url") or settings.get("google_sheet_url")
    tts_api_key = settings.get("api_key") or settings.get("everai_api_key")
    tts_voice_id = settings.get("voice_id") or settings.get("everai_voice_id", "1")

    if not sheet_url or not tts_api_key:
        ctx.logger.error("❌ Lỗi: Thiếu Sheet URL hoặc API Key.")
        return

    state = ctx.load_state()
    if "crawled_videos" not in state: state["crawled_videos"] = []

    processed_count = 0
    acc_limit = cfg.get("video_limit_per_run", 3)

    for channel in cfg.get("channels", []):
        if processed_count >= acc_limit:
            ctx.logger.info(f"🛑 Đã đạt giới hạn tài khoản ({acc_limit} video). Dừng quét kênh tiếp theo.")
            break

        if not channel.get("active", True): continue

        src_url = channel.get("url") or channel.get("channel_url")
        if not src_url: continue

        limit = channel.get("limit", 3)
        render_settings = channel.get("render_settings", {})
        last_crawled_url = channel.get("last_video_url", "")

        ctx.logger.info(f"🔍 Quét kênh: {src_url} (Lấy tối đa {limit} video)")

        try: all_videos = get_channel_videos(src_url, limit=15)
        except Exception as e:
            ctx.logger.error(f"   ⚠️ Lỗi quét video: {e}")
            continue

        new_videos_batch = []
        for v in all_videos:
            if v == last_crawled_url: break
            if v in state["crawled_videos"]: continue
            new_videos_batch.append(v)

        if not new_videos_batch: continue

        new_videos_batch.reverse()
        videos_to_process = new_videos_batch[:limit]

        for vid_url in videos_to_process:
            if processed_count >= acc_limit:
                ctx.logger.info(f"🛑 Đã đạt giới hạn tài khoản ({acc_limit} video). Ngừng xử lý các video còn lại trong kênh.")
                break

            ctx.logger.info(f"▶️ BẮT ĐẦU VIDEO: {vid_url}")
            try:
                paths = download_tiktok_video(vid_url, ctx.temp_dir)
                if not paths: continue

                clean_tid = tiktok_id.replace("@", "").strip()
                up_path = paths['ai_studio']

                acc_payload = {
                    "tiktok_id": clean_tid,
                    "chrome_profile": profile_name,
                    "video_path": up_path,
                    "email": acc_email,
                    "password": acc_password
                }

                if not upload_worker(acc_payload): continue
                time.sleep(10)

                row_data = None
                for _ in range(3):
                    row_data = get_latest_row_by_id(sheet_url, clean_tid)
                    if row_data: break
                    time.sleep(3)
                if not row_data: continue

                raw_content = row_data.get("content_text", "")
                raw_title = row_data.get("title_text", "")
                if not is_valid_vietnamese(raw_content) and is_valid_vietnamese(raw_title):
                    ctx.logger.error("   ❌ LỖI AI: Content trả về là tiếng Việt không dấu (hoặc bị rỗng). BỎ QUA video này!")
                    update_final_result(sheet_url, row_data['row'], "LỖI: AI TRẢ TEXT KHÔNG DẤU")
                    continue
                link_ct, local_content = handle_tts_and_update_sheet(tts_api_key, raw_content, tts_voice_id, row_data['row'], sheet_url, False, save_dir=ctx.temp_dir)
                local_title = None
                if row_data.get("title_text"):
                    _, local_title = handle_tts_and_update_sheet(tts_api_key, row_data["title_text"], tts_voice_id, row_data['row'], sheet_url, True, save_dir=ctx.temp_dir)
                
                if not local_content:
                    ctx.logger.error(f"   ⚠️ Bỏ qua video vì không tạo được Voice Content (local_content is None)")
                    continue

                ctx.logger.info("   🎬 Chuẩn bị Remixing...")

                assets_conf = render_settings.get("assets", {})

                t_frame_name = assets_conf.get("title_frame_filename")
                c_frame_name = assets_conf.get("content_frame_filename")
                logo_name = assets_conf.get("logo_filename")
                font_name = render_settings.get("text_overlay_settings", {}).get("font_filename")

                def download_if_missing(folder_type, local_dir, file_name):
                    if not file_name: return None
                    full_path = os.path.join(local_dir, file_name)
                    if not os.path.exists(full_path):
                        ctx.logger.info(f"   📥 Không có file '{file_name}'. Đang tải từ Supabase...")
                        SupabaseAPI.download_asset("assets", folder_type, local_dir, file_name)
                    else:
                        ctx.logger.info(f"   ✅ Đã có file '{file_name}' trong máy.")
                    return full_path

                title_frame_full_path = download_if_missing("frame", FRAME_DIR, t_frame_name)
                content_frame_full_path = download_if_missing("frame", FRAME_DIR, c_frame_name)
                download_if_missing("logo", LOGO_DIR, logo_name)
                download_if_missing("font", FONT_DIR, font_name)

                final_path = create_video_from_source_video(
                    audio_url=local_content,
                    source_video_url=paths['original'],
                    title_audio_url=local_title,
                    title_tiktok=row_data.get("title_text", "Video Viral"),
                    content_text=row_data.get("title_text", "Video Viral"),
                    script_url=sheet_url,
                    row_index=row_data['row'],
                    tiktok_id=clean_tid,
                    override_config=render_settings,
                    output_filename=f"final_{account_id}_{int(time.time())}.mp4",
                    temp_dir=ctx.temp_dir,
                    title_frame_path=title_frame_full_path,
                    content_frame_path=content_frame_full_path,
                    target_channel_url=src_url
                )
                if not final_path: continue

                drv_link = upload_video_to_drive(final_path, folder_id=folder_id)

                if drv_link and update_final_result(sheet_url, row_data['row'], drv_link):
                    ctx.logger.info("   ✅ HOÀN TẤT!")

                    if vid_url not in state["crawled_videos"]:
                        state["crawled_videos"].append(vid_url)
                        ctx.save_state(state)

                    try:
                        new_index = channel.get("video_index", 0) + 1
                        SupabaseAPI.update_channel_tracking(tiktok_id, src_url, vid_url, new_index)
                        ctx.logger.info(f"   ☁️ Đã cập nhật Supabase: last_video_url = {vid_url}")
                        if os.path.exists(final_path): os.remove(final_path)
                    except Exception as e:
                        ctx.logger.error(f"   ⚠️ Lỗi cập nhật lên Supabase: {e}")

                    processed_count += 1

                    try:
                        TeleReporter.log_success_video(tiktok_id, src_url)
                    except Exception as e:
                        ctx.logger.error(f"   ⚠️ Lỗi ghi nháp Telegram: {e}")

            except Exception as e:
                ctx.logger.error(f"   🔥 Lỗi: {e}")
            finally:
                ctx.cleanup_temp()
                time.sleep(5)

    ctx.logger.info(f"🏁 WORKER FINISHED. Tổng video thành công: {processed_count}/{acc_limit}")


if __name__ == "__main__":
    import sys
    args = sys.argv[1:]
    account_id = None

    for arg in args:
        arg = arg.strip()
        if not arg.startswith("--"):
            account_id = arg

    if not account_id:
        print("\n❌ LỖI: Thiếu ID tài khoản! (Ví dụ: @tai_khoan)")
    else:
        try:
            run_worker_process(account_id)
        except Exception as e:
            print(f"🔥 WORKER CRASHED: {e}")
            import traceback
            traceback.print_exc()