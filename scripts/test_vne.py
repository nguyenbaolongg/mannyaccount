import requests
from bs4 import BeautifulSoup
import json

res = requests.get('https://vnexpress.net/vne-go')
soup = BeautifulSoup(res.text, 'html.parser')
videos = soup.find_all('video')
print(f"Found {len(videos)} videos directly in HTML.")

for article in soup.find_all('article', class_='item-news'):
    title = article.find('h2', class_='title-news')
    title_text = title.text.strip() if title else 'No title'
    print(f"Article: {title_text}")
    v = article.find('video')
    if v:
        print(f"  Video src: {v.get('src')}")
        source = v.find('source')
        if source:
             print(f"  Source: {source.get('src')}")

# Try to find scripts containing video data
for s in soup.find_all('script'):
    if s.string and 'mp4' in s.string:
        import re
        urls = re.findall(r'(https?://[^"]+\.(?:mp4|m3u8)[^"]*)', s.string)
        if urls:
            print("Found in script:", urls[0])
            break
