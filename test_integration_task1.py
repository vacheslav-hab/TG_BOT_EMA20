#!/usr/bin/env python3
"""
Integration test for Task 1 - Test the complete signal processing flow
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from strategy import (detect_touch, validate_signal_direction, can_generate_signal, 
                     register_signal, StrategyManager)
from decimal import Decimal
from datetime import datetime, timezone

def test_complete_signal_flow():
    """Test the complete signal processing flow as it would work in main.py"""
    print("Testing complete signal processing flow...")
    
    # Mock market data - closed candle
    symbol = "BTCUSDT"
    last_closed_candle = {
        'high': 50200.0,
        'low': 49800.0,
        'close': 50100.0,  # Above EMA20
        'open': 49900.0,
        'timestamp': "2024-01-01T12:00:00Z"
    }
    
    # Mock EMA values
    ema20_current = 50000.0  # Current EMA20
    ema20_previous = 49995.0  # Previous EMA20 (slight upward slope)
    
    print(f"Testing {symbol} with candle: {last_closed_candle}")
    print(f"EMA20 current: {ema20_current}, previous: {ema20_previous}")
    
    # Step 1: Check for EMA20 touch
    touched = detect_touch(last_closed_candle, ema20_current)
    print(f"Step 1 - EMA20 touch detected: {touched}")
    
    if not touched:
        print("No touch detected, signal flow stops here")
        return False
    
    # Step 2: Determine potential signal direction
    last_closed_close = Decimal(str(last_closed_candle['close']))
    potential_direction = "LONG" if last_closed_close > Decimal(str(ema20_current)) else "SHORT"
    print(f"Step 2 - Potential direction: {potential_direction}")
    
    # Step 3: Validate signal direction
    direction_valid = validate_signal_direction(
        last_closed_candle, ema20_current, ema20_previous, potential_direction
    )
    print(f"Step 3 - Direction validation: {direction_valid}")
    
    if not direction_valid:
        print("Direction validation failed, signal flow stops here")
        return False
    
    # Step 4: Check signal deduplication
    can_generate = can_generate_signal(symbol, last_closed_candle['timestamp'])
    print(f"Step 4 - Can generate signal: {can_generate}")
    
    if not can_generate:
        print("Signal blocked by deduplication, signal flow stops here")
        return False
    
    # Step 5: Register signal (simulate signal creation)
    register_signal(symbol, last_closed_candle['timestamp'])
    print(f"Step 5 - Signal registered for {symbol}")
    
    # Step 6: Verify deduplication works for same candle
    can_generate_again = can_generate_signal(symbol, last_closed_candle['timestamp'])
    print(f"Step 6 - Can generate same candle again: {can_generate_again} (should be False)")
    
    # Step 7: Verify new candle allows signal
    new_candle_time = "2024-01-01T13:00:00Z"
    can_generate_new = can_generate_signal(symbol, new_candle_time)
    print(f"Step 7 - Can generate for new candle: {can_generate_new} (should be True)")
    
    success = (touched and direction_valid and can_generate and 
               not can_generate_again and can_generate_new)
    
    print(f"\nComplete flow test: {'PASS' if success else 'FAIL'}")
    return success

def test_edge_cases():
    """Test edge cases for the signal processing"""
    print("\nTesting edge cases...")
    
    # Test case 1: EMA slope exactly at tolerance boundary for LONG
    candle = {'close': 50100.0}
    ema_current = 50000.0
    ema_previous = 50005.0  # Exactly -0.01% slope
    
    # Calculate exact slope: (50000 - 50005) / 50005 = -0.0001 = -0.01%
    result1 = validate_signal_direction(candle, ema_current, ema_previous, "LONG")
    print(f"Edge case 1 - LONG at exact slope boundary: {result1} (should be True)")
    
    # Test case 2: EMA slope just beyond tolerance for LONG
    ema_previous_bad = 50006.0  # Slightly steeper decline
    result2 = validate_signal_direction(candle, ema_current, ema_previous_bad, "LONG")
    print(f"Edge case 2 - LONG beyond slope tolerance: {result2} (should be False)")
    
    # Test case 3: Price exactly at EMA (edge case)
    candle_edge = {'close': 50000.0}  # Exactly at EMA
    result3 = validate_signal_direction(candle_edge, ema_current, ema_previous, "LONG")
    print(f"Edge case 3 - Price exactly at EMA for LONG: {result3} (should be False)")
    
    return result1 and not result2 and not result3

def main():
    """Run integration tests"""
    print("=" * 70)
    print("Integration Test for Task 1 - EMA20 Touch Detection and Signal Timing")
    print("=" * 70)
    
    test1_passed = test_complete_signal_flow()
    test2_passed = test_edge_cases()
    
    print("\n" + "=" * 70)
    print("Integration Test Results:")
    print(f"Complete signal flow: {'PASS' if test1_passed else 'FAIL'}")
    print(f"Edge cases: {'PASS' if test2_passed else 'FAIL'}")
    
    all_passed = test1_passed and test2_passed
    print(f"\nOverall: {'ALL INTEGRATION TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")
    print("=" * 70)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())