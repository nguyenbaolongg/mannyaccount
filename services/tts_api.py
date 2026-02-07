import requests

def generate_voice(api_key, text, voice_id, speed, pitch):
    url = "https://www.everai.vn/api/v1/tts"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    payload = {
        "response_type": "indirect", "callback_url": "https://example.com/callback",
        "input_text": text, "voice_id": voice_id, "audio_type": "mp3",
        "bitrate": 128, "speed_rate": speed, "pitch_rate": pitch, "volume": 100
    }
    try:
        res = requests.post(url, json=payload, headers=headers)
        if res.status_code != 200: raise Exception(f"HTTP {res.status_code}")
        data = res.json()
        if data.get("status") == 1: return data["result"]["request_id"]
        raise Exception(data.get("error_message"))
    except Exception as e: raise e

def check_request_status(api_key, request_id):
    url = f"https://www.everai.vn/api/v1/tts/{request_id}/callback-result"
    try:
        res = requests.get(url, headers={"Authorization": f"Bearer {api_key}"})
        if res.status_code != 200: return None
        data = res.json()
        if data.get("status") == 1 and data.get("result"): return data["result"].get("payload")
        return None
    except: return None