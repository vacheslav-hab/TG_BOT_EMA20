@echo off
echo 🚀 Запуск Telegram Bot EMA20...
cd /d "%~dp0"

echo 🧹 Очистка системы...
python cleanup_bot.py

echo 🤖 Запуск бота...
python main.py
pause