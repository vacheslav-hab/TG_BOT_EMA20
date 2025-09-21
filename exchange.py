"""Exchange Manager - Работа с BingX API"""

import asyncio
import hmac
import hashlib
import time
from typing import Dict, List

import aiohttp
from aiohttp import ClientSession, AsyncResolver, TCPConnector
from config import logger, BINGX_API_KEY, BINGX_SECRET_KEY, SYMBOL_COUNT, MIN_VOLUME_USDT


class BingXAPI:
    """BingX API клиент"""
    
    def __init__(self, api_key: str, secret_key: str):
        self.api_key = api_key
        self.secret_key = secret_key
        self.base_url = "https://open-api.bingx.com"
        self.session = None
        self._resolver = None  # Инициализируем resolver как None
        
    async def ensure_session(self):
        """Ensure that we have an open session"""
        if not self.session or self.session.closed:
            # Создаем resolver с Google DNS при необходимости
            self._resolver = AsyncResolver(nameservers=["8.8.8.8"])
            # Создаем connector с нашим resolver
            connector = TCPConnector(resolver=self._resolver)
            # Используем наш connector с Google DNS
            self.session = ClientSession(connector=connector)
            logger.info("Создана новая сессия с Google DNS")
        return self.session
        
    async def close_session(self):
        """Close the session if it exists and is open"""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.info("Сессия закрыта")
            
    def _generate_signature(self, params: str) -> str:
        """Генерация подписи для запроса"""
        return hmac.new(
            self.secret_key.encode('utf-8'),
            params.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
    async def _make_request(
        self, method: str, endpoint: str, 
        params: Dict = None, signed: bool = False
    ) -> Dict:
        """Выполнение HTTP запроса к API"""
        # Ensure we have an open session
        await self.ensure_session()
            
        url = f"{self.base_url}{endpoint}"
        logger.info(f"Попытка подключения к {url}")
        
        if params is None:
            params = {}
            
        if signed:
            timestamp = int(time.time() * 1000)
            params['timestamp'] = timestamp
            
            query_string = '&'.join([
                f"{k}={v}" for k, v in sorted(params.items())
            ])
            signature = self._generate_signature(query_string)
            params['signature'] = signature
            
            headers = {
                'X-BX-APIKEY': self.api_key,
                'Content-Type': 'application/json'
            }
        else:
            headers = {'Content-Type': 'application/json'}
            
        try:
            async with self.session.request(
                method, url, params=params, headers=headers,
                timeout=10  # Увеличиваем таймаут до 10 секунд
            ) as response:
                data = await response.json()
                logger.info(f"Получен ответ от {url}: {response.status}")
                
                if response.status != 200:
                    logger.error(f"API Error {response.status}: {data}")
                    raise Exception(f"API request failed: {data}")
                    
                return data
                
        except Exception as e:
            logger.error(f"Request error: {e}")
            raise
            
    async def _make_request_with_retry(
        self, method: str, endpoint: str, 
        params: Dict = None, signed: bool = False, retries: int = 5  # Увеличиваем количество попыток до 5
    ) -> Dict:
        """HTTP запрос с повторами"""
        last_error = None
        
        for attempt in range(retries):
            try:
                return await self._make_request(method, endpoint, params, signed)
            except Exception as e:
                last_error = e
                if attempt < retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(
                        f"API request failed (attempt {attempt + 1}/{retries}): {e}. "
                        f"Retrying in {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"API request failed after {retries} attempts: {e}")
                    
        raise last_error
        
    async def get_contracts(self) -> Dict:
        """Получение списка контрактов"""
        return await self._make_request_with_retry(
            'GET', '/openApi/swap/v2/quote/contracts'
        )
        
    async def get_klines(
        self, symbol: str, interval: str = '1h', limit: int = 100
    ) -> Dict:
        """Получение свечных данных"""
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        return await self._make_request_with_retry(
            'GET', '/openApi/swap/v3/quote/klines', params
        )
        
    async def get_ticker_price(self, symbol: str = None) -> Dict:
        """Получение текущей цены"""
        params = {}
        if symbol:
            params['symbol'] = symbol
        return await self._make_request_with_retry(
            'GET', '/openApi/swap/v2/quote/ticker', params
        )


class ExchangeManager:
    def __init__(self):
        self.api = BingXAPI(BINGX_API_KEY, BINGX_SECRET_KEY)
        self.symbols = []
        self.symbol_info = {}
        logger.info("Инициализация ExchangeManager")
        
    async def initialize(self):
        """Инициализация подключения"""
        logger.info("Инициализация связи с BingX...")
        
        if not BINGX_API_KEY or not BINGX_SECRET_KEY:
            raise ValueError("BingX API credentials not configured")
            
        # Initialize the API session
        await self.api.ensure_session()
        
        # Загружаем список символов
        await self._load_symbols()
        logger.info(
            f"Загружено {len(self.symbols)} символов для торговли"
        )
        
    async def _load_symbols(self):
        """Загрузка топ символов по объему"""
        try:
            # Ensure we have an open session
            await self.api.ensure_session()
            
            # Получаем все контракты
            contracts_response = await self.api.get_contracts()
            
            if 'data' not in contracts_response:
                raise Exception("Invalid contracts response")
                
            contracts = contracts_response['data']
            
            # Фильтруем USDT фьючерсы
            usdt_contracts = [
                contract for contract in contracts 
                if contract.get('symbol', '').endswith('-USDT') and 
                contract.get('status') == 1 and  # Active status
                contract.get('apiStateOpen') == 'true'
            ]
            
            # Получаем тикеры для сортировки по объему
            tickers_response = await self.api.get_ticker_price()
            
            if 'data' not in tickers_response:
                raise Exception("Invalid tickers response")
                
            tickers = {
                ticker['symbol']: ticker 
                for ticker in tickers_response['data']
            }
            
            # Рассчитываем 24h объем для каждого символа с fallback логикой
            contracts_with_volume = []
            for contract in usdt_contracts:
                symbol = contract['symbol']
                volume_24h = 0.0
                
                # Пытаемся получить объем из разных источников
                if symbol in tickers:
                    ticker = tickers[symbol]
                    # Приоритет: quoteVolume > volume24h > baseVolume * price
                    if 'quoteVolume' in ticker and float(ticker['quoteVolume']) > 0:
                        volume_24h = float(ticker['quoteVolume'])
                    elif 'volume24h' in ticker and float(ticker['volume24h']) > 0:
                        volume_24h = float(ticker['volume24h'])
                    elif 'volume' in ticker and float(ticker['volume']) > 0 and 'lastPrice' in ticker:
                        volume_24h = float(ticker['volume']) * float(ticker['lastPrice'])
                
                contract['volume_24h'] = volume_24h
                contracts_with_volume.append(contract)
            
            # Фильтруем по минимальному объему, но всегда включаем BTC/USDT, ETH/USDT, BNB/USDT
            high_priority_symbols = ['BTC-USDT', 'ETH-USDT', 'BNB-USDT']
            filtered_contracts = [
                contract for contract in contracts_with_volume
                if contract['volume_24h'] >= MIN_VOLUME_USDT or 
                   contract['symbol'] in high_priority_symbols
            ]
            
            # Исключаем illiquid символы
            illiquid_patterns = ['X-USDT', 'TOWNS-USDT']
            filtered_contracts = [
                contract for contract in filtered_contracts
                if not any(pattern in contract['symbol'] for pattern in illiquid_patterns)
            ]
            
            # Сортируем по объему и берем топ SYMBOL_COUNT символов
            sorted_contracts = sorted(
                filtered_contracts,
                key=lambda x: x['volume_24h'],
                reverse=True
            )
            
            # Берем топ SYMBOL_COUNT символов
            top_contracts = sorted_contracts[:SYMBOL_COUNT]
            
            self.symbols = [
                contract['symbol'] for contract in top_contracts
            ]
            self.symbol_info = {
                contract['symbol']: contract 
                for contract in top_contracts
            }
            
            # Логируем информацию о топ символах
            logger.info(f"Загружено {len(self.symbols)} топ символов по объему:")
            for i, contract in enumerate(top_contracts[:10]):  # Показываем топ-10
                logger.info(f"  {i+1}. {contract['symbol']}: ${contract['volume_24h']:,.0f}")
            
        except Exception as e:
            logger.error(f"Ошибка загрузки символов: {e}")
            raise
            
    async def get_market_data(self):
        """Получение рыночных данных"""
        logger.debug("Получение рыночных данных...")
        
        if not self.symbols:
            raise Exception("Symbols not loaded")
            
        market_data = {
            'ohlcv': {},
            'tickers': {}
        }
        
        try:
            # Ensure we have an open session
            await self.api.ensure_session()
            
            # Получаем OHLCV данные для всех символов
            ohlcv_tasks = [
                self._get_symbol_ohlcv(symbol) for symbol in self.symbols
            ]
            
            ohlcv_results = await asyncio.gather(
                *ohlcv_tasks, return_exceptions=True
            )
            
            for symbol, result in zip(self.symbols, ohlcv_results):
                if isinstance(result, Exception):
                    logger.warning(
                        f"Ошибка получения OHLCV для {symbol}: {result}"
                    )
                    continue
                market_data['ohlcv'][symbol] = result
                
            # Получаем текущие цены
            tickers_response = await self.api.get_ticker_price()
            if 'data' in tickers_response:
                for ticker in tickers_response['data']:
                    symbol = ticker['symbol']
                    if symbol in self.symbols:
                        market_data['tickers'][symbol] = {
                            'bid': float(ticker.get('bidPrice', 0)),
                            'ask': float(ticker.get('askPrice', 0)),
                            'last': float(ticker.get('lastPrice', 0)),
                            'volume': float(ticker.get('volume', 0))
                        }
                        
        except Exception as e:
            logger.error(f"Ошибка получения рыночных данных: {e}")
            raise
            
        return market_data
        
    async def _get_symbol_ohlcv(self, symbol: str) -> List[Dict]:
        """Получение OHLCV данных для символа"""
        try:
            # Ensure we have an open session
            await self.api.ensure_session()
            
            response = await self.api.get_klines(symbol, '1h', 100)
            
            if 'data' not in response:
                raise Exception(f"Invalid klines response for {symbol}")
                
            klines = response['data']
            
            # Преобразуем в удобный формат
            ohlcv_data = []
            for kline in klines:
                ohlcv_data.append({
                    'timestamp': int(kline['time']),
                    'open': float(kline['open']),
                    'high': float(kline['high']),
                    'low': float(kline['low']),
                    'close': float(kline['close']),
                    'volume': float(kline['volume'])
                })
                
            return ohlcv_data
            
        except Exception as e:
            logger.error(f"Ошибка получения OHLCV для {symbol}: {e}")
            raise
            
    async def cleanup(self):
        """Очистка ресурсов"""
        await self.api.close_session()