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
        "tick_log_interval": 1000,
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
        "consecutive_green_bars": 3,
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
        "base_sl_points": 15.0,
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
        "symbol": "DEFAULT",
        "exchange": "NSE_FO",
        "lot_size": 1,
        "tick_size": 0.05,
        "product_type": "INTRADAY"
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
        "visual_indicator": True
    }
}
