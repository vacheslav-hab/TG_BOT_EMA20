#!/usr/bin/env python3
"""Test monitor_from field implementation in signal creation"""

import asyncio
import sys
import os
from datetime import datetime, timezone, timedelta
from decimal import Decimal

# Add current directory to path for imports
sys.path.insert(0, os.getcwd())

from strategy import create_signal_atomic, _next_candle_time_iso, _to_utc_dt, TF_SECONDS
from json_manager import JSONDataManager


async def test_monitor_from_calculation():
    """Test that monitor_from is correctly calculated as entry_candle_time + 1h"""
    print("Testing monitor_from calculation...")
    
    # Test case 1: ISO string timestamp
    entry_candle_time_iso = "2024-01-01T12:00:00Z"
    expected_monitor_from = "2024-01-01T13:00:00Z"
    
    actual_monitor_from = _next_candle_time_iso(entry_candle_time_iso)
    
    print(f"Entry candle time: {entry_candle_time_iso}")
    print(f"Expected monitor_from: {expected_monitor_from}")
    print(f"Actual monitor_from: {actual_monitor_from}")
    
    assert actual_monitor_from == expected_monitor_from, f"Expected {expected_monitor_from}, got {actual_monitor_from}"
    
    # Test case 2: Epoch timestamp
    entry_epoch = 1704110400  # 2024-01-01T12:00:00Z
    entry_dt = datetime.fromtimestamp(entry_epoch, tz=timezone.utc)
    entry_iso = entry_dt.isoformat().replace("+00:00", "Z")
    expected_monitor_from_2 = "2024-01-01T13:00:00Z"
    
    actual_monitor_from_2 = _next_candle_time_iso(entry_iso)
    
    print(f"\nEpoch test:")
    print(f"Entry epoch: {entry_epoch}")
    print(f"Entry ISO: {entry_iso}")
    print(f"Expected monitor_from: {expected_monitor_from_2}")
    print(f"Actual monitor_from: {actual_monitor_from_2}")
    
    assert actual_monitor_from_2 == expected_monitor_from_2, f"Expected {expected_monitor_from_2}, got {actual_monitor_from_2}"
    
    print("✅ monitor_from calculation tests passed!")


async def test_signal_creation_with_monitor_from():
    """Test that create_signal_atomic properly sets monitor_from field"""
    print("\nTesting signal creation with monitor_from...")
    
    # Clean up any existing test data
    json_manager = JSONDataManager()
    data = json_manager.load_data()
    if "positions" in data:
        data["positions"] = {}
    if "metadata" not in data:
        data["metadata"] = {}
    data["metadata"]["last_signal_candle"] = {}
    json_manager.save_data(data)
    
    # Test signal creation
    symbol = "BTCUSDT"
    direction = "LONG"
    entry = Decimal("50000.0")
    ema_value = Decimal("49950.0")
    entry_candle_time = "2024-01-01T12:00:00Z"
    
    signal = await create_signal_atomic(symbol, direction, entry, ema_value, entry_candle_time)
    
    if signal is None:
        print("❌ Signal creation returned None")
        return False
    
    print(f"Created signal: {signal['signal_id']}")
    print(f"Entry candle time: {signal.get('entry_candle_time')}")
    print(f"Monitor from: {signal.get('monitor_from')}")
    
    # Verify monitor_from is set correctly
    expected_monitor_from = "2024-01-01T13:00:00Z"
    actual_monitor_from = signal.get('monitor_from')
    
    assert actual_monitor_from == expected_monitor_from, f"Expected monitor_from {expected_monitor_from}, got {actual_monitor_from}"
    
    # Verify entry_candle_time is stored
    assert signal.get('entry_candle_time') == entry_candle_time, f"Entry candle time not stored correctly"
    
    print("✅ Signal creation with monitor_from test passed!")
    return True


async def test_time_difference():
    """Test that monitor_from is exactly 1 hour after entry_candle_time"""
    print("\nTesting time difference between entry_candle_time and monitor_from...")
    
    entry_candle_time = "2024-01-01T12:30:45Z"
    monitor_from = _next_candle_time_iso(entry_candle_time)
    
    entry_dt = _to_utc_dt(entry_candle_time)
    monitor_dt = _to_utc_dt(monitor_from)
    
    time_diff = monitor_dt - entry_dt
    expected_diff = timedelta(seconds=TF_SECONDS)  # 1 hour
    
    print(f"Entry time: {entry_dt}")
    print(f"Monitor time: {monitor_dt}")
    print(f"Time difference: {time_diff}")
    print(f"Expected difference: {expected_diff}")
    
    assert time_diff == expected_diff, f"Expected {expected_diff}, got {time_diff}"
    
    print("✅ Time difference test passed!")


async def main():
    """Run all tests"""
    print("Running monitor_from implementation tests...\n")
    
    try:
        await test_monitor_from_calculation()
        await test_time_difference()
        success = await test_signal_creation_with_monitor_from()
        
        if success:
            print("\n🎉 All monitor_from implementation tests passed!")
            return True
        else:
            print("\n❌ Some tests failed!")
            return False
            
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)