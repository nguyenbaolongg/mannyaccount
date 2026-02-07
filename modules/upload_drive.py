import os
import pickle
import requests  # <--- THÊM THƯ VIỆN NÀY
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.http import MediaFileUpload

# ================= CẤU HÌNH ĐƯỜNG DẪN =================
CURRENT_FILE_PATH = os.path.abspath(__file__)
MODULES_DIR = os.path.dirname(CURRENT_FILE_PATH)
PROJECT_ROOT = os.path.dirname(MODULES_DIR)
CONFIG_DIR  = os.path.join(PROJECT_ROOT, "config")

# Đường dẫn file credentials và token bên trong folder config
CREDENTIALS_FILE = os.path.join(CONFIG_DIR, 'credentials.json')
TOKEN_FILE = os.path.join(CONFIG_DIR, 'token.pickle')
if not os.path.exists(CONFIG_DIR):
    os.makedirs(CONFIG_DIR)
# ======================================================

SCOPES = ['https://www.googleapis.com/auth/drive.file']

# ======================================================
# 1. HÀM XÁC THỰC GOOGLE DRIVE
# ======================================================
def authenticate_google_drive():
    """Xử lý đăng nhập và lưu token"""
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                print(f"❌ Lỗi: Không tìm thấy file tại: {CREDENTIALS_FILE}")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)

    return build('drive', 'v3', credentials=creds)

# ======================================================
# 2. HÀM UPLOAD VIDEO
# ======================================================
def upload_video_to_drive(file_path, folder_id=None):
    """Hàm upload video lên Drive và trả về Link"""
    service = authenticate_google_drive()
    if not service: return None

    if not os.path.exists(file_path):
        print(f"❌ Không tìm thấy file video: {file_path}")
        return None

    file_name = os.path.basename(file_path)
    print(f"🚀 Đang chuẩn bị upload: {file_name}...")

    file_metadata = {'name': file_name}
    if folder_id:
        file_metadata['parents'] = [folder_id]

    media = MediaFileUpload(file_path, mimetype='video/mp4', resumable=True)

    try:
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()

        link = file.get('webViewLink')
        print(f"✅ Upload thành công!")
        print(f"🔗 Link Drive: {link}")
        return link

    except Exception as e:
        print(f"❌ Có lỗi khi upload: {e}")
        return None

# ======================================================
# 3. [MỚI] HÀM CẬP NHẬT LINK LÊN GOOGLE SHEET
# ======================================================
def update_sheet_drive_link(script_url, row_index, drive_link, tiktok_id=None):
    """Gửi request cập nhật cột J (Link) và Cột I (TikTok ID)"""
    if not script_url:
        print("⚠️ Chưa cấu hình SCRIPT_URL.")
        return

    print(f"🔄 Đang cập nhật Sheet dòng {row_index} (ID: {tiktok_id})...")

    payload = {
        "action": "update_file_path",
        "row": row_index,
        "file_path": drive_link,
        "tiktok_id": tiktok_id # [MỚI] Gửi thêm ID
    }

    try:
        response = requests.post(script_url, json=payload)
        if response.status_code == 200:
            print("✅ Đã cập nhật Sheet thành công!")
        else:
            print(f"⚠️ Lỗi cập nhật Sheet: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Lỗi kết nối Apps Script: {e}")

# ================= CHẠY THỬ =================
if __name__ == '__main__':
    # 1. CẤU HÌNH TEST
    MY_VIDEO = r"C:\Users\Acer\Videos\viral_44.mp4"
    FOLDER_ID = "1VgkkbUJ82kxzWXJH8cfn7UFMMFBKQkzS" # ID thư mục Drive

    # 👇 ĐIỀN URL APPS SCRIPT CỦA BẠN VÀO ĐÂY
    SCRIPT_URL = "https://script.google.com/macros/s/AKfycbx.../exec"

    # 👇 ĐIỀN SỐ DÒNG MUỐN UPDATE (Ví dụ dòng 2)
    ROW_INDEX = 2

    # 2. TẠO FILE GIẢ NẾU CẦN
    if not os.path.exists(MY_VIDEO):
        with open(MY_VIDEO, "w") as f: f.write("Test content")

    # 3. THỰC HIỆN UPLOAD
    drive_link = upload_video_to_drive(MY_VIDEO, FOLDER_ID)

    # 4. NẾU CÓ LINK -> UPDATE SHEET
    if drive_link:
        update_sheet_drive_link(SCRIPT_URL, ROW_INDEX, drive_link)