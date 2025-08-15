"""
defaults.py - Single Source of Truth for All Configuration Defaults

This file contains all default values used by both GUI and non-GUI components.
Any changes to defaults should be made here only.
"""

DEFAULT_CONFIG = {
    'strategy': {
        'strategy_version': 'research',
        'use_ema_crossover': True,
        'use_macd': False,
        'use_vwap': False,
        'use_rsi_filter': False,
        'use_htf_trend': False,
        'use_bollinger_bands': False,
        'use_stochastic': False,
        'use_atr': False,
        'fast_ema': 9,
        'slow_ema': 21,
        'macd_fast': 12,
        'macd_slow': 26,
        'macd_signal': 9,
        'rsi_length': 14,
        'rsi_overbought': 70,
        'rsi_oversold': 30,
        'htf_period': 20,
        'indicator_update_mode': 'tick'
    },
    'risk': {
        'base_sl_points': 12.0,
        'tp_points': [10.0, 25.0, 50.0, 100.0],
        'tp_percents': [0.25, 0.25, 0.25, 0.25],
        'use_trail_stop': True,
        'trail_activation_points': 5.0,
        'trail_distance_points': 7.0,
        'risk_per_trade_percent': 5.0,
        'commission_percent': 0.03,
        'commission_per_trade': 0.0,
        'max_position_value_percent': 95.0,
        'stt_percent': 0.025,
        'exchange_charges_percent': 0.0019,
        'gst_percent': 18.0,
        'slippage_points': 1.0
    },
    'capital': {
        'initial_capital': 100000.0
    },
    'instrument': {
        'symbol': 'NIFTY',
        'exchange': 'NSE_FO',
        'lot_size': 75,
        'tick_size': 0.05,
        'product_type': 'INTRADAY'
    },
    'session': {
        'is_intraday': True,
        'start_hour': 9,
        'start_min': 15,
        'end_hour': 15,
        'end_min': 30,
        'start_buffer_minutes': 5,
        'end_buffer_minutes': 20,
        'timezone': 'Asia/Kolkata'
    },
    'backtest': {
        'allow_short': False,
        'close_at_session_end': True,
        'save_results': True,
        'results_dir': 'backtest_results',
        'log_level': 'INFO'
    },
    'live': {
        'paper_trading': True,
        'exchange_type': 'NSE_FO',
        'feed_type': 'Quote',
        'log_ticks': False,
        'visual_indicator': True
    }
}