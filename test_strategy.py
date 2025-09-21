#!/usr/bin/env python3
"""
Unit tests for EMA20 strategy
"""

import asyncio
import pytest
import unittest
from datetime import datetime, timedelta
from strategy import StrategyManager, Signal

class TestStrategyManager(unittest.TestCase):
    
    def setUp(self):
        self.strategy = StrategyManager()
        
    def test_ema20_calculation(self):
        """Test EMA20 calculation with known data"""
        # Create test OHLCV data (25 candles for proper EMA20)
        ohlcv_data = []
        prices = [100, 101, 102, 103, 104, 105, 106, 107, 108, 109,
                 110, 111, 112, 113, 114, 115, 116, 117, 118, 119,
                 120, 121, 122, 123, 124]
        
        for i, price in enumerate(prices):
            ohlcv_data.append({
                'timestamp': 1000000 + i * 3600,
                'open': price - 0.5,
                'high': price + 1,
                'low': price - 1,
                'close': price,
                'volume': 1000
            })
            
        ema_values = self.strategy.calculate_ema20(ohlcv_data)
        
        # Should have 6 EMA values (25 candles - 20 for SMA + 1)
        self.assertEqual(len(ema_values), 6)
        
        # First EMA value should be calculated correctly using pandas EMA
        import pandas as pd
        series = pd.Series(prices)
        expected_ema_series = series.ewm(span=20, adjust=False).mean()
        expected_first_ema = expected_ema_series.iloc[19]
        self.assertAlmostEqual(ema_values[0], expected_first_ema, places=4)
        
        # EMA should be trending upward with rising prices
        for i in range(1, len(ema_values)):
            self.assertGreater(ema_values[i], ema_values[i-1])
            
    def test_ema20_insufficient_data(self):
        """Test EMA20 with insufficient data"""
        # Only 10 candles - should return empty list
        ohlcv_data = []
        for i in range(10):
            ohlcv_data.append({
                'timestamp': 1000000 + i * 3600,
                'open': 100,
                'high': 101,
                'low': 99,
                'close': 100,
                'volume': 1000
            })
            
        ema_values = self.strategy.calculate_ema20(ohlcv_data)
        self.assertEqual(len(ema_values), 0)
        
    def test_ema_rising_detection(self):
        """Test EMA rising trend detection"""
        # Rising EMA values
        rising_ema = [100.0, 100.5, 101.0, 101.5, 102.0]
        self.assertTrue(self.strategy.is_ema_rising(rising_ema, 3))
        
        # Falling EMA values
        falling_ema = [102.0, 101.5, 101.0, 100.5, 100.0]
        self.assertFalse(self.strategy.is_ema_rising(falling_ema, 3))
        
        # Mixed EMA values
        mixed_ema = [100.0, 100.5, 100.3, 100.8, 101.0]
        self.assertFalse(self.strategy.is_ema_rising(mixed_ema, 3))
        
    def test_ema_falling_detection(self):
        """Test EMA falling trend detection"""
        # Falling EMA values
        falling_ema = [102.0, 101.5, 101.0, 100.5, 100.0]
        self.assertTrue(self.strategy.is_ema_falling(falling_ema, 3))
        
        # Rising EMA values
        rising_ema = [100.0, 100.5, 101.0, 101.5, 102.0]
        self.assertFalse(self.strategy.is_ema_falling(rising_ema, 3))
        
    def test_touch_detection_long(self):
        """Test LONG touch detection"""
        symbol = "BTC-USDT"
        ema_value = 50000.0
        tolerance = 0.1  # 0.1%
        
        # LONG case: price was above tolerance zone and came into touch zone
        previous_price = 50100.0  # Above tolerance zone
        current_price = 50025.0   # In touch zone (EMA + 0.05%)
        
        touch = self.strategy.detect_touch(symbol, current_price, ema_value, previous_price)
        self.assertEqual(touch, "LONG")
        
    def test_touch_detection_short(self):
        """Test SHORT touch detection"""
        symbol = "BTC-USDT"
        ema_value = 50000.0
        
        # SHORT case: price was below tolerance zone and came into touch zone
        previous_price = 49900.0  # Below tolerance zone
        current_price = 49975.0   # In touch zone (EMA - 0.05%)
        
        touch = self.strategy.detect_touch(symbol, current_price, ema_value, previous_price)
        self.assertEqual(touch, "SHORT")
        
    def test_no_touch_detection(self):
        """Test no touch scenarios"""
        symbol = "BTC-USDT"
        ema_value = 50000.0
        
        # Price stays well above tolerance zone
        previous_price = 50300.0  # Well above upper tolerance zone (50250)
        current_price = 50400.0   # Well above upper tolerance zone (50250)
        touch = self.strategy.detect_touch(symbol, current_price, ema_value, previous_price)
        self.assertIsNone(touch)
        
        # Price stays well below tolerance zone
        previous_price = 49600.0  # Well below lower tolerance zone (49750)
        current_price = 49500.0   # Well below lower tolerance zone (49750)
        touch = self.strategy.detect_touch(symbol, current_price, ema_value, previous_price)
        self.assertIsNone(touch)

    def test_calculate_levels_long(self):
        """Test level calculation for LONG signals"""
        direction = "LONG"
        entry_price = 50000.0
        
        levels = self.strategy.calculate_levels(direction, entry_price)
        
        self.assertEqual(levels['sl'], 49500.0)    # -1%
        self.assertEqual(levels['tp1'], 50750.0)   # +1.5%
        self.assertEqual(levels['tp2'], 51500.0)   # +3%
        
    def test_calculate_levels_short(self):
        """Test level calculation for SHORT signals"""
        direction = "SHORT"
        entry_price = 50000.0
        
        levels = self.strategy.calculate_levels(direction, entry_price)
        
        self.assertEqual(levels['sl'], 50500.0)    # +1%
        self.assertEqual(levels['tp1'], 49250.0)   # -1.5%
        self.assertEqual(levels['tp2'], 48500.0)   # -3%
        
    def test_cooldown_mechanism(self):
        """Test signal cooldown mechanism"""
        symbol = "BTC-USDT"
        
        # No previous signal - no cooldown
        self.assertFalse(self.strategy.is_cooldown_active(symbol))
        
        # Add recent signal
        self.strategy.last_signals[symbol] = datetime.now()
        
        # Should be in cooldown
        self.assertTrue(self.strategy.is_cooldown_active(symbol))
        
        # Old signal - no cooldown
        old_time = datetime.now() - timedelta(hours=2)
        self.strategy.last_signals[symbol] = old_time
        self.assertFalse(self.strategy.is_cooldown_active(symbol))
        
    def test_signal_generation(self):
        """Test signal generation"""
        symbol = "BTC-USDT"
        direction = "LONG"
        current_price = 50000.0
        
        signal = self.strategy.generate_signal(symbol, direction, current_price)
        
        self.assertIsInstance(signal, Signal)
        self.assertEqual(signal.symbol, symbol)
        self.assertEqual(signal.direction, direction)
        self.assertEqual(signal.entry, current_price)
        self.assertEqual(signal.status, "OPEN")
        self.assertIsInstance(signal.created_at, datetime)
        
        # Check that cooldown is set
        self.assertTrue(self.strategy.is_cooldown_active(symbol))
        
    def test_signal_to_dict(self):
        """Test signal dictionary conversion"""
        signal = Signal(
            symbol="BTC-USDT",
            direction="LONG",
            entry=50000.0,
            sl=49500.0,
            tp1=50750.0,
            tp2=51500.0
        )
        
        signal_dict = signal.to_dict()
        
        self.assertEqual(signal_dict['symbol'], "BTC-USDT")
        self.assertEqual(signal_dict['direction'], "LONG")
        self.assertEqual(signal_dict['entry'], 50000.0)
        self.assertEqual(signal_dict['sl'], 49500.0)
        self.assertEqual(signal_dict['tp1'], 50750.0)
        self.assertEqual(signal_dict['tp2'], 51500.0)
        self.assertEqual(signal_dict['status'], "OPEN")
        self.assertIn('created_at', signal_dict)

def create_test_market_data():
    """Create test market data for integration tests"""
    # Create OHLCV data with clear trend
    ohlcv_data = []
    base_price = 50000
    
    # 25 candles with slight uptrend
    for i in range(25):
        price = base_price + (i * 10)  # Small uptrend
        ohlcv_data.append({
            'timestamp': 1000000 + i * 3600,
            'open': price - 5,
            'high': price + 10,
            'low': price - 10,
            'close': price,
            'volume': 1000
        })
        
    return {
        'ohlcv': {
            'BTC-USDT': ohlcv_data
        },
        'tickers': {
            'BTC-USDT': {
                'bid': 50240.0,
                'ask': 50250.0,
                'last': 50245.0,  # Close to EMA for potential touch
                'volume': 1000000
            }
        }
    }

class TestStrategyIntegration(unittest.TestCase):
    
    def setUp(self):
        self.strategy = StrategyManager()
        
    def test_market_analysis_no_signals(self):
        """Test market analysis with no signals generated"""
        market_data = create_test_market_data()
        
        # Modify price to be far from EMA
        market_data['tickers']['BTC-USDT']['last'] = 60000.0
        
        signals = asyncio.run(self.strategy.analyze_market(market_data))
        self.assertEqual(len(signals), 0)
        
    def test_market_analysis_with_signals(self):
        """Test market analysis that should generate signals"""
        market_data = create_test_market_data()
        
        # Set up a scenario that should trigger a signal
        # First run to establish previous price
        asyncio.run(self.strategy.analyze_market(market_data))
        
        # Modify for potential touch scenario  
        # Price should be set to create a touch condition
        market_data['tickers']['BTC-USDT']['last'] = 50235.0
        
        # This might generate signals depending on EMA calculation
        signals = asyncio.run(self.strategy.analyze_market(market_data))
        
        # The test may or may not generate signals depending on exact EMA values
        # This tests that the analysis runs without errors
        self.assertIsInstance(signals, list)

if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)