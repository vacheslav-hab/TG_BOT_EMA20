# -*- coding: utf-8 -*-
"""
Скрипт для очистки истории сделок и сброса PnL
"""

import json
import os
from datetime import datetime
from config import JSON_FILE, logger


def clear_trading_history():
    """Очистка всей истории сделок и сброс статистики"""
    try:
        # Проверяем существование файла
        if not os.path.exists(JSON_FILE):
            print("Файл signals.json не найден. Создаем новый пустой файл.")
            create_empty_file()
            return

        # Создаем резервную копию
        backup_file = create_backup()
        print(f"Резервная копия создана: {backup_file}")

        # Создаем пустую структуру данных
        create_empty_file()
        print("История сделок и статистика успешно очищены!")

    except Exception as e:
        logger.error(f"Ошибка при очистке истории сделок: {e}")
        print(f"Ошибка: {e}")


def create_backup():
    """Создание резервной копии текущего файла"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join(os.path.dirname(JSON_FILE), "backups")
    
    # Создаем директорию для бэкапов, если её нет
    os.makedirs(backup_dir, exist_ok=True)
    
    backup_file = os.path.join(backup_dir, f"signals_backup_{timestamp}.json")
    
    # Копируем файл
    with open(JSON_FILE, 'r', encoding='utf-8') as src:
        with open(backup_file, 'w', encoding='utf-8') as dst:
            dst.write(src.read())
    
    return backup_file


def create_empty_file():
    """Создание пустого файла с базовой структурой"""
    empty_data = {
        'positions': {},
        'statistics': {
            'total_signals': 0,
            'tp1_hits': 0,
            'tp2_hits': 0,
            'sl_hits': 0,
            'win_rate': 0.0,
            'total_pnl': 0.0,
            'average_pnl_per_trade': 0.0,
            'max_consecutive_wins': 0,
            'max_consecutive_losses': 0,
            'best_trade_pnl': 0.0,
            'worst_trade_pnl': 0.0
        },
        'daily_stats': {},
        'symbol_stats': {},
        'metadata': {
            'created_at': datetime.now().isoformat(),
            'version': '2.0'
        }
    }
    
    # Сохраняем пустую структуру
    with open(JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(empty_data, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    print("Очистка истории сделок и сброс PnL...")
    clear_trading_history()
    print("Готово! Теперь можно тестировать обновленного бота.")
