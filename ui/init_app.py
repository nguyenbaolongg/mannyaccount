import streamlit as st
from config.settings import LOGO_DIR

def setup_page():
    st.set_page_config(page_title="EverAI Pro Editor - V6.1", page_icon="🎬", layout="wide")
    st.markdown("<style>.stButton>button { width: 100%; height: 3em; }</style>", unsafe_allow_html=True)
    st.title("🎙️ EverAI Pro Editor (v6.1 - Full Features)")
    st.caption(f"Folder Logo: {LOGO_DIR}")
    st.divider()

def init_session_state():
    defaults = {
        'main_text_area': "",
        'current_sheet_row': None,
        'scraped_images': [],
        'article_title': "",
        'has_old_audio_on_sheet': False,
        'last_text_layer_path': None,
        'sheet_image_prompts': [],
        'search_results_preview': [],
        'source_video_url': "",
        'logo_key': 0,
        'img_key': 0,
        'last_result': None,
        'last_title_result': None,

        # [MỚI] Thêm dòng này để khởi tạo key cho ô nhập Title
        'input_title_voice': ""
    }

    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val