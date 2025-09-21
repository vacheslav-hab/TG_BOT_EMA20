import asyncio
import logging
from main import TradingBot

# Настройка логирования для отладки
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

async def main():
    print("Запуск отладки бота...")
    bot = TradingBot()
    
    try:
        print("Попытка запустить бота...")
        success = await bot.start()
        print(f"Результат запуска: {success}")
        
        if success:
            print("Бот успешно запущен, запуск основного цикла...")
            await bot.run()
        else:
            print("Не удалось запустить бота")
            
    except Exception as e:
        print(f"Ошибка при запуске бота: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("Остановка бота...")
        await bot.stop()

if __name__ == "__main__":
    asyncio.run(main())