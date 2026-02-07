import os
import requests
import shutil
import random
from datetime import datetime
from moviepy.editor import AudioFileClip, ImageClip, concatenate_videoclips, CompositeVideoClip, vfx, concatenate_audioclips
import streamlit as st
from config.settings import IMAGE_ROOT_DIR
from PIL import Image, ImageFilter, ImageOps
import numpy as np

# === CẤU HÌNH ===
TARGET_VIDEO_FOLDER = os.path.join(os.path.expanduser("~"), "Videos")
if not os.path.exists(TARGET_VIDEO_FOLDER):
    try: os.makedirs(TARGET_VIDEO_FOLDER)
    except: TARGET_VIDEO_FOLDER = os.getcwd()

DOWNLOAD_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.google.com/"
}

# ==============================================================================
# HÀM HỖ TRỢ (Tải file, Xử lý ảnh)
# ==============================================================================

def download_or_copy_file(source, save_path):
    """Tải file từ URL hoặc copy từ đường dẫn máy tính"""
    try:
        if not source: return False
        if source.startswith("http"):
            res = requests.get(source, headers=DOWNLOAD_HEADERS, stream=True, timeout=10, allow_redirects=True)
            res.raise_for_status()
            with open(save_path, 'wb') as f:
                for chunk in res.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        else:
            if os.path.exists(source):
                shutil.copy2(source, save_path)
                return True
            return False
    except Exception as e:
        print(f"⚠️ Lỗi tải file {source}: {e}")
        return False

def create_slide_with_effect(image_path, duration, target_res):
    """Tạo clip ảnh với hiệu ứng mờ nền và zoom nhẹ (Ken Burns effect)"""
    w_target, h_target = target_res

    pil_img = Image.open(image_path).convert("RGB")
    img_w, img_h = pil_img.size

    # 1. TẠO NỀN MỜ (BACKGROUND)
    bg_img = ImageOps.fit(pil_img, (w_target, h_target), method=Image.LANCZOS)
    bg_img = bg_img.filter(ImageFilter.GaussianBlur(radius=50))
    bg_clip = ImageClip(np.array(bg_img)).set_duration(duration)

    # 2. TẠO ẢNH CHÍNH (FOREGROUND)
    # Tính toán resize để vừa chiều ngang (hoặc dọc nếu ảnh quá dẹt)
    scale_factor = w_target / img_w
    new_w = w_target
    new_h = int(img_h * scale_factor)

    # Nếu ảnh quá dẹt (panorama) làm chiều cao quá bé -> Tăng kích thước theo chiều cao
    if new_h < h_target * 0.6:
        scale_factor = (h_target * 0.6) / img_h
        new_h = int(h_target * 0.6)
        new_w = int(img_w * scale_factor)

    # Thu nhỏ 95% để tạo viền đẹp mắt
    final_w = int(new_w * 0.95)
    final_h = int(new_h * 0.95)

    fg_img_resized = pil_img.resize((final_w, final_h), Image.LANCZOS)
    fg_clip = ImageClip(np.array(fg_img_resized)).set_duration(duration).set_position("center")

    # 3. HIỆU ỨNG ZOOM (IN/OUT)
    zoom_speed = 0.05
    zoom_mode = random.choice(['in', 'out'])

    if zoom_mode == 'in':
        fg_clip = fg_clip.resize(lambda t: 1 + (zoom_speed/duration) * t)
    else:
        start_zoom = 1 + zoom_speed
        fg_clip = fg_clip.resize(lambda t: start_zoom - (zoom_speed/duration) * t)

    return CompositeVideoClip([bg_clip, fg_clip], size=target_res).set_duration(duration)

# ==============================================================================
# HÀM CHÍNH: TẠO VIDEO TỪ DỮ LIỆU
# ==============================================================================

def create_video_from_scraped_data(
        audio_url,
        image_list,
        resolution_tuple,
        output_filename="video.mp4",
        # [CẬP NHẬT] Tách thành 2 biến frame riêng biệt
        title_frame_path=None,
        content_frame_path=None,
        text_overlay_path=None,
        logo_path=None,
        title_audio_url=None
):
    # Tạo thư mục tạm thời
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_asset_dir = os.path.join(IMAGE_ROOT_DIR, timestamp)
    if not os.path.exists(temp_asset_dir): os.makedirs(temp_asset_dir)

    status_text = st.empty()
    status_text.info(f"📂 Đang chuẩn bị dữ liệu...")

    # Khởi tạo biến để dọn dẹp sau khi chạy
    final_video = None
    final_audio = None
    clips_to_close = []

    try:
        # ------------------------------------------------------------------
        # BƯỚC 1: TẢI VÀ XỬ LÝ AUDIO
        # ------------------------------------------------------------------
        audio_paths = []

        # A. Voice Title (Nếu có)
        clip_title_audio = None
        if title_audio_url:
            path_title = os.path.join(temp_asset_dir, "title.mp3")
            if download_or_copy_file(title_audio_url, path_title):
                clip_title_audio = AudioFileClip(path_title)
                clips_to_close.append(clip_title_audio)
                audio_paths.append(clip_title_audio)

        # B. Voice Content (Bắt buộc)
        path_content = os.path.join(temp_asset_dir, "content.mp3")
        if not download_or_copy_file(audio_url, path_content):
            raise Exception("❌ Không tải được Voice Kịch bản.")

        clip_content_audio = AudioFileClip(path_content)
        clips_to_close.append(clip_content_audio)
        audio_paths.append(clip_content_audio)

        # C. Ghép Audio tổng
        if len(audio_paths) > 1:
            final_audio = concatenate_audioclips(audio_paths)
        else:
            final_audio = clip_content_audio

        # ------------------------------------------------------------------
        # BƯỚC 2: TẢI ẢNH
        # ------------------------------------------------------------------
        status_text.info(f"⚡ Đang tải ảnh...")
        local_img_paths = []
        for i, source in enumerate(image_list):
            source = source.strip()
            if not source: continue
            save_path = os.path.join(temp_asset_dir, f"img_{i}.jpg")
            if download_or_copy_file(source, save_path):
                if os.path.exists(save_path) and os.path.getsize(save_path) > 500:
                    local_img_paths.append(save_path)

        if not local_img_paths: raise Exception("❌ Không có ảnh hợp lệ nào.")
        if len(local_img_paths) == 1: local_img_paths.append(local_img_paths[0]) # Duplicate nếu chỉ 1 ảnh

        w, h = resolution_tuple

        # ------------------------------------------------------------------
        # BƯỚC 3: DỰNG HÌNH (VIDEO COMPOSITION)
        # ------------------------------------------------------------------

        video_segments = []

        # === TRƯỜNG HỢP A: CÓ VOICE TITLE (Tách Intro & Main) ===
        if clip_title_audio:
            status_text.info(f"✨ Đang dựng Intro (Frame Title)...")

            # --- [PHẦN INTRO] ---
            dur_intro = clip_title_audio.duration
            img_intro = local_img_paths[0] # Dùng ảnh đầu tiên cho Intro

            # 1. Slide ảnh nền
            intro_base = create_slide_with_effect(img_intro, dur_intro, resolution_tuple)
            clips_to_close.append(intro_base)

            intro_layers = [intro_base]

            # 2. Lớp phủ Frame Title
            if title_frame_path and os.path.exists(title_frame_path):
                t_frame = ImageClip(title_frame_path, transparent=True) \
                    .set_duration(dur_intro) \
                    .resize(newsize=(w, h)) \
                    .set_position(("center", "center"))
                intro_layers.append(t_frame)

            intro_video_part = CompositeVideoClip(intro_layers).set_duration(dur_intro)
            clips_to_close.append(intro_video_part)
            video_segments.append(intro_video_part)

            # --- [PHẦN MAIN] ---
            status_text.info(f"✨ Đang dựng Nội dung chính (Frame Content)...")
            dur_main = clip_content_audio.duration
            imgs_main = local_img_paths[1:] # Các ảnh còn lại
            if not imgs_main: imgs_main = [local_img_paths[0]] # Fallback

            slide_duration = dur_main / len(imgs_main)
            main_clips = []

            # Tạo slide cho từng ảnh
            for img_p in imgs_main:
                try:
                    sl = create_slide_with_effect(img_p, slide_duration, resolution_tuple)
                    main_clips.append(sl)
                    clips_to_close.append(sl)
                except: pass

            # Ghép các slide lại thành video nền
            main_base_video = concatenate_videoclips(main_clips, method="compose").set_duration(dur_main)
            main_layers = [main_base_video]

            # 2. Lớp phủ Frame Content
            if content_frame_path and os.path.exists(content_frame_path):
                c_frame = ImageClip(content_frame_path, transparent=True) \
                    .set_duration(dur_main) \
                    .resize(newsize=(w, h)) \
                    .set_position(("center", "center"))
                main_layers.append(c_frame)

            main_video_part = CompositeVideoClip(main_layers).set_duration(dur_main)
            clips_to_close.append(main_video_part)
            video_segments.append(main_video_part)

        # === TRƯỜNG HỢP B: KHÔNG CÓ TITLE (Chỉ 1 đoạn Content dài) ===
        else:
            status_text.info(f"✨ Đang dựng Video (Full Frame)...")
            total_dur = final_audio.duration
            slide_duration = total_dur / len(local_img_paths)

            clips = []
            for img_p in local_img_paths:
                sl = create_slide_with_effect(img_p, slide_duration, resolution_tuple)
                clips.append(sl)
                clips_to_close.append(sl)

            base_video = concatenate_videoclips(clips, method="compose").set_duration(total_dur)
            layers = [base_video]

            # Ưu tiên dùng Content Frame, nếu không có thì thử Title Frame
            use_frame = content_frame_path if (content_frame_path and os.path.exists(content_frame_path)) else title_frame_path

            if use_frame and os.path.exists(use_frame):
                frame_clip = ImageClip(use_frame, transparent=True) \
                    .set_duration(total_dur) \
                    .resize(newsize=(w, h)) \
                    .set_position(("center", "center"))
                layers.append(frame_clip)

            full_part = CompositeVideoClip(layers).set_duration(total_dur)
            clips_to_close.append(full_part)
            video_segments.append(full_part)

        # ------------------------------------------------------------------
        # BƯỚC 4: GHÉP CÁC PHẦN + TEXT OVERLAY + LOGO
        # ------------------------------------------------------------------

        # Nối Intro và Main (nếu có tách)
        visual_combined = concatenate_videoclips(video_segments, method="compose")
        total_duration = final_audio.duration

        final_layers = [visual_combined]

        # 1. Text Overlay (Nằm trên cùng Frame)
        if text_overlay_path and os.path.exists(text_overlay_path):
            text_clip = ImageClip(text_overlay_path, transparent=True) \
                .set_duration(total_duration) \
                .resize(newsize=(w, h)) \
                .set_position(("center", "center"))
            final_layers.append(text_clip)

        # 2. Logo (Nằm trên cùng tất cả)
        if logo_path and os.path.exists(logo_path):
            logo_clip = ImageClip(logo_path, transparent=True) \
                .set_duration(total_duration) \
                .resize(newsize=(w, h)) \
                .set_position(("center", "center"))
            final_layers.append(logo_clip)

        # Composite cuối cùng
        final_video_visual = CompositeVideoClip(final_layers).set_duration(total_duration)
        final_video = final_video_visual.set_audio(final_audio)

        # ------------------------------------------------------------------
        # BƯỚC 5: RENDER VIDEO
        # ------------------------------------------------------------------
        final_output_path = os.path.join(TARGET_VIDEO_FOLDER, output_filename)
        status_text.info(f"🚀 Đang Render Video ({round(total_duration)}s)...")

        final_video.write_videofile(
            final_output_path,
            fps=24,
            codec='libx264',
            audio_codec='aac',
            preset='ultrafast',   # Tăng tốc render
            ffmpeg_params=["-crf", "28"], # Giảm bitrate nhẹ để nhẹ file
            threads=4,
            verbose=False,
            logger=None
        )

        status_text.success(f"✅ Xong! Video lưu tại: {final_output_path}")
        return final_output_path

    except Exception as e:
        status_text.error(f"❌ Lỗi xử lý video: {e}")
        raise e

    finally:
        # Dọn dẹp tài nguyên để tránh tràn RAM
        try:
            for c in clips_to_close:
                try: c.close()
                except: pass
            if final_video: final_video.close()
            if final_audio: final_audio.close()
        except: pass

        # Xóa folder tạm
        try:
            if os.path.exists(temp_asset_dir):
                shutil.rmtree(temp_asset_dir)
        except: pass