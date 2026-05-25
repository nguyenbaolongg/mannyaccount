import os
import requests
import threading
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

app = FastAPI()

print("⏳ Đang khởi động TTS Server Proxy (Chuyển tiếp qua Voicebox Studio)...")
print("✅ TTS Server đã sẵn sàng nhận lệnh tại cổng 8000!")

tts_lock = threading.Lock()

class TTSRequest(BaseModel):
    text: str
    ref_audio_path: str = None
    ref_text: str = None
    save_path: str
    
    # Cấu hình mặc định theo yêu cầu RVC mới
    profile_id: str = "53b4b81a-959c-4fc0-b6d0-bdfc9f685cf5"
    engine: str = "viterbox"
    run_rvc: bool = True
    rvc_model_path: str = "voices/847040/model.pth"
    rvc_index_path: str = ""
    rvc_pitch: int = 0
    rvc_f0_method: str = "rmvpe"

@app.post("/v1/generate")
def generate_audio(req: TTSRequest):
    with tts_lock:
        try:
            print(f"📥 Đang nhận bài: '{req.text[:40]}...'")
            os.makedirs(os.path.dirname(req.save_path), exist_ok=True)

            # Chuyển tiếp payload sang Voicebox Studio API (cổng 8081)
            payload = {
                "text": req.text,
                "profile_id": req.profile_id,
                "engine": req.engine,
                "run_rvc": req.run_rvc,
                "rvc_model_path": req.rvc_model_path,
                "rvc_index_path": req.rvc_index_path,
                "rvc_pitch": req.rvc_pitch,
                "rvc_f0_method": req.rvc_f0_method,
                "normalize": True,       # Ép chuẩn hóa âm lượng TRƯỚC khi đưa vào RVC (giống main.py)
                "run_enhance": False     # Tắt bộ lọc Enhance kép vì broadcast_mastering đã làm quá tốt, bật lên sẽ làm tiếng bị nghẹt
            }

            SERVER_URL = "http://127.0.0.1:8081/generate/full-pipeline"
            
            print(f"🚀 Đang gửi yêu cầu sinh giọng RVC cho: '{req.text[:30]}...'")
            res = requests.post(SERVER_URL, json=payload, timeout=1800)
            
            if res.status_code == 200:
                with open(req.save_path, "wb") as f:
                    f.write(res.content)
                print(f"   🎉 Đã xuất file hoàn chỉnh: {os.path.basename(req.save_path)}\n")
                return {"status": "success", "file": req.save_path}
            else:
                print(f"   ❌ Voicebox Server báo lỗi ({res.status_code}): {res.text}\n")
                return {"status": "error", "message": f"Server error {res.status_code}: {res.text}"}

        except Exception as e:
            print(f"   ❌ Lỗi Server: {e}\n")
            return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)