# -*- coding: utf-8 -*-
"""
JSON Manager - Управление хранением данных о сигналах и PnL
"""

import json
import os
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path
import asyncio

from config import logger, JSON_FILE
import time
import errno

# Глобальный меж-инстансовый lock на запись/чтение JSON в рамках процесса
_json_file_lock = asyncio.Lock()


@dataclass
class PnLRecord:
    """Запись о прибыли/убытке"""
    timestamp: datetime
    level_type: str  # TP1, TP2, SL
    price: float
    pnl_percentage: float
    pnl_absolute: float
    
    def to_dict(self) -> Dict:
        """Конвертация в словарь для JSON"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'level_type': self.level_type,
            'price': self.price, 
            'pnl_percentage': self.pnl_percentage,
            'pnl_absolute': self.pnl_absolute
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'PnLRecord':
        """Создание из словаря"""
        return cls(
            timestamp=datetime.fromisoformat(data['timestamp']),
            level_type=data['level_type'],
            price=data['price'],
            pnl_percentage=data['pnl_percentage'],
            pnl_absolute=data['pnl_absolute']
        )


@dataclass 
class ExtendedPositionData:
    """Расширенные данные позиции"""
    signal_id: str
    symbol: str
    direction: str
    entry_price: float
    sl_price: float
    tp1_price: float
    tp2_price: float
    status: str
    created_at: datetime
    
    # Расширенные поля
    entry_volume: Optional[float] = None
    current_price: Optional[float] = None
    updated_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    max_profit: Optional[float] = None
    max_drawdown: Optional[float] = None
    
    # EMA tracking fields
    ema_used_period: Optional[int] = None
    ema_value: Optional[float] = None
    
    # История PnL
    pnl_history: List[PnLRecord] = None
    
    def __post_init__(self):
        if self.pnl_history is None:
            self.pnl_history = []
        if self.updated_at is None:
            self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict:
        """Конвертация в словарь для JSON"""
        data = {
            'signal_id': self.signal_id,
            'symbol': self.symbol,
            'direction': self.direction,
            'entry_price': self.entry_price,
            'sl_price': self.sl_price,
            'tp1_price': self.tp1_price,
            'tp2_price': self.tp2_price,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'entry_volume': self.entry_volume,
            'current_price': self.current_price,
            'max_profit': self.max_profit,
            'max_drawdown': self.max_drawdown,
            'ema_used_period': self.ema_used_period,  # New field
            'ema_value': self.ema_value,              # New field
            'pnl_history': [record.to_dict() for record in self.pnl_history]
        }
        
        # Добавляем опциональные временные метки
        if self.updated_at:
            data['updated_at'] = self.updated_at.isoformat()
        if self.closed_at:
            data['closed_at'] = self.closed_at.isoformat()
            
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ExtendedPositionData':
        """Создание из словаря"""
        pnl_history = []
        if 'pnl_history' in data and data['pnl_history']:
            pnl_history = [PnLRecord.from_dict(record) for record in data['pnl_history']]
        
        # Handle both old and new field names
        entry_price = data.get('entry_price', data.get('entry', 0))
        sl_price = data.get('sl_price', data.get('sl', 0))
        tp1_price = data.get('tp1_price', data.get('tp1', 0))
        tp2_price = data.get('tp2_price', data.get('tp2', 0))
        
        return cls(
            signal_id=data['signal_id'],
            symbol=data['symbol'],
            direction=data['direction'],
            entry_price=entry_price,
            sl_price=sl_price,
            tp1_price=tp1_price,
            tp2_price=tp2_price,
            status=data['status'],
            created_at=datetime.fromisoformat(data['created_at'].replace('Z','')),
            entry_volume=data.get('entry_volume'),
            current_price=data.get('current_price'),
            updated_at=datetime.fromisoformat(data['updated_at'].replace('Z','')) if data.get('updated_at') else None,
            closed_at=datetime.fromisoformat(data['closed_at'].replace('Z','')) if data.get('closed_at') else None,
            max_profit=data.get('max_profit'),
            max_drawdown=data.get('max_drawdown'),
            ema_used_period=data.get('ema_used_period'),  # New field
            ema_value=data.get('ema_value'),              # New field
            pnl_history=pnl_history
        )
    
    def validate_ema_data(self) -> bool:
        """Validate that EMA data is consistent and correct"""
        from config import EMA_PERIOD
        
        # Check that ema_used_period matches the configured value
        if self.ema_used_period is not None and self.ema_used_period != EMA_PERIOD:
            logger.warning(f"EMA period mismatch: expected {EMA_PERIOD}, got {self.ema_used_period}")
            return False
        
        # Check that if ema_used_period is set, ema_value is also set
        if self.ema_used_period is not None and self.ema_value is None:
            logger.warning("EMA period set but EMA value is missing")
            return False
        
        return True


class JSONDataManager:
    """Менеджер для работы с JSON данными"""
    
    def __init__(self, json_file: str = JSON_FILE):
        self.json_file = json_file
        self.backup_dir = Path(json_file).parent / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        self._lock = asyncio.Lock()  # Лок инстанса (оставляем для совместимости)
        
        # Создаем резервную копию при инициализации
        self._create_backup()
        
        logger.info(f"Инициализация JSONDataManager: {json_file}")
    
    def _create_backup(self):
        """Создание резервной копии JSON файла"""
        try:
            if os.path.exists(self.json_file):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = self.backup_dir / f"signals_backup_{timestamp}.json"
                shutil.copy2(self.json_file, backup_file)
                
                # Удаляем старые бэкапы (старше 30 дней)
                self._cleanup_old_backups(days=30)
                
        except Exception as e:
            logger.error(f"Ошибка создания резервной копии: {e}")
    
    def _cleanup_old_backups(self, days: int = 30):
        """Очистка старых резервных копий"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            for backup_file in self.backup_dir.glob("signals_backup_*.json"):
                file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                if file_time < cutoff_date:
                    backup_file.unlink()
                    
        except Exception as e:
            logger.error(f"Ошибка очистки резервных копий: {e}")
    
    async def load_data_async(self) -> Dict[str, Any]:
        """Асинхронная загрузка данных из JSON файла с глобальным блокированием"""
        async with _json_file_lock:
            return self.load_data()
    
    def load_data(self) -> Dict[str, Any]:
        """Загрузка данных из JSON файла"""
        try:
            if not os.path.exists(self.json_file):
                return self._get_empty_data_structure()
            
            with open(self.json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Проверяем и обновляем структуру при необходимости
            return self._validate_and_update_structure(data)
            
        except Exception as e:
            logger.error(f"Ошибка загрузки JSON данных: {e}")
            return self._get_empty_data_structure()
    
    async def save_data_async(self, data: Dict[str, Any]):
        """Асинхронное сохранение данных в JSON файл с глобальным блокированием"""
        async with _json_file_lock:
            self.save_data(data)
    
    def save_data(self, data: Dict[str, Any]):
        """Сохранение данных в JSON файл c ретраями и атомарной заменой (Windows-safe)"""
        # Используем глобальный лок и синхронный путь для совместимости с sync вызовами
        # NB: в sync методе нельзя await, поэтому полагаемся на дисциплину вызовов выше
        try:
            # Обновляем/дополняем метаданные, не перетирая существующие ключи
            meta = data.get('metadata', {})
            meta.update({
                'last_updated': datetime.now().isoformat(),
                'version': '2.0',
                'total_positions': len(data.get('positions', {}))
            })
            data['metadata'] = meta

            # Уникальный временный файл (на случай параллельных сохранений)
            temp_file = f"{self.json_file}.{os.getpid()}.tmp"

            # Пишем содержимое во временный файл
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())

            # Ретраим атомарную замену на Windows при WinError 32
            max_attempts = 10
            delay_sec = 0.1
            for attempt in range(1, max_attempts + 1):
                try:
                    # os.replace атомарен на Windows, но может упасть если файл занят
                    os.replace(temp_file, self.json_file)
                    break
                except OSError as e:
                    # Ошибка доступа к файлу: подождём и повторим
                    if getattr(e, 'winerror', None) == 32 or e.errno in (errno.EACCES, errno.EBUSY):
                        if attempt == max_attempts:
                            raise
                        time.sleep(delay_sec)
                        continue
                    raise
        except Exception as e:
            logger.error(f"Ошибка сохранения JSON данных: {e}")
            try:
                if 'temp_file' in locals() and os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception:
                pass
    
    def _get_empty_data_structure(self) -> Dict[str, Any]:
        """Получение пустой структуры данных"""
        return {
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
    
    def _validate_and_update_structure(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Валидация и обновление структуры данных"""
        # Если это старая версия, конвертируем
        if 'metadata' not in data or data.get('metadata', {}).get('version') != '2.0':
            data = self._migrate_from_old_version(data)
        
        # Проверяем наличие всех необходимых секций
        empty_structure = self._get_empty_data_structure()
        
        for key in empty_structure:
            if key not in data:
                data[key] = empty_structure[key]
        
        return data
    
    def _migrate_from_old_version(self, old_data: Dict[str, Any]) -> Dict[str, Any]:
        """Миграция данных из старой версии"""
        logger.info("Миграция данных в новую версию структуры")
        
        new_data = self._get_empty_data_structure()
        
        # Копируем позиции из старого формата
        if 'positions' in old_data:
            for signal_id, pos_data in old_data['positions'].items():
                # Конвертируем в новый формат, обеспечивая согласованность имен полей
                entry_price = pos_data.get('entry_price', pos_data.get('entry', 0))
                sl_price = pos_data.get('sl_price', pos_data.get('sl', 0))
                tp1_price = pos_data.get('tp1_price', pos_data.get('tp1', 0))
                tp2_price = pos_data.get('tp2_price', pos_data.get('tp2', 0))
                
                extended_pos = ExtendedPositionData(
                    signal_id=signal_id,
                    symbol=pos_data['symbol'],
                    direction=pos_data['direction'],
                    entry_price=entry_price,
                    sl_price=sl_price,
                    tp1_price=tp1_price,
                    tp2_price=tp2_price,
                    status=pos_data['status'],
                    created_at=datetime.fromisoformat(pos_data['created_at'].replace('Z',''))
                )
                
                new_data['positions'][signal_id] = extended_pos.to_dict()
        
        # Копируем статистику
        if 'statistics' in old_data:
            new_data['statistics'].update(old_data['statistics'])
        
        return new_data
    
    async def add_position_async(self, position: ExtendedPositionData):
        """Асинхронное добавление новой позиции"""
        data = await self.load_data_async()
        data['positions'][position.signal_id] = position.to_dict()
        data['statistics']['total_signals'] += 1
        await self.save_data_async(data)
    
    def add_position(self, position: ExtendedPositionData):
        """Добавление новой позиции"""
        data = self.load_data()
        data['positions'][position.signal_id] = position.to_dict()
        data['statistics']['total_signals'] += 1
        self.save_data(data)
    
    async def update_position_async(self, signal_id: str, updates: Dict[str, Any]):
        """Асинхронное обновление позиции"""
        data = await self.load_data_async()
        
        if signal_id in data['positions']:
            data['positions'][signal_id].update(updates)
            data['positions'][signal_id]['updated_at'] = datetime.now().isoformat()
            await self.save_data_async(data)
    
    def update_position(self, signal_id: str, updates: Dict[str, Any]):
        """Обновление позиции"""
        data = self.load_data()
        
        if signal_id in data['positions']:
            data['positions'][signal_id].update(updates)
            data['positions'][signal_id]['updated_at'] = datetime.now().isoformat()
            self.save_data(data)
    
    async def add_pnl_record_async(self, signal_id: str, pnl_record: PnLRecord):
        """Асинхронное добавление записи PnL"""
        data = await self.load_data_async()
        
        if signal_id in data['positions']:
            if 'pnl_history' not in data['positions'][signal_id]:
                data['positions'][signal_id]['pnl_history'] = []
            
            data['positions'][signal_id]['pnl_history'].append(pnl_record.to_dict())
            await self.save_data_async(data)
    
    def add_pnl_record(self, signal_id: str, pnl_record: PnLRecord):
        """Добавление записи PnL"""
        data = self.load_data()
        
        if signal_id in data['positions']:
            if 'pnl_history' not in data['positions'][signal_id]:
                data['positions'][signal_id]['pnl_history'] = []
            
            data['positions'][signal_id]['pnl_history'].append(pnl_record.to_dict())
            self.save_data(data)
    
    async def get_positions_async(self, status_filter: Optional[str] = None) -> Dict[str, ExtendedPositionData]:
        """Асинхронное получение позиций с фильтрацией по статусу"""
        data = await self.load_data_async()
        positions = {}
        
        for signal_id, pos_data in data['positions'].items():
            if status_filter is None or pos_data['status'] == status_filter:
                positions[signal_id] = ExtendedPositionData.from_dict(pos_data)
        
        return positions
    
    def get_positions(self, status_filter: Optional[str] = None) -> Dict[str, ExtendedPositionData]:
        """Получение позиций с фильтрацией по статусу"""
        data = self.load_data()
        positions = {}
        
        for signal_id, pos_data in data['positions'].items():
            if status_filter is None or pos_data['status'] == status_filter:
                positions[signal_id] = ExtendedPositionData.from_dict(pos_data)
        
        return positions
    
    async def get_statistics_async(self) -> Dict[str, Any]:
        """Асинхронное получение статистики"""
        data = await self.load_data_async()
        return data['statistics']
    
    def get_statistics(self) -> Dict[str, Any]:
        """Получение статистики"""
        data = self.load_data()
        return data['statistics']
    
    async def update_statistics_async(self, stats_update: Dict[str, Any]):
        """Асинхронное обновление статистики"""
        data = await self.load_data_async()
        data['statistics'].update(stats_update)
        await self.save_data_async(data)
    
    def update_statistics(self, stats_update: Dict[str, Any]):
        """Обновление статистики"""
        data = self.load_data()
        data['statistics'].update(stats_update)
        self.save_data(data)
    
    def export_to_csv(self, output_file: str):
        """Экспорт данных в CSV формат"""
        import csv
        
        data = self.load_data()
        
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'signal_id', 'symbol', 'direction', 'entry_price', 'sl_price',
                'tp1_price', 'tp2_price', 'status', 'created_at', 'closed_at',
                'max_profit', 'max_drawdown', 'final_pnl'
            ]
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for signal_id, pos_data in data['positions'].items():
                # Вычисляем финальный PnL
                final_pnl = 0.0
                if pos_data.get('pnl_history'):
                    final_pnl = pos_data['pnl_history'][-1]['pnl_percentage']
                
                writer.writerow({
                    'signal_id': signal_id,
                    'symbol': pos_data['symbol'],
                    'direction': pos_data['direction'],
                    'entry_price': pos_data['entry_price'],
                    'sl_price': pos_data['sl_price'],
                    'tp1_price': pos_data['tp1_price'],
                    'tp2_price': pos_data['tp2_price'],
                    'status': pos_data['status'],
                    'created_at': pos_data['created_at'],
                    'closed_at': pos_data.get('closed_at', ''),
                    'max_profit': pos_data.get('max_profit', 0.0),
                    'max_drawdown': pos_data.get('max_drawdown', 0.0),
                    'final_pnl': final_pnl
                })
        
        logger.info(f"Данные экспортированы в CSV: {output_file}")
    
    def get_open_signal(self, symbol: str, direction: str):
        """Get open signal for symbol+direction - for deduplication check"""
        data = self.load_data()
        positions = data.get('positions', {})
        
        # Look for existing signal with same symbol and direction that is OPEN or PARTIAL
        for signal_id, pos_data in positions.items():
            if (pos_data.get('symbol') == symbol and 
                pos_data.get('direction') == direction and 
                pos_data.get('status') in ['OPEN', 'PARTIAL']):
                return pos_data
                
        return None
        
    def count_signals(self, status: list[str] = None):
        """Count signals with specific status - for active positions count"""
        data = self.load_data()
        positions = data.get('positions', {})
        
        if status is None:
            return len(positions)
            
        count = 0
        for signal_id, pos_data in positions.items():
            if pos_data.get('status') in status:
                count += 1
                
        return count
        
    def get_daily_report(self, date: Optional[datetime] = None) -> Dict[str, Any]:
        """Получение дневного отчета"""
        if date is None:
            date = datetime.now()
        
        date_str = date.strftime("%Y-%m-%d")
        data = self.load_data()
        
        daily_positions = []
        daily_pnl = 0.0
        
        for signal_id, pos_data in data['positions'].items():
            created_date = datetime.fromisoformat(pos_data['created_at']).strftime("%Y-%m-%d")
            
            if created_date == date_str:
                daily_positions.append(pos_data)
                
                # Суммируем PnL
                if pos_data.get('pnl_history'):
                    daily_pnl += pos_data['pnl_history'][-1]['pnl_percentage']
        
        return {
            'date': date_str,
            'total_signals': len(daily_positions),
            'total_pnl': daily_pnl,
            'positions': daily_positions
        }