#!/usr/bin/env python3
import os
import sys
import json
import requests

# Lùi 3 cấp để về thư mục mannyAccount (nơi chứa thư mục services)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)
from services.sheet_api import safe_post_json

SHEET_URL = "https://script.google.com/macros/s/AKfycbzze8wbf3s9o6OtH180Qp-ofKj_ZuL3S-o4-GoahxvJ2IhE-jPD9YQLTQnvMkrEgRyg/exec"

def save_article_to_sheet(ai_result: dict, article_url: str, id_tiktok: str) -> dict | None:
    """
    Ghi dữ liệu Báo Mạng vào sheet 'tổng'.
    - B, E: hook
    - C: script_voice
    - G: image_prompts (danh sách mô tả ảnh)
    - I: title_tiktok
    - N: id_tiktok
    """
    payload = {
        "action": "save_facebook", # Có thể cần đổi thành save_article nếu AppScript có hàm riêng
        "sheet_name": "tổng",
        "link": article_url,                                        # A
        "hook": ai_result.get("hook", ""),                          # B + E
        "script_voice": ai_result.get("script_voice", ""),          # C
        "main_idea": ai_result.get("main_idea", ""),                # D
        "scenes": json.dumps(ai_result.get("scenes", []), ensure_ascii=False), # G (Chứa mảng các object scene)
        "source_name": "Bài Báo",                                   # H
        "title_tiktok": ai_result.get("title_tiktok", ""),          # I
        "id_tiktok": id_tiktok,                                     # N (Cần sửa Google App Script để nhận biến này)
        "have_frame": False,
    }

    print(f"      📊 Ghi Sheet 'tổng': id_tiktok→N, hook→B+E, voice→C, image_prompts→G")

    result = safe_post_json(SHEET_URL, payload)

    if result and result.get("status") == "success":
        row = result.get("row", "?")
        print(f"      ✅ Đã ghi Sheet dòng {row}")
        return result
    else:
        print(f"      ⚠️ Lỗi ghi Sheet: {result}")
        return result

def update_article_drive_link(row: int, drive_link: str) -> bool:
    payload = {
        "action": "update_fb_drive",
        "sheet_name": "tổng",
        "row": int(row),
        "drive_link": drive_link,
    }
    result = safe_post_json(SHEET_URL, payload)
    return result.get("status") == "success" if result else False
