import os
import requests

SERVER_URL = "http://127.0.0.1:8000/v1/generate"

def create_voice_default(text, save_dir, filename):
    save_path = os.path.join(save_dir, filename)
    payload = {
        "text": text,
        "save_path": save_path
    }

    try:
        print(f"   ⏳ Đang gửi yêu cầu đọc giọng mặc định...")
        # Tăng timeout lên 600s (10 phút) vì giờ Server xử lý nguyên 1 bài báo
        res = requests.post(SERVER_URL, json=payload, timeout=600)
        if res.status_code == 200 and res.json().get("status") == "success":
            return save_path
        else:
            print(f"   ❌ Server báo lỗi: {res.json().get('message')}")
    except Exception as e:
        print(f"   ❌ Lỗi kết nối TTS Server: {e}")
    return None

def create_voice_clone(text, ref_audio_path, ref_text, save_dir, filename):
    save_path = os.path.join(save_dir, filename)
    payload = {
        "text": text,
        "ref_audio_path": ref_audio_path,
        "ref_text": ref_text,
        "save_path": save_path
    }

    try:
        print(f"   🚀 Đang gửi nguyên bài báo sang Server để Clone giọng...")
        # Tăng timeout để tránh lỗi đứt kết nối khi bài quá dài
        res = requests.post(SERVER_URL, json=payload, timeout=600)
        data = res.json()

        if res.status_code == 200 and data.get("status") == "success":
            print("   🔗 Đã nhận file Audio hoàn hảo từ Server!")
            return save_path
        else:
            print(f"   ❌ Lỗi từ Server: {data.get('message')}")
    except Exception as e:
        print(f"   ❌ Lỗi kết nối TTS Server: {e}")
    return None

if __name__ == "__main__":
    # Xác định đường dẫn gốc
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    OUTPUT_DIR = os.path.join(BASE_DIR, 'assets', 'temp_voice')

    # Tạo thư mục chứa nếu chưa tồn tại
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # --- CẤU HÌNH BÀI TEST ---
    # 1. Đường dẫn file giọng mẫu (Bắt buộc phải có file này trong thư mục temp_voice)
    file_mau = os.path.join(OUTPUT_DIR, "example_ngoc_huyen.wav")

    # 2. Text mẫu (Bắt buộc PHẢI KHỚP 100% với những gì bạn đọc trong file_mau)
    text_mau = "Tác phẩm dự thi bảo đảm tính khoa học, tính đảng, tính chiến đấu, tính định hướng."

    # 3. Nội dung cần AI đọc (Cố tình cho dài một chút để test độ mượt)
    noi_dung_can_doc = "Xin chào, đây là bài kiểm tra hệ thống đọc tự động. Hệ thống đã được nâng cấp lên phiên bản bất tử, tự động băm nhỏ văn bản và ghép nối mượt mà không bao giờ sợ lỗi."

    ten_file_xuat = "a.wav"

    print("=== BẮT ĐẦU KIỂM TRA MÁY KHÁCH GỌI MÁY CHỦ ===")

    # Kiểm tra an toàn trước khi gọi
    if not os.path.exists(file_mau):
        print(f"⚠️ CẢNH BÁO: Không tìm thấy file giọng mẫu tại: {file_mau}")
        print("💡 Hãy copy file voice.wav của bạn vào thư mục trên rồi chạy lại nhé!")
    else:
        print(f"✅ Đã tìm thấy file mẫu: {file_mau}")
        print(f"📖 Text mẫu: {text_mau}")
        print(f"📝 Nội dung cần đọc: {noi_dung_can_doc}\n")

        # Gọi hàm
        kq = create_voice_clone(
            text=noi_dung_can_doc,
            ref_audio_path=file_mau,
            ref_text=text_mau,
            save_dir=OUTPUT_DIR,
            filename=ten_file_xuat
        )

        if kq:
            print(f"\n🎉 QUÁ ĐỈNH! Máy chủ đã trả file về thành công tại:\n👉 {kq}")
            print("Bạn có thể mở file này lên để nghe thử chất lượng ngay lập tức!")
        else:
            print("\n❌ TEST THẤT BẠI! Vui lòng mở cửa sổ Terminal đang chạy tts_server.py lên xem nó in ra dòng chữ màu đỏ gì nhé.")