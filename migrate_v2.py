import json
import os

# Đường dẫn file gốc
OLD_ACC_FILE = "config/tiktok_accounts.json"
OLD_RENDER_FILE = "config/render_config.json"
# Đường dẫn đích
NEW_CONFIG_DIR = "config/accounts"
DATA_DIR = "data"

def migrate():
    print("🚀 Đang chuyển đổi dữ liệu sang kiến trúc Multi-Process...")

    if not os.path.exists(NEW_CONFIG_DIR): os.makedirs(NEW_CONFIG_DIR)

    # 1. Đọc dữ liệu cũ
    try:
        with open(OLD_ACC_FILE, "r", encoding="utf-8") as f:
            acc_list = json.load(f).get("accounts", [])
        with open(OLD_RENDER_FILE, "r", encoding="utf-8") as f:
            render_list = json.load(f)
    except Exception as e:
        print(f"❌ Lỗi đọc file config cũ: {e}")
        return

    # 2. Xử lý từng tài khoản
    for acc in acc_list:
        tid = acc.get("tiktok_id")
        if not tid: continue

        # ID dùng để đặt tên folder/file (bỏ @)
        clean_id = tid.replace("@", "").strip()

        # --- GOM CẤU HÌNH RENDER CỦA NICK NÀY ---
        my_channels = []
        for r in render_list:
            if r.get("tiktok_id") == tid:
                # Tạo object kênh kèm setting riêng
                my_channels.append({
                    "url": r.get("channel_url"),
                    "limit": 3, # Mặc định 3 video/kênh
                    # Nhúng thẳng setting render vào đây để Worker dễ lấy
                    "render_settings": {
                        "title_settings": r.get("title_settings", {}),
                        "content_settings": r.get("content_settings", {}),
                        "text_overlay_settings": r.get("text_overlay_settings", {}),
                        "text_content_settings": r.get("text_content_settings", {}),
                        "assets": r.get("assets", {})
                    }
                })

        if not my_channels:
            print(f"⚠️ Nick {tid} chưa có cấu hình render nào. Bỏ qua.")
            continue

        # Tạo nội dung file config mới
        new_config = {
            "id": clean_id,
            "tiktok_id": tid,
            "email": acc.get("email"),
            "chrome_profile": acc.get("chrome_profile"),
            "video_limit_per_run": 3,
            "channels": my_channels # List kênh nguồn + cách render tương ứng
        }

        # Lưu file config riêng: config/accounts/empowercongdongthammy20.json
        with open(f"{NEW_CONFIG_DIR}/{clean_id}.json", "w", encoding="utf-8") as f:
            json.dump(new_config, f, indent=4, ensure_ascii=False)

        # Tạo cấu trúc thư mục dữ liệu riêng (QUAN TRỌNG ĐỂ KHÔNG XUNG ĐỘT)
        user_data_path = f"{DATA_DIR}/{clean_id}"
        os.makedirs(f"{user_data_path}/temp", exist_ok=True)

        # Tạo file state.json nếu chưa có
        if not os.path.exists(f"{user_data_path}/state.json"):
            with open(f"{user_data_path}/state.json", "w", encoding="utf-8") as f:
                json.dump({"crawled_videos": [], "history": []}, f)

        print(f"✅ Đã tạo môi trường cho: {tid} ({len(my_channels)} kênh nguồn)")

if __name__ == "__main__":
    migrate()