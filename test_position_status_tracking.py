#!/usr/bin/env python3
"""Test position status tracking and transitions"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from position_manager import PositionManager
from datetime import datetime, timezone

def test_position_status_transitions():
    """Test position status transitions: OPEN -> PARTIAL -> CLOSED"""
    pm = PositionManager()
    
    print("Testing Position Status Transitions")
    print("=" * 50)
    
    # Test data for LONG position
    entry_price = 50000.0
    tp1_price = 50750.0  # +1.5%
    tp2_price = 51500.0  # +3.0%
    sl_price = 49500.0   # -1.0%
    
    # Create test signal data
    signal_data = {
        "symbol": "BTCUSDT",
        "direction": "LONG",
        "entry_price": entry_price,
        "sl_price": sl_price,
        "tp1_price": tp1_price,
        "tp2_price": tp2_price,
        "status": "OPEN",
        "partial_hit": False,
        "current_candle_time": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    }
    
    print(f"\nInitial signal: {signal_data['status']}")
    print(f"Entry: ${entry_price}, TP1: ${tp1_price}, TP2: ${tp2_price}, SL: ${sl_price}")
    
    # Test 1: TP1 hit - should transition OPEN -> PARTIAL
    print("\n1. Testing TP1 hit (OPEN -> PARTIAL):")
    tp1_signal = signal_data.copy()
    updated_tp1 = pm.update_signal(tp1_signal, tp1_price)
    
    if updated_tp1:
        print(f"   Status: {signal_data['status']} -> {updated_tp1['status']}")
        print(f"   Partial hit flag: {updated_tp1.get('partial_hit', False)}")
        print(f"   SL moved to breakeven: ${updated_tp1['sl_price']}")
        
        # Verify status transition
        assert updated_tp1['status'] == 'PARTIAL', f"Expected PARTIAL, got {updated_tp1['status']}"
        assert updated_tp1.get('partial_hit') == True, "partial_hit flag should be True"
        assert updated_tp1['sl_price'] == entry_price, f"SL should be moved to breakeven ({entry_price})"
        print("   ✓ TP1 transition test passed")
    else:
        print("   ✗ TP1 transition test failed - no update returned")
        return False
    
    # Test 2: TP2 hit after TP1 - should transition PARTIAL -> CLOSED
    print("\n2. Testing TP2 hit after TP1 (PARTIAL -> CLOSED):")
    tp2_signal = updated_tp1.copy()
    updated_tp2 = pm.update_signal(tp2_signal, tp2_price)
    
    if updated_tp2:
        print(f"   Status: {tp2_signal['status']} -> {updated_tp2['status']}")
        print(f"   Exit reason: {updated_tp2.get('exit_reason', 'None')}")
        
        # Verify status transition
        assert updated_tp2['status'] == 'CLOSED', f"Expected CLOSED, got {updated_tp2['status']}"
        assert updated_tp2.get('exit_reason') == 'TP2_HIT', f"Expected TP2_HIT, got {updated_tp2.get('exit_reason')}"
        print("   ✓ TP2 transition test passed")
    else:
        print("   ✗ TP2 transition test failed - no update returned")
        return False
    
    # Test 3: SL hit after TP1 - should transition PARTIAL -> CLOSED
    print("\n3. Testing SL hit after TP1 (PARTIAL -> CLOSED):")
    sl_after_tp1_signal = updated_tp1.copy()  # Start from PARTIAL status
    sl_after_tp1_signal['status'] = 'PARTIAL'  # Ensure PARTIAL status
    updated_sl = pm.update_signal(sl_after_tp1_signal, sl_price)
    
    if updated_sl:
        print(f"   Status: {sl_after_tp1_signal['status']} -> {updated_sl['status']}")
        print(f"   Exit reason: {updated_sl.get('exit_reason', 'None')}")
        
        # Verify status transition
        assert updated_sl['status'] == 'CLOSED', f"Expected CLOSED, got {updated_sl['status']}"
        assert updated_sl.get('exit_reason') == 'SL_HIT', f"Expected SL_HIT, got {updated_sl.get('exit_reason')}"
        print("   ✓ SL after TP1 transition test passed")
    else:
        print("   ✗ SL after TP1 transition test failed - no update returned")
        return False
    
    # Test 4: Direct SL hit - should transition OPEN -> CLOSED
    print("\n4. Testing direct SL hit (OPEN -> CLOSED):")
    direct_sl_signal = signal_data.copy()
    updated_direct_sl = pm.update_signal(direct_sl_signal, sl_price)
    
    if updated_direct_sl:
        print(f"   Status: {signal_data['status']} -> {updated_direct_sl['status']}")
        print(f"   Exit reason: {updated_direct_sl.get('exit_reason', 'None')}")
        
        # Verify status transition
        assert updated_direct_sl['status'] == 'CLOSED', f"Expected CLOSED, got {updated_direct_sl['status']}"
        assert updated_direct_sl.get('exit_reason') == 'SL_HIT', f"Expected SL_HIT, got {updated_direct_sl.get('exit_reason')}"
        print("   ✓ Direct SL transition test passed")
    else:
        print("   ✗ Direct SL transition test failed - no update returned")
        return False
    
    # Test 5: Direct TP2 hit - should transition OPEN -> CLOSED
    print("\n5. Testing direct TP2 hit (OPEN -> CLOSED):")
    direct_tp2_signal = signal_data.copy()
    updated_direct_tp2 = pm.update_signal(direct_tp2_signal, tp2_price)
    
    if updated_direct_tp2:
        print(f"   Status: {signal_data['status']} -> {updated_direct_tp2['status']}")
        print(f"   Exit reason: {updated_direct_tp2.get('exit_reason', 'None')}")
        
        # Verify status transition
        assert updated_direct_tp2['status'] == 'CLOSED', f"Expected CLOSED, got {updated_direct_tp2['status']}"
        assert updated_direct_tp2.get('exit_reason') == 'TP2_HIT', f"Expected TP2_HIT, got {updated_direct_tp2.get('exit_reason')}"
        print("   ✓ Direct TP2 transition test passed")
    else:
        print("   ✗ Direct TP2 transition test failed - no update returned")
        return False
    
    print("\n" + "=" * 50)
    print("All position status transition tests passed! ✓")
    return True

def test_short_position_transitions():
    """Test SHORT position status transitions"""
    pm = PositionManager()
    
    print("\nTesting SHORT Position Status Transitions")
    print("=" * 50)
    
    # Test data for SHORT position
    entry_price = 50000.0
    tp1_price = 49250.0  # -1.5%
    tp2_price = 48500.0  # -3.0%
    sl_price = 50500.0   # +1.0%
    
    # Create test signal data
    signal_data = {
        "symbol": "BTCUSDT",
        "direction": "SHORT",
        "entry_price": entry_price,
        "sl_price": sl_price,
        "tp1_price": tp1_price,
        "tp2_price": tp2_price,
        "status": "OPEN",
        "partial_hit": False,
        "current_candle_time": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    }
    
    print(f"\nInitial SHORT signal: {signal_data['status']}")
    print(f"Entry: ${entry_price}, TP1: ${tp1_price}, TP2: ${tp2_price}, SL: ${sl_price}")
    
    # Test SHORT TP1 hit
    print("\n1. Testing SHORT TP1 hit (OPEN -> PARTIAL):")
    tp1_signal = signal_data.copy()
    updated_tp1 = pm.update_signal(tp1_signal, tp1_price)
    
    if updated_tp1:
        print(f"   Status: {signal_data['status']} -> {updated_tp1['status']}")
        print(f"   Partial hit flag: {updated_tp1.get('partial_hit', False)}")
        print(f"   SL moved to breakeven: ${updated_tp1['sl_price']}")
        
        # Verify status transition
        assert updated_tp1['status'] == 'PARTIAL', f"Expected PARTIAL, got {updated_tp1['status']}"
        assert updated_tp1.get('partial_hit') == True, "partial_hit flag should be True"
        assert updated_tp1['sl_price'] == entry_price, f"SL should be moved to breakeven ({entry_price})"
        print("   ✓ SHORT TP1 transition test passed")
    else:
        print("   ✗ SHORT TP1 transition test failed - no update returned")
        return False
    
    # Test SHORT SL hit after TP1
    print("\n2. Testing SHORT SL hit after TP1 (PARTIAL -> CLOSED):")
    sl_after_tp1_signal = updated_tp1.copy()
    updated_sl = pm.update_signal(sl_after_tp1_signal, sl_price)
    
    if updated_sl:
        print(f"   Status: {sl_after_tp1_signal['status']} -> {updated_sl['status']}")
        print(f"   Exit reason: {updated_sl.get('exit_reason', 'None')}")
        
        # Verify status transition
        assert updated_sl['status'] == 'CLOSED', f"Expected CLOSED, got {updated_sl['status']}"
        assert updated_sl.get('exit_reason') == 'SL_HIT', f"Expected SL_HIT, got {updated_sl.get('exit_reason')}"
        print("   ✓ SHORT SL after TP1 transition test passed")
    else:
        print("   ✗ SHORT SL after TP1 transition test failed - no update returned")
        return False
    
    print("\n" + "=" * 50)
    print("All SHORT position status transition tests passed! ✓")
    return True

if __name__ == "__main__":
    success1 = test_position_status_transitions()
    success2 = test_short_position_transitions()
    
    if success1 and success2:
        print("\n🎉 All position status tracking tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)