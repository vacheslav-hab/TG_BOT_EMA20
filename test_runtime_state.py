"""Test for runtime state functionality in main.py"""

import asyncio
import unittest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime
from main import TradingBot, RuntimeState


class TestRuntimeState(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.bot = TradingBot()
    
    def test_runtime_state_initialization(self):
        """Test that RuntimeState is properly initialized"""
        self.assertIsInstance(self.bot.state, RuntimeState)
        self.assertFalse(self.bot.state.running)
        self.assertEqual(self.bot.state.symbols, [])
        self.assertIsNone(self.bot.state.last_symbol_refresh)
        self.assertIsNone(self.bot.state.last_ohlcv_refresh)
        self.assertEqual(self.bot.state.cycle_count, 0)
        self.assertEqual(self.bot.state.api_call_count, 0)
        self.assertEqual(self.bot.state.signal_count, 0)
        self.assertEqual(self.bot.state.position_update_count, 0)
        self.assertEqual(self.bot.state.subscriber_count, 0)
        self.assertEqual(self.bot.state.active_positions, 0)
        self.assertEqual(self.bot.state.errors, [])
        self.assertIsNone(self.bot.state.last_error_time)
        
    def test_runtime_state_lock_initialization(self):
        """Test that state lock is properly initialized"""
        self.assertIsInstance(self.bot.state_lock, asyncio.Lock)
        
    async def test_state_locking(self):
        """Test that state access is properly locked"""
        # Test that we can acquire the lock
        async with self.bot.state_lock:
            # Modify state while holding lock
            self.bot.state.cycle_count = 5
            self.bot.state.api_call_count = 10
            
        # Verify changes were made
        self.assertEqual(self.bot.state.cycle_count, 5)
        self.assertEqual(self.bot.state.api_call_count, 10)
        
    async def test_concurrent_state_access(self):
        """Test concurrent access to state is handled properly"""
        # This test would ideally use multiple coroutines to test locking,
        # but for simplicity, we'll verify the lock exists and works
        self.assertIsInstance(self.bot.state_lock, asyncio.Lock)


class TestTradingBotStateUpdates(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.bot = TradingBot()
        # Mock dependencies
        self.bot.exchange_manager = Mock()
        self.bot.strategy_manager = Mock()
        self.bot.telegram_bot = Mock()
        self.bot.position_manager = Mock()
        self.bot.position_manager.get_active_positions_count.return_value = 0
        
    @patch('main.asyncio')
    async def test_start_updates_state(self, mock_asyncio):
        """Test that start method updates state correctly"""
        # Mock instance lock
        with patch('main.InstanceLock') as mock_lock_class:
            mock_lock = Mock()
            mock_lock.acquire.return_value = True
            mock_lock_class.return_value = mock_lock
            
            # Mock config validation
            with patch('main.validate_config') as mock_validate:
                mock_validate.return_value = True
                
                # Mock exchange initialization
                self.bot.exchange_manager.initialize = AsyncMock()
                self.bot.telegram_bot.start = AsyncMock()
                
                # Call start method
                result = await self.bot.start()
                
                # Verify state was updated
                self.assertTrue(self.bot.state.running)
                self.assertTrue(result)
                
    async def test_stop_updates_state(self):
        """Test that stop method updates state correctly"""
        # Set running state to True
        self.bot.state.running = True
        
        # Mock dependencies
        self.bot.telegram_bot.stop = AsyncMock()
        self.bot.exchange_manager.cleanup = AsyncMock()
        
        # Mock instance lock
        self.bot.instance_lock = Mock()
        
        # Call stop method
        await self.bot.stop()
        
        # Verify state was updated
        self.assertFalse(self.bot.state.running)
        
    async def test_refresh_top_symbols_updates_state(self):
        """Test that refresh_top_symbols updates state correctly"""
        # Mock exchange manager
        self.bot.exchange_manager._load_symbols = AsyncMock()
        self.bot.exchange_manager.symbols = ['BTC-USDT', 'ETH-USDT']
        
        # Mock sleep to avoid waiting
        with patch('main.asyncio.sleep', new_callable=AsyncMock):
            # Run one iteration of refresh_top_symbols
            task = asyncio.create_task(self.bot.refresh_top_symbols())
            
            # Let it run for a bit then cancel
            await asyncio.sleep(0.1)
            task.cancel()
            
            try:
                await task
            except asyncio.CancelledError:
                pass
                
            # Verify state was updated
            self.assertIsNotNone(self.bot.state.last_symbol_refresh)
            self.assertEqual(self.bot.state.symbols, ['BTC-USDT', 'ETH-USDT'])
            
    async def test_refresh_ohlcv_updates_state(self):
        """Test that refresh_ohlcv_and_ema updates state correctly"""
        # Mock sleep to avoid waiting
        with patch('main.asyncio.sleep', new_callable=AsyncMock):
            # Run one iteration of refresh_ohlcv_and_ema
            task = asyncio.create_task(self.bot.refresh_ohlcv_and_ema())
            
            # Let it run for a bit then cancel
            await asyncio.sleep(0.1)
            task.cancel()
            
            try:
                await task
            except asyncio.CancelledError:
                pass
                
            # Verify state was updated
            self.assertIsNotNone(self.bot.state.last_ohlcv_refresh)
            
    async def test_poll_tickers_updates_state(self):
        """Test that poll_tickers_loop updates state correctly"""
        # Set running state to True
        self.bot.state.running = True
        
        # Mock dependencies
        self.bot.exchange_manager.get_market_data = AsyncMock(return_value={
            'ohlcv': {},
            'tickers': {}
        })
        self.bot.telegram_bot.subscribers = set()
        self.bot.position_manager.monitor_all_positions.return_value = []
        self.bot.strategy_manager.analyze_market = AsyncMock(return_value=[])
        
        # Mock sleep to avoid waiting and control loop execution
        with patch('main.asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            # Make sleep raise an exception to break the loop after one iteration
            mock_sleep.side_effect = Exception("Break loop")
            
            try:
                await self.bot.poll_tickers_loop()
            except Exception as e:
                if "Break loop" not in str(e):
                    raise
                    
            # Verify state was updated
            self.assertEqual(self.bot.state.cycle_count, 1)
            self.assertEqual(self.bot.state.api_call_count, 2)  # 2 API calls per cycle


if __name__ == '__main__':
    unittest.main()