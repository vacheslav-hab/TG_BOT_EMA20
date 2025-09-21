# -*- coding: utf-8 -*-
"""
Bot Cleanup Script - Очистка ресурсов и завершение всех процессов
"""

import subprocess
import os
from pathlib import Path

def cleanup_python_processes():
    """Завершение всех процессов Python"""
    try:
        print("🧹 Завершение всех Python процессов...")
        result = subprocess.run(['taskkill', '/f', '/im', 'python.exe'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Python процессы завершены")
        else:
            print("ℹ️ Активных Python процессов не найдено")
    except Exception as e:
        print(f"❌ Ошибка при завершении процессов: {e}")

def cleanup_lock_file():
    """Удаление файла блокировки"""
    try:
        lock_file = Path("bot_instance.lock")
        if lock_file.exists():
            lock_file.unlink()
            print("✅ Файл блокировки удален")
        else:
            print("ℹ️ Файл блокировки не найден")
    except Exception as e:
        print(f"❌ Ошибка при удалении файла блокировки: {e}")

def main():
    """Основная функция очистки"""
    print("🚀 Запуск очистки системы...")
    cleanup_python_processes()
    cleanup_lock_file()
    print("✅ Очистка завершена! Теперь можно запускать бота.")

if __name__ == "__main__":
    main()