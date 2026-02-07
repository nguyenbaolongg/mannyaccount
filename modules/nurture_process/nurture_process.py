import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException
import time
import os
import random
import re

# ================= ⚙️ CẤU HÌNH NUÔI NICK =================
USER_DATA_DIR = os.path.join(os.getcwd(), "tiktok_profile_data")

CONFIG = {
    "step_delay_min": 2,
    "step_delay_max": 5
}

PROBABILITY = {
    "scroll_up": 0.08,
    "like": 0.15,
    "save": 0.05,
    "random_mouse": 0.50
}

class HumanBehavior:
    @staticmethod
    def sleep_random(min_s=None, max_s=None):
        if min_s is None: min_s = CONFIG["step_delay_min"]
        if max_s is None: max_s = CONFIG["step_delay_max"]
        time.sleep(random.uniform(min_s, max_s))

    @staticmethod
    def is_video_liked(driver):
        try:
            # TikTok thường dùng aria-label "Like" hoặc "Thích"
            btns = driver.find_elements(By.XPATH, '//button[@aria-label[contains(., "ike") or contains(., "hích")]]')
            for btn in btns:
                if btn.get_attribute("aria-pressed") == "true":
                    return True
            return False
        except:
            return False

    @staticmethod
    def safe_like(driver):
        try:
            if HumanBehavior.is_video_liked(driver):
                print("      ⚠️ Đã Like trước đó -> Bỏ qua.")
                return

            like_btn = driver.find_element(By.CSS_SELECTOR, '[data-e2e="like-icon"]')
            print(f"      ❤️  QUYẾT ĐỊNH: Thả tim")

            # Di chuyển chuột tới rồi mới click để giống người
            actions = ActionChains(driver)
            actions.move_to_element(like_btn).pause(random.uniform(0.3, 0.8)).click().perform()
            HumanBehavior.sleep_random(1, 2)
        except Exception as e:
            print(f"      ⚠️ Không tìm thấy nút Like hoặc lỗi: {e}")

    @staticmethod
    def safe_save(driver):
        try:
            # Nút lưu thường có class chứa "ButtonActionItem"
            save_btn = driver.find_element(By.XPATH, '//button[.//span[contains(@data-e2e, "save") or contains(@data-e2e, "undefined")]]')
            print("      🔖 Lưu video")
            save_btn.click()
            HumanBehavior.sleep_random(1, 2)
        except: pass

    @staticmethod
    def interact_with_video(driver):
        rand_val = random.random()
        if rand_val < PROBABILITY["like"]:
            HumanBehavior.safe_like(driver)
        elif rand_val < (PROBABILITY["like"] + PROBABILITY["save"]):
            HumanBehavior.safe_save(driver)
        else:
            print("      😶 Chỉ xem, không tương tác.")

    @staticmethod
    def browse_feed(driver, duration_seconds):
        print(f"☕ Bắt đầu nuôi nick trong {int(duration_seconds / 60)} phút...")
        start_time = time.time()

        while time.time() - start_time < duration_seconds:
            try:
                body = driver.find_element(By.TAG_NAME, 'body')

                # Quyết định lướt lên hay xuống
                if random.random() < PROBABILITY["scroll_up"]:
                    print("   ⬆️ Lướt lên xem lại")
                    body.send_keys(Keys.ARROW_UP)
                else:
                    print("   ⬇️ Lướt video tiếp theo")
                    body.send_keys(Keys.ARROW_DOWN)

                # Xem từ 8 - 30 giây (người thật ít khi lướt dưới 5s trừ khi rác)
                watch_duration = random.uniform(8, 30)
                print(f"      👀 Đang xem: {watch_duration:.1f}s")

                slept = 0
                has_interacted = False
                interact_at = random.uniform(5, watch_duration - 3)

                while slept < watch_duration:
                    if random.random() < PROBABILITY["random_mouse"]:
                        try:
                            ac = ActionChains(driver)
                            ac.move_by_offset(random.randint(-10, 10), random.randint(-10, 10)).perform()
                        except: pass

                    time.sleep(1)
                    slept += 1

                    # Tương tác nếu xem đủ lâu
                    if not has_interacted and slept >= interact_at and random.random() < 0.3:
                        HumanBehavior.interact_with_video(driver)
                        has_interacted = True

            except Exception as e:
                print(f"⚠️ Lỗi trong khi xem: {e}")
                time.sleep(2)

def get_chrome_main_version():
    """Hàm tự động lấy phiên bản Chrome trên máy để fix lỗi Version Mismatch"""
    try:
        # Lệnh này hoạt động trên Windows
        output = os.popen('reg query "HKEY_CURRENT_USER\\Software\\Google\\Chrome\\BLBeacon" /v version').read()
        version = re.search(r'\d+\.\d+\.\d+\.\d+', output).group()
        return int(version.split('.')[0])
    except:
        return None # Để uc tự quyết định nếu lỗi

def start_nurturing(minutes=15):
    if not os.path.exists(USER_DATA_DIR): os.makedirs(USER_DATA_DIR)

    # Lấy phiên bản Chrome hiện tại để fix lỗi Driver 145 vs Browser 144
    chrome_version = get_chrome_main_version()
    print(f"🔍 Phát hiện Chrome Version: {chrome_version}")

    options = uc.ChromeOptions()
    options.add_argument(f"--user-data-dir={USER_DATA_DIR}") # Lưu profile thật
    options.add_argument("--profile-directory=Default")
    options.add_argument("--mute-audio")
    options.add_argument("--disable-notifications")

    # Ẩn dòng chữ "Chrome is being controlled..."
    options.add_argument("--disable-infobars")

    driver = None
    try:
        # version_main giúp khớp Driver với Browser
        driver = uc.Chrome(options=options, version_main=chrome_version, use_subprocess=True)
        driver.maximize_window()

        driver.get("https://www.tiktok.com/")
        time.sleep(5)

        # Kiểm tra xem có bị bắt đăng nhập không (nếu có profile thì thường không)
        HumanBehavior.browse_feed(driver, minutes * 60)
        return True
    except Exception as e:
        print(f"❌ Lỗi khởi động Chrome: {e}")
        return False
    finally:
        if driver:
            try: driver.quit()
            except: pass

if __name__ == "__main__":
    start_nurturing(10)