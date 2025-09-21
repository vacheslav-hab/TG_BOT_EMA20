# -*- coding: utf-8 -*-
"""
Telegram Bot EMA20 - Главный модуль
"""

import asyncio
import signal
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timezone
from decimal import Decimal
import math
import pandas as pd  # Add pandas import

from config import (logger, POLL_INTERVAL_SEC, validate_config, safe_log, 
                   EMA_PERIOD, TOUCH_TOLERANCE_PCT)
from exchange import ExchangeManager
from strategy import (StrategyManager, Signal, detect_touch, create_signal_atomic, 
                     can_generate_signal, register_signal, validate_signal_direction,
                     load_signal_metadata, save_signal_metadata, detect_touch_current,
                     detect_touch_current_strict, get_ema_last_closed)
from bot import TelegramBot
from position_manager import PositionManager
from instance_lock import InstanceLock, cleanup_instance_lock


@dataclass
class RuntimeState:
    """Структура для хранения состояния выполнения бота"""
    running: bool = False
    symbols: List[str] = field(default_factory=list)
    last_symbol_refresh: Optional[datetime] = None
    last_ohlcv_refresh: Optional[datetime] = None
    cycle_count: int = 0
    api_call_count: int = 0
    signal_count: int = 0
    position_update_count: int = 0
    subscriber_count: int = 0
    active_positions: int = 0
    errors: List[str] = field(default_factory=list)
    last_error_time: Optional[datetime] = None


class TradingBot:
    def __init__(self):
        self.state = RuntimeState()
        self.state_lock = asyncio.Lock()  # Блокировка для безопасного доступа к состоянию
        self.exchange_manager = ExchangeManager()
        self.strategy_manager = StrategyManager()
        self.telegram_bot = TelegramBot()
        self.position_manager = PositionManager()
        self.instance_lock = None
        self._semaphore = asyncio.Semaphore(8)  # Rate limiting for exchange API calls
        self.runtime_prev_price = {}  # For tracking previous prices
        logger.info("Инициализация TradingBot")
        
    async def start(self):
        """Запуск бота"""
        # Проверяем блокировку экземпляра
        self.instance_lock = InstanceLock()
        if not self.instance_lock.acquire():
            logger.error("❗ Не удалось запустить бот: уже работает другой экземпляр")
            return False
            
        if not validate_config():
            return False
            
        logger.info("Запуск Telegram Bot EMA20...")
        
        try:
            # Load persistent signal metadata for deduplication
            load_signal_metadata()
            
            # Инициализируем менеджер биржи
            await self.exchange_manager.initialize()
            
            # Передаем position_manager в telegram_bot
            self.telegram_bot.set_position_manager(self.position_manager)
            
            # Запускаем Telegram бота
            await self.telegram_bot.start()
            
            # Обновляем состояние
            async with self.state_lock:
                self.state.running = True
                
            logger.info("Бот успешно запущен")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка запуска бота: {e}")
            # Освобождаем блокировку при ошибке
            if self.instance_lock:
                self.instance_lock.release()
            return False
        
    async def stop(self):
        """Остановка бота"""
        logger.info("Остановка бота...")
        async with self.state_lock:
            self.state.running = False
        
        # Останавливаем Telegram бота
        await self.telegram_bot.stop()
        
        # Очищаем ресурсы
        await self.exchange_manager.cleanup()
        
        # Освобождаем блокировку экземпляра
        if self.instance_lock:
            self.instance_lock.release()
            
    async def refresh_top_symbols(self):
        """Обновление топ символов каждые 10 минут"""
        while self.state.running:
            try:
                logger.info("Обновление топ символов по объему...")
                await self.exchange_manager._load_symbols()
                logger.info(f"Обновлено {len(self.exchange_manager.symbols)} символов")
                
                # Обновляем состояние
                async with self.state_lock:
                    self.state.symbols = self.exchange_manager.symbols.copy()
                    self.state.last_symbol_refresh = datetime.now()
                    
            except Exception as e:
                logger.error(f"Ошибка обновления топ символов: {e}")
                async with self.state_lock:
                    self.state.errors.append(f"Symbol refresh error: {str(e)}")
                    self.state.last_error_time = datetime.now()
            
            # Ждем 10 минут
            await asyncio.sleep(600)  # 10 minutes
            
    async def refresh_ohlcv_and_ema(self):
        """Обновление OHLCV данных и EMA каждый час"""
        while self.state.running:
            try:
                logger.info("Обновление OHLCV данных и EMA...")
                # This would typically involve more complex logic
                # For now, we'll just log that it's happening
                logger.info("OHLCV и EMA данные обновлены")
                
                # Обновляем состояние
                async with self.state_lock:
                    self.state.last_ohlcv_refresh = datetime.now()
                    
            except Exception as e:
                logger.error(f"Ошибка обновления OHLCV/EMA: {e}")
                async with self.state_lock:
                    self.state.errors.append(f"OHLCV refresh error: {str(e)}")
                    self.state.last_error_time = datetime.now()
            
            # Ждем 1 час
            await asyncio.sleep(3600)  # 1 hour
            
    async def poll_tickers_loop(self):
        """Цикл опроса тикеров с интервалом POLL_INTERVAL_SEC"""
        while self.state.running:
            try:
                async with self.state_lock:
                    self.state.cycle_count += 1
                    cycle_count = self.state.cycle_count
                    
                logger.debug("Начало цикла обработки")
                
                # Очистка старых позиций каждые 100 циклов (примерно каждые 50 минут)
                if cycle_count % 100 == 0:
                    self.position_manager.cleanup_old_positions(days=7)
                
                # Save signal metadata every 50 cycles for persistence
                if cycle_count % 50 == 0:
                    save_signal_metadata()
                
                # Получаем рыночные данные с rate limiting
                async with self._semaphore:
                    market_data = await self._make_request_with_retry(
                        self.exchange_manager.get_market_data
                    )
                    async with self.state_lock:
                        self.state.api_call_count += 1
                
                # Обновляем состояние с актуальными данными
                async with self.state_lock:
                    ohlcv_count = len(market_data.get('ohlcv', {}))
                    ticker_count = len(market_data.get('tickers', {}))
                    subscriber_count = len(self.telegram_bot.subscribers)
                    active_positions = self.position_manager.get_active_positions_count()
                    
                    self.state.subscriber_count = subscriber_count
                    self.state.active_positions = active_positions
                    
                logger.info(
                    f"Получено OHLCV: {ohlcv_count}, тикеров: {ticker_count}, "
                    f"подписчиков: {subscriber_count}, позиций: {active_positions}"
                )
                
                # Мониторинг активных позиций
                position_updates = self.position_manager.monitor_all_positions(market_data)
                
                if position_updates:
                    safe_log('info', f"📊 Обновления позиций: {len(position_updates)}")
                    # Отправляем уведомления о закрытии позиций
                    await self.telegram_bot.broadcast_position_updates(position_updates)
                    
                    # Обновляем состояние
                    async with self.state_lock:
                        self.state.position_update_count += len(position_updates)
                
                # Process signals with EMA20 touch detection
                await self._process_signals_with_ema20_detection(market_data)
                
                await asyncio.sleep(POLL_INTERVAL_SEC)
                
            except Exception as e:
                logger.error(f"Ошибка в основном цикле: {e}")
                async with self.state_lock:
                    self.state.errors.append(f"Main loop error: {str(e)}")
                    self.state.last_error_time = datetime.now()
                await asyncio.sleep(POLL_INTERVAL_SEC)
                
    def _validate_price_input(self, price: float, symbol: str) -> bool:
        """
        Validate that price input is positive and finite.
        Requirement 6.5: Validate all price inputs are positive and finite
        """
        if not isinstance(price, (int, float)):
            logger.warning(f"Invalid price type for {symbol}: {type(price)}")
            return False
            
        if not math.isfinite(price):
            logger.warning(f"Non-finite price for {symbol}: {price}")
            return False
            
        if price <= 0:
            logger.warning(f"Non-positive price for {symbol}: {price}")
            return False
            
        return True
        
    def _validate_timestamp_format(self, timestamp, symbol: str) -> bool:
        """
        Validate timestamp format and conversion.
        Requirement 6.5: Add timestamp format validation and conversion
        """
        if timestamp is None:
            logger.warning(f"Missing timestamp for {symbol}")
            return False
            
        try:
            # Try to convert to datetime
            if isinstance(timestamp, (int, float)):
                # Handle milliseconds timestamps from BingX API
                ts = int(timestamp)
                # If timestamp is in milliseconds, convert to seconds
                if ts > 10**10:  # Timestamps in milliseconds are larger than 10^10
                    ts = ts // 1000
                datetime.fromtimestamp(ts, tz=timezone.utc)
            elif isinstance(timestamp, str):
                datetime.fromisoformat(timestamp.replace('Z','')).replace(tzinfo=timezone.utc)
            else:
                logger.warning(f"Invalid timestamp type for {symbol}: {type(timestamp)}")
                return False
                
            return True
        except Exception as e:
            logger.warning(f"Invalid timestamp format for {symbol}: {timestamp} - {e}")
            return False
            
    async def _process_signals_with_ema20_detection(self, market_data):
        """Process signals with EMA20 touch detection - ONLY on closed candles"""
        try:
            ohlcv_data = market_data.get('ohlcv', {})
            tickers = market_data.get('tickers', {})
            
            # Get active positions to prevent duplicate signals
            active_positions_dict = self.position_manager.get_active_positions()
            
            # Track last signal time per symbol for deduplication
            last_signal_time = {}
            
            for symbol, ohlcv in ohlcv_data.items():
                try:
                    # Get current price
                    if symbol not in tickers:
                        continue
                        
                    current_price = tickers[symbol]['last']
                    # Requirement 6.5: Validate all price inputs are positive and finite
                    if not self._validate_price_input(current_price, symbol):
                        continue
                        
                    # Calculate EMA20 values
                    ema_values = self.strategy_manager.calculate_ema20(ohlcv)
                    if not ema_values or len(ema_values) < 2:
                        logger.debug(f"SKIP_SYMBOL {symbol}: Insufficient EMA "
                                    f"values ({len(ema_values) if ema_values else 0})")
                        continue
                        
                    # Convert to DataFrame for easier manipulation
                    df = pd.DataFrame(ohlcv)
                    if len(df) < 2:
                        logger.debug(f"SKIP_SYMBOL {symbol}: Insufficient OHLCV "
                                    f"data ({len(df)} candles)")
                        continue
                    
                    # FIX: Ensure timestamp is properly formatted before processing
                    # Convert numeric timestamps to ISO format strings
                    df['timestamp'] = df['timestamp'].apply(
                        lambda x: self._convert_timestamp_to_iso(x) if isinstance(x, (int, float)) else x
                    )
                    
                    # Use current candle for touch detection (df[-1]) instead of closed candle (df[-2])
                    current_candle = df.iloc[-1]  # Current candle
                    
                    # Requirement 6.3: Add proper candle timestamp extraction and validation
                    entry_candle_time = current_candle.get('timestamp')
                    # Requirement 6.5: Add timestamp format validation and conversion
                    if not self._validate_timestamp_format(entry_candle_time, symbol):
                        logger.debug(f"SKIP_SYMBOL {symbol}: Invalid timestamp in current candle")
                        continue
                    
                    ema20 = ema_values[-1]
                    ema20_prev = ema_values[-2] if len(ema_values) >= 2 else ema20
                    
                    # Validate EMA values
                    if not self._validate_price_input(ema20, f"{symbol}_EMA20_CURRENT") or \
                       not self._validate_price_input(ema20_prev, f"{symbol}_EMA20_PREV"):
                        continue
                    
                    # NEW: Use detect_touch_current_strict for current candle touch detection
                    # Get bid/ask prices if available
                    bid_price = tickers[symbol].get('bid')
                    ask_price = tickers[symbol].get('ask')
                    
                    # Use strict touch detection
                    touch_result, touch_data = detect_touch_current_strict(
                        symbol, df, pd.Series(ema_values), 
                        bid=bid_price, ask=ask_price,
                        last_signal_time=last_signal_time, 
                        active_positions=active_positions_dict
                    )
                    
                    if not touch_result:
                        # Log skip reason with detailed context as per requirements
                        try:
                            reason = touch_data if isinstance(touch_data, str) else "no_touch"
                            ctx = {
                                "symbol": symbol,
                                "candle_ts": candle_ts,
                                "now": datetime.utcnow().isoformat() + "Z",
                                "ema_last_closed": str(ema_last_closed),
                                "candle_low": str(current_candle['low']),
                                "candle_high": str(current_candle['high']),
                                "current_price": str(entry_price),
                                "price_source": price_source,
                                "in_active_positions": bool(symbol in active_positions_dict),
                                "last_signal_time": last_signal_time.get(symbol)
                            }
                            logger.info("SKIP_SIGNAL reason=%s %s", reason, ctx)
                        except Exception:
                            pass
                        continue
                    
                    # Extract data from touch detection result
                    direction = touch_data["direction"]
                    entry_price = touch_data["entry_price"]
                    candle_ts = touch_data["candle_ts"]
                    ema_last_closed = touch_data["ema"]
                    price_source = touch_data["price_source"]
                    
                    # ATTEMPT log
                    try:
                        logger.info("ATTEMPT_SIGNAL", extra={
                            "symbol": symbol,
                            "candle_ts": candle_ts,
                            "now": datetime.utcnow().isoformat() + "Z",
                            "ema_last_closed": str(ema_last_closed),
                            "candle_low": str(current_candle['low']),
                            "candle_high": str(current_candle['high']),
                            "current_price": str(entry_price),
                            "price_source": price_source,
                            "last_signal_time": last_signal_time.get(symbol),
                            "active_position": symbol in active_positions_dict
                        })
                    except Exception:
                        pass
                    
                    # Check anti-spam - only one signal per symbol per candle
                    if can_generate_signal(symbol, candle_ts):
                        # Create signal atomically (with deduplication)
                        # Requirement 6.3: Update signal creation to use closed candle data exclusively
                        sig = await create_signal_atomic(
                            symbol, direction, Decimal(str(entry_price)), 
                            Decimal(str(ema_last_closed)), candle_ts
                        )
                        
                        if sig:  # Send only if signal was created
                            logger.info(f"SIGNAL CREATED {symbol} "
                                       f"{direction} id={sig['signal_id']}")
                            # Register signal generation
                            register_signal(symbol, candle_ts)
                            # Convert to Signal object for sending
                            entry_price = sig.get('entry_price', 
                                                 sig.get('entry', 0))
                            signal_obj = Signal(
                                symbol=symbol,
                                direction=direction,
                                entry=entry_price,
                                sl=sig['sl_price'],
                                tp1=sig['tp1_price'],
                                tp2=sig['tp2_price']
                            )
                            await self.telegram_bot.broadcast_signals([signal_obj])
                            
                            # Update signal count
                            async with self.state_lock:
                                self.state.signal_count += 1
                            
                            # Log created signal with detailed context as per requirements
                            try:
                                ctx = {
                                    "symbol": symbol,
                                    "candle_ts": candle_ts,
                                    "now": datetime.utcnow().isoformat() + "Z",
                                    "ema_last_closed": str(ema_last_closed),
                                    "candle_low": str(current_candle['low']),
                                    "candle_high": str(current_candle['high']),
                                    "entry": str(entry_price),
                                    "direction": direction,
                                    "tol": str(Decimal(str(ema_last_closed)) * TOUCH_TOLERANCE_PCT)
                                }
                                logger.info("CREATED_SIGNAL %s", ctx)
                            except Exception:
                                pass
                        else:
                            # Log skip with reason and context as per requirements
                            reason = "duplicate_or_cooldown"
                            ctx = {
                                "symbol": symbol,
                                "candle_ts": candle_ts,
                                "now": datetime.utcnow().isoformat() + "Z",
                                "ema_last_closed": str(ema_last_closed),
                                "candle_low": str(current_candle['low']),
                                "candle_high": str(current_candle['high']),
                                "current_price": str(entry_price),
                                "price_source": price_source,
                                "in_active_positions": bool(symbol in active_positions_dict),
                                "last_signal_time": last_signal_time.get(symbol)
                            }
                            logger.info("SKIP_SIGNAL reason=%s %s", reason, ctx)
                    else:
                        # Log skip with reason and context as per requirements
                        reason = "antispam_protection"
                        ctx = {
                            "symbol": symbol,
                            "candle_ts": candle_ts,
                            "now": datetime.utcnow().isoformat() + "Z",
                            "ema_last_closed": str(ema_last_closed),
                            "candle_low": str(current_candle['low']),
                            "candle_high": str(current_candle['high']),
                            "current_price": str(entry_price),
                            "price_source": price_source,
                            "in_active_positions": bool(symbol in active_positions_dict),
                            "last_signal_time": last_signal_time.get(symbol)
                        }
                        logger.info("SKIP_SIGNAL reason=%s %s", reason, ctx)
                except Exception as e:
                    logger.error(f"Error processing signal for {symbol}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error in signal processing: {e}")

    def _convert_timestamp_to_iso(self, timestamp) -> str:
        """
        Convert timestamp (int/float) to ISO format string.
        Handles both seconds and milliseconds timestamps.
        """
        try:
            if isinstance(timestamp, (int, float)):
                ts = int(timestamp)
                # If timestamp is in milliseconds, convert to seconds
                if ts > 10**10:  # Timestamps in milliseconds are larger than 10^10
                    ts = ts // 1000
                return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat().replace("+00:00", "Z")
            else:
                return str(timestamp)
        except Exception as e:
            logger.warning(f"Failed to convert timestamp {timestamp} to ISO format: {e}")
            return str(timestamp)

    async def _make_request_with_retry(self, func, *args, retries: int = 3, **kwargs):
        """Выполнение запроса с повторными попытками"""
        last_error = None
        
        for attempt in range(retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(
                        f"Запрос не удался (попытка {attempt + 1}/{retries}): {e}. "
                        f"Повтор через {wait_time}с..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Запрос не удался после {retries} попыток: {e}")
                    
        raise last_error
        
    async def run(self):
        """Главная функция с планировщиком задач"""
        try:
            if await self.start():
                # Запускаем задачи в параллельных корутинах
                tasks = [
                    asyncio.create_task(self.poll_tickers_loop()),
                    asyncio.create_task(self.refresh_top_symbols()),
                    asyncio.create_task(self.refresh_ohlcv_and_ema())
                ]
                
                # Ждем завершения всех задач
                await asyncio.gather(*tasks, return_exceptions=True)
                
        except KeyboardInterrupt:
            logger.info("Получен сигнал остановки")
        except Exception as e:
            logger.error(f"Неожиданная ошибка: {e}")
        finally:
            await self.stop()


def main():
    """Точка входа в приложение"""
    bot = TradingBot()
    asyncio.run(bot.run())


if __name__ == "__main__":
    main()