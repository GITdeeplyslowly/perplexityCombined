#!/usr/bin/env python3
"""
Test HTF trend fix for the KeyError: 'close' issue
"""

import pandas as pd
import sys
import os
from datetime import datetime
from types import MappingProxyType

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'myQuant'))

def test_htf_trend_fix():
    """Test HTF trend processing with CSV data"""
    
    print("🔍 Testing HTF trend fix...")
    
    # Create a minimal config for testing
    test_config = {
        'strategy': {
            'use_ema_crossover': True,
            'use_macd': True,
            'use_vwap': True,
            'use_rsi_filter': False,
            'use_htf_trend': True,  # Enable HTF trend
            'use_bollinger_bands': False,
            'use_atr': False,
            'fast_ema': 9,
            'slow_ema': 21,
            'macd_fast': 12,
            'macd_slow': 26,
            'macd_signal': 9,
            'htf_period': 20,  # HTF period
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'consecutive_green_bars': 5,
            'atr_len': 14,
            'noise_filter_enabled': False,
            'noise_filter_percentage': 0.001,
            'noise_filter_min_ticks': 1.0
        },
        'session': {
            'start_hour': 9,
            'start_min': 15,
            'end_hour': 15,
            'end_min': 30,
            'start_buffer_minutes': 5,
            'end_buffer_minutes': 20,
            'no_trade_start_minutes': 5,
            'no_trade_end_minutes': 20,
            'timezone': 'Asia/Kolkata'
        },
        'risk': {
            'max_positions_per_day': 25,
            'base_sl_points': 15
        },
        'instrument': {
            'symbol': 'TEST_SYMBOL',
            'tick_size': 0.05,
            'lot_size': 15
        }
    }
    
    # Freeze config (required by liveStrategy)
    frozen_config = MappingProxyType(test_config)
    
    # Load sample CSV data
    csv_file = "live_ticks_20251001_170006.csv"
    if not os.path.exists(csv_file):
        print(f"❌ CSV file {csv_file} not found!")
        return False
    
    df = pd.read_csv(csv_file)
    print(f"✅ Loaded {len(df)} rows from CSV")
    
    try:
        # Import the strategy (this should work now)
        from core.liveStrategy import ModularIntradayStrategy
        
        # Create strategy instance with HTF trend enabled
        strategy = ModularIntradayStrategy(frozen_config)
        print(f"✅ Strategy created successfully with HTF trend enabled")
        
        # Test processing a few ticks
        for i in range(min(5, len(df))):
            row = df.iloc[i]
            tick_data = {
                'timestamp': pd.to_datetime(row['timestamp']),
                'price': row['price'],
                'volume': row['volume']
            }
            
            print(f"📊 Processing tick {i+1}: price={tick_data['price']}, volume={tick_data['volume']}")
            
            # This should not raise KeyError: 'close' anymore
            result = strategy.on_tick(tick_data)
            print(f"✅ Tick {i+1} processed successfully, result: {result}")
        
        print(f"\n🎉 HTF trend fix verified successfully!")
        return True
        
    except KeyError as e:
        if "'close'" in str(e):
            print(f"❌ KeyError: 'close' still occurring: {e}")
            return False
        else:
            print(f"❌ Different KeyError: {e}")
            return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_htf_trend_fix()
    if success:
        print(f"\n✅ All tests passed! HTF trend should work without KeyError.")
    else:
        print(f"\n❌ Tests failed!")
    
    sys.exit(0 if success else 1)