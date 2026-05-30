#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════
  Facebook News Auto Remix — Pipeline chính
  
  FLOW MỚI:
  1. Cào 10 video (reels) từ Facebook page
  2. Lọc video mới (so sánh last_video_id)
  3. Với mỗi video mới:
     a. Download video
     b. Gửi video + caption cho Gemini AI → nhận JSON
     c. Ghi JSON lên Google Sheet (hook→B, script_voice→I)
     d. Lấy hook → tạo voice
     e. Dựng video: intro (video gốc + frame + logo + voice hook)
                   + video gốc (giữ audio gốc)
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
    return default

VOICE_PROFILE_ID = _env("VOICEBOX_PROFILE_ID", "cb6f4c6a-2617-4eeb-a148-909f0084d8c8")

# Logo/frame paths
LOGO_PATH = os.path.join(APP_DIR, "assets", "logo.png")
FRAME_PATH = os.path.join(APP_DIR, "assets", "frame.png")


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

            success = self._process_one_video(video, source)

            if success:
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
    #  XỬ LÝ 1 VIDEO — Flow mới
    # ═══════════════════════════════════════════════════
    def _process_one_video(self, video: dict, source: dict) -> bool:
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

            # Check trùng hash
            if self._check_hash_exists(dl["hash"]):
                print(f"      ⏭️ Trùng file hash → skip")
                return False

            # Lưu record vào DB
            record_id = self._insert_video_record(source["id"], video, dl)

            # ── [2/6] Gửi video + caption cho ChatGPT qua web ──
            print(f"      🤖 [2/6] ChatGPT phân tích video...")
            ai_result = analyze_video_with_chatgpt(dl["path"], caption)

            if not ai_result:
                # Fallback: tạo JSON cơ bản từ caption
                print(f"      ℹ️ AI không khả dụng — dùng caption gốc")
                ai_result = {
                    "title_tiktok": caption[:100],
                    "hook": caption[:80],
                    "script_voice": caption[:200],
                    "main_idea": caption[:150],
                    "estimated_duration_seconds": 30,
                    "scenes": [],
                    "content_style": "Tin tức viral",
                }

            hook = ai_result.get("hook", "")
            script_voice = ai_result.get("script_voice", "")
            title = ai_result.get("title_tiktok", "")

            # Cập nhật DB
            if record_id:
                supabase.table("facebook_videos").update({
                    "ai_title": title,
                    "ai_script": script_voice,
                    "status": "generating_script",
                }).eq("id", record_id).execute()

            # ── [3/6] Ghi lên Google Sheet ──
            print(f"      📊 [3/6] Ghi Google Sheet...")
            sheet_result = save_fb_to_sheet(
                ai_result=ai_result,
                video_url=video["url"],
                source_name=source.get("source_name", ""),
            )
            sheet_row = sheet_result.get("row") if sheet_result else None

            # ── [4/6] Tạo voice từ hook ──
            print(f"      🗣️ [4/6] Tạo voice hook: \"{hook[:50]}...\"")
            voice_path = None

            if hook:
                try:
                    voice_path = create_voice_full_pipeline(
                        text=hook,
                        save_dir=work_dir,
                        filename=f"hook_{job_id}.wav",
                        profile_id=VOICE_PROFILE_ID,
                    )
                    if voice_path and os.path.exists(voice_path):
                        print(f"      ✅ Voice OK: {os.path.getsize(voice_path) / 1024:.0f}KB")
                    else:
                        print(f"      ⚠️ Voice trả về nhưng file không tồn tại")
                        voice_path = None
                except Exception as e:
                    print(f"      ⚠️ Voice lỗi: {e} — bỏ qua voice")

            # ── [5/6] Dựng video: intro (hook voice + frame) + video gốc ──
            print(f"      🎬 [5/6] Dựng video...")
            final_path = self._edit_video(
                source_video=dl["path"],
                voice_path=voice_path,
                title=hook or title,
                work_dir=work_dir,
                job_id=job_id,
            )

            # ── [6/6] Hoàn tất ──
            if record_id:
                supabase.table("facebook_videos").update({
                    "status": "completed",
                    "processed_path": final_path,
                }).eq("id", record_id).execute()

            if sheet_row:
                update_fb_status(sheet_row, "completed")

            print(f"      🎉 [6/6] XONG!")
            print(f"      📁 Video: {final_path}")

            return True

        except Exception as e:
            print(f"      ❌ Lỗi: {e}")
            return False
        finally:
            pass  # Giữ temp files để debug, dọn sau

    # ═══════════════════════════════════════════════════
    #  VIDEO EDITOR — FFmpeg
    #
    #  Đoạn đầu: video gốc + frame + logo + voice hook
    #  Đoạn sau:  video gốc (giữ voice gốc)
    # ═══════════════════════════════════════════════════
    def _edit_video(self, source_video: str, voice_path: str | None,
                    title: str, work_dir: str, job_id: str) -> str:
        """
        Dựng video 2 phần:
        - Intro: lấy đoạn đầu video gốc + overlay frame/logo + voice hook (mute audio gốc)
        - Body: phần còn lại video gốc (giữ nguyên audio gốc)
        """
        final_path = os.path.join(work_dir, f"final_{job_id}.mp4")

        # Lấy duration voice hook
        hook_duration = 5.0  # mặc định 5 giây nếu không có voice
        if voice_path and os.path.exists(voice_path):
            try:
                result = subprocess.run(
                    ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                     "-of", "csv=p=0", voice_path],
                    capture_output=True, text=True, timeout=10
                )
                hook_duration = float(result.stdout.strip()) + 0.5
            except:
                hook_duration = 5.0

        # Lấy duration video gốc
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                 "-of", "csv=p=0", source_video],
                capture_output=True, text=True, timeout=10
            )
            total_duration = float(result.stdout.strip())
        except:
            total_duration = 30.0

        # Phần 1: Intro — video gốc (đoạn đầu) + voice hook + frame/logo
        intro_path = os.path.join(work_dir, f"intro_{job_id}.mp4")

        # Xây FFmpeg filter cho intro
        filter_parts = []
        inputs = ["-ss", "0", "-t", str(hook_duration), "-i", source_video]
        input_idx = 1

        # Thêm voice hook
        if voice_path and os.path.exists(voice_path):
            inputs += ["-i", voice_path]
            audio_map = f"[{input_idx}:a]"
            input_idx += 1
        else:
            audio_map = None

        # Thêm logo overlay nếu có
        has_logo = os.path.exists(LOGO_PATH)
        if has_logo:
            inputs += ["-i", LOGO_PATH]
            logo_idx = input_idx
            input_idx += 1

        # Thêm frame overlay nếu có
        has_frame = os.path.exists(FRAME_PATH)
        if has_frame:
            inputs += ["-i", FRAME_PATH]
            frame_idx = input_idx
            input_idx += 1

        # Build filter complex
        filters = []
        
        # Định dạng video gốc về 1080x1920 (giữ nguyên tỷ lệ, thêm viền đen nếu cần)
        filters.append("[0:v]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2[bg]")
        current = "[bg]"

        if has_frame:
            # Scale frame đúng 1080x1920
            filters.append(f"[{frame_idx}:v]scale=1080:1920[frame]")
            filters.append(f"{current}[frame]overlay=0:0[with_frame]")
            current = "[with_frame]"

        if has_logo:
            filters.append(f"[{logo_idx}:v]scale=80:80[logo]")
            filters.append(f"{current}[logo]overlay=W-90:10[with_logo]")
            current = "[with_logo]"

        # Thêm text title
        safe_title = title.replace("'", "").replace('"', '').replace(':', ' ')[:60]
        filters.append(
            f"{current}drawtext=text='{safe_title}'"
            f":fontsize=28:fontcolor=white:borderw=2:bordercolor=black"
            f":x=(w-text_w)/2:y=h-60[vout]"
        )

        if filters:
            filter_str = ";".join(filters)
        else:
            filter_str = f"[0:v]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2[vout]"

        # Build intro command
        intro_cmd = ["ffmpeg", "-y"] + inputs
        intro_cmd += ["-filter_complex", filter_str, "-map", "[vout]"]

        if audio_map:
            intro_cmd += ["-map", audio_map]
        else:
            intro_cmd += ["-an"]

        intro_cmd += [
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-shortest",
            intro_path
        ]

        print(f"         Tạo intro ({hook_duration:.1f}s)...")
        try:
            subprocess.run(intro_cmd, capture_output=True, text=True, timeout=120)
        except Exception as e:
            print(f"         ⚠️ FFmpeg intro lỗi: {e}")

        # Phần 2: Body — phần còn lại video gốc (giữ audio gốc)
        body_path = os.path.join(work_dir, f"body_{job_id}.mp4")
        body_cmd = [
            "ffmpeg", "-y",
            "-ss", str(hook_duration),
            "-i", source_video,
            "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            body_path
        ]

        body_duration = total_duration - hook_duration
        if body_duration > 1:
            print(f"         Tạo body ({body_duration:.1f}s, giữ audio gốc)...")
            try:
                subprocess.run(body_cmd, capture_output=True, text=True, timeout=120)
            except Exception as e:
                print(f"         ⚠️ FFmpeg body lỗi: {e}")

        # Ghép intro + body
        if os.path.exists(intro_path) and os.path.exists(body_path) and body_duration > 1:
            concat_list = os.path.join(work_dir, "concat.txt")
            with open(concat_list, "w") as f:
                f.write(f"file '{intro_path}'\n")
                f.write(f"file '{body_path}'\n")

            concat_cmd = [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0",
                "-i", concat_list,
                "-c", "copy",
                final_path
            ]
            print(f"         Ghép intro + body...")
            try:
                subprocess.run(concat_cmd, capture_output=True, text=True, timeout=60)
            except:
                pass

        # Fallback
        if not os.path.exists(final_path):
            if os.path.exists(intro_path):
                shutil.copy2(intro_path, final_path)
            else:
                shutil.copy2(source_video, final_path)
                print(f"         ℹ️ Dùng video gốc (FFmpeg thất bại)")

        size_mb = os.path.getsize(final_path) / 1024 / 1024
        print(f"         ✅ Video final: {size_mb:.1f}MB")
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

    def _insert_video_record(self, source_id: str, video: dict, dl: dict) -> str | None:
        try:
            result = supabase.table("facebook_videos").insert({
                "source_id": source_id,
                "facebook_video_id": video.get("video_id"),
                "original_url": video["url"],
                "caption": video.get("caption", "")[:500],
                "status": "downloaded",
                "file_hash": dl.get("hash"),
                "file_size_bytes": dl.get("size"),
                "downloaded_path": dl.get("path"),
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
