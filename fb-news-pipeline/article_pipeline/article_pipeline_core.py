#!/usr/bin/env python3
import os
import sys
import time
import json
from datetime import datetime

# Import các module vừa viết
from category_crawler import CategoryCrawler
from article_crawler import ArticleCrawler
from image_searcher import ImageSearcher
from article_sheet_api import save_article_to_sheet
from article_chatgpt_automator import analyze_article_with_chatgpt
from article_ffmpeg import create_article_video

# Import từ project chính (mannyAccount)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from services.tts_api import create_voice_full_pipeline

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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

try:
    from supabase import create_client
    supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"❌ Lỗi Supabase: {e}")
    sys.exit(1)

class ArticlePipelineCore:
    def __init__(self):
        self.cat_crawler = CategoryCrawler()
        self.art_crawler = ArticleCrawler()
        self.img_searcher = ImageSearcher()
        self.temp_dir = os.path.join(PROJECT_ROOT, "temp")
        os.makedirs(self.temp_dir, exist_ok=True)

    def run_once(self):
        print("\n" + "="*50)
        print("🚀 KHỞI ĐỘNG CỖ MÁY BÁO MẠNG -> VIDEO")
        print("="*50)
        
        # 1. Lấy danh sách nguồn báo
        try:
            res = supabase_client.table("article_sources").select("*").eq("is_active", True).execute()
            sources = res.data or []
        except Exception as e:
            print(f"❌ Lỗi lấy nguồn: {e}")
            return

        if not sources:
            print("📭 Không có nguồn báo nào đang bật.")
            return

        for source in sources:
            sid = source["id"]
            id_tiktok = source["id_tiktok"]
            category_url = source["category_url"]
            last_article_url = source.get("last_article_url")
            
            print(f"\n📡 Đang kiểm tra nguồn: {id_tiktok} ({category_url})")
            
            # 2. Quét danh mục tìm link bài mới nhất
            links = self.cat_crawler.get_latest_articles(category_url, max_links=3)
            if not links:
                print("   ⚠️ Không tìm thấy bài báo nào trong danh mục.")
                continue
                
            newest_link = links[0]
            if newest_link == last_article_url:
                print("   ✅ Không có bài báo mới (Đã làm bài mới nhất rồi).")
                continue
                
            print(f"   🔥 CÓ BÀI BÁO MỚI! -> {newest_link}")
            
            # 3. Cào nội dung & Ảnh của bài báo
            job_dir = os.path.join(self.temp_dir, f"article_{int(time.time())}")
            article_data = self.art_crawler.crawl(newest_link, job_dir)
            
            if not article_data or not article_data["content"]:
                print("   ❌ Cào bài báo thất bại hoặc bài quá ngắn.")
                continue
                
            # 4. Gửi nội dung cho AI phân tích qua ChatGPT (Giao diện Chrome)
            ai_result = analyze_article_with_chatgpt(article_data["content"], id_tiktok)
            
            if not ai_result:
                print("   ❌ AI phân tích thất bại.")
                continue
                
            # 5. Cào thêm ảnh mạng nếu thiếu (Dựa vào scenes -> visual_description)
            scenes = ai_result.get("scenes", [])
            prompts = [scene.get("visual_description", "") for scene in scenes if scene.get("visual_description")]
            downloaded_imgs = article_data["images"]
            
            if prompts:
                # Nếu thiếu ảnh, tự động search thêm
                extra_imgs = self.img_searcher.download_missing_images(prompts, job_dir)
                downloaded_imgs.extend(extra_imgs)
                
            print(f"   📸 Tổng cộng có {len(downloaded_imgs)} ảnh để làm video.")
            
            # 6. Ghi Google Sheet (Sheet 'tổng')
            save_article_to_sheet(ai_result, newest_link, id_tiktok)
            
            # 7. Khởi tạo Voice (âm thanh)
            print("   🗣️ Bắt đầu tổng hợp Voice cho bài báo...")
            full_text = f"{ai_result.get('hook', '')}. {ai_result.get('script_voice', '')}"
            voice_path = None
            try:
                voice_path = create_voice_full_pipeline(
                    text=full_text,
                    save_dir=job_dir,
                    filename="full_voice.wav",
                    profile_id="theanh28" # TODO: Lấy từ config/DB nếu cần đổi giọng
                )
                if voice_path and os.path.exists(voice_path):
                    print(f"      ✅ Sinh Voice thành công: {os.path.getsize(voice_path) / 1024:.0f}KB")
                else:
                    print("      ⚠️ Sinh Voice bị rỗng!")
                    voice_path = None
            except Exception as e:
                print(f"      ⚠️ Sinh Voice lỗi: {e}")

            # 8. Dựng Video bằng FFmpeg
            if downloaded_imgs and voice_path:
                print("   🎬 [TRẠM DỪNG TẠM THỜI] Chuyển qua bước Dựng Video FFmpeg...")
                output_video_path = os.path.join(job_dir, f"final_{id_tiktok}_{int(time.time())}.mp4")
                create_article_video(id_tiktok, downloaded_imgs, voice_path, output_video_path)
            else:
                print("   ⚠️ Thiếu ảnh hoặc Voice, không thể dựng video.")

            # Cập nhật last_article_url vào Supabase
            try:
                supabase_client.table("article_sources").update({"last_article_url": newest_link}).eq("id", sid).execute()
                print("   ✅ Đã đánh dấu bài báo này là 'Đã Xử Lý' trong Database.")
            except Exception as e:
                print(f"   ⚠️ Lỗi cập nhật last_article_url: {e}")
                
            break # Chạy 1 bài báo trước để test

    def run_loop(self):
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
