import os
import requests

# Sử dụng chuẩn API mới từ xa (Full Pipeline)
SERVER_URL = "http://127.0.0.1:8081/generate/full-pipeline"

def create_voice_full_pipeline(text, save_dir, filename, profile_id="53b4b81a-959c-4fc0-b6d0-bdfc9f685cf5", rvc_model=None, rvc_pitch=0, emotion="binh_thuong", speed=1.15):
    """
    Hàm gọi API Voicebox mới (Full Pipeline API có hỗ trợ RVC).
    """
    save_path = os.path.join(save_dir, filename)
    
    # Ưu tiên lấy voice_id từ rvc_model
    voice_id_to_use = profile_id
    if rvc_model and str(rvc_model).strip():
        voice_id_to_use = str(rvc_model).strip()
        
    # Mapping ID cũ sang UUID mới (nếu truyền ID số hoặc ID cũ)
    if voice_id_to_use in ["847040", "aca10ed4-3ed0-4146-a6ff-96112b593988", "53b4b81a-959c-4fc0-b6d0-bdfc9f685cf5", "viterbox", "tiktok", "theanh28"]:
        profile_uuid = "53b4b81a-959c-4fc0-b6d0-bdfc9f685cf5"
        rvc_path = "voices/847040/model.pth"
    elif voice_id_to_use == "227742":
        profile_uuid = "f305433e-eb74-4e7f-9b93-298e63dde0f4"
        rvc_path = "voices/227742/model.pth"
    else:
        profile_uuid = voice_id_to_use
        rvc_path = f"voices/{voice_id_to_use}/model.pth"
    
    payload = {
        "text": text,
        "profile_id": profile_uuid,
        "engine": "viterbox",
        "run_rvc": True,
        "run_enhance": False,
        "rvc_model_path": rvc_path,
        "rvc_index_path": "",
        "rvc_pitch": rvc_pitch,
        "rvc_f0_method": "rmvpe"
    }

    try:
        import fcntl
        lock_file = "/tmp/voicebox_rvc.lock"
        
        print(f"   ⏳ Đang chờ lượt để sinh giọng (chống OOM cho GPU)...", flush=True)
        with open(lock_file, "w") as lf:
            fcntl.flock(lf, fcntl.LOCK_EX)
            try:
                print(f"   🚀 Đang gửi yêu cầu Full-Pipeline (Voice: {voice_id_to_use}) cho: '{text[:30]}...'", flush=True)
                res = requests.post(SERVER_URL, json=payload, timeout=1800)
                
                if res.status_code == 200:
                    with open(save_path, "wb") as f:
                        f.write(res.content)
                    print(f"   ✅ Thành công! File lưu tại: {save_path}", flush=True)
                    return save_path
                else:
                    print(f"   ❌ Server báo lỗi ({res.status_code}): {res.text}", flush=True)
                    if "not found" in res.text.lower() or res.status_code in (400, 404, 500):
                        print(f"   ⚠️ Lỗi Pipeline RVC. Tự động chuyển sang TTS thuần gốc của hệ thống...", flush=True)
                        payload["profile_id"] = "viterbox"
                        payload["run_rvc"] = False
                        res_fb = requests.post(SERVER_URL, json=payload, timeout=1800)
                        if res_fb.status_code == 200:
                            with open(save_path, "wb") as f:
                                f.write(res_fb.content)
                            print(f"   ✅ Thành công (Fallback TTS Thuần)! File lưu tại: {save_path}", flush=True)
                            return save_path
                        else:
                            print(f"   ❌ Lỗi sau khi fallback ({res_fb.status_code}): {res_fb.text}", flush=True)
            finally:
                fcntl.flock(lf, fcntl.LOCK_UN)
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