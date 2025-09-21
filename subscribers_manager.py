# -*- coding: utf-8 -*-
"""
Subscribers Manager - Управление подписчиками Telegram бота
"""

import json
import os
import shutil
from datetime import datetime, timedelta
from typing import Dict, Set, Optional, Any
from dataclasses import dataclass
from pathlib import Path
import asyncio

from config import logger


@dataclass
class SubscriberData:
    """Данные подписчика"""
    user_id: int
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    language_code: Optional[str]
    subscribed_at: datetime
    last_activity: datetime
    is_active: bool = True
    total_commands: int = 0
    
    def to_dict(self) -> Dict:
        """Конвертация в словарь для JSON"""
        return {
            'user_id': self.user_id,
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'language_code': self.language_code,
            'subscribed_at': self.subscribed_at.isoformat(),
            'last_activity': self.last_activity.isoformat(),
            'is_active': self.is_active,
            'total_commands': self.total_commands
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'SubscriberData':
        """Создание из словаря"""
        return cls(
            user_id=data['user_id'],
            username=data.get('username'),
            first_name=data.get('first_name'),
            last_name=data.get('last_name'),
            language_code=data.get('language_code'),
            subscribed_at=datetime.fromisoformat(data['subscribed_at']),
            last_activity=datetime.fromisoformat(data['last_activity']),
            is_active=data.get('is_active', True),
            total_commands=data.get('total_commands', 0)
        )


class SubscribersManager:
    """Менеджер для работы с подписчиками"""
    
    def __init__(self, subscribers_file: str = 'subscribers.json'):
        self.subscribers_file = subscribers_file
        self.backup_dir = Path(subscribers_file).parent / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        self._lock = asyncio.Lock()  # Add lock for concurrent access
        
        # Создаем резервную копию при инициализации
        self._create_backup()
        
        logger.info(f"Инициализация SubscribersManager: {subscribers_file}")
    
    def _create_backup(self):
        """Создание резервной копии файла подписчиков"""
        try:
            if os.path.exists(self.subscribers_file):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = self.backup_dir / f"subscribers_backup_{timestamp}.json"
                shutil.copy2(self.subscribers_file, backup_file)
                
                # Удаляем старые бэкапы (старше 30 дней)
                self._cleanup_old_backups(days=30)
                
        except Exception as e:
            logger.error(f"Ошибка создания резервной копии подписчиков: {e}")
    
    def _cleanup_old_backups(self, days: int = 30):
        """Очистка старых резервных копий"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            for backup_file in self.backup_dir.glob("subscribers_backup_*.json"):
                file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                if file_time < cutoff_date:
                    backup_file.unlink()
                    
        except Exception as e:
            logger.error(f"Ошибка очистки резервных копий подписчиков: {e}")
    
    async def load_data_async(self) -> Dict[str, Any]:
        """Асинхронная загрузка данных подписчиков из JSON файла с блокировкой"""
        async with self._lock:
            return self.load_data()
    
    def load_data(self) -> Dict[str, Any]:
        """Загрузка данных подписчиков из JSON файла"""
        try:
            if not os.path.exists(self.subscribers_file):
                return self._get_empty_data_structure()
            
            with open(self.subscribers_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Проверяем и обновляем структуру при необходимости
            return self._validate_and_update_structure(data)
            
        except Exception as e:
            logger.error(f"Ошибка загрузки данных подписчиков: {e}")
            return self._get_empty_data_structure()
    
    async def save_data_async(self, data: Dict[str, Any]):
        """Асинхронное сохранение данных подписчиков в JSON файл с блокировкой"""
        async with self._lock:
            self.save_data(data)
    
    def save_data(self, data: Dict[str, Any]):
        """Сохранение данных подписчиков в JSON файл"""
        try:
            # Добавляем метаданные
            data['metadata'] = {
                'last_updated': datetime.now().isoformat(),
                'version': '1.0',
                'total_subscribers': len(data.get('subscribers', {})),
                'active_subscribers': len([s for s in data.get('subscribers', {}).values() if s.get('is_active', True)])
            }
            
            # Атомарное сохранение
            temp_file = f"{self.subscribers_file}.tmp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Заменяем основной файл
            if os.path.exists(self.subscribers_file):
                os.replace(temp_file, self.subscribers_file)
            else:
                os.rename(temp_file, self.subscribers_file)
                
        except Exception as e:
            logger.error(f"Ошибка сохранения данных подписчиков: {e}")
            # Удаляем временный файл при ошибке
            if os.path.exists(f"{self.subscribers_file}.tmp"):
                os.remove(f"{self.subscribers_file}.tmp")
    
    def _get_empty_data_structure(self) -> Dict[str, Any]:
        """Получение пустой структуры данных подписчиков"""
        return {
            'subscribers': {},
            'statistics': {
                'total_subscribers': 0,
                'active_subscribers': 0,
                'total_commands_executed': 0,
                'first_subscriber_date': None,
                'last_activity_date': None
            },
            'daily_stats': {},
            'metadata': {
                'created_at': datetime.now().isoformat(),
                'version': '1.0'
            }
        }
    
    def _validate_and_update_structure(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Валидация и обновление структуры данных"""
        # Проверяем наличие всех необходимых секций
        empty_structure = self._get_empty_data_structure()
        
        for key in empty_structure:
            if key not in data:
                data[key] = empty_structure[key]
        
        return data
    
    async def add_subscriber_async(self, user_id: int, username: str = None,
                       first_name: str = None, last_name: str = None,
                       language_code: str = None) -> bool:
        """Асинхронное добавление нового подписчика или обновление существующего"""
        data = await self.load_data_async()
        
        is_new_subscriber = str(user_id) not in data['subscribers']
        now = datetime.now()
        
        if is_new_subscriber:
            # Новый подписчик
            subscriber = SubscriberData(
                user_id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                language_code=language_code,
                subscribed_at=now,
                last_activity=now,
                is_active=True,
                total_commands=1
            )
            
            data['subscribers'][str(user_id)] = subscriber.to_dict()
            data['statistics']['total_subscribers'] += 1
            
            if data['statistics']['first_subscriber_date'] is None:
                data['statistics']['first_subscriber_date'] = now.isoformat()
                
            logger.info(f"✅ Добавлен новый подписчик: {username} (ID: {user_id})")
        else:
            # Обновляем существующего подписчика
            subscriber_data = data['subscribers'][str(user_id)]
            subscriber_data['username'] = username
            subscriber_data['first_name'] = first_name
            subscriber_data['last_activity'] = now.isoformat()
            subscriber_data['is_active'] = True
            subscriber_data['total_commands'] += 1
            
            logger.info(f"🔄 Обновлен подписчик: {username} (ID: {user_id})")
        
        # Обновляем общую статистику
        data['statistics']['active_subscribers'] = len([
            s for s in data['subscribers'].values() if s.get('is_active', True)
        ])
        data['statistics']['total_commands_executed'] += 1
        data['statistics']['last_activity_date'] = now.isoformat()
        
        # Обновляем дневную статистику
        date_str = now.strftime("%Y-%m-%d")
        if date_str not in data['daily_stats']:
            data['daily_stats'][date_str] = {
                'new_subscribers': 0,
                'active_users': [],
                'total_commands': 0
            }
        
        if is_new_subscriber:
            data['daily_stats'][date_str]['new_subscribers'] += 1
        
        # Преобразуем set в list для JSON сериализации
        if isinstance(data['daily_stats'][date_str]['active_users'], set):
            data['daily_stats'][date_str]['active_users'] = list(data['daily_stats'][date_str]['active_users'])
        
        if user_id not in data['daily_stats'][date_str]['active_users']:
            data['daily_stats'][date_str]['active_users'].append(user_id)
        
        data['daily_stats'][date_str]['total_commands'] += 1
        
        await self.save_data_async(data)
        return is_new_subscriber
    
    def add_subscriber(self, user_id: int, username: str = None,
                       first_name: str = None, last_name: str = None,
                       language_code: str = None) -> bool:
        """Добавление нового подписчика или обновление существующего"""
        data = self.load_data()
        
        is_new_subscriber = str(user_id) not in data['subscribers']
        now = datetime.now()
        
        if is_new_subscriber:
            # Новый подписчик
            subscriber = SubscriberData(
                user_id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                language_code=language_code,
                subscribed_at=now,
                last_activity=now,
                is_active=True,
                total_commands=1
            )
            
            data['subscribers'][str(user_id)] = subscriber.to_dict()
            data['statistics']['total_subscribers'] += 1
            
            if data['statistics']['first_subscriber_date'] is None:
                data['statistics']['first_subscriber_date'] = now.isoformat()
                
            logger.info(f"✅ Добавлен новый подписчик: {username} (ID: {user_id})")
        else:
            # Обновляем существующего подписчика
            subscriber_data = data['subscribers'][str(user_id)]
            subscriber_data['username'] = username
            subscriber_data['first_name'] = first_name
            subscriber_data['last_activity'] = now.isoformat()
            subscriber_data['is_active'] = True
            subscriber_data['total_commands'] += 1
            
            logger.info(f"🔄 Обновлен подписчик: {username} (ID: {user_id})")
        
        # Обновляем общую статистику
        data['statistics']['active_subscribers'] = len([
            s for s in data['subscribers'].values() if s.get('is_active', True)
        ])
        data['statistics']['total_commands_executed'] += 1
        data['statistics']['last_activity_date'] = now.isoformat()
        
        # Обновляем дневную статистику
        date_str = now.strftime("%Y-%m-%d")
        if date_str not in data['daily_stats']:
            data['daily_stats'][date_str] = {
                'new_subscribers': 0,
                'active_users': [],
                'total_commands': 0
            }
        
        if is_new_subscriber:
            data['daily_stats'][date_str]['new_subscribers'] += 1
        
        # Преобразуем set в list для JSON сериализации
        if isinstance(data['daily_stats'][date_str]['active_users'], set):
            data['daily_stats'][date_str]['active_users'] = list(data['daily_stats'][date_str]['active_users'])
        
        if user_id not in data['daily_stats'][date_str]['active_users']:
            data['daily_stats'][date_str]['active_users'].append(user_id)
        
        data['daily_stats'][date_str]['total_commands'] += 1
        
        self.save_data(data)
        return is_new_subscriber
    
    async def update_subscriber_activity_async(self, user_id: int):
        """Асинхронное обновление активности подписчика"""
        data = await self.load_data_async()
        
        if str(user_id) in data['subscribers']:
            now = datetime.now()
            data['subscribers'][str(user_id)]['last_activity'] = now.isoformat()
            data['subscribers'][str(user_id)]['total_commands'] += 1
            
            # Обновляем общую статистику
            data['statistics']['total_commands_executed'] += 1
            data['statistics']['last_activity_date'] = now.isoformat()
            
            # Обновляем дневную статистику
            date_str = now.strftime("%Y-%m-%d")
            if date_str not in data['daily_stats']:
                data['daily_stats'][date_str] = {
                    'new_subscribers': 0,
                    'active_users': [],
                    'total_commands': 0
                }
            
            if user_id not in data['daily_stats'][date_str]['active_users']:
                data['daily_stats'][date_str]['active_users'].append(user_id)
            
            data['daily_stats'][date_str]['total_commands'] += 1
            
            await self.save_data_async(data)
    
    def update_subscriber_activity(self, user_id: int):
        """Обновление активности подписчика"""
        data = self.load_data()
        
        if str(user_id) in data['subscribers']:
            now = datetime.now()
            data['subscribers'][str(user_id)]['last_activity'] = now.isoformat()
            data['subscribers'][str(user_id)]['total_commands'] += 1
            
            # Обновляем общую статистику
            data['statistics']['total_commands_executed'] += 1
            data['statistics']['last_activity_date'] = now.isoformat()
            
            # Обновляем дневную статистику
            date_str = now.strftime("%Y-%m-%d")
            if date_str not in data['daily_stats']:
                data['daily_stats'][date_str] = {
                    'new_subscribers': 0,
                    'active_users': [],
                    'total_commands': 0
                }
            
            if user_id not in data['daily_stats'][date_str]['active_users']:
                data['daily_stats'][date_str]['active_users'].append(user_id)
            
            data['daily_stats'][date_str]['total_commands'] += 1
            
            self.save_data(data)
    
    async def remove_subscriber_async(self, user_id: int):
        """Асинхронная деактивация подписчика (пометка как неактивный)"""
        data = await self.load_data_async()
        
        if str(user_id) in data['subscribers']:
            data['subscribers'][str(user_id)]['is_active'] = False
            data['subscribers'][str(user_id)]['last_activity'] = datetime.now().isoformat()
            
            # Пересчитываем активных подписчиков
            data['statistics']['active_subscribers'] = len([
                s for s in data['subscribers'].values() if s.get('is_active', True)
            ])
            
            await self.save_data_async(data)
            logger.info(f"🚫 Подписчик {user_id} деактивирован")
    
    def remove_subscriber(self, user_id: int):
        """Деактивация подписчика (пометка как неактивный)"""
        data = self.load_data()
        
        if str(user_id) in data['subscribers']:
            data['subscribers'][str(user_id)]['is_active'] = False
            data['subscribers'][str(user_id)]['last_activity'] = datetime.now().isoformat()
            
            # Пересчитываем активных подписчиков
            data['statistics']['active_subscribers'] = len([
                s for s in data['subscribers'].values() if s.get('is_active', True)
            ])
            
            self.save_data(data)
            logger.info(f"🚫 Подписчик {user_id} деактивирован")
    
    async def get_subscribers_async(self, active_only: bool = True) -> Dict[int, SubscriberData]:
        """Асинхронное получение списка подписчиков"""
        data = await self.load_data_async()
        subscribers = {}
        
        for user_id_str, subscriber_data in data['subscribers'].items():
            if not active_only or subscriber_data.get('is_active', True):
                user_id = int(user_id_str)
                subscribers[user_id] = SubscriberData.from_dict(subscriber_data)
        
        return subscribers
    
    def get_subscribers(self, active_only: bool = True) -> Dict[int, SubscriberData]:
        """Получение списка подписчиков"""
        data = self.load_data()
        subscribers = {}
        
        for user_id_str, subscriber_data in data['subscribers'].items():
            if not active_only or subscriber_data.get('is_active', True):
                user_id = int(user_id_str)
                subscribers[user_id] = SubscriberData.from_dict(subscriber_data)
        
        return subscribers
    
    async def get_subscriber_ids_async(self, active_only: bool = True) -> Set[int]:
        """Асинхронное получение множества ID подписчиков"""
        subscribers = await self.get_subscribers_async(active_only)
        return set(subscribers.keys())
    
    def get_subscriber_ids(self, active_only: bool = True) -> Set[int]:
        """Получение множества ID подписчиков"""
        subscribers = self.get_subscribers(active_only)
        return set(subscribers.keys())
    
    async def get_statistics_async(self) -> Dict[str, Any]:
        """Асинхронное получение статистики подписчиков"""
        data = await self.load_data_async()
        return data['statistics']
    
    def get_statistics(self) -> Dict[str, Any]:
        """Получение статистики подписчиков"""
        data = self.load_data()
        return data['statistics']
    
    async def get_daily_report_async(self, date: Optional[datetime] = None) -> Dict[str, Any]:
        """Асинхронное получение дневного отчета по подписчикам"""
        if date is None:
            date = datetime.now()
        
        date_str = date.strftime("%Y-%m-%d")
        data = await self.load_data_async()
        
        daily_data = data['daily_stats'].get(date_str, {
            'new_subscribers': 0,
            'active_users': [],
            'total_commands': 0
        })
        
        return {
            'date': date_str,
            'new_subscribers': daily_data['new_subscribers'],
            'active_users_count': len(daily_data['active_users']),
            'total_commands': daily_data['total_commands'],
            'active_users': daily_data['active_users']
        }
    
    def get_daily_report(self, date: Optional[datetime] = None) -> Dict[str, Any]:
        """Получение дневного отчета по подписчикам"""
        if date is None:
            date = datetime.now()
        
        date_str = date.strftime("%Y-%m-%d")
        data = self.load_data()
        
        daily_data = data['daily_stats'].get(date_str, {
            'new_subscribers': 0,
            'active_users': [],
            'total_commands': 0
        })
        
        return {
            'date': date_str,
            'new_subscribers': daily_data['new_subscribers'],
            'active_users_count': len(daily_data['active_users']),
            'total_commands': daily_data['total_commands'],
            'active_users': daily_data['active_users']
        }
    
    def export_to_csv(self, output_file: str):
        """Экспорт подписчиков в CSV формат"""
        import csv
        
        data = self.load_data()
        
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'user_id', 'username', 'first_name', 'last_name', 'language_code',
                'subscribed_at', 'last_activity', 'is_active', 'total_commands'
            ]
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for user_id_str, subscriber_data in data['subscribers'].items():
                writer.writerow({
                    'user_id': subscriber_data['user_id'],
                    'username': subscriber_data.get('username', ''),
                    'first_name': subscriber_data.get('first_name', ''),
                    'last_name': subscriber_data.get('last_name', ''),
                    'language_code': subscriber_data.get('language_code', ''),
                    'subscribed_at': subscriber_data['subscribed_at'],
                    'last_activity': subscriber_data['last_activity'],
                    'is_active': subscriber_data.get('is_active', True),
                    'total_commands': subscriber_data.get('total_commands', 0)
                })
        
        logger.info(f"Подписчики экспортированы в CSV: {output_file}")
    
    def cleanup_inactive_subscribers(self, days_inactive: int = 90):
        """Очистка неактивных подписчиков (старше указанного количества дней)"""
        data = self.load_data()
        cutoff_date = datetime.now() - timedelta(days=days_inactive)
        
        removed_count = 0
        for user_id_str, subscriber_data in list(data['subscribers'].items()):
            last_activity = datetime.fromisoformat(subscriber_data['last_activity'])
            
            if last_activity < cutoff_date and not subscriber_data.get('is_active', True):
                del data['subscribers'][user_id_str]
                removed_count += 1
        
        if removed_count > 0:
            # Пересчитываем статистику
            data['statistics']['total_subscribers'] = len(data['subscribers'])
            data['statistics']['active_subscribers'] = len([
                s for s in data['subscribers'].values() if s.get('is_active', True)
            ])
            
            self.save_data(data)
            logger.info(f"🧹 Удалено {removed_count} неактивных подписчиков")
        
        return removed_count