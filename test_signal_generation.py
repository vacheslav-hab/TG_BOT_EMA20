#!/usr/bin/env python3
"""
Unit tests for signal generation functionality
"""

import unittest
import json
import tempfile
import os
from datetime import datetime
from decimal import Decimal
from unittest.mock import patch, MagicMock

# Add current directory to path for imports
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from strategy import (detect_touch, validate_signal_direction, can_generate_signal, 
                     register_signal, create_signal_atomic, _validate_price_input,
                     _validate_candle_data)
from decimal import Decimal


class TestSignalGeneration(unittest.TestCase):
    
    def setUp(self):
        """Setup for each test"""
        # Clear any existing signal metadata
        global last_signal_candle
        from strategy import last_signal_candle
        last_signal_candle.clear()
        
    def test_detect_touch_valid_touch(self):
        """Test EMA20 touch detection with valid touch scenario"""
        # Mock candle data
        candle = {
            'high': 50200.0,
            'low': 49800.0,
            'close': 50100.0,
            'open': 49900.0,
            'timestamp': "2024-01-01T12:00:00Z"
        }
        
        # EMA20 value within candle range with 0.5% tolerance
        ema_value = 50000.0
        
        # Should detect touch
        result = detect_touch(candle, ema_value)
        self.assertTrue(result)
        
    def test_detect_touch_no_touch(self):
        """Test EMA20 touch detection with no touch scenario"""
        # Mock candle data
        candle = {
            'high': 50200.0,
            'low': 49800.0,
            'close': 50100.0,
            'open': 49900.0,
            'timestamp': "2024-01-01T12:00:00Z"
        }
        
        # EMA20 value outside candle range even with 0.5% tolerance
        ema_value = 49000.0
        
        # Should not detect touch
        result = detect_touch(candle, ema_value)
        self.assertFalse(result)
        
    def test_validate_signal_direction_long_valid(self):
        """Test LONG signal direction validation with valid parameters"""
        candle = {'close': 50100.0}
        ema_current = 50000.0
        ema_previous = 49995.0  # Slight upward slope
        direction = "LONG"
        
        result = validate_signal_direction(candle, ema_current, ema_previous, direction)
        self.assertTrue(result)
        
    def test_validate_signal_direction_long_invalid_price(self):
        """Test LONG signal direction validation with price below EMA"""
        candle = {'close': 49900.0}  # Below EMA
        ema_current = 50000.0
        ema_previous = 49995.0
        direction = "LONG"
        
        result = validate_signal_direction(candle, ema_current, ema_previous, direction)
        self.assertFalse(result)
        
    def test_validate_signal_direction_long_invalid_slope(self):
        """Test LONG signal direction validation with steep negative slope"""
        candle = {'close': 50100.0}
        ema_current = 50000.0
        ema_previous = 50010.0  # Steep decline beyond -0.01% tolerance
        direction = "LONG"
        
        result = validate_signal_direction(candle, ema_current, ema_previous, direction)
        self.assertFalse(result)
        
    def test_validate_signal_direction_short_valid(self):
        """Test SHORT signal direction validation with valid parameters"""
        candle = {'close': 49900.0}
        ema_current = 50000.0
        ema_previous = 50005.0  # Slight downward slope
        direction = "SHORT"
        
        result = validate_signal_direction(candle, ema_current, ema_previous, direction)
        self.assertTrue(result)
        
    def test_validate_signal_direction_short_invalid_price(self):
        """Test SHORT signal direction validation with price above EMA"""
        candle = {'close': 50100.0}  # Above EMA
        ema_current = 50000.0
        ema_previous = 50005.0
        direction = "SHORT"
        
        result = validate_signal_direction(candle, ema_current, ema_previous, direction)
        self.assertFalse(result)
        
    def test_validate_signal_direction_short_invalid_slope(self):
        """Test SHORT signal direction validation with steep positive slope"""
        candle = {'close': 49900.0}
        ema_current = 50000.0
        ema_previous = 49990.0  # Steep incline beyond +0.01% tolerance
        direction = "SHORT"
        
        result = validate_signal_direction(candle, ema_current, ema_previous, direction)
        self.assertFalse(result)
        
    def test_can_generate_signal_first_signal(self):
        """Test signal generation allowance for first signal"""
        symbol = "BTCUSDT"
        candle_time = "2024-01-01T12:00:00Z"
        
        result = can_generate_signal(symbol, candle_time)
        self.assertTrue(result)
        
    def test_can_generate_signal_duplicate_protection(self):
        """Test signal generation duplicate protection"""
        symbol = "BTCUSDT"
        candle_time = "2024-01-01T12:00:00Z"
        
        # Register first signal
        register_signal(symbol, candle_time)
        
        # Try to generate another signal for same candle
        result = can_generate_signal(symbol, candle_time)
        self.assertFalse(result)
        
    def test_can_generate_signal_new_candle(self):
        """Test signal generation for new candle"""
        symbol = "BTCUSDT"
        candle_time1 = "2024-01-01T12:00:00Z"
        candle_time2 = "2024-01-01T13:00:00Z"
        
        # Register first signal
        register_signal(symbol, candle_time1)
        
        # Try to generate signal for new candle
        result = can_generate_signal(symbol, candle_time2)
        self.assertTrue(result)
        
    def test_create_signal_atomic_valid(self):
        """Test atomic signal creation with valid parameters"""
        # This test would require mocking the JSONDataManager and async operations
        # For now, we'll test the validation parts
        pass
        
    def test_validate_price_input_valid(self):
        """Test price input validation with valid price"""
        result = _validate_price_input(50000.0, "test_price")
        self.assertTrue(result)
        
    def test_validate_price_input_zero(self):
        """Test price input validation with zero price"""
        result = _validate_price_input(0.0, "test_price")
        self.assertFalse(result)
        
    def test_validate_price_input_negative(self):
        """Test price input validation with negative price"""
        result = _validate_price_input(-50000.0, "test_price")
        self.assertFalse(result)
        
    def test_validate_price_input_infinite(self):
        """Test price input validation with infinite price"""
        result = _validate_price_input(float('inf'), "test_price")
        self.assertFalse(result)
        
    def test_validate_price_input_nan(self):
        """Test price input validation with NaN price"""
        result = _validate_price_input(float('nan'), "test_price")
        self.assertFalse(result)
        
    def test_validate_candle_data_valid(self):
        """Test candle data validation with valid data"""
        candle = {
            'high': 50200.0,
            'low': 49800.0,
            'open': 49900.0,
            'close': 50100.0,
            'timestamp': "2024-01-01T12:00:00Z"
        }
        
        result = _validate_candle_data(candle, "BTCUSDT")
        self.assertTrue(result)
        
    def test_validate_candle_data_missing_field(self):
        """Test candle data validation with missing field"""
        candle = {
            'high': 50200.0,
            'low': 49800.0,
            'open': 49900.0,
            'close': 50100.0
            # Missing timestamp
        }
        
        result = _validate_candle_data(candle, "BTCUSDT")
        self.assertFalse(result)
        
    def test_validate_candle_data_invalid_price(self):
        """Test candle data validation with invalid price"""
        candle = {
            'high': 50200.0,
            'low': -49800.0,  # Negative price
            'open': 49900.0,
            'close': 50100.0,
            'timestamp': "2024-01-01T12:00:00Z"
        }
        
        result = _validate_candle_data(candle, "BTCUSDT")
        self.assertFalse(result)
        
    def test_validate_candle_data_invalid_high_low(self):
        """Test candle data validation with high < low"""
        candle = {
            'high': 49800.0,  # High less than low
            'low': 50200.0,
            'open': 49900.0,
            'close': 50100.0,
            'timestamp': "2024-01-01T12:00:00Z"
        }
        
        result = _validate_candle_data(candle, "BTCUSDT")
        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()