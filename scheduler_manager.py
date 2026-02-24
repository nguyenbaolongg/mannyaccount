import os
import sys
import time
import json
import subprocess
from datetime import datetime

# Import API kết nối với Supabase
from services.supabase_api import SupabaseAPI

# ================= CẤU HÌNH HỆ THỐNG =================
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(PROJECT_ROOT, "config")
SCHEDULE_FILE = os.path.join(CONFIG_DIR, "schedule_config.json")

# [QUAN TRỌNG] Số lượng tài khoản chạy cùng một lúc
MAX_CONCURRENT_WORKERS = 10

def load_json(path):
    if not os.path.exists(path): return {}
    try:
        with open(path, "r", encoding="utf-8") as f: return json.load(f)
    except: return {}

def get_active_accounts():
    accounts = SupabaseAPI.get_all_active_accounts()

    active_ids = []
    for acc in accounts:
        if acc.get("active"):
            acc_id = acc.get("tiktok_id")
            if acc_id:
                active_ids.append(acc_id)

    return active_ids

def run_worker_batch(account_ids):
    """Chạy một nhóm worker song song"""
    processes = []
    print(f"   🚀 Đang khởi động {len(account_ids)} luồng song song...")

    for acc_id in account_ids:
        worker_script = os.path.join(PROJECT_ROOT, "core", "worker.py")
        cmd = [sys.executable, worker_script, acc_id]

        try:
            p = subprocess.Popen(cmd, cwd=PROJECT_ROOT)
            processes.append((acc_id, p))
            print(f"      ▶️  Đã kích hoạt: {acc_id} (PID: {p.pid})")
        except Exception as e:
            print(f"      ❌ Lỗi kích hoạt {acc_id}: {e}")

    print(f"   ⏳ Đang chờ {len(processes)} luồng hoàn tất xử lý...")

    finished_count = 0
    total = len(processes)

    while finished_count < total:
        time.sleep(2)
        finished_count = 0
        for acc_id, p in processes:
            if p.poll() is not None:
                finished_count += 1

    print(f"   ✅ Đợt chạy này đã hoàn tất (100%).")

def start_schedule_loop():
    print("="*60)
    print(f"🤖 MATRIX SCHEDULER - SUPABASE MODE")
    print(f"📂 Root: {PROJECT_ROOT}")
    print(f"⚡ Max Concurrent: {MAX_CONCURRENT_WORKERS}")
    print("="*60)

    last_run_time = ""

    while True:
        try:
            now = datetime.now()
            current_hhmm = now.strftime("%H:%M")

            sch_config = load_json(SCHEDULE_FILE)
            crawl_times = sch_config.get("crawl_times", [])

            if current_hhmm in crawl_times and current_hhmm != last_run_time:
                print(f"\n⏰ [TRIGGER] Đã đến giờ chạy: {current_hhmm}")
                last_run_time = current_hhmm

                active_ids = get_active_accounts()

                if not active_ids:
                    print("   ⚠️ Không có tài khoản nào đang Active trên Supabase.")
                else:
                    print(f"   📋 Danh sách chạy: {active_ids}")

                    total_accs = len(active_ids)
                    for i in range(0, total_accs, MAX_CONCURRENT_WORKERS):
                        batch = active_ids[i : i + MAX_CONCURRENT_WORKERS]
                        print(f"\n   📦 [BATCH] Chạy nhóm {i//MAX_CONCURRENT_WORKERS + 1}: {batch}")

                        run_worker_batch(batch)

                        if i + MAX_CONCURRENT_WORKERS < total_accs:
                            print("   💤 Nghỉ 10s trước khi chạy nhóm tiếp theo...")
                            time.sleep(10)

                print(f"\n🏁 [SESSION DONE] Đã chạy xong lịch trình {current_hhmm}")

            if now.second % 30 == 0:
                print(f"⏳ [{current_hhmm}] Đang chờ lịch... {crawl_times}", end="\r")

            time.sleep(1)

        except KeyboardInterrupt:
            print("\n🛑 Đã dừng thủ công.")
            break
        except Exception as e:
            print(f"\n❌ Lỗi Scheduler Main Loop: {e}")
            time.sleep(5)

if __name__ == "__main__":
    start_schedule_loop()