#!/usr/bin/env python3
"""
Test script to verify the timestamp fix for numpy.float64 replace error.
"""

import pandas as pd
import sys
import os
import numpy as np
from datetime import datetime, timezone

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils import iso_to_dt, now_utc


def test_timestamp_conversion():
    """
    Test timestamp conversion with different input types including numpy.float64.
    """
    print("Testing timestamp conversion...")
    
    # Test cases
    test_cases = [
        # Integer timestamp (seconds)
        1704110400,
        # Integer timestamp (milliseconds)
        1704110400000,
        # Float timestamp (seconds)
        1704110400.0,
        # Float timestamp (milliseconds)
        1704110400000.0,
        # Numpy float64 timestamp (seconds)
        np.float64(1704110400),
        # Numpy float64 timestamp (milliseconds)
        np.float64(1704110400000),
        # ISO string
        "2024-01-01T12:00:00Z",
        # ISO string without Z
        "2024-01-01T12:00:00"
    ]
    
    for i, timestamp in enumerate(test_cases):
        try:
            print(f"\nTest {i+1}: {type(timestamp).__name__} - {timestamp}")
            result = iso_to_dt(timestamp)
            print(f"  ✅ Success: {result}")
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    print("\nAll tests completed.")


def test_position_manager_fix():
    """
    Test the specific fix in position_manager.py for handling numpy.float64 timestamps.
    """
    print("\nTesting position manager timestamp handling...")
    
    # Simulate the problematic scenario
    candle_time = np.float64(1704110400000)  # Milliseconds timestamp as numpy.float64
    
    try:
        # This should not raise an error anymore
        if isinstance(candle_time, (int, float)):
            candle_iso = datetime.fromtimestamp(int(candle_time), tz=timezone.utc).isoformat().replace("+00:00", "Z")
            print(f"  ✅ Numeric timestamp conversion: {candle_iso}")
        else:
            # This line was causing the error before the fix
            candle_iso = datetime.fromisoformat(str(candle_time).replace('Z','')).replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
            print(f"  ✅ String timestamp conversion: {candle_iso}")
    except Exception as e:
        print(f"  ❌ Error in timestamp handling: {e}")
    
    print("Position manager test completed.")


if __name__ == "__main__":
    test_timestamp_conversion()
    test_position_manager_fix()