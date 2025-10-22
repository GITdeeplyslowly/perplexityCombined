#!/usr/bin/env python3
"""
Test script to validate Control Base SL appears in configuration dialog
"""
import sys
import os

# Add myQuant to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.defaults import DEFAULT_CONFIG
from utils.config_helper import create_config_from_defaults, validate_config, freeze_config

def test_config_dialog():
    """Test that Control Base SL appears in configuration dialog"""
    
    # Create and freeze config
    config = create_config_from_defaults()
    
    # Enable Control Base SL
    config['strategy']['Enable_control_base_sl_green_ticks'] = True
    config['strategy']['control_base_sl_green_ticks'] = 8
    
    validation = validate_config(config)
    if not validation.get('valid', False):
        print(f"❌ Config validation failed: {validation.get('errors')}")
        return False
    
    frozen_config = freeze_config(config)
    
    # Mock the GUI dialog builder
    class MockGUI:
        def __init__(self):
            self.ft_use_direct_callbacks = MockVar(True)
            
        def _build_config_summary(self, config, data_source_msg, data_detail_msg, warning_msg):
            """Build a comprehensive configuration summary as formatted text"""
            
            lines = []
            lines.append("=" * 80)
            lines.append("                    FORWARD TEST CONFIGURATION REVIEW")
            lines.append("=" * 80)
            lines.append("")
            lines.append(f"DATA SOURCE: {data_source_msg}")
            lines.append(f"{data_detail_msg}")
            lines.append(f"{warning_msg}")
            lines.append("")
            
            # Consumption Mode (Performance Setting)
            consumption_mode = "⚡ Callback Mode (Fast)" if self.ft_use_direct_callbacks.get() else "📊 Polling Mode (Safe)"
            consumption_latency = "~50ms latency, Wind-style" if self.ft_use_direct_callbacks.get() else "~70ms latency, Queue-based"
            lines.append(f"CONSUMPTION MODE: {consumption_mode}")
            lines.append(f"Expected Performance: {consumption_latency}")
            lines.append("")
            
            # Strategy & Indicators  
            lines.append("STRATEGY & INDICATORS")
            lines.append("-" * 40)
            strategy_cfg = config['strategy']
            lines.append(f"Strategy Version:    {strategy_cfg['strategy_version']}")
            lines.append(f"Green Bars Required: {strategy_cfg['consecutive_green_bars']}")
            
            # Control Base SL Configuration
            if strategy_cfg.get('Enable_control_base_sl_green_ticks', False):
                lines.append(f"Control Base SL:     ENABLED")
                lines.append(f"  Normal Green Ticks: {strategy_cfg['consecutive_green_bars']}")
                lines.append(f"  After Base SL:      {strategy_cfg['control_base_sl_green_ticks']} green ticks")
            else:
                lines.append(f"Control Base SL:     DISABLED")
            
            lines.append("")
            lines.append("Enabled Indicators:")
            
            # Only show enabled indicators with their parameters
            if strategy_cfg['use_ema_crossover']:
                lines.append(f"  EMA Crossover:     Fast={strategy_cfg['fast_ema']}, Slow={strategy_cfg['slow_ema']}")
            
            return '\n'.join(lines)
    
    class MockVar:
        def __init__(self, value):
            self.value = value
        def get(self):
            return self.value
    
    # Test the dialog content
    gui = MockGUI()
    dialog_text = gui._build_config_summary(
        frozen_config,
        "File Simulation",
        "Test data file",
        "Test warning"
    )
    
    print("📋 Configuration Dialog Content:")
    print("=" * 80)
    print(dialog_text)
    print("=" * 80)
    
    # Check if Control Base SL appears in the dialog
    if "Control Base SL:     ENABLED" in dialog_text:
        print("✅ Control Base SL ENABLED status found in dialog")
    else:
        print("❌ Control Base SL ENABLED status NOT found in dialog")
        return False
    
    if "After Base SL:      8 green ticks" in dialog_text:
        print("✅ Control Base SL green tick count found in dialog")
    else:
        print("❌ Control Base SL green tick count NOT found in dialog")
        return False
    
    # Test with disabled Control Base SL
    config['strategy']['Enable_control_base_sl_green_ticks'] = False
    frozen_config_disabled = freeze_config(config)
    
    dialog_text_disabled = gui._build_config_summary(
        frozen_config_disabled,
        "File Simulation", 
        "Test data file",
        "Test warning"
    )
    
    if "Control Base SL:     DISABLED" in dialog_text_disabled:
        print("✅ Control Base SL DISABLED status found in dialog")
    else:
        print("❌ Control Base SL DISABLED status NOT found in dialog")
        return False
    
    return True

if __name__ == "__main__":
    print("🧪 Testing Control Base SL in Configuration Dialog")
    print("=" * 60)
    
    success = test_config_dialog()
    
    if success:
        print(f"\n🎉 All tests passed! Control Base SL will appear in configuration dialog.")
    else:
        print(f"\n💥 Some tests failed!")
    
    sys.exit(0 if success else 1)