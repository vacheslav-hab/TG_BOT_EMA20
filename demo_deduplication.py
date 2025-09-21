#!/usr/bin/env python3
"""
Demo script to show signal deduplication functionality
"""

import asyncio
from decimal import Decimal
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from strategy import create_signal_atomic
from config import EMA_PERIOD


async def demo_signal_deduplication():
    """Demonstrate signal deduplication functionality"""
    print("=== Signal Deduplication Demo ===")
    print(f"EMA Period: {EMA_PERIOD}")
    print()
    
    symbol = "BTC-USDT"
    direction = "LONG"
    entry_price = Decimal("50000.0")
    ema_value = Decimal("49900.0")
    
    print(f"Attempting to create signal for {symbol} {direction}")
    print(f"Entry price: {entry_price}")
    print(f"EMA value: {ema_value}")
    print()
    
    # Try to create the same signal twice
    print("Creating first signal...")
    signal1 = await create_signal_atomic(symbol, direction, entry_price, ema_value)
    
    if signal1:
        print(f"✅ First signal created successfully!")
        print(f"   Signal ID: {signal1['signal_id']}")
        print(f"   EMA period: {signal1['ema_used_period']}")
        print(f"   EMA value: {signal1['ema_value']}")
    else:
        print("❌ Failed to create first signal")
    
    print()
    print("Creating second signal (should be skipped due to deduplication)...")
    signal2 = await create_signal_atomic(symbol, direction, entry_price, ema_value)
    
    if signal2:
        print("❌ Second signal was created (this should not happen!)")
    else:
        print("✅ Second signal was correctly skipped due to deduplication")
    
    print()
    print("=== Demo Complete ===")


if __name__ == "__main__":
    asyncio.run(demo_signal_deduplication())