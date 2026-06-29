#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════
  chatgpt_automator.py — Tự động hóa ChatGPT qua trình duyệt

  Dùng Chrome profile thật (persistent context) để:
  - Bypass Cloudflare
  - Giữ phiên đăng nhập vĩnh viễn
  - Upload video + gửi prompt + lấy JSON
═══════════════════════════════════════════════════════
"""

import os
import json
import time
import re
from playwright.sync_api import sync_playwright

# apps/creator_facebook/chatgpt_automator.py → creator_facebook → apps → mannyAccount (project root)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
APP_DIR = PROJECT_ROOT
CHROME_PROFILE = os.path.join(PROJECT_ROOT, "data", "chrome_profiles", "chatgpt", "chrome_chatgpt")
PROMPT_FILE = os.path.join(PROJECT_ROOT, "config", "prompts", "prompt_script.txt")


def load_prompt() -> str:
    if os.path.exists(PROMPT_FILE):
        with open(PROMPT_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""


def login_chatgpt_interactive(is_tele_bot: bool = False):
    """
    Mở Chrome thật (có profile) để đăng nhập ChatGPT.
    Profile lưu vĩnh viễn → lần sau không cần login lại.
    """
    profile_dir = CHROME_PROFILE
    if is_tele_bot:
        profile_dir = os.path.join(PROJECT_ROOT, "data", "chrome_profiles", "chatgpt", "chrome_chatgpt_telebot")
        print("╔═══════════════════════════════════════════════════╗")
        print("║  🔑 ĐĂNG NHẬP CHATGPT (TELEGRAM BOT)              ║")
        print("╚═══════════════════════════════════════════════════╝")
    else:
        print("╔═══════════════════════════════════════════════════╗")
        print("║  🔑 ĐĂNG NHẬP CHATGPT                             ║")
        print("╚═══════════════════════════════════════════════════╝")
    print()
    print("📋 Hướng dẫn:")
    print("   1. Chrome sẽ mở trang ChatGPT")
    print("   2. Tick ô 'Xác minh bạn là con người' nếu có")
    print("   3. Đăng nhập tài khoản ChatGPT")
    print("   4. Khi thấy ô chat → quay lại terminal nhấn ENTER")
    print()


    os.makedirs(profile_dir, exist_ok=True)
    # Xóa lock cũ nếu có (tránh lỗi "profile already in use")
    for lock_name in ["SingletonLock", "SingletonCookie", "SingletonSocket"]:
        lock_file = os.path.join(profile_dir, lock_name)
        if os.path.lexists(lock_file):
            try:
                os.remove(lock_file)
            except Exception:
                pass
    print("🧹 Đã kiểm tra và xóa Singleton* cũ")

    with sync_playwright() as p:
        # Dùng persistent context = Chrome profile thật
        # Không bị Cloudflare chặn như browser thường
        context = p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=False,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
            ],
            viewport={"width": 1280, "height": 800},
            locale="vi-VN",
            timezone_id="Asia/Ho_Chi_Minh",
            # Không set user_agent → dùng UA mặc định của Chrome = tự nhiên nhất
        )

        page = context.pages[0] if context.pages else context.new_page()
        page.goto("https://chatgpt.com/", wait_until="domcontentloaded")

        print("🌐 Chrome đã mở. Hãy đăng nhập ChatGPT...")
        print()
        input("👉 Đăng nhập xong → nhấn ENTER ở đây... ")

        print()
        print(f"✅ Profile đã lưu: {profile_dir}")
        print("🎉 Lần sau pipeline sẽ tự động dùng phiên này!")

        context.close()


def analyze_video_with_chatgpt(video_path: str, caption: str, is_tele_bot: bool = False, extra_content: str = "") -> dict | None:
    """
    Tự động:
    1. Mở ChatGPT (dùng Chrome profile đã login)
    2. Upload file video
    3. Gửi prompt + caption + extra_content (nếu có)
    4. Chờ ChatGPT trả lời
    5. Parse JSON từ phản hồi
    """
    profile_dir = CHROME_PROFILE
    if is_tele_bot:
        profile_dir = os.path.join(PROJECT_ROOT, "data", "chrome_profiles", "chatgpt", "chrome_chatgpt_telebot")

    if not os.path.exists(profile_dir):
        print("      ❌ CHƯA LOGIN CHATGPT!")
        if is_tele_bot:
            print("      💡 Chạy: python3 chatgpt_automator.py login tele")
        else:
            print("      💡 Chạy: python3 chatgpt_automator.py login")
        return None

    prompt_text = load_prompt()
    
    extra_instruction = ""
    if extra_content:
        extra_instruction = (
            f"\n[CHỈ ĐẠO CỐT LÕI TỪ NGƯỜI DÙNG]:\n"
            f"Nội dung/Thông điệp chính: {extra_content}\n\n"
            f"⚠️ YÊU CẦU QUAN TRỌNG: Hãy lấy nội dung người dùng vừa cung cấp làm TRỌNG TÂM (chiếm 70% nội dung kịch bản). "
            f"Bắt buộc: 'title_tiktok' và 'hook' PHẢI nhắc trực tiếp đến ít nhất 2 ý/từ khóa quan trọng có trong nội dung này. "
            f"Chỉ sử dụng hình ảnh và bối cảnh từ video gốc để phụ trợ, minh họa cho nội dung này. Kịch bản, Hook và Voice Script phải bám sát tuyệt đối vào chỉ đạo trên!\n"
        )
    else:
        extra_instruction = "\n[CHỈ ĐẠO]: Hãy bám sát vào hình ảnh và nội dung của video gốc để viết content.\n"
    extra_instruction += (
        "\n[YÊU CẦU ĐỊNH DẠNG BẮT BUỘC]:\n"
        "- TUYỆT ĐỐI KHÔNG viết tắt. Mọi từ ngữ phải được viết đầy đủ bằng tiếng Việt chuẩn (Ví dụ: phải viết 'không' thay vì 'ko', 'được' thay vì 'đc', 'thành phố Hồ Chí Minh' thay vì 'TPHCM').\n"
    )
        
    if is_tele_bot:
        extra_instruction += (
            "\n[YÊU CẦU RIÊNG CỦA TELEGRAM BOT]:\n"
            "- TUYỆT ĐỐI KHÔNG sử dụng bất kỳ hashtag nào (ví dụ: #tintuc).\n"
            "- TUYỆT ĐỐI KHÔNG sử dụng emoji, icon hay ký tự đặc biệt trang trí (ví dụ: 🔥, 😊, 📌).\n"
        )
        
    full_prompt = (
        f"{prompt_text}\n\n"
        f"VIDEO GỐC:\n"
        f"Caption/Tiêu đề gốc: {caption}\n"
        f"{extra_instruction}\n"
        f"Hãy phân tích video được đính kèm và xuất đúng định dạng JSON."
    )

    print(f"      🤖 Mở ChatGPT (Profile: {'Tele Bot' if is_tele_bot else 'Main'})...")

    # Xóa lock cũ
    for lock_name in ["SingletonLock", "SingletonCookie", "SingletonSocket"]:
        lock_file = os.path.join(profile_dir, lock_name)
        if os.path.lexists(lock_file):
            try:
                os.remove(lock_file)
            except Exception:
                pass

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=False,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
            ],
            viewport={"width": 1920, "height": 1080},
        )

        page = context.pages[0] if context.pages else context.new_page()

        try:
            page.goto("https://chatgpt.com/", wait_until="domcontentloaded", timeout=60000)
            time.sleep(5)

            # Kiểm tra Cloudflare
            if "challenge" in page.url or "Xác minh" in (page.text_content("body") or ""):
                print("      ❌ Cloudflare chặn! Cần login lại.")
                context.close()
                return None

            # Chờ ô nhập xuất hiện
            try:
                page.wait_for_selector("#prompt-textarea, [contenteditable='true']", timeout=20000)
            except:
                print("      ❌ Không thấy ô chat. Cookie hết hạn?")
                print("      💡 Chạy lại: python3 chatgpt_automator.py login")
                context.close()
                return None

            # Upload video
            print("      📎 Upload video...")
            file_input = page.locator("input[type='file']")
            if file_input.count() > 0:
                file_input.first.set_input_files(video_path)
            else:
                print("      ❌ Không tìm thấy nút upload file")
                context.close()
                return None

            time.sleep(5)  # Chờ upload xong

            # Điền prompt vào ô chat
            print("      ✍️ Nhập prompt...")
            textarea = page.locator("#prompt-textarea, [contenteditable='true']").first

            textarea.click()
            
            # Xóa text cũ nếu có (Ctrl+A rồi Backspace)
            import platform
            modifier = "Meta" if platform.system() == "Darwin" else "Control"
            page.keyboard.press(f"{modifier}+A")
            time.sleep(0.2)
            page.keyboard.press("Backspace")
            time.sleep(0.5)
            
            # Xử lý gõ từng dòng để tránh việc \n kích hoạt gửi tin nhắn sớm
            lines = full_prompt.split('\n')
            for i, line in enumerate(lines):
                if line:
                    page.keyboard.type(line, delay=2)
                # Nếu chưa phải dòng cuối cùng thì ấn Shift+Enter để xuống dòng
                if i < len(lines) - 1:
                    page.keyboard.press("Shift+Enter")
                    time.sleep(0.1)

            time.sleep(2)

            # Click gửi
            print("      🚀 Gửi yêu cầu...")
            send_btn = page.locator('[data-testid="send-button"], button[aria-label="Send"], button[aria-label="Gửi lời nhắc"]').first
            send_btn.click(timeout=120000)

            # Chờ ChatGPT trả lời xong (tối đa 5 phút)
            print("      ⏳ Chờ ChatGPT phản hồi (có thể mất 1-3 phút)...")
            time.sleep(10)  # Chờ bắt đầu sinh

            # Chờ nút gửi xuất hiện lại = ChatGPT đã xong
            for _ in range(60):  # Tối đa 5 phút
                time.sleep(5)
                # Kiểm tra: nếu nút gửi visible VÀ không có animation "đang sinh"
                stop_btn = page.locator('[data-testid="stop-button"], button[aria-label="Stop"]')
                if stop_btn.count() == 0:
                    break  # Không còn nút dừng = đã xong
            else:
                print("      ⚠️ Timeout 5 phút — lấy kết quả hiện tại")

            time.sleep(3)

            # Lấy phản hồi cuối cùng
            print("      📥 Đọc kết quả...")
            messages = page.locator('div[data-message-author-role="assistant"]')

            if messages.count() == 0:
                print("      ❌ Không thấy phản hồi từ ChatGPT")
                context.close()
                return None

            raw_text = messages.last.inner_text().strip()

            # Parse JSON
            # Loại bỏ markdown
            raw_text = re.sub(r'^```(?:json)?\s*', '', raw_text, flags=re.MULTILINE)
            raw_text = re.sub(r'\s*```\s*$', '', raw_text, flags=re.MULTILINE)
            raw_text = raw_text.strip()

            # Tìm JSON object
            match = re.search(r'\{.*\}', raw_text, re.DOTALL)
            if match:
                raw_text = match.group(0)

            result = json.loads(raw_text)

            print("      ✅ Nhận JSON thành công từ ChatGPT!")
            print(f"         Hook: {result.get('hook', '')[:60]}...")

            # Lưu JSON vào file (backup)
            backup_dir = os.path.join(APP_DIR, "data", "ai_results")
            os.makedirs(backup_dir, exist_ok=True)
            backup_file = os.path.join(backup_dir, f"chatgpt_{int(time.time())}.json")
            with open(backup_file, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"         💾 Backup: {backup_file}")

            context.close()
            return result

        except json.JSONDecodeError:
            print(f"      ❌ ChatGPT không trả JSON hợp lệ")
            print(f"         Raw: {raw_text[:300]}...")
            context.close()
            return None
        except Exception as e:
            print(f"      ❌ Lỗi: {e}")
            try:
                page.screenshot(path=os.path.join(APP_DIR, "chatgpt_error.png"))
                print(f"         📸 Screenshot: chatgpt_error.png")
            except:
                pass
            context.close()
            return None


# ── CLI ──
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "login":
        if len(sys.argv) > 2 and sys.argv[2] == "tele":
            login_chatgpt_interactive(is_tele_bot=True)
        else:
            login_chatgpt_interactive()
    elif len(sys.argv) > 2:
        res = analyze_video_with_chatgpt(sys.argv[1], sys.argv[2])
        if res:
            print(json.dumps(res, indent=2, ensure_ascii=False))
    else:
        print("Cách dùng:")
        print("  python3 chatgpt_automator.py login                  → Đăng nhập ChatGPT (Main)")
        print("  python3 chatgpt_automator.py login tele             → Đăng nhập ChatGPT (Tele Bot)")
        print("  python3 chatgpt_automator.py <video.mp4> <caption>  → Test phân tích")
