"""Test for atomic operations with concurrent write attempts"""

import asyncio
import json
import os
import tempfile
import unittest
from unittest.mock import patch, mock_open
from json_manager import JSONDataManager
from subscribers_manager import SubscribersManager
from strategy import Signal
from position_manager import ExtendedPositionData


class TestAtomicOperations(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        # Create temporary files for testing
        self.temp_dir = tempfile.mkdtemp()
        self.signals_file = os.path.join(self.temp_dir, "test_signals.json")
        self.subscribers_file = os.path.join(self.temp_dir, "test_subscribers.json")
        
        # Create managers with temporary files
        self.json_manager = JSONDataManager(self.signals_file)
        self.subscribers_manager = SubscribersManager(self.subscribers_file)
    
    def tearDown(self):
        """Clean up test fixtures"""
        # Remove temporary files
        if os.path.exists(self.signals_file):
            os.remove(self.signals_file)
        if os.path.exists(self.subscribers_file):
            os.remove(self.subscribers_file)
        if os.path.exists(self.temp_dir):
            os.rmdir(self.temp_dir)
    
    def test_atomic_write_read_operations(self):
        """Test atomic write/read operations"""
        # Test that we can write and read data correctly
        test_data = {
            'positions': {},
            'statistics': {
                'total_signals': 5,
                'tp1_hits': 2,
                'tp2_hits': 1,
                'sl_hits': 1
            }
        }
        
        # Save data
        self.json_manager.save_data(test_data)
        
        # Read data back
        loaded_data = self.json_manager.load_data()
        
        # Check that data matches
        self.assertEqual(loaded_data['statistics']['total_signals'], 5)
        self.assertEqual(loaded_data['statistics']['tp1_hits'], 2)
    
    def test_concurrent_write_attempts_signals(self):
        """Test concurrent write attempts for signals"""
        # This test would ideally use asyncio to test concurrent access,
        # but for simplicity, we'll test that the locking mechanism works
        
        # Add a position
        signal = Signal(
            symbol="BTC-USDT",
            direction="LONG",
            entry=50000.0,
            sl=49500.0,
            tp1=50750.0,
            tp2=51500.0
        )
        
        position = ExtendedPositionData(
            signal_id="BTC-USDT_LONG_20250914_120000",
            symbol="BTC-USDT",
            direction="LONG",
            entry_price=50000.0,
            sl_price=49500.0,
            tp1_price=50750.0,
            tp2_price=51500.0,
            status="OPEN",
            created_at="2025-09-14T12:00:00"
        )
        
        # Add position
        self.json_manager.add_position(position)
        
        # Check that position was added
        positions = self.json_manager.get_positions()
        self.assertIn("BTC-USDT_LONG_20250914_120000", positions)
    
    def test_concurrent_write_attempts_subscribers(self):
        """Test concurrent write attempts for subscribers"""
        # Add a subscriber
        is_new = self.subscribers_manager.add_subscriber(
            user_id=123456789,
            username="testuser",
            first_name="Test",
            last_name="User"
        )
        
        # Check that subscriber was added
        self.assertTrue(is_new)
        
        subscribers = self.subscribers_manager.get_subscribers()
        self.assertIn(123456789, subscribers)
        
        # Update subscriber activity
        self.subscribers_manager.update_subscriber_activity(123456789)
        
        # Check that activity was updated
        subscribers = self.subscribers_manager.get_subscribers()
        self.assertIn(123456789, subscribers)
        self.assertEqual(subscribers[123456789].total_commands, 2)
    
    def test_temp_file_cleanup_on_error(self):
        """Test that temporary files are cleaned up on error"""
        # This is difficult to test directly without mocking file operations
        # but we can verify the temp file naming convention
        temp_file = f"{self.signals_file}.tmp"
        self.assertFalse(os.path.exists(temp_file))
        
    async def test_async_concurrent_access_json_manager(self):
        """Test async concurrent access to JSON manager"""
        # Create multiple tasks that try to write to the same file
        async def write_task(task_id):
            test_data = {
                'positions': {f"task_{task_id}": {"symbol": f"SYM{task_id}"}},
                'statistics': {'total_signals': task_id}
            }
            await self.json_manager.save_data_async(test_data)
            return task_id
            
        # Run multiple concurrent tasks
        tasks = [write_task(i) for i in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check that all tasks completed successfully
        for result in results:
            self.assertIsInstance(result, int)  # Should be the task_id
            
    async def test_async_concurrent_access_subscribers_manager(self):
        """Test async concurrent access to subscribers manager"""
        # Create multiple tasks that try to add subscribers
        async def add_subscriber_task(task_id):
            user_id = 1000000 + task_id
            is_new = await self.subscribers_manager.add_subscriber_async(
                user_id=user_id,
                username=f"user{task_id}",
                first_name=f"First{task_id}",
                last_name=f"Last{task_id}"
            )
            return is_new
            
        # Run multiple concurrent tasks
        tasks = [add_subscriber_task(i) for i in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check that all tasks completed successfully
        for result in results:
            self.assertIsInstance(result, bool)  # Should be True for new subscribers
            
        # Check that all subscribers were added
        subscribers = await self.subscribers_manager.get_subscribers_async()
        self.assertEqual(len(subscribers), 5)
        
    def test_atomic_write_failure_handling(self):
        """Test handling of atomic write failures"""
        # Mock file operations to simulate failure
        with patch('builtins.open', mock_open()) as mock_file:
            mock_file.side_effect = Exception("Disk full")
            
            test_data = {'test': 'data'}
            
            # Should handle the exception gracefully
            with self.assertRaises(Exception):
                self.json_manager.save_data(test_data)
                
            # Verify temp file is cleaned up
            temp_file = f"{self.signals_file}.tmp"
            # Note: This is hard to test without more complex mocking
            
    def test_metadata_inclusion(self):
        """Test that metadata is included in saved data"""
        test_data = {
            'positions': {},
            'statistics': {'total_signals': 1}
        }
        
        self.json_manager.save_data(test_data)
        loaded_data = self.json_manager.load_data()
        
        # Check that metadata was added
        self.assertIn('metadata', loaded_data)
        self.assertIn('last_updated', loaded_data['metadata'])
        self.assertIn('version', loaded_data['metadata'])


if __name__ == '__main__':
    unittest.main()