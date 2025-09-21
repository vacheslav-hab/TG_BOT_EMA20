#!/usr/bin/env python3
"""
Test script to verify the session fix for the BingX API connector issue
"""

import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from exchange import ExchangeManager
from config import logger


async def test_session_fix():
    """Test that the session fix works correctly"""
    print("=== Testing Session Fix ===")
    
    try:
        # Initialize the exchange manager
        exchange_manager = ExchangeManager()
        await exchange_manager.initialize()
        
        print(f"✅ Successfully initialized exchange manager with {len(exchange_manager.symbols)} symbols")
        
        # Try to get market data multiple times to test session reuse
        for i in range(3):
            print(f"Attempt {i+1} to get market data...")
            market_data = await exchange_manager.get_market_data()
            
            ohlcv_count = len(market_data.get('ohlcv', {}))
            ticker_count = len(market_data.get('tickers', {}))
            
            print(f"   OHLCV data for {ohlcv_count} symbols")
            print(f"   Ticker data for {ticker_count} symbols")
            
            if ohlcv_count > 0 and ticker_count > 0:
                print(f"   ✅ Successfully retrieved market data (attempt {i+1})")
            else:
                print(f"   ⚠️  Retrieved market data but with limited information (attempt {i+1})")
        
        # Clean up
        await exchange_manager.cleanup()
        print("✅ Successfully cleaned up resources")
        
        print("\n🎉 Session fix test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Session fix test failed: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_session_fix())
    sys.exit(0 if success else 1)