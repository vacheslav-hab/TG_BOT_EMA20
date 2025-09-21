from position_manager import PositionManager
import tempfile
import json
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

# Test the PnL calculation
position_manager = PositionManager(temp_file.name)

# Test weighted PnL calculation - exact test from requirements
# Long trade, TP1 hit then TP2
pnl = position_manager.calculate_pnl(100, [(101.5, 0.5), (103, 0.5)], "LONG")
print(f"Weighted PnL calculation result: {pnl}%")

# Expected: TP1: (101.5-100)/100 * 0.5 = 0.75%
#           TP2: (103-100)/100 * 0.5 = 1.5%
#           Total = 2.25%
expected_pnl = 2.25
print(f"Expected PnL: {expected_pnl}%")
print(f"Calculation correct: {abs(pnl - expected_pnl) < 0.01}")

# Test active positions count
active_count = position_manager.get_active_positions_count()
print(f"Active positions count: {active_count}")

# Clean up
os.unlink(temp_file.name)
print("PnL calculation test completed successfully")