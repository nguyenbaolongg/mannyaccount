#!/bin/bash
cd "$(dirname "$0")"

echo "========================================"
echo " KHỞI ĐỘNG TELEGRAM BOT"
echo "========================================"

source ../.venv/bin/activate
python tele_bot.py
