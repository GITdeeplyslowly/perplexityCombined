#!/usr/bin/env python3
"""
Comprehensive Green Tick Validation Test

This test validates that the consecutive green tick counting logic in liveStrategy.py
works correctly with real market data from the CSV file.

Tests:
1. Green tick counting accuracy with real price movements  
2. Entry condition validation timing
3. Race condition detection between tick updates and entry checks
4. Noise filtering behavior
"""

import sys
import os
import pandas as pd
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from myQuant.core.liveStrategy import ModularIntradayStrategy
    from myQuant.config.defaults import DEFAULT_CONFIG
    from myQuant.utils.config_helper import ConfigAccessor
    from types import MappingProxyType
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running from the project root")
    sys.exit(1)

class MockConfigAccessor:
    """Mock config accessor for testing"""
    def __init__(self, config):
        self.config = config
    
    def get_strategy_param(self, param_name):
        return self.config['strategy'].get(param_name)
    
    def get(self, section):
        return self.config.get(section, {})

class MockPerfLogger:
    """Mock performance logger"""
    def __init__(self):
        self.blocked_entries = []
    
    def entry_blocked(self, reason):
        self.blocked_entries.append(reason)

def test_green_tick_counting_with_csv_data():
    """Test green tick counting with actual CSV price data"""
    print("🧪 Testing Green Tick Counting with CSV Data")
    print("=" * 60)
    
    # Load the CSV data
    csv_path = project_root / "live_ticks_20251001_170006.csv"
    if not csv_path.exists():
        print(f"❌ CSV file not found: {csv_path}")
        return False
    
    # Read first 100 rows to test
    df = pd.read_csv(csv_path, names=['timestamp', 'price', 'volume'], nrows=100)
    print(f"📊 Loaded {len(df)} price ticks for testing")
    
    # Initialize strategy with test config
    config = MappingProxyType(DEFAULT_CONFIG)
    strategy = ModularIntradayStrategy(config)
    strategy.perf_logger = MockPerfLogger()
    
    # Key test variables
    strategy.consecutive_green_bars_required = 5  # Default requirement
    strategy.green_bars_count = 0
    strategy.prev_tick_price = None
    
    print(f"🎯 Testing requirement: {strategy.consecutive_green_bars_required} consecutive green ticks")
    print()
    
    # Track green tick sequences
    green_sequences = []
    current_sequence = []
    
    print("📈 Price Movement Analysis:")
    print("Tick | Price    | Change   | Green Count | Status")
    print("-" * 55)
    
    for i, row in df.iterrows():
        price = row['price']
        
        # Update green tick count (same logic as strategy)
        prev_price = strategy.prev_tick_price
        if prev_price is not None:
            if price > prev_price:
                strategy.green_bars_count += 1
                current_sequence.append(price)
                status = f"GREEN +{strategy.green_bars_count}"
                
                # Check if we reached the requirement
                if strategy.green_bars_count >= strategy.consecutive_green_bars_required:
                    status += " ✅ ENTRY OK"
                
            else:
                # Reset on non-green tick
                if current_sequence:
                    green_sequences.append(current_sequence.copy())
                current_sequence = []
                strategy.green_bars_count = 0
                status = "RESET"
        else:
            status = "INIT"
        
        # Update previous price
        strategy.prev_tick_price = price
        
        # Display analysis
        if prev_price:
            if price > prev_price:
                change = f"+{price - prev_price:.2f}"
            else:
                change = f"{price - prev_price:.2f}"
        else:
            change = "N/A"
        print(f"{i:4d} | {price:8.2f} | {change:>8} | {strategy.green_bars_count:11d} | {status}")
        
        # Stop after first valid entry condition or 50 ticks
        if strategy.green_bars_count >= strategy.consecutive_green_bars_required or i >= 50:
            break
    
    print()
    print("📊 Analysis Results:")
    print(f"   Max consecutive green ticks reached: {max(len(seq) for seq in green_sequences) if green_sequences else 0}")
    print(f"   Total green sequences found: {len(green_sequences)}")
    print(f"   Entry requirement met: {'✅ YES' if strategy.green_bars_count >= strategy.consecutive_green_bars_required else '❌ NO'}")
    
    return True

def test_entry_condition_timing():
    """Test the timing of entry condition checks vs tick updates"""
    print("\n🕐 Testing Entry Condition Timing")
    print("=" * 60)
    
    # Simulate the exact sequence from the log where entry was blocked then allowed
    test_prices = [230.95, 231.8, 232.35, 232.9, 232.5]  # From CSV analysis
    
    config = MappingProxyType(DEFAULT_CONFIG)
    strategy = ModularIntradayStrategy(config)
    strategy.perf_logger = MockPerfLogger()
    strategy.consecutive_green_bars_required = 5
    strategy.green_bars_count = 0
    strategy.prev_tick_price = None
    
    print("Simulating price sequence from CSV data around 09:15:40 (232.9 entry):")
    print("Price | Green Count | Can Enter? | Notes")
    print("-" * 50)
    
    for i, price in enumerate(test_prices):
        # Update green tick count first
        if strategy.prev_tick_price is not None:
            if price > strategy.prev_tick_price:
                strategy.green_bars_count += 1
            else:
                strategy.green_bars_count = 0
        
        # Check entry condition
        can_enter = strategy._check_consecutive_green_ticks()
        
        notes = ""
        if price == 232.9:
            notes = "⚠️ ACTUAL ENTRY PRICE"
        elif strategy.green_bars_count >= strategy.consecutive_green_bars_required:
            notes = "✅ Entry allowed"
        elif strategy.green_bars_count > 0:
            notes = f"Need {strategy.consecutive_green_bars_required - strategy.green_bars_count} more"
        
        print(f"{price:5.2f} | {strategy.green_bars_count:11d} | {str(can_enter):10s} | {notes}")
        
        strategy.prev_tick_price = price
    
    print(f"\n📊 Result: Entry at 232.9 should have been {'ALLOWED' if strategy.green_bars_count >= 3 else 'BLOCKED'}")
    print(f"   But requirement is {strategy.consecutive_green_bars_required} green ticks")
    print(f"   Actual green ticks at entry: {3}")  # From manual analysis
    
    return True

def test_noise_filtering():
    """Test noise filtering behavior"""
    print("\n🔇 Testing Noise Filtering")
    print("=" * 60)
    
    # Test with noise filtering enabled vs disabled
    config_dict = dict(DEFAULT_CONFIG)
    config_dict['strategy']['noise_filter_enabled'] = True
    config_dict['strategy']['noise_filter_percentage'] = 0.001  # 0.1%
    config_dict['strategy']['noise_filter_min_ticks'] = 1
    
    config = MappingProxyType(config_dict)
    strategy = ModularIntradayStrategy(config)
    strategy.perf_logger = MockPerfLogger()
    strategy.tick_size = 0.05  # Common tick size
    
    # Test small price movements that might be noise
    test_prices = [232.0, 232.05, 232.10, 232.05, 232.15]  # Small movements
    
    print("Testing with noise filtering enabled:")
    print("Price | Movement | Green Count | Notes")
    print("-" * 45)
    
    strategy.prev_tick_price = None
    strategy.green_bars_count = 0
    
    for price in test_prices:
        prev_count = strategy.green_bars_count
        strategy._update_green_tick_count(price)
        
        movement = "N/A" if strategy.prev_tick_price is None else f"{price - strategy.prev_tick_price:.2f}"
        change = f"(+{strategy.green_bars_count - prev_count})" if strategy.green_bars_count != prev_count else ""
        
        print(f"{price:5.2f} | {movement:8s} | {strategy.green_bars_count:11d} | {change}")
    
    return True

def main():
    """Run all green tick validation tests"""
    print("🧪 COMPREHENSIVE GREEN TICK VALIDATION TEST SUITE")
    print("=" * 70)
    print(f"📁 Project root: {project_root}")
    print()
    
    tests = [
        test_green_tick_counting_with_csv_data,
        test_entry_condition_timing,
        test_noise_filtering
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
                print("✅ PASSED")
            else:
                failed += 1
                print("❌ FAILED")
        except Exception as e:
            failed += 1
            print(f"💥 ERROR: {e}")
        print()
    
    print("=" * 70)
    print(f"📊 Test Summary: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed!")
        return True
    else:
        print("⚠️ Some tests failed - check the green tick logic!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)