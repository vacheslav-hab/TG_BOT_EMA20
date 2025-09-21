import asyncio
import logging
from main import TradingBot

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

async def main():
    print("Запуск бота...")
    bot = TradingBot()
    
    # Отключаем проверку блокировки для тестирования
    bot.instance_lock = None
    
    try:
        # Инициализируем менеджер биржи напрямую
        print("Инициализация биржи...")
        await bot.exchange_manager.initialize()
        
        # Передаем position_manager в telegram_bot
        bot.telegram_bot.set_position_manager(bot.position_manager)
        
        # Запускаем Telegram бота
        print("Запуск Telegram бота...")
        await bot.telegram_bot.start()
        
        # Обновляем состояние
        async with bot.state_lock:
            bot.state.running = True
            
        print("Бот успешно запущен!")
        
        # Запускаем основной цикл
        print("Запуск основного цикла...")
        await bot.run()
        
    except KeyboardInterrupt:
        print("Получен сигнал остановки...")
    except Exception as e:
        print(f"Ошибка при запуске бота: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("Остановка бота...")
        await bot.stop()

if __name__ == "__main__":
    asyncio.run(main())