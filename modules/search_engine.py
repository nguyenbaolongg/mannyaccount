from duckduckgo_search import DDGS
import time

def search_images_on_web(keywords, max_results=3):
    """
    Tìm kiếm hình ảnh dựa trên từ khóa sử dụng DuckDuckGo.
    Trả về danh sách các URL hình ảnh.
    """
    found_images = []
    print(f"🔍 Đang tìm kiếm: {keywords}...")

    try:
        with DDGS() as ddgs:
            # Tìm kiếm hình ảnh
            results = list(ddgs.images(
                keywords,
                region="wt-wt", # World-wide
                safesearch="off",
                max_results=max_results
            ))

            for res in results:
                img_url = res.get('image')
                if img_url:
                    found_images.append(img_url)

    except Exception as e:
        print(f"❌ Lỗi tìm kiếm '{keywords}': {e}")

    return found_images