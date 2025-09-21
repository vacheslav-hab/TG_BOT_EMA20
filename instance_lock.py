# -*- coding: utf-8 -*-
"""
Instance Lock Manager - Предотвращение запуска нескольких экземпляров бота
"""

import os
import sys
import time
import subprocess
from pathlib import Path
from config import logger


class InstanceLock:
    """Класс для предотвращения запуска нескольких экземпляров"""
    
    def __init__(self, lock_file="bot_instance.lock"):
        self.lock_file = Path(lock_file)
        self.lock_handle = None
        
    def acquire(self, timeout=5):
        """Получение блокировки экземпляра"""
        try:
            # Проверяем, существует ли файл блокировки
            if self.lock_file.exists():
                # Читаем PID из файла
                try:
                    with open(self.lock_file, 'r') as f:
                        old_pid = int(f.read().strip())
                    
                    # Проверяем, работает ли процесс с таким PID
                    if self._is_process_running(old_pid):
                        logger.error(f"❌ Другой экземпляр бота уже работает (PID: {old_pid})")
                        logger.info("🔧 Для остановки используйте: taskkill /f /im python.exe")
                        return False
                    else:
                        logger.info("🧹 Удаляем устаревший файл блокировки")
                        self.lock_file.unlink()
                        
                except (ValueError, FileNotFoundError):
                    # Файл поврежден, удаляем его
                    logger.info("🧹 Удаляем поврежденный файл блокировки")
                    self.lock_file.unlink()
            
            # Создаем новый файл блокировки
            current_pid = os.getpid()
            with open(self.lock_file, 'w') as f:
                f.write(str(current_pid))
            
            logger.info(f"🔒 Блокировка экземпляра получена (PID: {current_pid})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка при получении блокировки: {e}")
            return False
    
    def release(self):
        """Освобождение блокировки"""
        try:
            if self.lock_file.exists():
                self.lock_file.unlink()
                logger.info("🔓 Блокировка экземпляра освобождена")
        except Exception as e:
            logger.error(f"❌ Ошибка при освобождении блокировки: {e}")
    
    def _is_process_running(self, pid):
        """Проверка, работает ли процесс с указанным PID"""
        try:
            if sys.platform == "win32":
                # Windows
                result = subprocess.run(
                    ['tasklist', '/FI', f'PID eq {pid}', '/FO', 'CSV'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                # Проверяем, есть ли PID в выводе (исключая заголовок)
                lines = result.stdout.strip().split('\n')
                return len(lines) > 1 and str(pid) in result.stdout
            else:
                # Unix/Linux
                os.kill(pid, 0)
                return True
        except (OSError, subprocess.TimeoutExpired, subprocess.CalledProcessError):
            return False
    
    def __enter__(self):
        """Контекстный менеджер - вход"""
        if not self.acquire():
            raise RuntimeError("Не удалось получить блокировку экземпляра")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Контекстный менеджер - выход"""
        self.release()


def check_single_instance():
    """Проверка и обеспечение единственного экземпляра"""
    lock = InstanceLock()
    return lock.acquire()


def cleanup_instance_lock():
    """Очистка файла блокировки"""
    lock = InstanceLock()
    lock.release()