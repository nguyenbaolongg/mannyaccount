import streamlit.web.cli as stcli
import os
import sys

def resolve_path(path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, path)
    return os.path.join(os.path.abspath("."), path)
if __name__ == "__main__":
    print("🚀 [SYSTEM] Đang khởi động Giao diện Web (Streamlit)...")

    # 1. Cấu hình chạy Streamlit
    # Trỏ thẳng vào file giao diện chính (app.py)
    app_path = resolve_path("app.py")

    if not os.path.exists(app_path):
        print(f"❌ [ERROR] Không tìm thấy file giao diện tại: {app_path}")
        sys.exit(1)

    sys.argv = [
        "streamlit",
        "run",
        app_path,
        "--global.developmentMode=false",
    ]

    # 2. Chạy Streamlit
    sys.exit(stcli.main())