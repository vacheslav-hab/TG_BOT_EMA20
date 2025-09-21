"""Integration tests for the complete EMA20 trading system"""

import unittest
import asyncio
import json
import tempfile
import os
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

from main import TradingBot
from strategy import Signal
from position_manager import PositionStatus


class TestSystemIntegration(unittest.IsolatedAsyncioTestCase):
    
    def setUp(self):
        """Setup for each test"""
        # Use temporary file for testing
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        self.temp_file.close()
        
        # Mock environment variables
        self.env_patcher = patch.dict('os.environ', {
            'BINGX_API_KEY': 'test_key',
            'BINGX_SECRET_KEY': 'test_secret',
            'TELEGRAM_BOT_TOKEN': 'test_token',
            'JSON_FILE': self.temp_file.name
        })
        self.env_patcher.start()
        
        # Patch JSON_FILE in position_manager module
        self.json_file_patcher = patch('position_manager.JSON_FILE', self.temp_file.name)
        self.json_file_patcher.start()
        
    def tearDown(self):
        """Cleanup after each test"""
        self.env_patcher.stop()
        self.json_file_patcher.stop()
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)
            
    def create_mock_market_data(self):
        """Create mock market data for testing"""
        return {
            'ohlcv': {
                'BTC-USDT': [
                    {
                        'timestamp': 1700000000 + i * 3600,
                        'open': 50000 + i * 10,
                        'high': 50010 + i * 10,
                        'low': 49990 + i * 10,
                        'close': 50000 + i * 10,
                        'volume': 1000
                    }
                    for i in range(25)  # Enough for EMA20 calculation
                ]
            },
            'tickers': {
                'BTC-USDT': {
                    'bid': 50240.0,
                    'ask': 50250.0,
                    'last': 50245.0,
                    'volume': 1000000
                }
            }
        }
        
    @patch('exchange.ExchangeManager.initialize')
    @patch('exchange.ExchangeManager.get_market_data')
    @patch('bot.TelegramBot.start')
    @patch('bot.TelegramBot.broadcast_signals')
    @patch('bot.TelegramBot.broadcast_position_updates')
    async def test_complete_signal_lifecycle(
        self, mock_broadcast_updates, mock_broadcast_signals, 
        mock_bot_start, mock_get_market_data, mock_initialize
    ):
        """Test complete signal lifecycle from generation to closure"""
        
        # Setup mocks
        mock_initialize.return_value = True
        mock_bot_start.return_value = None
        mock_broadcast_signals.return_value = None
        mock_broadcast_updates.return_value = None
        
        # Create trading bot
        bot = TradingBot()
        
        # Mock successful start
        await bot.start()
        
        # Phase 1: Generate signal
        market_data = self.create_mock_market_data()
        
        # Modify data to trigger a signal
        bot.strategy_manager.previous_prices['BTC-USDT'] = 50400.0  # Price was higher
        market_data['tickers']['BTC-USDT']['last'] = 50245.0  # Price touches EMA
        
        mock_get_market_data.return_value = market_data
        
        # Analyze market to generate signal
        signals = await bot.strategy_manager.analyze_market(market_data)
        
        if signals:
            # Add signal to position manager
            signal = signals[0]
            signal_id = bot.position_manager.add_position(signal)
            
            # Verify signal was added
            self.assertIn(signal_id, bot.position_manager.active_positions)
            self.assertEqual(signal.status, PositionStatus.OPEN.value)
            
            # Phase 2: Monitor position - TP1 hit
            market_data['tickers']['BTC-USDT']['last'] = signal.tp1  # Price reaches TP1
            
            updates = bot.position_manager.monitor_all_positions(market_data)
            
            # Verify TP1 update
            self.assertEqual(len(updates), 1)
            update = updates[0]
            self.assertEqual(update.triggered_level, "TP1")
            self.assertEqual(update.new_status, PositionStatus.TP1_HIT.value)
            self.assertGreater(update.pnl_percentage, 0)
            
            # Phase 3: Monitor position - TP2 hit
            market_data['tickers']['BTC-USDT']['last'] = signal.tp2  # Price reaches TP2
            
            updates = bot.position_manager.monitor_all_positions(market_data)
            
            # Verify TP2 update
            self.assertEqual(len(updates), 1)
            update = updates[0]
            self.assertEqual(update.triggered_level, "TP2")
            self.assertEqual(update.new_status, PositionStatus.TP2_HIT.value)
            
            # Verify position is marked as closed
            self.assertEqual(bot.position_manager.get_active_positions_count(), 0)
            
        await bot.stop()
        
    @patch('exchange.ExchangeManager.initialize')
    @patch('exchange.ExchangeManager.get_market_data')
    @patch('bot.TelegramBot.start')
    async def test_stop_loss_scenario(
        self, mock_bot_start, mock_get_market_data, mock_initialize
    ):
        """Test stop loss triggering scenario"""
        
        # Setup mocks
        mock_initialize.return_value = True
        mock_bot_start.return_value = None
        
        bot = TradingBot()
        await bot.start()
        
        # Create a LONG signal manually
        signal = Signal(
            symbol="BTC-USDT",
            direction="LONG",
            entry=50000.0,
            sl=49500.0,
            tp1=50750.0,
            tp2=51500.0
        )
        
        signal_id = bot.position_manager.add_position(signal)
        
        # Create market data with price hitting SL
        market_data = {
            'tickers': {
                'BTC-USDT': {
                    'last': 49500.0  # Price hits SL
                }
            }
        }
        
        mock_get_market_data.return_value = market_data
        
        # Monitor positions
        updates = bot.position_manager.monitor_all_positions(market_data)
        
        # Verify SL update
        self.assertEqual(len(updates), 1)
        update = updates[0]
        self.assertEqual(update.triggered_level, "SL")
        self.assertEqual(update.new_status, PositionStatus.SL_HIT.value)
        self.assertLess(update.pnl_percentage, 0)
        
        await bot.stop()
        
    @patch('exchange.ExchangeManager.initialize')
    @patch('exchange.ExchangeManager.get_market_data')
    @patch('bot.TelegramBot.start')
    async def test_multiple_symbols_monitoring(
        self, mock_bot_start, mock_get_market_data, mock_initialize
    ):
        """Test monitoring multiple symbols simultaneously"""
        
        # Setup mocks
        mock_initialize.return_value = True
        mock_bot_start.return_value = None
        
        bot = TradingBot()
        await bot.start()
        
        # Create multiple signals
        signals = [
            Signal(symbol="BTC-USDT", direction="LONG", entry=50000.0, 
                  sl=49500.0, tp1=50750.0, tp2=51500.0),
            Signal(symbol="ETH-USDT", direction="SHORT", entry=3000.0, 
                  sl=3030.0, tp1=2955.0, tp2=2910.0),
            Signal(symbol="ADA-USDT", direction="LONG", entry=1.0, 
                  sl=0.99, tp1=1.015, tp2=1.03)
        ]
        
        # Add all signals to position manager
        signal_ids = []
        for signal in signals:
            signal_id = bot.position_manager.add_position(signal)
            signal_ids.append(signal_id)
            
        # Create market data that triggers different levels
        market_data = {
            'tickers': {
                'BTC-USDT': {'last': 50750.0},  # TP1 for LONG
                'ETH-USDT': {'last': 2955.0},   # TP1 for SHORT
                'ADA-USDT': {'last': 0.99}      # SL for LONG
            }
        }
        
        mock_get_market_data.return_value = market_data
        
        # Monitor all positions
        updates = bot.position_manager.monitor_all_positions(market_data)
        
        # Verify all positions were updated
        self.assertEqual(len(updates), 3)
        
        # Check specific updates
        btc_update = next(u for u in updates if u.symbol == "BTC-USDT")
        eth_update = next(u for u in updates if u.symbol == "ETH-USDT")
        ada_update = next(u for u in updates if u.symbol == "ADA-USDT")
        
        self.assertEqual(btc_update.triggered_level, "TP1")
        self.assertEqual(eth_update.triggered_level, "TP1")
        self.assertEqual(ada_update.triggered_level, "SL")
        
        await bot.stop()
        
    @patch('exchange.ExchangeManager.initialize')
    @patch('bot.TelegramBot.start')
    async def test_statistics_accumulation(self, mock_bot_start, mock_initialize):
        """Test statistics accumulation over multiple signals"""
        
        # Setup mocks
        mock_initialize.return_value = True
        mock_bot_start.return_value = None
        
        bot = TradingBot()
        await bot.start()
        
        # Simulate multiple completed signals
        test_scenarios = [
            ("BTC-USDT", "LONG", 50000.0, 50750.0, "TP1"),  # Profit
            ("ETH-USDT", "SHORT", 3000.0, 2955.0, "TP1"),   # Profit
            ("ADA-USDT", "LONG", 1.0, 1.03, "TP2"),         # Bigger profit
            ("DOT-USDT", "SHORT", 10.0, 10.1, "SL"),        # Loss
            ("LINK-USDT", "LONG", 20.0, 19.8, "SL")         # Loss
        ]
        
        for symbol, direction, entry, final_price, level in test_scenarios:
            # Create signal
            signal = Signal(
                symbol=symbol,
                direction=direction,
                entry=entry,
                sl=entry * 0.99 if direction == "LONG" else entry * 1.01,
                tp1=entry * 1.015 if direction == "LONG" else entry * 0.985,
                tp2=entry * 1.03 if direction == "LONG" else entry * 0.97
            )
            
            signal_id = bot.position_manager.add_position(signal)
            
            # Trigger the level
            market_data = {'tickers': {symbol: {'last': final_price}}}
            updates = bot.position_manager.monitor_all_positions(market_data)
            
            # Verify update
            self.assertEqual(len(updates), 1)
            self.assertEqual(updates[0].triggered_level, level)
            
        # Check final statistics
        stats = bot.position_manager.statistics
        
        self.assertEqual(stats['total_signals'], 5)
        self.assertEqual(stats['tp1_hits'], 2)
        self.assertEqual(stats['tp2_hits'], 1)
        self.assertEqual(stats['sl_hits'], 2)
        
        # Win rate should be 60% (3 wins out of 5)
        self.assertAlmostEqual(stats['win_rate'], 60.0, places=1)
        
        await bot.stop()
        
    @patch('exchange.ExchangeManager.initialize')
    @patch('bot.TelegramBot.start')
    async def test_position_persistence(self, mock_bot_start, mock_initialize):
        """Test position persistence across bot restarts"""
        
        # Setup mocks
        mock_initialize.return_value = True
        mock_bot_start.return_value = None
        
        # First bot instance
        bot1 = TradingBot()
        await bot1.start()
        
        # Add position
        signal = Signal(
            symbol="BTC-USDT",
            direction="LONG",
            entry=50000.0,
            sl=49500.0,
            tp1=50750.0,
            tp2=51500.0
        )
        
        signal_id = bot1.position_manager.add_position(signal)
        
        # Save and stop
        bot1.position_manager.save_positions()
        await bot1.stop()
        
        # Create new bot instance
        bot2 = TradingBot()
        await bot2.start()
        
        # Verify position was loaded
        self.assertIn(signal_id, bot2.position_manager.active_positions)
        self.assertEqual(len(bot2.position_manager.active_positions), 1)
        
        loaded_signal = bot2.position_manager.active_positions[signal_id]
        self.assertEqual(loaded_signal.symbol, "BTC-USDT")
        self.assertEqual(loaded_signal.direction, "LONG")
        self.assertEqual(loaded_signal.entry, 50000.0)
        
        await bot2.stop()


class TestBotCommands(unittest.IsolatedAsyncioTestCase):
    """Test Telegram bot command handling"""
    
    def setUp(self):
        """Setup for each test"""
        self.env_patcher = patch.dict('os.environ', {
            'TELEGRAM_BOT_TOKEN': 'test_token'
        })
        self.env_patcher.start()
        
    def tearDown(self):
        """Cleanup after each test"""
        self.env_patcher.stop()
        
    def test_signal_message_formatting(self):
        """Test signal message formatting"""
        from bot import TelegramBot
        
        bot = TelegramBot()
        
        signal = Signal(
            symbol="BTC-USDT",
            direction="LONG",
            entry=50000.0,
            sl=49500.0,
            tp1=50750.0,
            tp2=51500.0
        )
        
        message = bot.format_signal_message(signal)
        
        self.assertIn("🚀", message)  # LONG emoji
        self.assertIn("BTC-USDT", message)
        self.assertIn("50,000", message)  # Entry price (formatted)
        self.assertIn("49,500", message)  # SL
        self.assertIn("50,750", message)  # TP1
        self.assertIn("51,500", message)  # TP2
        
    def test_position_update_message_formatting(self):
        """Test position update message formatting"""
        from bot import TelegramBot
        from position_manager import PositionUpdate
        
        bot = TelegramBot()
        
        update = PositionUpdate(
            signal_id="test_id",
            symbol="BTC-USDT",
            direction="LONG",
            current_price=50750.0,
            old_status="OPEN",
            new_status="TP1_HIT",
            pnl_percentage=1.5,
            triggered_level="TP1"
        )
        
        message = bot.format_position_update_message(update)
        
        self.assertIn("🎯", message)  # TP1 emoji
        self.assertIn("Take Profit 1", message)
        self.assertIn("BTC-USDT", message)
        self.assertIn("50,750", message)  # Current price (formatted)
        self.assertIn("+1.50%", message)  # PnL


if __name__ == '__main__':
    unittest.main()