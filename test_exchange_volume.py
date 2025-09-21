"""Test for exchange volume-based symbol selection"""

import unittest
from unittest.mock import AsyncMock, patch
from exchange import ExchangeManager


class TestExchangeVolumeSelection(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.exchange_manager = ExchangeManager()
    
    @patch('exchange.BingXAPI')
    async def test_get_top_symbols_by_volume(self, mock_api_class):
        """Test get_top_symbols_by_volume function"""
        # Mock API responses
        mock_api = AsyncMock()
        mock_api_class.return_value = mock_api
        
        # Mock contracts response
        mock_contracts_response = {
            'data': [
                {
                    'symbol': 'BTC-USDT',
                    'status': 1,
                    'apiStateOpen': 'true'
                },
                {
                    'symbol': 'ETH-USDT',
                    'status': 1,
                    'apiStateOpen': 'true'
                },
                {
                    'symbol': 'BNB-USDT',
                    'status': 1,
                    'apiStateOpen': 'true'
                },
                {
                    'symbol': 'SOL-USDT',
                    'status': 1,
                    'apiStateOpen': 'true'
                },
                {
                    'symbol': 'X-USDT',
                    'status': 1,
                    'apiStateOpen': 'true'
                }
            ]
        }
        
        # Mock tickers response
        mock_tickers_response = {
            'data': [
                {
                    'symbol': 'BTC-USDT',
                    'quoteVolume': '1000000000',  # 1B
                    'lastPrice': '50000'
                },
                {
                    'symbol': 'ETH-USDT',
                    'quoteVolume': '500000000',   # 500M
                    'lastPrice': '3000'
                },
                {
                    'symbol': 'BNB-USDT',
                    'quoteVolume': '200000000',   # 200M
                    'lastPrice': '300'
                },
                {
                    'symbol': 'SOL-USDT',
                    'quoteVolume': '50000000',    # 50M
                    'lastPrice': '100'
                },
                {
                    'symbol': 'X-USDT',
                    'quoteVolume': '1000000',     # 1M (below threshold)
                    'lastPrice': '0.1'
                }
            ]
        }
        
        mock_api.get_contracts.return_value = mock_contracts_response
        mock_api.get_ticker_price.return_value = mock_tickers_response
        
        # Test the _load_symbols method
        with patch.object(self.exchange_manager, 'api', mock_api):
            await self.exchange_manager._load_symbols()
        
        # Check that symbols are loaded correctly
        self.assertIn('BTC-USDT', self.exchange_manager.symbols)
        self.assertIn('ETH-USDT', self.exchange_manager.symbols)
        self.assertIn('BNB-USDT', self.exchange_manager.symbols)
        self.assertIn('SOL-USDT', self.exchange_manager.symbols)
        # X-USDT should be excluded due to low volume
        self.assertNotIn('X-USDT', self.exchange_manager.symbols)
        
        # Check that high priority symbols are included regardless of volume
        # (We would need to test this with a low-volume high-priority symbol)


if __name__ == '__main__':
    unittest.main()