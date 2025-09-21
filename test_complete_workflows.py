#!/usr/bin/env python3
"""
Integration tests for complete signal generation and position monitoring workflows
"""

import unittest
import json
import tempfile
import os
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

# Add current directory to path for imports
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from strategy import (detect_touch, validate_signal_direction, can_generate_signal, 
                     register_signal, create_signal_atomic)
from position_manager import PositionManager
from json_manager import JSONDataManager
from decimal import Decimal


class TestCompleteWorkflows(unittest.TestCase):
    
    def setUp(self):
        """Setup for each test"""
        # Use temporary file for testing
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        self.temp_file.close()
        
        # Ensure the temporary file is empty with proper structure
        empty_data = {
            "positions": {}, 
            "statistics": {
                "total_signals": 0,
                "tp1_hits": 0,
                "tp2_hits": 0,
                "sl_hits": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "average_pnl_per_trade": 0.0,
                "max_consecutive_wins": 0,
                "max_consecutive_losses": 0,
                "best_trade_pnl": 0.0,
                "worst_trade_pnl": 0.0
            }, 
            "daily_stats": {}, 
            "symbol_stats": {}, 
            "metadata": {
                "created_at": "2025-09-16T00:00:00",
                "version": "2.0",
                "last_signal_candle": {}
            }
        }
        with open(self.temp_file.name, 'w') as f:
            json.dump(empty_data, f)
        
        self.position_manager = PositionManager(json_file=self.temp_file.name)
        
    def tearDown(self):
        """Cleanup after each test"""
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)
            
    def test_end_to_end_signal_generation_and_monitoring(self):
        """Test end-to-end signal generation and position monitoring workflow"""
        # Step 1: Simulate market data with EMA20 touch
        symbol = "BTCUSDT"
        last_closed_candle = {
            'high': 50200.0,
            'low': 49800.0,
            'close': 50100.0,
            'open': 49900.0,
            'timestamp': "2024-01-01T12:00:00Z"
        }
        
        ema20_current = 50000.0
        ema20_previous = 49995.0
        
        # Step 2: Check for EMA20 touch
        touched = detect_touch(last_closed_candle, ema20_current)
        self.assertTrue(touched, "EMA20 touch should be detected")
        
        # Step 3: Determine potential signal direction
        last_closed_close = Decimal(str(last_closed_candle['close']))
        potential_direction = "LONG" if last_closed_close > Decimal(str(ema20_current)) else "SHORT"
        self.assertEqual(potential_direction, "LONG", "Direction should be LONG")
        
        # Step 4: Validate signal direction
        direction_valid = validate_signal_direction(
            last_closed_candle, ema20_current, ema20_previous, potential_direction
        )
        self.assertTrue(direction_valid, "Signal direction should be valid")
        
        # Step 5: Check signal deduplication
        can_generate = can_generate_signal(symbol, last_closed_candle['timestamp'])
        self.assertTrue(can_generate, "Should be able to generate signal")
        
        # Step 6: Create signal atomically
        import asyncio
        sig = asyncio.run(create_signal_atomic(
            symbol, potential_direction, last_closed_close, 
            Decimal(str(ema20_current)), last_closed_candle['timestamp']
        ))
        
        self.assertIsNotNone(sig, "Signal should be created")
        self.assertIn("signal_id", sig, "Signal should have an ID")
        self.assertIn("monitor_from", sig, "Signal should have monitor_from field")
        
        # Step 7: Register signal generation
        register_signal(symbol, last_closed_candle['timestamp'])
        
        # Step 8: Verify deduplication works for same candle
        can_generate_again = can_generate_signal(symbol, last_closed_candle['timestamp'])
        self.assertFalse(can_generate_again, "Should not generate signal for same candle again")
        
        # Step 9: Verify new candle allows signal
        new_candle_time = "2024-01-01T13:00:00Z"
        can_generate_new = can_generate_signal(symbol, new_candle_time)
        self.assertTrue(can_generate_new, "Should generate signal for new candle")
        
        # Step 10: Test position monitoring with the created signal
        signal_id = sig["signal_id"]
        
        # Update position with monitoring times
        self.position_manager.json_manager.update_position(signal_id, {
            "monitor_from": "2024-01-01T10:00:00Z",
            "current_candle_time": "2024-01-01T12:00:00Z"
        })
        
        # Test TP1 hit
        current_price = 50750.0  # TP1 level
        update = self.position_manager.check_position_levels(signal_id, current_price)
        
        self.assertIsNotNone(update, "Position update should be generated")
        self.assertEqual(update.new_status, "PARTIAL", "Status should be PARTIAL after TP1")
        self.assertEqual(update.triggered_level, "TP1", "Triggered level should be TP1")
        self.assertGreater(update.pnl_percentage, 0, "PnL should be positive")
        
    def test_multi_symbol_concurrent_processing(self):
        """Test multi-symbol concurrent processing workflow"""
        symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
        
        # Process multiple symbols
        created_signals = []
        
        for i, symbol in enumerate(symbols):
            # Create different market conditions for each symbol
            last_closed_candle = {
                'high': 50000.0 + i * 1000,
                'low': 49000.0 + i * 1000,
                'close': 49500.0 + i * 1000,
                'open': 49200.0 + i * 1000,
                'timestamp': "2024-01-01T12:00:00Z"
            }
            
            ema20_current = 49400.0 + i * 1000
            ema20_previous = 49395.0 + i * 1000
            
            # Check for EMA20 touch
            touched = detect_touch(last_closed_candle, ema20_current)
            if touched:
                # Determine potential signal direction
                last_closed_close = Decimal(str(last_closed_candle['close']))
                potential_direction = "LONG" if last_closed_close > Decimal(str(ema20_current)) else "SHORT"
                
                # Validate signal direction
                direction_valid = validate_signal_direction(
                    last_closed_candle, ema20_current, ema20_previous, potential_direction
                )
                
                if direction_valid:
                    # Check signal deduplication
                    can_generate = can_generate_signal(symbol, last_closed_candle['timestamp'])
                    if can_generate:
                        # Create signal atomically
                        import asyncio
                        sig = asyncio.run(create_signal_atomic(
                            symbol, potential_direction, last_closed_close, 
                            Decimal(str(ema20_current)), last_closed_candle['timestamp']
                        ))
                        
                        if sig:
                            created_signals.append(sig)
                            # Register signal generation
                            register_signal(symbol, last_closed_candle['timestamp'])
        
        # Verify that signals were created for all symbols
        self.assertEqual(len(created_signals), len(symbols), 
                        "Should create signals for all symbols")
        
        # Verify each signal has required fields
        for sig in created_signals:
            self.assertIn("signal_id", sig, "Each signal should have an ID")
            self.assertIn("monitor_from", sig, "Each signal should have monitor_from field")
            self.assertIn("entry_candle_time", sig, "Each signal should have entry_candle_time")
            
    def test_error_recovery_and_system_stability(self):
        """Test error recovery and system stability"""
        # Test with malformed data
        symbol = "BTCUSDT"
        
        # Test with invalid candle data (missing fields)
        invalid_candle = {
            'high': 50200.0,
            'low': 49800.0
            # Missing close, open, timestamp
        }
        
        # This should not cause a crash
        try:
            touched = detect_touch(invalid_candle, 50000.0)
            # Should handle gracefully
        except Exception as e:
            self.fail(f"Should not crash with invalid candle data: {e}")
            
        # Test with invalid prices
        try:
            from strategy import _validate_price_input
            result = _validate_price_input(-50000.0, "test")
            self.assertFalse(result, "Should return False for negative price")
        except Exception as e:
            self.fail(f"Should not crash with invalid price: {e}")
            
        # Test with invalid timestamp
        try:
            can_generate = can_generate_signal(symbol, None)
            self.assertFalse(can_generate, "Should return False for None timestamp")
        except Exception as e:
            self.fail(f"Should not crash with None timestamp: {e}")


if __name__ == '__main__':
    unittest.main()