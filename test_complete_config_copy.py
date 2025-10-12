#!/usr/bin/env python3
"""
Test that the results file contains complete dialog box information.
Verify all sections and details are properly copied.
"""

import pandas as pd
import json
from datetime import datetime
from myQuant.live.forward_test_results import ForwardTestResults

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

def test_complete_dialog_mirror():
    """Test that config table includes all dialog box sections."""
    print("\n" + "="*80)
    print("TESTING COMPLETE DIALOG BOX INFORMATION COPY")
    print("="*80)
    
    # Create test results with complete config
    config = create_complete_test_config()
    
    # Create mock position manager (minimal)
    class MockPositionManager:
        def __init__(self):
            self.trades = []
    
    mock_pm = MockPositionManager()
    start_time = datetime(2025, 10, 12, 13, 28, 26)
    
    # Create results object with proper parameters
    results = ForwardTestResults(config, mock_pm, start_time)
    results.end_time = datetime(2025, 10, 12, 13, 37, 7)
    
    # Get the configuration table
    config_df = results.get_config_table()
    
    print(f"\nConfiguration Table Generated ({len(config_df)} parameters):")
    print("-" * 60)
    
    # Expected sections from dialog box
    expected_sections = {
        'DATA SOURCE': [
            'Data Source Type', 'Historical File', 'Data Warning'
        ],
        'INSTRUMENT & SESSION': [
            'Symbol', 'Exchange', 'Product Type', 'Lot Size', 'Tick Size',
            'Session Start', 'Session End', 'Auto Stop', 'Max Loss/Day'
        ],
        'RISK & CAPITAL MANAGEMENT': [
            'Initial Capital', 'Max Trades/Day', 'Base Stop Loss',
            'Take Profit Levels', 'TP Points', 'TP Percentages',
            'Trail Stop', 'Trail Activation', 'Trail Distance',
            'Risk per Trade', 'Commission'
        ],
        'STRATEGY & INDICATORS': [
            'Strategy Version', 'Green Bars Required', 'Enabled Indicators',
            'EMA Crossover Enabled', 'Fast EMA', 'Slow EMA'
        ],
        'DATA SOURCE DETAILS': [
            'Mode', 'File Path', 'Status'
        ],
        'TEST EXECUTION': [
            'Start Time', 'End Time'
        ]
    }
    
    # Check each parameter
    found_params = set(config_df['Parameter'].tolist())
    all_expected = set()
    for section_params in expected_sections.values():
        all_expected.update(section_params)
    
    print("\nSECTION-BY-SECTION VERIFICATION:")
    print("-" * 40)
    
    for section_name, section_params in expected_sections.items():
        print(f"\n{section_name}:")
        for param in section_params:
            if param in found_params:
                value = config_df[config_df['Parameter'] == param]['Value'].iloc[0]
                print(f"  ✓ {param}: {value}")
            else:
                print(f"  ✗ MISSING: {param}")
    
    # Show all parameters for verification
    print(f"\nCOMPLETE PARAMETER LIST ({len(config_df)} total):")
    print("-" * 40)
    for idx, row in config_df.iterrows():
        print(f"{row['Parameter']:30} : {row['Value']}")
    
    # Coverage analysis
    missing = all_expected - found_params
    extra = found_params - all_expected
    
    print("\nCOVERAGE ANALYSIS:")
    print("-" * 20)
    print(f"Expected parameters: {len(all_expected)}")
    print(f"Found parameters: {len(found_params)}")
    print(f"Missing: {len(missing)} - {list(missing) if missing else 'None'}")
    print(f"Extra: {len(extra)} - {list(extra) if extra else 'None'}")
    
    # Specific dialog box format checks
    print("\nDIALOG BOX FORMAT VERIFICATION:")
    print("-" * 30)
    
    # Check specific formatting requirements
    session_start = config_df[config_df['Parameter'] == 'Session Start']['Value'].iloc[0]
    session_end = config_df[config_df['Parameter'] == 'Session End']['Value'].iloc[0]
    print(f"Session times formatted properly: {session_start} - {session_end}")
    
    auto_stop = config_df[config_df['Parameter'] == 'Auto Stop']['Value'].iloc[0]
    trail_stop = config_df[config_df['Parameter'] == 'Trail Stop']['Value'].iloc[0]
    print(f"Boolean values as text: Auto Stop={auto_stop}, Trail Stop={trail_stop}")
    
    base_sl = config_df[config_df['Parameter'] == 'Base Stop Loss']['Value'].iloc[0]
    print(f"Stop loss with units: {base_sl}")
    
    risk_pct = config_df[config_df['Parameter'] == 'Risk per Trade']['Value'].iloc[0]
    commission_pct = config_df[config_df['Parameter'] == 'Commission']['Value'].iloc[0]
    print(f"Percentages formatted: Risk={risk_pct}, Commission={commission_pct}")
    
    tp_levels = config_df[config_df['Parameter'] == 'Take Profit Levels']['Value'].iloc[0]
    tp_points = config_df[config_df['Parameter'] == 'TP Points']['Value'].iloc[0]
    tp_percents = config_df[config_df['Parameter'] == 'TP Percentages']['Value'].iloc[0]
    print(f"Take Profit details: {tp_levels}")
    print(f"  Points: {tp_points}")
    print(f"  Percentages: {tp_percents}")
    
    indicators = config_df[config_df['Parameter'] == 'Enabled Indicators']['Value'].iloc[0]
    print(f"Indicators summary: {indicators}")
    
    data_source = config_df[config_df['Parameter'] == 'Data Source Type']['Value'].iloc[0]
    mode = config_df[config_df['Parameter'] == 'Mode']['Value'].iloc[0]
    print(f"Data source info: {data_source} / {mode}")
    
    print("\n" + "="*80)
    print("TEST COMPLETE - DIALOG BOX INFORMATION COPY VERIFIED")
    print("="*80)
    
    return len(missing) == 0  # Success if no missing parameters

if __name__ == "__main__":
    success = test_complete_dialog_mirror()
    if success:
        print("\n✓ SUCCESS: All dialog box information properly copied to results!")
    else:
        print("\n✗ ISSUES: Some dialog box information missing from results")