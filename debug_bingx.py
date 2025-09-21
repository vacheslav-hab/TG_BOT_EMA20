#!/usr/bin/env python3
"""
Debug script to test BingX API connection
"""

import asyncio
from exchange import ExchangeManager
from config import logger

async def debug_bingx_connection():
    """Debug BingX API connection"""
    
    exchange = ExchangeManager()
    
    try:
        logger.info("Testing BingX API connection...")
        
        # Initialize the exchange first
        await exchange.initialize()
        
        logger.info(f"Symbols loaded: {len(exchange.symbols)}")
        
        if exchange.symbols:
            logger.info(f"First 10 symbols: {exchange.symbols[:10]}")
            
            # Test market data
            logger.info("Testing market data retrieval...")
            market_data = await exchange.get_market_data()
            
            ohlcv_count = len(market_data.get('ohlcv', {}))
            ticker_count = len(market_data.get('tickers', {}))
            
            logger.info(f"OHLCV data for {ohlcv_count} symbols")
            logger.info(f"Ticker data for {ticker_count} symbols")
            
            # Show sample data
            if market_data.get('tickers'):
                sample_symbol = list(market_data['tickers'].keys())[0]
                sample_ticker = market_data['tickers'][sample_symbol]
                logger.info(f"Sample ticker {sample_symbol}: {sample_ticker}")
        else:
            logger.error("No symbols loaded!")
                
    except Exception as e:
        logger.error(f"API Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        await exchange.cleanup()

if __name__ == "__main__":
    asyncio.run(debug_bingx_connection())