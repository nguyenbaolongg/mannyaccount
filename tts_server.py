import os
import threading
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
from vieneu import Vieneu
from vieneu_utils.core_utils import split_text_into_chunks, join_audio_chunks

app = FastAPI()

print("⏳ Đang khởi động TTS Server (Bản Bất Tử)...")
tts = Vieneu()
print("✅ TTS Server đã sẵn sàng nhận lệnh tại cổng 8000!")

tts_lock = threading.Lock()

class TTSRequest(BaseModel):
    text: str
    ref_audio_path: str = None
    ref_text: str = None
    save_path: str

@app.post("/v1/generate")
def generate_audio(req: TTSRequest):
    with tts_lock:
        try:
            print(f"📥 Đang nhận bài: '{req.text[:40]}...'")
            os.makedirs(os.path.dirname(req.save_path), exist_ok=True)

            # 1. Dùng bộ lọc chuẩn hóa xịn của Web
            clean_text = tts.normalizer.normalize(req.text)

            # 2. Băm nhỏ bằng thuật toán của Web
            chunks = split_text_into_chunks(clean_text, max_chars=120)
            print(f"🔪 Đã tự băm thành {len(chunks)} đoạn ngắn để tránh ngộp AI.")

            all_wavs = []

            for i, chunk in enumerate(chunks):
                chunk_wav = None

                # 3. CƠ CHẾ BẢO HIỂM: Thử lại 3 lần cho mỗi câu
                for attempt in range(3):
                    tweak_chunk = chunk
                    if attempt == 1: tweak_chunk = chunk + ","
                    if attempt == 2: tweak_chunk = chunk + " ."

                    try:
                        # max_chars=500 để tắt tính năng tự băm ngầm của hàm infer
                        wav = tts.infer(
                            text=tweak_chunk,
                            ref_audio=req.ref_audio_path,
                            ref_text=req.ref_text,
                            max_chars=500,
                            temperature=0.8 # Khóa nhiệt độ để tránh AI ảo giác
                        )
                        chunk_wav = wav
                        print(f"   ✅ Đọc xong đoạn {i+1}/{len(chunks)}")
                        break # Thành công thì thoát vòng lặp Retry
                    except Exception as e:
                        if attempt == 2:
                            print(f"   ⚠️ Lỗi dị biệt ở đoạn {i+1}. Bỏ qua để giữ 1 giọng!")

                if chunk_wav is not None and len(chunk_wav) > 0:
                    all_wavs.append(chunk_wav)

            if not all_wavs:
                raise Exception("AI bó tay toàn tập. Hãy kiểm tra lại File giọng mẫu (voice.wav)!")

            # 4. Khâu lại bằng thuật toán mượt mà của Web
            final_wav = join_audio_chunks(all_wavs, tts.sample_rate, silence_p=0.2, crossfade_p=0.0)

            tts.save(final_wav, req.save_path)
            print(f"   🎉 Đã xuất file hoàn chỉnh: {os.path.basename(req.save_path)}\n")
            return {"status": "success", "file": req.save_path}

        except Exception as e:
            print(f"   ❌ Lỗi Server: {e}\n")
            return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)