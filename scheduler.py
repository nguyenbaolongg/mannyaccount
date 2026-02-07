import os
import time
import subprocess
import json
from datetime import datetime
import sys # [QUAN TRỌNG] Để lấy đường dẫn python hiện tại

def get_active_account_ids():
    ids = []
    path = os.path.join("config", "accounts")
    if os.path.exists(path):
        for f in os.listdir(path):
            if f.endswith(".json"): ids.append(f.replace(".json", ""))
    return ids

def load_schedule():
    path = os.path.join("config", "schedule_config.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return {"crawl_times": []}

def main():
    print("==================================================")
    print(f"🤖 MATRIX SCHEDULER: Đang chạy với Python: {sys.executable}")
    print("==================================================")

    running_procs = {}
    last_trigger = ""
    wait_counter = 0

    while True:
        try:
            now = datetime.now().strftime("%H:%M")
            schedule = load_schedule()
            crawl_times = schedule.get("crawl_times", [])

            # === KÍCH HOẠT ===
            if now in crawl_times and now != last_trigger:
                print(f"\n⚡ [{now}] PHÁT HIỆN LỊCH CHẠY! BẮT ĐẦU KÍCH HOẠT...")
                last_trigger = now

                accs = get_active_account_ids()
                for acc_id in accs:
                    if acc_id not in running_procs:
                        print(f"   🚀 [SPAWN] Khởi động Worker: {acc_id}")

                        # [SỬA QUAN TRỌNG] Dùng sys.executable thay vì "python"
                        # Để đảm bảo Worker dùng đúng môi trường ảo có thư viện requests
                        worker_path = os.path.join("core", "worker.py")
                        cmd = [sys.executable, worker_path, acc_id]

                        p = subprocess.Popen(cmd)
                        running_procs[acc_id] = p

                        time.sleep(5)

                        # === DỌN DẸP ===
            finished = []
            for acc, p in running_procs.items():
                if p.poll() is not None:
                    print(f"   ✅ Worker {acc} đã hoàn thành.")
                    finished.append(acc)

            for acc in finished:
                del running_procs[acc]

            # === LOG ===
            if wait_counter % 10 == 0:
                print(f"⏳ [{now}] Đang chờ... (Active workers: {len(running_procs)})")

            wait_counter += 1
            time.sleep(1)

        except KeyboardInterrupt:
            print("\n🛑 Đã dừng thủ công.")
            break
        except Exception as e:
            print(f"❌ Lỗi Scheduler: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()