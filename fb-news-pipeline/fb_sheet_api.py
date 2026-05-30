#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════
  fb_sheet_api.py — Ghi dữ liệu lên Google Sheet
  Dùng Apps Script URL có sẵn, ghi vào sheet "facebook"

  Cột trên sheet "facebook":
  A: link gốc Facebook
  B: hook
  C: title_tiktok
  D: main_idea
  E: content_style
  F: estimated_duration_seconds
  G: scenes (JSON string)
  H: source_name
  I: script_voice
  J: voice_link
  K: drive_link
  L: status
═══════════════════════════════════════════════════════
"""

import os
import sys
import json
import requests
import time
import random

# Tái sử dụng safe_post_json từ project chính
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
from services.sheet_api import safe_post_json

SHEET_URL = "https://script.google.com/macros/s/AKfycbwFf388vFhruw_eKOra_uGKltu6SdJQnSiA2dkovmkC6tWPFsSJsAYgLPmnre7vY-lK/exec"


def save_fb_to_sheet(ai_result: dict, video_url: str, source_name: str = "") -> dict | None:
    """
    Lưu kết quả AI phân tích lên Google Sheet tab "facebook".

    ai_result: JSON từ Gemini AI (hook, script_voice, title_tiktok...)
    video_url: URL video gốc Facebook
    source_name: Tên nguồn (VD: Theanh28)

    Trả về: {"status": "success", "row": 5} hoặc None
    """
    payload = {
        "action": "save_facebook",
        "sheet_name": "facebook",
        "link": video_url,
        "hook": ai_result.get("hook", ""),
        "title_tiktok": ai_result.get("title_tiktok", ""),
        "main_idea": ai_result.get("main_idea", ""),
        "content_style": ai_result.get("content_style", ""),
        "estimated_duration": ai_result.get("estimated_duration_seconds", 30),
        "scenes": json.dumps(ai_result.get("scenes", []), ensure_ascii=False),
        "source_name": source_name,
        "script_voice": ai_result.get("script_voice", ""),
    }

    print(f"      📊 Ghi Sheet: hook → B, script_voice → I")

    result = safe_post_json(SHEET_URL, payload)

    if result and result.get("status") == "success":
        row = result.get("row", "?")
        print(f"      ✅ Đã ghi Sheet dòng {row}")
        return result
    else:
        print(f"      ⚠️ Sheet response: {result}")
        return result


def update_fb_voice_link(row: int, voice_link: str) -> bool:
    """Cập nhật link voice vào cột J"""
    payload = {
        "action": "update_fb_voice",
        "sheet_name": "facebook",
        "row": int(row),
        "voice_link": voice_link,
    }
    result = safe_post_json(SHEET_URL, payload)
    return result.get("status") == "success" if result else False


def update_fb_drive_link(row: int, drive_link: str) -> bool:
    """Cập nhật link Drive vào cột K"""
    payload = {
        "action": "update_fb_drive",
        "sheet_name": "facebook",
        "row": int(row),
        "drive_link": drive_link,
    }
    result = safe_post_json(SHEET_URL, payload)
    return result.get("status") == "success" if result else False


def update_fb_status(row: int, status: str) -> bool:
    """Cập nhật status vào cột L"""
    payload = {
        "action": "update_fb_status",
        "sheet_name": "facebook",
        "row": int(row),
        "status": status,
    }
    result = safe_post_json(SHEET_URL, payload)
    return result.get("status") == "success" if result else False
