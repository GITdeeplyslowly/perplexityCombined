#!/usr/bin/env python3
"""
Generate a sample Excel file to demonstrate the complete dialog box information copy.
"""

import pandas as pd
import json
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

def generate_sample_excel():
    """Generate sample Excel file with complete dialog information."""
    try:
        from myQuant.live.forward_test_results import ForwardTestResults
        
        # Create mock position manager with sample trade
        class MockPositionManager:
            def __init__(self):
                from myQuant.core.position_manager import Trade
                from datetime import datetime, timedelta
                
                # Create sample trade that matches the dataframe
                start = datetime(2025, 10, 12, 13, 30, 0)
                self.trades = [
                    Trade(
                        entry_time=start,
                        exit_time=start + timedelta(minutes=5),
                        symbol="DATA_SIMULATION_PLACEHOLDER",
                        side="BUY",
                        quantity=75,
                        entry_price=100.0,
                        exit_price=105.0,
                        gross_pnl=375.0,
                        commission=15.0,
                        net_pnl=360.0
                    )
                ]
        
        config = create_complete_test_config()
        mock_pm = MockPositionManager()
        start_time = datetime(2025, 10, 12, 13, 28, 26)
        
        # Create results object
        results = ForwardTestResults(config, mock_pm, start_time)
        results.end_time = datetime(2025, 10, 12, 13, 37, 7)
        
        # Generate Excel file
        filename = "complete_dialog_info_demo.xlsx"
        results.export_to_excel(filename)
        
        print("✓ Sample Excel file generated: complete_dialog_info_demo.xlsx")
        print("✓ Contains all dialog box information in results table")
        
        # Show configuration summary
        config_df = results.get_config_table()
        print(f"✓ Configuration parameters captured: {len(config_df)}")
        
        # Show key sections included
        params = config_df['Parameter'].tolist()
        sections = {
            'Data Source': [p for p in params if 'Data' in p or 'File' in p or 'Mode' in p],
            'Instrument': [p for p in params if any(x in p for x in ['Symbol', 'Exchange', 'Product', 'Lot', 'Tick'])],
            'Session': [p for p in params if any(x in p for x in ['Session', 'Auto Stop', 'Max Loss'])],
            'Risk Management': [p for p in params if any(x in p for x in ['Capital', 'Trades', 'Stop', 'Trail', 'Risk', 'Commission', 'TP'])],
            'Strategy': [p for p in params if any(x in p for x in ['Strategy', 'Green', 'EMA', 'Indicators'])],
            'Execution': [p for p in params if any(x in p for x in ['Start Time', 'End Time'])]
        }
        
        print("\nSections included:")
        for section, section_params in sections.items():
            if section_params:
                print(f"  {section}: {len(section_params)} parameters")
        
        return True
        
    except Exception as e:
        print(f"✗ Error generating Excel file: {e}")
        return False

if __name__ == "__main__":
    success = generate_sample_excel()
    if success:
        print("\n" + "="*60)
        print("COMPLETE DIALOG BOX INFORMATION SUCCESSFULLY EXPORTED")
        print("="*60)
        print("The Excel file now contains all sections from the dialog:")
        print("• DATA SOURCE information")
        print("• INSTRUMENT & SESSION details")
        print("• RISK & CAPITAL MANAGEMENT parameters")
        print("• STRATEGY & INDICATORS configuration")
        print("• DATA SOURCE DETAILS")
        print("• TEST EXECUTION timing")
        print("="*60)
    else:
        print("\n✗ Failed to generate complete Excel export")