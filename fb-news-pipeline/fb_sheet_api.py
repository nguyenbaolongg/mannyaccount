#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════
  fb_sheet_api.py — Ghi dữ liệu lên Google Sheet
  Dùng Apps Script URL có sẵn, ghi vào sheet "facebook"

  Cột trên sheet "facebook":
  A: link gốc Facebook
  B: hook
  C: script_voice
  D: main_idea
  E: hook (duplicate)
  F: have_frame (true/false)
  G: scenes (JSON string)
  H: source_name
  I: title_tiktok
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

SHEET_URL = "https://script.google.com/macros/s/AKfycbzOb4bhHJotOVpljRvRJHuBr4RxzfjKqquW1TB1TOYJpg7iH8kI0mmnOpmf0gwF42Bi/exec"


def save_fb_to_sheet(ai_result: dict, video_url: str, source_name: str = "", id_tiktok: str = "") -> dict | None:
    """
    Lưu kết quả AI phân tích lên Google Sheet tab "facebook".
    Mapping: B=hook, C=script_voice, E=hook, I=title_tiktok, N=id_tiktok
    """
    payload = {
        "action": "save_facebook",
        "sheet_name": "tổng", # Ghi vào sheet tổng theo yêu cầu
        "link": video_url,                                          # A
        "hook": ai_result.get("hook", ""),                          # B + E
        "script_voice": ai_result.get("script_voice", ""),          # C
        "main_idea": ai_result.get("main_idea", ""),                # D
        "estimated_duration": ai_result.get("estimated_duration_seconds", 30),
        "have_frame": ai_result.get("have_frame", False),            # F
        "scenes": json.dumps(ai_result.get("scenes", []), ensure_ascii=False),  # G
        "source_name": source_name,                                 # H
        "title_tiktok": ai_result.get("title_tiktok", ""),          # I
        "id_tiktok": id_tiktok,                                     # N
    }

    print(f"      📊 Ghi Sheet: hook→B+E, script_voice→C, title_tiktok→I")

    result = safe_post_json(SHEET_URL, payload)

    if result and result.get("status") == "success":
        row = result.get("row", "?")
        print(f"      ✅ Đã ghi Sheet dòng {row}")
        return result
    else:
        print(f"      ⚠️ Sheet response: {result}")
        return result


def update_fb_voice_link(row: int, voice_link: str) -> bool:
    """Cập nhật link voice vào cột K (cột 11)"""
    payload = {
        "action": "update_fb_voice",
        "sheet_name": "tổng",
        "row": int(row),
        "voice_link": voice_link,
    }
    result = safe_post_json(SHEET_URL, payload)
    return result.get("status") == "success" if result else False


def update_fb_drive_link(row: int, drive_link: str) -> bool:
    """Cập nhật link Drive vào cột J (cột 10)"""
    payload = {
        "action": "update_fb_drive",
        "sheet_name": "tổng",
        "row": int(row),
        "drive_link": drive_link,
    }
    result = safe_post_json(SHEET_URL, payload)
    return result.get("status") == "success" if result else False


def update_fb_status(row: int, status: str) -> bool:
    """Cập nhật status vào cột L"""
    payload = {
        "action": "update_fb_status",
        "sheet_name": "tổng",
        "row": int(row),
        "status": status,
    }
    result = safe_post_json(SHEET_URL, payload)
    return result.get("status") == "success" if result else False
