#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════
  chatgpt_automator.py — Tự động hóa ChatGPT qua trình duyệt
  
  Mục đích:
  - Mở trang ChatGPT bằng Playwright (dùng cookie đã login)
  - Upload file video
  - Gửi prompt + caption
  - Chờ kết quả JSON trả về
═══════════════════════════════════════════════════════
"""

import os
import json
import time
import re
from playwright.sync_api import sync_playwright

COOKIE_DIR = os.path.join(os.path.dirname(__file__), "data", "chatgpt_cookies")
COOKIE_PATH = os.path.join(COOKIE_DIR, "state.json")
PROMPT_FILE = os.path.join(os.path.dirname(__file__), "config", "prompt_script.txt")

def load_prompt() -> str:
    if os.path.exists(PROMPT_FILE):
        with open(PROMPT_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""

def login_chatgpt_interactive():
    """Mở trình duyệt để người dùng đăng nhập ChatGPT bằng tay 1 lần"""
    print("╔═══════════════════════════════════════════════════╗")
    print("║  🔑 ĐĂNG NHẬP CHATGPT ĐỂ LƯU COOKIE              ║")
    print("╚═══════════════════════════════════════════════════╝")
    print("\n1. Trình duyệt sẽ mở ChatGPT.")
    print("2. Vui lòng đăng nhập vào tài khoản của bạn.")
    print("3. Sau khi thấy ô nhập tin nhắn, quay lại đây nhấn ENTER.\n")
    
    os.makedirs(COOKIE_DIR, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--no-sandbox"])
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        page.goto("https://chatgpt.com/")
        
        input("👉 Nhấn ENTER khi bạn đã đăng nhập thành công... ")
        
        context.storage_state(path=COOKIE_PATH)
        print(f"✅ Đã lưu phiên đăng nhập tại: {COOKIE_PATH}")
        browser.close()

def analyze_video_with_chatgpt(video_path: str, caption: str) -> dict | None:
    """
    Giả lập upload video lên ChatGPT, điền prompt, chờ và parse JSON.
    """
    if not os.path.exists(COOKIE_PATH):
        print("      ❌ CHƯA ĐĂNG NHẬP CHATGPT. Hãy chạy: python3 chatgpt_automator.py login")
        return None

    prompt_text = load_prompt()
    full_prompt = f"{prompt_text}\n\nVIDEO GỐC:\nCaption/Tiêu đề gốc: {caption}\n\nHãy phân tích video được đính kèm và xuất đúng định dạng JSON."

    print("      🤖 Đang mở ChatGPT qua Playwright...")

    with sync_playwright() as p:
        # Có thể dùng headless=True, nhưng để headless=False giúp tránh bị Cloudflare chặn dễ dàng hơn
        # Để chạy ngầm ổn định, ta sẽ để headless=True, nếu bị chặn thì đổi thành False
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-blink-features=AutomationControlled"])
        context = browser.new_context(
            storage_state=COOKIE_PATH,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        page = context.new_page()

        try:
            page.goto("https://chatgpt.com/", wait_until="domcontentloaded", timeout=60000)
            
            # Chờ ô nhập xuất hiện
            try:
                page.wait_for_selector("#prompt-textarea", timeout=20000)
            except:
                print("      ❌ Không tìm thấy ô nhập liệu. Có thể cookie hết hạn hoặc bị Cloudflare chặn.")
                page.screenshot(path="chatgpt_error.png")
                return None

            print("      📎 Đang upload video lên ChatGPT...")
            # Set file upload
            page.set_input_files("input[type='file']", video_path)
            
            # Chờ 1 chút để nó nhận diện file (nút gửi thường bị vô hiệu hóa khi đang upload)
            time.sleep(3)
            
            # Điền prompt
            print("      ✍️ Đang nhập prompt...")
            page.fill("#prompt-textarea", full_prompt)
            time.sleep(2)
            
            # Click gửi
            print("      🚀 Gửi yêu cầu, chờ ChatGPT phản hồi...")
            page.click('[data-testid="send-button"]')
            
            # Chờ ChatGPT sinh nội dung (Dấu hiệu: nút gửi sẽ biến thành nút dừng, sau đó biến lại thành nút gửi)
            # Ta chờ nút gửi xuất hiện lại VÀ không có trạng thái bị vô hiệu hóa (disabled)
            time.sleep(5) # Đợi nó bắt đầu sinh
            page.wait_for_selector('[data-testid="send-button"]', state="visible", timeout=300000) # Đợi tối đa 5 phút
            time.sleep(2) # Chờ load hẳn

            # Lấy tin nhắn cuối cùng từ trợ lý
            print("      📥 Đang đọc kết quả từ ChatGPT...")
            assistant_messages = page.locator('div[data-message-author-role="assistant"]')
            
            if assistant_messages.count() == 0:
                print("      ❌ Không tìm thấy phản hồi từ trợ lý.")
                return None
                
            last_msg_html = assistant_messages.last.inner_html()
            last_msg_text = assistant_messages.last.inner_text()
            
            # Parse JSON
            raw_text = last_msg_text.strip()
            # Lọc bỏ code blocks
            raw_text = re.sub(r'^```(?:json)?\s*', '', raw_text)
            raw_text = re.sub(r'\s*```$', '', raw_text)
            raw_text = raw_text.strip()
            
            # Tìm đoạn JSON trong text (nếu ChatGPT lỡ chèn chữ thừa)
            match = re.search(r'\{.*\}', raw_text, re.DOTALL)
            if match:
                raw_text = match.group(0)

            result = json.loads(raw_text)
            print("      ✅ Lấy JSON thành công từ ChatGPT!")
            return result

        except Exception as e:
            print(f"      ❌ Lỗi khi tự động hóa ChatGPT: {e}")
            page.screenshot(path="chatgpt_error.png")
            return None
        finally:
            browser.close()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "login":
        login_chatgpt_interactive()
    elif len(sys.argv) > 2:
        res = analyze_video_with_chatgpt(sys.argv[1], sys.argv[2])
        print(json.dumps(res, indent=2, ensure_ascii=False))
    else:
        print("Cách dùng:")
        print("  python3 chatgpt_automator.py login")
        print("  python3 chatgpt_automator.py <video.mp4> <caption_text>")
