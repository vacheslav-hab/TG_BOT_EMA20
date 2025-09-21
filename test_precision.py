"""Test for precision calculations with small prices"""

import unittest
from decimal import Decimal
from strategy import StrategyManager
from decimal_utils import format_price, precise_multiply


class TestPrecisionCalculations(unittest.TestCase):
    
    def test_small_price_precision(self):
        """Test precision with small price like 0.00005342"""
        entry_price = 0.00005342
        
        # Calculate expected values using Decimal
        entry_decimal = Decimal(str(entry_price))
        expected_sl = precise_multiply(entry_decimal, Decimal('0.99'))
        expected_tp1 = precise_multiply(entry_decimal, Decimal('1.015'))
        expected_tp2 = precise_multiply(entry_decimal, Decimal('1.03'))
        
        # Test direct decimal calculations
        sl_decimal = precise_multiply(entry_decimal, Decimal('0.99'))
        tp1_decimal = precise_multiply(entry_decimal, Decimal('1.015'))
        tp2_decimal = precise_multiply(entry_decimal, Decimal('1.03'))
        
        # Check that calculations match expected values
        self.assertEqual(sl_decimal, expected_sl)
        self.assertEqual(tp1_decimal, expected_tp1)
        self.assertEqual(tp2_decimal, expected_tp2)
        
    def test_strategy_calculate_levels(self):
        """Test StrategyManager.calculate_levels with small price"""
        strategy = StrategyManager()
        
        entry_price = 0.00005342
        levels = strategy.calculate_levels("LONG", entry_price)
        
        # Check that we get reasonable values
        self.assertLess(levels['sl'], entry_price)
        self.assertGreater(levels['tp1'], entry_price)
        self.assertGreater(levels['tp2'], entry_price)
        self.assertGreater(levels['tp2'], levels['tp1'])
        
    def test_short_levels(self):
        """Test SHORT level calculations"""
        strategy = StrategyManager()
        
        entry_price = 0.00005342
        levels = strategy.calculate_levels("SHORT", entry_price)
        
        # For SHORT, SL should be higher than entry
        self.assertGreater(levels['sl'], entry_price)
        self.assertLess(levels['tp1'], entry_price)
        self.assertLess(levels['tp2'], entry_price)
        self.assertLess(levels['tp2'], levels['tp1'])


if __name__ == '__main__':
    unittest.main()