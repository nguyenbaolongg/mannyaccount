import sys
import os

# Thêm đường dẫn thư mục gốc vào hệ thống để Python tìm thấy các module con
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ui.auto_bot_ui import render_main_ui

if __name__ == "__main__":
    render_main_ui()