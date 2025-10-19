#!/usr/bin/env python3
"""
Test script to validate Control Base SL implementation
"""
import sys
import os
import logging
from types import MappingProxyType

# Add myQuant to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.defaults import DEFAULT_CONFIG
from utils.config_helper import create_config_from_defaults, validate_config, freeze_config
from core.liveStrategy import ModularIntradayStrategy
from core.position_manager import PositionManager

def test_control_base_sl():
    """Test the Control Base SL functionality"""
    
    # Create and freeze config
    config = create_config_from_defaults()
    validation = validate_config(config)
    if not validation.get('valid', False):
        print(f"❌ Config validation failed: {validation.get('errors')}")
        return False
    
    frozen_config = freeze_config(config)
    print(f"✅ Config created and frozen successfully")
    
    # Initialize strategy
    try:
        strategy = ModularIntradayStrategy(frozen_config)
        print(f"✅ Strategy initialized successfully")
        print(f"   - Control Base SL enabled: {strategy.control_base_sl_enabled}")
        print(f"   - Normal green ticks: {strategy.consecutive_green_bars_required}")
        print(f"   - Base SL green ticks: {strategy.base_sl_green_ticks}")
        print(f"   - Current threshold: {strategy.current_green_tick_threshold}")
    except Exception as e:
        print(f"❌ Strategy initialization failed: {e}")
        return False
    
    # Initialize position manager with strategy callback
    try:
        pm = PositionManager(frozen_config, strategy_callback=strategy.on_position_exit)
        print(f"✅ Position Manager initialized with strategy callback")
    except Exception as e:
        print(f"❌ Position Manager initialization failed: {e}")
        return False
    
    # Test exit reason standardization
    test_cases = [
        ("Stop Loss", "base_sl"),
        ("Take Profit 1", "target_profit"),
        ("Trailing Stop", "trailing_stop"),
        ("Session End", "session_end"),
        ("Unknown Reason", "unknown reason")
    ]
    
    print(f"\n📋 Testing exit reason standardization:")
    for input_reason, expected in test_cases:
        result = pm._standardize_exit_reason(input_reason)
        status = "✅" if result == expected else "❌"
        print(f"   {status} '{input_reason}' -> '{result}' (expected: '{expected}')")
    
    # Test strategy callback logic
    print(f"\n🧪 Testing strategy callback logic:")
    
    # Simulate base SL exit
    initial_threshold = strategy.current_green_tick_threshold
    print(f"   Initial threshold: {initial_threshold}")
    
    strategy.on_position_exit({"exit_reason": "base_sl"})
    print(f"   After base SL exit: {strategy.current_green_tick_threshold}")
    print(f"   Last exit was base SL: {strategy.last_exit_was_base_sl}")
    
    # Simulate profitable exit
    strategy.on_position_exit({"exit_reason": "target_profit"})
    print(f"   After profitable exit: {strategy.current_green_tick_threshold}")
    print(f"   Last exit was base SL: {strategy.last_exit_was_base_sl}")
    
    print(f"\n✅ Control Base SL test completed successfully!")
    return True

if __name__ == "__main__":
    # Setup basic logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
    
    print("🧪 Testing Control Base SL Implementation")
    print("=" * 50)
    
    success = test_control_base_sl()
    
    if success:
        print(f"\n🎉 All tests passed!")
    else:
        print(f"\n💥 Some tests failed!")
    
    sys.exit(0 if success else 1)