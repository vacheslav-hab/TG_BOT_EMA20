#!/usr/bin/env python3
"""
Integration test for the strict touch detection implementation in the main bot flow.
"""

import pandas as pd
import sys
import os
from datetime import datetime, timezone, timedelta
import asyncio

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from strategy import detect_touch_current_strict, get_ema_last_closed
from utils import iso_to_dt, now_utc


def test_integration():
    """
    Test the integration of strict touch detection with the main bot flow.
    """
    print("Testing integration of strict touch detection...")
    
    # Create test data with recent timestamps (within 3 hours)
    timestamps = []
    base_time = datetime.now(timezone.utc) - timedelta(minutes=90)  # 1.5 hours ago
    for i in range(25):
        ts = (base_time + timedelta(minutes=i*5)).isoformat().replace("+00:00", "Z")
        timestamps.append(ts)
    
    # Create DataFrame with EMA touch scenario
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
    
    # Test the integration
    symbol = "TESTUSDT"
    last_signal_time = {}
    active_positions = {}
    
    # Run strict touch detection
    result, data = detect_touch_current_strict(
        symbol, df, ema_series,
        bid=None, ask=None,
        last_signal_time=last_signal_time,
        active_positions=active_positions
    )
    
    if result:
        print(f"✅ PASS: Touch detected - {data}")
        
        # Log attempt signal
        try:
            print("ATTEMPT_SIGNAL", {
                "symbol": symbol,
                "candle_ts": data["candle_ts"],
                "now": datetime.utcnow().isoformat() + "Z",
                "ema_last_closed": str(data["ema"]),
                "candle_low": str(df.iloc[-1]['low']),
                "candle_high": str(df.iloc[-1]['high']),
                "current_price": str(data["entry_price"]),
                "price_source": data["price_source"],
                "last_signal_time": last_signal_time.get(symbol),
                "active_position": symbol in active_positions
            })
        except Exception as e:
            print(f"Error logging ATTEMPT_SIGNAL: {e}")
            
        # Simulate signal creation
        if last_signal_time.get(symbol) != data["candle_ts"]:
            last_signal_time[symbol] = data["candle_ts"]
            
            # Log created signal
            try:
                ctx = {
                    "symbol": symbol,
                    "direction": data["direction"],
                    "entry": str(data["entry_price"]),
                    "candle_ts": data["candle_ts"],
                    "monitor_from": None,  # Would be set in real implementation
                    "now": datetime.utcnow().isoformat() + "Z"
                }
                print("CREATED_SIGNAL", ctx)
            except Exception as e:
                print(f"Error logging CREATED_SIGNAL: {e}")
        else:
            # Log skip signal with reason and context
            try:
                reason = "already_signaled_on_this_candle"
                ctx = {
                    "symbol": symbol,
                    "candle_ts": data["candle_ts"],
                    "now": datetime.utcnow().isoformat() + "Z",
                    "ema_last_closed": str(data["ema"]),
                    "candle_low": str(df.iloc[-1]['low']),
                    "candle_high": str(df.iloc[-1]['high']),
                    "current_price": str(data["entry_price"]),
                    "price_source": data["price_source"],
                    "in_active_positions": False,
                    "last_signal_time": last_signal_time.get(symbol)
                }
                print("SKIP_SIGNAL reason=%s %s" % (reason, ctx))
            except Exception as e:
                print(f"Error logging SKIP_SIGNAL: {e}")
    else:
        print(f"❌ FAIL: No touch - {data}")
        
        # Log skip signal with reason and context
        try:
            reason = data if isinstance(data, str) else "no_touch"
            ctx = {
                "symbol": symbol,
                "candle_ts": data["candle_ts"] if "candle_ts" in data else None,
                "now": datetime.utcnow().isoformat() + "Z",
                "ema_last_closed": str(data["ema"]) if "ema" in data else None,
                "candle_low": str(df.iloc[-1]['low']) if len(df) > 0 else None,
                "candle_high": str(df.iloc[-1]['high']) if len(df) > 0 else None,
                "current_price": str(data["entry_price"]) if "entry_price" in data else None,
                "price_source": data["price_source"] if "price_source" in data else None,
                "in_active_positions": False,
                "last_signal_time": last_signal_time.get(symbol)
            }
            print("SKIP_SIGNAL reason=%s %s" % (reason, ctx))
        except Exception as e:
            print(f"Error logging SKIP_SIGNAL: {e}")
    
    print("\nIntegration test completed.")


if __name__ == "__main__":
    test_integration()