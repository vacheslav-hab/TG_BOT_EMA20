#!/usr/bin/env python3
"""
Тест Telegram бота - проверка подключения и команд
"""

import asyncio
from bot import TelegramBot
from config import logger

async def test_telegram_bot():
    """Тест Telegram бота"""
    
    bot = TelegramBot()
    
    try:
        logger.info("🔍 Тестирование Telegram бота...")
        
        # Запускаем бота
        await bot.start()
        
        logger.info(f"📊 Текущее количество подписчиков: {len(bot.subscribers)}")
        logger.info(f"🤖 Статус бота: {'Активен' if bot.running else 'Остановлен'}")
        logger.info("📱 Бот готов принимать команды!")
        logger.info(f"🔗 Ссылка на бота: https://t.me/bot{bot.application.bot.token.split(':')[0]}")
        
        # Симулируем ожидание
        logger.info("⏳ Ожидание команд... (Нажмите Ctrl+C для остановки)")
        
        # Ждем команды
        while True:
            await asyncio.sleep(5)
            if bot.subscribers:
                logger.info(f"👥 Активных подписчиков: {len(bot.subscribers)}")
                
    except KeyboardInterrupt:
        logger.info("🛑 Остановка по команде пользователя")
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
    finally:
        await bot.stop()
        logger.info("✅ Бот остановлен")

if __name__ == "__main__":
    asyncio.run(test_telegram_bot())