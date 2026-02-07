import sys
import os
import time
import json
import requests
import random
import shutil # <--- [QUAN TRỌNG] Thêm thư viện để copy file

# ================= CẤU HÌNH ĐƯỜNG DẪN =================
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USER_SETTINGS_FILE = os.path.join(PROJECT_ROOT, "user_settings.json")
TEMP_VOICE_DIR = os.path.join(PROJECT_ROOT, "assets", "temp_voice")
CREDENTIALS_FILE = os.path.join(PROJECT_ROOT,"config",'credentials.json')
# Tạo thư mục lưu voice nếu chưa có
if not os.path.exists(TEMP_VOICE_DIR): os.makedirs(TEMP_VOICE_DIR)

# Thêm đường dẫn để import modules
sys.path.append(PROJECT_ROOT)

# Import các module cần thiết
from core.context import AccountContext
from modules.video_handler import download_tiktok_video, get_channel_videos
from modules.ai_studio_uploader import run_ai_studio_uploader
from modules.video_remix import create_video_from_source_video
from modules.upload_drive import upload_video_to_drive
from services.sheet_api import get_latest_row_by_id, update_final_result, update_voice_links
from services.tts_api import generate_voice, check_request_status

# ================= HÀM HỖ TRỢ =================

def load_user_settings():
    """Đọc file user_settings.json"""
    if not os.path.exists(USER_SETTINGS_FILE): return {}
    try:
        with open(USER_SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except: return {}

def load_credentials():
    """Đọc file user_settings.json"""
    if not os.path.exists(CREDENTIALS_FILE): return {}
    try:
        with open(USER_SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except: return {}

def handle_tts_and_update_sheet(api_key, text, voice_id, row_idx, sheet_url, is_title=False):
    """
    Quy trình TTS chuẩn:
    1. Tạo Voice
    2. Có link -> Up ngay lên Sheet
    3. Tải file về máy -> Trả về đường dẫn để Edit
    """
    if not text: return None, None

    label = "Tiêu đề" if is_title else "Nội dung"
    print(f"   🔊 Đang tạo Voice {label}...")

    try:
        # 1. Gửi yêu cầu tạo Voice
        req_id = generate_voice(api_key, text, voice_id, 1.0, 1.0)

        if not req_id:
            print("   ❌ Lỗi: Không gọi được API TTS.")
            return None, None

        # 2. Chờ kết quả (Polling)
        audio_url = None
        for _ in range(60): # Chờ tối đa 60s
            time.sleep(1)
            res = check_request_status(api_key, req_id)

            # Xử lý kết quả trả về
            if res:
                if isinstance(res, dict) and res.get("audio_link"):
                    audio_url = res["audio_link"]
                elif isinstance(res, str) and res.startswith("http"):
                    audio_url = res

                if audio_url: break

        if audio_url:
            print(f"   ✅ TTS Thành công: {audio_url}")

            # 3. UP LINK VOICE LÊN SHEET NGAY LẬP TỨC
            if sheet_url and row_idx:
                print(f"   ☁️ Đang cập nhật Link {label} lên Sheet...")
                if is_title:
                    update_voice_links(sheet_url, row_idx, title_voice_link=audio_url, content_voice_link=None)
                else:
                    update_voice_links(sheet_url, row_idx, title_voice_link=None, content_voice_link=audio_url)

            # 4. Tải file về máy để Remix
            local_filename = f"tts_{row_idx}_{int(time.time())}_{'title' if is_title else 'content'}.mp3"
            local_path = os.path.join(TEMP_VOICE_DIR, local_filename)

            try:
                content = requests.get(audio_url).content
                with open(local_path, 'wb') as f:
                    f.write(content)
                return audio_url, local_path
            except Exception as e:
                print(f"   ⚠️ Lỗi tải file mp3: {e}")
                return audio_url, None
        else:
            print("   ❌ Timeout: TTS không trả về link.")
            return None, None

    except Exception as e:
        print(f"   🔥 Lỗi TTS Exception: {e}")
        return None, None

# ================= WORKER CHÍNH (LOGIC CUỐN CHIẾU) =================

def run_worker_process(account_id):
    # --- 1. KHỞI TẠO ---
    ctx = AccountContext(account_id)
    ctx.logger.info("🚀 WORKER STARTED: Chế độ Cuốn Chiếu (Sequential Blocking)")

    cfg = ctx.config
    tiktok_id = cfg.get("tiktok_id")
    profile_name = cfg.get("chrome_profile")

    setting_folder = load_credentials()
    folder_id = setting_folder.get("id_folder")

    # Load Settings
    settings = load_user_settings()
    sheet_url = settings.get("sheet_url") or settings.get("google_sheet_url")
    tts_api_key = settings.get("api_key") or settings.get("everai_api_key")
    tts_voice_id = settings.get("voice_id") or settings.get("everai_voice_id", "1")

    # Validate Config
    if not sheet_url:
        ctx.logger.error("❌ Lỗi: Thiếu Sheet URL.")
        return
    if not tts_api_key:
        ctx.logger.error("❌ Lỗi: Thiếu TTS API Key.")
        return

    state = ctx.load_state()
    history = state.get("crawled_videos", [])
    processed_count = 0

    # --- 2. QUÉT VIDEO ---
    for channel in cfg.get("channels", []):
        src_url = channel.get("url")
        limit = channel.get("limit", 2)
        render_settings = channel.get("render_settings", {})

        ctx.logger.info(f"🔍 Quét kênh: {src_url}")
        videos = get_channel_videos(src_url, limit=5)

        # Lọc video chưa làm
        new_videos = [v for v in videos if v not in history]

        # --- 3. XỬ LÝ TỪNG VIDEO (LOOP CHÍNH) ---
        for vid_url in new_videos[:limit]:
            ctx.logger.info(f"▶️ BẮT ĐẦU VIDEO: {vid_url}")

            # ======================================================
            # BƯỚC 1: TẢI VIDEO GỐC
            # ======================================================
            paths = download_tiktok_video(vid_url, ctx.temp_dir)
            if not paths:
                ctx.logger.error("   ❌ Tải video thất bại. Bỏ qua.")
                continue

            # ======================================================
            # BƯỚC 2: UPLOAD AI STUDIO (ĐÃ FIX LỖI WinError 32)
            # ======================================================
            ctx.logger.info("   📤 Uploading to AI Studio...")
            tiktok_id = tiktok_id.replace("@", "").strip()

            # --- [FIX QUAN TRỌNG] TẠO BẢN COPY ĐỂ UPLOAD ---
            # Nguyên nhân: Chrome giữ file gốc nên bước Remix không mở được.
            # Giải pháp: Copy ra 1 bản để Upload, file gốc giữ nguyên để Remix.
            upload_video_path = paths['ai_studio']
            try:
                # Tạo tên file: video.mp4 -> video_upload_copy.mp4
                copy_path = upload_video_path.replace(".mp4", "_upload_copy.mp4")
                shutil.copy2(upload_video_path, copy_path)
                upload_video_path = copy_path # Trỏ sang dùng file copy
                ctx.logger.info(f"   blob: Đã tạo bản sao để upload: {os.path.basename(copy_path)}")
            except Exception as e:
                ctx.logger.warning(f"   ⚠️ Không thể copy file (sẽ dùng file gốc): {e}")

            # Upload bằng file copy
            upload_success = run_ai_studio_uploader(
                local_video_path=upload_video_path,
                specific_profile_name=profile_name,
                tiktok_id=tiktok_id
            )

            # Nếu upload thất bại -> Dừng video này, qua video kế
            if not upload_success:
                ctx.logger.error("   ❌ Upload AI Studio thất bại (False). Bỏ qua video này.")
                continue

            # ======================================================
            # BƯỚC 3: CHỜ 10S & LẤY TEXT TỪ SHEET
            # ======================================================
            ctx.logger.info("   ⏳ Upload thành công. Chờ 10s để hệ thống cập nhật Text...")
            time.sleep(10) # Ngủ cứng 10s theo yêu cầu

            ctx.logger.info("   📥 Đang lấy Text từ Sheet (Dòng mới nhất)...")

            # Thử lấy dữ liệu (Retry 3 lần)
            row_data = None
            for _ in range(3):
                row_data = get_latest_row_by_id(sheet_url, tiktok_id)
                if row_data: break
                time.sleep(3)

            if not row_data:
                ctx.logger.error("   ❌ Không tìm thấy Text trên Sheet. (Có thể AI Studio chưa kịp ghi). Bỏ qua.")
                continue

            ctx.logger.info(f"   ✅ Đã lấy được Text (Dòng {row_data['row']})")

            # ======================================================
            # BƯỚC 4: TẠO VOICE & UP LINK VOICE LÊN SHEET
            # ======================================================
            ctx.logger.info("   🗣️ Tạo Voice & Update Sheet...")

            # A. Voice Nội dung (Content)
            link_content, local_content = handle_tts_and_update_sheet(
                tts_api_key, row_data["content_text"], tts_voice_id,
                row_data['row'], sheet_url, is_title=False
            )

            # B. Voice Tiêu đề (Title)
            link_title, local_title = None, None
            if row_data.get("title_text"):
                link_title, local_title = handle_tts_and_update_sheet(
                    tts_api_key, row_data["title_text"], tts_voice_id,
                    row_data['row'], sheet_url, is_title=True
                )

            # Bắt buộc phải có Voice nội dung mới Edit được
            if not local_content:
                ctx.logger.error("   ❌ Lỗi tạo Voice nội dung. Bỏ qua.")
                continue

            # ======================================================
            # BƯỚC 5: EDIT (REMIX) VIDEO - ĐÃ CẬP NHẬT ĐỦ THAM SỐ
            # ======================================================
            ctx.logger.info("   🎬 Remixing Video...")
            output_filename = f"final_{int(time.time())}.mp4"

            # Gọi hàm remix với đầy đủ tham số
            final_path = create_video_from_source_video(
                # 1. Các file input
                audio_url=local_content,            # File voice nội dung (local path)
                source_video_url=paths['original'], # File video gốc (không phải file copy)
                title_audio_url=local_title,        # File voice tiêu đề (local path)

                # 2. Thông tin Text/Nội dung
                title_tiktok=row_data.get("title_text", "Video Viral"),
                content_text=row_data.get("title_text", ""),

                # 3. Thông tin quản lý (CÁC THAM SỐ QUAN TRỌNG)
                script_url=sheet_url,       # Để ghi log
                row_index=row_data['row'],  # Để biết dòng nào
                tiktok_id=tiktok_id,        # ID người dùng

                # 4. Cấu hình output
                override_config=render_settings,
                output_filename=output_filename,
                temp_dir=ctx.temp_dir
            )

            if not final_path or not os.path.exists(final_path):
                ctx.logger.error("   ❌ Lỗi Remix Video. Bỏ qua.")
                continue

            # ======================================================
            # BƯỚC 6: UPLOAD DRIVE & UPDATE LINK VIDEO
            # ======================================================
            ctx.logger.info("   ☁️ Uploading Final Video to Drive...")
            drive_link = upload_video_to_drive(final_path,folder_id = folder_id)

            if drive_link:
                # Cập nhật link video vào cột J (File Path) và set trạng thái
                update_success = update_final_result(sheet_url, row_data['row'], drive_link)

                if update_success:
                    ctx.logger.info("   ✅ HOÀN TẤT VIDEO NÀY! (Đã cập nhật Sheet)")

                    # Chỉ khi mọi thứ thành công mới lưu vào lịch sử
                    state["crawled_videos"].append(vid_url)
                    ctx.save_state(state)
                    processed_count += 1
                else:
                    ctx.logger.error("   ⚠️ Lỗi update link video lên Sheet.")
            else:
                ctx.logger.error("   ❌ Lỗi Upload Drive.")

            # ======================================================
            # DỌN DẸP & QUA VIDEO B
            # ======================================================
            ctx.cleanup_temp()
            ctx.logger.info("   🏁 Nghỉ 5s trước khi qua Video tiếp theo...")
            time.sleep(5)

    ctx.logger.info(f"🏁 WORKER FINISHED. Tổng video thành công: {processed_count}")


# ================= HÀM TEST RIÊNG (CHỈ TEST TTS) =================

def test_tts_flow(account_id):
    print(f"\n🧪 --- TEST CHẾ ĐỘ: LẤY TEXT SHEET & TẠO VOICE ---")
    print(f"📌 Account ID: {account_id}")

    # 1. Load Cấu hình
    ctx = AccountContext(account_id)
    tiktok_id = ctx.config.get("tiktok_id")

    settings = load_user_settings()
    sheet_url = settings.get("sheet_url") or settings.get("google_sheet_url")
    tts_api_key = settings.get("api_key") or settings.get("everai_api_key")
    tts_voice_id = settings.get("voice_id") or settings.get("everai_voice_id", "1")
    if not sheet_url or not tts_api_key:
        print("❌ Lỗi: Thiếu Sheet URL hoặc API Key trong user_settings.json")
        return

    print(f"🔎 Đang tìm dữ liệu trên Sheet cho ID: {tiktok_id}")
    print(f"   (Lưu ý: Sheet phải có dòng chứa ID này và cột Content Text phải có chữ)")

    # 2. Lấy dữ liệu từ Sheet
    row_data = get_latest_row_by_id(sheet_url, tiktok_id)
    print(row_data)
    if not row_data:
        print("❌ KHÔNG TÌM THẤY DỮ LIỆU KHỚP!")
        print("   👉 Hãy kiểm tra lại cột N (TikTok ID) trong Sheet xem có đúng ID chưa.")
        print("   👉 Hãy kiểm tra lại cột C (Content Text) xem đã có nội dung chưa.")
        return

    print(f"✅ TÌM THẤY DỮ LIỆU (Dòng {row_data['row']})")
    print(f"   📝 Title: {row_data.get('title_text', '')[:30]}...")
    print(f"   📝 Content: {row_data.get('content_text', '')[:30]}...")
    print("-" * 50)

    # 3. Test tạo Voice Nội dung
    print("🗣️ Đang test tạo Voice NỘI DUNG...")
    link, path = handle_tts_and_update_sheet(
        tts_api_key,
        row_data["content_text"],
        tts_voice_id,
        row_data['row'],
        sheet_url,
        is_title=False
    )

    if path:
        print(f"   ✅ Content Voice OK!")
        print(f"      🔗 Link: {link}")
        print(f"      📂 File: {path}")
    else:
        print("   ❌ Lỗi tạo Content Voice")

    # 4. Test tạo Voice Tiêu đề (nếu có)
    if row_data.get("title_text"):
        print("\n🗣️ Đang test tạo Voice TIÊU ĐỀ...")
        link_t, path_t = handle_tts_and_update_sheet(
            tts_api_key,
            row_data["title_text"],
            tts_voice_id,
            row_data['row'],
            sheet_url,
            is_title=True
        )
        if path_t:
            print(f"   ✅ Title Voice OK!")
        else:
            print("   ❌ Lỗi tạo Title Voice")

    print("\n🏁 HOÀN TẤT TEST TTS.")

if __name__ == "__main__":
    # --- BỘ XỬ LÝ THAM SỐ THÔNG MINH ---
    import sys

    # 1. Lấy danh sách tham số (bỏ tên file script ở đầu)
    args = sys.argv[1:]

    account_id = None
    is_test_mode = False

    # 2. Duyệt qua từng tham số để nhận diện
    for arg in args:
        arg = arg.strip()
        if arg == "--test-tts":
            is_test_mode = True
        elif not arg.startswith("--"):
            # Nếu không bắt đầu bằng -- thì nó là Account ID
            account_id = arg

    # 3. Thực thi
    if not account_id:
        print("\n❌ LỖI: Thiếu ID tài khoản!")
        print("   👉 Cách dùng đúng: python core/worker.py @ten_tai_khoan --test-tts")
    else:
        if is_test_mode:
            # Chạy chế độ Test TTS
            test_tts_flow(account_id)
        else:
            # Chạy Worker bình thường
            run_worker_process(account_id)