"""Position Manager - Мониторинг TP/SL уровней"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from enum import Enum
import math

from config import logger, safe_log
from strategy import Signal
from json_manager import JSONDataManager, ExtendedPositionData, PnLRecord
from typing import Any


def _validate_price_input(price: float, field_name: str) -> bool:
    """Validate price input for PnL calculations"""
    if not isinstance(price, (int, float)):
        logger.warning(f"Invalid price type for {field_name}: {type(price)}")
        return False
    
    if not math.isfinite(price):
        logger.warning(f"Non-finite price for {field_name}: {price}")
        return False
    
    if price <= 0:
        logger.warning(f"Non-positive price for {field_name}: {price}")
        return False
    
    return True


class PositionStatus(Enum):
    """Статусы позиций"""
    OPEN = "OPEN"
    PARTIAL = "PARTIAL"  # Changed from TP1_HIT to PARTIAL per requirements
    TP2_HIT = "TP2_HIT"
    SL_HIT = "SL_HIT"
    CLOSED = "CLOSED"


@dataclass
class PositionUpdate:
    """Обновление позиции"""
    signal_id: str
    symbol: str
    direction: str
    current_price: float
    old_status: str
    new_status: str
    pnl_percentage: float
    triggered_level: Optional[str] = None  # TP1, TP2, SL
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class PositionManager:
    """Менеджер позиций для мониторинга TP/SL"""
    
    def __init__(self, json_file=None):
        self.active_positions: Dict[str, Signal] = {}  # {signal_id: Signal}
        self.position_updates: List[PositionUpdate] = []
        self.json_manager = JSONDataManager(json_file) if json_file else JSONDataManager()
        self.statistics = {
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
        }
        logger.info("Инициализация PositionManager с новым JSON менеджером")
        self.load_positions()
        
    def generate_signal_id(self, signal: Signal) -> str:
        """Генерация уникального ID для сигнала"""
        timestamp = signal.created_at.strftime("%Y%m%d_%H%M%S")
        return f"{signal.symbol}_{signal.direction}_{timestamp}"
        
    def add_position(self, signal: Signal) -> str:
        """Добавление новой позиции для мониторинга"""
        signal_id = self.generate_signal_id(signal)
        signal.status = PositionStatus.OPEN.value
        
        # Создаем расширенные данные позиции
        extended_position = ExtendedPositionData(
            signal_id=signal_id,
            symbol=signal.symbol,
            direction=signal.direction,
            entry_price=signal.entry,
            sl_price=signal.sl,
            tp1_price=signal.tp1,
            tp2_price=signal.tp2,
            status=signal.status,
            created_at=signal.created_at,
            current_price=signal.entry,
            entry_volume=1000.0  # Условный объем для расчета PnL в $
        )
        
        # Добавляем начальную запись PnL
        initial_pnl = PnLRecord(
            timestamp=datetime.now(),
            level_type="ENTRY",
            price=signal.entry,
            pnl_percentage=0.0,
            pnl_absolute=0.0
        )
        extended_position.pnl_history.append(initial_pnl)
        
        self.active_positions[signal_id] = signal
        self.json_manager.add_position(extended_position)
        
        # Update in-memory statistics
        self.statistics['total_signals'] += 1
        
        safe_log('info', f"📈 Новая позиция добавлена: {signal_id}")
        logger.info(f"   {signal.direction} {signal.symbol} @ ${signal.entry}")
        logger.info(f"   SL: ${signal.sl} | TP1: ${signal.tp1} | TP2: ${signal.tp2}")
        
        return signal_id
        
    def check_position_levels(
        self, signal_id: str, current_price: float
    ) -> Optional[PositionUpdate]:
        """Проверка уровней TP/SL для позиции - exact logic from requirements"""
        
        # Load the signal data from JSON
        positions = self.json_manager.get_positions()
        if signal_id not in positions:
            return None
            
        signal = positions[signal_id]
        
        # Convert to dictionary for manipulation
        signal_dict = signal.to_dict()
        original_status = signal_dict['status']  # Store original status before update
        
        # Apply the exact update logic
        updated_signal = self.update_signal(signal_dict, current_price)
        
        if updated_signal is None:
            return None
            
        # If signal was updated, process the changes
        old_status = original_status  # Use the stored original status
        new_status = updated_signal["status"]
        
        # Determine triggered level based on exit_reason or status change
        triggered_level = updated_signal.get("exit_reason", "").replace("_HIT", "")
        
        # For TP1 hits, we need to set the triggered_level manually since we don't set exit_reason
        if new_status == "PARTIAL" and old_status == "OPEN":
            triggered_level = "TP1"
        
        # Remove debug output
        # logger.debug(f"DEBUG: old_status={old_status}, new_status={new_status}, triggered_level={triggered_level}")
        
        # Calculate PnL using the weighted method if this is a partial or final close
        entry = signal_dict["entry_price"]
        direction = signal_dict["direction"]
        
        # For partial close (TP1), use 50% weight
        # For final close (TP2 or SL), use remaining weight (50% if TP1 already hit, 100% if not)
        if triggered_level == "TP1":
            # Partial close at TP1 with 50% weight
            exits = [(updated_signal["tp1_price"], 0.5)]
            pnl_percentage = self.calculate_pnl(entry, exits, direction)
        elif triggered_level == "TP2":
            # Check if TP1 was already hit
            if signal_dict.get("partial_hit"):
                # TP1 already hit, so this is the remaining 50%
                exits = [(updated_signal["tp2_price"], 0.5)]
            else:
                # TP1 not hit, so this is 100% at TP2
                exits = [(updated_signal["tp2_price"], 1.0)]
            pnl_percentage = self.calculate_pnl(entry, exits, direction)
        elif triggered_level == "SL":
            # Full close at SL
            exits = [(updated_signal["sl_price"], 1.0)]
            pnl_percentage = self.calculate_pnl(entry, exits, direction)
        else:
            pnl_percentage = 0.0
            
        # Save the updated signal to JSON
        self.json_manager.update_position(signal_id, updated_signal)
        
        # Create position update object
        update = PositionUpdate(
            signal_id=signal_id,
            symbol=signal_dict["symbol"],
            direction=signal_dict["direction"],
            current_price=current_price,
            old_status=old_status,
            new_status=new_status,
            pnl_percentage=pnl_percentage,
            triggered_level=triggered_level
        )
        
        # Update statistics
        self.update_statistics(triggered_level, pnl_percentage)
        
        # Save update
        self.position_updates.append(update)
        
        safe_log('info', f"🎯 Уровень достигнут: {signal_id}")
        logger.info(f"   {triggered_level} @ ${current_price:.6f}")
        logger.info(f"   PnL: {pnl_percentage:+.2f}%")
        
        # If this is TP1, log the SL move to breakeven
        if triggered_level == "TP1":
            logger.info(f"   SL обновлен до breakeven: ${updated_signal['sl_price']:.6f}")
            
        return update
        
    def update_signal(self, signal, current_price):
        """Exact SL/TP monitoring logic from requirements"""
        entry = signal["entry_price"]  # Adjusted field name
        direction = signal["direction"]
        sl = signal["sl_price"]        # Adjusted field name
        tp1 = signal["tp1_price"]      # Adjusted field name
        tp2 = signal["tp2_price"]      # Adjusted field name

        # Enforce monitor_from: only monitor when candle_time >= monitor_from
        current_candle_time = signal.get("current_candle_time")
        monitor_from = signal.get("monitor_from")
        if monitor_from and current_candle_time:
            try:
                if isinstance(current_candle_time, (int, float)):
                    cur_iso = datetime.fromtimestamp(int(current_candle_time), tz=timezone.utc).isoformat().replace("+00:00", "Z")
                else:
                    cur_iso = datetime.fromisoformat(str(current_candle_time).replace('Z','')).replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
                mon_iso = str(monitor_from)
                cur_dt = datetime.fromisoformat(cur_iso.replace('Z','')).replace(tzinfo=timezone.utc)
                mon_dt = datetime.fromisoformat(mon_iso.replace('Z','')).replace(tzinfo=timezone.utc)
                if cur_dt < mon_dt:
                    return None
            except Exception:
                pass

        if direction == "LONG":
            # Stop Loss
            if current_price <= sl and signal["status"] in ["OPEN", "PARTIAL"]:
                signal["status"] = "CLOSED"
                signal["exit_reason"] = "SL_HIT"
                # Добавляем логирование для отладки
                logger.info(f"[{signal['symbol']}] Проверка TP/SL на свече "
                           f"{current_candle_time} (Entry={entry}, TP={tp2}, "
                           f"SL={sl}) - SL сработал")
                return signal

            # Take Profit 2 (check first for proper order as per requirements 4.3, 4.4, 4.5, 4.6)
            if current_price >= tp2 and signal["status"] in ["OPEN", "PARTIAL"]:
                signal["status"] = "CLOSED"
                signal["exit_reason"] = "TP2_HIT"
                # Добавляем логирование для отладки
                logger.info(f"[{signal['symbol']}] Проверка TP/SL на свече "
                           f"{current_candle_time} (Entry={entry}, TP2={tp2}, "
                           f"SL={sl}) - TP2 сработал")
                return signal

            # Take Profit 1
            if current_price >= tp1 and signal["status"] == "OPEN":
                signal["status"] = "PARTIAL"
                signal["partial_hit"] = True
                signal["sl_price"] = entry  # move to breakeven
                # Добавляем логирование для отладки
                logger.info(f"[{signal['symbol']}] Проверка TP/SL на свече "
                           f"{current_candle_time} (Entry={entry}, TP1={tp1}, "
                           f"SL={sl}) - TP1 сработал")
                return signal

        elif direction == "SHORT":
            if current_price >= sl and signal["status"] in ["OPEN", "PARTIAL"]:
                signal["status"] = "CLOSED"
                signal["exit_reason"] = "SL_HIT"
                # Добавляем логирование для отладки
                logger.info(f"[{signal['symbol']}] Проверка TP/SL на свече "
                           f"{current_candle_time} (Entry={entry}, TP={tp2}, "
                           f"SL={sl}) - SL сработал")
                return signal

            # Take Profit 2 (check first for proper order as per requirements 4.3, 4.4, 4.5, 4.6)
            if current_price <= tp2 and signal["status"] in ["OPEN", "PARTIAL"]:
                signal["status"] = "CLOSED"
                signal["exit_reason"] = "TP2_HIT"
                # Добавляем логирование для отладки
                logger.info(f"[{signal['symbol']}] Проверка TP/SL на свече "
                           f"{current_candle_time} (Entry={entry}, TP2={tp2}, "
                           f"SL={sl}) - TP2 сработал")
                return signal

            # Take Profit 1
            if current_price <= tp1 and signal["status"] == "OPEN":
                signal["status"] = "PARTIAL"
                signal["partial_hit"] = True
                signal["sl_price"] = entry
                # Добавляем логирование для отладки
                logger.info(f"[{signal['symbol']}] Проверка TP/SL на свече "
                           f"{current_candle_time} (Entry={entry}, TP1={tp1}, "
                           f"SL={sl}) - TP1 сработал")
                return signal

        return None
    
    def calculate_pnl(self, entry: float, exits: list[tuple[float, float]], direction: str) -> float:
        """
        Calculate weighted PnL for partial closes.
        Do not sum TP1+TP2 fully.
        
        exits: list of tuples (exit_price, weight)
               weight is fraction of position closed (0.5 = 50%)
        Example: [(tp1, 0.5), (tp2, 0.5)]
        """
        # Validate inputs
        if not _validate_price_input(entry, "entry_price"):
            return 0.0
            
        if not exits:
            logger.warning("Empty exits list provided to calculate_pnl")
            return 0.0
            
        if direction not in ["LONG", "SHORT"]:
            logger.warning(f"Invalid direction provided to calculate_pnl: {direction}")
            return 0.0
            
        pnl_total = 0.0
        for exit_price, weight in exits:
            if not _validate_price_input(exit_price, "exit_price"):
                return 0.0
                
            if not isinstance(weight, (int, float)) or weight < 0 or weight > 1:
                logger.warning(f"Invalid weight provided to calculate_pnl: {weight}")
                return 0.0
            
            if direction == "LONG":
                profit_pct = (exit_price - entry) / entry
            else:  # SHORT
                profit_pct = (entry - exit_price) / entry
            pnl_total += profit_pct * weight
        return round(pnl_total * 100, 2)  # return in %
        
    def calculate_pnl_percentage(self, signal: Signal, current_price: float) -> float:
        """Расчет PnL в процентах"""
        # Validate inputs
        if not _validate_price_input(current_price, f"{signal.symbol}_current_price"):
            return 0.0
            
        if signal.direction == "LONG":
            return ((current_price - signal.entry) / signal.entry) * 100
        else:  # SHORT
            return ((signal.entry - current_price) / signal.entry) * 100
            
    def _calculate_absolute_pnl(self, signal: Signal, current_price: float, volume: float = 1000.0) -> float:
        """Расчет абсолютного PnL в $"""
        # Validate inputs
        if not _validate_price_input(current_price, f"{signal.symbol}_current_price"):
            return 0.0
            
        if not isinstance(volume, (int, float)) or volume <= 0:
            logger.warning(f"Invalid volume provided to _calculate_absolute_pnl: {volume}")
            return 0.0
        
        pnl_percentage = self.calculate_pnl_percentage(signal, current_price)
        return (pnl_percentage / 100) * volume
        
    def _update_position_extremes(self, signal_id: str, current_price: float):
        """Обновление максимальной прибыли и просадки"""
        if signal_id not in self.active_positions:
            return
            
        signal = self.active_positions[signal_id]
        current_pnl = self.calculate_pnl_percentage(signal, current_price)
        
        # Обновляем в JSON
        updates = {
            'current_price': current_price
        }
        
        # Получаем текущие экстремумы из JSON
        positions = self.json_manager.get_positions()
        if signal_id in positions:
            pos_data = positions[signal_id]
            max_profit = pos_data.max_profit or 0.0
            max_drawdown = pos_data.max_drawdown or 0.0
            
            # Обновляем экстремумы
            if current_pnl > max_profit:
                updates['max_profit'] = current_pnl
            if current_pnl < max_drawdown:
                updates['max_drawdown'] = current_pnl
                
            self.json_manager.update_position(signal_id, updates)
            
    def update_statistics(self, triggered_level: str, pnl_percentage: float):
        """Обновление статистики"""
        if triggered_level == "TP1":
            self.statistics['tp1_hits'] += 1
        elif triggered_level == "TP2":
            self.statistics['tp2_hits'] += 1
        elif triggered_level == "SL":
            self.statistics['sl_hits'] += 1
            
        self.statistics['total_pnl'] += pnl_percentage
        
        # Обновляем винрейт
        total_closed = (self.statistics['tp1_hits'] + 
                       self.statistics['tp2_hits'] + 
                       self.statistics['sl_hits'])
        
        if total_closed > 0:
            wins = self.statistics['tp1_hits'] + self.statistics['tp2_hits']
            self.statistics['win_rate'] = (wins / total_closed) * 100
            self.statistics['average_pnl_per_trade'] = self.statistics['total_pnl'] / total_closed
        
        # Обновляем экстремумы PnL
        if pnl_percentage > self.statistics['best_trade_pnl']:
            self.statistics['best_trade_pnl'] = pnl_percentage
        if pnl_percentage < self.statistics['worst_trade_pnl']:
            self.statistics['worst_trade_pnl'] = pnl_percentage
        
        # Сохраняем обновленную статистику
        self.json_manager.update_statistics(self.statistics)
        
    def get_active_positions_count(self) -> int:
        """Get count of active positions (OPEN or PARTIAL) - exact function from requirements"""
        return self.json_manager.count_signals(status=["OPEN", "PARTIAL"])
        
    def get_active_positions(self) -> Dict[str, Any]:
        """Get all active positions (OPEN or PARTIAL)"""
        positions = self.json_manager.get_positions()
        active_positions = {}
        for signal_id, position in positions.items():
            if position.status in ["OPEN", "PARTIAL"]:
                active_positions[position.symbol] = position
        return active_positions
        
    def get_statistics_summary(self) -> str:
        """Получение сводки статистики"""
        stats = self.json_manager.get_statistics()
        
        summary = (
            f"📊 Статистика торговых сигналов:\n\n"
            f"🎯 Всего сигналов: {stats['total_signals']}\n"
            f"✅ TP1 достигнуто: {stats['tp1_hits']}\n"
            f"🎉 TP2 достигнуто: {stats['tp2_hits']}\n"
            f"❌ SL сработало: {stats['sl_hits']}\n"
            f"📈 Винрейт: {stats['win_rate']:.1f}%\n"
            f"💰 Общий PnL: {stats['total_pnl']:+.2f}%\n"
            f"📊 Ср. PnL/сделка: {stats.get('average_pnl_per_trade', 0):+.2f}%\n"
            f"🚀 Лучшая сделка: {stats.get('best_trade_pnl', 0):+.2f}%\n"
            f"🔻 Худшая сделка: {stats.get('worst_trade_pnl', 0):+.2f}%\n"
            f"📍 Активных позиций: {self.get_active_positions_count()}"
        )
        
        return summary
        
    def cleanup_old_positions(self, days: int = 7):
        """Очистка старых позиций"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        old_positions = []
        positions = self.json_manager.get_positions()
        
        for signal_id, pos_data in positions.items():
            if (pos_data.created_at < cutoff_date and 
                pos_data.status in ["CLOSED", "SL_HIT"]):  # Updated to match current status values
                old_positions.append(signal_id)
                # Удаляем из локального словаря
                if signal_id in self.active_positions:
                    del self.active_positions[signal_id]
                    
        if old_positions:
            logger.info(f"🧹 Очищено {len(old_positions)} старых позиций")
            # Обновляем JSON (удаляем старые позиции)
            data = self.json_manager.load_data()
            for signal_id in old_positions:
                if signal_id in data['positions']:
                    del data['positions'][signal_id]
            self.json_manager.save_data(data)
            
    # Оставляем старые методы для обратной совместимости
    def save_positions(self):
        """Сохранение позиций (для обратной совместимости)"""
        # Обновляем статистику в JSON
        self.json_manager.update_statistics(self.statistics)
            
    def load_positions(self):
        """Загрузка позиций из JSON"""
        try:
            data = self.json_manager.load_data()
            
            # Загружаем позиции в локальный словарь
            if 'positions' in data:
                for signal_id, pos_data in data['positions'].items():
                    # Handle both old and new data formats
                    # Check for both 'entry_price' and 'entry' fields
                    entry_price = pos_data.get('entry_price', pos_data.get('entry', 0))
                    sl_price = pos_data.get('sl_price', pos_data.get('sl', 0))
                    tp1_price = pos_data.get('tp1_price', pos_data.get('tp1', 0))
                    tp2_price = pos_data.get('tp2_price', pos_data.get('tp2', 0))
                    
                    # Ensure all required fields are present
                    if entry_price is None or sl_price is None or tp1_price is None or tp2_price is None:
                        logger.warning(f"Пропущена позиция {signal_id} из-за отсутствия обязательных полей")
                        continue
                    
                    signal = Signal(
                        symbol=pos_data['symbol'],
                        direction=pos_data['direction'],
                        entry=entry_price,
                        sl=sl_price,
                        tp1=tp1_price,
                        tp2=tp2_price
                    )
                    signal.status = pos_data['status']
                    signal.created_at = datetime.fromisoformat(pos_data['created_at'].replace('Z',''))
                    
                    self.active_positions[signal_id] = signal
                    
            # Загружаем статистику
            if 'statistics' in data:
                self.statistics.update(data['statistics'])
                
            safe_log('info', f"📂 Загружено {len(self.active_positions)} позиций")
            
        except Exception as e:
            logger.error(f"Ошибка загрузки позиций: {e}")
    
    def get_position_details(self, signal_id: str) -> Optional[Dict]:
        """Получение детальной информации о позиции"""
        positions = self.json_manager.get_positions()
        if signal_id in positions:
            pos_data = positions[signal_id]
            return {
                'signal_id': signal_id,
                'symbol': pos_data.symbol,
                'direction': pos_data.direction,
                'entry_price': pos_data.entry_price,
                'current_price': pos_data.current_price,
                'status': pos_data.status,
                'max_profit': pos_data.max_profit or 0.0,
                'max_drawdown': pos_data.max_drawdown or 0.0,
                'pnl_history': pos_data.pnl_history,
                'created_at': pos_data.created_at,
                'updated_at': pos_data.updated_at
            }
        return None
        
    def export_data_to_csv(self, filename: str = None):
        """Экспорт данных в CSV"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"trading_signals_{timestamp}.csv"
            
        self.json_manager.export_to_csv(filename)
        return filename
        
    def get_daily_report(self, date: datetime = None) -> Dict:
        """Получение дневного отчета"""
        return self.json_manager.get_daily_report(date)
        
    def monitor_all_positions(self, market_data: Dict) -> List[PositionUpdate]:
        """Мониторинг всех активных позиций - exact function from requirements"""
        updates = []
        
        tickers = market_data.get('tickers', {})
        ohlcv_data = market_data.get('ohlcv', {})
        
        # Get all positions from JSON
        positions = self.json_manager.get_positions()
        
        for signal_id, position in positions.items():
            # Only monitor OPEN or PARTIAL positions
            if position.status not in ["OPEN", "PARTIAL"]:
                continue
                
            symbol = position.symbol
            if symbol not in tickers:
                continue
                
            # Build and iterate closed candles chronologically, skipping active one
            closed_candles = []
            if symbol in ohlcv_data and len(ohlcv_data[symbol]) > 1:
                closed_candles = ohlcv_data[symbol][:-1]

            pos_raw: Dict[str, Any] = self.json_manager.load_data().get('positions', {}).get(signal_id, {})
            monitor_from_iso = pos_raw.get('monitor_from') if pos_raw else None

            # Prepare position_dict for use in both loop and fallback
            position_dict = position.to_dict()
            
            if not closed_candles:
                # Skip monitoring if no closed candle data available
                # This ensures we only monitor based on closed candles with proper timing
                continue

            # Process each closed candle
            position_updated = False
            for cc in closed_candles:
                candle_time = cc.get('timestamp') or cc.get('time')
                try:
                    if isinstance(candle_time, (int, float)):
                        candle_iso = datetime.fromtimestamp(int(candle_time), tz=timezone.utc).isoformat().replace("+00:00", "Z")
                    else:
                        # FIX: Convert to string before calling replace to handle numpy types
                        candle_iso = datetime.fromisoformat(str(candle_time).replace('Z','')).replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
                except Exception:
                    continue

                if monitor_from_iso:
                    try:
                        # FIX: Convert to string before calling replace to handle numpy types
                        if datetime.fromisoformat(str(candle_iso).replace('Z','')).replace(tzinfo=timezone.utc) < datetime.fromisoformat(str(monitor_from_iso).replace('Z','')).replace(tzinfo=timezone.utc):
                            continue
                    except Exception:
                        pass

                # Ensure position_dict always defined before use in this loop
                position_dict = position.to_dict()
                position_dict["current_candle_time"] = candle_iso
                
                # Capture original status before any updates
                original_status = position_dict["status"]

                high_price = cc['high']
                low_price = cc['low']

                direction = position.direction
                updated_position = None

                logger.info("MONITOR CHECK", extra={"symbol": position.symbol, "candle_time": candle_iso, "high": high_price, "low": low_price})

                if direction == "LONG":
                    # TP2 first
                    if high_price >= position.tp2_price:
                        updated_position = self.update_signal(position_dict, high_price)
                    # TP1 then potential TP2 in same candle
                    elif high_price >= position.tp1_price and position_dict["status"] == "OPEN":
                        updated_position = self.update_signal(position_dict, high_price)
                        if updated_position is not None and high_price >= position.tp2_price:
                            position_dict.update(updated_position)
                            updated_position = self.update_signal(position_dict, high_price)
                    # SL last
                    elif low_price <= position.sl_price:
                        updated_position = self.update_signal(position_dict, low_price)
                else:
                    # SHORT mirror
                    if low_price <= position.tp2_price:
                        updated_position = self.update_signal(position_dict, low_price)
                    elif low_price <= position.tp1_price and position_dict["status"] == "OPEN":
                        updated_position = self.update_signal(position_dict, low_price)
                        if updated_position is not None and low_price <= position.tp2_price:
                            position_dict.update(updated_position)
                            updated_position = self.update_signal(position_dict, low_price)
                    elif high_price >= position.sl_price:
                        updated_position = self.update_signal(position_dict, high_price)

                if updated_position is None:
                    continue

                # Mark that position was updated
                position_updated = True
                
                self.json_manager.update_position(signal_id, updated_position)

                entry = position.entry_price
                exit_reason = updated_position.get("exit_reason", "")
                if exit_reason == "SL_HIT":
                    exits = [(updated_position["sl_price"], 1.0)]
                    triggered_level = "SL"
                elif exit_reason == "TP2_HIT":
                    if position_dict.get("partial_hit"):
                        exits = [(updated_position["tp2_price"], 0.5)]
                    else:
                        exits = [(updated_position["tp2_price"], 1.0)]
                    triggered_level = "TP2"
                else:
                    exits = [(updated_position["tp1_price"], 0.5)]
                    triggered_level = "TP1"

                pnl_percentage = self.calculate_pnl(entry, exits, direction)

                updates.append(PositionUpdate(
                    signal_id=signal_id,
                    symbol=position.symbol,
                    direction=position.direction,
                    current_price=exits[0][0],
                    old_status=original_status,
                    new_status=updated_position["status"],
                    pnl_percentage=pnl_percentage,
                    triggered_level=triggered_level
                ))

                self.update_statistics(triggered_level, pnl_percentage)

                safe_log('info', f"🎯 Уровень достигнут: {signal_id}")
                logger.info(f"   {triggered_level} @ ${exits[0][0]:.6f}")
                logger.info(f"   PnL: {pnl_percentage:+.2f}%")
                # Break after TP2 or SL; for TP1 continue to allow further processing on next candles
                if triggered_level in ("TP2", "SL"):
                    break
            
            # Only use fallback if no closed candles were available AND no position was updated
            if not closed_candles and not position_updated:
                # Fallback to original behavior if no closed candle data available
                current_price = tickers[symbol]['last']
                # Ensure variable exists in this branch
                position_dict["current_candle_time"] = None
                
                # Apply the exact update logic
                updated_position = self.update_signal(position_dict, current_price)
                
                if updated_position is not None:
                    # Save the updated position to JSON
                    self.json_manager.update_position(signal_id, updated_position)
                    
                    # Calculate PnL
                    entry = position.entry_price
                    direction = position.direction
                    
                    # Determine exit type and weight for PnL calculation
                    exit_reason = updated_position.get("exit_reason", "")
                    if exit_reason == "SL_HIT":
                        exits = [(updated_position["sl_price"], 1.0)]
                        triggered_level = "SL"
                    elif exit_reason == "TP2_HIT":
                        # Check if TP1 was already hit
                        if position_dict.get("partial_hit"):
                            # TP1 already hit, so this is the remaining 50%
                            exits = [(updated_position["tp2_price"], 0.5)]
                        else:
                            # TP1 not hit, so this is 100% at TP2
                            exits = [(updated_position["tp2_price"], 1.0)]
                        triggered_level = "TP2"
                    else:
                        # This is a partial hit (TP1)
                        exits = [(updated_position["tp1_price"], 0.5)]
                        triggered_level = "TP1"
                    
                    pnl_percentage = self.calculate_pnl(entry, exits, direction)
                    
                    # Create position update object
                    update = PositionUpdate(
                        signal_id=signal_id,
                        symbol=position.symbol,
                        direction=position.direction,
                        current_price=current_price,
                        old_status=position_dict["status"],
                        new_status=updated_position["status"],
                        pnl_percentage=pnl_percentage,
                        triggered_level=triggered_level
                    )
                    
                    # Update statistics
                    self.update_statistics(triggered_level, pnl_percentage)
                    
                    # Save update
                    updates.append(update)
                    
                    safe_log('info', f"🎯 Уровень достигнут: {signal_id}")
                    logger.info(f"   {triggered_level} @ ${current_price:.6f}")
                    logger.info(f"   PnL: {pnl_percentage:+.2f}%")
                    
                    # If this is TP1, log the SL move to breakeven
                    if triggered_level == "TP1":
                        logger.info(f"   SL обновлен до breakeven: "
                                   f"${updated_position['sl_price']:.6f}")
        
        return updates


def _validate_price_input(price: float, context: str = "price") -> bool:
    """
    Validate that price input is positive and finite.
    Requirement 6.5: Validate all price inputs are positive and finite
    """
    if not isinstance(price, (int, float)):
        logger.warning(f"Invalid {context} type: {type(price)}")
        return False
        
    if not math.isfinite(price):
        logger.warning(f"Non-finite {context}: {price}")
        return False
        
    if price <= 0:
        logger.warning(f"Non-positive {context}: {price}")
        return False
        
    return True
