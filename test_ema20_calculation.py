#!/usr/bin/env python3
"""
Test script to validate EMA20 calculation function
"""

import unittest
import pandas as pd
from strategy import calc_ema20


class TestEMA20Calculation(unittest.TestCase):
    
    def test_ema20_calculation(self):
        """Test the exact EMA20 calculation function from requirements"""
        # Create test data - 20 closed candles
        closes = [100 + i for i in range(20)]  # [100, 101, 102, ..., 119]
        
        # Calculate EMA20 using our function
        ema_value = calc_ema20(closes)
        
        # Calculate EMA20 using pandas directly for verification
        series = pd.Series(closes)
        expected_ema = series.ewm(span=20, adjust=False).mean().iloc[-1]
        
        # They should be equal
        self.assertEqual(ema_value, float(expected_ema))
        
    def test_ema20_with_realistic_data(self):
        """Test EMA20 with more realistic price data"""
        # Sample price data
        closes = [50000, 50100, 49950, 50200, 50150, 50300, 50250, 50400, 50350, 50500,
                  50450, 50600, 50550, 50700, 50650, 50800, 50750, 50900, 50850, 51000]
        
        # Calculate EMA20 using our function
        ema_value = calc_ema20(closes)
        
        # With this data, EMA20 should be around the average of the series
        simple_average = sum(closes) / len(closes)
        
        # EMA should be close to simple average but slightly weighted toward recent prices
        self.assertGreater(ema_value, simple_average * 0.99)
        self.assertLess(ema_value, simple_average * 1.01)


if __name__ == '__main__':
    unittest.main()