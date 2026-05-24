import os
import requests

# Đảm bảo bạn đang bật server Voicebox ở cổng 8080
SERVER_URL = "http://127.0.0.1:8080/api/external/tts"

def generate_base_voice(text, save_dir, filename, engine="viterbox"):
    """
    Hàm gọi API Voicebox để sinh giọng đọc GỐC (Base Voice - chưa qua RVC).
    Bằng cách truyền thẳng tên engine (viterbox, vieneu...) vào 'voice_id', 
    server sẽ nhận diện đây không phải là một profile (có RVC) mà chỉ là engine TTS,
    từ đó trả về giọng đọc gốc chưa bị thay đổi qua model RVC.
    """
    save_path = os.path.join(save_dir, filename)
    os.makedirs(save_dir, exist_ok=True)
    
    payload = {
        "text": text,
        "voice_id": engine, # Truyền trực tiếp tên engine để bypass luồng RVC
        "language": "vi",
        "speed": 1.0
    }

    try:
        print(f"🚀 Đang gửi yêu cầu sinh giọng GỐC (Engine: {engine}) cho: '{text[:30]}...'")
        res = requests.post(SERVER_URL, json=payload, timeout=1800)
        
        if res.status_code == 200:
            with open(save_path, "wb") as f:
                f.write(res.content)
            print(f"   ✅ Thành công! File giọng gốc lưu tại: {save_path}")
            return save_path
        else:
            print(f"   ❌ Server báo lỗi ({res.status_code}): {res.text}")
            
    except Exception as e:
        print(f"   ❌ Lỗi kết nối Voicebox Server: {e}")
        
    return None

if __name__ == "__main__":
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    OUTPUT_DIR = os.path.join(BASE_DIR, 'assets', 'temp_voice')
    
    noi_dung_can_doc = "Chào bạn, đây là bài kiểm tra giọng đọc gốc, âm thanh này hoàn toàn chưa đi qua bộ lọc RVC."
    ten_file_xuat = "test_base_voice_no_rvc.wav"

    print("=== BẮT ĐẦU KIỂM TRA GIỌNG ĐỌC GỐC (BASE VOICE) ===")
    print(f"📝 Nội dung cần đọc: {noi_dung_can_doc}\n")

    kq = generate_base_voice(
        text=noi_dung_can_doc,
        save_dir=OUTPUT_DIR,
        filename=ten_file_xuat,
        engine="viterbox"  # Bạn có thể đổi thành "vieneu" nếu muốn test engine base khác
    )
    
    if kq:
        print(f"\n🎉 HOÀN TẤT! File gốc (không RVC) nằm ở:\n👉 {kq}")
    else:
        print("\n❌ THẤT BẠI! Hãy chắc chắn server Voicebox (port 8080) đang hoạt động.")
