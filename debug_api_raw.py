#!/usr/bin/env python3
"""
Raw API debugging for BingX
"""

import asyncio
import aiohttp
import json
from config import logger, BINGX_API_KEY, BINGX_SECRET_KEY

async def test_raw_api():
    """Test raw BingX API calls"""
    
    async with aiohttp.ClientSession() as session:
        # Test contracts endpoint
        logger.info("Testing contracts endpoint...")
        
        try:
            url = "https://open-api.bingx.com/openApi/swap/v2/quote/contracts"
            
            async with session.get(url) as response:
                logger.info(f"Response status: {response.status}")
                logger.info(f"Response headers: {dict(response.headers)}")
                
                text = await response.text()
                logger.info(f"Response text (first 500 chars): {text[:500]}")
                
                try:
                    data = json.loads(text)
                    logger.info(f"JSON response keys: {list(data.keys())}")
                    
                    if 'data' in data:
                        contracts = data['data']
                        logger.info(f"Total contracts: {len(contracts)}")
                        
                        if contracts:
                            logger.info(f"Sample contract: {contracts[0]}")
                            
                            # Check for USDT contracts
                            usdt_contracts = [c for c in contracts if c.get('symbol', '').endswith('-USDT')]
                            logger.info(f"USDT contracts found: {len(usdt_contracts)}")
                            
                            if usdt_contracts:
                                logger.info("First 3 USDT contracts:")
                                for i, contract in enumerate(usdt_contracts[:3]):
                                    logger.info(f"  {contract}")
                    else:
                        logger.info("Available keys in response:")
                        for key, value in data.items():
                            logger.info(f"  {key}: {type(value)} = {str(value)[:100]}")
                            
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON: {e}")
                    
        except Exception as e:
            logger.error(f"Request failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_raw_api())