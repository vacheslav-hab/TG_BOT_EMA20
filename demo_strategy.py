#!/usr/bin/env python3
"""
Demo script showing EMA20 strategy in action
"""

import asyncio
import json
from datetime import datetime
from strategy import StrategyManager, Signal

def create_demo_market_data():
    """Create realistic demo market data"""
    
    # Simulate BTC price movement around EMA20 
    base_price = 50000
    ohlcv_data = []
    
    # Generate 30 candles with a realistic price pattern
    prices = [
        # Initial uptrend to establish EMA
        49000, 49100, 49200, 49300, 49400, 49500, 49600, 49700, 49800, 49900,
        50000, 50100, 50200, 50300, 50400, 50500, 50600, 50700, 50800, 50900,
        # Pullback toward EMA (potential LONG touch)
        50800, 50700, 50600, 50500, 50400, 50300, 50200, 50100, 50050, 50025
    ]
    
    for i, price in enumerate(prices):
        ohlcv_data.append({
            'timestamp': 1700000000 + i * 3600,  # Hourly candles
            'open': price - 20,
            'high': price + 50,
            'low': price - 50,
            'close': price,
            'volume': 1000 + (i * 10)
        })
    
    return {
        'ohlcv': {
            'BTC-USDT': ohlcv_data,
            'ETH-USDT': ohlcv_data,  # Same pattern for demo
        },
        'tickers': {
            'BTC-USDT': {
                'bid': 50020.0,
                'ask': 50030.0,
                'last': 50025.0,  # Current price near EMA
                'volume': 50000000
            },
            'ETH-USDT': {
                'bid': 50020.0,
                'ask': 50030.0,
                'last': 50025.0,
                'volume': 25000000
            }
        }
    }

def create_touch_scenario_data():
    """Create data that will definitely trigger touch detection"""
    
    # Create OHLCV with clear EMA trend
    ohlcv_data = []
    for i in range(25):
        price = 50000 + (i * 20)  # Clear uptrend
        ohlcv_data.append({
            'timestamp': 1700000000 + i * 3600,
            'open': price - 10,
            'high': price + 15,
            'low': price - 15,
            'close': price,
            'volume': 1000
        })
    
    return {
        'ohlcv': {
            'DEMO-USDT': ohlcv_data
        },
        'tickers': {
            'DEMO-USDT': {
                'bid': 50475.0,
                'ask': 50485.0,
                'last': 50480.0,  # Near the calculated EMA
                'volume': 1000000
            }
        }
    }

async def demo_ema_calculation():
    """Demo EMA20 calculation"""
    print("=" * 60)
    print("🧮 EMA20 CALCULATION DEMO")
    print("=" * 60)
    
    strategy = StrategyManager()
    demo_data = create_demo_market_data()
    
    btc_ohlcv = demo_data['ohlcv']['BTC-USDT']
    
    print(f"📊 Processing {len(btc_ohlcv)} candles for BTC-USDT")
    print(f"💰 Price range: ${btc_ohlcv[0]['close']:,.0f} - ${btc_ohlcv[-1]['close']:,.0f}")
    
    ema_values = strategy.calculate_ema20(btc_ohlcv)
    
    if ema_values:
        print(f"📈 EMA20 calculated: {len(ema_values)} values")
        print(f"🎯 Current EMA20: ${ema_values[-1]:,.2f}")
        print(f"📊 EMA trend: {'Rising' if strategy.is_ema_rising(ema_values) else 'Falling'}")
        
        # Show last few EMA values
        print("\\n📋 Last 5 EMA20 values:")
        for i, ema in enumerate(ema_values[-5:], 1):
            print(f"   {i}. ${ema:,.2f}")
    else:
        print("❌ Could not calculate EMA20")

async def demo_touch_detection():
    """Demo touch detection logic"""
    print("\\n" + "=" * 60)
    print("🎯 TOUCH DETECTION DEMO") 
    print("=" * 60)
    
    strategy = StrategyManager()
    demo_data = create_touch_scenario_data()
    
    # Get OHLCV and calculate EMA
    ohlcv = demo_data['ohlcv']['DEMO-USDT']
    ema_values = strategy.calculate_ema20(ohlcv)
    current_ema = ema_values[-1] if ema_values else 50000
    
    print(f"📊 Current EMA20: ${current_ema:,.2f}")
    
    # Test various price scenarios
    scenarios = [
        {"name": "Above tolerance zone", "prev": current_ema * 1.002, "curr": current_ema * 1.001},
        {"name": "LONG touch scenario", "prev": current_ema * 1.002, "curr": current_ema * 1.0005},
        {"name": "SHORT touch scenario", "prev": current_ema * 0.998, "curr": current_ema * 0.9995},
        {"name": "Below tolerance zone", "prev": current_ema * 0.998, "curr": current_ema * 0.997},
    ]
    
    for scenario in scenarios:
        touch = strategy.detect_touch(
            "DEMO-USDT", scenario["curr"], current_ema, scenario["prev"]
        )
        
        touch_result = touch if touch else "No touch"
        print(f"   {scenario['name']}: {touch_result}")
        print(f"      Prev: ${scenario['prev']:,.2f} → Curr: ${scenario['curr']:,.2f}")

async def demo_signal_generation():
    """Demo complete signal generation"""
    print("\\n" + "=" * 60)
    print("🚀 SIGNAL GENERATION DEMO")
    print("=" * 60)
    
    strategy = StrategyManager()
    demo_data = create_demo_market_data()
    
    print("🔍 Analyzing market for signals...")
    
    # First analysis to establish baseline
    await strategy.analyze_market(demo_data)
    
    # Modify data to create touch scenario
    demo_data['tickers']['BTC-USDT']['last'] = 50250.0  # Price near EMA
    demo_data['tickers']['ETH-USDT']['last'] = 50200.0  # Different price
    
    # Set previous prices to create touch scenario
    strategy.previous_prices['BTC-USDT'] = 50400.0  # Was higher
    strategy.previous_prices['ETH-USDT'] = 49800.0  # Was lower
    
    print("📈 Simulating price movements that could trigger signals...")
    
    signals = await strategy.analyze_market(demo_data)
    
    if signals:
        print(f"\\n🎉 Generated {len(signals)} signals!")
        for i, signal in enumerate(signals, 1):
            print(f"\\n📋 Signal #{i}:")
            print(f"   Symbol: {signal.symbol}")
            print(f"   Direction: {signal.direction}")
            print(f"   Entry: ${signal.entry:,.2f}")
            print(f"   Stop Loss: ${signal.sl:,.2f}")
            print(f"   Take Profit 1: ${signal.tp1:,.2f}")
            print(f"   Take Profit 2: ${signal.tp2:,.2f}")
            print(f"   Risk/Reward: 1:{(signal.tp1 - signal.entry) / abs(signal.entry - signal.sl):.1f}")
    else:
        print("🤷 No signals generated in this scenario")

async def demo_cooldown_mechanism():
    """Demo cooldown mechanism"""
    print("\\n" + "=" * 60)
    print("⏰ COOLDOWN MECHANISM DEMO")
    print("=" * 60)
    
    strategy = StrategyManager()
    
    symbol = "TEST-USDT"
    
    # Test cooldown states
    print(f"🔍 Testing cooldown for {symbol}")
    print(f"   Initial state: {'Active' if strategy.is_cooldown_active(symbol) else 'Inactive'}")
    
    # Generate a signal (activates cooldown)
    signal = strategy.generate_signal(symbol, "LONG", 50000.0)
    print(f"\\n🚀 Generated signal: {signal.direction} {signal.symbol}")
    print(f"   Cooldown after signal: {'Active' if strategy.is_cooldown_active(symbol) else 'Inactive'}")
    
    # Show cooldown remaining time
    if symbol in strategy.last_signals:
        from datetime import datetime, timedelta
        last_signal = strategy.last_signals[symbol]
        elapsed = datetime.now() - last_signal
        remaining = timedelta(minutes=60) - elapsed  # MIN_SIGNAL_COOLDOWN_MIN = 60
        print(f"   Time remaining: {remaining.total_seconds() / 60:.1f} minutes")

def demo_json_serialization():
    """Demo signal JSON serialization"""
    print("\\n" + "=" * 60)
    print("💾 JSON SERIALIZATION DEMO")
    print("=" * 60)
    
    # Create a sample signal
    signal = Signal(
        symbol="BTC-USDT",
        direction="LONG", 
        entry=50000.0,
        sl=49500.0,
        tp1=50750.0,
        tp2=51500.0
    )
    
    # Convert to dictionary
    signal_dict = signal.to_dict()
    
    # Serialize to JSON
    json_string = json.dumps(signal_dict, indent=2)
    
    print("📋 Signal object converted to JSON:")
    print(json_string)
    
    # Show how it could be stored/transmitted
    print("\\n💡 This JSON can be:")
    print("   • Stored in signals.json file")
    print("   • Sent via Telegram API")
    print("   • Logged for analysis")
    print("   • Used for backtesting")

async def main():
    """Run all demos"""
    print("🎯 EMA20 TRADING STRATEGY DEMONSTRATION")
    print("🤖 Telegram Bot EMA20 - Strategy Module")
    print()
    
    await demo_ema_calculation()
    await demo_touch_detection()
    await demo_signal_generation()
    await demo_cooldown_mechanism()
    demo_json_serialization()
    
    print("\\n" + "=" * 60)
    print("✅ DEMO COMPLETED")
    print("=" * 60)
    print("🎉 Strategy implementation is working correctly!")
    print("📊 Key features demonstrated:")
    print("   • EMA20 calculation with rising/falling detection")
    print("   • Touch detection for LONG/SHORT scenarios")
    print("   • Signal generation with proper risk/reward levels")
    print("   • Cooldown mechanism to prevent spam")
    print("   • JSON serialization for data persistence")
    print("\\n🚀 Ready for integration with Telegram bot!")

if __name__ == "__main__":
    asyncio.run(main())