#!/usr/bin/env python3
"""
EMA Crossover Analysis Tool

This tool analyzes the log file and CSV data to validate that EMA crossover signals
are working correctly. It will:
1. Extract trade entries from the log
2. Find corresponding price data in CSV
3. Calculate EMA values around entry points
4. Verify EMA crossover conditions were met
"""

import pandas as pd
import numpy as np
from datetime import datetime
import re
from pathlib import Path

def calculate_ema(prices, period):
    """Calculate Exponential Moving Average"""
    return prices.ewm(span=period, adjust=False).mean()

def analyze_ema_crossover_validation():
    """Analyze if EMA crossover conditions were properly validated"""
    print("🔍 EMA CROSSOVER VALIDATION ANALYSIS")
    print("=" * 60)
    
    # Load CSV data
    csv_path = Path("live_ticks_20251001_170006.csv")
    if not csv_path.exists():
        print(f"❌ CSV file not found: {csv_path}")
        return False
    
    print("📊 Loading price data...")
    df = pd.read_csv(csv_path, names=['timestamp', 'price', 'volume'], skiprows=1)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    print(f"   Loaded {len(df):,} price ticks")
    
    # Calculate EMAs
    print("📈 Calculating EMAs (Fast=9, Slow=21)...")
    df['fast_ema'] = calculate_ema(df['price'], 9)
    df['slow_ema'] = calculate_ema(df['price'], 21)
    df['ema_crossover'] = df['fast_ema'] > df['slow_ema']
    df['crossover_signal'] = df['ema_crossover'] & (~df['ema_crossover'].shift(1).fillna(False))
    
    # Load log data
    log_path = Path("log.txt")
    if not log_path.exists():
        print(f"❌ Log file not found: {log_path}")
        return False
    
    print("📋 Extracting trade entries from log...")
    with open(log_path, 'r', encoding='utf-8') as f:
        log_content = f.read()
    
    # Extract trade entries
    entry_pattern = r'Entry price: â‚¹([\d.]+) per unit'
    entries = re.findall(entry_pattern, log_content)
    
    # Get unique entry prices (first 10)
    unique_entries = list(dict.fromkeys(entries))[:10]
    print(f"   Found {len(entries)} total entries, analyzing first {len(unique_entries)} unique prices")
    
    print("\n🎯 EMA CROSSOVER ANALYSIS FOR EACH ENTRY:")
    print("=" * 80)
    
    validation_results = []
    
    for i, entry_price in enumerate(unique_entries, 1):
        price_val = float(entry_price)
        print(f"\n📌 Entry #{i}: ₹{price_val}")
        print("-" * 50)
        
        # Find closest price match in CSV
        price_matches = df[abs(df['price'] - price_val) < 0.01]
        
        if price_matches.empty:
            print(f"   ❌ No exact price match found in CSV data")
            validation_results.append({
                'entry': i,
                'price': price_val,
                'csv_match': False,
                'ema_crossover': None,
                'signal_valid': False
            })
            continue
        
        # Get the first match (earliest time)
        match_idx = price_matches.index[0]
        match_row = df.loc[match_idx]
        
        print(f"   📅 Time: {match_row['timestamp']}")
        print(f"   💰 Price: ₹{match_row['price']:.2f}")
        
        # Check EMA values at entry point
        if pd.isna(match_row['fast_ema']) or pd.isna(match_row['slow_ema']):
            print(f"   ⚠️  EMAs not yet calculated (insufficient data)")
            validation_results.append({
                'entry': i,
                'price': price_val,
                'csv_match': True,
                'ema_crossover': None,
                'signal_valid': False,
                'reason': 'EMAs not calculated'
            })
            continue
        
        fast_ema = match_row['fast_ema']
        slow_ema = match_row['slow_ema']
        crossover_condition = fast_ema > slow_ema
        
        print(f"   📊 Fast EMA (9): ₹{fast_ema:.2f}")
        print(f"   📊 Slow EMA (21): ₹{slow_ema:.2f}")
        print(f"   🔄 Fast > Slow: {crossover_condition} ({'✅' if crossover_condition else '❌'})")
        
        # Check for recent crossover signal
        recent_crossover = False
        if match_idx >= 50:  # Check last 50 ticks for crossover
            recent_data = df.loc[match_idx-50:match_idx]
            recent_crossover = recent_data['crossover_signal'].any()
        
        print(f"   🎯 Recent Crossover Signal: {recent_crossover} ({'✅' if recent_crossover else '❌'})")
        
        # Overall validation
        signal_valid = crossover_condition and (recent_crossover or match_idx < 50)
        print(f"   ✅ Entry Valid: {signal_valid}")
        
        validation_results.append({
            'entry': i,
            'price': price_val,
            'csv_match': True,
            'fast_ema': fast_ema,
            'slow_ema': slow_ema,
            'ema_crossover': crossover_condition,
            'recent_crossover': recent_crossover,
            'signal_valid': signal_valid
        })
    
    # Summary analysis
    print("\n📊 VALIDATION SUMMARY:")
    print("=" * 50)
    
    valid_entries = sum(1 for r in validation_results if r.get('signal_valid', False))
    total_analyzed = len([r for r in validation_results if r.get('csv_match', False)])
    
    print(f"   Total Entries Analyzed: {total_analyzed}")
    print(f"   Valid EMA Crossovers: {valid_entries}")
    print(f"   Invalid Entries: {total_analyzed - valid_entries}")
    print(f"   Success Rate: {(valid_entries/total_analyzed*100):.1f}%" if total_analyzed > 0 else "N/A")
    
    # Detailed breakdown
    print(f"\n📋 Detailed Results:")
    for result in validation_results:
        if result.get('csv_match'):
            status = "✅ VALID" if result.get('signal_valid') else "❌ INVALID"
            reason = result.get('reason', 'EMA crossover check')
            print(f"   Entry #{result['entry']} (₹{result['price']:.2f}): {status} - {reason}")
    
    return True

def analyze_ema_trend_around_entries():
    """Analyze the EMA trend around the first few entries"""
    print("\n🔍 EMA TREND ANALYSIS AROUND ENTRIES")
    print("=" * 60)
    
    # Load and prepare data
    df = pd.read_csv("live_ticks_20251001_170006.csv", names=['timestamp', 'price', 'volume'], skiprows=1)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['fast_ema'] = calculate_ema(df['price'], 9)
    df['slow_ema'] = calculate_ema(df['price'], 21)
    
    # Analyze around first entry point (232.9)
    entry_prices = [232.9, 233.9, 216.5]
    
    for price in entry_prices:
        print(f"\n📌 Analyzing trend around ₹{price}")
        print("-" * 40)
        
        # Find the price point
        match_idx = df[abs(df['price'] - price) < 0.5].index
        if len(match_idx) == 0:
            print("   No close matches found")
            continue
            
        idx = match_idx[0]
        start_idx = max(0, idx - 30)
        end_idx = min(len(df), idx + 10)
        
        trend_data = df.iloc[start_idx:end_idx]
        
        print("   Recent EMA Trend (last 10 points before entry):")
        print("   Time        | Price  | Fast EMA | Slow EMA | Cross?")
        print("   " + "-" * 55)
        
        for i, row in trend_data.tail(10).iterrows():
            cross_status = "✅" if row['fast_ema'] > row['slow_ema'] else "❌"
            print(f"   {row['timestamp'].strftime('%H:%M:%S')} | {row['price']:6.2f} | {row['fast_ema']:8.2f} | {row['slow_ema']:8.2f} | {cross_status}")
    
    return True

def main():
    """Main analysis function"""
    print("🧪 EMA CROSSOVER STRATEGY VALIDATION")
    print("=" * 70)
    print("Analyzing EMA crossover indicator performance against actual trades")
    print()
    
    try:
        # Main validation analysis
        if not analyze_ema_crossover_validation():
            return False
        
        # Trend analysis
        analyze_ema_trend_around_entries()
        
        print("\n" + "=" * 70)
        print("🎯 CONCLUSION:")
        print("   • EMA crossover validation completed")
        print("   • Check results above for signal accuracy")
        print("   • Fast EMA (9) vs Slow EMA (21) crossover analysis")
        
        return True
        
    except Exception as e:
        print(f"💥 Error during analysis: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)