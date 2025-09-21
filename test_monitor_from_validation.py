#!/usr/bin/env python3
"""Test monitor_from validation in position monitoring"""

import asyncio
import sys
import os
from datetime import datetime, timezone, timedelta
from decimal import Decimal

# Add current directory to path for imports
sys.path.insert(0, os.getcwd())

from position_manager import PositionManager
from json_manager import JSONDataManager


def create_test_signal(signal_id, symbol, direction, entry_price, entry_candle_time, monitor_from):
    """Create a test signal with monitor_from field"""
    return {
        "signal_id": signal_id,
        "symbol": symbol,
        "direction": direction,
        "entry_price": entry_price,
        "sl_price": entry_price * 0.99 if direction == "LONG" else entry_price * 1.01,
        "tp1_price": entry_price * 1.015 if direction == "LONG" else entry_price * 0.985,
        "tp2_price": entry_price * 1.03 if direction == "LONG" else entry_price * 0.97,
        "status": "OPEN",
        "created_at": "2024-01-01T12:00:00Z",
        "entry_candle_time": entry_candle_time,
        "monitor_from": monitor_from,
        "partial_hit": False
    }


def test_monitor_from_validation():
    """Test that update_signal respects monitor_from timing"""
    print("Testing monitor_from validation in update_signal...")
    
    position_manager = PositionManager()
    
    # Test case 1: Candle time before monitor_from (should return None)
    signal = create_test_signal(
        "test-1", "BTCUSDT", "LONG", 50000.0,
        "2024-01-01T12:00:00Z",  # entry_candle_time
        "2024-01-01T13:00:00Z"   # monitor_from (1 hour later)
    )
    
    # Set current_candle_time to before monitor_from
    signal["current_candle_time"] = "2024-01-01T12:30:00Z"  # 30 minutes after entry, but before monitor_from
    
    # Try to trigger TP1 - should be ignored due to monitor_from
    tp1_price = signal["tp1_price"]
    result = position_manager.update_signal(signal, tp1_price + 100)  # Price well above TP1
    
    print(f"Test 1 - Candle before monitor_from:")
    print(f"  Entry candle: {signal['entry_candle_time']}")
    print(f"  Monitor from: {signal['monitor_from']}")
    print(f"  Current candle: {signal['current_candle_time']}")
    print(f"  Result: {result}")
    
    assert result is None, f"Expected None (monitoring not started), got {result}"
    print("  ✅ Correctly ignored candle before monitor_from")
    
    # Test case 2: Candle time at monitor_from (should process)
    signal2 = create_test_signal(
        "test-2", "BTCUSDT", "LONG", 50000.0,
        "2024-01-01T12:00:00Z",  # entry_candle_time
        "2024-01-01T13:00:00Z"   # monitor_from
    )
    
    # Set current_candle_time to exactly monitor_from
    signal2["current_candle_time"] = "2024-01-01T13:00:00Z"
    
    # Try to trigger TP1 - should work now
    tp1_price = signal2["tp1_price"]
    result2 = position_manager.update_signal(signal2, tp1_price + 100)
    
    print(f"\nTest 2 - Candle at monitor_from:")
    print(f"  Entry candle: {signal2['entry_candle_time']}")
    print(f"  Monitor from: {signal2['monitor_from']}")
    print(f"  Current candle: {signal2['current_candle_time']}")
    print(f"  Result status: {result2['status'] if result2 else None}")
    
    assert result2 is not None, "Expected signal update, got None"
    assert result2["status"] == "PARTIAL", f"Expected PARTIAL status, got {result2['status']}"
    print("  ✅ Correctly processed candle at monitor_from")
    
    # Test case 3: Candle time after monitor_from (should process)
    signal3 = create_test_signal(
        "test-3", "BTCUSDT", "LONG", 50000.0,
        "2024-01-01T12:00:00Z",  # entry_candle_time
        "2024-01-01T13:00:00Z"   # monitor_from
    )
    
    # Set current_candle_time to after monitor_from
    signal3["current_candle_time"] = "2024-01-01T14:00:00Z"  # 1 hour after monitor_from
    
    # Try to trigger TP1 - should work
    tp1_price = signal3["tp1_price"]
    result3 = position_manager.update_signal(signal3, tp1_price + 100)
    
    print(f"\nTest 3 - Candle after monitor_from:")
    print(f"  Entry candle: {signal3['entry_candle_time']}")
    print(f"  Monitor from: {signal3['monitor_from']}")
    print(f"  Current candle: {signal3['current_candle_time']}")
    print(f"  Result status: {result3['status'] if result3 else None}")
    
    assert result3 is not None, "Expected signal update, got None"
    assert result3["status"] == "PARTIAL", f"Expected PARTIAL status, got {result3['status']}"
    print("  ✅ Correctly processed candle after monitor_from")
    
    print("\n🎉 All monitor_from validation tests passed!")
    return True


def test_monitor_all_positions_timing():
    """Test that monitor_all_positions respects monitor_from timing"""
    print("\nTesting monitor_from validation in monitor_all_positions...")
    
    # Clean up test data
    json_manager = JSONDataManager()
    data = json_manager.load_data()
    data["positions"] = {}
    json_manager.save_data(data)
    
    # Create a test signal in JSON storage
    signal_id = "test-monitor-all"
    test_signal = create_test_signal(
        signal_id, "BTCUSDT", "LONG", 50000.0,
        "2024-01-01T12:00:00Z",  # entry_candle_time
        "2024-01-01T13:00:00Z"   # monitor_from
    )
    
    # Store signal in JSON
    data["positions"][signal_id] = test_signal
    json_manager.save_data(data)
    
    position_manager = PositionManager()
    
    # Create market data with candles before monitor_from
    market_data = {
        'tickers': {
            'BTCUSDT': {'last': 51000.0}  # Above TP1
        },
        'ohlcv': {
            'BTCUSDT': [
                {
                    'timestamp': "2024-01-01T12:30:00Z",  # Before monitor_from
                    'high': 51000.0,  # Above TP1
                    'low': 49000.0,
                    'open': 50000.0,
                    'close': 50500.0
                },
                {
                    'timestamp': "2024-01-01T13:30:00Z",  # After monitor_from
                    'high': 51000.0,  # Above TP1
                    'low': 49000.0,
                    'open': 50500.0,
                    'close': 50800.0
                },
                {  # Current active candle (should be ignored)
                    'timestamp': "2024-01-01T14:00:00Z",
                    'high': 51200.0,
                    'low': 50800.0,
                    'open': 50800.0,
                    'close': 51000.0
                }
            ]
        }
    }
    
    # Monitor positions - should only process the candle after monitor_from
    updates = position_manager.monitor_all_positions(market_data)
    
    print(f"Number of position updates: {len(updates)}")
    
    if updates:
        update = updates[0]
        print(f"Update triggered level: {update.triggered_level}")
        print(f"Update new status: {update.new_status}")
        
        # Should have triggered TP1 from the second candle (after monitor_from)
        assert update.triggered_level == "TP1", f"Expected TP1, got {update.triggered_level}"
        assert update.new_status == "PARTIAL", f"Expected PARTIAL, got {update.new_status}"
        print("  ✅ Correctly processed only candles after monitor_from")
    else:
        print("  ❌ No updates generated - this might indicate an issue")
        return False
    
    print("\n🎉 monitor_all_positions timing test passed!")
    return True


def main():
    """Run all tests"""
    print("Running monitor_from validation tests...\n")
    
    try:
        success1 = test_monitor_from_validation()
        success2 = test_monitor_all_positions_timing()
        
        if success1 and success2:
            print("\n🎉 All monitor_from validation tests passed!")
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
    success = main()
    sys.exit(0 if success else 1)