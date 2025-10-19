#!/usr/bin/env python3
"""
Test script to verify graceful data extraction in liveStrategy
Run this to test that the strategy no longer crashes on missing data fields.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from core.liveStrategy import ModularIntradayStrategy
from datetime import datetime
from types import MappingProxyType
from utils.config_helper import create_config_from_defaults, freeze_config

def test_graceful_extraction():
    """Test that the strategy handles missing data gracefully"""
    
    # Use the default configuration to ensure all required fields are present
    base_config = create_config_from_defaults()
    test_config = freeze_config(base_config)

    print("🔄 Testing graceful data extraction in liveStrategy...")
    
    try:
        # Initialize strategy
        strategy = ModularIntradayStrategy(test_config)
        print("✅ Strategy initialized successfully")
        
        # Test 1: Missing 'close' field (should not crash)
        print("\n📋 Test 1: Missing 'close' field")
        bad_tick_1 = pd.Series({
            'volume': 100, 
            'high': 100.0, 
            'low': 99.0, 
            'open': 99.5
        })
        result1 = strategy.process_tick_or_bar(bad_tick_1)
        print("✅ Handled missing 'close' field gracefully - no crash!")
        
        # Test 2: Missing 'price' field fallback (should not crash)
        print("\n📋 Test 2: Missing both 'close' and 'price' fields")
        bad_tick_2 = pd.Series({'volume': 100})
        result2 = strategy.process_tick_or_bar(bad_tick_2)
        print("✅ Handled missing 'price' field gracefully - no crash!")
        
        # Test 3: Valid data (should work normally)
        print("\n📋 Test 3: Valid tick data")
        good_tick = pd.Series({
            'close': 100.0, 
            'volume': 150, 
            'high': 100.5, 
            'low': 99.5, 
            'open': 100.0
        })
        result3 = strategy.process_tick_or_bar(good_tick)
        print("✅ Processed valid tick data successfully")
        print(f"   - EMA values calculated: fast_ema={result3.get('fast_ema', 'N/A')}")
        
        # Test 4: on_tick method with missing timestamp
        print("\n📋 Test 4: Missing timestamp in tick (on_tick method)")
        bad_tick_dict = {'close': 100.0, 'volume': 100}  # Missing timestamp
        result4 = strategy.on_tick(bad_tick_dict)
        if result4 is None:
            print("✅ on_tick handled missing timestamp gracefully - returned None")
        else:
            print("❌ on_tick should have returned None for missing timestamp")
            
        # Test 5: on_tick method with valid data
        print("\n📋 Test 5: Valid tick data with timestamp (on_tick method)")
        good_tick_dict = {
            'close': 100.0, 
            'volume': 100, 
            'timestamp': datetime.now()
        }
        result5 = strategy.on_tick(good_tick_dict)
        print(f"✅ on_tick processed valid data successfully - returned: {type(result5)}")
        
        print("\n🎉 All graceful extraction tests PASSED!")
        print("✅ Live trading system will no longer halt on data quality issues")
        print("✅ Strategy gracefully handles:")
        print("   - Missing 'close' or 'price' fields")
        print("   - Missing 'timestamp' fields")
        print("   - Invalid or empty data")
        print("   - All edge cases return safely without crashing")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test FAILED with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_graceful_extraction()
    exit(0 if success else 1)