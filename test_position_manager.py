"""Unit tests for Position Manager and TP/SL monitoring"""

import unittest
import json
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Import config to patch JSON_FILE correctly
import config

from position_manager import PositionManager, PositionStatus, PositionUpdate
from strategy import Signal


class TestPositionManager(unittest.TestCase):
    
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
                "version": "2.0"
            }
        }
        with open(self.temp_file.name, 'w') as f:
            json.dump(empty_data, f)
        
        self.position_manager = PositionManager(json_file=self.temp_file.name)
        
    def tearDown(self):
        """Cleanup after each test"""
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)
            
    def create_test_signal(self, symbol="BTC-USDT", direction="LONG", entry=50000.0):
        """Create a test signal"""
        if direction == "LONG":
            sl = entry * 0.99    # -1%
            tp1 = entry * 1.015  # +1.5%
            tp2 = entry * 1.03   # +3%
        else:  # SHORT
            sl = entry * 1.01    # +1%
            tp1 = entry * 0.985  # -1.5%
            tp2 = entry * 0.97   # -3%
            
        return Signal(
            symbol=symbol,
            direction=direction,
            entry=entry,
            sl=sl,
            tp1=tp1,
            tp2=tp2
        )
        
    def test_signal_id_generation(self):
        """Test signal ID generation"""
        signal = self.create_test_signal()
        signal_id = self.position_manager.generate_signal_id(signal)
        
        self.assertIn(signal.symbol, signal_id)
        self.assertIn(signal.direction, signal_id)
        self.assertIsInstance(signal_id, str)
        
    def test_add_position(self):
        """Test adding a new position"""
        signal = self.create_test_signal()
        
        signal_id = self.position_manager.add_position(signal)
        
        self.assertIn(signal_id, self.position_manager.active_positions)
        self.assertEqual(signal.status, PositionStatus.OPEN.value)
        self.assertEqual(self.position_manager.statistics['total_signals'], 1)
        
    def test_long_tp1_detection(self):
        """Test TP1 detection for LONG position"""
        signal = self.create_test_signal("BTC-USDT", "LONG", 50000.0)
        signal_id = self.position_manager.add_position(signal)
        
        # Price reaches TP1
        current_price = 50750.0  # TP1 level
        update = self.position_manager.check_position_levels(signal_id, current_price)
        
        self.assertIsNotNone(update)
        self.assertEqual(update.new_status, "PARTIAL")  # Changed from TP1_HIT to PARTIAL per requirements
        self.assertEqual(update.triggered_level, "TP1")
        self.assertGreater(update.pnl_percentage, 0)
        
    def test_long_tp2_detection(self):
        """Test TP2 detection for LONG position"""
        signal = self.create_test_signal("BTC-USDT", "LONG", 50000.0)
        signal_id = self.position_manager.add_position(signal)
        
        # First hit TP1 to move to PARTIAL status
        current_price = 50750.0  # TP1 level
        update1 = self.position_manager.check_position_levels(signal_id, current_price)
        self.assertIsNotNone(update1)
        self.assertEqual(update1.new_status, "PARTIAL")
        self.assertEqual(update1.triggered_level, "TP1")
        
        # Then hit TP2
        current_price = 51500.0  # TP2 level
        update2 = self.position_manager.check_position_levels(signal_id, current_price)
        
        self.assertIsNotNone(update2)
        self.assertEqual(update2.new_status, "CLOSED")  # Changed from PositionStatus.TP2_HIT.value to "CLOSED" per requirements
        self.assertEqual(update2.triggered_level, "TP2")
        self.assertGreater(update2.pnl_percentage, 0)
        
    def test_long_sl_detection(self):
        """Test SL detection for LONG position"""
        signal = self.create_test_signal("BTC-USDT", "LONG", 50000.0)
        signal_id = self.position_manager.add_position(signal)
        
        # Price hits SL
        current_price = 49500.0  # SL level
        update = self.position_manager.check_position_levels(signal_id, current_price)
        
        self.assertIsNotNone(update)
        self.assertEqual(update.new_status, "CLOSED")  # Changed from PositionStatus.SL_HIT.value to "CLOSED" per requirements
        self.assertEqual(update.triggered_level, "SL")
        self.assertLess(update.pnl_percentage, 0)
        
    def test_short_tp1_detection(self):
        """Test TP1 detection for SHORT position"""
        signal = self.create_test_signal("BTC-USDT", "SHORT", 50000.0)
        signal_id = self.position_manager.add_position(signal)
        
        # Price reaches TP1
        current_price = 49250.0  # TP1 level for SHORT
        update = self.position_manager.check_position_levels(signal_id, current_price)
        
        self.assertIsNotNone(update)
        self.assertEqual(update.new_status, "PARTIAL")  # Changed from PositionStatus.TP1_HIT.value to "PARTIAL" per requirements
        self.assertEqual(update.triggered_level, "TP1")
        self.assertGreater(update.pnl_percentage, 0)
        
    def test_short_sl_detection(self):
        """Test SL detection for SHORT position"""
        signal = self.create_test_signal("BTC-USDT", "SHORT", 50000.0)
        signal_id = self.position_manager.add_position(signal)
        
        # Price hits SL
        current_price = 50500.0  # SL level for SHORT
        update = self.position_manager.check_position_levels(signal_id, current_price)
        
        self.assertIsNotNone(update)
        self.assertEqual(update.new_status, "CLOSED")  # Changed from PositionStatus.SL_HIT.value to "CLOSED" per requirements
        self.assertEqual(update.triggered_level, "SL")
        self.assertLess(update.pnl_percentage, 0)
        
    def test_no_level_triggered(self):
        """Test when no level is triggered"""
        signal = self.create_test_signal("BTC-USDT", "LONG", 50000.0)
        signal_id = self.position_manager.add_position(signal)
        
        # Price stays in middle range
        current_price = 50100.0
        update = self.position_manager.check_position_levels(signal_id, current_price)
        
        self.assertIsNone(update)
        
    def test_pnl_calculation_long(self):
        """Test PnL calculation for LONG positions"""
        signal = self.create_test_signal("BTC-USDT", "LONG", 50000.0)
        
        # Test profit scenario
        current_price = 51000.0
        pnl = self.position_manager.calculate_pnl_percentage(signal, current_price)
        expected_pnl = ((51000 - 50000) / 50000) * 100  # 2%
        self.assertAlmostEqual(pnl, expected_pnl, places=2)
        
        # Test loss scenario
        current_price = 49000.0
        pnl = self.position_manager.calculate_pnl_percentage(signal, current_price)
        expected_pnl = ((49000 - 50000) / 50000) * 100  # -2%
        self.assertAlmostEqual(pnl, expected_pnl, places=2)
        
    def test_pnl_calculation_short(self):
        """Test PnL calculation for SHORT positions"""
        signal = self.create_test_signal("BTC-USDT", "SHORT", 50000.0)
        
        # Test profit scenario (price goes down)
        current_price = 49000.0
        pnl = self.position_manager.calculate_pnl_percentage(signal, current_price)
        expected_pnl = ((50000 - 49000) / 50000) * 100  # 2%
        self.assertAlmostEqual(pnl, expected_pnl, places=2)
        
        # Test loss scenario (price goes up)
        current_price = 51000.0
        pnl = self.position_manager.calculate_pnl_percentage(signal, current_price)
        expected_pnl = ((50000 - 51000) / 50000) * 100  # -2%
        self.assertAlmostEqual(pnl, expected_pnl, places=2)
        
    def test_weighted_pnl_calculation(self):
        """Test weighted PnL calculation - exact test from requirements"""
        # Long trade, TP1 hit then TP2
        pnl = self.position_manager.calculate_pnl(100, [(101.5, 0.5), (103, 0.5)], "LONG")
        # TP1: (101.5-100)/100 * 0.5 = 0.75% 
        # TP2: (103-100)/100 * 0.5 = 1.5%
        # Total = 2.25%
        self.assertAlmostEqual(pnl, 2.25, places=2)
        
    def test_statistics_update(self):
        """Test statistics updating"""
        initial_stats = self.position_manager.statistics.copy()
        
        # Add TP1 hit
        self.position_manager.update_statistics("TP1", 1.5)
        self.assertEqual(self.position_manager.statistics['tp1_hits'], initial_stats['tp1_hits'] + 1)
        
        # Add TP2 hit
        self.position_manager.update_statistics("TP2", 3.0)
        self.assertEqual(self.position_manager.statistics['tp2_hits'], initial_stats['tp2_hits'] + 1)
        
        # Add SL hit
        self.position_manager.update_statistics("SL", -1.0)
        self.assertEqual(self.position_manager.statistics['sl_hits'], initial_stats['sl_hits'] + 1)
        
        # Check win rate calculation
        total_closed = self.position_manager.statistics['tp1_hits'] + \
                      self.position_manager.statistics['tp2_hits'] + \
                      self.position_manager.statistics['sl_hits']
        wins = self.position_manager.statistics['tp1_hits'] + \
               self.position_manager.statistics['tp2_hits']
        expected_win_rate = (wins / total_closed) * 100
        
        self.assertAlmostEqual(self.position_manager.statistics['win_rate'], expected_win_rate, places=1)
        
    def test_monitor_all_positions(self):
        """Test monitoring multiple positions"""
        # Add multiple positions
        signal1 = self.create_test_signal("BTC-USDT", "LONG", 50000.0)
        signal2 = self.create_test_signal("ETH-USDT", "SHORT", 3000.0)
        
        signal_id1 = self.position_manager.add_position(signal1)
        signal_id2 = self.position_manager.add_position(signal2)
        
        # Create market data that triggers levels
        market_data = {
            'tickers': {
                'BTC-USDT': {'last': 50750.0},  # Triggers TP1 for LONG
                'ETH-USDT': {'last': 2955.0}    # Triggers TP1 for SHORT (corrected from 2925)
            }
        }
        
        updates = self.position_manager.monitor_all_positions(market_data)
        
        self.assertEqual(len(updates), 2)
        
        # Check that both updates are TP1
        for update in updates:
            self.assertEqual(update.triggered_level, "TP1")
            self.assertEqual(update.new_status, "PARTIAL")  # Changed from PositionStatus.TP1_HIT.value to "PARTIAL" per requirements
            
    def test_active_positions_count(self):
        """Test active positions counting"""
        self.assertEqual(self.position_manager.get_active_positions_count(), 0)
        
        # Add open position
        signal = self.create_test_signal()
        signal_id = self.position_manager.add_position(signal)
        self.assertEqual(self.position_manager.get_active_positions_count(), 1)
        
        # Close position by updating it in the JSON file
        self.position_manager.json_manager.update_position(signal_id, {"status": PositionStatus.TP2_HIT.value})
        self.assertEqual(self.position_manager.get_active_positions_count(), 0)
        
    def test_cleanup_old_positions(self):
        """Test cleanup of old positions"""
        # Add an old closed position
        signal = self.create_test_signal()
        signal_id = self.position_manager.add_position(signal)
        
        # Make it old and closed in the JSON file
        old_time = datetime.now() - timedelta(days=10)
        self.position_manager.json_manager.update_position(signal_id, {
            "created_at": old_time.isoformat(),
            "status": "CLOSED"  # Changed from PositionStatus.TP2_HIT.value to "CLOSED" per requirements
        })
        
        # Add a recent position
        signal2 = self.create_test_signal("ETH-USDT", "SHORT")
        signal_id2 = self.position_manager.add_position(signal2)
        
        self.assertEqual(len(self.position_manager.active_positions), 2)
        
        # Cleanup old positions
        self.position_manager.cleanup_old_positions(days=7)
        
        # Only recent position should remain
        self.assertEqual(len(self.position_manager.active_positions), 1)
        self.assertIn(signal_id2, self.position_manager.active_positions)
        self.assertNotIn(signal_id, self.position_manager.active_positions)
        
    def test_save_load_positions(self):
        """Test saving and loading positions"""
        # Add some positions
        signal1 = self.create_test_signal("BTC-USDT", "LONG")
        signal2 = self.create_test_signal("ETH-USDT", "SHORT")
        
        signal_id1 = self.position_manager.add_position(signal1)
        signal_id2 = self.position_manager.add_position(signal2)
        
        # Update statistics
        self.position_manager.update_statistics("TP1", 1.5)
        
        # Save positions
        self.position_manager.save_positions()
        
        # Create new manager and load from the same test file
        new_manager = PositionManager(json_file=self.temp_file.name)
        
        # Check that positions and statistics were loaded
        self.assertEqual(len(new_manager.active_positions), 2)
        self.assertIn(signal_id1, new_manager.active_positions)
        self.assertIn(signal_id2, new_manager.active_positions)
        self.assertEqual(new_manager.statistics['tp1_hits'], 1)
        
    def test_statistics_summary(self):
        """Test statistics summary generation"""
        # Add some test data to JSON
        test_stats = {
            'total_signals': 10,
            'tp1_hits': 4,
            'tp2_hits': 3,
            'sl_hits': 3,
            'win_rate': 70.0,
            'total_pnl': 15.5
        }
        self.position_manager.json_manager.update_statistics(test_stats)
        
        summary = self.position_manager.get_statistics_summary()
        
        self.assertIn("10", summary)  # total signals
        self.assertIn("4", summary)   # tp1 hits
        self.assertIn("3", summary)   # tp2 hits
        self.assertIn("70.0%", summary)  # win rate
        self.assertIn("+15.50%", summary)  # total pnl (formatted with +)


class TestPositionUpdate(unittest.TestCase):
    
    def test_position_update_creation(self):
        """Test PositionUpdate creation"""
        update = PositionUpdate(
            signal_id="test_id",
            symbol="BTC-USDT",
            direction="LONG",
            current_price=50500.0,
            old_status="OPEN",
            new_status="PARTIAL",  # Changed from "TP1_HIT" to "PARTIAL" per requirements
            pnl_percentage=1.0,
            triggered_level="TP1"
        )
        
        self.assertEqual(update.signal_id, "test_id")
        self.assertEqual(update.symbol, "BTC-USDT")
        self.assertEqual(update.direction, "LONG")
        self.assertEqual(update.current_price, 50500.0)
        self.assertEqual(update.old_status, "OPEN")
        self.assertEqual(update.new_status, "PARTIAL")  # Changed from "TP1_HIT" to "PARTIAL" per requirements
        self.assertEqual(update.pnl_percentage, 1.0)
        self.assertEqual(update.triggered_level, "TP1")
        self.assertIsInstance(update.timestamp, datetime)


if __name__ == '__main__':
    unittest.main()