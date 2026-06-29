#!/usr/bin/env python3
import os
import sys
import time
import json
import shutil
from datetime import datetime
import concurrent.futures

# Import các module vừa viết
from category_crawler import CategoryCrawler
from article_crawler import ArticleCrawler
from image_searcher import ImageSearcher
from article_sheet_api import save_article_to_sheet
from article_chatgpt_automator import analyze_article_with_chatgpt
from article_ffmpeg import create_article_video

# Import từ project chính (mannyAccount)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from shared.services.tts_api import create_voice_full_pipeline

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENV_FILE = os.path.join(PROJECT_ROOT, ".env")

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
VOICE_PROFILE_ID = ENV.get("VOICEBOX_PROFILE_ID", "c2d78da2-521d-44a8-af55-ecf603866489")

try:
    from supabase import create_client
    supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"❌ Lỗi Supabase: {e}")
    sys.exit(1)

QUALITY_LOG_PATH = os.path.join(PROJECT_ROOT, "data", "quality_log.jsonl")

def _append_quality_log(pipeline: str, source_name: str, quality_score: int, status: str, reason: str = ""):
    """Ghi 1 dòng JSON vào quality_log.jsonl để Telegram bot đọc báo cáo."""
    try:
        entry = json.dumps({
            "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "pl": pipeline,
            "src": source_name,
            "score": quality_score,
            "st": status,
            "reason": reason,
        }, ensure_ascii=False)
        with open(QUALITY_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(entry + "\n")
    except Exception:
        pass

class ArticlePipelineCore:
    def __init__(self):
        self.cat_crawler = CategoryCrawler()
        self.art_crawler = ArticleCrawler()
        self.img_searcher = ImageSearcher()
        self.temp_dir = os.path.join(PROJECT_ROOT, "temp")
        os.makedirs(self.temp_dir, exist_ok=True)

    def process_channel_independently(self, id_tiktok, channel_sources):
        print(f"\n[KÊNH {id_tiktok}] 🟢 Bắt đầu chạy độc lập với {len(channel_sources)} danh mục báo.")
        
        for source in channel_sources:
            sid = source["id"]
            category_url = source["category_url"]
            last_article_url = source.get("last_article_url")
            
            print(f"\n[KÊNH {id_tiktok}] 📡 Quét danh mục: {category_url}")
            
            # Lấy 10 bài báo mới nhất
            links = self.cat_crawler.get_latest_articles(category_url, max_links=10)
            if not links:
                print(f"[KÊNH {id_tiktok}] ⚠️ Không tìm thấy bài báo nào trong danh mục.")
                continue
                
            links_to_process = []
            for link in links:
                if link == last_article_url:
                    break
                links_to_process.append(link)
                
            if not links_to_process:
                print(f"[KÊNH {id_tiktok}] ✅ Không có bài báo mới (Đã làm đến bài mới nhất rồi).")
                continue
                
            # Đảo ngược danh sách để xử lý bài cũ nhất trước, bài mới nhất sau cùng
            # Để nếu có lỗi giữa chừng, lần sau chạy lại không bị bỏ sót.
            links_to_process.reverse()
            
            print(f"[KÊNH {id_tiktok}] 🔥 Tìm thấy {len(links_to_process)} bài báo mới chưa làm! Sẽ xử lý lần lượt...")
            
            for article_url in links_to_process:
                print(f"\n[KÊNH {id_tiktok}] 🕷️ Đang xử lý: {article_url}")
                success = self.process_single_article(id_tiktok, sid, article_url)
                
                if not success:
                    print(f"[KÊNH {id_tiktok}] ❌ Xử lý thất bại bài {article_url}. Dừng xử lý danh mục này để tránh lọt bài.")
                    break # Break để lần sau chạy lại từ bài này
                else:
                    # Cập nhật last_article_url ngay khi xử lý thành công 1 bài
                    try:
                        supabase_client.table("article_sources").update({"last_article_url": article_url}).eq("id", sid).execute()
                        print(f"[KÊNH {id_tiktok}] ✅ Đã cập nhật mốc bài báo: {article_url}")
                    except Exception as e:
                        print(f"[KÊNH {id_tiktok}] ⚠️ Lỗi cập nhật last_article_url DB: {e}")
                        
            print(f"[KÊNH {id_tiktok}] 🏁 Hoàn thành danh mục: {category_url}. Chuyển sang danh mục tiếp theo...")
            
        print(f"\n[KÊNH {id_tiktok}] 🛑 Kết thúc chu trình của kênh này.")

    def process_single_article(self, id_tiktok, sid, article_url):
        """Xử lý 1 bài báo từ A-Z. Trả về True nếu upload thành công, False nếu lỗi."""
        job_dir = os.path.join(self.temp_dir, f"article_{int(time.time())}_{id_tiktok}")
        try:
            # 1. Cào nội dung & Ảnh của bài báo
            article_data = self.art_crawler.crawl(article_url, job_dir)
            if not article_data:
                print(f"   [KÊNH {id_tiktok}] ❌ Không cào được nội dung bài báo.")
                return False
                
            # 2. Gửi nội dung cho AI phân tích qua ChatGPT
            ai_result = analyze_article_with_chatgpt(article_url, id_tiktok)
            if not ai_result:
                print(f"   [KÊNH {id_tiktok}] ❌ AI phân tích thất bại.")
                return False

            # Quality gate: bỏ qua bài báo chất lượng thấp (trả True để advance checkpoint)
            quality_score = int(ai_result.get("quality_score", 5))
            skip_reason = ai_result.get("skip_reason", "")
            quality_threshold = int(os.environ.get("QUALITY_THRESHOLD", "6"))
            if quality_score < quality_threshold:
                print(f"   [KÊNH {id_tiktok}] ⏭️ Quality score {quality_score}/10 dưới ngưỡng {quality_threshold} → bỏ qua. {f'Lý do: {skip_reason}' if skip_reason else ''}")
                _append_quality_log("article", id_tiktok, quality_score, "skip", skip_reason)
                return True
            print(f"   [KÊNH {id_tiktok}] ✅ Quality score: {quality_score}/10")
            _append_quality_log("article", id_tiktok, quality_score, "done")

            # 3. Gom ảnh gốc & Tìm thêm ảnh
            downloaded_imgs = article_data.get("images", [])
            if len(downloaded_imgs) > 1:
                downloaded_imgs = downloaded_imgs[1:]  # Bỏ ảnh đầu (thường là banner/thumbnail)
            downloaded_videos = article_data.get("videos", [])
            
            if not downloaded_imgs:
                print(f"   [KÊNH {id_tiktok}] ⚠️ Bài báo không có ảnh gốc, sẽ tìm toàn bộ ảnh từ DuckDuckGo...")
            
            TARGET_IMAGES = 7
            if len(downloaded_imgs) < TARGET_IMAGES:
                scenes = ai_result.get("scenes", [])
                search_prompts = [s.get("visual_description", "") for s in scenes if len(s.get("visual_description", "")) > 10]
                needed = TARGET_IMAGES - len(downloaded_imgs)
                if search_prompts:
                    search_prompts = search_prompts[:needed]
                    print(f"   [KÊNH {id_tiktok}] 🔎 Thiếu ảnh, đang tìm thêm {needed} ảnh từ DuckDuckGo...")
                    extra_imgs = self.img_searcher.download_missing_images(search_prompts, job_dir)
                    downloaded_imgs.extend(extra_imgs)
            
            if not downloaded_imgs:
                print(f"   [KÊNH {id_tiktok}] ❌ Không tìm được ảnh nào (cả từ bài báo lẫn DuckDuckGo). Bỏ qua bài này.")
                return False
            
            print(f"   [KÊNH {id_tiktok}] 📸 Tổng số ảnh để làm video: {len(downloaded_imgs)}, Số video: {len(downloaded_videos)}")
            
            # 4. Sinh Voice
            print(f"   [KÊNH {id_tiktok}] 🗣️ Bắt đầu sinh Voice OmniVoice...")
            hook_text = ai_result.get('hook', '')
            script_text = ai_result.get('script_voice', '')
            
            tone = ai_result.get("tone", "Trung tính")
            channel_voice_id = VOICE_PROFILE_ID
            try:
                voice_cfg_path = os.path.join(PROJECT_ROOT, "assets", "channels", id_tiktok, "voice_config.json")
                if os.path.exists(voice_cfg_path):
                    with open(voice_cfg_path, "r", encoding="utf-8") as f:
                        voice_cfg = json.load(f)
                        
                        tone_id = voice_cfg.get(tone, "").strip()
                        neutral_id = voice_cfg.get("Trung tính", "").strip()
                        
                        if tone_id:
                            channel_voice_id = tone_id
                        elif neutral_id:
                            channel_voice_id = neutral_id
            except Exception: pass
            
            print(f"   [KÊNH {id_tiktok}] 🎵 Tone nhận diện: {tone} -> Chọn Voice ID: {channel_voice_id}")

            voice_hook_path = None
            voice_script_path = None
            
            try:
                if hook_text:
                    voice_hook_path = create_voice_full_pipeline(hook_text, job_dir, "hook_voice.wav", channel_voice_id)
                if script_text:
                    voice_script_path = create_voice_full_pipeline(script_text, job_dir, "script_voice.wav", channel_voice_id)
            except Exception as e:
                print(f"   [KÊNH {id_tiktok}] ⚠️ Lỗi sinh Voice: {e}")
                return False
                
            # 5. Dựng Video
            if not downloaded_imgs or (not voice_hook_path and not voice_script_path):
                print(f"   [KÊNH {id_tiktok}] ⚠️ Thiếu ảnh hoặc voice, hủy dựng video.")
                return False
                
            print(f"   [KÊNH {id_tiktok}] 🎬 Đang dựng FFmpeg...")
            output_video_path = os.path.join(job_dir, f"final_{id_tiktok}_{int(time.time())}.mp4")
            
            # Nếu có video gốc từ báo, truyền video đầu tiên vào (nếu có nhiều lấy 1)
            appended_video_path = downloaded_videos[0] if downloaded_videos else None
            create_article_video(id_tiktok, downloaded_imgs, voice_hook_path, voice_script_path, output_video_path, hook_text, appended_video_path, tone)
            
            # 6. Upload & Lưu Google Sheet
            drive_link = None
            if os.path.exists(output_video_path):
                print(f"   [KÊNH {id_tiktok}] ☁️ Đang upload Google Drive...")
                try:
                    from shared.modules.upload_drive import upload_video_to_drive
                    gdrive_folder_id = ENV.get("DRIVE_FOLDER_ID", ENV.get("GDRIVE_FOLDER_ID", "1VgkkbUJ82kxzWXJH8cfn7UFMMFBKQkzS"))
                    drive_link = upload_video_to_drive(output_video_path, gdrive_folder_id)
                    print(f"   [KÊNH {id_tiktok}] ✅ Upload xong: {drive_link}")
                except Exception as e:
                    print(f"   [KÊNH {id_tiktok}] ⚠️ Lỗi upload Drive: {e}")
                    return False
            else:
                print(f"   [KÊNH {id_tiktok}] ⚠️ Render FFmpeg thất bại, không ra file mp4.")
                return False
                
            if drive_link:
                print(f"   [KÊNH {id_tiktok}] 📊 Ghi Sheet...")
                sheet_result = save_article_to_sheet(ai_result, article_url, id_tiktok)
                sheet_row = sheet_result.get("row") if sheet_result else None
                if sheet_row:
                    from article_sheet_api import update_article_drive_link
                    try:
                        sheet_name = "facebook" if id_tiktok == "Adsupnews" else "tổng"
                        update_article_drive_link(sheet_row, drive_link, sheet_name)
                    except Exception as e:
                        print(f"   [KÊNH {id_tiktok}] ⚠️ Lỗi ghi link Drive: {e}")
                return True
            return False

        finally:
            self._cleanup_job(job_dir)

    def run_once(self):
        print("\n" + "="*50)
        print("🚀 KHỞI ĐỘNG CỖ MÁY BÁO MẠNG -> VIDEO (ĐA LUỒNG)")
        print("="*50)
        
        try:
            res = supabase_client.table("article_sources").select("*").eq("is_active", True).execute()
            sources = res.data or []
        except Exception as e:
            print(f"❌ Lỗi lấy nguồn Database: {e}")
            return

        if not sources:
            print("📭 Không có nguồn báo nào đang bật.")
            return

        # Lọc theo danh sách kênh được chọn (nếu có tham số --channels)
        channels_arg = None
        if "--channels" in sys.argv:
            idx = sys.argv.index("--channels")
            channels_arg = sys.argv[idx+1].split(",")
            
        channels_map = {}
        for source in sources:
            tid = source["id_tiktok"]
            if channels_arg and tid not in channels_arg:
                continue
            if tid not in channels_map:
                channels_map[tid] = []
            channels_map[tid].append(source)
            
        print(f"🌐 Tìm thấy {len(channels_map)} Kênh Tiktok cần chạy.")
        
        # Chạy song song từng id_tiktok (độc lập hoàn toàn, không ai đợi ai)
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(channels_map)) as executor:
            futures = []
            for id_tiktok, channel_sources in channels_map.items():
                futures.append(executor.submit(self.process_channel_independently, id_tiktok, channel_sources))
                
            # Đợi tất cả kênh chạy xong 1 vòng
            concurrent.futures.wait(futures)
            
        print("\n✅ TẤT CẢ CÁC KÊNH ĐÃ HOÀN THÀNH CHU TRÌNH.")

    def _cleanup_job(self, job_dir):
        if not os.path.exists(job_dir):
            return
        try:
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(job_dir):
                for f in filenames:
                    total_size += os.path.getsize(os.path.join(dirpath, f))
            size_mb = total_size / (1024 * 1024)
            shutil.rmtree(job_dir)
            print(f"   🧹 Dọn {size_mb:.1f} MB tạm của {os.path.basename(job_dir)}")
        except Exception as e:
            pass

    def _cleanup_old_jobs(self):
        if not os.path.exists(self.temp_dir):
            return
        old_jobs = [d for d in os.listdir(self.temp_dir) if os.path.isdir(os.path.join(self.temp_dir, d)) and d.startswith("article_")]
        total_freed = 0
        for job_name in old_jobs:
            job_path = os.path.join(self.temp_dir, job_name)
            try:
                for dirpath, dirnames, filenames in os.walk(job_path):
                    for f in filenames:
                        total_freed += os.path.getsize(os.path.join(dirpath, f))
                shutil.rmtree(job_path)
            except:
                pass
        if total_freed > 0:
            print(f"🧹 Đã dọn dẹp {len(old_jobs)} job cũ, giải phóng {total_freed / (1024*1024):.1f} MB")

    def run_loop(self):
        self._cleanup_old_jobs()
        while True:
            self.run_once()
            print("\n⏳ Chờ 30 phút để quét lại...")
            time.sleep(30 * 60)

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "run-once"
    core = ArticlePipelineCore()
    if mode == "start":
        core.run_loop()
    else:
        core.run_once()
