import os
import requests
from bs4 import BeautifulSoup

class ArticleCrawler:
    def __init__(self):
        # Tránh bị web báo chặn chặn Bot
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def crawl(self, url, save_dir):
        print(f"🕷️ Đang cào bài báo từ: {url}")
        try:
            res = requests.get(url, headers=self.headers, timeout=15)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, "html.parser")
            
            # 1. Trích xuất Tiêu đề
            title = ""
            if soup.h1:
                title = soup.h1.get_text(strip=True)
            elif soup.title:
                title = soup.title.get_text(strip=True)
                
            # 2. Trích xuất Text Content (bỏ qua các đoạn quá ngắn)
            paragraphs = soup.find_all("p")
            text_lines = []
            for p in paragraphs:
                txt = p.get_text(strip=True)
                if len(txt) > 40: # Lọc bỏ các text rác, caption ngắn
                    text_lines.append(txt)
            
            full_text = "\n".join(text_lines)
            
            # 3. Trích xuất Hình ảnh
            img_urls = []
            # Bắt cả src và data-src (vì nhiều trang báo dùng lazy load)
            for img in soup.find_all("img"):
                src = img.get("data-src") or img.get("src")
                if src and src.startswith("http"):
                    # Loại bỏ các ảnh logo, icon, avatar (dựa vào từ khóa thường thấy)
                    if any(x in src.lower() for x in ['logo', 'icon', 'avatar', 'thumb']):
                        continue
                    img_urls.append(src)
            
            # Xóa trùng lặp và chỉ lấy tối đa 5-7 ảnh đầu tiên của bài báo
            img_urls = list(dict.fromkeys(img_urls))[:7]
            
            # 4. Tải ảnh về thư mục
            downloaded_images = []
            os.makedirs(save_dir, exist_ok=True)
            for idx, img_url in enumerate(img_urls):
                try:
                    img_res = requests.get(img_url, headers=self.headers, timeout=10)
                    if img_res.status_code == 200:
                        img_path = os.path.join(save_dir, f"img_{idx}.jpg")
                        with open(img_path, "wb") as f:
                            f.write(img_res.content)
                        downloaded_images.append(img_path)
                except Exception as e:
                    print(f"   ⚠️ Lỗi tải ảnh {idx}: {e}")
                    
            print(f"✅ Đã cào xong: Tiêu đề + {len(full_text)} ký tự + {len(downloaded_images)} ảnh.")
            return {
                "title": title,
                "content": full_text[:4000], # Cắt tối đa 4000 ký tự (đủ cho ChatGPT)
                "images": downloaded_images
            }
            
        except Exception as e:
            print(f"❌ Lỗi khi cào bài báo: {e}")
            return None

# Test thử nếu chạy file này trực tiếp
if __name__ == "__main__":
    crawler = ArticleCrawler()
    test_dir = os.path.join(os.path.dirname(__file__), "test_article_images")
    res = crawler.crawl("https://kenh14.vn/can-canh-hien-truong-vu-chay-lon-tai-xuong-go-o-ha-noi-cot-khoi-den-boc-cao-hang-chuc-met-20240312080512345.chn", test_dir)
    if res:
        print("Tiêu đề:", res["title"])
        print("Số lượng ảnh:", len(res["images"]))
