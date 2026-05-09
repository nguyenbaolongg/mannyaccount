import os
import requests

SERVER_URL = "http://127.0.0.1:8080/generate/full-pipeline"

def create_voice_full_pipeline(text, save_dir, filename, profile_id="viterbox", rvc_model="models/my_voice.pth", rvc_pitch=0, emotion="binh_thuong"):
    save_path = os.path.join(save_dir, filename)
    payload = {
        "text": text,
        "profile_id": profile_id,
        "run_rvc": True,
        "rvc_model_path": rvc_model,
        "rvc_pitch": rvc_pitch,
        "emotion": emotion,
        "language": "vi",
        "run_enhance": False
    }

    try:
        print(f"   🚀 Đang gửi yêu cầu Full Pipeline (TTS + RVC) cho: '{text[:30]}...'")
        # Timeout 300s vì RVC và TTS cộng lại có thể lâu
        res = requests.post(SERVER_URL, json=payload, timeout=300)
        
        if res.status_code == 200:
            with open(save_path, "wb") as f:
                f.write(res.content)
            print(f"   ✅ Thành công! File lưu tại: {save_path}")
            return save_path
        else:
            try:
                err_msg = res.json().get('message', res.text)
            except:
                err_msg = res.text
            print(f"   ❌ Server báo lỗi ({res.status_code}): {err_msg}")
    except Exception as e:
        print(f"   ❌ Lỗi kết nối Voicebox Server: {e}")
    return None

def create_voice_default(text, save_dir, filename):
    """Giữ nguyên tên hàm cũ nhưng chuyển sang gọi API mới với RVC=False nếu muốn tiết kiệm tài nguyên"""
    save_path = os.path.join(save_dir, filename)
    payload = {
        "text": text,
        "profile_id": "viterbox",
        "run_rvc": False, # Chỉ lấy TTS thô
        "rvc_model_path": "",
        "language": "vi",
        "rvc_index_path": "",
        "rvc_f0_method": "rmvpe",
        "run_enhance": False
    }

    try:
        print(f"   ⏳ Đang gửi yêu cầu đọc giọng TTS mặc định...")
        res = requests.post(SERVER_URL, json=payload, timeout=200)
        if res.status_code == 200:
            with open(save_path, "wb") as f:
                f.write(res.content)
            return save_path
        else:
            print(f"   ❌ Server báo lỗi: {res.status_code}")
    except Exception as e:
        print(f"   ❌ Lỗi kết nối TTS Server: {e}")
    return None

def create_voice_clone(text, ref_audio_path, ref_text, save_dir, filename):
    """
    Hàm này trước đây dùng để Clone kiểu cũ. 
    Bây giờ chuyển sang dùng Full Pipeline với model RVC mặc định.
    """
    return create_voice_full_pipeline(text, save_dir, filename)

if __name__ == "__main__":
    # Xác định đường dẫn gốc
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    OUTPUT_DIR = os.path.join(BASE_DIR, 'assets', 'temp_voice')

    # Tạo thư mục chứa nếu chưa tồn tại
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # --- CẤU HÌNH BÀI TEST ---
    noi_dung_can_doc = "Chào bạn, đây là bài kiểm tra kết nối hệ thống Voicebox Studio mới nhất. Hệ thống đang chạy Full Pipeline bao gồm cả TTS và RVC."
    ten_file_xuat = "test_voicebox.wav"

    print("=== BẮT ĐẦU KIỂM TRA MÁY KHÁCH GỌI MÁY CHỦ VOICEBOX STUDIO ===")
    print(f"📝 Nội dung cần đọc: {noi_dung_can_doc}\n")

    # Gọi hàm mới
    kq = create_voice_full_pipeline(
        text=noi_dung_can_doc,
        save_dir=OUTPUT_DIR,
        filename=ten_file_xuat,
        profile_id="viterbox",
        rvc_model="models/my_voice.pth", # Thay bằng model thực tế trên server của bạn
        rvc_pitch=0
    )

    if kq:
        print(f"\n🎉 THÀNH CÔNG! File đã được lưu tại:\n👉 {kq}")
    else:
        print("\n❌ THẤT BẠI! Vui lòng kiểm tra Server Voicebox Studio đang chạy ở cổng 8080.")