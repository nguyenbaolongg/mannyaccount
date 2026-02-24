import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow

# ================= CẤU HÌNH ĐƯỜNG DẪN =================
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(PROJECT_ROOT, "config")

CREDENTIALS_FILE = os.path.join(CONFIG_DIR, 'credentials.json')
TOKEN_PICKLE = os.path.join(CONFIG_DIR, 'token.pickle')
TOKEN_JSON = os.path.join(CONFIG_DIR, 'token.json')

# Quyền truy cập Drive (Giống hệt trong file upload_drive.py của bạn)
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def force_relogin():
    print("🧹 BƯỚC 1: Đang dọn dẹp bộ nhớ đăng nhập cũ...")

    # 1. Xóa các file token cũ (nếu có) để ép hệ thống quên tài khoản cũ đi
    for token_file in [TOKEN_PICKLE, TOKEN_JSON]:
        if os.path.exists(token_file):
            try:
                os.remove(token_file)
                print(f"   🗑️ Đã xóa phiên đăng nhập cũ: {os.path.basename(token_file)}")
            except Exception as e:
                print(f"   ⚠️ Không thể xóa {token_file}: {e}")

    # 2. Kiểm tra xem file credentials.json đã đúng vị trí chưa
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"\n❌ LỖI: Không tìm thấy file {CREDENTIALS_FILE}!")
        print("👉 Hãy đảm bảo file credentials.json đã được đặt đúng trong thư mục 'config'.")
        return

    print("\n🌐 BƯỚC 2: Đang mở trình duyệt để yêu cầu cấp quyền mới...")
    print("⚠️  LƯU Ý QUAN TRỌNG: Hãy chọn ĐÚNG tài khoản Gmail đang sở hữu thư mục Drive cần lưu video nhé!")

    try:
        # 3. Khởi tạo luồng xác thực mới (Sẽ tự động mở tab mới trên Chrome)
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
        creds = flow.run_local_server(port=0)

        # 4. Lưu lại token mới sau khi bạn bấm "Cho phép" trên trình duyệt
        with open(TOKEN_PICKLE, 'wb') as token:
            pickle.dump(creds, token)

        print("\n✅ XÁC THỰC THÀNH CÔNG! Đã lưu token mới.")
        print("🎉 Bây giờ bạn có thể tắt file này và chạy lại tool chính được rồi.")

    except Exception as e:
        print(f"\n❌ Có lỗi xảy ra trong quá trình xác thực: {e}")

if __name__ == '__main__':
    force_relogin()