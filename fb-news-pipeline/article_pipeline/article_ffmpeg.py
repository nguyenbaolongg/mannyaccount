import os
import json
import subprocess
import random

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHANNELS_DIR = os.path.join(PROJECT_ROOT, "assets", "channels")

def _get_supabase_client():
    env_file = os.path.join(PROJECT_ROOT, ".env")
    env = {}
    if os.path.exists(env_file):
        try:
            with open(env_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, val = line.split("=", 1)
                        env[key.strip()] = val.strip()
        except:
            pass
    url = env.get("SUPABASE_URL", "")
    key = env.get("SUPABASE_KEY", "")
    if url and key:
        try:
            from supabase import create_client
            return create_client(url, key)
        except Exception as e:
            print(f"⚠️ Không thể tạo client Supabase: {e}")
    return None

def sync_channel_assets(id_tiktok: str):
    """Đồng bộ assets (frame, logo, config.json) của kênh từ Supabase Storage về local."""
    client = _get_supabase_client()
    if not client:
        return

    channel_dir = os.path.join(CHANNELS_DIR, id_tiktok)
    os.makedirs(channel_dir, exist_ok=True)
    
    storage_folder = f"channels/{id_tiktok}"
    try:
        res = client.storage.from_("assets").list(storage_folder)
        if not isinstance(res, list):
            return
            
        files = [f.get("name") for f in res if isinstance(f, dict) and f.get("name")]
        
        for file_name in files:
            if file_name in ["frame.png", "logo.png", "config.json"]:
                local_path = os.path.join(channel_dir, file_name)
                storage_path = f"{storage_folder}/{file_name}"
                try:
                    data = client.storage.from_("assets").download(storage_path)
                    with open(local_path, "wb") as f:
                        f.write(data)
                    print(f"   📥 Đã tải thành công {file_name} của kênh {id_tiktok} từ Supabase Storage.")
                except Exception as e:
                    print(f"   ⚠️ Lỗi tải file {file_name} từ Supabase Storage: {e}")
    except Exception as e:
        print(f"   ⚠️ Lỗi kết nối Supabase Storage để đồng bộ assets: {e}")

def get_channel_config(id_tiktok: str) -> dict:
    """Đọc cấu hình frame và logo của một kênh cụ thể, có fallback về mặc định."""
    # Đồng bộ từ Supabase Storage trước
    sync_channel_assets(id_tiktok)
    
    channel_dir = os.path.join(CHANNELS_DIR, id_tiktok)
    config_path = os.path.join(channel_dir, "config.json")
    
    frame_path = os.path.join(channel_dir, "frame.png")
    logo_path = os.path.join(channel_dir, "logo.png")
    
    # Fallback về default ở assets/ nếu kênh riêng chưa có
    if not os.path.exists(frame_path):
        default_frame = os.path.join(PROJECT_ROOT, "assets", "frame.png")
        if os.path.exists(default_frame):
            frame_path = default_frame
            
    if not os.path.exists(logo_path):
        default_logo = os.path.join(PROJECT_ROOT, "assets", "logo.png")
        if os.path.exists(default_logo):
            logo_path = default_logo

    config = {
        "frame_path": frame_path,
        "logo_path": logo_path,
        "logo_x": 50,
        "logo_y": 50,
        "logo_scale": 150 # Chiều rộng của logo (px)
    }
    
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                custom_config = json.load(f)
                config.update(custom_config)
        except Exception as e:
            print(f"⚠️ Lỗi đọc {config_path}: {e}")
            
    return config

def create_article_video(id_tiktok: str, image_paths: list, voice_path: str, output_path: str):
    """
    Dựng video từ mảng ảnh tĩnh và file âm thanh.
    Mỗi id_tiktok sẽ dùng cấu hình riêng.
    """
    print(f"\n🎬 Đang dựng video cho kênh: {id_tiktok}")
    
    # 1. Lấy thông số cấu hình của kênh này
    cfg = get_channel_config(id_tiktok)
    
    has_frame = os.path.exists(cfg["frame_path"])
    has_logo = os.path.exists(cfg["logo_path"])
    
    if has_frame:
        print(f"   🖼️ Đã tìm thấy Frame riêng của kênh {id_tiktok}")
    else:
        print(f"   ⚠️ Kênh {id_tiktok} chưa có file frame.png")
        
    if has_logo:
        print(f"   💠 Đã tìm thấy Logo riêng của kênh {id_tiktok}")
    else:
        print(f"   ⚠️ Kênh {id_tiktok} chưa có file logo.png")
        
    # Lấy độ dài audio
    try:
        duration_cmd = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration", 
            "-of", "default=noprint_wrappers=1:nokey=1", voice_path
        ]
        audio_dur = float(subprocess.check_output(duration_cmd).decode("utf-8").strip())
        print(f"   🎙️ Độ dài audio: {audio_dur:.2f} giây")
    except Exception as e:
        print(f"   ❌ Lỗi lấy độ dài audio: {e}")
        return
        
    num_imgs = len(image_paths)
    if num_imgs == 0:
        return
        
    img_dur = audio_dur / num_imgs
    print(f"   📸 Mỗi ảnh hiển thị: {img_dur:.2f} giây")
    
    # 2. Xây dựng inputs và filter_complex cho từng ảnh
    inputs = []
    filter_complex_parts = []
    v_segments = []
    
    for idx, img in enumerate(image_paths):
        # Mỗi ảnh là 1 input với loop và thời lượng tương ứng
        inputs.extend(["-loop", "1", "-t", f"{img_dur:.3f}", "-i", os.path.abspath(img)])
        
        # Tạo tên các pad tạm
        bg_raw = f"[bg_raw{idx}]"
        fg_raw = f"[fg_raw{idx}]"
        bg = f"[bg{idx}]"
        fg = f"[fg{idx}]"
        overlay_pad = f"[overlayed{idx}]"
        v_seg = f"[v_seg{idx}]"
        
        # Scale & blur cho ảnh thứ idx
        filter_complex_parts.append(
            f"[{idx}:v]split=2{bg_raw}{fg_raw};"
            f"{bg_raw}scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:5{bg};"
            f"{fg_raw}scale=1080:1920:force_original_aspect_ratio=decrease{fg};"
            f"{bg}{fg}overlay=(W-w)/2:(H-h)/2,setsar=1{overlay_pad}"
        )
        
        # Chọn ngẫu nhiên loại hiệu ứng chuyển động
        effect = random.choice(["zoom_in", "zoom_out", "pan_left", "pan_right", "pan_up", "pan_down"])
        num_frames = max(1, int(img_dur * 25))
        
        # Áp dụng hiệu ứng chuyển động ngẫu nhiên lên overlay_pad
        if effect == "zoom_in":
            filter_complex_parts.append(
                f"{overlay_pad}zoompan=z='min(zoom+0.001,1.15)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={num_frames}:s=1080x1920:fps=25{v_seg}"
            )
        elif effect == "zoom_out":
            filter_complex_parts.append(
                f"{overlay_pad}zoompan=z='max(1.15-0.001*on,1.0)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={num_frames}:s=1080x1920:fps=25{v_seg}"
            )
        elif effect == "pan_left":
            filter_complex_parts.append(
                f"{overlay_pad}scale=1242:2208,crop=1080:1920:x='(iw-1080)*(1-n/{num_frames})':y='(ih-1920)/2'{v_seg}"
            )
        elif effect == "pan_right":
            filter_complex_parts.append(
                f"{overlay_pad}scale=1242:2208,crop=1080:1920:x='(iw-1080)*(n/{num_frames})':y='(ih-1920)/2'{v_seg}"
            )
        elif effect == "pan_up":
            filter_complex_parts.append(
                f"{overlay_pad}scale=1242:2208,crop=1080:1920:x='(iw-1080)/2':y='(ih-1920)*(1-n/{num_frames})'{v_seg}"
            )
        else: # pan_down
            filter_complex_parts.append(
                f"{overlay_pad}scale=1242:2208,crop=1080:1920:x='(iw-1080)/2':y='(ih-1920)*(n/{num_frames})'{v_seg}"
            )
        v_segments.append(v_seg)
        
    # Ghép (concat) các phân đoạn video của từng ảnh lại thành 1 video duy nhất
    concat_inputs = "".join(v_segments)
    filter_complex_parts.append(f"{concat_inputs}concat=n={num_imgs}:v=1:a=0[v_scaled]")
    
    # Thêm voice audio input
    audio_idx = num_imgs
    inputs.extend(["-i", voice_path])
    
    curr_idx = num_imgs + 1
    out_pad = "[v_scaled]"
    
    # Thêm Frame (khung viền) nếu có
    if has_frame:
        inputs.extend(["-i", cfg["frame_path"]])
        filter_complex_parts.append(f"{out_pad}[{curr_idx}:v]overlay=0:0[v_framed]")
        out_pad = "[v_framed]"
        curr_idx += 1
        
    # Thêm Logo nếu có
    if has_logo:
        inputs.extend(["-i", cfg["logo_path"]])
        lx, ly, lscale = cfg.get("logo_x", 50), cfg.get("logo_y", 50), cfg.get("logo_scale", 150)
        filter_complex_parts.append(f"[{curr_idx}:v]scale={lscale}:-1[logo_scaled]")
        filter_complex_parts.append(f"{out_pad}[logo_scaled]overlay={lx}:{ly}[v_final]")
        out_pad = "[v_final]"
        curr_idx += 1
        
    # Nối tất cả các filter
    filter_complex = ";".join(filter_complex_parts)
    
    cmd = ["ffmpeg", "-y"] + inputs + [
        "-filter_complex", filter_complex,
        "-map", f"{out_pad}",
        "-map", f"{audio_idx}:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "25", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        output_path
    ]
    
    print(f"   🚀 Đang render FFmpeg...")
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"   ✅ Đã xong video: {output_path}")
    except Exception as e:
        print(f"   ❌ Lỗi FFmpeg: {e}")
