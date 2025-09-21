#!/usr/bin/env python3
"""
Test script for Task 1 implementation - EMA20 touch detection and signal timing
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from strategy import detect_touch, validate_signal_direction, can_generate_signal, register_signal
from datetime import datetime, timezone

def test_detect_touch():
    """Test the updated detect_touch function"""
    print("Testing detect_touch function...")
    
    # Test case 1: EMA20 within candle range (should detect touch)
    candle1 = {
        'high': 50000.0,
        'low': 49000.0,
        'close': 49500.0,
        'open': 49200.0
    }
    ema_value1 = 49800.0  # Within range
    
    result1 = detect_touch(candle1, ema_value1)
    print(f"Test 1 - EMA within range: {result1} (expected: True)")
    
    # Test case 2: EMA20 outside candle range (should not detect touch)
    candle2 = {
        'high': 50000.0,
        'low': 49000.0,
        'close': 49500.0,
        'open': 49200.0
    }
    ema_value2 = 51000.0  # Outside range
    
    result2 = detect_touch(candle2, ema_value2)
    print(f"Test 2 - EMA outside range: {result2} (expected: False)")
    
    # Test case 3: EMA20 at edge with tolerance (should detect touch)
    candle3 = {
        'high': 50000.0,
        'low': 49000.0,
        'close': 49500.0,
        'open': 49200.0
    }
    ema_value3 = 50250.0  # Just outside high but within 0.5% tolerance
    
    result3 = detect_touch(candle3, ema_value3)
    print(f"Test 3 - EMA at edge with tolerance: {result3} (expected: True)")
    
    return all([result1, not result2, result3])

def test_validate_signal_direction():
    """Test the signal direction validation function"""
    print("\nTesting validate_signal_direction function...")
    
    # Test case 1: Valid LONG signal (price above EMA, EMA slope >= -0.01%)
    candle1 = {'close': 50100.0}
    ema_current1 = 50000.0
    ema_previous1 = 49990.0  # Slight upward slope
    
    result1 = validate_signal_direction(candle1, ema_current1, ema_previous1, "LONG")
    print(f"Test 1 - Valid LONG: {result1} (expected: True)")
    
    # Test case 2: Invalid LONG signal (price below EMA)
    candle2 = {'close': 49900.0}
    ema_current2 = 50000.0
    ema_previous2 = 49990.0
    
    result2 = validate_signal_direction(candle2, ema_current2, ema_previous2, "LONG")
    print(f"Test 2 - Invalid LONG (price below EMA): {result2} (expected: False)")
    
    # Test case 3: Valid SHORT signal (price below EMA, EMA slope <= +0.01%)
    candle3 = {'close': 49900.0}
    ema_current3 = 50000.0
    ema_previous3 = 50010.0  # Slight downward slope
    
    result3 = validate_signal_direction(candle3, ema_current3, ema_previous3, "SHORT")
    print(f"Test 3 - Valid SHORT: {result3} (expected: True)")
    
    # Test case 4: Invalid SHORT signal (EMA slope too steep upward)
    candle4 = {'close': 49900.0}
    ema_current4 = 50000.0
    ema_previous4 = 49900.0  # Too steep upward slope (>0.01%)
    
    result4 = validate_signal_direction(candle4, ema_current4, ema_previous4, "SHORT")
    print(f"Test 4 - Invalid SHORT (steep upward EMA): {result4} (expected: False)")
    
    return all([result1, not result2, result3, not result4])

def test_signal_deduplication():
    """Test the signal deduplication mechanism"""
    print("\nTesting signal deduplication...")
    
    symbol = "BTCUSDT"
    candle_time1 = "2024-01-01T12:00:00Z"
    candle_time2 = "2024-01-01T13:00:00Z"
    
    # Test case 1: First signal should be allowed
    result1 = can_generate_signal(symbol, candle_time1)
    print(f"Test 1 - First signal: {result1} (expected: True)")
    
    # Register the signal
    register_signal(symbol, candle_time1)
    
    # Test case 2: Same candle should be blocked
    result2 = can_generate_signal(symbol, candle_time1)
    print(f"Test 2 - Same candle blocked: {result2} (expected: False)")
    
    # Test case 3: Different candle should be allowed
    result3 = can_generate_signal(symbol, candle_time2)
    print(f"Test 3 - Different candle allowed: {result3} (expected: True)")
    
    return all([result1, not result2, result3])

def main():
    """Run all tests"""
    print("=" * 60)
    print("Testing Task 1 Implementation")
    print("=" * 60)
    
    test1_passed = test_detect_touch()
    test2_passed = test_validate_signal_direction()
    test3_passed = test_signal_deduplication()
    
    print("\n" + "=" * 60)
    print("Test Results:")
    print(f"detect_touch: {'PASS' if test1_passed else 'FAIL'}")
    print(f"validate_signal_direction: {'PASS' if test2_passed else 'FAIL'}")
    print(f"signal_deduplication: {'PASS' if test3_passed else 'FAIL'}")
    
    all_passed = test1_passed and test2_passed and test3_passed
    print(f"\nOverall: {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")
    print("=" * 60)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())