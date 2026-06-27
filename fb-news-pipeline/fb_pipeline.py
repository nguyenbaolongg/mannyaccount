#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════
  Facebook News Auto Remix — Pipeline chính

  FLOW:
  1. Cào 10 video (reels) từ Facebook page
  2. Lọc video mới (so sánh last_video_id)
  3. Với mỗi video mới:
     a. Download video
     b. Gửi video + caption cho ChatGPT → nhận JSON
     c. Ghi JSON lên Google Sheet (hook→B+E, script_voice→C, title→I)
     d. Tạo voice hook (cột E)
     e. Nếu CÓ FRAME → tạo thêm voice script (cột C) → edit giống TikTok
        Nếu KHÔNG FRAME → hook intro (mute+voice) + body (audio gốc) + logo xuyên suốt
     f. Cập nhật last_video_id
═══════════════════════════════════════════════════════
"""

import os
import sys
import time
import json
import shutil
import uuid
import subprocess
from datetime import datetime, timezone

# Thêm project chính vào path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# Import từ project chính
from services.supabase_api import supabase
from services.tts_api import create_voice_full_pipeline

# Import từ fb-news-pipeline
from fb_crawler import crawl_facebook_videos
from fb_downloader import download_video
from chatgpt_automator import analyze_video_with_chatgpt
from fb_sheet_api import save_fb_to_sheet, update_fb_voice_link, update_fb_drive_link, update_fb_status

TEMP_DIR = os.path.join(os.path.dirname(__file__), "temp")
APP_DIR = os.path.dirname(os.path.abspath(__file__))

# Đọc config từ .env
def _env(key, default=""):
    env_path = os.path.join(APP_DIR, ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith(key + "="):
                    return line.split("=", 1)[1].strip()
VOICE_PROFILE_ID = _env("VOICEBOX_PROFILE_ID", "cb6f4c6a-2617-4eeb-a148-909f0084d8c8")
GDRIVE_FOLDER_ID = _env("DRIVE_FOLDER_ID", _env("GDRIVE_FOLDER_ID", "1VgkkbUJ82kxzWXJH8cfn7UFMMFBKQkzS"))

# Logo/frame paths
LOGO_PATH = os.path.join(APP_DIR, "assets", "logo.png")
FRAME_PATH = os.path.join(APP_DIR, "assets", "frame.png")


def _get_duration(file_path: str) -> float:
    """Lấy duration file media bằng ffprobe"""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "csv=p=0", file_path],
            capture_output=True, text=True, timeout=10
        )
        return float(result.stdout.strip())
    except:
        return 0.0

def _is_horizontal(file_path: str) -> bool:
    """Kiểm tra xem video có phải là video ngang không (width > height)"""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-select_streams", "v:0", 
             "-show_entries", "stream=width,height", "-of", "csv=s=x:p=0", file_path],
            capture_output=True, text=True, timeout=10
        )
        w, h = map(int, result.stdout.strip().split('x'))
        return w > h
    except:
        return False


class FBNewsPipeline:
    def __init__(self):
        os.makedirs(TEMP_DIR, exist_ok=True)
        self.stats = {"scanned": 0, "new": 0, "completed": 0, "failed": 0}

    # ═══════════════════════════════════════════════════
    #  CHẠY PIPELINE 1 LẦN
    # ═══════════════════════════════════════════════════
    def run(self):
        self.stats = {"scanned": 0, "new": 0, "completed": 0, "failed": 0}

        print("═" * 55)
        print("  🚀 BẮT ĐẦU PIPELINE FACEBOOK NEWS")
        print("═" * 55)

        sources = self._get_active_sources()
        print(f"📋 {len(sources)} nguồn Facebook active")

        if not sources:
            print("💤 Chưa có nguồn nào. Thêm trên giao diện.")
            return

        for source in sources:
            try:
                self._process_source(source)
            except Exception as e:
                print(f"🔥 Lỗi nguồn {source.get('source_name')}: {e}")

        print()
        print("═" * 55)
        s = self.stats
        print(f"📊 KẾT QUẢ: {s['scanned']} nguồn | {s['new']} mới | {s['completed']} xong | {s['failed']} lỗi")
        print("═" * 55)

    # ═══════════════════════════════════════════════════
    #  XỬ LÝ 1 NGUỒN
    # ═══════════════════════════════════════════════════
    def _process_source(self, source: dict):
        name = source.get("source_name", "")
        url = source.get("source_url", "")
        last_vid = source.get("last_video_id")

        print(f"\n📡 ── {name} ──")
        print(f"   URL: {url}")
        print(f"   Last video: {last_vid or '(chưa có)'}")
        self.stats["scanned"] += 1

        # BƯỚC 1: Cào 10 video đầu
        all_videos = crawl_facebook_videos(url, max_videos=10)

        if not all_videos:
            print("   💤 Không cào được video nào.")
            self._update_scan_time(source["id"])
            return

        # BƯỚC 2: Lọc video mới
        new_videos = []
        if not last_vid:
            print(f"   📌 Lần đầu quét — lấy tất cả {len(all_videos)} video")
            new_videos = all_videos
        else:
            for v in all_videos:
                if v["video_id"] == last_vid:
                    print(f"   📌 Gặp last_video_id [{last_vid}] → dừng")
                    break
                new_videos.append(v)

        if not new_videos:
            print("   💤 Không có video mới.")
            self._update_scan_time(source["id"])
            return

        print(f"   ✨ {len(new_videos)} video MỚI")
        self.stats["new"] += len(new_videos)

        # BƯỚC 3: Xử lý từng video
        latest_done_id = None

        for i, video in enumerate(new_videos, 1):
            print(f"\n   ▶️ Video {i}/{len(new_videos)}: [{video['video_id']}]")
            print(f"      Caption: {video['caption'][:80]}...")

            result = self._process_one_video(video, source)

            if result == True:
                self.stats["completed"] += 1
                if not latest_done_id:
                    latest_done_id = video["video_id"]
            else:
                self.stats["failed"] += 1

        # BƯỚC 4: Cập nhật last_video_id
        self._update_scan_time(source["id"], latest_done_id)
        if latest_done_id:
            print(f"   ☁️ last_video_id = {latest_done_id}")

    # ═══════════════════════════════════════════════════
    #  XỬ LÝ 1 VIDEO
    # ═══════════════════════════════════════════════════
    def _process_one_video(self, video: dict, source: dict, on_success=None) -> bool:
        job_id = uuid.uuid4().hex[:8]
        work_dir = os.path.join(TEMP_DIR, f"job_{job_id}")
        os.makedirs(work_dir, exist_ok=True)

        try:
            caption = video.get("caption", "").strip()

            # ── [1/6] Download video ──
            print(f"      📥 [1/6] Download...")
            dl = download_video(video["url"], video["video_id"])
            if not dl:
                raise Exception("Download thất bại")

            if self._check_hash_exists(dl["hash"]):
                print(f"      ⏭️ Trùng file hash → skip")
                return "duplicate"

            # Ghi đè caption từ crawler (thường là "34K") bằng title xịn từ yt-dlp
            if dl.get("title") and len(dl["title"]) > 5:
                real_title = dl["title"]
                parts = real_title.split(" | ")
                if len(parts) >= 2 and ("views" in parts[0].lower() or "lượt xem" in parts[0].lower()):
                    caption = parts[1].strip()
                elif len(parts) >= 1:
                    caption = parts[0].strip()
                else:
                    caption = real_title
                print(f"      📝 Tìm thấy Caption xịn: \"{caption[:60]}...\"")

            # ── [2/6] ChatGPT phân tích ──
            print(f"      🤖 [2/6] ChatGPT phân tích video...")
            ai_result = analyze_video_with_chatgpt(dl["path"], caption)

            if not ai_result:
                print(f"      ℹ️ AI không khả dụng — dùng caption gốc")
                ai_result = {
                    "title_tiktok": caption[:100],
                    "hook": caption[:80],
                    "script_voice": caption[:200],
                    "main_idea": caption[:150],
                    "have_frame": False,
                    "scenes": [],
                }

            hook = ai_result.get("hook", "")
            script_voice = ai_result.get("script_voice", "")
            title = ai_result.get("title_tiktok", "")
            have_frame = ai_result.get("have_frame", False)

            print(f"      📋 have_frame = {have_frame}")

            # ── [3/6] Tạo voice ──
            # Luôn tạo voice cho hook (cột E)
            print(f"      🗣️ [3/6] Tạo voice hook: \"{hook[:50]}...\"")
            hook_voice_path = None
            script_voice_path = None

            if hook:
                try:
                    hook_voice_path = create_voice_full_pipeline(
                        text=hook, save_dir=work_dir,
                        filename=f"hook_{job_id}.wav",
                        profile_id=VOICE_PROFILE_ID,
                    )
                    if hook_voice_path and os.path.exists(hook_voice_path):
                        print(f"      ✅ Hook voice OK: {os.path.getsize(hook_voice_path) / 1024:.0f}KB")
                    else:
                        hook_voice_path = None
                except Exception as e:
                    print(f"      ⚠️ Hook voice lỗi: {e}")

            # Nếu CÓ FRAME → tạo voice gộp cả hook và script_voice để thay thế hoàn toàn audio gốc
            # Nếu KHÔNG FRAME → không cần script_voice, chỉ dùng voice hook và audio gốc
            if have_frame and script_voice:
                full_text = f"{hook}. {script_voice}" if hook else script_voice
                print(f"      🗣️ Tạo voice script (cột C): \"{full_text[:50]}...\"")
                try:
                    script_voice_path = create_voice_full_pipeline(
                        text=full_text, save_dir=work_dir,
                        filename=f"script_{job_id}.wav",
                        profile_id=VOICE_PROFILE_ID,
                    )
                    if script_voice_path and os.path.exists(script_voice_path):
                        print(f"      ✅ Script voice OK: {os.path.getsize(script_voice_path) / 1024:.0f}KB")
                    else:
                        script_voice_path = None
                except Exception as e:
                    print(f"      ⚠️ Script voice lỗi: {e}")

            # ── [4/6] Dựng video ──
            mode_name = "CÓ FRAME" if have_frame else "KHÔNG FRAME"
            print(f"      🎬 [4/6] Dựng video (mode: {mode_name})...")

            if have_frame:
                final_path = self._edit_video_with_frame(
                    source_video=dl["path"],
                    hook_voice_path=hook_voice_path,
                    script_voice_path=script_voice_path,
                    title=title, hook_text=hook,
                    work_dir=work_dir, job_id=job_id,
                    source=source,
                )
            else:
                final_path = self._edit_video_no_frame(
                    source_video=dl["path"],
                    hook_voice_path=hook_voice_path,
                    hook_text=hook or title,
                    work_dir=work_dir, job_id=job_id,
                    source=source,
                )

            # ── [5/6] Upload Google Drive ──
            drive_link = None
            if final_path and os.path.exists(final_path):
                print(f"      ☁️ [5/6] Đang upload video lên Google Drive...")
                from modules.upload_drive import upload_video_to_drive
                drive_link = upload_video_to_drive(final_path, GDRIVE_FOLDER_ID)

            if not drive_link:
                raise Exception("Upload video lên Google Drive thất bại hoặc link trống.")

            # ── [6/6] Ghi dữ liệu khi đã hoàn tất mọi bước thành công ──
            print(f"      📊 [6/6] Lưu kết quả lên Google Sheet & Database...")
            
            # 1. Lưu Google Sheet
            sheet_result = save_fb_to_sheet(
                ai_result=ai_result,
                video_url=video["url"],
                source_name=source.get("source_name", ""),
                id_tiktok=source.get("id_tiktok", source.get("source_name", "")),
            )
            sheet_row = sheet_result.get("row") if sheet_result else None
            
            if sheet_row:
                update_fb_status(sheet_row, "completed")
                # Cập nhật link Drive vào cột J (cột 10)
                update_fb_drive_link(sheet_row, drive_link)
                print(f"      ✅ Đã đẩy link Drive vào Google Sheet dòng {sheet_row}")

            # 2. Lưu Supabase
            record_id = self._insert_video_record(source.get("id"), video, dl, ai_result, final_path)
            if record_id:
                print(f"      ✅ Đã lưu record Supabase ID: {record_id}")

            print(f"      🎉 XONG!")
            print(f"      📁 Video: {final_path}")
            print(f"      🔗 Link Drive: {drive_link}")
                
            if on_success:
                try:
                    on_success(drive_link, final_path)
                except Exception as e:
                    print(f"      ⚠️ Lỗi callback on_success: {e}")
                
            # Giải phóng bộ nhớ sau khi upload thành công
            print(f"      🧹 Đang dọn dẹp bộ nhớ tạm...")
            try:
                import shutil
                if os.path.exists(work_dir):
                    shutil.rmtree(work_dir)
                if dl and dl.get("path") and os.path.exists(dl["path"]):
                    os.remove(dl["path"])
                print(f"      ✅ Đã giải phóng bộ nhớ cho job {job_id}")
            except Exception as e:
                print(f"      ⚠️ Lỗi khi dọn dẹp: {e}")
                    
            return True

        except Exception as e:
            print(f"      ❌ Lỗi: {e}")
            import traceback
            traceback.print_exc()
            return False

    # ═══════════════════════════════════════════════════
    #  MODE 1: CÓ FRAME
    #  → Giống TikTok: dùng video_remix.create_video_from_source_video
    #  → Intro: hook voice (cột E) + frame + logo + text
    #  → Body:  script voice (cột C) + frame + logo
    # ═══════════════════════════════════════════════════
    def _edit_video_with_frame(self, source_video, hook_voice_path, script_voice_path,
                                title, hook_text, work_dir, job_id, source):
        # NATIVE FFmpeg implementation cho chế độ CÓ FRAME
        # Sử dụng 1 pass duy nhất: Loop video gốc + chèn full script_voice
        
        final_path = os.path.join(work_dir, f"final_{job_id}.mp4")

        hook_duration = 5.0
        if hook_voice_path and os.path.exists(hook_voice_path):
            d = _get_duration(hook_voice_path)
            if d > 0:
                hook_duration = d + 0.5

        has_logo = False # os.path.exists(LOGO_PATH) # Tạm tắt logo
        has_frame = os.path.exists(FRAME_PATH)

        # ── XÂY DỰNG FFMPEG COMMAND (1 PASS) ──
        inputs = []
        input_idx = 0
        
        has_ai_audio = (script_voice_path and os.path.exists(script_voice_path)) or (hook_voice_path and os.path.exists(hook_voice_path))
        
        # Dùng -stream_loop -1 để lặp lại video gốc nếu nó ngắn hơn voice
        if has_ai_audio:
            inputs += ["-stream_loop", "-1"]
            
        inputs += ["-i", source_video]
        input_idx += 1
        
        if script_voice_path and os.path.exists(script_voice_path):
            inputs += ["-i", script_voice_path]
            audio_idx = input_idx
            input_idx += 1
        else:
            audio_idx = None
            
        if has_frame:
            inputs += ["-i", FRAME_PATH]
            frame_idx = input_idx
            input_idx += 1

        if has_logo:
            inputs += ["-i", LOGO_PATH]
            logo_idx = input_idx
            input_idx += 1

        is_horiz = _is_horizontal(source_video)
        delogo_config = source.get("delogo", "").strip()
        delogo_filter = f",delogo={delogo_config}" if delogo_config else ""

        if is_horiz:
            filters = [
                "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:5[bg_blur]",
                "[0:v]scale=1080:1920:force_original_aspect_ratio=decrease[fg]",
                f"[bg_blur][fg]overlay=(W-w)/2:(H-h)/2-150{delogo_filter}[bg]"
            ]
        else:
            filters = [f"[0:v]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:100{delogo_filter}[bg]"]
        
        current = "[bg]"

        if has_frame:
            filters.append(f"[{frame_idx}:v]scale=1080:1920[frame]")
            filters.append(f"{current}[frame]overlay=0:0[with_frame]")
            current = "[with_frame]"

        if has_logo:
            filters.append(f"[{logo_idx}:v]scale=1080:1920[logo]")
            filters.append(f"{current}[logo]overlay=0:0[with_logo]")
            current = "[with_logo]"

        import textwrap
        font_path = os.path.join(APP_DIR, "assets", "font", "RobotoCondensed-Bold.ttf")
        has_font = os.path.exists(font_path)
        
        wrapped_lines = []
        font_size = 50
        start_y = 1920 - 690 
        line_spacing = int(font_size * 1.2)
        
        if has_font and hook_text:
            safe_text = str(hook_text).replace("'", "").replace(":", "\\:").replace("%", "\\%").strip().upper()
            max_width_px = 950
            avg_char_width = font_size * 0.55
            max_chars = int(max_width_px / avg_char_width)
            wrapped_lines = textwrap.wrap(safe_text, width=max_chars)
            
            for i, line in enumerate(wrapped_lines):
                y_pos = start_y + (i * line_spacing)
                # Text hiển thị xuyên suốt video
                draw_filter = (
                    f"drawtext=fontfile='{font_path}':text='{line}':"
                    f"fontsize={font_size}:fontcolor=white:bordercolor=black:borderw=2:"
                    f"shadowcolor=black:shadowx=2:shadowy=2:x=65:y={y_pos}"
                )
                filters.append(f"{current}{draw_filter}[vout{i}]")
                current = f"[vout{i}]"

        filters.append(f"{current}copy[vout]")

        cmd = ["ffmpeg", "-y"] + inputs
        cmd += ["-filter_complex", ";".join(filters), "-map", "[vout]"]
        cmd += ["-map", f"{audio_idx}:a"] if audio_idx is not None else ["-map", "0:a?"]
        
        # Dùng -shortest để cắt đúng lúc AI Voice kết thúc (vì video loop vô hạn)
        cmd += ["-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-c:a", "aac", "-b:a", "128k", "-shortest", final_path]

        print(f"         Tạo video CÓ FRAME (1 pass: Voice full + loop video)...")
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if res.returncode != 0:
                print(f"         ⚠️ FFmpeg lỗi: {res.stderr}")
        except Exception as e:
            print(f"         ⚠️ FFmpeg lỗi exception: {e}")

        if not os.path.exists(final_path):
            import shutil
            shutil.copy2(source_video, final_path)
            print(f"         ℹ️ Dùng video gốc (FFmpeg thất bại)")

        if os.path.exists(final_path):
            size_mb = os.path.getsize(final_path) / 1024 / 1024
            print(f"         ✅ Video CÓ FRAME: {size_mb:.1f}MB")

        return final_path

    # ═══════════════════════════════════════════════════
    #  MODE 2: KHÔNG FRAME (trong video_remix)
    #  → Đoạn đầu: video gốc (mute) + hook voice + frame + logo
    #  → Đoạn sau: video gốc (giữ audio gốc) + logo
    #  → Logo xuyên suốt toàn bộ video
    # ═══════════════════════════════════════════════════
    def _edit_video_no_frame(self, source_video, hook_voice_path, hook_text,
                              work_dir, job_id, source):
        # 1 PASS: Xử lý lại hình ảnh (Text, Logo) + Đè Voice đoạn đầu
        final_path = os.path.join(work_dir, f"final_{job_id}.mp4")

        hook_duration = 5.0
        if hook_voice_path and os.path.exists(hook_voice_path):
            d = _get_duration(hook_voice_path)
            if d > 0:
                hook_duration = d + 0.5

        has_logo = False # os.path.exists(LOGO_PATH) # Tạm tắt logo
        has_frame = os.path.exists(FRAME_PATH)

        inputs = ["-i", source_video]
        input_idx = 1

        if hook_voice_path and os.path.exists(hook_voice_path):
            inputs += ["-i", hook_voice_path]
            audio_idx = input_idx
            input_idx += 1
        else:
            audio_idx = None

        if has_frame:
            inputs += ["-i", FRAME_PATH]
            frame_idx = input_idx
            input_idx += 1

        if has_logo:
            inputs += ["-i", LOGO_PATH]
            logo_idx = input_idx
            input_idx += 1

        is_horiz = _is_horizontal(source_video)
        delogo_config = source.get("delogo", "").strip()
        delogo_filter = f",delogo={delogo_config}" if delogo_config else ""

        if is_horiz:
            filters = [
                "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:5[bg_blur]",
                "[0:v]scale=1080:1920:force_original_aspect_ratio=decrease[fg]",
                f"[bg_blur][fg]overlay=(W-w)/2:(H-h)/2-150{delogo_filter}[bg]"
            ]
        else:
            filters = [f"[0:v]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:100{delogo_filter}[bg]"]
        
        current = "[bg]"

        if has_frame:
            filters.append(f"[{frame_idx}:v]scale=1080:1920[frame]")
            filters.append(f"{current}[frame]overlay=0:0[with_frame]")
            current = "[with_frame]"

        if has_logo:
            filters.append(f"[{logo_idx}:v]scale=1080:1920[logo]")
            filters.append(f"{current}[logo]overlay=0:0[with_logo]")
            current = "[with_logo]"

        import textwrap
        font_path = os.path.join(APP_DIR, "assets", "font", "RobotoCondensed-Bold.ttf")
        has_font = os.path.exists(font_path)
        
        if has_font and hook_text:
            safe_text = str(hook_text).replace("'", "").replace(":", "\\:").replace("%", "\\%").strip().upper()
            font_size = 50
            max_width_px = 950
            avg_char_width = font_size * 0.55
            max_chars = int(max_width_px / avg_char_width)
            wrapped_lines = textwrap.wrap(safe_text, width=max_chars)
            
            start_y = 1920 - 690  
            line_spacing = int(font_size * 1.2)
            
            for i, line in enumerate(wrapped_lines):
                y_pos = start_y + (i * line_spacing)
                # Text hiển thị xuyên suốt video
                draw_filter = (
                    f"drawtext=fontfile='{font_path}':text='{line}':"
                    f"fontsize={font_size}:fontcolor=white:bordercolor=black:borderw=2:"
                    f"shadowcolor=black:shadowx=2:shadowy=2:"
                    f"x=65:y={y_pos}"
                )
                filters.append(f"{current}{draw_filter}[vout{i}]")
                current = f"[vout{i}]"

        filters.append(f"{current}copy[vout]")

        # Kiểm tra video gốc có audio không
        has_audio = False
        try:
            probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=codec_name", "-of", "default=noprint_wrappers=1:nokey=1", source_video], capture_output=True, text=True)
            has_audio = bool(probe.stdout.strip())
        except:
            pass

        if audio_idx is not None:
            if has_audio:
                # Mute audio gốc đoạn đầu, mix với hook voice, độ dài bằng audio gốc
                filters.append(f"[0:a]volume=0:enable='between(t,0,{hook_duration})'[orig_mute]")
                filters.append(f"[orig_mute][{audio_idx}:a]amix=inputs=2:duration=first:dropout_transition=0[aout]")
            else:
                filters.append(f"[{audio_idx}:a]acopy[aout]")
        else:
            if has_audio:
                filters.append(f"[0:a]acopy[aout]")

        cmd = ["ffmpeg", "-y"] + inputs
        cmd += ["-filter_complex", ";".join(filters), "-map", "[vout]"]
        
        if (audio_idx is not None) or has_audio:
            cmd += ["-map", "[aout]"]
            
        cmd += ["-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-c:a", "aac", "-b:a", "128k", final_path]

        print(f"         Tạo video KHÔNG FRAME (1 pass: Voice hook mix audio gốc, có chỉnh sửa text/logo)...")
        try:
            subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        except Exception as e:
            print(f"         ⚠️ FFmpeg lỗi: {e}")

        # Fallback
        if not os.path.exists(final_path):
            import shutil
            shutil.copy2(source_video, final_path)
            print(f"         ℹ️ Dùng video gốc (FFmpeg thất bại)")

        if os.path.exists(final_path):
            size_mb = os.path.getsize(final_path) / 1024 / 1024
            print(f"         ✅ Video NO FRAME: {size_mb:.1f}MB")
            
        return final_path

    # ═══════════════════════════════════════════════════
    #  SUPABASE HELPERS
    # ═══════════════════════════════════════════════════
    def _get_active_sources(self) -> list:
        try:
            result = supabase.table("facebook_sources") \
                .select("*").eq("is_active", True) \
                .order("created_at").execute()
            return result.data or []
        except Exception as e:
            print(f"❌ Lỗi load sources: {e}")
            return []

    def _update_scan_time(self, source_id: str, last_video_id: str = None):
        try:
            update = {"last_scan_at": datetime.now(timezone.utc).isoformat()}
            if last_video_id:
                update["last_video_id"] = last_video_id
            supabase.table("facebook_sources").update(update).eq("id", source_id).execute()
        except:
            pass

    def _insert_video_record(self, source_id: str, video: dict, dl: dict, ai_result: dict, final_path: str) -> str | None:
        try:
            result = supabase.table("facebook_videos").insert({
                "source_id": source_id,
                "facebook_video_id": video.get("video_id"),
                "original_url": video["url"],
                "caption": video.get("caption", "")[:500],
                "status": "completed",
                "file_hash": dl.get("hash"),
                "file_size_bytes": dl.get("size"),
                "downloaded_path": dl.get("path"),
                "ai_title": ai_result.get("title_tiktok", ""),
                "ai_script": ai_result.get("script_voice", ""),
                "processed_path": final_path,
            }).execute()
            return result.data[0]["id"] if result.data else None
        except Exception as e:
            if "23505" in str(e):
                return None
            print(f"      ⚠️ DB insert lỗi: {e}")
            return None

    def _check_hash_exists(self, file_hash: str) -> bool:
        try:
            result = supabase.table("facebook_videos") \
                .select("id").eq("file_hash", file_hash).limit(1).execute()
            return bool(result.data)
        except:
            return False


# ═══════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Facebook News Auto Remix Pipeline")
    parser.add_argument("command", nargs="?", default="run-once",
                       choices=["run-once", "start", "login"],
                       help="run-once: chạy 1 lần | start: chạy liên tục | login: login Facebook")
    parser.add_argument("--interval", type=int, default=30,
                       help="Khoảng cách giữa các lần quét (phút)")
    args = parser.parse_args()

    if args.command == "login":
        from fb_crawler import login_facebook_interactive
        login_facebook_interactive()
        return

    pipeline = FBNewsPipeline()

    if args.command == "run-once":
        pipeline.run()
    elif args.command == "start":
        print(f"⏱️ Chạy liên tục, quét mỗi {args.interval} phút")
        while True:
            pipeline.run()
            print(f"\n📅 Đợi {args.interval} phút...\n")
            time.sleep(args.interval * 60)


if __name__ == "__main__":
    main()
