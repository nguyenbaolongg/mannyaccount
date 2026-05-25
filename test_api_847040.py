import requests
import time

URL = "http://127.0.0.1:8081/generate/full-pipeline"

payload = {
    "text": "Nha khoa Sài Gòn Tâm Đức tại thành phố Hồ Chí Minh vừa phải nhận mức phạt cực nặng từ Sở Y tế. Dù đang trong thời gian bị đình chỉ hoạt động nhưng cơ sở này vẫn ngang nhiên tiếp đón khách, khám chữa bệnh trái phép. Hành vi coi thường pháp luật này đã khiến nha khoa phải nộp phạt chín mươi triệu đồng và tiếp tục bị đình chỉ hoạt động thêm mười tám tháng. Không những vậy, hai cá nhân tại đây cũng bị phạt mỗi người ba mươi lăm triệu đồng do không có chứng chỉ hành nghề. Đây là lời cảnh tỉnh đanh thép cho những cơ sở y tế thiếu tôn trọng quy định của nhà nước.",
    "profile_id": "53b4b81a-959c-4fc0-b6d0-bdfc9f685cf5",
    "engine": "viterbox",
    "run_rvc": True,
    "run_enhance": False,
    "normalize": True,
    "rvc_model_path": "voices/847040/model.pth",
    "rvc_index_path": "",
    "rvc_pitch": 0,
    "rvc_f0_method": "rmvpe"
}

print(f"🚀 Đang gửi lệnh test tới Server Voicebox (Cổng 8081)...")
start_time = time.time()

try:
    response = requests.post(URL, json=payload, timeout=60)
    
    if response.status_code == 200:
        elapsed = time.time() - start_time
        save_path = "test_ket_qua_847040.wav"
        with open(save_path, "wb") as f:
            f.write(response.content)
        print(f"✅ THÀNH CÔNG! Đã nhận được file âm thanh sau {elapsed:.2f} giây.")
        print(f"🎧 File được lưu tại: {save_path}")
    else:
        print(f"❌ LỖI TỪ SERVER (Mã {response.status_code}): {response.text}")
except requests.exceptions.RequestException as e:
    print(f"❌ KHÔNG THỂ KẾT NỐI TỚI SERVER: {e}")
    print("💡 Gợi ý: Hãy kiểm tra xem server Voicebox đã chạy ở cổng 8081 chưa.")
