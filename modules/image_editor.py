import os
import requests
import textwrap
from datetime import datetime
import PIL.Image, PIL.ImageDraw, PIL.ImageFont, PIL.ImageEnhance
# Import cấu hình từ folder config
from config.settings import FRAME_DIR, TEMPLATE_FILE, FONT_NAME

IMAGE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

def create_frame_with_text(fallback_img_path, text_content):
    try:
        bg_img = None
        if os.path.exists(TEMPLATE_FILE):
            try: bg_img = PIL.Image.open(TEMPLATE_FILE).convert("RGBA")
            except: pass

        if bg_img is None and fallback_img_path:
            if fallback_img_path.startswith("http"):
                raw = requests.get(fallback_img_path, headers=IMAGE_HEADERS, stream=True, timeout=10).raw
                bg_img = PIL.Image.open(raw).convert("RGBA")
            elif os.path.exists(fallback_img_path):
                bg_img = PIL.Image.open(fallback_img_path).convert("RGBA")

        if bg_img is None:
            W, H = 1080, 1920
        else:
            W, H = bg_img.size

        text_layer = PIL.Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw = PIL.ImageDraw.Draw(text_layer)

        box_top_y = int(H * 0.68)
        box_bottom_y = int(H * 0.90)
        box_height = box_bottom_y - box_top_y
        margin_x = int(W * 0.12)
        max_text_width = W - (2 * margin_x)
        font_size = int(W / 22)
        if font_size < 30: font_size = 30

        try:
            if os.path.exists(FONT_NAME):
                font = PIL.ImageFont.truetype(FONT_NAME, font_size)
            else:
                font = PIL.ImageFont.truetype("arialbd.ttf", font_size)
        except:
            font = PIL.ImageFont.load_default()

        avg_char_width = font_size * 0.58
        chars_per_line = int(max_text_width / avg_char_width)
        wrapped_text = textwrap.fill(text_content.upper(), width=chars_per_line)

        bbox = draw.textbbox((0, 0), wrapped_text, font=font, align="center")
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        x = (W - text_w) / 2
        y = box_top_y + (box_height - text_h) / 2

        draw.text((x + 3, y + 3), wrapped_text, font=font, align="center", fill=(0,0,0, 80))
        draw.text((x, y), wrapped_text, font=font, align="center", fill="white")

        output_filename = f"text_layer_{int(datetime.now().timestamp())}.png"
        save_path = os.path.join(FRAME_DIR, output_filename)
        text_layer.save(save_path, "PNG")
        return save_path
    except Exception as e:
        print(f"Error creating text layer: {e}")
        return None

def create_ui_thumbnail(img_path, index=None):
    try:
        if img_path.startswith("http"):
            raw = requests.get(img_path, stream=True, timeout=5).raw
            img = PIL.Image.open(raw).convert("RGBA")
        else:
            img = PIL.Image.open(img_path).convert("RGBA")

        img.thumbnail((400, 400), PIL.Image.LANCZOS)

        if index is None:
            enhancer = PIL.ImageEnhance.Brightness(img)
            img = enhancer.enhance(0.4)
            return img

        draw = PIL.ImageDraw.Draw(img)
        w, h = img.size
        text = str(index)
        font_size = int(h / 5)
        if font_size < 30: font_size = 30
        try: font = PIL.ImageFont.truetype("arial.ttf", font_size)
        except: font = PIL.ImageFont.load_default()

        box_w = int(font_size * 1.5)
        box_h = int(font_size * 1.5)
        pad = 5
        x1, y1 = w - box_w - pad, pad
        x2, y2 = w - pad, box_h + pad
        draw.rectangle([x1, y1, x2, y2], fill="red", outline="white", width=3)
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_w = text_bbox[2] - text_bbox[0]
        text_h = text_bbox[3] - text_bbox[1]
        text_x = x1 + (box_w - text_w) / 2
        text_y = y1 + (box_h - text_h) / 2
        draw.text((text_x, text_y - (text_h * 0.1)), text, fill="white", font=font)
        return img
    except: return None