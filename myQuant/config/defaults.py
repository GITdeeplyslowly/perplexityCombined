"""
defaults.py - Single Source of Truth for All Configuration Defaults

This file contains all default values used by both GUI and non-GUI components.
Any changes to defaults should be made here only.
"""

import os
from typing import Dict, Any

# Single Source of Truth for defaults used by GUI and runners.
DEFAULT_CONFIG: Dict[str, Any] = {
    "logging": {
        # Canonical single key for file path
        "logfile": os.path.join("logs", "trading_bot.log"),
        # legacy alias kept for compatibility with older callers
        "log_file": os.path.join("logs", "trading_bot.log"),
        # Whether progress/logging of tick-level events is enabled
        "log_progress": False,
        # Maximum number of reason strings to include in signal logs (None == unlimited)
        "max_signal_reasons": 5,
        "log_to_file": True,
        "console_output": True,
        "verbosity": "INFO",
        "tick_log_interval": 2500,
        "max_file_size": 10 * 1024 * 1024,
        "backup_count": 5,
        "log_level_overrides": {},
        # optional structured JSON event stream
        "json_event_log": False,
        "json_event_file": os.path.join("logs", "events.jsonl")
    },
    "strategy": {
        "strategy_version": 1,
        "use_ema_crossover": True,
        "use_macd": False,
        "use_vwap": False,
        "use_rsi_filter": False,
        "use_htf_trend": False,
        "use_bollinger_bands": False,
        "use_stochastic": False,
        "use_atr": False,
        "use_consecutive_green": True,
        "fast_ema": 9,
        "slow_ema": 21,
        "macd_fast": 12,
        "macd_slow": 26,
        "macd_signal": 9,
        "rsi_length": 14,
        "rsi_overbought": 70,
        "rsi_oversold": 30,
        "htf_period": 20,
        "consecutive_green_bars": 5,
        "atr_len": 14,
        "indicator_update_mode": "tick",
        # Add noise filter parameters
        "noise_filter_enabled": True,
        "noise_filter_percentage": 0.0001,  # 0.01% threshold
        "noise_filter_min_ticks": 1.0,      # Minimum number of ticks to consider
        # nan/recovery thresholds (kept here for future use)
        "nan_streak_threshold": 7,
        "nan_recovery_threshold": 3
    },
    "risk": {
        "max_positions_per_day": 25,
        "base_sl_points": 10.0,
        "tp_points": [10.0, 25.0, 50.0, 100.0],
        "tp_percents": [0.25, 0.25, 0.25, 0.25],
        "use_trail_stop": True,
        "trail_activation_points": 5.0,
        "trail_distance_points": 7.0,
        "risk_per_trade_percent": 1.0,
        "commission_percent": 0.03,
        "commission_per_trade": 0.0,
        "tick_size": 0.05,
        # PositionManager runtime expectations (single-source defaults)
        "max_position_value_percent": 100.0,
        "stt_percent": 0.025,
        "exchange_charges_percent": 0.003,
        "gst_percent": 18.0,
        "slippage_points": 0.0
    },
    "capital": {
        "initial_capital": 100000.0
    },
    "instrument": {
        "symbol": "NIFTY",  # Default to Nifty options - lot_size now comes from instrument_mappings (SSOT)
        "exchange": "NSE_FO",
        "product_type": "INTRADAY"
        # instrument_token: Dynamic per option contract, populated when user selects specific option
        # lot_size and tick_size removed - instrument_mappings is now SSOT
    },
    # Comprehensive instrument mapping with corrected lot sizes (as of Oct 2024)
    "instrument_mappings": {
        # Index Options - Updated with current lot sizes
        "NIFTY": {"lot_size": 75, "exchange": "NSE_FO", "tick_size": 0.05, "type": "Index Options"},
        "BANKNIFTY": {"lot_size": 15, "exchange": "NSE_FO", "tick_size": 0.05, "type": "Index Options"},
        "FINNIFTY": {"lot_size": 25, "exchange": "NSE_FO", "tick_size": 0.05, "type": "Index Options"},
        "MIDCPNIFTY": {"lot_size": 50, "exchange": "NSE_FO", "tick_size": 0.05, "type": "Index Options"},
        "SENSEX": {"lot_size": 10, "exchange": "BSE_FO", "tick_size": 0.05, "type": "Index Options"},
        "BANKEX": {"lot_size": 15, "exchange": "BSE_FO", "tick_size": 0.05, "type": "Index Options"},
        
        # Individual Stock Options - Updated with current lot sizes (Popular F&O stocks)
        "RELIANCE": {"lot_size": 250, "exchange": "NSE_FO", "tick_size": 0.05, "type": "Stock Options"},
        "HDFCBANK": {"lot_size": 550, "exchange": "NSE_FO", "tick_size": 0.05, "type": "Stock Options"},
        "ICICIBANK": {"lot_size": 775, "exchange": "NSE_FO", "tick_size": 0.05, "type": "Stock Options"},
        "INFY": {"lot_size": 300, "exchange": "NSE_FO", "tick_size": 0.05, "type": "Stock Options"},
        "TCS": {"lot_size": 150, "exchange": "NSE_FO", "tick_size": 0.05, "type": "Stock Options"},
        "SBIN": {"lot_size": 1500, "exchange": "NSE_FO", "tick_size": 0.05, "type": "Stock Options"},
        "LT": {"lot_size": 300, "exchange": "NSE_FO", "tick_size": 0.05, "type": "Stock Options"},
        "WIPRO": {"lot_size": 1200, "exchange": "NSE_FO", "tick_size": 0.05, "type": "Stock Options"},
        "MARUTI": {"lot_size": 100, "exchange": "NSE_FO", "tick_size": 0.05, "type": "Stock Options"},
        "BHARTIARTL": {"lot_size": 1081, "exchange": "NSE_FO", "tick_size": 0.05, "type": "Stock Options"},
        
        # Additional Popular Stock Options with Current Lot Sizes
        "ADANIPORTS": {"lot_size": 1200, "exchange": "NSE_FO", "tick_size": 0.05, "type": "Stock Options"},
        "ASIANPAINT": {"lot_size": 300, "exchange": "NSE_FO", "tick_size": 0.05, "type": "Stock Options"},
        "AXISBANK": {"lot_size": 1200, "exchange": "NSE_FO", "tick_size": 0.05, "type": "Stock Options"},
        "BAJFINANCE": {"lot_size": 125, "exchange": "NSE_FO", "tick_size": 0.05, "type": "Stock Options"},
        "BAJAJFINSV": {"lot_size": 600, "exchange": "NSE_FO", "tick_size": 0.05, "type": "Stock Options"},
        "COALINDIA": {"lot_size": 2400, "exchange": "NSE_FO", "tick_size": 0.05, "type": "Stock Options"},
        "DRREDDY": {"lot_size": 150, "exchange": "NSE_FO", "tick_size": 0.05, "type": "Stock Options"},
        "EICHERMOT": {"lot_size": 200, "exchange": "NSE_FO", "tick_size": 0.05, "type": "Stock Options"},
        "GRASIM": {"lot_size": 450, "exchange": "NSE_FO", "tick_size": 0.05, "type": "Stock Options"},
        "HCLTECH": {"lot_size": 600, "exchange": "NSE_FO", "tick_size": 0.05, "type": "Stock Options"},
        "HEROMOTOCO": {"lot_size": 225, "exchange": "NSE_FO", "tick_size": 0.05, "type": "Stock Options"},
        "HINDALCO": {"lot_size": 1875, "exchange": "NSE_FO", "tick_size": 0.05, "type": "Stock Options"},
        "HINDUNILVR": {"lot_size": 300, "exchange": "NSE_FO", "tick_size": 0.05, "type": "Stock Options"},
        "INDUSINDBK": {"lot_size": 900, "exchange": "NSE_FO", "tick_size": 0.05, "type": "Stock Options"},
        "ITC": {"lot_size": 1600, "exchange": "NSE_FO", "tick_size": 0.05, "type": "Stock Options"},
        "JSWSTEEL": {"lot_size": 1200, "exchange": "NSE_FO", "tick_size": 0.05, "type": "Stock Options"},
        "KOTAKBANK": {"lot_size": 400, "exchange": "NSE_FO", "tick_size": 0.05, "type": "Stock Options"},
        "NESTLEIND": {"lot_size": 50, "exchange": "NSE_FO", "tick_size": 0.05, "type": "Stock Options"},
        "NTPC": {"lot_size": 2700, "exchange": "NSE_FO", "tick_size": 0.05, "type": "Stock Options"},
        "ONGC": {"lot_size": 3400, "exchange": "NSE_FO", "tick_size": 0.05, "type": "Stock Options"},
        "POWERGRID": {"lot_size": 2400, "exchange": "NSE_FO", "tick_size": 0.05, "type": "Stock Options"},
        "SUNPHARMA": {"lot_size": 600, "exchange": "NSE_FO", "tick_size": 0.05, "type": "Stock Options"},
        "TATAMOTORS": {"lot_size": 1500, "exchange": "NSE_FO", "tick_size": 0.05, "type": "Stock Options"},
        "TATASTEEL": {"lot_size": 6000, "exchange": "NSE_FO", "tick_size": 0.05, "type": "Stock Options"},
        "TECHM": {"lot_size": 600, "exchange": "NSE_FO", "tick_size": 0.05, "type": "Stock Options"},
        "TITAN": {"lot_size": 250, "exchange": "NSE_FO", "tick_size": 0.05, "type": "Stock Options"},
        "ULTRACEMCO": {"lot_size": 100, "exchange": "NSE_FO", "tick_size": 0.05, "type": "Stock Options"},
        
        # Index Futures - Same lot sizes as options
        "NIFTYFUT": {"lot_size": 75, "exchange": "NSE_FO", "tick_size": 0.05, "type": "Index Futures"},
        "BANKNIFTYFUT": {"lot_size": 15, "exchange": "NSE_FO", "tick_size": 0.05, "type": "Index Futures"},
        
        # Stock Futures - Same lot sizes as stock options
        "RELIANCEFUT": {"lot_size": 250, "exchange": "NSE_FO", "tick_size": 0.05, "type": "Stock Futures"},
        
        # Cash Market (lot size = 1 for cash)
        "NIFTY_CASH": {"lot_size": 1, "exchange": "NSE_CM", "tick_size": 0.05, "type": "Cash Market"},
        "BANKNIFTY_CASH": {"lot_size": 1, "exchange": "NSE_CM", "tick_size": 0.05, "type": "Cash Market"},
        "RELIANCE_CASH": {"lot_size": 1, "exchange": "NSE_CM", "tick_size": 0.05, "type": "Cash Market"},
        "HDFCBANK_CASH": {"lot_size": 1, "exchange": "NSE_CM", "tick_size": 0.05, "type": "Cash Market"}
    },
    "session": {
        "is_intraday": True,
        "start_hour": 9,
        "start_min": 15,
        "end_hour": 15,
        "end_min": 30,
        "start_buffer_minutes": 5,
        "end_buffer_minutes": 20,
        "no_trade_start_minutes": 5,
        "no_trade_end_minutes": 10,
        "timezone": "Asia/Kolkata"
    },
    "backtest": {
        "allow_short": False,
        "close_at_session_end": True,
        "save_results": True,
        "results_dir": "results",
        "log_level": "INFO"
    },
    "live": {
        "paper_trading": True,
        "exchange_type": "NSE_FO",
        "feed_type": "LTP",
        "log_ticks": False,
        "visual_indicator": True,
        "api_key": "",  # REQUIRED for live trading - will fail-fast if empty
        "client_code": "",  # REQUIRED for live trading - will fail-fast if empty
        "pin": "",  # OPTIONAL - if empty, will try to reuse saved session
        "totp_token": "",  # OPTIONAL - if empty, will try to reuse saved session
        "allow_interactive_auth": False  # Enable interactive PIN/TOTP prompts when session expires
    }
}
