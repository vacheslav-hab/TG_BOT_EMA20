#!/usr/bin/env python3
"""
Script to validate signals.json for duplicate signals and EMA period usage
"""

import json
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import EMA_PERIOD


def validate_signals_file(file_path='signals.json'):
    """Validate signals.json file for duplicates and EMA period usage"""
    
    print(f"Validating {file_path}...")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"File {file_path} not found")
        return False
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        return False
    
    signals = data.get('positions', {})
    
    # Check for duplicate signals (same symbol + direction)
    symbol_direction_count = {}
    duplicate_count = 0
    missing_ema_info = 0
    incorrect_ema_period = 0
    active_signals = 0
    
    print("\nChecking for duplicate signals...")
    
    for signal_id, signal in signals.items():
        key = f"{signal['symbol']}_{signal['direction']}"
        
        # Count active signals
        if signal['status'] in ('OPEN', 'PARTIAL'):
            active_signals += 1
            
        if key in symbol_direction_count:
            symbol_direction_count[key] += 1
            if signal['status'] in ('OPEN', 'PARTIAL'):
                print(f"⚠️  DUPLICATE ACTIVE SIGNAL: {signal['symbol']} {signal['direction']}")
                duplicate_count += 1
        else:
            symbol_direction_count[key] = 1
            
        # Check EMA information
        if 'ema_used_period' not in signal:
            print(f"⚠️  Missing ema_used_period in signal {signal_id}")
            missing_ema_info += 1
        elif signal['ema_used_period'] != EMA_PERIOD:
            print(f"⚠️  Incorrect EMA period {signal['ema_used_period']} in signal {signal_id} (expected {EMA_PERIOD})")
            incorrect_ema_period += 1
    
    print(f"\nValidation Results:")
    print(f"Total signals: {len(signals)}")
    print(f"Active signals (OPEN/PARTIAL): {active_signals}")
    print(f"Duplicate active signals: {duplicate_count}")
    print(f"Signals missing EMA info: {missing_ema_info}")
    print(f"Signals with incorrect EMA period: {incorrect_ema_period}")
    
    if duplicate_count == 0 and missing_ema_info == 0 and incorrect_ema_period == 0:
        print("\n✅ All validations passed!")
        return True
    else:
        print(f"\n❌ {duplicate_count + missing_ema_info + incorrect_ema_period} issues found")
        return False


def validate_ema_period_usage(file_path='signals.json'):
    """Validate that all signals use the correct EMA period"""
    
    print(f"\nValidating EMA period usage in {file_path}...")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"File {file_path} not found")
        return False
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        return False
    
    signals = data.get('positions', {})
    
    missing_ema_info = 0
    incorrect_ema_period = 0
    
    for signal_id, signal in signals.items():
        if 'ema_used_period' not in signal:
            print(f"⚠️  Missing ema_used_period in signal {signal_id}")
            missing_ema_info += 1
        elif signal['ema_used_period'] != EMA_PERIOD:
            print(f"⚠️  Incorrect EMA period {signal['ema_used_period']} in signal {signal_id} (expected {EMA_PERIOD})")
            incorrect_ema_period += 1
    
    print(f"Signals missing EMA info: {missing_ema_info}")
    print(f"Signals with incorrect EMA period: {incorrect_ema_period}")
    
    if missing_ema_info == 0 and incorrect_ema_period == 0:
        print("✅ EMA period validation passed!")
        return True
    else:
        print(f"❌ EMA period validation failed with {missing_ema_info + incorrect_ema_period} issues")
        return False


if __name__ == '__main__':
    file_path = 'signals.json'
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    
    success1 = validate_signals_file(file_path)
    success2 = validate_ema_period_usage(file_path)
    
    if success1 and success2:
        print("\n🎉 All validations passed!")
        sys.exit(0)
    else:
        print("\n💥 Validation failed!")
        sys.exit(1)