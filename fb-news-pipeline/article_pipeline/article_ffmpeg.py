import os
import json
import subprocess

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHANNELS_DIR = os.path.join(PROJECT_ROOT, "assets", "channels")

def get_channel_config(id_tiktok: str) -> dict:
    """Đọc cấu hình frame và logo của một kênh cụ thể."""
    channel_dir = os.path.join(CHANNELS_DIR, id_tiktok)
    config_path = os.path.join(channel_dir, "config.json")
    
    # Cấu hình mặc định nếu kênh chưa có file config.json
    config = {
        "frame_path": os.path.join(channel_dir, "frame.png"),
        "logo_path": os.path.join(channel_dir, "logo.png"),
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
    
    # 2. Sinh list.txt cho FFmpeg concat
    work_dir = os.path.dirname(output_path)
    list_path = os.path.join(work_dir, "img_list.txt")
    with open(list_path, "w", encoding="utf-8") as f:
        for img in image_paths:
            f.write(f"file '{os.path.abspath(img)}'\n")
            f.write(f"duration {img_dur:.3f}\n")
        # Lặp lại ảnh cuối để tránh lỗi
        f.write(f"file '{os.path.abspath(image_paths[-1])}'\n")

    # 3. Lệnh FFmpeg
    # Scale ảnh vừa khung 1080x1920 (làm nhòe viền nếu thiếu)
    # Lắp frame, lắp logo
    filter_complex = "[0:v]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,setsar=1[v_scaled];"
    
    inputs = ["-f", "concat", "-safe", "0", "-i", list_path]
    inputs.extend(["-i", voice_path])
    
    idx = 2
    out_pad = "[v_scaled]"
    
    if has_frame:
        inputs.extend(["-i", cfg["frame_path"]])
        filter_complex += f"{out_pad}[{idx}:v]overlay=0:0[v_framed];"
        out_pad = "[v_framed]"
        idx += 1
        
    if has_logo:
        inputs.extend(["-i", cfg["logo_path"]])
        lx, ly, lscale = cfg.get("logo_x", 50), cfg.get("logo_y", 50), cfg.get("logo_scale", 150)
        filter_complex += f"[{idx}:v]scale={lscale}:-1[logo_scaled];"
        filter_complex += f"{out_pad}[logo_scaled]overlay={lx}:{ly}[v_final];"
        out_pad = "[v_final]"
        idx += 1
        
    # Loại bỏ chấm phẩy cuối cùng nếu filter_complex có
    filter_complex = filter_complex.rstrip(";")
    if out_pad == "[v_scaled]":
        filter_complex = filter_complex.replace("[v_scaled];", "") # Không cần lằng nhằng nếu không có frame/logo
        # Thay vào đó chỉ cần gán map
        
    cmd = ["ffmpeg", "-y"] + inputs + [
        "-filter_complex", filter_complex,
        "-map", f"{out_pad}",
        "-map", "1:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
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
