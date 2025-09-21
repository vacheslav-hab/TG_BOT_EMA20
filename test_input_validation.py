#!/usr/bin/env python3
"""Test input validation for PnL calculations"""

import sys
import os
import math
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from position_manager import PositionManager, _validate_price_input

def test_price_input_validation():
    """Test price input validation function"""
    print("Testing Price Input Validation")
    print("=" * 50)
    
    # Test valid inputs
    print("\n1. Testing valid inputs:")
    valid_cases = [
        (100.0, "valid_float"),
        (50, "valid_int"),
        (0.01, "small_positive"),
        (999999.99, "large_positive")
    ]
    
    for price, description in valid_cases:
        result = _validate_price_input(price, description)
        print(f"   {description}: {price} -> {result}")
        assert result == True, f"Expected True for {description}"
    
    # Test invalid inputs
    print("\n2. Testing invalid inputs:")
    invalid_cases = [
        (0, "zero"),
        (-100, "negative"),
        (float('inf'), "infinity"),
        (float('-inf'), "negative_infinity"),
        (float('nan'), "nan"),
        ("100", "string"),
        (None, "none"),
        ([], "list")
    ]
    
    for price, description in invalid_cases:
        result = _validate_price_input(price, description)
        print(f"   {description}: {price} -> {result}")
        assert result == False, f"Expected False for {description}"
    
    print("\n✓ All price validation tests passed!")
    return True

def test_pnl_calculation_with_invalid_inputs():
    """Test PnL calculation with invalid inputs"""
    pm = PositionManager()
    
    print("\nTesting PnL Calculation with Invalid Inputs")
    print("=" * 50)
    
    # Test with invalid entry price
    print("\n1. Testing invalid entry price:")
    result = pm.calculate_pnl(-100, [(50750, 0.5)], "LONG")
    print(f"   Negative entry price: {result}% (should be 0.0)")
    assert result == 0.0, "Should return 0.0 for negative entry price"
    
    # Test with invalid exit price
    print("\n2. Testing invalid exit price:")
    result = pm.calculate_pnl(50000, [(float('inf'), 0.5)], "LONG")
    print(f"   Infinite exit price: {result}% (should be 0.0)")
    assert result == 0.0, "Should return 0.0 for infinite exit price"
    
    # Test with invalid direction
    print("\n3. Testing invalid direction:")
    result = pm.calculate_pnl(50000, [(50750, 0.5)], "INVALID")
    print(f"   Invalid direction: {result}% (should be 0.0)")
    assert result == 0.0, "Should return 0.0 for invalid direction"
    
    # Test with invalid weight
    print("\n4. Testing invalid weight:")
    result = pm.calculate_pnl(50000, [(50750, 1.5)], "LONG")  # weight > 1
    print(f"   Weight > 1: {result}% (should be 0.0)")
    assert result == 0.0, "Should return 0.0 for weight > 1"
    
    result = pm.calculate_pnl(50000, [(50750, -0.5)], "LONG")  # negative weight
    print(f"   Negative weight: {result}% (should be 0.0)")
    assert result == 0.0, "Should return 0.0 for negative weight"
    
    # Test with empty exits list
    print("\n5. Testing empty exits list:")
    result = pm.calculate_pnl(50000, [], "LONG")
    print(f"   Empty exits: {result}% (should be 0.0)")
    assert result == 0.0, "Should return 0.0 for empty exits list"
    
    print("\n✓ All invalid input tests passed!")
    return True

def test_pnl_calculation_edge_cases():
    """Test PnL calculation edge cases"""
    pm = PositionManager()
    
    print("\nTesting PnL Calculation Edge Cases")
    print("=" * 50)
    
    # Test with very small prices
    print("\n1. Testing very small prices:")
    result = pm.calculate_pnl(0.001, [(0.0015, 1.0)], "LONG")
    expected = ((0.0015 - 0.001) / 0.001) * 100  # +50%
    print(f"   Small prices: {result}% (expected {expected}%)")
    assert abs(result - expected) < 0.01, f"Expected {expected}, got {result}"
    
    # Test with very large prices
    print("\n2. Testing very large prices:")
    result = pm.calculate_pnl(100000, [(101500, 1.0)], "LONG")
    expected = ((101500 - 100000) / 100000) * 100  # +1.5%
    print(f"   Large prices: {result}% (expected {expected}%)")
    assert abs(result - expected) < 0.01, f"Expected {expected}, got {result}"
    
    # Test with zero weight (should be valid but contribute nothing)
    print("\n3. Testing zero weight:")
    result = pm.calculate_pnl(50000, [(50750, 0.0)], "LONG")
    print(f"   Zero weight: {result}% (should be 0.0)")
    assert result == 0.0, "Should return 0.0 for zero weight"
    
    # Test with multiple exits including zero weight
    print("\n4. Testing mixed weights with zero:")
    result = pm.calculate_pnl(50000, [(50750, 0.5), (51500, 0.0), (49500, 0.5)], "LONG")
    expected = (1.5 * 0.5) + (0 * 0.0) + (-1.0 * 0.5)  # +0.25%
    print(f"   Mixed weights: {result}% (expected {expected}%)")
    assert abs(result - expected) < 0.01, f"Expected {expected}, got {result}"
    
    print("\n✓ All edge case tests passed!")
    return True

if __name__ == "__main__":
    success1 = test_price_input_validation()
    success2 = test_pnl_calculation_with_invalid_inputs()
    success3 = test_pnl_calculation_edge_cases()
    
    if success1 and success2 and success3:
        print("\n🎉 All input validation tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)