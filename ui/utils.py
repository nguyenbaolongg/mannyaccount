import json
import os
import streamlit as st
from datetime import datetime
from PIL import Image

# ================= CẤU HÌNH PATH CHUNG =================
CURRENT_FILE = os.path.abspath(__file__)
UI_DIR = os.path.dirname(CURRENT_FILE)
PROJECT_ROOT = os.path.dirname(UI_DIR)
CONFIG_DIR = os.path.join(PROJECT_ROOT, "config")
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")

# Đảm bảo folder tồn tại
FRAME_DIR = os.path.join(ASSETS_DIR, "frame")
AI_STUDIO_DIR = os.path.join(ASSETS_DIR, "ai_studio_data")
TEMP_DOWNLOADS_DIR = os.path.join(ASSETS_DIR, "temp_downloads")

for d in [FRAME_DIR, AI_STUDIO_DIR, TEMP_DOWNLOADS_DIR, CONFIG_DIR]:
    if not os.path.exists(d): os.makedirs(d)

# Các file config
TRACKING_FILE = os.path.join(CONFIG_DIR, "channels_tracking.json")
ACCOUNTS_FILE = os.path.join(CONFIG_DIR, "tiktok_accounts.json")
RENDER_CONFIG_FILE = os.path.join(CONFIG_DIR, "render_config.json")
USER_SETTINGS_FILE = os.path.join(PROJECT_ROOT, "user_settings.json")
SCHEDULE_FILE = os.path.join(CONFIG_DIR, "schedule_config.json")
SESSION_CONFIG_FILE = os.path.join(CONFIG_DIR, "session_config.json")
ACCOUNTS_DIR = os.path.join(CONFIG_DIR, "accounts")
if not os.path.exists(ACCOUNTS_DIR): os.makedirs(ACCOUNTS_DIR)
# --- HELPER FUNCTIONS ---
def load_json(filepath):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f: return json.load(f)
        except: return {}
    return {}

def save_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def save_frame_image(uploaded_file):
    if uploaded_file:
        try:
            file_path = os.path.join(FRAME_DIR, uploaded_file.name)
            with open(file_path, "wb") as f: f.write(uploaded_file.getbuffer())
            return uploaded_file.name
        except Exception as e:
            st.error(f"Lỗi lưu ảnh: {e}")
    return None

def normalize_time_input(time_str):
    try:
        t = time_str.strip()
        dt = datetime.strptime(t, "%H:%M")
        return dt.strftime("%H:%M")
    except: return None

def safe_show_image(path, width=100):
    if os.path.exists(path):
        try:
            image = Image.open(path)
            st.image(image, width=width)
        except Exception:
            st.caption(f"Ảnh lỗi: {os.path.basename(path)}")