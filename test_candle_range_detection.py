#!/usr/bin/env python3
"""Test TP/SL detection using candle high/low ranges"""

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
    if direction == "LONG":
        sl_price = entry_price * 0.99    # -1%
        tp1_price = entry_price * 1.015  # +1.5%
        tp2_price = entry_price * 1.03   # +3%
    else:  # SHORT
        sl_price = entry_price * 1.01    # +1%
        tp1_price = entry_price * 0.985  # -1.5%
        tp2_price = entry_price * 0.97   # -3%
    
    return {
        "signal_id": signal_id,
        "symbol": symbol,
        "direction": direction,
        "entry_price": entry_price,
        "sl_price": sl_price,
        "tp1_price": tp1_price,
        "tp2_price": tp2_price,
        "status": "OPEN",
        "created_at": "2024-01-01T12:00:00Z",
        "entry_candle_time": entry_candle_time,
        "monitor_from": monitor_from,
        "partial_hit": False
    }


def test_long_tp1_detection():
    """Test TP1 detection for LONG position using candle high"""
    print("Testing LONG TP1 detection using candle high...")
    
    # Clean up test data
    json_manager = JSONDataManager()
    data = json_manager.load_data()
    data["positions"] = {}
    json_manager.save_data(data)
    
    # Create LONG signal: Entry 50000, TP1 50750, TP2 51500, SL 49500
    signal_id = "test-long-tp1"
    test_signal = create_test_signal(
        signal_id, "BTCUSDT", "LONG", 50000.0,
        "2024-01-01T12:00:00Z",  # entry_candle_time
        "2024-01-01T13:00:00Z"   # monitor_from
    )
    
    print(f"LONG Signal levels: Entry={test_signal['entry_price']}, TP1={test_signal['tp1_price']}, TP2={test_signal['tp2_price']}, SL={test_signal['sl_price']}")
    
    # Store signal in JSON
    data["positions"][signal_id] = test_signal
    json_manager.save_data(data)
    
    position_manager = PositionManager()
    
    # Create market data with candle that hits TP1 via high
    market_data = {
        'tickers': {
            'BTCUSDT': {'last': 50500.0}
        },
        'ohlcv': {
            'BTCUSDT': [
                {
                    'timestamp': "2024-01-01T13:00:00Z",  # At monitor_from
                    'high': 50800.0,    # Above TP1 (50750)
                    'low': 50200.0,     # Above entry
                    'open': 50300.0,
                    'close': 50500.0
                },
                {  # Current active candle (should be ignored)
                    'timestamp': "2024-01-01T14:00:00Z",
                    'high': 50600.0,
                    'low': 50400.0,
                    'open': 50500.0,
                    'close': 50550.0
                }
            ]
        }
    }
    
    # Monitor positions
    updates = position_manager.monitor_all_positions(market_data)
    
    assert len(updates) == 1, f"Expected 1 update, got {len(updates)}"
    
    update = updates[0]
    print(f"Update: {update.triggered_level} @ {update.current_price}, Status: {update.old_status} -> {update.new_status}")
    
    assert update.triggered_level == "TP1", f"Expected TP1, got {update.triggered_level}"
    assert update.new_status == "PARTIAL", f"Expected PARTIAL, got {update.new_status}"
    assert update.current_price == test_signal['tp1_price'], f"Expected TP1 price {test_signal['tp1_price']}, got {update.current_price}"
    
    print("✅ LONG TP1 detection using candle high works correctly")
    return True


def test_short_tp1_detection():
    """Test TP1 detection for SHORT position using candle low"""
    print("\nTesting SHORT TP1 detection using candle low...")
    
    # Clean up test data
    json_manager = JSONDataManager()
    data = json_manager.load_data()
    data["positions"] = {}
    json_manager.save_data(data)
    
    # Create SHORT signal: Entry 50000, TP1 49250, TP2 48500, SL 50500
    signal_id = "test-short-tp1"
    test_signal = create_test_signal(
        signal_id, "BTCUSDT", "SHORT", 50000.0,
        "2024-01-01T12:00:00Z",  # entry_candle_time
        "2024-01-01T13:00:00Z"   # monitor_from
    )
    
    print(f"SHORT Signal levels: Entry={test_signal['entry_price']}, TP1={test_signal['tp1_price']}, TP2={test_signal['tp2_price']}, SL={test_signal['sl_price']}")
    
    # Store signal in JSON
    data["positions"][signal_id] = test_signal
    json_manager.save_data(data)
    
    position_manager = PositionManager()
    
    # Create market data with candle that hits TP1 via low
    market_data = {
        'tickers': {
            'BTCUSDT': {'last': 49500.0}
        },
        'ohlcv': {
            'BTCUSDT': [
                {
                    'timestamp': "2024-01-01T13:00:00Z",  # At monitor_from
                    'high': 49800.0,    # Below entry
                    'low': 49200.0,     # Below TP1 (49250)
                    'open': 49700.0,
                    'close': 49500.0
                },
                {  # Current active candle (should be ignored)
                    'timestamp': "2024-01-01T14:00:00Z",
                    'high': 49600.0,
                    'low': 49400.0,
                    'open': 49500.0,
                    'close': 49450.0
                }
            ]
        }
    }
    
    # Monitor positions
    updates = position_manager.monitor_all_positions(market_data)
    
    assert len(updates) == 1, f"Expected 1 update, got {len(updates)}"
    
    update = updates[0]
    print(f"Update: {update.triggered_level} @ {update.current_price}, Status: {update.old_status} -> {update.new_status}")
    
    assert update.triggered_level == "TP1", f"Expected TP1, got {update.triggered_level}"
    assert update.new_status == "PARTIAL", f"Expected PARTIAL, got {update.new_status}"
    assert update.current_price == test_signal['tp1_price'], f"Expected TP1 price {test_signal['tp1_price']}, got {update.current_price}"
    
    print("✅ SHORT TP1 detection using candle low works correctly")
    return True


def test_multiple_levels_same_candle():
    """Test multiple TP/SL level hits within the same candle"""
    print("\nTesting multiple level hits in same candle...")
    
    # Clean up test data
    json_manager = JSONDataManager()
    data = json_manager.load_data()
    data["positions"] = {}
    json_manager.save_data(data)
    
    # Create LONG signal
    signal_id = "test-multiple-levels"
    test_signal = create_test_signal(
        signal_id, "BTCUSDT", "LONG", 50000.0,
        "2024-01-01T12:00:00Z",  # entry_candle_time
        "2024-01-01T13:00:00Z"   # monitor_from
    )
    
    print(f"LONG Signal levels: Entry={test_signal['entry_price']}, TP1={test_signal['tp1_price']}, TP2={test_signal['tp2_price']}, SL={test_signal['sl_price']}")
    
    # Store signal in JSON
    data["positions"][signal_id] = test_signal
    json_manager.save_data(data)
    
    position_manager = PositionManager()
    
    # Create market data with candle that hits both TP1 and TP2
    market_data = {
        'tickers': {
            'BTCUSDT': {'last': 51000.0}
        },
        'ohlcv': {
            'BTCUSDT': [
                {
                    'timestamp': "2024-01-01T13:00:00Z",  # At monitor_from
                    'high': 51600.0,    # Above TP2 (51500) and TP1 (50750)
                    'low': 50200.0,     # Above entry
                    'open': 50300.0,
                    'close': 51000.0
                },
                {  # Current active candle (should be ignored)
                    'timestamp': "2024-01-01T14:00:00Z",
                    'high': 51100.0,
                    'low': 50900.0,
                    'open': 51000.0,
                    'close': 51050.0
                }
            ]
        }
    }
    
    # Monitor positions
    updates = position_manager.monitor_all_positions(market_data)
    
    print(f"Number of updates: {len(updates)}")
    for i, update in enumerate(updates):
        print(f"Update {i+1}: {update.triggered_level} @ {update.current_price}, Status: {update.old_status} -> {update.new_status}")
    
    # Should trigger TP2 directly (since TP2 is checked first and both levels are hit)
    assert len(updates) == 1, f"Expected 1 update (TP2), got {len(updates)}"
    
    update = updates[0]
    assert update.triggered_level == "TP2", f"Expected TP2 (checked first), got {update.triggered_level}"
    assert update.new_status == "CLOSED", f"Expected CLOSED, got {update.new_status}"
    
    print("✅ Multiple level detection works correctly (TP2 prioritized)")
    return True


def test_sl_detection():
    """Test SL detection using candle low for LONG position"""
    print("\nTesting SL detection using candle low...")
    
    # Clean up test data
    json_manager = JSONDataManager()
    data = json_manager.load_data()
    data["positions"] = {}
    json_manager.save_data(data)
    
    # Create LONG signal
    signal_id = "test-sl"
    test_signal = create_test_signal(
        signal_id, "BTCUSDT", "LONG", 50000.0,
        "2024-01-01T12:00:00Z",  # entry_candle_time
        "2024-01-01T13:00:00Z"   # monitor_from
    )
    
    print(f"LONG Signal levels: Entry={test_signal['entry_price']}, TP1={test_signal['tp1_price']}, TP2={test_signal['tp2_price']}, SL={test_signal['sl_price']}")
    
    # Store signal in JSON
    data["positions"][signal_id] = test_signal
    json_manager.save_data(data)
    
    position_manager = PositionManager()
    
    # Create market data with candle that hits SL via low
    market_data = {
        'tickers': {
            'BTCUSDT': {'last': 49800.0}
        },
        'ohlcv': {
            'BTCUSDT': [
                {
                    'timestamp': "2024-01-01T13:00:00Z",  # At monitor_from
                    'high': 50200.0,    # Below entry
                    'low': 49400.0,     # Below SL (49500)
                    'open': 50000.0,
                    'close': 49800.0
                },
                {  # Current active candle (should be ignored)
                    'timestamp': "2024-01-01T14:00:00Z",
                    'high': 49900.0,
                    'low': 49700.0,
                    'open': 49800.0,
                    'close': 49850.0
                }
            ]
        }
    }
    
    # Monitor positions
    updates = position_manager.monitor_all_positions(market_data)
    
    assert len(updates) == 1, f"Expected 1 update, got {len(updates)}"
    
    update = updates[0]
    print(f"Update: {update.triggered_level} @ {update.current_price}, Status: {update.old_status} -> {update.new_status}")
    
    assert update.triggered_level == "SL", f"Expected SL, got {update.triggered_level}"
    assert update.new_status == "CLOSED", f"Expected CLOSED, got {update.new_status}"
    assert update.current_price == test_signal['sl_price'], f"Expected SL price {test_signal['sl_price']}, got {update.current_price}"
    
    print("✅ SL detection using candle low works correctly")
    return True


def main():
    """Run all tests"""
    print("Running candle range TP/SL detection tests...\n")
    
    try:
        success1 = test_long_tp1_detection()
        success2 = test_short_tp1_detection()
        success3 = test_multiple_levels_same_candle()
        success4 = test_sl_detection()
        
        if success1 and success2 and success3 and success4:
            print("\n🎉 All candle range TP/SL detection tests passed!")
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