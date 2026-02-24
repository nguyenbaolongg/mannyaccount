import requests
import json

def save_to_sheet(script_url, link, title, script, combined_hints, original_video, title_tiktok, tiktok_id, file_path=""):

    if not script_url: return None

    payload = {
        "action": "save",
        "link": link,
        "title": title,
        "script": script,
        "combined_hints": combined_hints,
        "original_video": original_video,
        "title_tiktok": title_tiktok,
        "tiktok_id": tiktok_id, # Cột N
        "file_path": file_path
    }

    try:
        response = requests.post(script_url, json=payload, timeout=20)
        return response.json()
    except Exception as e:
        print(f"❌ Lỗi Save to Sheet: {e}")
        return {"status": "error", "message": str(e)}

def update_tiktok_info(script_url, row, file_path=None, link_tiktok=None, title_tiktok=None):
    """
    [CŨ/MỚI] Cập nhật thông tin cơ bản (Action: update_tiktok_info)
    """
    try:
        payload = {"action": "update_tiktok_info", "row": int(row)}
        if file_path: payload["file_path"] = str(file_path)
        if link_tiktok: payload["link_tiktok"] = str(link_tiktok)
        if title_tiktok: payload["title_tiktok"] = str(title_tiktok)

        requests.post(script_url, json=payload, timeout=20)
        return True
    except: return False

def update_final_result(script_url, row_idx, drive_link):

    try:
        payload = {
            "action": "update_file_path",
            "row": int(row_idx),
            "file_path": str(drive_link)
        }
        requests.post(script_url, json=payload, timeout=20)
        return True
    except: return False

def update_voice_links(sheet_url, row, title_voice_link, content_voice_link):

    try:
        payload = {
            "action": "update_voice",
            "row": int(row),
            "title_voice": str(title_voice_link) if title_voice_link else "",
            "content_voice": str(content_voice_link) if content_voice_link else ""
        }
        requests.post(sheet_url, json=payload, timeout=20)
        return True
    except Exception as e:
        print(f"❌ Lỗi update voice: {e}")
        return False

def update_status_finish(script_url, row, link_tiktok):

    try:
        payload = {
            "action": "finish_upload",
            "row": int(row),
            "link_tiktok": str(link_tiktok)
        }
        res = requests.post(script_url, json=payload, timeout=20)
        return res.json().get("status") == "success"
    except: return False

# ==============================================================================
# 2. CÁC HÀM ĐỌC DỮ LIỆU (READ)
# ==============================================================================

def get_data_from_sheet(script_url, row_number=None):

    if not script_url: return None

    payload = {"action": "read"}
    if row_number: payload["row"] = int(row_number)

    try:
        res = requests.post(script_url, json=payload, timeout=30)
        if res.status_code != 200: return None

        data = res.json()
        if data.get("status") == "success":
            # Xử lý text
            raw_title = data.get("title_text", "")
            clean_title = raw_title.replace("\n", " ").strip() if raw_title else ""
            raw_content = data.get("content_text", "")
            clean_content = raw_content.replace("\n", " ").strip() if raw_content else ""

            return (
                data.get("url", "").strip(),            # 0
                clean_title,                            # 1
                clean_content,                          # 2
                data.get("row"),                        # 3
                data.get("existing_content_audio", ""), # 4
                data.get("existing_title_audio", ""),   # 5
                data.get("image_prompts", []),          # 6
                data.get("original_video_url", ""),     # 7
                data.get("tiktok_id", ""),              # 8 [QUAN TRỌNG: ID TikTok]
                data.get("title_tiktok", ""),           # 9
                data.get("status", "")                  # 10
            )
        else: return None
    except: return None

def get_pending_tasks(script_url):

    if not script_url: return []
    try:
        payload = {"action": "read_pending"}
        res = requests.post(script_url, json=payload, timeout=30)
        data = res.json()
        if data.get("status") == "success":
            return data.get("tasks", [])
        return []
    except: return []

def get_last_row_index(sheet_url):
    try:
        payload = {"action": "read", "row": ""}
        # Gửi request
        response = requests.post(sheet_url, json=payload, timeout=10)

        if response.status_code != 200:
            print(f"❌ HTTP Error {response.status_code}: {response.text}")
            return 0

        try:
            data = response.json()
        except Exception as json_err:
            print(f"❌ Lỗi đọc JSON (Có thể Script bị Crash): {response.text[:200]}...") # In 200 ký tự đầu
            return 0

        if data.get("status") == "success":
            return int(data.get("row", 0))
        return 0

    except Exception as e:
        print(f"🔥 Lỗi Exception: {e}")
        return 0

def get_latest_row_by_id(sheet_url, tiktok_id):
    if not sheet_url: return "SHeet không đúng"
    def norm(x):
        return str(x).replace("@","").strip().lower()

    target = norm(tiktok_id)
    last_row = get_last_row_index(sheet_url)
    scan_limit = 200
    for r in range(last_row, max(1, last_row - scan_limit), -1):
        data = get_data_from_sheet(sheet_url, r)
        if not data:
            continue

        sheet_id = norm(data[8])
        content = data[2]
        title = data[1]
        if target == sheet_id:
            if content and len(content) > 5:
                return {
                    "row": r,
                    "title_text": title,
                    "content_text": content,
                    "tiktok_id_sheet": sheet_id
                }
            else:
                print(f"Row {r} match ID but no text yet, waiting...")
                continue
    return None
