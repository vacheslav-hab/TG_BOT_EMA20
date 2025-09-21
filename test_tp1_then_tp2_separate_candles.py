#!/usr/bin/env python3
"""Test TP1 followed by TP2 in separate candles"""

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


def test_tp1_then_tp2_separate_candles():
    """Test TP1 hit in first candle, then TP2 hit in second candle"""
    print("Testing TP1 then TP2 in separate candles...")
    
    # Clean up test data
    json_manager = JSONDataManager()
    data = json_manager.load_data()
    data["positions"] = {}
    json_manager.save_data(data)
    
    # Create LONG signal
    signal_id = "test-tp1-tp2-separate"
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
    
    # First candle: hits TP1 only
    market_data_1 = {
        'tickers': {
            'BTCUSDT': {'last': 50800.0}
        },
        'ohlcv': {
            'BTCUSDT': [
                {
                    'timestamp': "2024-01-01T13:00:00Z",  # At monitor_from
                    'high': 50800.0,    # Above TP1 (50750) but below TP2 (51500)
                    'low': 50200.0,     # Above entry
                    'open': 50300.0,
                    'close': 50600.0
                },
                {  # Current active candle (should be ignored)
                    'timestamp': "2024-01-01T14:00:00Z",
                    'high': 50900.0,
                    'low': 50600.0,
                    'open': 50600.0,
                    'close': 50700.0
                }
            ]
        }
    }
    
    # Monitor positions - should trigger TP1
    updates_1 = position_manager.monitor_all_positions(market_data_1)
    
    print(f"First candle updates: {len(updates_1)}")
    assert len(updates_1) == 1, f"Expected 1 update, got {len(updates_1)}"
    
    update_1 = updates_1[0]
    print(f"Update 1: {update_1.triggered_level} @ {update_1.current_price}, Status: {update_1.old_status} -> {update_1.new_status}")
    
    assert update_1.triggered_level == "TP1", f"Expected TP1, got {update_1.triggered_level}"
    assert update_1.new_status == "PARTIAL", f"Expected PARTIAL, got {update_1.new_status}"
    
    # Second candle: hits TP2
    market_data_2 = {
        'tickers': {
            'BTCUSDT': {'last': 51600.0}
        },
        'ohlcv': {
            'BTCUSDT': [
                {
                    'timestamp': "2024-01-01T13:00:00Z",  # Previous candle (already processed)
                    'high': 50800.0,
                    'low': 50200.0,
                    'open': 50300.0,
                    'close': 50600.0
                },
                {
                    'timestamp': "2024-01-01T14:00:00Z",  # New candle
                    'high': 51600.0,    # Above TP2 (51500)
                    'low': 50600.0,     # Above entry
                    'open': 50700.0,
                    'close': 51400.0
                },
                {  # Current active candle (should be ignored)
                    'timestamp': "2024-01-01T15:00:00Z",
                    'high': 51500.0,
                    'low': 51300.0,
                    'open': 51400.0,
                    'close': 51450.0
                }
            ]
        }
    }
    
    # Monitor positions - should trigger TP2
    updates_2 = position_manager.monitor_all_positions(market_data_2)
    
    print(f"Second candle updates: {len(updates_2)}")
    assert len(updates_2) == 1, f"Expected 1 update, got {len(updates_2)}"
    
    update_2 = updates_2[0]
    print(f"Update 2: {update_2.triggered_level} @ {update_2.current_price}, Status: {update_2.old_status} -> {update_2.new_status}")
    
    assert update_2.triggered_level == "TP2", f"Expected TP2, got {update_2.triggered_level}"
    assert update_2.new_status == "CLOSED", f"Expected CLOSED, got {update_2.new_status}"
    assert update_2.old_status == "PARTIAL", f"Expected old status PARTIAL, got {update_2.old_status}"
    
    print("✅ TP1 then TP2 in separate candles works correctly")
    return True


def main():
    """Run the test"""
    print("Running TP1 then TP2 separate candles test...\n")
    
    try:
        success = test_tp1_then_tp2_separate_candles()
        
        if success:
            print("\n🎉 TP1 then TP2 separate candles test passed!")
            return True
        else:
            print("\n❌ Test failed!")
            return False
            
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)