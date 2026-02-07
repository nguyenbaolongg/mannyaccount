import os
import requests
import shutil
import json
import ffmpeg
import random
import logging
import textwrap
from datetime import datetime

# ==============================================================================
# 0. SETUP MÔI TRƯỜNG
# ==============================================================================
if "FONTCONFIG_FILE" in os.environ: del os.environ["FONTCONFIG_FILE"]
if "FONTCONFIG_PATH" in os.environ: del os.environ["FONTCONFIG_PATH"]

try:
    import streamlit as st
except ImportError:
    class MockSt:
        def info(self, msg): print(f"[INFO] {msg}")
        def error(self, msg): print(f"[ERROR] {msg}")
        def success(self, msg): print(f"[SUCCESS] {msg}")
    st = MockSt()

logging.getLogger('streamlit').setLevel(logging.ERROR)

# ==============================================================================
# 1. CẤU HÌNH ĐƯỜNG DẪN
# ==============================================================================
CURRENT_FILE_PATH = os.path.abspath(__file__)
MODULES_DIR = os.path.dirname(CURRENT_FILE_PATH)
PROJECT_ROOT = os.path.dirname(MODULES_DIR)

ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")
TEMP_REMIX_DIR = os.path.join(ASSETS_DIR, "temp_remix")
FRAME_DIR = os.path.join(ASSETS_DIR, "frame")
LOGO_DIR = os.path.join(ASSETS_DIR, "logo")
FONT_DIR = os.path.join(ASSETS_DIR, "font")
TARGET_VIDEO_FOLDER = os.path.join(os.path.expanduser("~"), "Videos")
RENDER_CONFIG_PATH = os.path.join(PROJECT_ROOT, "config", "render_config.json")

for d in [TARGET_VIDEO_FOLDER, TEMP_REMIX_DIR, FRAME_DIR, LOGO_DIR, FONT_DIR]:
    os.makedirs(d, exist_ok=True)

# ==============================================================================
# 2. CÁC HÀM HỖ TRỢ (UTILS)
# ==============================================================================
def download_or_copy_file(source, save_path):
    try:
        if not source: return False
        source = str(source).strip()
        if os.path.exists(source):
            shutil.copy2(source, save_path)
            return True
        if source.startswith("http"):
            res = requests.get(source, stream=True, timeout=30)
            if res.status_code == 200:
                with open(save_path, 'wb') as f:
                    for chunk in res.iter_content(chunk_size=8192): f.write(chunk)
                return True
        return False
    except Exception as e:
        print(f"⚠️ Load Error ({source}): {e}")
    return False

def get_media_duration(file_path):
    """Lấy thời lượng chính xác của file media (video/audio)"""
    try:
        if not os.path.exists(file_path): return 0.0
        probe = ffmpeg.probe(file_path)
        return float(probe['format']['duration'])
    except: return 0.0

def wrap_text_ffmpeg(text, font_size, max_width_px):
    if not text: return []
    avg_char_width = font_size * 0.55
    if avg_char_width <= 0: avg_char_width = 10
    max_chars_per_line = int(max_width_px / avg_char_width)
    if max_chars_per_line < 1: max_chars_per_line = 1
    return textwrap.wrap(text, width=max_chars_per_line)

def normalize_url(url):
    if not url: return ""
    return str(url).lower().replace("https://", "").replace("http://", "").replace("www.", "").strip().rstrip('/')

# ==============================================================================
# LOGIC TÌM CONFIG
# ==============================================================================
def load_render_config(target_channel_url=None, target_tiktok_id=None):
    default_config = {
        "channel_url": "Default",
        "title_settings": {"source_start": 0, "zoom_factor": 1.4, "manual_x_offset": "center", "manual_y_offset": "center"},
        "content_settings": {"source_start": 5.0, "zoom_factor": 1.1, "manual_x_offset": 0, "manual_y_offset": 0},
        "text_overlay_settings": {"font_filename": "arialbd.ttf", "font_size": 60, "text_color": "#FFFFFF", "stroke_width": 2, "box_width_percentage": 0.85, "box_y_start": 0.70},
        "text_content_settings": {"font_filename": "arialbd.ttf", "font_size": 35, "text_color": "#FFFFFF", "stroke_width": 2, "box_width_percentage": 0.85, "box_y_start": 0.15},
        "assets": {"logo_width": 150}
    }

    if os.path.exists(RENDER_CONFIG_PATH):
        try:
            with open(RENDER_CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)

            selected_config = None
            if isinstance(data, list):
                if target_channel_url:
                    clean_target_url = normalize_url(target_channel_url)
                    if target_tiktok_id:
                        for cfg in data:
                            cfg_url = normalize_url(cfg.get("channel_url", ""))
                            cfg_id = cfg.get("tiktok_id")
                            if (clean_target_url in cfg_url or cfg_url in clean_target_url) and cfg_id == target_tiktok_id:
                                selected_config = cfg; break

                    if not selected_config:
                        for cfg in data:
                            cfg_url = normalize_url(cfg.get("channel_url", ""))
                            if (clean_target_url in cfg_url or cfg_url in clean_target_url) and not cfg.get("tiktok_id"):
                                selected_config = cfg; break

                    if not selected_config:
                        for cfg in data:
                            cfg_url = normalize_url(cfg.get("channel_url", ""))
                            if clean_target_url in cfg_url or cfg_url in clean_target_url:
                                selected_config = cfg; break

                if not selected_config and len(data) > 0: selected_config = data[0]

            elif isinstance(data, dict): selected_config = data

            if selected_config:
                for key in ["title_settings", "content_settings", "assets", "text_overlay_settings", "text_content_settings"]:
                    if key in selected_config: default_config[key].update(selected_config[key])

        except Exception as e: print(f"⚠️ Lỗi đọc config: {e}")

    return default_config

# ==============================================================================
# 3. CORE RENDER SEGMENT (XỬ LÝ CẮT, LẶP, VÀ HIỆU ỨNG NÂNG CAO)
# ==============================================================================
def render_segment_to_file(video_filename, audio_filename, output_filename, settings, text_settings, text_content, frame_filename, temp_dir):
    if not os.path.exists(video_filename): return False
    if not os.path.exists(audio_filename): return False

    print(f"   ⚙️ Rendering segment: {output_filename}")

    # 1. Lấy thông số thời gian
    duration_audio = get_media_duration(audio_filename) # Thời lượng Audio (Cần đạt được)
    total_video_duration = get_media_duration(video_filename) # Thời lượng Video gốc

    font_file_clean = "font.ttf"
    if not os.path.exists(font_file_clean): font_file_clean = "C\\:/Windows/Fonts/arial.ttf"

    s_start = float(settings.get("source_start", 0))
    raw_end = settings.get("source_end", "auto")
    zoom = float(settings.get("zoom_factor", 1.0))

    # [TÍNH NĂNG MỚI] Random các tham số biến đổi
    # -----------------------------------------------------
    # 1. Speed (Tốc độ): Tăng/Giảm ngẫu nhiên từ 0.95 (chậm) đến 1.05 (nhanh)
    video_speed = random.uniform(0.95, 1.05)

    # 2. Volume (Âm lượng Biz): Thay đổi nhẹ âm lượng video gốc (nếu có dùng video gốc làm nền âm thanh)

    # 3. Distort (Bóp méo): Dùng lenscorrection để làm cong nhẹ hình (1-2%)
    k1_distort = random.uniform(-0.03, 0.03) # -2% đến +2%
    k2_distort = random.uniform(-0.03, 0.03)

    # 4. Filter màu (Color Grading nhẹ): Thay đổi contrast, brightness, saturation
    contrast_val = random.uniform(1.0, 1.1)     # Tăng tương phản nhẹ
    brightness_val = random.uniform(-0.02, 0.02) # Tăng giảm độ sáng nhẹ
    saturation_val = random.uniform(0.9, 1.2)    # Tăng giảm độ bão hòa
    # -----------------------------------------------------

    v_in = ffmpeg.input(video_filename)
    a_in = ffmpeg.input(audio_filename)

    # 2. Xử lý Logic Cắt Video (Hỗ trợ số âm)
    real_end = None

    if raw_end != "auto" and raw_end is not None:
        val = float(raw_end)
        # Nếu là số âm (VD: -8) -> Lấy tổng thời gian - 8
        if val < 0:
            real_end = total_video_duration + val
            if real_end < s_start:
                print(f"⚠️ Cảnh báo: Video quá ngắn để cắt đuôi {val}s. Lấy full.")
                real_end = None
            else:
                print(f"   ✂️ Cắt đuôi {val}s -> Kết thúc cắt tại: {real_end}")
        else:
            real_end = val

    # 3. Áp dụng Filter Cắt (Trim) -> Tách đoạn video ra khỏi video gốc
    if real_end:
        v = v_in.filter('trim', start=s_start, end=real_end)
    else:
        v = v_in.filter('trim', start=s_start) # Cắt từ start đến hết

    # 4. [QUAN TRỌNG] Reset Time & Loop
    v = v.filter('setpts', 'PTS-STARTPTS')
    v = v.filter('loop', loop=-1, size=32767, start=0)

    # -----------------------------------------------------------------------
    # 5. Xử lý HIỆU ỨNG (VISUAL EFFECTS) - Áp dụng các filter mới
    # -----------------------------------------------------------------------

    # A. Thay đổi Tốc độ Video (Speed)
    # setpts < 1 là nhanh, > 1 là chậm. Ví dụ speed 1.05 -> setpts = 1/1.05
    v = v.filter('setpts', f'PTS/{video_speed}')

    # B. Zoom & Scale
    target_w = 1080
    scaled_w = int(target_w * zoom)
    if scaled_w % 2 != 0: scaled_w += 1
    v = v.filter('scale', width=scaled_w, height=-2)

    # C. Bóp méo (Distort) - Lens Correction [MỚI]
    # k1, k2: các hệ số bóp méo (quadratic correction). Giá trị nhỏ (0.01-0.05) tạo hiệu ứng nhẹ.
    v = v.filter('lenscorrection', k1=k1_distort, k2=k2_distort)

    # D. Color Filter (Lớp phủ màu/ánh sáng) [MỚI]
    # eq: chỉnh contrast, brightness, saturation
    v = v.filter('eq', contrast=contrast_val, brightness=brightness_val, saturation=saturation_val)

    # Thêm nhiễu hạt siêu nhỏ (Noise) để thay đổi từng pixel (giúp lách bản quyền tốt hơn)
    # v = v.filter('noise', alls=5, allf='t+u') # (Tùy chọn: Có thể bật nếu muốn, nhưng sẽ làm nặng render)

    # Tạo nền đen khớp thời lượng Audio
    bg = ffmpeg.input(f'color=c=black:s=1080x1920:d={duration_audio}', f='lavfi')

    raw_x = settings.get("manual_x_offset", "center")
    raw_y = settings.get("manual_y_offset", "center")
    x_expr = '(W-w)/2' if str(raw_x) == 'center' else f'(W-w)/2 + {raw_x}'
    y_expr = '(H-h)/2' if str(raw_y) == 'center' else f'(H-h)/2 + {raw_y}'

    # Ghép video đã loop vào nền đen
    v = ffmpeg.overlay(bg, v, x=x_expr, y=y_expr, shortest=1)

    # Thêm Frame
    if frame_filename and os.path.exists(frame_filename):
        fr = ffmpeg.input(frame_filename).filter('scale', 1080, 1920)
        v = ffmpeg.overlay(v, fr)

    # Thêm Text
    if text_content:
        t_color = text_settings.get("text_color", "#FFFFFF").replace("#", "0x")
        f_size = int(text_settings.get("font_size", 60))
        border_w = int(text_settings.get("stroke_width", 2))
        box_w_pct = float(text_settings.get("box_width_percentage", 0.85))
        y_start_pct = float(text_settings.get("box_y_start", 0.7))

        max_text_width = int(1080 * box_w_pct)
        safe_text = str(text_content).replace("'", "").replace(":", "").replace("%", "").strip().upper()
        wrapped_lines = wrap_text_ffmpeg(safe_text, f_size, max_text_width)

        start_y_px = 1920 * y_start_pct
        line_spacing_px = f_size * 1.2

        for i, line in enumerate(wrapped_lines):
            current_line_y = start_y_px + (i * line_spacing_px)
            v = v.drawtext(
                text=line, fontfile=font_file_clean, fontsize=f_size,
                fontcolor=t_color, borderw=border_w, bordercolor="black",
                shadowcolor="black", shadowx=2, shadowy=2,
                x='(w-text_w)/2', y=str(current_line_y), fix_bounds=True
            )

    # -----------------------------------------------------------------------
    # 6. Xử lý AUDIO (Chỉnh âm lượng + Tốc độ) [MỚI]
    # -----------------------------------------------------------------------

    # B. Tăng/Giảm Âm lượng (Volume Biz)
    # Random volume từ 0.9 (90%) đến 1.3 (130%)
    audio_vol = random.uniform(0.9, 1.3)
    a_in = a_in.filter('volume', volume=audio_vol)

    try:
        (
            ffmpeg
            .output(v, a_in, output_filename, t=duration_audio, r=30, vcodec='libx264', acodec='aac', pix_fmt='yuv420p', preset='ultrafast')
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        return True
    except ffmpeg.Error as e:
        print(f"❌ FFmpeg Log:\n{e.stderr.decode('utf8')}")
        return False

# ==============================================================================
# 4. MAIN FLOW
# ==============================================================================
def create_video_from_source_video(
        audio_url, source_video_url, resolution_tuple=(1080, 1920),
        output_filename=None,
        title_frame_path=None, content_frame_path=None,
        title_tiktok=None, content_text=None,
        logo_path=None, title_audio_url=None, script_url=None,
        row_index=None,
        target_channel_url=None,
        tiktok_id=None,
        **kwargs
):
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    if not output_filename: output_filename = f"remix_{timestamp_str}.mp4"

    temp_dir = os.path.join(TEMP_REMIX_DIR, f"task_{timestamp_str}")
    os.makedirs(temp_dir, exist_ok=True)
    original_cwd = os.getcwd()

    print(f"\n📂 TEMP DIR: {temp_dir}")
    print(f"🚀 [Pipeline] Row {row_index} | TikTok ID: {tiktok_id}")
    final_path = os.path.join(TARGET_VIDEO_FOLDER, output_filename)

    try:
        # B1. Download Resources
        p_vid_name = "vid.mp4"
        p_aud_main_name = "aud_main.mp3"
        p_aud_title_name = "aud_title.mp3"

        if not download_or_copy_file(source_video_url, os.path.join(temp_dir, p_vid_name)):
            raise Exception("Không thể tải Video gốc.")

        if not audio_url: raise Exception("Link Audio Content bị rỗng.")
        if not download_or_copy_file(audio_url, os.path.join(temp_dir, p_aud_main_name)):
            raise Exception("Không thể tải Audio Content.")

        has_intro = False
        if title_audio_url:
            if download_or_copy_file(title_audio_url, os.path.join(temp_dir, p_aud_title_name)):
                has_intro = True

        # B2. Load Config
        cfg = load_render_config(target_channel_url, target_tiktok_id=tiktok_id)
        assets = cfg.get("assets", {})

        def find_asset_src(arg, key, default_folder):
            if arg:
                if os.path.exists(arg): return arg
                filename = os.path.basename(arg)
                p = os.path.join(default_folder, filename)
                if os.path.exists(p): return p
            val = assets.get(key)
            if val:
                if os.path.exists(val): return val
                p = os.path.join(default_folder, val)
                if os.path.exists(p): return p
            return None

        src_t_frame = find_asset_src(title_frame_path, "title_frame_filename", FRAME_DIR)
        src_c_frame = find_asset_src(content_frame_path, "content_frame_filename", FRAME_DIR)
        src_logo = find_asset_src(logo_path, "logo_filename", LOGO_DIR)
        src_font_name = cfg["text_content_settings"].get("font_filename", "arialbd.ttf")

        # B3. Copy Assets
        local_t_frame_name = "frame_intro.png" if src_t_frame else None
        if src_t_frame: shutil.copy2(src_t_frame, os.path.join(temp_dir, local_t_frame_name))

        local_c_frame_name = "frame_content.png" if src_c_frame else None
        if src_c_frame: shutil.copy2(src_c_frame, os.path.join(temp_dir, local_c_frame_name))

        font_src_path = None
        possible_fonts = [
            os.path.join(FONT_DIR, src_font_name),
            os.path.join(PROJECT_ROOT, "config", src_font_name),
            os.path.join("C:\\Windows\\Fonts", src_font_name),
            os.path.join("C:\\Windows\\Fonts", "arial.ttf")
        ]
        for p in possible_fonts:
            if os.path.exists(p): font_src_path = p; break
        if font_src_path: shutil.copy2(font_src_path, os.path.join(temp_dir, "font.ttf"))

        # B4. Render
        os.chdir(temp_dir)
        segs = []

        if has_intro:
            out = "seg1.mp4"
            if render_segment_to_file(p_vid_name, p_aud_title_name, out, cfg["title_settings"], cfg["text_overlay_settings"], title_tiktok, local_t_frame_name, temp_dir):
                segs.append(out)

        out2 = "seg2.mp4"
        if not os.path.exists(p_aud_main_name): raise Exception("Mất file aud_main.mp3")

        if render_segment_to_file(p_vid_name, p_aud_main_name, out2, cfg["content_settings"], cfg["text_content_settings"], content_text, local_c_frame_name, temp_dir):
            segs.append(out2)
        else:
            raise Exception("Render Content Failed")

        with open("list.txt", "w", encoding="utf-8") as f:
            for s in segs: f.write(f"file '{s}'\n")

        (ffmpeg.input("list.txt", format='concat', safe=0).output("concat.mp4", c='copy').overwrite_output().run(quiet=True))

        local_logo_name = "logo.png" if src_logo else None
        if src_logo: shutil.copy2(src_logo, local_logo_name)

        if local_logo_name and os.path.exists(local_logo_name):
            lw = int(assets.get("logo_width", 150))
            (ffmpeg.input("concat.mp4")
             .overlay(ffmpeg.input(local_logo_name).filter('scale', lw, -1), x='main_w-overlay_w-30', y='30')
             .output(final_path, vcodec='libx264', acodec='copy', preset='ultrafast')
             .overwrite_output().run(capture_stdout=True, capture_stderr=True))
        else:
            shutil.move("concat.mp4", final_path)

        if os.path.exists(final_path):
            print(f"✅ DONE: {final_path}")
            return final_path

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback; traceback.print_exc()
    finally:
        os.chdir(original_cwd)
        if os.path.exists(temp_dir): shutil.rmtree(temp_dir, ignore_errors=True)

# ==============================================================================
# 5. TEST UNIT (CHẠY THỬ)
# ==============================================================================
if __name__ == "__main__":
    print("🧪 --- BẮT ĐẦU TEST MODULE VIDEO REMIX ---")

    # ---------------------------------------------------------
    # BƯỚC 1: CẤU HÌNH INPUT GIẢ LẬP (SỬA ĐƯỜNG DẪN TẠI ĐÂY)
    # ---------------------------------------------------------
    # Hãy trỏ đến 1 file video và 1 file mp3 có thật trên máy tính của bạn để test
    # Lưu ý: Dùng r"..." để tránh lỗi đường dẫn Windows

    # Ví dụ: r"D:\Downloads\video_goc.mp4"
    fake_video_source = r"D:\US\Lõm Hóp\Videos\Mọi người lưu ý nhé!.mp4"

    # Ví dụ: r"D:\Downloads\audio_tts.mp3"
    fake_audio_content = r"C:\Users\Acer\Downloads\tiktok_Mấy_bà_hay_than_thở_80fe982bba43.mp3"

    # (Tùy chọn) Audio tiêu đề
    fake_audio_title = r"C:\Users\Acer\Downloads\tiktok_Hướng_dẫn_chụp_ảnh_n_49825f9f84bd.mp3"

    # ---------------------------------------------------------
    # BƯỚC 2: TẠO FILE DUMMY NẾU CHƯA CÓ (CHỈ ĐỂ TRÁNH LỖI KHI CODE CHẠY)
    # ---------------------------------------------------------
    if not os.path.exists(fake_video_source):
        print(f"⚠️ Không thấy file video test tại: {fake_video_source}")
        print("👉 Vui lòng sửa biến 'fake_video_source' trỏ đến 1 file MP4 có thật.")

    if not os.path.exists(fake_audio_content):
        print(f"⚠️ Không thấy file audio test tại: {fake_audio_content}")
        print("👉 Vui lòng sửa biến 'fake_audio_content' trỏ đến 1 file MP3 có thật.")

    # ---------------------------------------------------------
    # BƯỚC 3: CHẠY HÀM RENDER
    # ---------------------------------------------------------
    if os.path.exists(fake_video_source) and os.path.exists(fake_audio_content):
        print("\n🚀 Đang chạy lệnh render...")

        try:
            result_path = create_video_from_source_video(
                audio_url=fake_audio_content,           # Audio nội dung
                source_video_url=fake_video_source,     # Video nền
                title_audio_url=fake_audio_title,       # Audio tiêu đề (Intro)

                # Nội dung Text
                title_tiktok="TEST TITLE HEADER",
                content_text="Day la noi dung test thu nghiem.\nVideo se duoc cat va lap lai.",

                # Giả lập config
                target_channel_url="https://www.tiktok.com/@tamsudaokeo28",
                tiktok_id="@nguyenbaolong826",

                # File output
                output_filename="test_result_video.mp4",

                # Debug row index
                row_index=999
            )

            if result_path and os.path.exists(result_path):
                print(f"\n✅ TEST THÀNH CÔNG!")
                print(f"📂 File kết quả: {result_path}")
                print(f"⏱️ Hãy mở file lên xem video có bị đen màn hình hay không.")
            else:
                print("\n❌ TEST THẤT BẠI: Hàm chạy xong nhưng không thấy file output.")

        except Exception as e:
            print(f"\n❌ TEST ERROR (CRASH): {e}")
            import traceback
            traceback.print_exc()
    else:
        print("\n⛔ DỪNG TEST: Thiếu file input.")