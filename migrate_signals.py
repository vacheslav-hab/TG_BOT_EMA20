#!/usr/bin/env python3
"""
Script to migrate existing signals to include EMA fields
"""

import json
import sys
import os
from datetime import datetime

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import EMA_PERIOD


def migrate_signals_file(input_file='signals.json', output_file='signals_migrated.json'):
    """Migrate signals.json file to include EMA fields for existing signals"""
    
    print(f"Migrating {input_file} to {output_file}...")
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"File {input_file} not found")
        return False
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        return False
    
    signals = data.get('positions', {})
    migrated_count = 0
    
    print(f"Processing {len(signals)} signals...")
    
    for signal_id, signal in signals.items():
        # Add EMA fields if they don't exist
        if 'ema_used_period' not in signal:
            signal['ema_used_period'] = EMA_PERIOD
            migrated_count += 1
            
        if 'ema_value' not in signal:
            # Set a default EMA value (this is just for migration purposes)
            signal['ema_value'] = signal.get('entry', 0) * 0.99
            migrated_count += 1
    
    # Update metadata
    if 'metadata' not in data:
        data['metadata'] = {}
    data['metadata']['migrated_at'] = datetime.now().isoformat()
    data['metadata']['ema_period'] = EMA_PERIOD
    
    # Save migrated data
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Successfully migrated {migrated_count} fields in {len(signals)} signals")
        print(f"Migrated data saved to {output_file}")
        return True
    except Exception as e:
        print(f"Error saving migrated data: {e}")
        return False


def validate_migrated_file(file_path='signals_migrated.json'):
    """Validate the migrated file"""
    
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
        print("✅ Migration validation passed!")
        return True
    else:
        print(f"❌ Migration validation failed with {missing_ema_info + incorrect_ema_period} issues")
        return False


if __name__ == '__main__':
    input_file = 'signals.json'
    output_file = 'signals_migrated.json'
    
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    
    success = migrate_signals_file(input_file, output_file)
    
    if success:
        validate_success = validate_migrated_file(output_file)
        if validate_success:
            print("\n🎉 Migration completed successfully!")
            print(f"You can now replace {input_file} with {output_file} if you want to use the migrated data")
        else:
            print("\n💥 Migration validation failed!")
    else:
        print("\n💥 Migration failed!")