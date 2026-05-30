import os
import requests

# ─── CẤU HÌNH ──────────────────────────────────────────────────────────────────
# Voice mặc định: "voice the anh 28" - lưu trong PostgreSQL DB
# DB đã có: rvc_model_path = voices/847040/model.pth
#           rvc_index_path = voices/847040/model.index
#           default_engine = viterbox
DEFAULT_PROFILE_ID = "d4dbf9de-2f6a-42e7-8f8d-0e5586824a21"
DEFAULT_SPEED       = 1.05

# URL kết nối API
LOCAL_URL  = "http://127.0.0.1:8080/generate/full-pipeline"
PUBLIC_URL = "https://voice.adsup.vn/generate/full-pipeline"


def _get_server_url() -> str:
    """Tự động chọn URL: thử local trước, nếu không được dùng public."""
    override = os.environ.get("VOICEBOX_API_URL", "").strip()
    if override:
        return override
    try:
        r = requests.get("http://127.0.0.1:8080/health", timeout=2)
        if r.status_code == 200:
            return LOCAL_URL
    except Exception:
        pass
    return PUBLIC_URL


# Alias cũ → UUID mới trong DB
_ALIAS_MAP = {
    "theanh28": DEFAULT_PROFILE_ID,
    "tiktok":   DEFAULT_PROFILE_ID,
    "847040":   DEFAULT_PROFILE_ID,
    "viterbox": DEFAULT_PROFILE_ID,
}


def create_voice_full_pipeline(
    text,
    save_dir,
    filename,
    profile_id=DEFAULT_PROFILE_ID,
    rvc_pitch=0,
    emotion="binh_thuong",
    speed=DEFAULT_SPEED,
    rvc_model=None,   # tương thích ngược — bị bỏ qua, DB lo
):
    """
    Gọi API Voicebox Full Pipeline.

    - profile_id : UUID của voice trong PostgreSQL (mặc định: voice the anh 28)
    - Mọi cấu hình RVC (model path, index path) đọc tự động từ DB theo profile_id
    - Tự động chọn URL nội bộ :8080 hoặc voice.adsup.vn khi cần
    """
    save_path = os.path.join(save_dir, filename)

    # Chuẩn hóa alias → UUID
    if rvc_model and str(rvc_model).strip():
        profile_id = _ALIAS_MAP.get(str(rvc_model).strip(), str(rvc_model).strip())
    profile_id = _ALIAS_MAP.get(profile_id, profile_id)

    # Payload đồng bộ 100% với Web frontend (App.jsx handleGenerate)
    payload = {
        "text":            text,
        "profile_id":      profile_id,
        "language":        "vi",
        "engine":          "viterbox",
        "run_rvc":         True,
        "run_enhance":     False,          # Tắt enhance - test so sánh với web
        "enhance_neural":  "off",
        "normalize":       True,
        "rvc_pitch":       rvc_pitch,
        "rvc_f0_method":   "rmvpe",
        "speed":           speed,
        "emotion":         emotion,
    }


    try:
        import fcntl
        lock_file = "/tmp/voicebox_rvc.lock"

        server_url = _get_server_url()
        url_label = "noi bo :8080" if "127.0.0.1" in server_url else "cong khai voice.adsup.vn"
        print(f"   [API] {url_label} | Voice: {profile_id[:8]}... | Speed: {speed}", flush=True)
        print(f"   [*] Cho luot GPU...", flush=True)

        with open(lock_file, "w") as lf:
            fcntl.flock(lf, fcntl.LOCK_EX)
            try:
                print(f"   [>>] Tong hop: '{text[:40]}...'", flush=True)
                res = requests.post(server_url, json=payload, timeout=1800)

                if res.status_code == 200:
                    with open(save_path, "wb") as f:
                        f.write(res.content)
                    print(f"   [OK] Luu: {save_path}", flush=True)
                    return save_path

                print(f"   [ERR] {res.status_code}: {res.text[:200]}", flush=True)
                # Fallback: thử lại không RVC
                if res.status_code in (400, 404, 500):
                    print(f"   [!] Fallback: thu TTS khong RVC...", flush=True)
                    payload["run_rvc"] = False
                    res2 = requests.post(server_url, json=payload, timeout=1800)
                    if res2.status_code == 200:
                        with open(save_path, "wb") as f:
                            f.write(res2.content)
                        print(f"   [OK] Fallback thanh cong: {save_path}", flush=True)
                        return save_path
                    print(f"   [ERR] Fallback that bai: {res2.status_code}", flush=True)
            finally:
                fcntl.flock(lf, fcntl.LOCK_UN)
    except Exception as e:
        print(f"   [ERR] Loi ket noi: {e}", flush=True)
    return None


# ─── Helper functions ───────────────────────────────────────────────────────────
def create_voice_default(text, save_dir, filename):
    """Dung voice mac dinh (voice the anh 28)."""
    return create_voice_full_pipeline(text, save_dir, filename)


def create_voice_clone(text, ref_audio_path, ref_text, save_dir, filename):
    """Tuong thich nguoc."""
    return create_voice_full_pipeline(
        text, save_dir, filename,
        profile_id="75b59968-5d03-4f45-ad03-45dc7d01e95e"
    )


# ─── Test truc tiep ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    OUTPUT_DIR = os.path.join(BASE_DIR, "assets", "temp_voice")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    text = "Xin chao! Day la bai kiem tra ket noi API voi giong voice the anh 28, toc do 1.1."
    print(f"Test: {text}\n")

    result = create_voice_full_pipeline(
        text=text,
        save_dir=OUTPUT_DIR,
        filename="test_theanh28.wav",
    )

    if result:
        print(f"\nTHANH CONG: {result}")
    else:
        print("\nTHAT BAI! Kiem tra server tai http://127.0.0.1:8080 hoac https://voice.adsup.vn")