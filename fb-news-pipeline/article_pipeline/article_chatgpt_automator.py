#!/usr/bin/env python3
import os
import json
import time
import re
from playwright.sync_api import sync_playwright

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROMPT_FILE = os.path.join(PROJECT_ROOT, "config", "prompt_article.txt")

def get_chrome_profile_dir(id_tiktok: str) -> str:
    return os.path.join(PROJECT_ROOT, "data", f"chrome_chatgpt_{id_tiktok}")

def load_prompt() -> str:
    if os.path.exists(PROMPT_FILE):
        with open(PROMPT_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return """Bạn là một Biên tập viên TikTok/Shorts chuyên nghiệp. Hãy đọc bài báo dưới đây và viết 1 kịch bản video.
Yêu cầu trả về chuẩn định dạng JSON, TUYỆT ĐỐI không có văn bản nào ngoài JSON.
{
  "hook": "1-2 câu giật gân, thu hút sự chú ý",
  "script_voice": "Nội dung chi tiết tóm tắt bài báo",
  "title_tiktok": "Tiêu đề để đăng lên TikTok (có hashtag)",
  "image_prompts": ["mô tả ảnh 1", "mô tả ảnh 2"]
}"""

def login_chatgpt_interactive(id_tiktok: str):
    print("╔═══════════════════════════════════════════════════╗")
    print(f"║  🔑 ĐĂNG NHẬP CHATGPT CHO KÊNH: {id_tiktok:<16}  ║")
    print("╚═══════════════════════════════════════════════════╝")
    profile_dir = get_chrome_profile_dir(id_tiktok)
    os.makedirs(profile_dir, exist_ok=True)
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=False,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
            viewport={"width": 1280, "height": 800},
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto("https://chatgpt.com/", wait_until="domcontentloaded")
        print("🌐 Chrome đã mở. Hãy đăng nhập ChatGPT...")
        input("👉 Đăng nhập xong → nhấn ENTER ở đây... ")
        context.close()

def analyze_article_with_chatgpt(article_text: str, id_tiktok: str) -> dict | None:
    profile_dir = get_chrome_profile_dir(id_tiktok)
    if not os.path.exists(profile_dir):
        print(f"      ❌ CHƯA LOGIN CHATGPT CHO KÊNH {id_tiktok}!")
        return None

    prompt_text = load_prompt()
    full_prompt = (
        f"{prompt_text}\n\n"
        f"BÀI BÁO:\n{article_text}\n\n"
        f"Hãy phân tích và BẮT BUỘC xuất đúng định dạng JSON, có thêm trường \"id_tiktok\": \"{id_tiktok}\"."
    )

    print(f"      🤖 Mở ChatGPT (Automator) cho kênh {id_tiktok}...")
    lock_file = os.path.join(profile_dir, "SingletonLock")
    if os.path.exists(lock_file):
        try: os.remove(lock_file)
        except: pass

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=False,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
            viewport={"width": 1280, "height": 800},
        )

        page = context.pages[0] if context.pages else context.new_page()

        try:
            page.goto("https://chatgpt.com/", wait_until="domcontentloaded", timeout=60000)
            time.sleep(5)

            if "challenge" in page.url or "Xác minh" in (page.text_content("body") or ""):
                print("      ❌ Cloudflare chặn! Cần login lại ChatGPT.")
                context.close()
                return None

            try:
                page.wait_for_selector("#prompt-textarea, [contenteditable='true']", timeout=20000)
            except:
                print("      ❌ Không thấy ô chat.")
                context.close()
                return None

            print("      ✍️ Nhập prompt và nội dung bài báo...")
            textarea = page.locator("#prompt-textarea, [contenteditable='true']").first
            textarea.click()

            # Không dùng bàn phím type chậm vì nội dung bài báo rất dài sẽ mất nhiều thời gian
            # Thay vào đó dùng JS paste nội dung vào
            textarea.fill(full_prompt)
            time.sleep(1)

            print("      🚀 Gửi yêu cầu...")
            send_btn = page.locator('[data-testid="send-button"], button[aria-label="Send"]').first
            send_btn.click()

            print("      ⏳ Chờ ChatGPT phản hồi (có thể mất 1-2 phút)...")
            time.sleep(10) 

            for _ in range(60):
                time.sleep(5)
                stop_btn = page.locator('[data-testid="stop-button"], button[aria-label="Stop"]')
                if stop_btn.count() == 0:
                    break
            else:
                print("      ⚠️ Timeout 5 phút — lấy kết quả hiện tại")

            time.sleep(3)
            print("      📥 Đọc kết quả...")
            messages = page.locator('div[data-message-author-role="assistant"]')

            if messages.count() == 0:
                print("      ❌ Không thấy phản hồi từ ChatGPT")
                context.close()
                return None

            raw_text = messages.last.inner_text().strip()

            raw_text = re.sub(r'^```(?:json)?\s*', '', raw_text, flags=re.MULTILINE)
            raw_text = re.sub(r'\s*```\s*$', '', raw_text, flags=re.MULTILINE)
            raw_text = raw_text.strip()

            match = re.search(r'\{.*\}', raw_text, re.DOTALL)
            if match:
                raw_text = match.group(0)

            result = json.loads(raw_text)
            result["id_tiktok"] = id_tiktok # Ép cứng lại đề phòng AI quên

            print("      ✅ Nhận JSON thành công từ ChatGPT UI!")
            print(f"         Hook: {result.get('hook', '')[:60]}...")
            
            context.close()
            return result

        except json.JSONDecodeError:
            print(f"      ❌ ChatGPT không trả JSON hợp lệ")
            print(f"         Raw: {raw_text[:300]}...")
            context.close()
            return None
        except Exception as e:
            print(f"      ❌ Lỗi: {e}")
            context.close()
            return None

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2 and sys.argv[1] == "login":
        login_chatgpt_interactive(sys.argv[2])
    else:
        print("Cách dùng: python3 article_chatgpt_automator.py login <id_tiktok>")
