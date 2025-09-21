"""Integration tests for exchange operations"""

import asyncio
import unittest
from unittest.mock import AsyncMock, Mock, patch
from exchange import ExchangeManager


class TestExchangeIntegration(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.exchange_manager = ExchangeManager()
        
    async def asyncSetUp(self):
        """Async setup for async tests"""
        pass
        
    async def asyncTearDown(self):
        """Async teardown for async tests"""
        pass
        
    @patch('exchange.BingXAPI')
    async def test_initialize_exchange(self, mock_api_class):
        """Test exchange initialization"""
        # Mock API
        mock_api = AsyncMock()
        mock_api_class.return_value = mock_api
        
        # Test initialization
        await self.exchange_manager.initialize()
        
        # Verify API was created
        mock_api_class.assert_called_once()
        self.assertIsNotNone(self.exchange_manager.api)
        
    @patch('exchange.BingXAPI')
    async def test_load_symbols_integration(self, mock_api_class):
        """Test loading symbols integration with real API responses"""
        # Mock API
        mock_api = AsyncMock()
        mock_api_class.return_value = mock_api
        
        # Mock contracts response with perpetual futures
        mock_contracts_response = {
            'data': [
                {
                    'symbol': 'BTC-USDT',
                    'status': 1,
                    'apiStateOpen': 'true',
                    'contractType': 'PERPETUAL'
                },
                {
                    'symbol': 'ETH-USDT',
                    'status': 1,
                    'apiStateOpen': 'true',
                    'contractType': 'PERPETUAL'
                },
                {
                    'symbol': 'BNB-USDT',
                    'status': 1,
                    'apiStateOpen': 'true',
                    'contractType': 'PERPETUAL'
                },
                {
                    'symbol': 'SOL-USDT',
                    'status': 1,
                    'apiStateOpen': 'true',
                    'contractType': 'PERPETUAL'
                },
                {
                    'symbol': 'X-USDT',
                    'status': 1,
                    'apiStateOpen': 'true',
                    'contractType': 'PERPETUAL'
                }
            ]
        }
        
        # Mock tickers response with volume data
        mock_tickers_response = {
            'data': [
                {
                    'symbol': 'BTC-USDT',
                    'quoteVolume': '1000000000',  # 1B USDT
                    'lastPrice': '50000'
                },
                {
                    'symbol': 'ETH-USDT',
                    'quoteVolume': '500000000',   # 500M USDT
                    'lastPrice': '3000'
                },
                {
                    'symbol': 'BNB-USDT',
                    'quoteVolume': '200000000',   # 200M USDT
                    'lastPrice': '300'
                },
                {
                    'symbol': 'SOL-USDT',
                    'quoteVolume': '50000000',    # 50M USDT
                    'lastPrice': '100'
                },
                {
                    'symbol': 'X-USDT',
                    'quoteVolume': '1000000',     # 1M USDT (below threshold)
                    'lastPrice': '0.1'
                }
            ]
        }
        
        # Set up mock responses
        mock_api.get_contracts.return_value = mock_contracts_response
        mock_api.get_ticker_price.return_value = mock_tickers_response
        
        # Initialize and load symbols
        await self.exchange_manager.initialize()
        with patch.object(self.exchange_manager, 'api', mock_api):
            await self.exchange_manager._load_symbols()
        
        # Verify results
        self.assertGreater(len(self.exchange_manager.symbols), 0)
        self.assertIn('BTC-USDT', self.exchange_manager.symbols)
        self.assertIn('ETH-USDT', self.exchange_manager.symbols)
        self.assertIn('BNB-USDT', self.exchange_manager.symbols)
        # X-USDT should be excluded due to low volume
        self.assertNotIn('X-USDT', self.exchange_manager.symbols)
        
    @patch('exchange.BingXAPI')
    async def test_get_market_data_integration(self, mock_api_class):
        """Test getting market data integration"""
        # Mock API
        mock_api = AsyncMock()
        mock_api_class.return_value = mock_api
        
        # Mock OHLCV response
        mock_ohlcv_response = {
            'data': [
                {
                    'time': 1000000,
                    'open': '49900',
                    'high': '50100',
                    'low': '49800',
                    'close': '50000',
                    'volume': '1000'
                }
                for _ in range(25)  # 25 candles
            ]
        }
        
        # Mock ticker response
        mock_ticker_response = {
            'data': [
                {
                    'symbol': 'BTC-USDT',
                    'last': '50000',
                    'bid': '49999',
                    'ask': '50001',
                    'quoteVolume': '100000000'
                }
            ]
        }
        
        # Set up mock responses
        mock_api.get_kline.return_value = mock_ohlcv_response
        mock_api.get_ticker_price.return_value = mock_ticker_response
        
        # Initialize exchange manager
        await self.exchange_manager.initialize()
        with patch.object(self.exchange_manager, 'api', mock_api):
            # Load symbols first
            await self.exchange_manager._load_symbols()
            self.exchange_manager.symbols = ['BTC-USDT']
            
            # Get market data
            market_data = await self.exchange_manager.get_market_data()
        
        # Verify market data structure
        self.assertIn('ohlcv', market_data)
        self.assertIn('tickers', market_data)
        self.assertIn('BTC-USDT', market_data['ohlcv'])
        self.assertIn('BTC-USDT', market_data['tickers'])
        self.assertEqual(len(market_data['ohlcv']['BTC-USDT']), 25)
        
    @patch('exchange.BingXAPI')
    async def test_volume_fallback_logic(self, mock_api_class):
        """Test volume fallback logic with different volume fields"""
        # Mock API
        mock_api = AsyncMock()
        mock_api_class.return_value = mock_api
        
        # Mock contracts response
        mock_contracts_response = {
            'data': [
                {
                    'symbol': 'BTC-USDT',
                    'status': 1,
                    'apiStateOpen': 'true',
                    'contractType': 'PERPETUAL'
                }
            ]
        }
        
        # Mock tickers response with different volume fields
        mock_tickers_response = {
            'data': [
                {
                    'symbol': 'BTC-USDT',
                    'volume24h': '1000000000',  # Alternative volume field
                    'lastPrice': '50000'
                }
            ]
        }
        
        # Set up mock responses
        mock_api.get_contracts.return_value = mock_contracts_response
        mock_api.get_ticker_price.return_value = mock_tickers_response
        
        # Initialize and load symbols
        await self.exchange_manager.initialize()
        with patch.object(self.exchange_manager, 'api', mock_api):
            await self.exchange_manager._load_symbols()
        
        # Verify BTC-USDT is included (using fallback volume logic)
        self.assertIn('BTC-USDT', self.exchange_manager.symbols)
        
    @patch('exchange.BingXAPI')
    async def test_high_priority_symbols_inclusion(self, mock_api_class):
        """Test that high priority symbols are always included"""
        # Mock API
        mock_api = AsyncMock()
        mock_api_class.return_value = mock_api
        
        # Mock contracts response
        mock_contracts_response = {
            'data': [
                {
                    'symbol': 'BTC-USDT',
                    'status': 1,
                    'apiStateOpen': 'true',
                    'contractType': 'PERPETUAL'
                },
                {
                    'symbol': 'ETH-USDT',
                    'status': 1,
                    'apiStateOpen': 'true',
                    'contractType': 'PERPETUAL'
                },
                {
                    'symbol': 'BNB-USDT',
                    'status': 1,
                    'apiStateOpen': 'true',
                    'contractType': 'PERPETUAL'
                }
            ]
        }
        
        # Mock tickers response with very low volumes for high priority symbols
        mock_tickers_response = {
            'data': [
                {
                    'symbol': 'BTC-USDT',
                    'quoteVolume': '100000',  # Very low volume
                    'lastPrice': '50000'
                },
                {
                    'symbol': 'ETH-USDT',
                    'quoteVolume': '50000',   # Very low volume
                    'lastPrice': '3000'
                },
                {
                    'symbol': 'BNB-USDT',
                    'quoteVolume': '20000',   # Very low volume
                    'lastPrice': '300'
                }
            ]
        }
        
        # Set up mock responses
        mock_api.get_contracts.return_value = mock_contracts_response
        mock_api.get_ticker_price.return_value = mock_tickers_response
        
        # Initialize and load symbols
        await self.exchange_manager.initialize()
        with patch.object(self.exchange_manager, 'api', mock_api):
            await self.exchange_manager._load_symbols()
        
        # Verify high priority symbols are included despite low volume
        self.assertIn('BTC-USDT', self.exchange_manager.symbols)
        self.assertIn('ETH-USDT', self.exchange_manager.symbols)
        self.assertIn('BNB-USDT', self.exchange_manager.symbols)
        
    @patch('exchange.BingXAPI')
    async def test_min_volume_filtering(self, mock_api_class):
        """Test minimum volume filtering"""
        # Mock API
        mock_api = AsyncMock()
        mock_api_class.return_value = mock_api
        
        # Mock contracts response
        mock_contracts_response = {
            'data': [
                {
                    'symbol': 'BTC-USDT',
                    'status': 1,
                    'apiStateOpen': 'true',
                    'contractType': 'PERPETUAL'
                },
                {
                    'symbol': 'LOWVOL-USDT',
                    'status': 1,
                    'apiStateOpen': 'true',
                    'contractType': 'PERPETUAL'
                }
            ]
        }
        
        # Mock tickers response with one symbol below minimum volume
        mock_tickers_response = {
            'data': [
                {
                    'symbol': 'BTC-USDT',
                    'quoteVolume': '1000000000',  # Above threshold
                    'lastPrice': '50000'
                },
                {
                    'symbol': 'LOWVOL-USDT',
                    'quoteVolume': '100000',      # Below threshold (1M)
                    'lastPrice': '1.0'
                }
            ]
        }
        
        # Set up mock responses
        mock_api.get_contracts.return_value = mock_contracts_response
        mock_api.get_ticker_price.return_value = mock_tickers_response
        
        # Initialize and load symbols
        await self.exchange_manager.initialize()
        with patch.object(self.exchange_manager, 'api', mock_api):
            await self.exchange_manager._load_symbols()
        
        # Verify high volume symbol is included, low volume is excluded
        self.assertIn('BTC-USDT', self.exchange_manager.symbols)
        self.assertNotIn('LOWVOL-USDT', self.exchange_manager.symbols)


if __name__ == '__main__':
    # Run async tests
    unittest.main()