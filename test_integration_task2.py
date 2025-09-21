#!/usr/bin/env python3
"""Integration test for Task 2: Position monitoring delay mechanism"""

import asyncio
import sys
import os
from datetime import datetime, timezone, timedelta
from decimal import Decimal

# Add current directory to path for imports
sys.path.insert(0, os.getcwd())

from strategy import create_signal_atomic
from position_manager import PositionManager
from json_manager import JSONDataManager


async def test_complete_position_monitoring_flow():
    """Test the complete flow from signal creation to position monitoring with delays"""
    print("Testing complete position monitoring flow with delays...")
    
    # Clean up test data
    json_manager = JSONDataManager()
    data = json_manager.load_data()
    data["positions"] = {}
    if "metadata" not in data:
        data["metadata"] = {}
    data["metadata"]["last_signal_candle"] = {}
    json_manager.save_data(data)
    
    # Step 1: Create a signal with monitor_from field
    symbol = "BTCUSDT"
    direction = "LONG"
    entry = Decimal("50000.0")
    ema_value = Decimal("49950.0")
    entry_candle_time = "2024-01-01T12:00:00Z"
    
    print(f"Step 1: Creating signal for {symbol} {direction} @ {entry}")
    signal = await create_signal_atomic(symbol, direction, entry, ema_value, entry_candle_time)
    
    assert signal is not None, "Signal creation failed"
    assert signal.get('monitor_from') == "2024-01-01T13:00:00Z", f"Expected monitor_from 2024-01-01T13:00:00Z, got {signal.get('monitor_from')}"
    
    print(f"✅ Signal created with ID: {signal['signal_id']}")
    print(f"   Entry candle: {signal['entry_candle_time']}")
    print(f"   Monitor from: {signal['monitor_from']}")
    print(f"   Levels: Entry={signal['entry_price']}, TP1={signal['tp1_price']}, TP2={signal['tp2_price']}, SL={signal['sl_price']}")
    
    position_manager = PositionManager()
    
    # Step 2: Test monitoring before monitor_from (should be ignored)
    print(f"\nStep 2: Testing monitoring before monitor_from...")
    market_data_before = {
        'tickers': {
            'BTCUSDT': {'last': 51000.0}  # Above TP1
        },
        'ohlcv': {
            'BTCUSDT': [
                {
                    'timestamp': "2024-01-01T12:30:00Z",  # Before monitor_from
                    'high': 51000.0,  # Above TP1
                    'low': 49500.0,
                    'open': 50000.0,
                    'close': 50500.0
                },
                {  # Current active candle (should be ignored)
                    'timestamp': "2024-01-01T13:00:00Z",
                    'high': 50600.0,
                    'low': 50400.0,
                    'open': 50500.0,
                    'close': 50550.0
                }
            ]
        }
    }
    
    updates_before = position_manager.monitor_all_positions(market_data_before)
    print(f"   Updates before monitor_from: {len(updates_before)}")
    assert len(updates_before) == 0, f"Expected 0 updates before monitor_from, got {len(updates_before)}"
    print("✅ Correctly ignored candles before monitor_from")
    
    # Step 3: Test monitoring at monitor_from (should trigger TP1)
    print(f"\nStep 3: Testing monitoring at monitor_from...")
    market_data_at = {
        'tickers': {
            'BTCUSDT': {'last': 50800.0}
        },
        'ohlcv': {
            'BTCUSDT': [
                {
                    'timestamp': "2024-01-01T13:00:00Z",  # At monitor_from
                    'high': 50800.0,  # Above TP1 but below TP2
                    'low': 50200.0,
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
    
    updates_at = position_manager.monitor_all_positions(market_data_at)
    print(f"   Updates at monitor_from: {len(updates_at)}")
    assert len(updates_at) == 1, f"Expected 1 update at monitor_from, got {len(updates_at)}"
    
    update_tp1 = updates_at[0]
    print(f"   TP1 Update: {update_tp1.triggered_level} @ {update_tp1.current_price}, Status: {update_tp1.old_status} -> {update_tp1.new_status}")
    
    assert update_tp1.triggered_level == "TP1", f"Expected TP1, got {update_tp1.triggered_level}"
    assert update_tp1.new_status == "PARTIAL", f"Expected PARTIAL, got {update_tp1.new_status}"
    assert update_tp1.old_status == "OPEN", f"Expected old status OPEN, got {update_tp1.old_status}"
    print("✅ Correctly triggered TP1 at monitor_from")
    
    # Step 4: Test monitoring after monitor_from (should trigger TP2)
    print(f"\nStep 4: Testing monitoring after monitor_from...")
    market_data_after = {
        'tickers': {
            'BTCUSDT': {'last': 51600.0}
        },
        'ohlcv': {
            'BTCUSDT': [
                {
                    'timestamp': "2024-01-01T13:00:00Z",  # Previous candle
                    'high': 50800.0,
                    'low': 50200.0,
                    'open': 50300.0,
                    'close': 50600.0
                },
                {
                    'timestamp': "2024-01-01T14:00:00Z",  # After monitor_from
                    'high': 51600.0,  # Above TP2
                    'low': 50600.0,
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
    
    updates_after = position_manager.monitor_all_positions(market_data_after)
    print(f"   Updates after monitor_from: {len(updates_after)}")
    assert len(updates_after) == 1, f"Expected 1 update after monitor_from, got {len(updates_after)}"
    
    update_tp2 = updates_after[0]
    print(f"   TP2 Update: {update_tp2.triggered_level} @ {update_tp2.current_price}, Status: {update_tp2.old_status} -> {update_tp2.new_status}")
    
    assert update_tp2.triggered_level == "TP2", f"Expected TP2, got {update_tp2.triggered_level}"
    assert update_tp2.new_status == "CLOSED", f"Expected CLOSED, got {update_tp2.new_status}"
    assert update_tp2.old_status == "PARTIAL", f"Expected old status PARTIAL, got {update_tp2.old_status}"
    print("✅ Correctly triggered TP2 after monitor_from")
    
    # Step 5: Verify PnL calculations
    print(f"\nStep 5: Verifying PnL calculations...")
    print(f"   TP1 PnL: {update_tp1.pnl_percentage}% (expected: +0.75%)")
    print(f"   TP2 PnL: {update_tp2.pnl_percentage}% (expected: +3.00%)")
    
    # TP1 should be +0.75% (50% of +1.5%)
    assert abs(update_tp1.pnl_percentage - 0.75) < 0.01, f"Expected TP1 PnL ~0.75%, got {update_tp1.pnl_percentage}%"
    
    # TP2 should be +3.00% (remaining 50% of +3.0% since TP1 already hit)
    assert abs(update_tp2.pnl_percentage - 3.00) < 0.01, f"Expected TP2 PnL ~3.00%, got {update_tp2.pnl_percentage}%"
    
    print("✅ PnL calculations are correct")
    
    print(f"\n🎉 Complete position monitoring flow test passed!")
    return True


async def main():
    """Run the integration test"""
    print("Running Task 2 integration test...\n")
    
    try:
        success = await test_complete_position_monitoring_flow()
        
        if success:
            print("\n🎉 Task 2 integration test passed!")
            print("\nTask 2 Implementation Summary:")
            print("✅ 2.1 monitor_from field added to signal creation")
            print("✅ 2.2 Position monitoring logic respects timing constraints")
            print("✅ 2.3 TP/SL detection uses candle high/low ranges with proper order")
            print("✅ All requirements 4.1, 4.2, 4.3, 4.4, 4.5, 4.6 implemented")
            return True
        else:
            print("\n❌ Integration test failed!")
            return False
            
    except Exception as e:
        print(f"\n❌ Integration test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)