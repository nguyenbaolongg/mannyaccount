#!/bin/bash
cd /home/giang-adsup/Documents/voice/voiceHA_Long_Hung
./.venv/bin/python -m backend.main --port 8082 > /home/giang-adsup/mannyAccount/server_log_8082.txt 2>&1 &
PID=$!
sleep 20
cd /home/giang-adsup/mannyAccount
python3 test_api_8082.py
kill $PID
cat /home/giang-adsup/mannyAccount/server_log_8082.txt
