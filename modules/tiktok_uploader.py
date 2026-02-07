import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os
import sys

# ================= CẤU HÌNH UPLOAD =================
CURRENT_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT_DIR = os.path.dirname(CURRENT_FILE_DIR)
# Trỏ chính xác vào folder profile data
USER_DATA_DIR = os.path.join(PROJECT_ROOT_DIR, "tiktok_data/tiktok_profile_data")

print(f"📂 Profile Path: {USER_DATA_DIR}")
# ===================================================

def get_current_username(driver):
    """
    Lấy Username bằng Selenium
    """
    try:
        print("👤 Đang tự động phát hiện Username...")
        driver.get("https://www.tiktok.com/")

        # Chờ tối đa 20s để tìm thẻ a có href bắt đầu bằng /@
        try:
            profile_link = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href^="/@"]'))
            )
            href = profile_link.get_attribute("href")  # Dạng https://www.tiktok.com/@username

            # Xử lý chuỗi để lấy username
            if "/@" in href:
                username = href.split("/@")[1].split("?")[0] # Lấy phần sau /@ và bỏ tham số query nếu có
                username = "@" + username.replace("/", "")
                print(f"✅ Đã phát hiện Username: {username}")
                return username
        except:
            print("⚠️ Không tìm thấy element username trên trang chủ.")

        return None
    except Exception as e:
        print(f"⚠️ Lỗi lấy username: {e}")
        return None

def get_link_from_profile(driver, username):
    """
    Vào profile lấy video mới nhất
    """
    try:
        if not username:
            print("❌ Không có username, không thể lấy link.")
            return None

        # Nếu username chưa có @ thì thêm vào (để URL đúng chuẩn)
        clean_username = username if username.startswith("@") else f"@{username}"
        profile_url = f"https://www.tiktok.com/{clean_username}"

        print(f"\n🔄 Đang truy cập Profile: {profile_url}")
        driver.get(profile_url)

        print("⏳ Đang tìm video mới nhất...")
        # Chờ video load (data-e2e="user-post-item")
        try:
            latest_video_element = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-e2e="user-post-item"] a'))
            )
            video_link = latest_video_element.get_attribute("href")
            print(f"✅ Đã lấy được link: {video_link}")
            return video_link
        except:
            print("❌ Không tìm thấy video nào trong profile.")
            return None

    except Exception as e:
        print(f"⚠️ Lỗi lấy link từ Profile: {e}")
        return None

def upload_video_to_tiktok(video_path, caption):
    if not os.path.exists(video_path):
        print(f"❌ Lỗi: Không tìm thấy file {video_path}")
        return None

    if not caption:
        caption = "Video Remix #fyp #xuhuong"

    print(f"🚀 Bắt đầu Upload (Selenium): {os.path.basename(video_path)}")

    # Cấu hình Undetected Chromedriver
    options = uc.ChromeOptions()
    options.add_argument(f"--user-data-dir={USER_DATA_DIR}")
    options.add_argument("--disable-popup-blocking")
    # options.add_argument("--headless") # Khuyên dùng False để debug

    driver = None
    uploaded_link = None

    try:
        # Khởi tạo browser
        driver = uc.Chrome(options=options, use_subprocess=True)

        # BƯỚC 1: LẤY USERNAME
        detected_username = get_current_username(driver)

        # BƯỚC 2: VÀO TRANG UPLOAD
        print("🔗 Đang vào TikTok Studio...")
        driver.get("https://www.tiktok.com/tiktokstudio/upload")

        # Check login đơn giản qua URL
        time.sleep(3)
        if "login" in driver.current_url:
            print("❌ Bạn chưa đăng nhập! Hãy đăng nhập thủ công vào profile này rồi chạy lại.")
            return None

        # BƯỚC 3: UPLOAD FILE
        print("📤 Đang tải file lên...")
        # Tìm input type file (Selenium cần send_keys vào thẻ input này)
        try:
            # Chờ thẻ input xuất hiện
            file_input = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="file"]'))
            )
            file_input.send_keys(video_path)
        except Exception as e:
            print(f"❌ Lỗi tìm ô upload file: {e}")
            return None

        # BƯỚC 4: ĐIỀN CAPTION
        print("✍️ Đang xử lý Caption...")
        time.sleep(5) # Chờ popup xử lý file hiện lên một chút

        try:
            # Tìm ô editor contenteditable
            editor = WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'div[contenteditable="true"]'))
            )
            editor.click()
            time.sleep(0.5)

            # Xóa caption cũ (Ctrl+A -> Backspace)
            # Lưu ý: Mac OS dùng Keys.COMMAND, Windows dùng Keys.CONTROL
            modifier = Keys.COMMAND if sys.platform == 'darwin' else Keys.CONTROL
            editor.send_keys(modifier, 'a')
            time.sleep(0.5)
            editor.send_keys(Keys.BACKSPACE)
            time.sleep(0.5)

            # Nhập caption mới
            editor.send_keys(str(caption))
        except Exception as e:
            print(f"⚠️ Lỗi điền caption (có thể bỏ qua nếu video vẫn lên): {e}")

        # BƯỚC 5: CLICK ĐĂNG
        print("🚀 Đang tìm nút Đăng...")
        # Cuộn xuống cuối trang
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        try:
            post_btn = driver.find_element(By.CSS_SELECTOR, '[data-e2e="post_video_button"]')

            # Vòng lặp chờ nút enable (hết disable và hết loading)
            max_wait = 120 # 2 phút
            start_time = time.time()

            while time.time() - start_time < max_wait:
                is_disabled = post_btn.get_attribute("disabled") is not None
                is_loading = post_btn.get_attribute("data-loading") == "true"

                if not is_disabled and not is_loading:
                    print("✅ Nút Đăng đã sáng. Click!")
                    # Click bằng JS để tránh bị che bởi phần tử khác
                    driver.execute_script("arguments[0].click();", post_btn)
                    break

                time.sleep(2)
                print("⏳ Đang chờ xử lý video...", end="\r")
            else:
                print("\n❌ Timeout: Nút đăng không sáng sau 2 phút.")
                return None

        except Exception as e:
            print(f"❌ Lỗi tìm nút đăng: {e}")
            return None

        # BƯỚC 6: XÁC NHẬN THÀNH CÔNG VÀ LẤY LINK
        print("\n👀 Đang chờ thông báo thành công...")
        success = False

        # Chờ tối đa 30s check thành công
        for _ in range(30):
            page_source = driver.page_source.lower()
            current_url = driver.current_url

            # Check popup "Post now" nếu có
            try:
                btns = driver.find_elements(By.XPATH, "//button[contains(text(), 'Post now')]")
                if btns:
                    btns[0].click()
            except:
                pass

            if "uploaded" in page_source or "đã được tải lên" in page_source or "manage" in current_url:
                print("🎉 Phát hiện upload thành công!")
                success = True
                break
            time.sleep(1)

        if success:
            time.sleep(5) # Chờ server TikTok
            if detected_username:
                uploaded_link = get_link_from_profile(driver, detected_username)
            else:
                print("⚠️ Không có username để lấy link.")
        else:
            print("❌ Không xác nhận được trạng thái thành công.")

    except Exception as e:
        print(f"❌ Lỗi nghiêm trọng: {e}")
    finally:
        if driver:
            print("👋 Đóng trình duyệt...")
            driver.quit()

    return uploaded_link

# ================== CHẠY CODE ==================

if __name__ == "__main__":
    v_path = r"C:\Users\Acer\Videos\viral_4_1769591148.mp4"
    caption_text = "Tin tức"
    upload_video_to_tiktok(v_path, caption_text)