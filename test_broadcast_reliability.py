"""
Test cases for broadcast reliability
"""

import asyncio
import unittest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime
from telegram import Bot
from strategy import Signal
from position_manager import PositionUpdate
from bot import TelegramBot


class TestBroadcastReliability(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.bot = TelegramBot()
        self.bot.subscribers = {123456789, 987654321, 111111111}  # Valid subscribers
        self.bot.application = Mock()
        self.bot.application.bot = AsyncMock()
        
    def test_broadcast_signals_with_invalid_chat_id(self):
        """Test that broadcast continues to other users when one fails"""
        # Create test signals
        signal = Signal(
            symbol="BTC-USDT",
            direction="LONG",
            entry=50000.0,
            sl=49500.0,
            tp1=50750.0,
            tp2=51500.0,
            ema_value=49800.0,
            created_at=datetime.now()
        )
        signals = [signal]
        
        # Mock send_message to fail for one user but succeed for others
        async def mock_send_message(chat_id, text):
            if chat_id == 111111111:  # This user will fail
                raise Exception("Bot was blocked by the user")
            return Mock()
            
        self.bot.application.bot.send_message = AsyncMock(side_effect=mock_send_message)
        
        # Run the broadcast
        asyncio.run(self.bot.broadcast_signals(signals))
        
        # Verify that send_message was called for all users
        self.assertEqual(self.bot.application.bot.send_message.call_count, 3)
        # Verify that the failed user was removed from subscribers
        self.assertNotIn(111111111, self.bot.subscribers)
        
    def test_broadcast_position_updates_with_invalid_chat_id(self):
        """Test that position update broadcast continues to other users when one fails"""
        # Create test position updates
        update = PositionUpdate(
            signal_id="BTC-USDT_LONG_20250914_123456",
            symbol="BTC-USDT",
            direction="LONG",
            triggered_level="TP1",
            current_price=50750.0,
            pnl_percentage=1.5,
            new_status="TP1_HIT",
            timestamp=datetime.now()
        )
        updates = [update]
        
        # Mock send_message to fail for one user but succeed for others
        async def mock_send_message(chat_id, text):
            if chat_id == 111111111:  # This user will fail
                raise Exception("Chat not found")
            return Mock()
            
        self.bot.application.bot.send_message = AsyncMock(side_effect=mock_send_message)
        
        # Run the broadcast
        asyncio.run(self.bot.broadcast_position_updates(updates))
        
        # Verify that send_message was called for all users
        self.assertEqual(self.bot.application.bot.send_message.call_count, 3)
        # Verify that the failed user was removed from subscribers
        self.assertNotIn(111111111, self.bot.subscribers)
        
    def test_broadcast_signals_success_failure_counters(self):
        """Test that success/failure counters are properly logged"""
        # Create test signals
        signal = Signal(
            symbol="ETH-USDT",
            direction="SHORT",
            entry=3000.0,
            sl=3030.0,
            tp1=2955.0,
            tp2=2910.0,
            ema_value=3010.0,
            created_at=datetime.now()
        )
        signals = [signal]
        
        # Mock send_message to fail for one user but succeed for others
        async def mock_send_message(chat_id, text):
            if chat_id == 111111111:  # This user will fail
                raise Exception("User is deactivated")
            return Mock()
            
        self.bot.application.bot.send_message = AsyncMock(side_effect=mock_send_message)
        
        # Capture log messages
        with self.assertLogs('bot', level='INFO') as log:
            asyncio.run(self.bot.broadcast_signals(signals))
            
            # Check that success and failure counts are logged
            success_log_found = any("успех 2" in record.getMessage() for record in log.records)
            failure_log_found = any("ошибок 1" in record.getMessage() for record in log.records)
            
            self.assertTrue(success_log_found, "Success count not logged properly")
            self.assertTrue(failure_log_found, "Failure count not logged properly")
            
    def test_broadcast_position_updates_success_failure_counters(self):
        """Test that success/failure counters are properly logged for position updates"""
        # Create test position updates
        update = PositionUpdate(
            signal_id="ETH-USDT_SHORT_20250914_123456",
            symbol="ETH-USDT",
            direction="SHORT",
            triggered_level="SL",
            current_price=3030.0,
            pnl_percentage=-1.0,
            new_status="SL_HIT",
            timestamp=datetime.now()
        )
        updates = [update]
        
        # Mock send_message to fail for one user but succeed for others
        async def mock_send_message(chat_id, text):
            if chat_id == 111111111:  # This user will fail
                raise Exception("Bot was blocked by the user")
            return Mock()
            
        self.bot.application.bot.send_message = AsyncMock(side_effect=mock_send_message)
        
        # Capture log messages
        with self.assertLogs('bot', level='INFO') as log:
            asyncio.run(self.bot.broadcast_position_updates(updates))
            
            # Check that success and failure counts are logged
            success_log_found = any("успех 2" in record.getMessage() for record in log.records)
            failure_log_found = any("ошибок 1" in record.getMessage() for record in log.records)
            
            self.assertTrue(success_log_found, "Success count not logged properly")
            self.assertTrue(failure_log_found, "Failure count not logged properly")


if __name__ == '__main__':
    unittest.main()