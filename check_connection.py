#!/usr/bin/env python3
"""
Kịch bản kiểm tra kết nối API tới hệ thống Voicebox Studio (Local & Remote).
Hỗ trợ kiểm tra độ trễ, mã trạng thái HTTP, và tính hợp lệ của file âm thanh phản hồi.
"""

import os
import sys
import time
import argparse
import requests

# Màu sắc hiển thị terminal
GREEN = '\033[0;32m'
BLUE = '\033[0;34m'
YELLOW = '\033[1;33m'
RED = '\033[0;31m'
NC = '\033[0m' # No Color

def check_connection(server_url, text, voice_id="75b59968-5d03-4f45-ad03-45dc7d01e95e", speed=1.15):
    print(f"\n{BLUE}===================================================================={NC}")
    print(f"{GREEN}       KIỂM TRA KẾT NỐI API VOICEBOX STUDIO (EXTERNAL TTS){NC}")
    print(f"{BLUE}===================================================================={NC}")
    print(f"🔗 {YELLOW}URL đích:{NC} {server_url}")
    print(f"📝 {YELLOW}Nội dung:{NC} '{text}'")
    print(f"⚙️  {YELLOW}Cấu hình:{NC} Voice ID: {voice_id} | Tốc độ: {speed}\n")

    payload = {
        "text": text,
        "voice_id": voice_id,
        "language": "vi",
        "speed": speed
    }

    # Thư mục lưu file kiểm tra
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(base_dir, 'assets', 'temp_voice')
    os.makedirs(output_dir, exist_ok=True)
    save_path = os.path.join(output_dir, 'connection_test_result.wav')

    start_time = time.time()
    try:
        print(f"⏳ Đang gửi yêu cầu tới Server... (Vui lòng chờ)")
        res = requests.post(server_url, json=payload, timeout=60)
        elapsed_time = time.time() - start_time

        print(f"⏱️  Thời gian phản hồi: {elapsed_time:.2f} giây")
        print(f"🏷️  Mã trạng thái HTTP: {res.status_code}")

        if res.status_code == 200:
            # Kiểm tra content-type
            content_type = res.headers.get('Content-Type', '')
            print(f"📦 Kiểu dữ liệu nhận được: {content_type}")

            with open(save_path, "wb") as f:
                f.write(res.content)
            
            file_size_kb = os.path.getsize(save_path) / 1024
            print(f"💾 Dung lượng file: {file_size_kb:.2f} KB")

            if file_size_kb > 1.0: # File hợp lệ thường lớn hơn 1KB
                print(f"\n{GREEN}🎉 THÀNH CÔNG! HỆ THỐNG HOẠT ĐỘNG HOÀN HẢO!{NC}")
                print(f"👉 File âm thanh đã được lưu tại:\n   {save_path}\n")
                return True
            else:
                print(f"\n{RED}❌ CẢNH BÁO: File âm thanh nhận được quá nhỏ (có thể bị lỗi rỗng).{NC}\n")
                return False
        else:
            print(f"\n{RED}❌ THẤT BẠI: Server trả về lỗi!{NC}")
            print(f"Chi tiết lỗi từ Server: {res.text}\n")
            
            # Hướng dẫn khắc phục nhanh
            if res.status_code == 500:
                print(f"{YELLOW}💡 Gợi ý khắc phục:{NC} Kiểm tra log phía Server (backend.main). Có thể do thiếu module hoặc lỗi xử lý audio.")
            elif res.status_code == 404:
                print(f"{YELLOW}💡 Gợi ý khắc phục:{NC} Kiểm tra lại đường dẫn URL hoặc Voice ID '{voice_id}' có tồn tại trên Server hay không.")
            elif res.status_code in (502, 503, 504):
                print(f"{YELLOW}💡 Gợi ý khắc phục:{NC} Máy chủ đang quá tải hoặc cấu hình Nginx/Proxy chuyển tiếp chưa chính xác.")
            return False

    except requests.exceptions.ConnectionError:
        print(f"\n{RED}❌ THẤT BẠI: Không thể kết nối tới máy chủ!{NC}")
        print(f"{YELLOW}💡 Gợi ý khắc phục:{NC}")
        print(f"  1. Nếu dùng Localhost (127.0.0.1): Đảm bảo dịch vụ Voicebox đang chạy ở cổng 8080.")
        print(f"  2. Nếu dùng Tên miền/IP từ xa: Kiểm tra lại tường lửa (ufw allow 8080), đường truyền mạng hoặc cấu hình Port Forwarding/Nginx.\n")
        return False
    except requests.exceptions.Timeout:
        print(f"\n{RED}❌ THẤT BẠI: Kết nối bị quá giờ (Timeout)!{NC}")
        print(f"{YELLOW}💡 Gợi ý khắc phục:{NC} Máy chủ mất quá nhiều thời gian để xử lý. Hãy kiểm tra xem GPU/CPU phía Server có bị treo không.\n")
        return False
    except Exception as e:
        print(f"\n{RED}❌ THẤT BẠI: Lỗi không xác định: {e}{NC}\n")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Kiểm tra kết nối API Voicebox Studio.")
    parser.add_argument(
        "--url", 
        type=str, 
        default="http://127.0.0.1:8080/api/external/tts",
        help="URL của endpoint API (Mặc định: http://127.0.0.1:8080/api/external/tts)"
    )
    parser.add_argument(
        "--remote", 
        action="store_true", 
        help="Sử dụng URL miền từ xa mặc định (https://voice.adsup.vn/api/external/tts)"
    )
    parser.add_argument(
        "--text", 
        type=str, 
        default="Chào bạn, đây là luồng kiểm tra kết nối API tự động đến hệ thống Voicebox Studio.",
        help="Nội dung văn bản cần đọc thử"
    )
    parser.add_argument(
        "--voice", 
        type=str, 
        default="75b59968-5d03-4f45-ad03-45dc7d01e95e",
        help="Voice ID hoặc tên Profile (Mặc định: 75b59968-5d03-4f45-ad03-45dc7d01e95e)"
    )
    parser.add_argument(
        "--speed", 
        type=float, 
        default=1.15,
        help="Tốc độ đọc (Mặc định: 1.15)"
    )

    args = parser.parse_args()

    # Nếu người dùng chọn flag --remote, tự động chuyển sang domain
    target_url = "https://voice.adsup.vn/api/external/tts" if args.remote else args.url

    check_connection(
        server_url=target_url,
        text=args.text,
        voice_id=args.voice,
        speed=args.speed
    )
