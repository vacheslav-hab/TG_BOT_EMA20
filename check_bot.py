#!/usr/bin/env python3
"""
Check bot information and test connection
"""

import asyncio
from telegram import Bot
from config import logger, TELEGRAM_BOT_TOKEN

async def check_bot_info():
    """Check bot information and connection"""
    
    if not TELEGRAM_BOT_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN не найден!")
        return
        
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    
    try:
        # Получаем информацию о боте
        bot_info = await bot.get_me()
        
        logger.info("🤖 ИНФОРМАЦИЯ О БОТЕ:")
        logger.info(f"   ID: {bot_info.id}")
        logger.info(f"   Username: @{bot_info.username}")
        logger.info(f"   First Name: {bot_info.first_name}")
        logger.info(f"   Can Join Groups: {bot_info.can_join_groups}")
        logger.info(f"   Can Read All Group Messages: {bot_info.can_read_all_group_messages}")
        logger.info(f"   Supports Inline Queries: {bot_info.supports_inline_queries}")
        
        # Правильная ссылка на бота
        bot_link = f"https://t.me/{bot_info.username}"
        logger.info(f"🔗 ССЫЛКА НА БОТА: {bot_link}")
        
        # Проверяем обновления
        logger.info("📱 Проверяем последние обновления...")
        updates = await bot.get_updates()
        
        if updates:
            logger.info(f"📨 Найдено {len(updates)} обновлений:")
            for update in updates[-5:]:  # Последние 5
                if update.message:
                    user = update.message.from_user
                    text = update.message.text
                    date = update.message.date
                    logger.info(f"   {date}: @{user.username} ({user.id}): {text}")
        else:
            logger.info("📭 Новых обновлений нет")
            
    except Exception as e:
        logger.error(f"❌ Ошибка проверки бота: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_bot_info())