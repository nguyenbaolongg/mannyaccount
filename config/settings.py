import os
import sys
import json

# === 1. ĐỊNH NGHĨA ĐƯỜNG DẪN GỐC (PATH) ===
if getattr(sys, 'frozen', False):
    APP_PATH = os.path.dirname(sys.executable)
else:
    # Đi ngược lên 1 cấp vì file này nằm trong folder config
    APP_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# === 2. CÁC FOLDER CON (ASSETS) ===
SETTINGS_FILE = os.path.join(APP_PATH, "../user_settings.json")
UPLOAD_TEMP_DIR = os.path.join(APP_PATH, "assets", "User_Uploads")
IMAGE_ROOT_DIR = os.path.join(APP_PATH, "assets", "Downloaded_Images")
FRAME_DIR = os.path.join(APP_PATH, "assets", "frame")
LOGO_DIR = os.path.join(APP_PATH, "assets", "logo")
FONT_DIR = os.path.join(APP_PATH, "assets", "font")

# Tạo folder nếu chưa có
for folder in [UPLOAD_TEMP_DIR, IMAGE_ROOT_DIR, FRAME_DIR, LOGO_DIR, FONT_DIR]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# Đường dẫn file mẫu và font
TEMPLATE_FILE = os.path.join(FRAME_DIR, "fr.png")
FONT_NAME = os.path.join(FONT_DIR, "font.ttf")

VIDEO_RESOLUTIONS = {
    "1080x1920 (TikTok/Shorts)": (1080, 1920),
    "1920x1080 (Youtube)": (1920, 1080),
    "1080x1080 (Vuông)": (1080, 1080),
}

# === 3. HÀM LOAD/SAVE SETTINGS ===
def load_user_settings():
    """Đọc cấu hình từ file JSON, nếu không có thì trả về mặc định"""
    default = {
        "api_key": "",
        "sheet_url": "",
        "voice_id": "vi_female_kieunhi_mn"
    }

    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved_data = json.load(f)
                # Merge dữ liệu save vào default để tránh lỗi thiếu key
                return {**default, **saved_data}
        except:
            return default
    return default

def save_user_settings(api_key, sheet_url, voice_id):
    """Lưu cấu hình vào file JSON"""
    try:
        data = {
            "api_key": api_key,
            "sheet_url": sheet_url,
            "voice_id": voice_id
        }
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except:
        return False

# === 4. KHỞI TẠO GIÁ TRỊ MẶC ĐỊNH ===
# [SỬA QUAN TRỌNG] Đặt tên biến là LOADED_SETTINGS để các file khác import được
LOADED_SETTINGS = load_user_settings()

# Các biến này sẽ được sidebar.py import
API_KEY = LOADED_SETTINGS["api_key"]
DEFAULT_SHEET_URL = LOADED_SETTINGS["sheet_url"]
DEFAULT_VOICE_ID = LOADED_SETTINGS["voice_id"]