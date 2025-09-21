"""
Database Manager - Работа с JSON
"""

import json
from config import logger, JSON_FILE

class DatabaseManager:
    def __init__(self):
        self.signals = {}
        self.json_file = JSON_FILE
        logger.info("Инициализация DatabaseManager")
        
    async def load_signals(self):
        """Загрузка сигналов"""
        logger.info(f"Загрузка сигналов из {self.json_file}")
        # TODO: Загрузка из JSON файла
        
    async def save_signals(self):
        """Сохранение сигналов"""
        logger.debug("Сохранение сигналов...")
        # TODO: Сохранение в JSON файл
        
    def get_active_signals(self):
        """Получение активных сигналов"""
        # TODO: Фильтрация активных сигналов
        return {}