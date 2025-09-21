#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестирование системы управления подписчиками
"""

import os
import json
from datetime import datetime
from subscribers_manager import SubscribersManager, SubscriberData


def test_subscribers_manager():
    """Тест основной функциональности SubscribersManager"""
    
    # Используем тестовый файл
    test_file = "test_subscribers.json"
    
    try:
        # Удаляем тестовый файл если существует
        if os.path.exists(test_file):
            os.remove(test_file)
        
        print("🧪 Тестирование SubscribersManager...")
        
        # Создаем менеджер
        manager = SubscribersManager(test_file)
        
        # Тест 1: Добавление подписчиков
        print("\n📝 Тест 1: Добавление подписчиков")
        
        # Добавляем первого подписчика
        is_new1 = manager.add_subscriber(
            user_id=123456789,
            username="test_user1",
            first_name="Иван",
            last_name="Петров",
            language_code="ru"
        )
        print(f"Первый подписчик добавлен: {is_new1}")
        
        # Добавляем второго подписчика
        is_new2 = manager.add_subscriber(
            user_id=987654321,
            username="test_user2",
            first_name="Maria",
            language_code="en"
        )
        print(f"Второй подписчик добавлен: {is_new2}")
        
        # Повторное добавление первого подписчика
        is_new3 = manager.add_subscriber(
            user_id=123456789,
            username="test_user1_updated"
        )
        print(f"Повторное добавление первого: {is_new3}")
        
        # Тест 2: Получение статистики
        print("\n📊 Тест 2: Статистика")
        stats = manager.get_statistics()
        print(f"Всего подписчиков: {stats['total_subscribers']}")
        print(f"Активных подписчиков: {stats['active_subscribers']}")
        print(f"Команд выполнено: {stats['total_commands_executed']}")
        
        # Тест 3: Обновление активности
        print("\n🔄 Тест 3: Обновление активности")
        manager.update_subscriber_activity(123456789)
        manager.update_subscriber_activity(987654321)
        
        stats_after = manager.get_statistics()
        print(f"Команд после обновления: {stats_after['total_commands_executed']}")
        
        # Тест 4: Получение подписчиков
        print("\n👥 Тест 4: Список подписчиков")
        subscribers = manager.get_subscribers(active_only=True)
        print(f"Активных подписчиков в словаре: {len(subscribers)}")
        for user_id, subscriber in subscribers.items():
            print(f"  - {user_id}: {subscriber.username} ({subscriber.total_commands} команд)")
        
        # Тест 5: Дневной отчет
        print("\n📅 Тест 5: Дневной отчет")
        daily_report = manager.get_daily_report()
        print(f"Дата: {daily_report['date']}")
        print(f"Новых подписчиков: {daily_report['new_subscribers']}")
        print(f"Активных пользователей: {daily_report['active_users_count']}")
        print(f"Команд за день: {daily_report['total_commands']}")
        
        # Тест 6: Экспорт в CSV
        print("\n💾 Тест 6: Экспорт в CSV")
        csv_file = "test_export.csv"
        manager.export_to_csv(csv_file)
        
        if os.path.exists(csv_file):
            print(f"✅ CSV файл создан: {csv_file}")
            with open(csv_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                print(f"Строк в файле: {len(lines)}")
            os.remove(csv_file)
        else:
            print("❌ Ошибка создания CSV файла")
        
        # Тест 7: Деактивация подписчика
        print("\n🚫 Тест 7: Деактивация подписчика")
        manager.remove_subscriber(987654321)
        
        stats_final = manager.get_statistics()
        print(f"Активных после деактивации: {stats_final['active_subscribers']}")
        
        # Тест 8: Проверка структуры JSON файла
        print("\n🔍 Тест 8: Структура JSON файла")
        if os.path.exists(test_file):
            with open(test_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            print("Основные секции:")
            for key in data.keys():
                print(f"  - {key}")
            
            print(f"Подписчиков в файле: {len(data.get('subscribers', {}))}")
            print(f"Версия данных: {data.get('metadata', {}).get('version', 'не указана')}")
        
        print("\n✅ Все тесты завершены успешно!")
        
    except Exception as e:
        print(f"\n❌ Ошибка тестирования: {e}")
        
    finally:
        # Очистка тестовых файлов
        for file in [test_file, "test_export.csv"]:
            if os.path.exists(file):
                os.remove(file)
        
        # Удаляем папку backups если пустая
        backup_dir = "backups"
        if os.path.exists(backup_dir) and not os.listdir(backup_dir):
            os.rmdir(backup_dir)


if __name__ == "__main__":
    test_subscribers_manager()