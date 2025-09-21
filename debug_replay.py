#!/usr/bin/env python3
"""
Debug replay script for testing EMA20 touch detection logic.
Loads CSV with 1h candles, calculates EMA20 on closed candles only,
and runs detect_touch_current_strict for each step.
"""

import pandas as pd
import numpy as np
from decimal import Decimal
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from strategy import detect_touch_current_strict, get_ema_last_closed
from utils import iso_to_dt, now_utc


def load_sample_candles():
    """
    Create sample 1h candles data for testing.
    In a real scenario, this would load from a CSV file.
    """
    # Sample data - in practice you would load from CSV
    # This is just a simple example for demonstration
    data = {
        'timestamp': [
            '2025-09-18T10:00:00Z', '2025-09-18T11:00:00Z', '2025-09-18T12:00:00Z',
            '2025-09-18T13:00:00Z', '2025-09-18T14:00:00Z', '2025-09-18T15:00:00Z',
            '2025-09-18T16:00:00Z', '2025-09-18T17:00:00Z', '2025-09-18T18:00:00Z',
            '2025-09-18T19:00:00Z', '2025-09-18T20:00:00Z', '2025-09-18T21:00:00Z',
            '2025-09-18T22:00:00Z', '2025-09-18T23:00:00Z', '2025-09-19T00:00:00Z',
            '2025-09-19T01:00:00Z', '2025-09-19T02:00:00Z', '2025-09-19T03:00:00Z',
            '2025-09-19T04:00:00Z', '2025-09-19T05:00:00Z', '2025-09-19T06:00:00Z',
            '2025-09-19T07:00:00Z', '2025-09-19T08:00:00Z', '2025-09-19T09:00:00Z',
            '2025-09-19T10:00:00Z'
        ],
        'open': [
            2600, 2610, 2620, 2630, 2640, 2650, 2660, 2670, 2680, 2690,
            2700, 2710, 2720, 2730, 2740, 2750, 2760, 2770, 2780, 2790,
            2800, 2810, 2820, 2830, 2840
        ],
        'high': [
            2620, 2630, 2640, 2650, 2660, 2670, 2680, 2690, 2700, 2710,
            2720, 2730, 2740, 2750, 2760, 2770, 2780, 2790, 2800, 2810,
            2820, 2830, 2840, 2850, 2860
        ],
        'low': [
            2590, 2600, 2610, 2620, 2630, 2640, 2650, 2660, 2670, 2680,
            2690, 2700, 2710, 2720, 2730, 2740, 2750, 2760, 2770, 2780,
            2790, 2800, 2810, 2820, 2830
        ],
        'close': [
            2610, 2620, 2630, 2640, 2650, 2660, 2670, 2680, 2690, 2700,
            2710, 2720, 2730, 2740, 2750, 2760, 2770, 2780, 2790, 2800,
            2810, 2820, 2830, 2840, 2850
        ]
    }
    
    return pd.DataFrame(data)


def calculate_ema20_on_closed_candles(candles_df):
    """
    Calculate EMA20 only on closed candles.
    """
    closes = candles_df['close'].tolist()
    series = pd.Series(closes)
    ema_series = series.ewm(span=20, adjust=False).mean()
    return ema_series


def run_debug_replay():
    """
    Run debug replay of touch detection logic.
    """
    print("Loading sample candles...")
    candles_df = load_sample_candles()
    print(f"Loaded {len(candles_df)} candles")
    
    print("\nCalculating EMA20 on closed candles only...")
    ema_series = calculate_ema20_on_closed_candles(candles_df)
    print(f"Calculated EMA20 for {len(ema_series)} candles")
    
    # Simulate incremental processing
    print("\nRunning touch detection for each step...")
    last_signal_time = {}
    active_positions = {}
    
    for i in range(20, len(candles_df)):  # Need at least 20 candles for EMA
        # Get subset up to current candle
        subset_df = candles_df.iloc[:i+1].copy()
        subset_ema = ema_series.iloc[:i+1]
        
        symbol = "TESTUSDT"
        current_candle = subset_df.iloc[-1]
        
        # Simulate bid/ask prices
        bid = float(current_candle['low'])  # Simplified
        ask = float(current_candle['high'])  # Simplified
        
        print(f"\n--- Step {i-19} ---")
        print(f"Current candle: {current_candle['timestamp']}")
        print(f"Price range: [{current_candle['low']:.2f} - {current_candle['high']:.2f}]")
        print(f"Close: {current_candle['close']:.2f}")
        print(f"EMA20 (closed): {subset_ema.iloc[-2]:.2f}")  # Use -2 for closed candle
        
        # Run strict touch detection
        touch_result, touch_data = detect_touch_current_strict(
            symbol, subset_df, subset_ema,
            bid=bid, ask=ask,
            last_signal_time=last_signal_time,
            active_positions=active_positions
        )
        
        if touch_result:
            print(f"✅ TOUCH DETECTED: {touch_data}")
            # Register signal to prevent duplicates
            last_signal_time[symbol] = touch_data['candle_ts']
        else:
            print(f"❌ No touch: {touch_data}")
    
    print("\nDebug replay completed.")


if __name__ == "__main__":
    run_debug_replay()