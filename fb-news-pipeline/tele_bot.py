import os
import telebot
import threading
from dotenv import load_dotenv
import re
from fb_pipeline import FBNewsPipeline
import uuid

load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not BOT_TOKEN:
    print("⚠️ Vui lòng thêm TELEGRAM_BOT_TOKEN vào file .env")
    exit(1)

bot = telebot.TeleBot(BOT_TOKEN)

def extract_video_id(url):
    # Dùng regex đơn giản để bóc ID hoặc trả về uuid ngẫu nhiên nếu không tìm thấy
    match = re.search(r'/video/(\d+)', url) or re.search(r'v=(\d+)', url) or re.search(r'/(?:reel|shorts)/(\d+)', url) or re.search(r'/videos/(\d+)', url)
    if match:
        return match.group(1)
    return uuid.uuid4().hex[:8]

def process_video_thread(message, url):
    chat_id = message.chat.id
    try:
        # Giả lập video object
        video = {
            "url": url,
            "video_id": extract_video_id(url),
            "caption": "Telegram Link"
        }
        
        # Giả lập source object
        source = {
            "id": None, 
            "delogo": "" # Có thể cấu hình sau
        }
        
        pipeline = FBNewsPipeline()
        
        def on_success(drive_link, final_path):
            bot.send_message(chat_id, f"🎉 Đã làm xong video!\n🔗 Link Google Drive: {drive_link}")
            
            # Gửi video trực tiếp vào Telegram (nén trước)
            try:
                if os.path.exists(final_path):
                    import subprocess
                    compressed_path = final_path.replace(".mp4", "_compressed.mp4")
                    bot.send_message(chat_id, "🗜 Đang nén video để gửi trực tiếp vào Telegram...")
                    
                    # Lệnh nén video bằng FFmpeg (giảm bitrate, nhanh)
                    cmd = [
                        "ffmpeg", "-y", "-i", final_path,
                        "-vcodec", "libx264", "-crf", "32", "-preset", "veryfast",
                        "-c:a", "aac", "-b:a", "64k",
                        compressed_path
                    ]
                    subprocess.run(cmd, capture_output=True)
                    
                    # Lấy dung lượng file sau khi nén
                    send_path = compressed_path if os.path.exists(compressed_path) else final_path
                    size_mb = os.path.getsize(send_path) / 1024 / 1024
                    
                    if size_mb < 50:
                        bot.send_message(chat_id, f"📤 Đang tải video lên Telegram ({size_mb:.1f}MB)...")
                        with open(send_path, 'rb') as f:
                            bot.send_video(chat_id, f, caption="🎬 Thành phẩm của bạn đây!")
                    else:
                        bot.send_message(chat_id, f"⚠️ Video dù đã nén vẫn có dung lượng {size_mb:.1f}MB (> 50MB), vượt quá giới hạn gửi trực tiếp của Telegram API. Vui lòng tải qua link Google Drive.")
                        
                    if os.path.exists(compressed_path):
                        os.remove(compressed_path)
            except Exception as e:
                bot.send_message(chat_id, f"⚠️ Lỗi khi tải file lên Telegram: {e}")
                
        bot.send_message(chat_id, "⏳ Bắt đầu phân tích kịch bản và render video (mất khoảng 2-3 phút)...")
        
        success = pipeline._process_one_video(video, source, on_success=on_success)
        
        if not success:
            bot.send_message(chat_id, "❌ Quá trình tạo video thất bại. Vui lòng kiểm tra lại link hoặc xem log hệ thống.")
            
    except Exception as e:
        bot.send_message(chat_id, f"❌ Có lỗi xảy ra: {e}")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    text = message.text
    chat_id = message.chat.id
    
    urls = re.findall(r'(https?://[^\s]+)', text)
    if not urls:
        bot.send_message(chat_id, "👋 Chào bạn! Hãy dán 1 link TikTok hoặc Facebook vào đây, tôi sẽ tự động xử lý video cho bạn!")
        return
        
    for url in urls:
        if 'tiktok.com' in url or 'facebook.com' in url or 'fb.watch' in url:
            bot.send_message(chat_id, f"📥 Đã nhận link: {url}")
            # Chạy thread ngầm để bot có thể nhận nhiều link cùng lúc
            threading.Thread(target=process_video_thread, args=(message, url)).start()
        else:
            bot.send_message(chat_id, f"⚠️ Hiện tại tôi chỉ hỗ trợ link TikTok và Facebook.\nLink này không hợp lệ: {url}")

if __name__ == '__main__':
    print("🚀 Telegram Bot đang chạy! Chờ tin nhắn...")
    try:
        bot.infinity_polling()
    except KeyboardInterrupt:
        print("Đã dừng Bot.")
