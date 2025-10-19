#!/usr/bin/env python3
"""
Test dynamic configuration table with different enabled/disabled features.
Shows how the config table adapts to various indicator and risk parameter combinations.
"""

import pandas as pd
from datetime import datetime

def build_dynamic_config_table(config, start_time=None, end_time=None):
    """
    Simulate the dynamic get_config_table method to test different configurations.
    """
    config_data = []
    
    # Extract sections
    inst = config.get('instrument', {})
    capital = config.get('capital', {})
    risk = config.get('risk', {})
    session = config.get('session', {})
    strategy = config.get('strategy', {})
    data_sim = config.get('data_simulation', {})
    
    # DATA SOURCE section - Always show
    if data_sim.get('enabled', False):
        config_data.append(("Data Source Type", "FILE DATA SIMULATION"))
        if data_sim.get('file_path'):
            config_data.append(("Historical File", data_sim.get('file_path')))
        config_data.append(("Data Warning", "Uses HISTORICAL data, not live market prices"))
    else:
        config_data.append(("Data Source Type", "LIVE WEBSTREAM"))
        config_data.append(("Data Status", "Live market data"))
    
    # INSTRUMENT section - Core params
    config_data.append(("Symbol", inst.get('symbol', 'N/A')))
    config_data.append(("Exchange", inst.get('exchange', 'N/A')))
    config_data.append(("Product Type", inst.get('product_type', 'N/A')))
    
    if inst.get('lot_size') is not None:
        config_data.append(("Lot Size", inst.get('lot_size')))
    if inst.get('tick_size') is not None:
        config_data.append(("Tick Size", inst.get('tick_size')))
    
    # SESSION section - Dynamic
    if session.get('start_hour') is not None and session.get('start_min') is not None:
        config_data.append(("Session Start", f"{session.get('start_hour', 9):02d}:{session.get('start_min', 15):02d}"))
    if session.get('end_hour') is not None and session.get('end_min') is not None:
        config_data.append(("Session End", f"{session.get('end_hour', 15):02d}:{session.get('end_min', 30):02d}"))
    
    if session.get('auto_stop_enabled') is not None:
        config_data.append(("Auto Stop", "Enabled" if session.get('auto_stop_enabled') else "Disabled"))
    if session.get('max_loss_per_day') is not None:
        config_data.append(("Max Loss/Day", session.get('max_loss_per_day')))
    
    # CAPITAL section
    if capital.get('initial_capital') is not None:
        config_data.append(("Initial Capital", capital.get('initial_capital')))
    
    # RISK MANAGEMENT section - Dynamic
    if risk.get('max_positions_per_day') is not None:
        config_data.append(("Max Trades/Day", risk.get('max_positions_per_day')))
    if risk.get('base_sl_points') is not None:
        config_data.append(("Base Stop Loss", f"{risk.get('base_sl_points')} points"))
    
    # Take Profit - only if configured
    tp_points = risk.get('tp_points', [])
    tp_percents = risk.get('tp_percents', [])
    if tp_points and len(tp_points) > 0:
        config_data.append(("Take Profit Levels", f"{len(tp_points)} levels"))
        config_data.append(("TP Points", str(tp_points)))
        if tp_percents and len(tp_percents) > 0:
            config_data.append(("TP Percentages", str(tp_percents)))
    
    # Trail Stop - only if enabled
    if risk.get('use_trail_stop') is True:
        config_data.append(("Trail Stop", "Enabled"))
        if risk.get('trail_activation_points') is not None:
            config_data.append(("Trail Activation", f"{risk.get('trail_activation_points')} points"))
        if risk.get('trail_distance_points') is not None:
            config_data.append(("Trail Distance", f"{risk.get('trail_distance_points')} points"))
    elif risk.get('use_trail_stop') is False:
        config_data.append(("Trail Stop", "Disabled"))
    
    if risk.get('risk_per_trade_percent') is not None:
        config_data.append(("Risk per Trade", f"{risk.get('risk_per_trade_percent')}%"))
    if risk.get('commission_percent') is not None:
        config_data.append(("Commission", f"{risk.get('commission_percent')}%"))
    
    # STRATEGY section - Dynamic based on enabled indicators
    config_data.append(("Strategy Version", "1"))
    
    if strategy.get('consecutive_green_bars') is not None and strategy.get('consecutive_green_bars') > 0:
        config_data.append(("Green Bars Required", strategy.get('consecutive_green_bars')))
    
    # Build dynamic enabled indicators
    enabled_indicators = []
    
    # EMA Crossover
    if strategy.get('use_ema_crossover') is True:
        fast_ema = strategy.get('fast_ema', 'N/A')
        slow_ema = strategy.get('slow_ema', 'N/A')
        enabled_indicators.append(f"EMA Crossover: Fast={fast_ema}, Slow={slow_ema}")
        config_data.append(("EMA Crossover Enabled", "True"))
        config_data.append(("Fast EMA", fast_ema))
        config_data.append(("Slow EMA", slow_ema))
    
    # MACD
    if strategy.get('use_macd') is True:
        enabled_indicators.append("MACD Signal")
        config_data.append(("MACD Enabled", "True"))
        if strategy.get('macd_fast_period') is not None:
            config_data.append(("MACD Fast Period", strategy.get('macd_fast_period')))
        if strategy.get('macd_slow_period') is not None:
            config_data.append(("MACD Slow Period", strategy.get('macd_slow_period')))
    
    # RSI Filter
    if strategy.get('use_rsi_filter') is True:
        enabled_indicators.append("RSI Filter")
        config_data.append(("RSI Filter Enabled", "True"))
        if strategy.get('rsi_period') is not None:
            config_data.append(("RSI Period", strategy.get('rsi_period')))
        if strategy.get('rsi_overbought') is not None:
            config_data.append(("RSI Overbought", strategy.get('rsi_overbought')))
    
    # VWAP
    if strategy.get('use_vwap') is True:
        enabled_indicators.append("VWAP")
        config_data.append(("VWAP Enabled", "True"))
    
    # HTF Trend
    if strategy.get('use_htf_trend') is True:
        enabled_indicators.append("HTF Trend")
        config_data.append(("HTF Trend Enabled", "True"))
        if strategy.get('htf_timeframe') is not None:
            config_data.append(("HTF Timeframe", strategy.get('htf_timeframe')))
    
    # Consecutive Green
    consecutive_bars = strategy.get('consecutive_green_bars', 0)
    if consecutive_bars > 0:
        enabled_indicators.append(f"Consecutive Green: {consecutive_bars} bars required")
    
    # Add summary
    if enabled_indicators:
        config_data.append(("Enabled Indicators", "; ".join(enabled_indicators)))
    else:
        config_data.append(("Enabled Indicators", "Basic Strategy Only"))
    
    # DATA SOURCE DETAILS
    if data_sim.get('enabled', False):
        config_data.append(("Mode", "File Simulation"))
        if data_sim.get('file_path'):
            config_data.append(("File Path", data_sim.get('file_path')))
        config_data.append(("Status", "Historical data replay"))
    else:
        config_data.append(("Mode", "Live WebStream"))
        config_data.append(("Status", "Live market connection"))
    
    # EXECUTION INFO
    if start_time:
        config_data.append(("Start Time", start_time.strftime("%Y-%m-%d %H:%M:%S")))
    if end_time:
        config_data.append(("End Time", end_time.strftime("%Y-%m-%d %H:%M:%S")))
    
    return pd.DataFrame(config_data, columns=['Parameter', 'Value'])

def test_scenario_1_basic_ema_only():
    """Scenario 1: Basic EMA crossover strategy only"""
    config = {
        'instrument': {
            'symbol': 'BANKNIFTY2511050000CE',
            'exchange': 'NFO',
            'product_type': 'INTRADAY',
            'lot_size': 15,
            'tick_size': 0.05
        },
        'capital': {'initial_capital': 50000.0},
        'risk': {
            'max_positions_per_day': 10,
            'base_sl_points': 15.0,
            'risk_per_trade_percent': 2.0,
            'commission_percent': 0.05
        },
        'session': {
            'start_hour': 9, 'start_min': 15,
            'end_hour': 15, 'end_min': 30,
            'auto_stop_enabled': True,
            'max_loss_per_day': 1000.0
        },
        'strategy': {
            'use_ema_crossover': True,
            'fast_ema': 5,
            'slow_ema': 13,
            'consecutive_green_bars': 3
        },
        'data_simulation': {'enabled': False}
    }
    return config

def test_scenario_2_comprehensive_indicators():
    """Scenario 2: All indicators enabled with complex configuration"""
    config = {
        'instrument': {
            'symbol': 'NIFTY2510524500CE',
            'exchange': 'NFO',
            'product_type': 'INTRADAY',
            'lot_size': 50,
            'tick_size': 0.05
        },
        'capital': {'initial_capital': 200000.0},
        'risk': {
            'max_positions_per_day': 25,
            'base_sl_points': 20.0,
            'tp_points': [15.0, 30.0, 50.0, 100.0],
            'tp_percents': [0.4, 0.3, 0.2, 0.1],
            'use_trail_stop': True,
            'trail_activation_points': 10.0,
            'trail_distance_points': 5.0,
            'risk_per_trade_percent': 1.5,
            'commission_percent': 0.03
        },
        'session': {
            'start_hour': 9, 'start_min': 15,
            'end_hour': 15, 'end_min': 30,
            'auto_stop_enabled': True,
            'max_loss_per_day': 2500.0
        },
        'strategy': {
            'use_ema_crossover': True,
            'fast_ema': 9,
            'slow_ema': 21,
            'use_macd': True,
            'macd_fast_period': 12,
            'macd_slow_period': 26,
            'macd_signal_period': 9,
            'use_rsi_filter': True,
            'rsi_period': 14,
            'rsi_overbought': 70,
            'rsi_oversold': 30,
            'use_vwap': True,
            'use_htf_trend': True,
            'htf_timeframe': '1H',
            'consecutive_green_bars': 5
        },
        'data_simulation': {
            'enabled': True,
            'file_path': 'C:/Users/user/data/nifty_ticks_20251012.csv'
        }
    }
    return config

def test_scenario_3_minimal_config():
    """Scenario 3: Minimal configuration with few parameters"""
    config = {
        'instrument': {
            'symbol': 'RELIANCE',
            'exchange': 'NSE'
        },
        'capital': {'initial_capital': 10000.0},
        'risk': {
            'base_sl_points': 5.0,
            'use_trail_stop': False
        },
        'strategy': {
            'consecutive_green_bars': 2
        },
        'data_simulation': {'enabled': False}
    }
    return config

def test_scenario_4_partial_indicators():
    """Scenario 4: Some indicators enabled, others disabled"""
    config = {
        'instrument': {
            'symbol': 'SBIN2511250CE',
            'exchange': 'NFO',
            'product_type': 'INTRADAY',
            'lot_size': 3000
        },
        'capital': {'initial_capital': 75000.0},
        'risk': {
            'max_positions_per_day': 15,
            'base_sl_points': 8.0,
            'tp_points': [10.0, 20.0],
            'tp_percents': [0.7, 0.3],
            'use_trail_stop': False,  # Explicitly disabled
            'commission_percent': 0.04
        },
        'session': {
            'start_hour': 9, 'start_min': 30,
            'end_hour': 15, 'end_min': 0,
            'auto_stop_enabled': False
        },
        'strategy': {
            'use_ema_crossover': False,  # Disabled
            'use_macd': True,  # Enabled
            'macd_fast_period': 8,
            'macd_slow_period': 21,
            'use_rsi_filter': True,  # Enabled
            'rsi_period': 21,
            'use_vwap': False,  # Disabled
            'use_htf_trend': False,  # Disabled
            'consecutive_green_bars': 4
        },
        'data_simulation': {
            'enabled': True,
            'file_path': 'C:/data/sbin_historical.csv'
        }
    }
    return config

def run_dynamic_config_tests():
    """Run all test scenarios to demonstrate dynamic behavior"""
    print("=" * 100)
    print("DYNAMIC CONFIGURATION TABLE TESTING")
    print("=" * 100)
    
    scenarios = [
        ("Basic EMA Only", test_scenario_1_basic_ema_only),
        ("Comprehensive All Indicators", test_scenario_2_comprehensive_indicators),
        ("Minimal Configuration", test_scenario_3_minimal_config),
        ("Partial Indicators", test_scenario_4_partial_indicators)
    ]
    
    start_time = datetime(2025, 10, 12, 14, 30, 0)
    end_time = datetime(2025, 10, 12, 15, 45, 0)
    
    for scenario_name, config_func in scenarios:
        print(f"\n{'-' * 80}")
        print(f"SCENARIO: {scenario_name.upper()}")
        print(f"{'-' * 80}")
        
        config = config_func()
        config_df = build_dynamic_config_table(config, start_time, end_time)
        
        print(f"Configuration Parameters: {len(config_df)}")
        print(f"Adapts to: {scenario_name}")
        print()
        
        # Show enabled features summary
        strategy = config.get('strategy', {})
        risk = config.get('risk', {})
        
        enabled_features = []
        if strategy.get('use_ema_crossover'): enabled_features.append("EMA Crossover")
        if strategy.get('use_macd'): enabled_features.append("MACD")
        if strategy.get('use_rsi_filter'): enabled_features.append("RSI Filter")
        if strategy.get('use_vwap'): enabled_features.append("VWAP")
        if strategy.get('use_htf_trend'): enabled_features.append("HTF Trend")
        if risk.get('use_trail_stop'): enabled_features.append("Trail Stop")
        if risk.get('tp_points'): enabled_features.append("Take Profit")
        
        print(f"Enabled Features: {', '.join(enabled_features) if enabled_features else 'Basic Only'}")
        
        # Show parameter categories
        categories = {
            'Data Source': [p for p in config_df['Parameter'] if any(x in p for x in ['Data Source', 'File', 'Mode', 'Status'])],
            'Instrument': [p for p in config_df['Parameter'] if any(x in p for x in ['Symbol', 'Exchange', 'Product', 'Lot', 'Tick'])],
            'Risk Management': [p for p in config_df['Parameter'] if any(x in p for x in ['Capital', 'Trades', 'Stop', 'Trail', 'Risk', 'Commission', 'TP'])],
            'Strategy': [p for p in config_df['Parameter'] if any(x in p for x in ['Strategy', 'Green', 'EMA', 'MACD', 'RSI', 'VWAP', 'HTF', 'Indicators'])],
            'Session': [p for p in config_df['Parameter'] if any(x in p for x in ['Session', 'Auto Stop', 'Max Loss'])],
            'Execution': [p for p in config_df['Parameter'] if any(x in p for x in ['Start Time', 'End Time'])]
        }
        
        print("\nParameter Distribution:")
        for category, params in categories.items():
            if params:
                print(f"  {category}: {len(params)} parameters")
        
        # Show key dynamic adaptations
        print("\nKey Adaptations:")
        
        # Check indicator-specific parameters
        indicator_params = [p for p in config_df['Parameter'] if any(x in p for x in ['EMA', 'MACD', 'RSI', 'VWAP', 'HTF'])]
        if indicator_params:
            print(f"  • Indicator parameters: {len(indicator_params)} (adapts to enabled indicators)")
        
        # Check take profit configuration
        tp_params = [p for p in config_df['Parameter'] if 'TP' in p or 'Take Profit' in p]
        if tp_params:
            print(f"  • Take Profit details: {len(tp_params)} parameters (only when configured)")
        elif not risk.get('tp_points'):
            print(f"  • Take Profit: Excluded (not configured)")
        
        # Check trail stop
        trail_params = [p for p in config_df['Parameter'] if 'Trail' in p]
        if trail_params:
            if risk.get('use_trail_stop'):
                print(f"  • Trail Stop: {len(trail_params)} parameters (enabled with details)")
            else:
                print(f"  • Trail Stop: {len(trail_params)} parameters (disabled)")
        
        # Show sample of actual parameters
        print(f"\nSample Parameters (first 10):")
        for idx in range(min(10, len(config_df))):
            param = config_df.iloc[idx]['Parameter']
            value = config_df.iloc[idx]['Value']
            print(f"  {param}: {value}")
        
        if len(config_df) > 10:
            print(f"  ... and {len(config_df) - 10} more parameters")
        
        # Export scenario
        csv_filename = f"dynamic_config_{scenario_name.lower().replace(' ', '_')}.csv"
        config_df.to_csv(csv_filename, index=False)
        print(f"\n✓ Exported: {csv_filename}")
    
    print("\n" + "=" * 100)
    print("DYNAMIC CONFIGURATION TESTING COMPLETE")
    print("=" * 100)
    print("Key Benefits:")
    print("• Configuration table adapts to enabled/disabled features")
    print("• Parameter count varies based on actual configuration")
    print("• Only shows relevant indicator settings")
    print("• Excludes disabled risk management features")
    print("• Maintains clean, focused results export")
    print("=" * 100)

if __name__ == "__main__":
    run_dynamic_config_tests()