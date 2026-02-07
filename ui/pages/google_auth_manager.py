import streamlit as st
import json
import os

# Xác định đường dẫn project root
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_DIR))
CREDENTIALS_PATH = os.path.join(PROJECT_ROOT,"config", "credentials.json")

def load_credentials():
    """Đọc file credentials.json"""
    default_structure = {
        "installed": {
            "client_id": "",
            "project_id": "",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": "",
            "redirect_uris": ["http://localhost"]
        },
        "id_folder": ""
    }

    if os.path.exists(CREDENTIALS_PATH):
        try:
            with open(CREDENTIALS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data
        except Exception as e:
            st.error(f"Lỗi đọc file JSON: {e}")
            return default_structure
    return default_structure

def save_credentials(data):
    """Lưu dữ liệu vào file credentials.json"""
    try:
        with open(CREDENTIALS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"Lỗi lưu file: {e}")
        return False

def render_google_auth_manager():
    st.markdown("## 🔐 Cấu hình Google Credentials & Drive")
    st.caption(f"File đường dẫn: `{CREDENTIALS_PATH}`")

    # Load dữ liệu hiện tại
    full_data = load_credentials()

    # 1. Lấy dữ liệu OAuth
    root_key = "installed" if "installed" in full_data else "web"
    if root_key not in full_data:
        root_key = "installed"
        if root_key not in full_data: full_data[root_key] = {}

    creds = full_data.get(root_key, {})

    # Chuẩn bị dữ liệu hiển thị (Lưu vào biến tạm để làm placeholder)
    cur_id_folder = full_data.get("id_folder", "")
    cur_client_id = creds.get("client_id", "")
    cur_project_id = creds.get("project_id", "")
    cur_secret = creds.get("client_secret", "")

    cur_redirects = creds.get("redirect_uris", ["http://localhost"])
    cur_redirect_str = ", ".join(cur_redirects) if isinstance(cur_redirects, list) else str(cur_redirects)

    cur_auth_uri = creds.get("auth_uri", "https://accounts.google.com/o/oauth2/auth")
    cur_token_uri = creds.get("token_uri", "https://oauth2.googleapis.com/token")
    cur_cert_url = creds.get("auth_provider_x509_cert_url", "https://www.googleapis.com/oauth2/v1/certs")

    with st.form("google_creds_form"):
        # --- PHẦN 1: GOOGLE DRIVE CONFIG ---
        st.subheader("📁 Cấu hình Google Drive")
        st.info("Nhập ID mới để thay đổi. Để trống sẽ giữ nguyên ID cũ (hiển thị mờ).")

        # Placeholder là dữ liệu hiện tại
        new_id_folder = st.text_input("ID Folder:", value="", placeholder=cur_id_folder)

        st.divider()

        # --- PHẦN 2: OAUTH CREDENTIALS ---
        st.subheader("🔑 OAuth 2.0 Client IDs")

        col1, col2 = st.columns(2)
        with col1:
            inp_client_id = st.text_input("Client ID:", value="", placeholder=cur_client_id)
            inp_project_id = st.text_input("Project ID:", value="", placeholder=cur_project_id)

        with col2:
            # Lưu ý: type="password" vẫn hỗ trợ placeholder
            inp_secret = st.text_input("Client Secret:", value="", placeholder=cur_secret, type="password")

        inp_redirects = st.text_area(
            "Redirect URIs (Ngăn cách bằng dấu phẩy):",
            value="",
            placeholder=cur_redirect_str,
            help="Ví dụ: http://localhost"
        )

        # Thông tin nâng cao
        with st.expander("⚙️ Cấu hình Nâng cao (URI)", expanded=False):
            inp_auth_uri = st.text_input("Auth URI:", value="", placeholder=cur_auth_uri)
            inp_token_uri = st.text_input("Token URI:", value="", placeholder=cur_token_uri)
            inp_cert_url = st.text_input("Cert URL:", value="", placeholder=cur_cert_url)

        st.divider()

        # Nút Submit
        submitted = st.form_submit_button("💾 LƯU CẤU HÌNH", type="primary")

        if submitted:
            # LOGIC XỬ LÝ: Nếu ô nhập có dữ liệu -> Dùng mới. Nếu để trống -> Dùng cũ (Placeholder)

            final_id_folder = new_id_folder.strip() if new_id_folder.strip() else cur_id_folder
            final_client_id = inp_client_id.strip() if inp_client_id.strip() else cur_client_id
            final_project_id = inp_project_id.strip() if inp_project_id.strip() else cur_project_id
            final_secret = inp_secret.strip() if inp_secret.strip() else cur_secret

            final_auth_uri = inp_auth_uri.strip() if inp_auth_uri.strip() else cur_auth_uri
            final_token_uri = inp_token_uri.strip() if inp_token_uri.strip() else cur_token_uri
            final_cert_url = inp_cert_url.strip() if inp_cert_url.strip() else cur_cert_url

            # Xử lý Redirects
            if inp_redirects.strip():
                final_redirect_list = [uri.strip() for uri in inp_redirects.split(",") if uri.strip()]
            else:
                final_redirect_list = cur_redirects

            # Tạo object update
            updated_creds = {
                "client_id": final_client_id,
                "project_id": final_project_id,
                "auth_uri": final_auth_uri,
                "token_uri": final_token_uri,
                "auth_provider_x509_cert_url": final_cert_url,
                "client_secret": final_secret,
                "redirect_uris": final_redirect_list
            }

            # Cập nhật vào data gốc
            full_data[root_key] = updated_creds
            full_data["id_folder"] = final_id_folder

            # Lưu file
            if save_credentials(full_data):
                st.success("✅ Đã cập nhật credentials.json thành công!")
                # Reload lại trang để placeholder cập nhật giá trị mới
                st.rerun()

if __name__ == "__main__":
    st.set_page_config(layout="wide")
    render_google_auth_manager()