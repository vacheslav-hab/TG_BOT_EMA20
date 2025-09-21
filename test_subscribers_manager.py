# -*- coding: utf-8 -*-
"""
Unit tests for subscribers_manager.py
"""

import os
import json
import tempfile
from datetime import datetime, timedelta
import pytest
from subscribers_manager import SubscribersManager, SubscriberData


class TestSubscribersManager:
    """Тесты для SubscribersManager"""
    
    def setup_method(self):
        """Подготовка перед каждым тестом"""
        # Создаем временный файл для тестов
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
        self.temp_file.close()
        self.manager = SubscribersManager(self.temp_file.name)
    
    def teardown_method(self):
        """Очистка после каждого теста"""
        # Удаляем временный файл
        if os.path.exists(self.temp_file.name):
            os.remove(self.temp_file.name)
        
        # Удаляем папку backups если создана
        backup_dir = os.path.join(os.path.dirname(self.temp_file.name), "backups")
        if os.path.exists(backup_dir):
            for file in os.listdir(backup_dir):
                os.remove(os.path.join(backup_dir, file))
            os.rmdir(backup_dir)
    
    def test_init(self):
        """Тест инициализации"""
        assert isinstance(self.manager, SubscribersManager)
        assert self.manager.subscribers_file == self.temp_file.name
        assert os.path.exists(self.temp_file.name)
    
    def test_add_new_subscriber(self):
        """Тест добавления нового подписчика"""
        user_id = 123456789
        result = self.manager.add_subscriber(
            user_id=user_id,
            username="testuser",
            first_name="Иван",
            last_name="Петров",
            language_code="ru"
        )
        
        assert result is True  # Новый подписчик
        
        # Проверяем данные
        subscribers = self.manager.get_subscribers()
        assert len(subscribers) == 1
        assert user_id in subscribers
        
        subscriber = subscribers[user_id]
        assert subscriber.username == "testuser"
        assert subscriber.first_name == "Иван"
        assert subscriber.last_name == "Петров"
        assert subscriber.language_code == "ru"
        assert subscriber.is_active is True
        assert subscriber.total_commands == 1
    
    def test_add_existing_subscriber(self):
        """Тест повторного добавления подписчика"""
        user_id = 123456789
        
        # Добавляем первый раз
        self.manager.add_subscriber(user_id=user_id, username="testuser1")
        
        # Добавляем второй раз
        result = self.manager.add_subscriber(
            user_id=user_id,
            username="testuser2",
            first_name="Иван"
        )
        
        assert result is False  # Уже существующий подписчик
        
        # Проверяем обновленные данные
        subscribers = self.manager.get_subscribers()
        assert len(subscribers) == 1
        assert user_id in subscribers
        
        subscriber = subscribers[user_id]
        assert subscriber.username == "testuser2"
        assert subscriber.first_name == "Иван"
        assert subscriber.total_commands == 2
    
    def test_update_subscriber_activity(self):
        """Тест обновления активности подписчика"""
        user_id = 123456789
        
        # Добавляем подписчика
        self.manager.add_subscriber(user_id=user_id, username="testuser")
        
        # Получаем исходные данные
        subscribers_before = self.manager.get_subscribers()
        subscriber_before = subscribers_before[user_id]
        commands_before = subscriber_before.total_commands
        
        # Обновляем активность
        self.manager.update_subscriber_activity(user_id)
        
        # Проверяем обновленные данные
        subscribers_after = self.manager.get_subscribers()
        subscriber_after = subscribers_after[user_id]
        assert subscriber_after.total_commands == commands_before + 1
    
    def test_remove_subscriber(self):
        """Тест деактивации подписчика"""
        user_id = 123456789
        
        # Добавляем подписчика
        self.manager.add_subscriber(user_id=user_id, username="testuser")
        
        # Проверяем, что подписчик активен
        subscribers_active = self.manager.get_subscribers(active_only=True)
        assert len(subscribers_active) == 1
        
        # Деактивируем подписчика
        self.manager.remove_subscriber(user_id)
        
        # Проверяем, что активных подписчиков нет
        subscribers_active = self.manager.get_subscribers(active_only=True)
        assert len(subscribers_active) == 0
        
        # Проверяем, что подписчик есть в общем списке, но неактивен
        subscribers_all = self.manager.get_subscribers(active_only=False)
        assert len(subscribers_all) == 1
        assert user_id in subscribers_all
        assert subscribers_all[user_id].is_active is False
    
    def test_get_subscriber_ids(self):
        """Тест получения ID подписчиков"""
        user_id1 = 123456789
        user_id2 = 987654321
        
        # Добавляем подписчиков
        self.manager.add_subscriber(user_id=user_id1, username="user1")
        self.manager.add_subscriber(user_id=user_id2, username="user2")
        self.manager.remove_subscriber(user_id2)  # Деактивируем второго
        
        # Получаем ID активных подписчиков
        active_ids = self.manager.get_subscriber_ids(active_only=True)
        assert active_ids == {user_id1}
        
        # Получаем ID всех подписчиков
        all_ids = self.manager.get_subscriber_ids(active_only=False)
        assert all_ids == {user_id1, user_id2}
    
    def test_get_statistics(self):
        """Тест получения статистики"""
        user_id1 = 123456789
        user_id2 = 987654321
        
        # Добавляем подписчиков
        self.manager.add_subscriber(user_id=user_id1, username="user1")
        self.manager.add_subscriber(user_id=user_id2, username="user2")
        self.manager.remove_subscriber(user_id2)  # Деактивируем второго
        
        # Обновляем активность
        self.manager.update_subscriber_activity(user_id1)
        self.manager.update_subscriber_activity(user_id1)
        
        # Получаем статистику
        stats = self.manager.get_statistics()
        
        assert stats['total_subscribers'] == 2
        assert stats['active_subscribers'] == 1
        assert stats['total_commands_executed'] == 4  # 2 добавления + 2 обновления
    
    def test_export_to_csv(self):
        """Тест экспорта в CSV"""
        user_id = 123456789
        
        # Добавляем подписчика
        self.manager.add_subscriber(
            user_id=user_id,
            username="testuser",
            first_name="Иван",
            language_code="ru"
        )
        
        # Экспортируем в CSV
        csv_file = self.temp_file.name + ".csv"
        self.manager.export_to_csv(csv_file)
        
        # Проверяем, что файл создан
        assert os.path.exists(csv_file)
        
        # Проверяем содержимое файла
        with open(csv_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "user_id" in content
            assert "testuser" in content
            assert "Иван" in content
            assert "ru" in content
        
        # Удаляем тестовый файл
        os.remove(csv_file)
    
    def test_data_persistence(self):
        """Тест персистентности данных"""
        user_id = 123456789
        
        # Добавляем подписчика
        self.manager.add_subscriber(
            user_id=user_id,
            username="testuser",
            first_name="Иван"
        )
        
        # Создаем новый менеджер с тем же файлом
        new_manager = SubscribersManager(self.temp_file.name)
        
        # Проверяем, что данные сохранились
        subscribers = new_manager.get_subscribers()
        assert len(subscribers) == 1
        assert user_id in subscribers
        assert subscribers[user_id].username == "testuser"
        assert subscribers[user_id].first_name == "Иван"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])