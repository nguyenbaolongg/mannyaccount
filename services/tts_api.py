import os
import requests

# Sử dụng chuẩn API mới từ xa
SERVER_URL = "http://127.0.0.1:8080/api/external/tts"

def create_voice_full_pipeline(text, save_dir, filename, profile_id="00529487-0a22-48b3-8617-26d3539f250f", rvc_model=None, rvc_pitch=0, emotion="binh_thuong", speed=1.15):
    """
    Hàm gọi API Voicebox mới (External API).
    """
    save_path = os.path.join(save_dir, filename)
    
    # Ưu tiên lấy voice_id từ rvc_model nếu nó là một UUID (không phải đường dẫn .pth mặc định và không phải mã cũ voice-xxx)
    voice_id_to_use = profile_id
    if rvc_model and ".pth" not in str(rvc_model) and rvc_model not in ["models/my_voice.pth", "1", "vi_female_kieunhi_mn"] and not str(rvc_model).startswith("voice-"):
        voice_id_to_use = str(rvc_model).strip()
        
    # Nếu voice_id_to_use đang là viterbox (hoặc tên tiktok, theanh28) do kịch bản cũ truyền vào, tự động ưu tiên dùng UUID của giọng mới
    if voice_id_to_use in ["viterbox", "tiktok", "theanh28"]:
        voice_id_to_use = "00529487-0a22-48b3-8617-26d3539f250f"
    
    payload = {
        "text": text,
        "voice_id": voice_id_to_use,
        "language": "vi",
        "speed": speed
    }

    try:
        print(f"   🚀 Đang gửi yêu cầu sinh giọng (Voice ID: {voice_id_to_use}) cho: '{text[:30]}...'", flush=True)
        res = requests.post(SERVER_URL, json=payload, timeout=1800)
        
        if res.status_code == 200:
            with open(save_path, "wb") as f:
                f.write(res.content)
            print(f"   ✅ Thành công! File lưu tại: {save_path}", flush=True)
            return save_path
        else:
            print(f"   ❌ Server báo lỗi ({res.status_code}): {res.text}", flush=True)
            # TỰ ĐỘNG FALLBACK VỀ UUID TIKTOK / VITERBOX NẾU VOICE ID KHÔNG TỒN TẠI
            if "not found" in res.text.lower() or res.status_code in (400, 404, 500):
                fallback_voice = "00529487-0a22-48b3-8617-26d3539f250f" if voice_id_to_use != "00529487-0a22-48b3-8617-26d3539f250f" else "viterbox"
                print(f"   ⚠️ Voice ID '{voice_id_to_use}' không tồn tại trên Server. Tự động chuyển sang giọng chuẩn '{fallback_voice}'...", flush=True)
                payload["voice_id"] = fallback_voice
                res_fb = requests.post(SERVER_URL, json=payload, timeout=1800)
                if res_fb.status_code == 200:
                    with open(save_path, "wb") as f:
                        f.write(res_fb.content)
                    print(f"   ✅ Thành công (Fallback {fallback_voice})! File lưu tại: {save_path}", flush=True)
                    return save_path
                else:
                    print(f"   ❌ Lỗi sau khi fallback ({res_fb.status_code}): {res_fb.text}", flush=True)
    except Exception as e:
        print(f"   ❌ Lỗi kết nối Voicebox Server: {e}", flush=True)
    return None

def create_voice_default(text, save_dir, filename):
    return create_voice_full_pipeline(text, save_dir, filename, profile_id="00529487-0a22-48b3-8617-26d3539f250f")

def create_voice_clone(text, ref_audio_path, ref_text, save_dir, filename):
    return create_voice_full_pipeline(text, save_dir, filename, profile_id="75b59968-5d03-4f45-ad03-45dc7d01e95e")

if __name__ == "__main__":
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    OUTPUT_DIR = os.path.join(BASE_DIR, 'assets', 'temp_voice')
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    noi_dung_can_doc = "Chào bạn, đây là bài kiểm tra kết nối API hệ thống Voicebox Studio mới nhất."
    ten_file_xuat = "test_voicebox.wav"

    print("=== BẮT ĐẦU KIỂM TRA MÁY KHÁCH GỌI MÁY CHỦ VOICEBOX STUDIO ===")
    print(f"📝 Nội dung cần đọc: {noi_dung_can_doc}\n")

    kq = create_voice_full_pipeline(
        text=noi_dung_can_doc,
        save_dir=OUTPUT_DIR,
        filename=ten_file_xuat,
        profile_id="75b59968-5d03-4f45-ad03-45dc7d01e95e"
    )

    if kq:
        print(f"\n🎉 THÀNH CÔNG! File đã được lưu tại:\n👉 {kq}")
    else:
        print("\n❌ THẤT BẠI! Vui lòng kiểm tra Server Voicebox Studio đang chạy ở cổng 8080.")