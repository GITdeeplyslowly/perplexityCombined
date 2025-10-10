#!/usr/bin/env python3
"""
EMA Crossover and Green Tick Logic Comparison

Compares the implementation between backtest (researchStrategy.py) and 
forward test (liveStrategy.py) to identify any differences that might 
explain behavioral variations.
"""

import re
import os
from pathlib import Path
from typing import Dict, List, Tuple

def extract_method_code(file_path: str, method_name: str) -> str:
    """Extract method code from a Python file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the method definition
    pattern = rf'def {method_name}\(.*?\):'
    match = re.search(pattern, content)
    
    if not match:
        return f"Method {method_name} not found"
    
    start_pos = match.start()
    lines = content[:start_pos].count('\n')
    
    # Extract method body (approximate - gets the method and some context)
    method_lines = content[start_pos:].split('\n')
    extracted_lines = []
    indent_level = None
    
    for i, line in enumerate(method_lines):
        if i == 0:  # Method definition line
            extracted_lines.append(line)
            continue
            
        if line.strip() == '':
            extracted_lines.append(line)
            continue
            
        current_indent = len(line) - len(line.lstrip())
        
        if indent_level is None and line.strip():
            indent_level = current_indent
            
        if line.strip() and current_indent <= 4 and i > 1:  # Next method or class
            break
            
        extracted_lines.append(line)
    
    return '\n'.join(extracted_lines[:50])  # Limit to first 50 lines

def compare_methods():
    """Compare key methods between backtest and forward test implementations"""
    
    print("🔍 EMA CROSSOVER & GREEN TICK LOGIC COMPARISON")
    print("=" * 80)
    print("Comparing backtest (researchStrategy.py) vs forward test (liveStrategy.py)")
    print()
    
    base_path = "c:/Users/user/projects/Perplexity Combined/myQuant/core"
    backtest_file = f"{base_path}/researchStrategy.py"
    forward_file = f"{base_path}/liveStrategy.py"
    
    methods_to_compare = [
        "entry_signal",
        "can_enter_new_position", 
        "_check_consecutive_green_ticks",
        "_update_green_tick_count"
    ]
    
    for method in methods_to_compare:
        print(f"📊 METHOD: {method}")
        print("-" * 60)
        
        print(f"\n🔄 BACKTEST (researchStrategy.py):")
        print("```python")
        backtest_code = extract_method_code(backtest_file, method)
        print(backtest_code)
        print("```")
        
        print(f"\n🔴 FORWARD TEST (liveStrategy.py):")
        print("```python")
        forward_code = extract_method_code(forward_file, method)
        print(forward_code)
        print("```")
        
        print("\n" + "="*80 + "\n")

def analyze_key_differences():
    """Analyze and highlight key differences"""
    
    print("🎯 KEY DIFFERENCES ANALYSIS")
    print("=" * 80)
    
    differences = {
        "EMA Crossover Logic": {
            "backtest": "Uses pre-calculated 'ema_bullish' from DataFrame",
            "forward_test": "Calculates ema_bullish real-time: fast_ema > slow_ema",
            "impact": "Different timing - backtest uses batch signals, forward test uses incremental"
        },
        
        "Green Tick Validation": {
            "backtest": "Called in can_enter_new_position() before signal generation",  
            "forward_test": "Called in can_enter_new_position() before signal generation",
            "impact": "Both should be identical - race condition was fixed"
        },
        
        "Signal Generation Flow": {
            "backtest": "entry_signal() checks indicators -> can_enter_new_position() checks constraints",
            "forward_test": "_generate_signal_from_tick() calls can_enter_new_position() first, then entry_signal()",
            "impact": "Order of validation differs - constraints checked before vs after indicators"
        },
        
        "Noise Filter Logic": {
            "backtest": "May use different noise filtering parameters",
            "forward_test": "Uses strict config-driven noise filtering",
            "impact": "Different green tick counting behavior"
        }
    }
    
    for category, details in differences.items():
        print(f"\n📋 {category}")
        print(f"   Backtest:     {details['backtest']}")
        print(f"   Forward Test: {details['forward_test']}")
        print(f"   Impact:       {details['impact']}")

def analyze_ema_crossover_implementations():
    """Analyze EMA crossover calculation differences"""
    
    print("\n🔬 EMA CROSSOVER CALCULATION ANALYSIS")
    print("=" * 80)
    
    print("""
📊 BACKTEST EMA CROSSOVER:
- Uses batch processing with pandas DataFrame operations
- Pre-calculates ema_bullish column: df['ema_bull'] = df['ema_fast'] > df['ema_slow']
- Signal detection uses crossover events: (current > previous) & (previous <= previous)
- Works with complete data series

🔴 FORWARD TEST EMA CROSSOVER:  
- Uses incremental processing with IncrementalEMA trackers
- Calculates ema_bullish real-time: fast_ema_val > slow_ema_val
- No crossover event detection - just current state comparison
- Works tick-by-tick with single data points

🎯 KEY DIFFERENCE:
Backtest detects EMA CROSSOVER EVENTS (when fast crosses above slow)
Forward test checks EMA POSITION STATE (if fast is currently above slow)

This explains why forward test might have different entry behavior!
""")

def main():
    """Main comparison analysis"""
    
    try:
        compare_methods()
        analyze_key_differences() 
        analyze_ema_crossover_implementations()
        
        print("\n" + "=" * 80)
        print("📋 ANALYSIS COMPLETE")
        print("\nKey Finding: EMA crossover logic differs significantly!")
        print("- Backtest: Detects crossover EVENTS")  
        print("- Forward test: Checks position STATE")
        print("\nThis could explain behavioral differences between backtest and forward test results.")
        
    except Exception as e:
        print(f"💥 Error during analysis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()