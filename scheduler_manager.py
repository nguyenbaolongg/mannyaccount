import json
import os
import sys
import time
import random
from datetime import datetime, timedelta
import threading
from services.sheet_api import get_last_row_index
# ================= CẤU HÌNH PATH =================
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.append(PROJECT_ROOT)

try:
    from run_viral_bot import (
        get_channel_videos, download_tiktok_video, process_viral_row,
        update_channel_last_video, SHEET_URL
    )
    from modules.ai_studio_uploader import run_ai_studio_uploader
    from modules.nurture_process.nurture_process import start_nurturing
except ImportError as e:
    print(f"❌ [SCHEDULER] Lỗi Import: {e}")
    sys.exit(1)

TEMP_VIDEO_DIR = os.path.join(PROJECT_ROOT, "assets", "temp_downloads")
CONFIG_FILE = os.path.join(PROJECT_ROOT, "config", "schedule_config.json")
CHANNELS_FILE = os.path.join(PROJECT_ROOT, "config", "channels_tracking.json")
ACCOUNTS_FILE = os.path.join(PROJECT_ROOT, "config", "tiktok_accounts.json")
SESSION_FILE = os.path.join(PROJECT_ROOT, "config", "session_config.json")

def load_json_live(path):
    if not os.path.exists(path): return {}
    try:
        with open(path, "r", encoding="utf-8") as f: return json.load(f)
    except: return {}

def save_accounts_current_index(index):
    data = load_json_live(ACCOUNTS_FILE)
    if data:
        data["current_index"] = index
        with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

class SchedulerManager:
    def __init__(self):
        self.last_crawl_check = ""
        self.stop_event = threading.Event()
        self.is_nurturing_active = False

    def get_active_data(self):
        c_data = load_json_live(CHANNELS_FILE)
        raw_c = c_data if isinstance(c_data, list) else c_data.get("channels", [])
        active_channels = [c for c in raw_c if c.get("active")]

        a_data = load_json_live(ACCOUNTS_FILE)
        raw_a = a_data.get("accounts", [])
        active_accounts_indices = [i for i, a in enumerate(raw_a) if a.get("active")]

        s_data = load_json_live(SESSION_FILE)
        limit_per_acc = int(s_data.get("upload_limit", 3))

        return active_channels, active_accounts_indices, limit_per_acc, raw_a

    # ==================================================================
    # [NEW] LOGIC PHÂN BỔ ĐỀU (ROUND-ROBIN DISTRIBUTION)
    # ==================================================================
    def smart_crawl_and_process(self):
        if self.is_nurturing_active: return

        print(f"\n🚀 [EXECUTE] ĐÃ ĐẾN GIỜ ({datetime.now().strftime('%H:%M')})! Bắt đầu phân phối...")
        channels, acc_indices, limit, all_accounts = self.get_active_data()

        if not channels or not acc_indices:
            print("⚠️ Chưa chọn Kênh hoặc Tài khoản Active.")
            return

        print(f"📊 Cấu hình: {len(channels)} Nguồn | {len(acc_indices)} Nick | Limit: {limit} vid/nick")

        # ---------------------------------------------------------
        # BƯỚC 1: GOM VIDEO VÀO TỪNG RỔ RIÊNG (Grouping by Channel)
        # ---------------------------------------------------------
        # Cấu trúc: { "url_kenh_A": [vid1, vid2, ...], "url_kenh_B": [vid3, ...] }
        channel_pools = {}

        print(f"📥 Đang quét video...")
        for ch in channels:
            if self.stop_event.is_set(): break
            url = ch.get("channel_url")
            last_saved = ch.get("last_video_url", "")
            scan_limit = int(ch.get("scan_limit", 5))

            vids = get_channel_videos(url, limit=scan_limit)

            # Lọc video mới
            new_vids = []
            for v in vids:
                if v == last_saved: break
                new_vids.append({"video_url": v, "source_channel": ch})

            if new_vids:
                # Random thứ tự video trong chính kênh đó luôn
                random.shuffle(new_vids)
                channel_pools[url] = new_vids
                print(f"   + Kênh {url}: {len(new_vids)} video mới")

        if not channel_pools:
            print("✅ Không có video mới nào.")
            return

        # ---------------------------------------------------------
        # BƯỚC 2: PHÂN PHỐI CHO TỪNG USER (Round-Robin)
        # ---------------------------------------------------------
        # Tạo danh sách key kênh để lặp vòng tròn
        source_keys = list(channel_pools.keys())

        for acc_idx in acc_indices:
            if self.stop_event.is_set(): break

            current_acc = all_accounts[acc_idx]
            tiktok_id = current_acc.get("tiktok_id", "Unknown")
            print(f"\n👤 [USER] Phân bổ cho: {tiktok_id}")
            save_accounts_current_index(acc_idx)

            assigned_items = []

            # Logic lấy: Lần lượt lấy từ từng kênh nguồn để đảm bảo cân bằng
            # Random vị trí bắt đầu để không phải lúc nào cũng ưu tiên kênh đầu tiên
            start_index = random.randint(0, len(source_keys) - 1)

            attempts = 0
            while len(assigned_items) < limit:
                # Duyệt qua các kênh nguồn theo vòng tròn
                current_source_key = source_keys[start_index % len(source_keys)]

                # Nếu kênh này còn video
                if channel_pools[current_source_key]:
                    # Lấy 1 video ra (POP) -> Video này sẽ biến mất khỏi Pool -> Không trùng
                    item = channel_pools[current_source_key].pop(0)
                    assigned_items.append(item)

                start_index += 1
                attempts += 1

                # Điều kiện thoát nếu vét cạn hết tất cả các kênh mà vẫn chưa đủ limit
                if all(len(pool) == 0 for pool in channel_pools.values()):
                    print("   ⚠️ Hết sạch video trong tất cả các kênh nguồn.")
                    break
                # Break an toàn
                if attempts > limit * len(source_keys) * 2: break

            print(f"   🎯 Đã nhận {len(assigned_items)} video (Đều các kênh).")

            # ---------------------------------------------------------
            # BƯỚC 3: THỰC THI (UPLOAD)
            # ---------------------------------------------------------
            for item in assigned_items:
                if self.stop_event.is_set(): break
                vid_link = item["video_url"]
                src_info = item["source_channel"]
                src_url = src_info.get("channel_url")

                print(f"   ▶️ Xử lý: {vid_link} (Nguồn: {src_url})")

                local_path = download_tiktok_video(vid_link, TEMP_VIDEO_DIR)
                if local_path and os.path.exists(local_path["ai_studio"]) and os.path.exists(local_path["original"]) :
                    if run_ai_studio_uploader(local_path["ai_studio"]):
                        print("   ✅ Upload OK. Đợi xử lý...")
                        time.sleep(15)

                        row_idx = get_last_row_index(SHEET_URL)
                        if row_idx > 1:
                            # Truyền cả TikTok ID và Source URL để render đúng config
                            process_viral_row(row_idx, local_path["original"], src_url, current_tiktok_id=tiktok_id)

                        update_channel_last_video(src_url, vid_link)
                    else:
                        print("   ❌ Upload thất bại.")

                    try: os.remove(local_path)
                    except: pass

                    nap = random.randint(30, 60)
                    print(f"   💤 Nghỉ {nap}s...")
                    time.sleep(nap)
                else:
                    print("   ❌ Lỗi tải video.")

        print("🏁 [EXECUTE] Hoàn tất chu trình phân phối.")
        self.print_waiting_status()

    def nurture_routine(self, duration_minutes):
        self.is_nurturing_active = True
        print(f"\n🍵 [NURTURE] Nuôi nick {duration_minutes} phút...")
        try: start_nurturing(minutes=duration_minutes)
        except: pass
        self.is_nurturing_active = False
        print("🏁 [NURTURE] Xong.")
        self.print_waiting_status()

    def print_waiting_status(self):
        sch_config = load_json_live(CONFIG_FILE)
        crawl_times = sch_config.get("crawl_times", [])
        print(f"\n⏳ [WAITING] Hệ thống đang chạy ngầm...")
        print(f"   🕒 Lịch quét: {crawl_times}")

    def run_scheduler(self):
        print("="*50); print(f"⏰ HỆ THỐNG SCHEDULER (SMART DISTRIBUTION)"); print("="*50)
        self.print_waiting_status()

        while not self.stop_event.is_set():
            sch_config = load_json_live(CONFIG_FILE)
            crawl_times = sch_config.get("crawl_times", [])
            nurture_wins = sch_config.get("nurture_windows", [])

            now = datetime.now()
            cur_time = now.strftime("%H:%M")

            # Check Nuôi
            active_nurture = False
            for win in nurture_wins:
                try:
                    s = datetime.strptime(win["start"], "%H:%M").replace(year=now.year, month=now.month, day=now.day)
                    e = datetime.strptime(win["end"], "%H:%M").replace(year=now.year, month=now.month, day=now.day)
                    if s <= now <= e:
                        rem = int((e-now).total_seconds()/60)
                        if rem > 2: self.nurture_routine(rem); active_nurture = True; break
                except: pass

            if active_nurture: time.sleep(30); continue

            # Check Chạy
            if cur_time in crawl_times and cur_time != self.last_crawl_check:
                self.last_crawl_check = cur_time
                self.smart_crawl_and_process()

            time.sleep(30)

    def stop(self): self.stop_event.set()

if __name__ == "__main__":
    bot = SchedulerManager()
    try: bot.run_scheduler()
    except KeyboardInterrupt: bot.stop()