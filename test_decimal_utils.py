"""Tests for decimal_utils module"""

import unittest
from decimal import Decimal
from decimal_utils import format_price, precise_divide, precise_multiply, precise_add, precise_subtract


class TestDecimalUtils(unittest.TestCase):
    
    def test_format_price_ge_1(self):
        """Test format_price for prices >= 1"""
        self.assertEqual(format_price(1.23456), "1.23")
        self.assertEqual(format_price(123.456789), "123.46")
        self.assertEqual(format_price(1000.0), "1000.00")
        
    def test_format_price_lt_1(self):
        """Test format_price for prices < 1"""
        self.assertEqual(format_price(0.123456), "0.123456")
        self.assertEqual(format_price(0.00005342), "0.00005342")
        self.assertEqual(format_price(0.00005300), "0.000053")
        self.assertEqual(format_price(0.00005000), "0.00005")
        
    def test_precise_divide(self):
        """Test precise division"""
        result = precise_divide(10, 3)
        self.assertIsInstance(result, Decimal)
        self.assertEqual(str(result), "3.333333333333333333333333333")
        
    def test_precise_multiply(self):
        """Test precise multiplication"""
        result = precise_multiply(0.00005342, 0.99)
        self.assertIsInstance(result, Decimal)
        # Should be approximately 0.0000528858
        self.assertAlmostEqual(float(result), 0.0000528858, places=10)
        
    def test_precise_add(self):
        """Test precise addition"""
        result = precise_add(0.00005342, 0.000001)
        self.assertIsInstance(result, Decimal)
        self.assertEqual(str(result), "0.00005442")
        
    def test_precise_subtract(self):
        """Test precise subtraction"""
        result = precise_subtract(0.00005342, 0.000001)
        self.assertIsInstance(result, Decimal)
        self.assertEqual(str(result), "0.00005242")


if __name__ == '__main__':
    unittest.main()