import requests

payload = {
    "name": "847040",
    "language": "vi",
    "voice_type": "rvc",
    "default_engine": "viterbox",
    "rvc_model_path": "voices/847040/model.pth",
    "rvc_index_path": "voices/847040/model.index"
}

try:
    res = requests.post("http://127.0.0.1:8080/profiles", json=payload)
    if res.status_code == 200:
        print("CREATED PROFILE:", res.json()["id"])
    else:
        print("API ERROR:", res.status_code, res.text)
except Exception as e:
    print("ERR:", e)
