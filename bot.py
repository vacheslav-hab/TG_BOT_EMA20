"""Telegram Bot Manager"""

import os
from typing import List
from datetime import datetime
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, ContextTypes
)
from config import logger, TELEGRAM_BOT_TOKEN, safe_log, EMA_PERIOD
from strategy import Signal
from position_manager import PositionUpdate
from subscribers_manager import SubscribersManager


class TelegramBot:
    def __init__(self):
        self.application = None
        self.subscribers = set()  # Временно оставляем для совместимости
        self.subscribers_manager = SubscribersManager()
        self.running = False
        self.position_manager = None  # Будет инициализирован в main.py
        logger.info("Инициализация TelegramBot")
        
        # Загружаем подписчиков из JSON при запуске
        self._load_subscribers_from_json()
    
    def _load_subscribers_from_json(self):
        """Загрузка подписчиков из JSON при запуске"""
        try:
            subscriber_ids = self.subscribers_manager.get_subscriber_ids(active_only=True)
            self.subscribers = subscriber_ids
            logger.info(f"Загружено {len(self.subscribers)} подписчиков из JSON")
        except Exception as e:
            logger.error(f"Ошибка загрузки подписчиков: {e}")
            self.subscribers = set()
    
    def set_position_manager(self, position_manager):
        """Установка менеджера позиций"""
        self.position_manager = position_manager
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /start"""
        user_id = update.effective_user.id
        username = update.effective_user.username or "Неизвестный"
        first_name = update.effective_user.first_name
        last_name = update.effective_user.last_name
        language_code = update.effective_user.language_code
        
        logger.info(f"📨 Получена команда /start от {username} (ID: {user_id})")
        
        # Добавляем подписчика через SubscribersManager
        is_new_subscriber = self.subscribers_manager.add_subscriber(
            user_id=user_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language_code=language_code
        )
        
        # Обновляем локальный сет для совместимости
        self.subscribers.add(user_id)
        
        if is_new_subscriber:
            safe_log('info', f"✅ НОВЫЙ подписчик: {username} (ID: {user_id})")
        else:
            safe_log('info', f"🔄 Повторная подписка: {username} (ID: {user_id})")
            
        logger.info(f"👥 Всего подписчиков: {len(self.subscribers)}")
        
        welcome_message = (
            "🤖 Привет! Я - EMA20 Trading Signals Bot\n\n"
            "📊 Я анализирую 70 топ фьючерсов BingX каждые 30 секунд\n"
            "🎯 Отправляю LONG/SHORT сигналы при касании EMA20\n"
            "⚠️ ВНИМАНИЕ: Только анализ, НЕ финансовые советы!\n\n"
            "📝 Команды:\n"
            "/start - Подписаться на сигналы\n"
            "/status - Статус бота\n"
            "/stats - Статистика торговли\n"
            "/export - Экспорт данных в CSV\n"
            "/report - Дневной отчет\n"
            "/position <id> - Детали позиции\n"
            "/subscribers - Статистика подписчиков\n"
            "/export_subscribers - Экспорт подписчиков\n"
            "/help - Помощь"
        )
        
        await update.message.reply_text(welcome_message)
        
    def _update_user_activity(self, user_id: int):
        """Обновление активности пользователя"""
        try:
            self.subscribers_manager.update_subscriber_activity(user_id)
        except Exception as e:
            logger.error(f"Ошибка обновления активности пользователя {user_id}: {e}")
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /status"""
        self._update_user_activity(update.effective_user.id)
        
        # Получаем статистику подписчиков
        subscribers_stats = self.subscribers_manager.get_statistics()
        
        status_message = (
            "🤖 Статус бота:\n\n"
            f"🔄 Состояние: {'✅ Активен' if self.running else '❌ Остановлен'}\n"
            f"👥 Подписчиков: {subscribers_stats.get('active_subscribers', len(self.subscribers))}\n"
            f"📋 Всего команд: {subscribers_stats.get('total_commands_executed', 0)}\n"
            f"📊 Мониторинг: 70 символов BingX\n"
            f"⏰ Интервал: 30 секунд\n"
            f"🎯 Стратегия: EMA{EMA_PERIOD} Touch Detection"
        )
        
        await update.message.reply_text(status_message)
        
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /help"""
        self._update_user_activity(update.effective_user.id)
        
        help_message = (
            "🔍 Помощь по EMA20 Trading Bot\n\n"
            "📊 Как работает:\n"
            f"• Анализирую 70 топ фьючерсов на BingX\n"
            f"• Рассчитываю EMA{EMA_PERIOD} на 1h свечах\n"
            "• Обнаруживаю касания EMA20\n"
            "• Отправляю сигналы с SL/TP уровнями\n\n"
            "🚨 Условия сигналов:\n"
            "• LONG: цена > EMA20, EMA20 растет, касание снизу\n"
            "• SHORT: цена < EMA20, EMA20 падает, касание сверху\n\n"
            "📈 Уровни:\n"
            "• LONG: SL -1%, TP1 +1.5%, TP2 +3%\n"
            "• SHORT: SL +1%, TP1 -1.5%, TP2 -3%\n\n"
            "⏰ Cooldown: 60 мин между сигналами на один символ\n\n"
            "⚠️ ОТКАЗ ОТ ОТВЕТСТВЕННОСТИ:\n"
            "Только анализ, не финансовые советы!"
        )
        
        await update.message.reply_text(help_message)
        
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /stats"""
        self._update_user_activity(update.effective_user.id)
        
        if self.position_manager:
            stats_message = self.position_manager.get_statistics_summary()
        else:
            stats_message = (
                "📊 Статистика торговых сигналов:\n\n"
                "🎯 Всего сигналов: --\n"
                "✅ TP1 достигнуто: --\n"
                "🏆 TP2 достигнуто: --\n"
                "❌ SL сработало: --\n"
                "📈 Винрейт: --%\n"
                "💰 Общий PnL: --%\n"
                "📍 Активных позиций: --\n\n"
                "⚠️ Статистика для анализа, не финансовые советы!"
            )
        
        await update.message.reply_text(stats_message)
    
    async def export_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /export - экспорт данных в CSV"""
        self._update_user_activity(update.effective_user.id)
        
        try:
            if not self.position_manager:
                await update.message.reply_text("⚠️ Менеджер позиций недоступен")
                return
                
            # Экспортируем данные в CSV
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"trading_signals_{timestamp}.csv"
            
            self.position_manager.json_manager.export_to_csv(filename)
            
            if os.path.exists(filename):
                # Отправляем файл пользователю
                with open(filename, 'rb') as f:
                    await update.message.reply_document(
                        document=f,
                        filename=filename,
                        caption=f"📊 Экспорт торговых данных\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                
                # Удаляем временный файл
                os.remove(filename)
                logger.info(f"CSV файл отправлен пользователю {update.effective_user.id}")
            else:
                await update.message.reply_text("❌ Ошибка создания файла экспорта")
                
        except Exception as e:
            logger.error(f"Ошибка экспорта данных: {e}")
            await update.message.reply_text("❌ Ошибка при экспорте данных")
    
    async def report_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /report - дневной отчет"""
        self._update_user_activity(update.effective_user.id)
        
        try:
            if not self.position_manager:
                await update.message.reply_text("⚠️ Менеджер позиций недоступен")
                return
                
            # Получаем дневной отчет
            report = self.position_manager.get_daily_report()
            
            message = (
                f"📅 Дневной отчет за {report['date']}\n\n"
                f"🎯 Сигналов за день: {report['total_signals']}\n"
                f"💰 Дневной PnL: {report['total_pnl']:+.2f}%\n\n"
            )
            
            if report['positions']:
                message += "📊 Позиции за день:\n"
                for pos in report['positions'][-5:]:  # Показываем последние 5
                    status_emoji = {
                        'OPEN': '🟡',
                        'TP1_HIT': '🟢', 
                        'TP2_HIT': '🟢',
                        'SL_HIT': '🔴',
                        'CLOSED': '⚪'
                    }.get(pos['status'], '⚪')
                    
                    message += f"{status_emoji} {pos['direction']} {pos['symbol']} - {pos['status']}\n"
                    
            message += "\n⚠️ Только для анализа, не финансовые советы!"
            
            await update.message.reply_text(message)
            
        except Exception as e:
            logger.error(f"Ошибка создания отчета: {e}")
            await update.message.reply_text("❌ Ошибка при создании отчета")
    
    async def position_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /position [signal_id] - детали позиции"""
        self._update_user_activity(update.effective_user.id)
        
        try:
            if not self.position_manager:
                await update.message.reply_text("⚠️ Менеджер позиций недоступен")
                return
                
            args = context.args
            if not args:
                await update.message.reply_text(
                    "❓ Использование: /position <signal_id>\n"
                    "Пример: /position BTC-USDT_LONG_20250914_123456"
                )
                return
                
            signal_id = ' '.join(args)  # На случай пробелов в ID
            position_details = self.position_manager.get_position_details(signal_id)
            
            if not position_details:
                await update.message.reply_text(f"❌ Позиция {signal_id} не найдена")
                return
                
            # Форматируем детали позиции
            status_emoji = {
                'OPEN': '🟡 Активна',
                'TP1_HIT': '🟢 TP1 достигнут', 
                'TP2_HIT': '🟢 TP2 достигнут',
                'SL_HIT': '🔴 SL сработал',
                'CLOSED': '⚪ Закрыта'
            }.get(position_details['status'], '⚪ Неизвестно')
            
            message = (
                f"📊 Детали позиции\n\n"
                f"🆔 ID: {signal_id}\n"
                f"📈 {position_details['direction']} {position_details['symbol']}\n"
                f"📍 Вход: ${position_details['entry_price']:,.6f}\n"
                f"💲 Текущая цена: ${position_details.get('current_price', 0):,.6f}\n"
                f"📊 Статус: {status_emoji}\n"
                f"🚀 Макс. прибыль: {position_details.get('max_profit', 0):+.2f}%\n"
                f"📉 Макс. просадка: {position_details.get('max_drawdown', 0):+.2f}%\n"
                f"⏰ Создана: {position_details['created_at'].strftime('%Y-%m-%d %H:%M:%S')}\n"
            )
            
            # Добавляем историю PnL
            if position_details.get('pnl_history'):
                message += "\n📈 История PnL:\n"
                for record in position_details['pnl_history'][-3:]:  # Последние 3 записи
                    timestamp = datetime.fromisoformat(record['timestamp'])
                    message += (
                        f"• {record['level_type']}: {record['pnl_percentage']:+.2f}% "
                        f"({timestamp.strftime('%H:%M:%S')})\n"
                    )
                    
            await update.message.reply_text(message)
            
        except Exception as e:
            logger.error(f"Ошибка получения деталей позиции: {e}")
            await update.message.reply_text("❌ Ошибка при получении деталей позиции")
    
    async def subscribers_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /subscribers - статистика подписчиков"""
        self._update_user_activity(update.effective_user.id)
        
        try:
            # Получаем статистику подписчиков
            stats = self.subscribers_manager.get_statistics()
            daily_report = self.subscribers_manager.get_daily_report()
            
            message = (
                f"👥 Статистика подписчиков\n\n"
                f"📊 Всего подписчиков: {stats.get('total_subscribers', 0)}\n"
                f"✅ Активных: {stats.get('active_subscribers', 0)}\n"
                f"📋 Выполнено команд: {stats.get('total_commands_executed', 0)}\n\n"
                f"📅 За сегодня ({daily_report['date']}): \n"
                f"🆕 Новых подписчиков: {daily_report['new_subscribers']}\n"
                f"👤 Активных пользователей: {daily_report['active_users_count']}\n"
                f"⌨️ Команд выполнено: {daily_report['total_commands']}\n\n"
            )
            
            # Добавляем дату первого подписчика, если есть
            if stats.get('first_subscriber_date'):
                first_date = datetime.fromisoformat(stats['first_subscriber_date'])
                message += f"🎯 Первый подписчик: {first_date.strftime('%Y-%m-%d %H:%M')}\n"
                
            # Добавляем последнюю активность, если есть
            if stats.get('last_activity_date'):
                last_activity = datetime.fromisoformat(stats['last_activity_date'])
                message += f"⏰ Последняя активность: {last_activity.strftime('%Y-%m-%d %H:%M')}\n"
            
            await update.message.reply_text(message)
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики подписчиков: {e}")
            await update.message.reply_text("❌ Ошибка при получении статистики подписчиков")
    
    async def export_subscribers_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /export_subscribers - экспорт подписчиков в CSV"""
        self._update_user_activity(update.effective_user.id)
        
        try:
            # Экспортируем подписчиков в CSV
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"subscribers_{timestamp}.csv"
            
            self.subscribers_manager.export_to_csv(filename)
            
            if os.path.exists(filename):
                # Отправляем файл пользователю
                with open(filename, 'rb') as f:
                    await update.message.reply_document(
                        document=f,
                        filename=filename,
                        caption=f"👥 Экспорт данных подписчиков\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                
                # Удаляем временный файл
                os.remove(filename)
                logger.info(f"CSV файл подписчиков отправлен пользователю {update.effective_user.id}")
            else:
                await update.message.reply_text("❌ Ошибка создания файла экспорта подписчиков")
                
        except Exception as e:
            logger.error(f"Ошибка экспорта подписчиков: {e}")
            await update.message.reply_text("❌ Ошибка при экспорте подписчиков")
        
    async def start(self):
        """Запуск Telegram бота"""
        logger.info("Запуск Telegram бота...")
        
        if not TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN не настроен")
            
        # Создаем приложение
        self.application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        # Добавляем обработчики команд
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        self.application.add_handler(CommandHandler("export", self.export_command))
        self.application.add_handler(CommandHandler("report", self.report_command))
        self.application.add_handler(CommandHandler("position", self.position_command))
        self.application.add_handler(CommandHandler("subscribers", self.subscribers_command))
        self.application.add_handler(CommandHandler("export_subscribers", self.export_subscribers_command))
        
        try:
            # Инициализируем и запускаем бота
            await self.application.initialize()
            await self.application.start()
            
            # Принудительно удаляем webhook (если был установлен)
            await self.application.bot.delete_webhook(drop_pending_updates=True)
            logger.info("Webhook удален, переходим к polling")
            
            # Запускаем polling с дополнительными параметрами
            await self.application.updater.start_polling(
                drop_pending_updates=True,
                allowed_updates=None
            )
            
            self.running = True
            safe_log('info', "✅ Telegram бот успешно запущен и слушает обновления")
            
        except Exception as e:
            logger.error(f"Ошибка при запуске Telegram бота: {e}")
            # Попытка очистить конфликтующие подключения
            try:
                await self.application.bot.delete_webhook(drop_pending_updates=True)
                logger.info("Попытка очистки webhook выполнена")
            except Exception as cleanup_error:
                logger.error(f"Ошибка очистки: {cleanup_error}")
            raise
        
    async def stop(self):
        """Остановка Telegram бота"""
        logger.info("Остановка Telegram бота...")
        self.running = False
        
        if self.application:
            # Останавливаем polling
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
            
    def format_signal_message(self, signal: Signal) -> str:
        """Форматирование сообщения о сигнале"""
        emoji = "🚀" if signal.direction == "LONG" else "🔴"
        
        message = (
            f"{emoji} {signal.direction} {signal.symbol}\n\n"
            f"📍 Entry: ${signal.entry:,.6f}\n"
            f"🛑 Stop Loss: ${signal.sl:,.6f}\n"
            f"🎯 Take Profit 1: ${signal.tp1:,.6f}\n"
            f"🎯 Take Profit 2: ${signal.tp2:,.6f}\n\n"
            f"📈 Risk/Reward: 1:{(abs(signal.tp1 - signal.entry) / abs(signal.entry - signal.sl)):.1f}\n"
            f"⏰ {signal.created_at.strftime('%H:%M:%S')}\n\n"
            f"⚠️ Не финансовые советы!"
        )
        
        return message
        
    async def broadcast_signals(self, signals: List[Signal]):
        """Рассылка сигналов с улучшенной обработкой ошибок"""
        if not signals:
            logger.debug("Нет сигналов для рассылки")
            return
            
        # Обновляем список подписчиков из JSON
        self._load_subscribers_from_json()
        
        if not self.subscribers:
            safe_log('warning', f"⚠️ Нет подписчиков! Сейчас подписчиков: {len(self.subscribers)}")
            logger.info(f"🔗 Правильная ссылка на бота: https://t.me/ema20_scalping_bot")
            logger.info(f"📋 Для получения сигналов отправьте /start боту")
            return
            
        logger.info(f"📢 НАЧАЛО РАССЫЛКИ: {len(signals)} сигналов → {len(self.subscribers)} подписчикам")
        
        for signal in signals:
            message = self.format_signal_message(signal)
            
            success_count = 0
            error_count = 0
            
            # Отправляем всем подписчикам
            for user_id in list(self.subscribers):  # Копия списка
                try:
                    if self.application and self.application.bot:
                        await self.application.bot.send_message(
                            chat_id=user_id, 
                            text=message
                        )
                        success_count += 1
                    else:
                        logger.warning(f"Бот не инициализирован для отправки сообщения пользователю {user_id}")
                        error_count += 1
                        
                except Exception as e:
                    error_count += 1
                    error_msg = str(e).lower()
                    safe_log('warning', f"⚠️ Ошибка отправки пользователю {user_id}: {e}")
                    # Удаляем недоступных пользователей
                    if "bot was blocked" in error_msg or "chat not found" in error_msg or "user is deactivated" in error_msg:
                        self.subscribers.discard(user_id)
                        try:
                            await self.subscribers_manager.remove_subscriber_async(user_id)
                            logger.info(f"🚫 Пользователь {user_id} заблокировал бота или недоступен")
                        except Exception as remove_error:
                            logger.error(f"Ошибка удаления подписчика {user_id}: {remove_error}")
                        
            logger.info(
                f"✅ Сигнал {signal.direction} {signal.symbol} разослан: "
                f"успех {success_count}, ошибок {error_count}"
            )
            
    def format_position_update_message(self, update: PositionUpdate) -> str:
        """Форматирование сообщения об обновлении позиции"""
        if update.triggered_level == "TP1":
            emoji = "🎯"
            level_text = "Take Profit 1"
        elif update.triggered_level == "TP2":
            emoji = "🏆" 
            level_text = "Take Profit 2"
        elif update.triggered_level == "SL":
            emoji = "🛑"
            level_text = "Stop Loss"
        else:
            emoji = "📊"
            level_text = "Позиция обновлена"
            
        pnl_emoji = "💚" if update.pnl_percentage > 0 else "❌"
        
        message = (
            f"{emoji} {level_text} достигнут!\n\n"
            f"📊 {update.direction} {update.symbol}\n"
            f"📍 Цена: ${update.current_price:,.6f}\n"
            f"{pnl_emoji} PnL: {update.pnl_percentage:+.2f}%\n"
            f"⏰ {update.timestamp.strftime('%H:%M:%S')}\n\n"
            f"⚠️ Позиция {'закрыта' if update.new_status in ['TP2_HIT', 'SL_HIT'] else 'частично закрыта'}"
        )
        
        return message
        
    async def broadcast_position_updates(self, updates: List[PositionUpdate]):
        """Рассылка обновлений позиций с улучшенной обработкой ошибок"""
        if not updates:
            return
            
        # Обновляем список подписчиков из JSON
        self._load_subscribers_from_json()
        
        if not self.subscribers:
            safe_log('warning', "⚠️ Нет подписчиков для отправки обновлений позиций")
            return
            
        logger.info(f"📨 РАССЫЛКА ОБНОВЛЕНИЙ: {len(updates)} обновлений → {len(self.subscribers)} подписчикам")
        
        for update in updates:
            message = self.format_position_update_message(update)
            
            success_count = 0
            error_count = 0
            
            # Отправляем всем подписчикам
            for user_id in list(self.subscribers):
                try:
                    if self.application and self.application.bot:
                        await self.application.bot.send_message(
                            chat_id=user_id, 
                            text=message
                        )
                        success_count += 1
                    else:
                        logger.warning(f"Бот не инициализирован для отправки сообщения пользователю {user_id}")
                        error_count += 1
                        
                except Exception as e:
                    error_count += 1
                    error_msg = str(e).lower()
                    safe_log('warning', f"⚠️ Ошибка отправки обновления пользователю {user_id}: {e}")
                    # Удаляем недоступных пользователей
                    if "bot was blocked" in error_msg or "chat not found" in error_msg or "user is deactivated" in error_msg:
                        self.subscribers.discard(user_id)
                        try:
                            await self.subscribers_manager.remove_subscriber_async(user_id)
                            logger.info(f"🚫 Пользователь {user_id} заблокировал бота или недоступен")
                        except Exception as remove_error:
                            logger.error(f"Ошибка удаления подписчика {user_id}: {remove_error}")
                    
            logger.info(
                f"✅ Обновление {update.symbol} {update.triggered_level} разослано: "
                f"успех {success_count}, ошибок {error_count}"
            )