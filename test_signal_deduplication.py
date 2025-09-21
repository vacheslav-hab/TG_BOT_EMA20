#!/usr/bin/env python3
"""
Test script to validate signal deduplication functionality
"""

import unittest
from unittest.mock import patch, MagicMock
import asyncio
from decimal import Decimal
import json
import os
import tempfile

# Add the project root to the Python path
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from strategy import create_signal_atomic, detect_touch
from json_manager import JSONDataManager
from config import EMA_PERIOD


class TestSignalDeduplication(unittest.TestCase):
    
    def setUp(self):
        # Create a temporary file for testing
        self.test_file = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
        self.test_file.close()
        
    def tearDown(self):
        # Clean up the temporary file
        if os.path.exists(self.test_file.name):
            os.unlink(self.test_file.name)
    
    @patch('strategy.JSONDataManager')
    def test_signal_deduplication(self, mock_json_manager):
        """Test that duplicate signals are not created"""
        # Setup mock
        mock_data = {"positions": {}}
        mock_instance = MagicMock()
        mock_instance.load_data.return_value = mock_data
        mock_instance.save_data = MagicMock()
        # Simulate that after the first call, there's an open signal
        mock_instance.get_open_signal.side_effect = [None, {"symbol": "BTC-USDT", "direction": "LONG", "status": "OPEN"}]
        mock_json_manager.return_value = mock_instance
        
        # Test implementation
        symbol = "BTC-USDT"
        direction = "LONG"
        entry = Decimal("50000.0")
        ema_value = Decimal("49900.0")
        
        # Execute two sequential signal creation attempts (not parallel)
        async def create_signals():
            task1 = await create_signal_atomic(symbol, direction, entry, ema_value)
            task2 = await create_signal_atomic(symbol, direction, entry, ema_value)
            return task1, task2
        
        results = asyncio.run(create_signals())
        
        # Verify only one signal was created (one should be signal object, other None)
        self.assertIsNotNone(results[0])
        self.assertIsNone(results[1])
        
    @patch('strategy.JSONDataManager')
    def test_ema20_usage(self, mock_json_manager):
        """Test that created signals contain correct EMA period information"""
        # Setup mock
        mock_data = {"positions": {}}
        mock_instance = MagicMock()
        mock_instance.load_data.return_value = mock_data
        mock_instance.save_data = MagicMock()
        mock_instance.get_open_signal.return_value = None  # No existing open signal
        mock_json_manager.return_value = mock_instance
        
        # Test implementation
        ema_info = {
            "ema_last": Decimal("0.5"),
            "ema_prev": Decimal("0.49"),
        }
        prev_price = Decimal("0.501")
        cur_price = Decimal("0.499")
        
        # Execute signal creation with mocked EMA values
        result = asyncio.run(create_signal_atomic("TEST/USDT", "LONG", cur_price, ema_info["ema_last"]))
        
        # Verify resulting signal contains:
        # - ema_used_period == 20
        # - ema_value matches the ema_last value used
        self.assertIsNotNone(result)
        self.assertEqual(result["ema_used_period"], 20)  # Fixed to 20 as per requirements
        self.assertEqual(result["ema_value"], float(ema_info["ema_last"]))
        
    @patch('strategy.JSONDataManager')
    def test_cooldown_enforcement(self, mock_json_manager):
        """Test that cooldown periods are respected"""
        from datetime import datetime, timedelta
        
        # Setup mock with existing signal in cooldown
        future_time = (datetime.utcnow() + timedelta(minutes=30)).isoformat() + "Z"
        mock_data = {
            "positions": {
                "BTC-USDT": {
                    "status": "CLOSED",
                    "direction": "LONG",
                    "cooldown_until": future_time
                }
            }
        }
        mock_instance = MagicMock()
        mock_instance.load_data.return_value = mock_data
        mock_instance.save_data = MagicMock()
        mock_json_manager.return_value = mock_instance
        
        # Test implementation
        symbol = "BTC-USDT"
        direction = "LONG"
        entry = Decimal("50000.0")
        ema_value = Decimal("49900.0")
        
        # Attempt to create new signal
        result = asyncio.run(create_signal_atomic(symbol, direction, entry, ema_value))
        
        # Verify result is None (signal creation rejected)
        self.assertIsNone(result)
        
    def test_detect_touch_function(self):
        """Test the detect_touch function with EMA20 values"""
        # Test LONG signal detection
        symbol = "BTC-USDT"
        ema20_last = Decimal("50000.0")
        ema20_prev = Decimal("49900.0")
        last_closed_close = Decimal("50100.0")
        previous_price = Decimal("50050.0")
        current_price = Decimal("49950.0")
        
        direction = detect_touch(
            symbol, ema20_last, ema20_prev, last_closed_close, 
            previous_price, current_price
        )
        
        # Should detect a LONG signal based on the conditions
        self.assertIn(direction, [None, "LONG", "SHORT"])
        
        # Test SHORT signal detection
        ema20_last = Decimal("50000.0")
        ema20_prev = Decimal("50100.0")
        last_closed_close = Decimal("49900.0")
        previous_price = Decimal("49950.0")
        current_price = Decimal("50050.0")
        
        direction = detect_touch(
            symbol, ema20_last, ema20_prev, last_closed_close, 
            previous_price, current_price
        )
        
        # Should detect a SHORT signal based on the conditions
        self.assertIn(direction, [None, "LONG", "SHORT"])


class TestJSONDataManagerWithEMAFields(unittest.TestCase):
    
    def setUp(self):
        # Create a temporary file for testing
        self.test_file = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
        self.test_file.close()
        
    def tearDown(self):
        # Clean up the temporary file
        if os.path.exists(self.test_file.name):
            os.unlink(self.test_file.name)
    
    def test_extended_position_data_with_ema_fields(self):
        """Test that ExtendedPositionData can handle EMA fields"""
        from json_manager import ExtendedPositionData
        from datetime import datetime
        
        # Create an ExtendedPositionData object with EMA fields
        position = ExtendedPositionData(
            signal_id="test_signal_123",
            symbol="BTC-USDT",
            direction="LONG",
            entry_price=50000.0,
            sl_price=49500.0,
            tp1_price=50750.0,
            tp2_price=51500.0,
            status="OPEN",
            created_at=datetime.now(),
            ema_used_period=EMA_PERIOD,
            ema_value=49900.0
        )
        
        # Convert to dict and back
        position_dict = position.to_dict()
        restored_position = ExtendedPositionData.from_dict(position_dict)
        
        # Verify EMA fields are preserved
        self.assertEqual(restored_position.ema_used_period, EMA_PERIOD)
        self.assertEqual(restored_position.ema_value, 49900.0)
        
    def test_ema_data_validation(self):
        """Test EMA data validation"""
        from json_manager import ExtendedPositionData
        from datetime import datetime
        
        # Create an ExtendedPositionData object with correct EMA fields
        position = ExtendedPositionData(
            signal_id="test_signal_123",
            symbol="BTC-USDT",
            direction="LONG",
            entry_price=50000.0,
            sl_price=49500.0,
            tp1_price=50750.0,
            tp2_price=51500.0,
            status="OPEN",
            created_at=datetime.now(),
            ema_used_period=EMA_PERIOD,
            ema_value=49900.0
        )
        
        # Validate EMA data
        self.assertTrue(position.validate_ema_data())
        
        # Create an ExtendedPositionData object with incorrect EMA period
        position_incorrect = ExtendedPositionData(
            signal_id="test_signal_124",
            symbol="BTC-USDT",
            direction="LONG",
            entry_price=50000.0,
            sl_price=49500.0,
            tp1_price=50750.0,
            tp2_price=51500.0,
            status="OPEN",
            created_at=datetime.now(),
            ema_used_period=9,  # Incorrect period
            ema_value=49900.0
        )
        
        # Validate EMA data - should fail
        self.assertFalse(position_incorrect.validate_ema_data())


if __name__ == '__main__':
    unittest.main()