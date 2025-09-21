from strategy import calc_ema20
from json_manager import JSONDataManager
import json
import tempfile
import os

# Create a temporary file for testing
temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
temp_file.close()

# Initialize with empty data structure
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

with open(temp_file.name, 'w') as f:
    json.dump(empty_data, f)

# Test the get_open_signal functionality
json_manager = JSONDataManager(temp_file.name)

# Add a test position
test_position = {
    "signal_id": "test_signal_1",
    "symbol": "BTC-USDT",
    "direction": "LONG",
    "entry_price": 50000.0,
    "sl_price": 49500.0,
    "tp1_price": 50750.0,
    "tp2_price": 51500.0,
    "status": "OPEN",
    "created_at": "2025-09-16T00:00:00",
    "ema_used_period": 20,
    "ema_tf": "1h",
    "ema_value": 49900.0
}

# Load data, add position, and save
data = json_manager.load_data()
data['positions']['test_signal_1'] = test_position
json_manager.save_data(data)

# Test deduplication check
open_signal = json_manager.get_open_signal("BTC-USDT", "LONG")
print(f"Open signal found: {open_signal is not None}")

if open_signal:
    print(f"Signal ID: {open_signal.get('signal_id')}")
    print(f"Status: {open_signal.get('status')}")

# Clean up
os.unlink(temp_file.name)
print("Deduplication test completed successfully")