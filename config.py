import os
import logging
from dotenv import load_dotenv
from decimal import Decimal

# Загружаем переменные окружения
load_dotenv()

# EMA Configuration
EMA_PERIOD = 20  # Единый источник для периода EMA

# Настройка логирования
import sys

# Создаем обработчики с правильной кодировкой
file_handler = logging.FileHandler('bot.log', encoding='utf-8')
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setStream(sys.stdout)

# Форматтер без emoji для консоли Windows
file_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
console_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')

file_handler.setFormatter(file_formatter)
console_handler.setFormatter(console_formatter)

logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, console_handler]
)

logger = logging.getLogger(__name__)

# Функция для безопасного логирования без emoji на Windows
def safe_log(level, message, *args, **kwargs):
    """Убираем emoji символы для совместимости с Windows CP1251"""
    # Словарь замены emoji на текстовые символы
    emoji_replacements = {
        '✅': '[OK]',
        '❌': '[ERROR]', 
        '⚠️': '[WARNING]',
        '📊': '[STATS]',
        '📂': '[FILE]',
        '🔄': '[REPEAT]',
        '📈': '[UP]',
        '📉': '[DOWN]',
        '🎯': '[TARGET]',
        '💰': '[PROFIT]',
        '🚀': '[LAUNCH]',
        '📍': '[POINT]'
    }
    
    # Заменяем emoji на текстовые символы
    clean_message = message
    for emoji, replacement in emoji_replacements.items():
        clean_message = clean_message.replace(emoji, replacement)
    
    # Логируем очищенное сообщение
    getattr(logger, level)(clean_message, *args, **kwargs)

# API Configuration
BINGX_API_KEY = os.getenv('BINGX_API_KEY')
BINGX_SECRET_KEY = os.getenv('BINGX_SECRET_KEY')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Trading Parameters
SYMBOL_COUNT = int(os.getenv('SYMBOL_COUNT', 70))
TIMEFRAME = os.getenv('TIMEFRAME', '1h')
POLL_INTERVAL_SEC = int(os.getenv('POLL_INTERVAL_SEC', 30))
# ТОЛЕРАНТНОСТЬ КАСАНИЯ EMA20 (настраиваемая)
# Рекомендация: 0.001 = 0.1% (мало) — 0.005 = 0.5% (шире)
TOUCH_TOLERANCE_PCT = Decimal(os.getenv('TOUCH_TOLERANCE_PCT', '0.001'))  # По умолчанию 0.001 (0.1%)
MIN_SIGNAL_COOLDOWN_MIN = int(os.getenv('MIN_SIGNAL_COOLDOWN_MIN', 60))
MIN_VOLUME_USDT = float(os.getenv('MIN_VOLUME_USDT', 1000000))  # Default 1M USDT

# Data Storage
JSON_FILE = os.getenv('JSON_FILE', 'signals.json')

def validate_config():
    """Проверяем обязательные параметры"""
    required_vars = ['BINGX_API_KEY', 'BINGX_SECRET_KEY', 'TELEGRAM_BOT_TOKEN']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Отсутствуют обязательные переменные: {missing_vars}")
        return False
    
    logger.info("Конфигурация прошла валидацию")
    return True