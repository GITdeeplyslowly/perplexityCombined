#!/usr/bin/env python3
"""
First Trade Detailed Analysis

Analyzes the very first trade to determine if all entry conditions were properly met.
This will help identify any remaining bugs in the entry validation system.
"""

import pandas as pd
import numpy as np
from datetime import datetime
import re
from pathlib import Path

def calculate_ema(prices, period):
    """Calculate Exponential Moving Average"""
    return prices.ewm(span=period, adjust=False).mean()

def analyze_first_trade_conditions():
    """Analyze the first trade in detail"""
    print("🔍 FIRST TRADE DETAILED ANALYSIS")
    print("=" * 60)
    print("Analyzing: Entry at ₹232.90 with timestamp 16:35:59")
    print()
    
    # Load CSV data
    print("📊 Loading market data...")
    df = pd.read_csv("live_ticks_20251001_170006.csv", names=['timestamp', 'price', 'volume'], skiprows=1)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Find the 232.90 entry point
    entry_matches = df[abs(df['price'] - 232.90) < 0.01]
    if entry_matches.empty:
        print("❌ No price match found for 232.90")
        return False
    
    entry_idx = entry_matches.index[0]  # First occurrence
    entry_row = df.loc[entry_idx]
    
    print(f"📍 Entry Point Found:")
    print(f"   Index: {entry_idx}")
    print(f"   Time: {entry_row['timestamp']}")
    print(f"   Price: ₹{entry_row['price']}")
    print()
    
    # Calculate EMAs up to entry point
    print("📈 Calculating EMA values...")
    df_subset = df.iloc[:entry_idx+1].copy()
    df_subset['fast_ema'] = calculate_ema(df_subset['price'], 9)
    df_subset['slow_ema'] = calculate_ema(df_subset['price'], 21)
    
    entry_fast_ema = df_subset.iloc[-1]['fast_ema']
    entry_slow_ema = df_subset.iloc[-1]['slow_ema']
    ema_condition = entry_fast_ema > entry_slow_ema
    
    print(f"   Fast EMA (9): ₹{entry_fast_ema:.2f}")
    print(f"   Slow EMA (21): ₹{entry_slow_ema:.2f}")
    print(f"   EMA Crossover: {ema_condition} ({'✅' if ema_condition else '❌'})")
    print()
    
    # Analyze green tick sequence leading to entry
    print("🟢 Green Tick Analysis:")
    print("   Analyzing price movements leading to entry...")
    
    # Get last 10 ticks before entry
    start_idx = max(0, entry_idx - 10)
    sequence = df.iloc[start_idx:entry_idx+1].copy()
    
    print(f"\n   Price Sequence (last {len(sequence)} ticks):")
    print("   #  | Time     | Price    | Change   | Green? | Count")
    print("   " + "-" * 55)
    
    green_count = 0
    for i, (idx, row) in enumerate(sequence.iterrows()):
        if i == 0:
            change = "N/A"
            is_green = False
        else:
            prev_price = sequence.iloc[i-1]['price']
            change = row['price'] - prev_price
            is_green = change > 0
            
            if is_green:
                green_count += 1
            else:
                green_count = 0
        
        change_str = f"{change:+.2f}" if i > 0 else "N/A"
        green_str = "✅" if i > 0 and is_green else "❌" if i > 0 else "➖"
        
        marker = " 🎯" if idx == entry_idx else ""
        
        print(f"   {i:2d} | {row['timestamp'].strftime('%H:%M:%S')} | {row['price']:8.2f} | {change_str:8s} | {green_str:6s} | {green_count:5d}{marker}")
    
    green_tick_condition = green_count >= 5
    print(f"\n   Final Green Tick Count: {green_count}")
    print(f"   Green Tick Condition (≥5): {green_tick_condition} ({'✅' if green_tick_condition else '❌'})")
    print()
    
    # Check other conditions that might be enabled
    print("📋 Other Entry Conditions:")
    
    # Session timing check
    entry_time = entry_row['timestamp']
    session_start = entry_time.replace(hour=9, minute=15, second=0, microsecond=0)
    session_end = entry_time.replace(hour=15, minute=30, second=0, microsecond=0)
    
    in_session = session_start <= entry_time <= session_end
    print(f"   Session Time Check: {in_session} ({'✅' if in_session else '❌'})")
    print(f"   Entry Time: {entry_time.strftime('%H:%M:%S')}")
    print(f"   Session: {session_start.strftime('%H:%M')}-{session_end.strftime('%H:%M')}")
    
    # Check if this is first trade (no position limit exceeded)
    print(f"   First Trade: ✅ (no existing positions)")
    print()
    
    # Overall analysis
    print("🔎 ENTRY VALIDATION SUMMARY:")
    print("=" * 40)
    
    all_conditions = [
        ("EMA Crossover (Fast > Slow)", ema_condition),
        ("Green Ticks (≥5)", green_tick_condition),
        ("Session Timing", in_session),
        ("Position Limits", True)  # First trade
    ]
    
    for condition_name, met in all_conditions:
        status = "✅ MET" if met else "❌ NOT MET"
        print(f"   {condition_name:25s}: {status}")
    
    all_met = all(met for _, met in all_conditions)
    print(f"\n   Overall Entry Valid: {all_met} ({'✅' if all_met else '❌'})")
    
    # Log analysis
    print(f"\n🔍 LOG ANALYSIS:")
    print("=" * 40)
    print("   Log shows:")
    print("   • 16:35:59 - ENTRY BLOCKED (#1): Need 5 green ticks, have 0")
    print("   • 16:35:59 - Opened position d5a8bf54")
    print("   • 16:35:59 - Entry price: ₹232.90")
    print()
    
    if not green_tick_condition:
        print("🚨 ISSUE IDENTIFIED:")
        print(f"   Green tick condition NOT MET ({green_count}/5)")
        print("   But trade was executed anyway!")
        print("   This suggests a remaining race condition or validation bypass.")
    elif not all_met:
        failed_conditions = [name for name, met in all_conditions if not met]
        print("🚨 ISSUE IDENTIFIED:")
        print(f"   Failed conditions: {', '.join(failed_conditions)}")
        print("   But trade was executed anyway!")
    else:
        print("✅ ALL CONDITIONS MET:")
        print("   Trade execution was correct!")
    
    return True

def analyze_tick_by_tick_around_entry():
    """Analyze tick-by-tick processing around the entry"""
    print("\n🎯 TICK-BY-TICK PROCESSING ANALYSIS")
    print("=" * 60)
    
    # Load data
    df = pd.read_csv("live_ticks_20251001_170006.csv", names=['timestamp', 'price', 'volume'], skiprows=1)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Find entry point
    entry_matches = df[abs(df['price'] - 232.90) < 0.01]
    if entry_matches.empty:
        return False
    
    entry_idx = entry_matches.index[0]
    
    # Analyze the exact sequence that might have triggered the entry
    print("Analyzing potential rapid tick processing scenario...")
    print()
    
    # Look at ticks around the entry point
    start_idx = max(0, entry_idx - 5)
    end_idx = min(len(df), entry_idx + 5)
    
    analysis_window = df.iloc[start_idx:end_idx+1].copy()
    
    print("Tick-by-tick green count progression:")
    print("Tick | Time     | Price    | Green Count | Entry Check?")
    print("-" * 55)
    
    green_count = 0
    for i, (idx, row) in enumerate(analysis_window.iterrows()):
        # Simulate green tick counting
        if i > 0:
            prev_price = analysis_window.iloc[i-1]['price']
            if row['price'] > prev_price:
                green_count += 1
            else:
                green_count = 0
        
        # Check if this could be an entry point
        could_enter = green_count >= 5
        is_actual_entry = idx == entry_idx
        
        entry_marker = " 🎯 ENTRY" if is_actual_entry else " ✅ COULD ENTER" if could_enter else ""
        
        print(f"{i:4d} | {row['timestamp'].strftime('%H:%M:%S')} | {row['price']:8.2f} | {green_count:11d} | {entry_marker}")
    
    return True

def main():
    """Main analysis function"""
    try:
        if not analyze_first_trade_conditions():
            return False
        
        analyze_tick_by_tick_around_entry()
        
        print("\n" + "=" * 60)
        print("📋 ANALYSIS COMPLETE")
        print("Check the results above to see if all entry conditions were met.")
        
        return True
        
    except Exception as e:
        print(f"💥 Error during analysis: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)