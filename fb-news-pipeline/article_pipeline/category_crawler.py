import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

class CategoryCrawler:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def get_latest_articles(self, category_url: str, max_links=5) -> list:
        print(f"📡 Đang quét danh mục: {category_url}")
        try:
            res = requests.get(category_url, headers=self.headers, timeout=15)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, "html.parser")
            
            article_links = []
            
            # Quét tất cả thẻ <a>
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                # Chuẩn hóa link tương đối thành tuyệt đối
                full_url = urljoin(category_url, href)
                
                # Loại bỏ link không hợp lệ hoặc link ảnh
                if full_url.endswith((".jpg", ".png", ".webp", ".gif")):
                    continue
                    
                # Nhận diện link bài báo (thường kết thúc bằng .html hoặc .chn)
                # Hoặc chứa từ khóa dạng gạch nối dài
                if (".html" in full_url or ".chn" in full_url) and len(full_url.split("/")[-1]) > 15:
                    if full_url not in article_links:
                        article_links.append(full_url)
                        
            # Lấy 5 bài báo mới nhất
            return article_links[:max_links]
            
        except Exception as e:
            print(f"❌ Lỗi quét danh mục {category_url}: {e}")
            return []

if __name__ == "__main__":
    crawler = CategoryCrawler()
    links = crawler.get_latest_articles("https://vnexpress.net/giai-tri")
    for link in links:
        print("Bắt được link:", link)
