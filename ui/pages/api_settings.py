import streamlit as st
from ui.utils import load_json, save_json, USER_SETTINGS_FILE

def render_api_settings():
    st.markdown("## 🔑 Cấu hình API & Hệ thống")
    settings = load_json(USER_SETTINGS_FILE)
    with st.form("api_settings_form"):
        st.subheader("1. Hệ thống AI Studio")
        ai_url = st.text_input("AI Studio URL:", value=settings.get("ai_studio_url", ""))
        st.subheader("2. Text-to-Speech (TTS)")
        api_key = st.text_input("API Key (TTS Provider):", value=settings.get("api_key", ""), type="password")
        voice_id = st.text_input("Voice ID Mặc định:", value=settings.get("voice_id", "vi_female_kieunhi_mn"))
        st.subheader("3. Google Sheet (Database)")
        sheet_url = st.text_input("Apps Script URL:", value=settings.get("sheet_url", ""))
        if st.form_submit_button("💾 LƯU CẤU HÌNH", type="primary"):
            new_data = {"api_key": api_key.strip(), "sheet_url": sheet_url.strip(), "voice_id": voice_id.strip(), "ai_studio_url": ai_url.strip()}
            save_json(USER_SETTINGS_FILE, {**settings, **new_data})
            st.success("✅ Đã lưu cấu hình!")