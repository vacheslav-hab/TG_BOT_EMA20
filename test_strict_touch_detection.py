#!/usr/bin/env python3
"""
Test script for the strict touch detection implementation.
"""

import pandas as pd
import sys
import os
from datetime import datetime, timezone, timedelta

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from strategy import detect_touch_current_strict, get_ema_last_closed
from utils import iso_to_dt, now_utc


def test_strict_touch_detection():
    """
    Test the strict touch detection function with various scenarios.
    """
    print("Testing strict touch detection...")
    
    # Create test data with recent timestamps (within 3 hours)
    timestamps = []
    base_time = datetime.now(timezone.utc) - timedelta(minutes=90)  # 1.5 hours ago
    for i in range(25):
        ts = (base_time + timedelta(minutes=i*5)).isoformat().replace("+00:00", "Z")
        timestamps.append(ts)
    
    # Create DataFrame with EMA touch scenario
    # Make the last few candles touch the EMA value
    data = {
        'timestamp': timestamps,
        'open': [2600 + i*10 for i in range(25)],
        'high': [2620 + i*10 for i in range(23)] + [2760, 2770],  # Last two touch EMA
        'low': [2590 + i*10 for i in range(23)] + [2740, 2750],   # Last two touch EMA
        'close': [2610 + i*10 for i in range(23)] + [2755, 2765]  # Last two touch EMA
    }
    
    df = pd.DataFrame(data)
    
    # Create EMA series
    closes = df['close'].tolist()
    series = pd.Series(closes)
    ema_series = series.ewm(span=20, adjust=False).mean()
    
    print(f"Created {len(df)} candles")
    print(f"Last candle timestamp: {df.iloc[-1]['timestamp']}")
    print(f"EMA[-2] (last closed): {ema_series.iloc[-2]}")
    print(f"Current candle low: {df.iloc[-1]['low']}")
    print(f"Current candle high: {df.iloc[-1]['high']}")
    
    # Test 1: Normal touch detection
    print("\n--- Test 1: Normal touch detection ---")
    result, data = detect_touch_current_strict(
        "TESTUSDT", df, ema_series,
        bid=None, ask=None,
        last_signal_time={},
        active_positions={}
    )
    
    if result:
        print(f"✅ PASS: Touch detected - {data}")
    else:
        print(f"❌ FAIL: No touch - {data}")
    
    # Test 2: Duplicate signal prevention
    print("\n--- Test 2: Duplicate signal prevention ---")
    last_signal_time = {"TESTUSDT": df.iloc[-1]['timestamp']}
    result, data = detect_touch_current_strict(
        "TESTUSDT", df, ema_series,
        bid=None, ask=None,
        last_signal_time=last_signal_time,
        active_positions={}
    )
    
    if not result and data == "already_signaled_on_this_candle":
        print("✅ PASS: Duplicate signal correctly prevented")
    else:
        print(f"❌ FAIL: Duplicate signal not prevented - {result}, {data}")
    
    # Test 3: Active position prevention
    print("\n--- Test 3: Active position prevention ---")
    result, data = detect_touch_current_strict(
        "TESTUSDT", df, ema_series,
        bid=None, ask=None,
        last_signal_time={},
        active_positions={"TESTUSDT": {}}
    )
    
    if not result and data == "position_already_open":
        print("✅ PASS: Active position correctly prevented signal")
    else:
        print(f"❌ FAIL: Active position not prevented - {result}, {data}")
    
    # Test 4: Old candle rejection
    print("\n--- Test 4: Old candle rejection ---")
    # Create a DataFrame with an old timestamp
    old_timestamps = timestamps.copy()
    old_timestamps[-1] = (datetime.now(timezone.utc) - timedelta(hours=4)).isoformat().replace("+00:00", "Z")
    old_data = {
        'timestamp': old_timestamps,
        'open': [2600 + i*10 for i in range(25)],
        'high': [2620 + i*10 for i in range(23)] + [2760, 2770],
        'low': [2590 + i*10 for i in range(23)] + [2740, 2750],
        'close': [2610 + i*10 for i in range(23)] + [2755, 2765]
    }
    old_df = pd.DataFrame(old_data)
    
    result, data = detect_touch_current_strict(
        "TESTUSDT", old_df, ema_series,
        bid=None, ask=None,
        last_signal_time={},
        active_positions={}
    )
    
    if not result and data == "candle_too_old":
        print("✅ PASS: Old candle correctly rejected")
    else:
        print(f"❌ FAIL: Old candle not rejected - {result}, {data}")
    
    print("\nAll tests completed.")


if __name__ == "__main__":
    test_strict_touch_detection()