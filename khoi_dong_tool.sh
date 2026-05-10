#!/bin/bash

echo "==================================================="
echo "   HỆ THỐNG KHỞI ĐỘNG AUTO TIKTOK + VOICE STUDIO   "
echo "==================================================="

# 1. Dọn dẹp tiến trình cũ (nếu có) đang chiếm cổng 8080 để tránh xung đột
echo "[1/3] Đang kiểm tra và dọn dẹp kết nối cũ..."
PIDS=$(lsof -t -i:8080)
if [ ! -z "$PIDS" ]; then
    echo "Phát hiện Voice server cũ đang chạy. Đang tắt..."
    kill -9 $PIDS 2>/dev/null
    sleep 2
fi

# 2. Bật Voicebox (Chạy ngầm để chờ lệnh)
echo "[2/3] Đang bật Tool Voice chạy ngầm chờ lệnh (Background)..."
cd /home/giang-adsup/Documents/voice/voiceHA_Long_Hung
# Chạy script start_viterbox.sh ngầm và đẩy log vào server_output.log
nohup ./start_viterbox.sh > server_output.log 2>&1 &
VOICE_PID=$!
echo "-> Voicebox đã khởi động (PID: $VOICE_PID). Chờ 5 giây để nạp model..."
sleep 5

# 3. Bật Tool Tiktok Many Account (Hiển thị Giao diện)
echo "[3/3] Đang khởi động Giao diện Tool Tiktok..."
cd /home/giang-adsup/mannyAccount
# Kích hoạt môi trường ảo của tool
source .venv/bin/activate
# Chạy giao diện
python desktop_app.py

# 4. Khi người dùng tắt giao diện Tool Tiktok đi, tự động tắt ngầm Tool Voice
echo "==================================================="
echo "Giao diện Tool Tiktok đã đóng. Đang tắt Tool Voice..."
kill -9 $VOICE_PID 2>/dev/null
kill -9 $(lsof -t -i:8080) 2>/dev/null
echo "Đã dọn dẹp hệ thống. Tạm biệt!"
echo "==================================================="
