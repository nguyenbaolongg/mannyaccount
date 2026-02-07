import os
import json
import requests
import yt_dlp
import shutil
import time
import subprocess # Dùng để gọi FFmpeg nén video
import requests
# Xác định đường dẫn gốc dự án
MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(MODULE_DIR)
RAPID_CONFIG_FILE = os.path.join(PROJECT_ROOT, "config", "rapid_api.json")

def load_rapid_config():
    """Hàm đọc cấu hình RapidAPI từ file JSON"""
    if not os.path.exists(RAPID_CONFIG_FILE):
        return {}
    try:
        with open(RAPID_CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

# --- [MỚI] HÀM NÉN VIDEO ---
def compress_video_if_needed(input_path, limit_mb=20):
    """
    Kiểm tra dung lượng file. Nếu > limit_mb thì nén lại.
    Trả về đường dẫn file nén (hoặc file gốc nếu không cần nén).
    """
    try:
        if not os.path.exists(input_path): return None

        file_size_mb = os.path.getsize(input_path) / (1024 * 1024)

        # Nếu file nhỏ hơn giới hạn thì dùng luôn file gốc
        if file_size_mb < limit_mb:
            print(f"   ✅ File nhẹ ({file_size_mb:.2f} MB). Không cần nén.")
            return input_path

        print(f"   ⚠️ File nặng ({file_size_mb:.2f} MB). Đang nén xuống < {limit_mb}MB cho AI Studio...")

        # Tạo tên file nén
        dir_name = os.path.dirname(input_path)
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        output_path = os.path.join(dir_name, f"{base_name}_small.mp4")

        # Lệnh FFmpeg nén: Giảm độ phân giải về 720p, CRF 28 (giảm chất lượng nhẹ), Preset veryfast
        # -fs 19M: Cố gắng giới hạn file ở mức 19MB (gần 20MB)
        cmd = [
            'ffmpeg', '-y', '-i', input_path,
            '-vf', 'scale=-2:720', # Resize về HD 720p để giảm nhẹ dung lượng
            '-c:v', 'libx264', '-crf', '28', '-preset', 'veryfast', # Nén mạnh
            '-c:a', 'aac', '-b:a', '64k', # Giảm bitrate audio
            '-fs', f'{int(limit_mb * 1024 * 1024)}', # Cắt nếu vượt quá dung lượng (Hard limit)
            output_path
        ]

        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        if os.path.exists(output_path):
            new_size = os.path.getsize(output_path) / (1024 * 1024)
            print(f"   🎉 Nén xong: {new_size:.2f} MB. Saved: {os.path.basename(output_path)}")
            return output_path
        else:
            print("   ❌ Lỗi nén file. Dùng tạm file gốc.")
            return input_path

    except Exception as e:
        print(f"   ❌ Lỗi Compression: {e}")
        return input_path

# --- PHẦN 1: CRAWLER (LẤY LINK VIDEO) ---

def get_videos_via_rapidapi(channel_url, limit=5):
    """Sử dụng RapidAPI quét danh sách video nếu yt-dlp thất bại"""
    config = load_rapid_config()
    try:
        if "@" in channel_url:
            username = channel_url.split('@')[-1].split('?')[0].strip('/')
        else:
            username = channel_url.split('/')[-1].split('?')[0]
    except: return []

    headers = {
        "x-rapidapi-key": config.get("keys", [""])[0],
        "x-rapidapi-host": config.get("host", "")
    }

    video_links = []
    try:
        url = "https://tiktok-downloader-download-tiktok-videos-without-watermark.p.rapidapi.com/user/index"
        response = requests.get(url, headers=headers, params={"username": username}, timeout=20)
        data = response.json()

        if isinstance(data, dict):
            items = data.get("data", {}).get("videos", []) if "data" in data else data.get("videos", [])
            for item in items[:limit]:
                vid_id = item.get("video_id")
                if vid_id:
                    video_links.append(f"https://www.tiktok.com/@{username}/video/{vid_id}")
    except Exception as e:
        print(f"⚠️ RapidAPI Crawl Error: {e}")
    return video_links

def get_channel_videos(channel_url, limit=5):
    """Hàm tổng hợp lấy link video"""
    print(f"🔍 Đang quét kênh: {channel_url}")

    ydl_opts = {
        'quiet': True, 'extract_flat': True, 'playlistend': limit,
        'ignoreerrors': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    video_links = []
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(channel_url, download=False)
            if info and 'entries' in info:
                for e in info['entries']:
                    if e:
                        v_url = e.get('url') or e.get('webpage_url')
                        if v_url: video_links.append(v_url)
    except Exception as e:
        print(f"⚠️ yt-dlp Error: {e}")

    if not video_links:
        print("   ↳ yt-dlp thất bại, chuyển sang RapidAPI...")
        video_links = get_videos_via_rapidapi(channel_url, limit)

    return [v for v in video_links if v]

# --- PHẦN 2: DOWNLOADER (TẢI FILE) ---

def download_via_tikwm(url, save_path):
    try:
        api_url = "https://www.tikwm.com/api/"
        res = requests.post(api_url, data={'url': url, 'hd': 1}, timeout=15).json()
        if res.get('code') == 0:
            play_url = res['data']['play']
            if not play_url.startswith("http"):
                v_url = "https://www.tikwm.com" + play_url
            else:
                v_url = play_url

            with requests.get(v_url, stream=True) as r:
                with open(save_path, 'wb') as f:
                    shutil.copyfileobj(r.raw, f)
            return True
    except: return False

def download_via_rapidapi(tiktok_url, save_path):
    config = load_rapid_config()
    keys = config.get("keys", [])
    host = config.get("host", "")
    api_url = config.get("endpoint", "")

    for key in keys:
        if not key: continue
        try:
            resp = requests.get(api_url, headers={"x-rapidapi-key": key, "x-rapidapi-host": host}, params={"url": tiktok_url}, timeout=20)
            if resp.status_code != 200: continue

            result = resp.json()
            download_url = None
            if isinstance(result, dict):
                download_url = result.get("video_hd") or result.get("video") or result.get("play")
                if isinstance(download_url, list): download_url = download_url[0]

            if download_url:
                with requests.get(download_url, stream=True) as r:
                    with open(save_path, 'wb') as f: shutil.copyfileobj(r.raw, f)
                return True
        except: continue
    return False

def download_tiktok_video(url, temp_dir):
    """
    Hàm tải video.
    Trả về Dict: {'original': path_goc, 'ai_studio': path_nho}
    """
    if not os.path.exists(temp_dir): os.makedirs(temp_dir)

    try:
        video_id = url.split("video/")[1].split("?")[0]
    except:
        video_id = str(int(time.time()))

    timestamp = int(time.time())
    final_path = os.path.join(temp_dir, f"src_{video_id}_{timestamp}.mp4")

    print(f"   ⬇️ Downloading: {url}")
    downloaded = False

    # 1. Thử TikWM
    if download_via_tikwm(url, final_path): downloaded = True
    # 2. Thử RapidAPI
    elif download_via_rapidapi(url, final_path): downloaded = True
    # 3. Fallback yt-dlp
    else:
        try:
            ydl_opts = {'outtmpl': final_path, 'format': 'best', 'quiet': True, 'overwrites': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl: ydl.download([url])
            if os.path.exists(final_path): downloaded = True
        except Exception as e: print(f"   ❌ Lỗi yt-dlp: {e}")

    if downloaded and os.path.exists(final_path):
        # [NEW LOGIC] Xử lý nén file cho AI Studio
        compressed_path = compress_video_if_needed(final_path, limit_mb=20)

        # Trả về cả 2 đường dẫn để Scheduler tự chọn dùng cái nào
        return {
            "original": final_path,        # Dùng để Edit/Remix (Full chất lượng)
            "ai_studio": compressed_path   # Dùng để upload AI Studio (<20MB)
        }

    return None