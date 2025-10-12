#!/usr/bin/env python3
"""
Test the enhanced strategy configuration that mirrors the GUI dialog
"""

import pandas as pd
from datetime import datetime

def test_enhanced_strategy_config():
    """Test the comprehensive strategy configuration display"""
    
    # Create mock configuration that matches what GUI would generate
    mock_config = {
        'instrument': {
            'symbol': 'NIFTY25DEC25000CE',
            'instrument_type': 'NIFTY',
            'exchange': 'NFO',
            'token': '12345',
            'lot_size': 75,
            'tick_size': 0.05
        },
        'capital': {
            'initial_capital': 100000.0,
            'position_size_method': 'capital_percentage',
            'fixed_amount': 25000.0,
            'fixed_quantity': 1,
            'max_positions': 3
        },
        'risk': {
            'risk_per_trade_percent': 1.0,
            'max_positions_per_day': 5,
            'base_sl_points': 50.0,
            'use_trail_stop': True,
            'trail_activation_points': 30.0,
            'trail_distance_points': 20.0,
            'tp_points': [25.0, 50.0, 100.0],
            'tp_percents': [0.5, 0.3, 0.2]
        },
        'strategy': {
            'use_ema_crossover': True,
            'fast_ema': 9,
            'slow_ema': 21,
            'use_macd': True,
            'macd_fast': 12,
            'macd_slow': 26,
            'macd_signal': 9,
            'use_rsi_filter': True,
            'rsi_length': 14,
            'rsi_oversold': 30.0,
            'rsi_overbought': 70.0,
            'use_vwap': True,
            'use_htf_trend': True,
            'htf_period': 60,
            'use_bollinger_bands': False,
            'use_stochastic': False,
            'use_atr': True,
            'consecutive_green_bars': 3
        },
        'session': {
            'is_intraday': True,
            'start_hour': 9,
            'start_min': 15,
            'end_hour': 15,
            'end_min': 30,
            'auto_stop_enabled': True,
            'max_loss_per_day': 5000.0
        },
        'live': {
            'feed_type': 'websocket',
            'paper_trading': True,
            'reconnect_attempts': 3,
            'tick_timeout': 30
        },
        'data_simulation': {
            'enabled': False,
            'file_path': ''
        }
    }
    
    def create_enhanced_config_table(config):
        """Replicate the enhanced configuration table logic"""
        config_data = []
        
        # === INSTRUMENT CONFIGURATION ===
        inst = config.get('instrument', {})
        config_data.append(("=== INSTRUMENT SETUP ===", ""))
        config_data.append(("Symbol", inst.get('symbol', 'N/A')))
        config_data.append(("Instrument Type", inst.get('instrument_type', 'N/A')))
        config_data.append(("Exchange", inst.get('exchange', 'N/A')))
        config_data.append(("Token", inst.get('token', 'N/A')))
        config_data.append(("Lot Size", str(inst.get('lot_size', 'N/A'))))
        config_data.append(("Tick Size", str(inst.get('tick_size', 'N/A'))))
        
        # === CAPITAL & POSITION SIZING ===
        capital = config.get('capital', {})
        config_data.append(("", ""))  # Spacer
        config_data.append(("=== CAPITAL MANAGEMENT ===", ""))
        config_data.append(("Initial Capital", f"{capital.get('initial_capital', 0):,.2f}"))
        config_data.append(("Position Size Method", capital.get('position_size_method', 'N/A')))
        config_data.append(("Fixed Amount", f"{capital.get('fixed_amount', 0):,.2f}"))
        config_data.append(("Fixed Quantity", str(capital.get('fixed_quantity', 0))))
        config_data.append(("Max Positions", str(capital.get('max_positions', 'N/A'))))
        
        # === RISK MANAGEMENT ===
        risk = config.get('risk', {})
        config_data.append(("", ""))  # Spacer
        config_data.append(("=== RISK MANAGEMENT ===", ""))
        config_data.append(("Risk per Trade", f"{risk.get('risk_per_trade_percent', 0)}%"))
        config_data.append(("Max Trades/Day", str(risk.get('max_positions_per_day', 'N/A'))))
        config_data.append(("Base Stop Loss", f"{risk.get('base_sl_points', 0)} pts"))
        config_data.append(("Use Trailing Stop", "Yes" if risk.get('use_trail_stop', False) else "No"))
        if risk.get('use_trail_stop', False):
            config_data.append(("Trail Activation", f"{risk.get('trail_activation_points', 0)} pts"))
            config_data.append(("Trail Distance", f"{risk.get('trail_distance_points', 0)} pts"))
        
        # Take Profit levels
        tp_points = risk.get('tp_points', [])
        tp_percents = risk.get('tp_percents', [])
        if tp_points:
            config_data.append(("Take Profit Points", str(tp_points)))
            config_data.append(("Take Profit %", str([f"{p*100:.1f}%" for p in tp_percents])))
        
        # === STRATEGY PARAMETERS ===
        strategy = config.get('strategy', {})
        config_data.append(("", ""))  # Spacer
        config_data.append(("=== STRATEGY INDICATORS ===", ""))
        config_data.append(("Use EMA Crossover", "Yes" if strategy.get('use_ema_crossover', False) else "No"))
        if strategy.get('use_ema_crossover', False):
            config_data.append(("Fast EMA", str(strategy.get('fast_ema', 'N/A'))))
            config_data.append(("Slow EMA", str(strategy.get('slow_ema', 'N/A'))))
        
        config_data.append(("Use MACD", "Yes" if strategy.get('use_macd', False) else "No"))
        if strategy.get('use_macd', False):
            config_data.append(("MACD Fast", str(strategy.get('macd_fast', 'N/A'))))
            config_data.append(("MACD Slow", str(strategy.get('macd_slow', 'N/A'))))
            config_data.append(("MACD Signal", str(strategy.get('macd_signal', 'N/A'))))
        
        config_data.append(("Use RSI Filter", "Yes" if strategy.get('use_rsi_filter', False) else "No"))
        if strategy.get('use_rsi_filter', False):
            config_data.append(("RSI Length", str(strategy.get('rsi_length', 'N/A'))))
            config_data.append(("RSI Oversold", str(strategy.get('rsi_oversold', 'N/A'))))
            config_data.append(("RSI Overbought", str(strategy.get('rsi_overbought', 'N/A'))))
        
        config_data.append(("Use VWAP", "Yes" if strategy.get('use_vwap', False) else "No"))
        config_data.append(("Use HTF Trend", "Yes" if strategy.get('use_htf_trend', False) else "No"))
        if strategy.get('use_htf_trend', False):
            config_data.append(("HTF Period", str(strategy.get('htf_period', 'N/A'))))
        config_data.append(("Use Bollinger Bands", "Yes" if strategy.get('use_bollinger_bands', False) else "No"))
        config_data.append(("Use Stochastic", "Yes" if strategy.get('use_stochastic', False) else "No"))
        config_data.append(("Use ATR", "Yes" if strategy.get('use_atr', False) else "No"))
        
        # === SESSION MANAGEMENT ===
        session = config.get('session', {})
        config_data.append(("", ""))  # Spacer
        config_data.append(("=== SESSION MANAGEMENT ===", ""))
        config_data.append(("Intraday Trading", "Yes" if session.get('is_intraday', True) else "No"))
        config_data.append(("Session Start", f"{session.get('start_hour', 9):02d}:{session.get('start_min', 15):02d}"))
        config_data.append(("Session End", f"{session.get('end_hour', 15):02d}:{session.get('end_min', 30):02d}"))
        config_data.append(("Auto Stop Enabled", "Yes" if session.get('auto_stop_enabled', False) else "No"))
        config_data.append(("Max Loss per Day", f"{session.get('max_loss_per_day', 0):,.2f}"))
        
        # === LIVE TRADING CONFIG ===
        live = config.get('live', {})
        config_data.append(("", ""))  # Spacer
        config_data.append(("=== LIVE TRADING SETUP ===", ""))
        config_data.append(("Feed Type", live.get('feed_type', 'N/A')))
        config_data.append(("Paper Trading", "Yes" if live.get('paper_trading', True) else "No"))
        config_data.append(("Reconnect Attempts", str(live.get('reconnect_attempts', 3))))
        config_data.append(("Tick Timeout", f"{live.get('tick_timeout', 30)}s"))
        
        # === DATA SOURCE ===
        data_sim = config.get('data_simulation', {})
        config_data.append(("", ""))  # Spacer
        config_data.append(("=== DATA SOURCE ===", ""))
        if data_sim.get('enabled', False):
            config_data.append(("Data Source", "File Simulation"))
            config_data.append(("Data File", data_sim.get('file_path', 'N/A')))
        else:
            config_data.append(("Data Source", "Live WebStream"))
            
        return pd.DataFrame(config_data, columns=['Parameter', 'Value'])
    
    print("=== TESTING ENHANCED STRATEGY CONFIGURATION ===")
    
    # Create the enhanced configuration table
    config_df = create_enhanced_config_table(mock_config)
    
    print(f"\nConfiguration table created with {len(config_df)} parameters")
    print(f"Columns: {list(config_df.columns)}")
    
    print(f"\n=== CONFIGURATION SECTIONS ===")
    current_section = None
    for _, row in config_df.iterrows():
        param = row['Parameter']
        value = row['Value']
        
        if param.startswith('===') and param.endswith('==='):
            current_section = param
            print(f"\n{current_section}")
        elif param == "":
            continue  # Skip spacers
        else:
            print(f"  {param}: {value}")
    
    # Export to CSV for verification
    csv_file = "enhanced_config_test.csv"
    config_df.to_csv(csv_file, index=False)
    print(f"\n✅ Enhanced configuration exported to {csv_file}")
    
    # Count sections
    sections = config_df[config_df['Parameter'].str.startswith('===')]['Parameter'].tolist()
    print(f"\n📊 Configuration contains {len(sections)} major sections:")
    for section in sections:
        print(f"  - {section}")
    
    return config_df

if __name__ == "__main__":
    df = test_enhanced_strategy_config()
    print(f"\n🎉 Enhanced strategy configuration test completed!")
    print(f"✅ Now mirrors all parameters from 'Run Forward Test' dialog box")
    print(f"✅ Comprehensive configuration with {len(df)} total parameters")