#!/usr/bin/env python3
import os
import json
import time
import re
from playwright.sync_api import sync_playwright

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROMPT_FILE = os.path.join(PROJECT_ROOT, "config", "prompts", "prompt_article.txt")

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

def analyze_article_with_chatgpt(article_url: str, id_tiktok: str) -> dict | None:
    profile_dir = get_chrome_profile_dir(id_tiktok)
    if not os.path.exists(profile_dir):
        print(f"      ❌ CHƯA LOGIN CHATGPT CHO KÊNH {id_tiktok}!")
        return None

    prompt_text = load_prompt()
    full_prompt = (
        f"👉 ĐƯỜNG DẪN BÀI BÁO CẦN PHÂN TÍCH: {article_url}\n\n"
        f"Hãy click hoặc truy cập vào đường dẫn trên, đọc nội dung bài báo và thực hiện theo yêu cầu dưới đây:\n\n"
        f"{prompt_text}\n\n"
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

            print("      ✍️ Nhập prompt và nội dung bài báo (gõ phím ảo)...")
            textarea = page.locator("#prompt-textarea, [contenteditable='true']").first
            textarea.click()

            # Xóa sạch text cũ trong ô chat trước khi gõ prompt mới
            textarea.press("Control+a")
            time.sleep(0.3)
            textarea.press("Backspace")
            time.sleep(0.5)

            # Thay vì type từng chữ tốn thời gian, dùng insert_text để paste ngay lập tức
            page.keyboard.insert_text(full_prompt)
            time.sleep(1)

            print("      🚀 Gửi yêu cầu...")
            # Thử nhiều selector khác nhau vì ChatGPT thay đổi UI thường xuyên
            send_selectors = [
                '[data-testid="send-button"]',
                'button[aria-label="Send prompt"]',
                'button[aria-label="Send"]',
                'button[aria-label="Gửi"]',
                '#composer-submit-button',
                'form button[type="submit"]',
                'button:has(svg path[d*="M15.192"])',  # SVG arrow icon
                'button:has(> svg)',  # Fallback: any button with SVG inside the composer
            ]
            sent = False
            for sel in send_selectors:
                try:
                    btn = page.locator(sel).first
                    if btn.is_visible(timeout=2000):
                        btn.click()
                        sent = True
                        print("      ✅ Đã nhấn nút Send")
                        break
                except:
                    continue
            
            if not sent:
                # Fallback: Nhấn Enter để gửi
                print("      ⚠️ Không tìm thấy nút Send, dùng Enter để gửi...")
                textarea.press("Enter")
                time.sleep(1)

            print("      ⏳ Chờ ChatGPT phản hồi (có thể mất 1-2 phút)...")
            time.sleep(10) 

            for _ in range(60):
                time.sleep(5)
                stop_btn = page.locator('[data-testid="stop-button"], button[aria-label="Stop generating"], button[aria-label="Stop"], button[aria-label="Dừng"]')
                if stop_btn.count() == 0:
                    break
            else:
                print("      ⚠️ Timeout 5 phút — lấy kết quả hiện tại")

            time.sleep(15)  # Chờ thêm để ChatGPT render xong hoàn toàn
            print("      📥 Đọc kết quả...")
            messages = page.locator('div[data-message-author-role="assistant"]')

            if messages.count() == 0:
                print("      ❌ Không thấy phản hồi từ ChatGPT")
                context.close()
                return None

            raw_text = messages.last.inner_text().strip()

            def _extract_json_from_text(text):
                """Trích xuất và sửa JSON từ phản hồi ChatGPT."""
                # Thử lấy nội dung từ code block nếu có
                text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.MULTILINE)
                text = re.sub(r'\s*```\s*$', '', text, flags=re.MULTILINE)
                text = text.strip()

                # Xóa ký tự Unicode vô hình và control characters
                text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
                # Thay smart quotes thành quotes thường
                text = text.replace('\u201c', '"').replace('\u201d', '"')
                text = text.replace('\u2018', "'").replace('\u2019', "'")

                result_text = None
                match = re.search(r'\{.*\}', text, re.DOTALL)
                if match:
                    result_text = match.group(0)

                is_truncated = False
                if not result_text:
                    is_truncated = True
                else:
                    # Chạy thử json.loads để kiểm tra xem đã parse thành công chưa
                    try:
                        # Thử xóa xuống dòng và trailing commas
                        clean_text = re.sub(r'(?<!\\)\n', ' ', result_text)
                        clean_text = re.sub(r',\s*([}\]])', r'\1', clean_text)
                        json.loads(clean_text)
                    except json.JSONDecodeError:
                        is_truncated = True # Nếu parse lỗi -> JSON chưa sinh xong -> Ép chờ tiếp

                return result_text, is_truncated


            # Lần 1: Thử trích xuất JSON
            json_text, is_truncated = _extract_json_from_text(raw_text)

            # Nếu JSON bị cắt cụt → chờ thêm rồi đọc lại (ChatGPT có thể chưa render xong)
            if is_truncated or json_text is None:
                print("      🔄 JSON chưa hoàn chỉnh, chờ thêm 15 giây để ChatGPT render xong...")
                time.sleep(15)
                # Đọc lại phản hồi mới nhất
                messages = page.locator('div[data-message-author-role="assistant"]')
                if messages.count() > 0:
                    raw_text = messages.last.inner_text().strip()
                    json_text_retry, is_truncated_retry = _extract_json_from_text(raw_text)
                    if json_text_retry:
                        json_text = json_text_retry
                        if not is_truncated_retry:
                            print("      ✅ Đọc lại thành công, JSON đã hoàn chỉnh!")

            if not json_text:
                print(f"      ❌ Không tìm thấy JSON trong phản hồi ChatGPT")
                print(f"         Raw: {raw_text[:300]}...")
                context.close()
                return None

            # Xóa trailing commas trước } hoặc ] (lỗi hay gặp từ AI)
            json_text = re.sub(r',\s*([}\]])', r'\1', json_text)

            try:
                result = json.loads(json_text)
            except json.JSONDecodeError as je:
                # Thử sửa lỗi phổ biến: xuống dòng trong string
                json_text_fixed = re.sub(r'(?<!\\)\n', ' ', json_text)
                try:
                    result = json.loads(json_text_fixed)
                except json.JSONDecodeError:
                    print(f"      ❌ ChatGPT không trả JSON hợp lệ")
                    print(f"         Lỗi: {je}")
                    print(f"         Raw: {json_text[:500]}...")
                    context.close()
                    return None
            # Đảm bảo tất cả các trường bắt buộc luôn có giá trị (để trống nếu AI không trả về)
            defaults = {
                "hook": "",
                "script_voice": "",
                "title_tiktok": "",
                "image_prompts": [],
            }
            for key, default_val in defaults.items():
                if key not in result:
                    result[key] = default_val

            result["id_tiktok"] = id_tiktok  # Ép cứng lại đề phòng AI quên

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
