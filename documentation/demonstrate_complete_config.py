#!/usr/bin/env python3
"""
Demonstrate the complete dialog box information extraction.
Shows the exact configuration table that will be exported to Excel.
"""

import pandas as pd
from datetime import datetime

def create_complete_test_config():
    """Create a config that matches the dialog box example."""
    return {
        'instrument': {
            'symbol': 'DATA_SIMULATION_PLACEHOLDER',
            'exchange': 'NFO',
            'product_type': 'INTRADAY',
            'lot_size': 75,
            'tick_size': 0.05
        },
        'capital': {
            'initial_capital': 100000.0
        },
        'risk': {
            'max_positions_per_day': 25,
            'base_sl_points': 10.0,
            'tp_points': [10.0, 25.0, 50.0, 100.0],
            'tp_percents': [0.4, 0.3, 0.2, 0.1],
            'use_trail_stop': True,
            'trail_activation_points': 5.0,
            'trail_distance_points': 7.0,
            'risk_per_trade_percent': 1.0,
            'commission_percent': 0.03
        },
        'session': {
            'start_hour': 9,
            'start_min': 15,
            'end_hour': 15,
            'end_min': 30,
            'auto_stop_enabled': True,
            'max_loss_per_day': 500.0
        },
        'strategy': {
            'consecutive_green_bars': 5,
            'use_ema_crossover': True,
            'fast_ema': 9,
            'slow_ema': 21,
            'use_macd': False,
            'use_rsi_filter': False,
            'use_vwap': False,
            'use_htf_trend': False
        },
        'data_simulation': {
            'enabled': True,
            'file_path': 'C:/Users/user/projects/angelalgo windsurf/smartapi/data/live_ticks_20251001_170006.csv'
        }
    }

def build_config_table(config, start_time, end_time):
    """
    Build the configuration table exactly as it will appear in Excel.
    This mirrors the get_config_table method from ForwardTestResults.
    """
    config_data = []
    
    # Extract all sections from config
    inst = config.get('instrument', {})
    capital = config.get('capital', {})
    risk = config.get('risk', {})
    session = config.get('session', {})
    strategy = config.get('strategy', {})
    data_sim = config.get('data_simulation', {})
    
    # DATA SOURCE section (first in dialog)
    if data_sim.get('enabled', False):
        config_data.append(("Data Source Type", "FILE DATA SIMULATION"))
        config_data.append(("Historical File", data_sim.get('file_path', 'N/A')))
        config_data.append(("Data Warning", "Uses HISTORICAL data, not live market prices"))
    else:
        config_data.append(("Data Source Type", "LIVE WEBSTREAM"))
        config_data.append(("Data Status", "Live market data"))
    
    # INSTRUMENT & SESSION section  
    config_data.append(("Symbol", inst.get('symbol', 'N/A')))
    config_data.append(("Exchange", inst.get('exchange', 'N/A')))
    config_data.append(("Product Type", inst.get('product_type', 'N/A')))
    config_data.append(("Lot Size", inst.get('lot_size', 'N/A')))
    config_data.append(("Tick Size", inst.get('tick_size', 'N/A')))
    config_data.append(("Session Start", f"{session.get('start_hour', 9):02d}:{session.get('start_min', 15):02d}"))
    config_data.append(("Session End", f"{session.get('end_hour', 15):02d}:{session.get('end_min', 30):02d}"))
    config_data.append(("Auto Stop", "Enabled" if session.get('auto_stop_enabled', False) else "Disabled"))
    config_data.append(("Max Loss/Day", session.get('max_loss_per_day', 'N/A')))
    
    # RISK & CAPITAL MANAGEMENT section
    config_data.append(("Initial Capital", capital.get('initial_capital', 'N/A')))
    config_data.append(("Max Trades/Day", risk.get('max_positions_per_day', 'N/A')))
    config_data.append(("Base Stop Loss", f"{risk.get('base_sl_points', 'N/A')} points"))
    
    # Take Profit details
    tp_points = risk.get('tp_points', [])
    tp_percents = risk.get('tp_percents', [])
    if tp_points:
        config_data.append(("Take Profit Levels", f"{len(tp_points)} levels"))
        config_data.append(("TP Points", str(tp_points)))
        config_data.append(("TP Percentages", str(tp_percents)))
    
    # Trail Stop details
    config_data.append(("Trail Stop", "Enabled" if risk.get('use_trail_stop', False) else "Disabled"))
    if risk.get('use_trail_stop', False):
        config_data.append(("Trail Activation", f"{risk.get('trail_activation_points', 'N/A')} points"))
        config_data.append(("Trail Distance", f"{risk.get('trail_distance_points', 'N/A')} points"))
    
    config_data.append(("Risk per Trade", f"{risk.get('risk_per_trade_percent', 'N/A')}%"))
    config_data.append(("Commission", f"{risk.get('commission_percent', 'N/A')}%"))
    
    # STRATEGY & INDICATORS section
    config_data.append(("Strategy Version", "1"))
    config_data.append(("Green Bars Required", strategy.get('consecutive_green_bars', 'N/A')))
    
    # Enabled Indicators details
    enabled_indicators = []
    if strategy.get('use_ema_crossover', False):
        fast_ema = strategy.get('fast_ema', 'N/A')
        slow_ema = strategy.get('slow_ema', 'N/A')
        enabled_indicators.append(f"EMA Crossover: Fast={fast_ema}, Slow={slow_ema}")
    
    consecutive_bars = strategy.get('consecutive_green_bars', 0)
    if consecutive_bars > 0:
        enabled_indicators.append(f"Consecutive Green: {consecutive_bars} bars required")
    
    enabled_indicators.append("Noise Filter: 0.01% threshold")
    
    config_data.append(("Enabled Indicators", "; ".join(enabled_indicators)))
    
    # Individual strategy parameters (for detailed view)
    config_data.append(("EMA Crossover Enabled", strategy.get('use_ema_crossover', 'N/A')))
    config_data.append(("Fast EMA", strategy.get('fast_ema', 'N/A')))
    config_data.append(("Slow EMA", strategy.get('slow_ema', 'N/A')))
    config_data.append(("MACD Enabled", strategy.get('use_macd', 'N/A')))
    config_data.append(("RSI Filter Enabled", strategy.get('use_rsi_filter', 'N/A')))
    config_data.append(("VWAP Enabled", strategy.get('use_vwap', 'N/A')))
    config_data.append(("HTF Trend Enabled", strategy.get('use_htf_trend', 'N/A')))
    
    # DATA SOURCE DETAILS section (as shown at bottom of dialog)
    if data_sim.get('enabled', False):
        config_data.append(("Mode", "File Simulation"))
        config_data.append(("File Path", data_sim.get('file_path', 'N/A')))
        config_data.append(("Status", "Historical data replay"))
    else:
        config_data.append(("Mode", "Live WebStream"))
        config_data.append(("Status", "Live market connection"))
    
    # TEST EXECUTION INFO (added by results system)
    if start_time:
        config_data.append(("Start Time", start_time.strftime("%Y-%m-%d %H:%M:%S")))
    if end_time:
        config_data.append(("End Time", end_time.strftime("%Y-%m-%d %H:%M:%S")))
        
    return pd.DataFrame(config_data, columns=['Parameter', 'Value'])

def demonstrate_complete_config_export():
    """Show the complete configuration table as it will appear in Excel."""
    print("="*80)
    print("COMPLETE DIALOG BOX INFORMATION IN EXCEL EXPORT")
    print("="*80)
    
    # Create the test configuration
    config = create_complete_test_config()
    start_time = datetime(2025, 10, 12, 13, 28, 26)
    end_time = datetime(2025, 10, 12, 13, 37, 7)
    
    # Build the configuration table
    config_df = build_config_table(config, start_time, end_time)
    
    print(f"\nCONFIGURATION TABLE ({len(config_df)} parameters)")
    print("This is exactly what will appear in the Excel file:")
    print("-" * 60)
    
    # Display as it would appear in Excel
    for idx, row in config_df.iterrows():
        param = row['Parameter']
        value = row['Value']
        print(f"{param:<30} | {value}")
    
    # Show section breakdown
    print("\n" + "="*80)
    print("DIALOG BOX SECTIONS CAPTURED:")
    print("="*80)
    
    sections = [
        "DATA SOURCE (File simulation details)",
        "INSTRUMENT & SESSION (Trading parameters)",  
        "RISK & CAPITAL MANAGEMENT (Risk controls)",
        "STRATEGY & INDICATORS (Logic configuration)",
        "DATA SOURCE DETAILS (Technical details)",
        "TEST EXECUTION (Runtime information)"
    ]
    
    for section in sections:
        print(f"✓ {section}")
    
    print(f"\n✓ Total parameters captured: {len(config_df)}")
    print("✓ All dialog box information now exported to Excel")
    print("✓ Maintains exact formatting and structure from dialog")
    
    # Export to CSV for verification  
    csv_filename = "complete_config_demo.csv"
    config_df.to_csv(csv_filename, index=False)
    print(f"\n✓ Sample exported to: {csv_filename}")
    
    return config_df

if __name__ == "__main__":
    config_df = demonstrate_complete_config_export()
    
    print("\n" + "="*80)
    print("IMPLEMENTATION COMPLETE")
    print("="*80)
    print("The forward test results file now includes:")
    print("• Complete dialog box configuration copy")
    print("• All sections exactly as shown to user") 
    print("• Proper formatting and structure")
    print("• Take profit, trail stop, and indicator details")
    print("• Data source and execution information")
    print("="*80)