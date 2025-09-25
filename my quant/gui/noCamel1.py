"""
unified_gui.py - Unified Trading Interface for both Backtesting and Live Trading

Provides a comprehensive GUI for:
- Configuring strategy parameters
- Running backtests
- Starting/stopping live trading
- Visualizing results
- Managing configurations
"""

import os
import json
import threading
import logging
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
import numpy as np
import pytz

from types import MappingProxyType
from typing import Dict, Any

from utils.config_helper import create_config_from_defaults, validate_config, freeze_config, ConfigAccessor
from backtest.backtest_runner import BacktestRunner
from utils.cache_manager import refresh_symbol_cache, load_symbol_cache
from live.trader import LiveTrader

from config.defaults import DEFAULT_CONFIG
from utils.logging_utils import setup_logging

# Module-level logger and strict startup logging using canonical DEFAULT_CONFIG.
# Fail-fast if DEFAULT_CONFIG does not provide the required logging keys.
logging_config = DEFAULT_CONFIG.get("logging", {}) or {}
required_logging_keys = ["logfile", "verbosity", "console_output", "file_rotation"]
missing_keys = [k for k in required_logging_keys if k not in logging_config]
if missing_keys:
    raise RuntimeError(f"DEFAULT_CONFIG logging section missing keys: {missing_keys}")

LOG_FILENAME = str(logging_config["logfile"])
LOG_VERBOSITY = str(logging_config["verbosity"])
LOG_CONSOLE = bool(logging_config["console_output"])
LOG_ROTATION = bool(logging_config["file_rotation"])

# Ensure log dir exists if provided (no empty dirname)
log_dir = os.path.dirname(LOG_FILENAME)
if log_dir:
    os.makedirs(log_dir, exist_ok=True)

# Configure unified logging (strict, fail-fast)
logger = setup_logging(
    log_level=LOG_VERBOSITY,
    log_file=LOG_FILENAME,
    console_output=LOG_CONSOLE,
    file_rotation=LOG_ROTATION,
    module_name=__name__
)

def now_ist():
    """Return current time in India Standard Time"""
    return datetime.now(pytz.timezone('Asia/Kolkata'))

class UnifiedTradingGUI(tk.Tk):
    def __init__(self, master=None):
        super().__init__(master)

        self.title("Unified Trading System")
        self.geometry("1200x800")
        self.minsize(1000, 700)

        # === SINGLE POINT OF CONFIGURATION (FIXED FLOW) ===
        # 1. Build runtime config from defaults (factory may apply normalization & user prefs)
        self.runtime_config = create_config_from_defaults()

        # 2. Merge persisted user preferences into runtime_config BEFORE widget creation
        self._merge_user_preferences_into_runtime_config()

        # 3. Initialize all GUI variables (this sets tk.Variable instances)
        self._initialize_all_variables()

        # 4. Initialize GUI variables from runtime_config (single source for widgets)
        self._initialize_variables_from_runtime_config()

        # 5. Logging is configured at module import from DEFAULT_CONFIG (strict, single source).
        # If runtime reconfiguration is desired, call setup_logging(...) explicitly with
        # runtime_config['logging'] (no fallbacks). We intentionally avoid best-effort
        # reconfiguration here to keep logging deterministic.

        # 6. Create GUI components and tabs
        self._create_gui_framework()
        self._build_backtest_tab()
        self._build_forward_test_tab()
        self._build_log_tab()

        logger.info("GUI initialized successfully with runtime config")

    def _initialize_variables_from_defaults(self):
        """Initialize all GUI variables from runtime_config (single source for widgets)"""
        # NEW: read sections from the runtime_config which already merges defaults + user prefs
        strategy_defaults = self.runtime_config.get('strategy', {})
        risk_defaults = self.runtime_config.get('risk', {})
        capital_defaults = self.runtime_config.get('capital', {})
        instrument_defaults = self.runtime_config.get('instrument', {})
        session_defaults = self.runtime_config.get('session', {})

        # --- Strategy variables ---
        self.bt_use_ema_crossover = tk.BooleanVar(value=strategy_defaults.get('use_ema_crossover', False))
        self.bt_use_macd = tk.BooleanVar(value=strategy_defaults.get('use_macd', False))
        self.bt_use_vwap = tk.BooleanVar(value=strategy_defaults.get('use_vwap', False))
        self.bt_use_rsi_filter = tk.BooleanVar(value=strategy_defaults.get('use_rsi_filter', False))
        self.bt_use_htf_trend = tk.BooleanVar(value=strategy_defaults.get('use_htf_trend', False))
        self.bt_use_bollinger_bands = tk.BooleanVar(value=strategy_defaults.get('use_bollinger_bands', False))
        self.bt_use_stochastic = tk.BooleanVar(value=strategy_defaults.get('use_stochastic', False))
        self.bt_use_atr = tk.BooleanVar(value=strategy_defaults.get('use_atr', False))

        # EMA parameters
        self.bt_fast_ema = tk.StringVar(value=str(strategy_defaults.get('fast_ema', '9')))
        self.bt_slow_ema = tk.StringVar(value=str(strategy_defaults.get('slow_ema', '21')))

        # MACD parameters
        self.bt_macd_fast = tk.StringVar(value=str(strategy_defaults.get('macd_fast', '12')))
        self.bt_macd_slow = tk.StringVar(value=str(strategy_defaults.get('macd_slow', '26')))
        self.bt_macd_signal = tk.StringVar(value=str(strategy_defaults.get('macd_signal', '9')))

        # RSI parameters
        self.bt_rsi_length = tk.StringVar(value=str(strategy_defaults.get('rsi_length', 14)))
        self.bt_rsi_oversold = tk.StringVar(value=str(strategy_defaults.get('rsi_oversold', 30)))
        self.bt_rsi_overbought = tk.StringVar(value=str(strategy_defaults.get('rsi_overbought', 70)))

        # HTF parameter
        self.bt_htf_period = tk.StringVar(value=str(strategy_defaults.get('htf_period', 20)))

        # --- Consecutive Green Bars parameter ---
        self.bt_consecutive_green_bars = tk.StringVar(value=str(strategy_defaults.get('consecutive_green_bars', 3)))

        # --- Risk management ---
        self.bt_base_sl_points = tk.StringVar(value=str(risk_defaults.get('base_sl_points', 12.0)))
        self.bt_tp_points = [tk.StringVar(value=str(p)) for p in risk_defaults.get('tp_points', [10.0, 25.0, 50.0, 100.0])]
        self.bt_tp_percents = [tk.StringVar(value=str(p*100)) for p in risk_defaults.get('tp_percents', [0.25,0.25,0.25,0.25])]
        self.bt_use_trail_stop = tk.BooleanVar(value=risk_defaults.get('use_trail_stop', False))
        self.bt_trail_activation = tk.StringVar(value=str(risk_defaults.get('trail_activation_points', 5.0)))
        self.bt_trail_distance = tk.StringVar(value=str(risk_defaults.get('trail_distance_points', 7.0)))
        self.bt_risk_per_trade_percent = tk.StringVar(value=str(risk_defaults.get('risk_per_trade_percent', 1.0)))

        # --- Capital settings ---
        self.bt_initial_capital = tk.StringVar(value=str(capital_defaults.get('initial_capital', 100000.0)))

        # --- Instrument settings ---
        self.bt_symbol = tk.StringVar(value=instrument_defaults.get('symbol', 'NIFTY'))
        self.bt_exchange = tk.StringVar(value=instrument_defaults.get('exchange', 'NSE_FO'))
        self.bt_lot_size = tk.StringVar(value=str(instrument_defaults.get('lot_size', 1)))

        # --- Session settings ---
        self.bt_is_intraday = tk.BooleanVar(value=session_defaults.get('is_intraday', True))
        self.bt_session_start_hour = tk.StringVar(value=str(session_defaults.get('start_hour', 9)))
        self.bt_session_start_min = tk.StringVar(value=str(session_defaults.get('start_min', 15)))
        self.bt_session_end_hour = tk.StringVar(value=str(session_defaults.get('end_hour', 15)))
        self.bt_session_end_min = tk.StringVar(value=str(session_defaults.get('end_min', 30)))
    def _load_user_preferences(self):
        """Load user preferences from saved file"""
        prefs_file = "user_preferences.json"
        if os.path.exists(prefs_file):
            try:
                with open(prefs_file, 'r') as f:
                    prefs = json.load(f)
                self._apply_preferences_to_gui(prefs)
                logger.info("User preferences applied to GUI (legacy path)")
            except Exception:
                logger.exception("Failed to load user preferences (legacy path)")


    def _apply_preferences_to_gui(self, preferences):
        """Apply saved preferences to GUI controls - Complete implementation"""
        # Strategy parameters
        if 'strategy' in preferences:
            strategy_prefs = preferences['strategy']
            self._set_if_exists(self.bt_use_ema_crossover, 'use_ema_crossover', strategy_prefs)
            self._set_if_exists(self.bt_use_macd, 'use_macd', strategy_prefs)
            self._set_if_exists(self.bt_use_vwap, 'use_vwap', strategy_prefs)
            self._set_if_exists(self.bt_use_rsi_filter, 'use_rsi_filter', strategy_prefs)
            self._set_if_exists(self.bt_use_htf_trend, 'use_htf_trend', strategy_prefs)
            self._set_if_exists(self.bt_fast_ema, 'fast_ema', strategy_prefs)
            self._set_if_exists(self.bt_slow_ema, 'slow_ema', strategy_prefs)
            self._set_if_exists(self.bt_macd_fast, 'macd_fast', strategy_prefs)
            self._set_if_exists(self.bt_macd_slow, 'macd_slow', strategy_prefs)
            self._set_if_exists(self.bt_macd_signal, 'macd_signal', strategy_prefs)
    
        # Risk parameters - Complete implementation
        if 'risk' in preferences:
            risk_prefs = preferences['risk']
            self._set_if_exists(self.bt_base_sl_points, 'base_sl_points', risk_prefs)
            self._set_if_exists(self.bt_use_trail_stop, 'use_trail_stop', risk_prefs)
            self._set_if_exists(self.bt_trail_activation, 'trail_activation_points', risk_prefs)
            self._set_if_exists(self.bt_trail_distance, 'trail_distance_points', risk_prefs)
            # Handle TP points array
            if 'tp_points' in risk_prefs and len(risk_prefs['tp_points']) >= 4:
                for i, tp_var in enumerate(self.bt_tp_points[:4]):
                    tp_var.set(str(risk_prefs['tp_points'][i]))

        # Capital settings
        if 'capital' in preferences:
            try:
                if 'initial_capital' in preferences['capital']:
                    self.bt_initial_capital.set(str(preferences['capital']['initial_capital']))
            except Exception:
                pass


        # Instrument settings
        if 'instrument' in preferences:
            try:
                if 'symbol' in preferences['instrument']:
                    self.bt_symbol.set(preferences['instrument']['symbol'])
            except Exception:
                pass


        # Session settings
        if 'session' in preferences:
            try:
                s = preferences['session']
                if 'start_hour' in s:
                    self.bt_session_start_hour.set(str(s['start_hour']))
                if 'start_min' in s:
                    self.bt_session_start_min.set(str(s['start_min']))
                if 'end_hour' in s:
                    self.bt_session_end_hour.set(str(s['end_hour']))
                if 'end_min' in s:
                    self.bt_session_end_min.set(str(s['end_min']))
            except Exception:
                pass

    def _set_if_exists(self, var, key, prefs_dict):
        """Set tkinter variable if key exists in preferences"""
        if key in prefs_dict:
            try:
                if isinstance(var, tk.StringVar):
                    var.set(str(prefs_dict[key]))
                elif isinstance(var, tk.BooleanVar):
                    var.set(bool(prefs_dict[key]))
                elif isinstance(var, tk.IntVar):
                    var.set(int(prefs_dict[key]))
                elif isinstance(var, tk.DoubleVar):
                    var.set(float(prefs_dict[key]))
            except Exception:
                pass

    def save_user_preferences(self):
        """Save user preferences to JSON file"""
        try:
            prefs = self.build_config_from_gui()
            # compute diff against defaults and save only diffs (existing save path handles this)
            diff = self._get_config_diff(prefs, DEFAULT_CONFIG)
            with open("user_preferences.json", "w") as f:
                json.dump(diff, f, indent=2)
            logger.info("User preferences saved")
        except Exception as e:
            logger.exception("Failed to save user preferences")

    def _get_config_diff(self, current, defaults):
        """Extract only values that differ from defaults"""
        diff = {}

        for section, params in current.items():
            if not isinstance(params, dict):
                continue
            for k, v in params.items():
                default_v = defaults.get(section, {}).get(k, None)
                if v != default_v:
                    diff.setdefault(section, {})[k] = v

        return diff

    def build_config_from_gui(self):
        """Build complete configuration from current GUI state"""
        config = create_config_from_defaults()

        # Update with current GUI values

        # Strategy settings
        config['strategy']['use_ema_crossover'] = self.bt_use_ema_crossover.get()
        config['strategy']['use_macd'] = self.bt_use_macd.get()
        config['strategy']['use_vwap'] = self.bt_use_vwap.get()
        config['strategy']['use_rsi_filter'] = self.bt_use_rsi_filter.get()
        config['strategy']['use_htf_trend'] = self.bt_use_htf_trend.get()
        config['strategy']['use_bollinger_bands'] = self.bt_use_bollinger_bands.get()
        config['strategy']['use_stochastic'] = self.bt_use_stochastic.get()
        config['strategy']['use_atr'] = self.bt_use_atr.get()

        # Convert string inputs to appropriate types
        config['strategy']['fast_ema'] = int(self.bt_fast_ema.get())
        config['strategy']['slow_ema'] = int(self.bt_slow_ema.get())
        config['strategy']['macd_fast'] = int(self.bt_macd_fast.get())
        config['strategy']['macd_slow'] = int(self.bt_macd_slow.get())
        config['strategy']['macd_signal'] = int(self.bt_macd_signal.get())
        # Consecutive Green Bars
        config['strategy']['consecutive_green_bars'] = int(self.bt_consecutive_green_bars.get())

        # --- ADD THIS LINE ---
        config['strategy']['strategy_version'] = DEFAULT_CONFIG['strategy'].get('strategy_version', 1)
        # ---------------------

        # Risk settings
        config['risk']['base_sl_points'] = float(self.bt_base_sl_points.get())
        config['risk']['use_trail_stop'] = self.bt_use_trail_stop.get()
        config['risk']['trail_activation_points'] = float(self.bt_trail_activation.get())
        config['risk']['trail_distance_points'] = float(self.bt_trail_distance.get())

        # Update take profit points and percentages
        tp_points = [float(var.get()) for var in self.bt_tp_points]
        tp_percents = [float(var.get())/100.0 for var in self.bt_tp_percents]  # Convert from percentage display
        config['risk']['tp_points'] = tp_points
        config['risk']['tp_percents'] = tp_percents

        # Capital settings
        config['capital']['initial_capital'] = float(self.bt_initial_capital.get())

        # Instrument settings
        config['instrument']['symbol'] = self.bt_symbol.get()
        config['instrument']['exchange'] = self.bt_exchange.get()
        config['instrument']['lot_size'] = int(self.bt_lot_size.get())

        # Session settings
        config['session']['is_intraday'] = self.bt_is_intraday.get()
        config['session']['start_hour'] = int(self.bt_session_start_hour.get())
        config['session']['start_min'] = int(self.bt_session_start_min.get())
        config['session']['end_hour'] = int(self.bt_session_end_hour.get())
        config['session']['end_min'] = int(self.bt_session_end_min.get())

        # Set the data file path for the backtest runner
        config['backtest']['data_path'] = self.bt_data_file.get()

        # --- Ensure logging config is propagated to backtest config ---
        # Include logging defaults from DEFAULT_CONFIG
        config['logging'] = DEFAULT_CONFIG.get('logging', {}).copy()
 
        # Add logger level overrides from GUI
        log_level_overrides = {}
        if hasattr(self, 'logger_levels'):
            for logger_name, level_var in self.logger_levels.items():
                level = level_var.get()
                if level != "DEFAULT":  # Only add non-default values
                    log_level_overrides[logger_name] = level
 
        config['logging']['log_level_overrides'] = log_level_overrides
        # Include the tick logging interval from GUI (SSOT entry)
        try:
            config['logging']['tick_log_interval'] = int(self.logger_tick_interval.get())
        except Exception:
            # fall back to defaults if GUI value malformed (should not happen if GUI validates)
            config['logging']['tick_log_interval'] = DEFAULT_CONFIG.get('logging', {}).get('tick_log_interval', 100)
 
        # FINAL: authoritative validation + freeze (GUI SSOT)
        try:
            validation = validate_config(config)
        except Exception as e:
            logger.exception("validate_config raised unexpected exception: %s", e)
            messagebox.showerror("Validation Error", f"Unexpected error during validation: {e}")
            return None

        if not validation.get('valid', False):
            errs = validation.get('errors', []) or ["Unknown validation failure"]
            messagebox.showerror("Configuration Validation Failed",
                                 "Please fix configuration issues:\n\n" + "\n".join(errs))
            return None

        # Freeze config to make it immutable for the run
        try:
            frozen = freeze_config(config)
        except Exception as e:
            logger.exception("freeze_config failed: %s", e)
            messagebox.showerror("Configuration Error", "Failed to freeze configuration. Aborting run.")
            return None

        # Ensure we actually received a MappingProxyType
        if not isinstance(frozen, MappingProxyType):
            logger.error("freeze_config did not return MappingProxyType; aborting run")
            messagebox.showerror("Configuration Error", "Configuration could not be frozen. Aborting run.")
            return None

        return frozen

    def run_backtest(self):
        """Run backtest with GUI configuration"""
        try:
            # Get validated and frozen config from GUI (returns None on validation failure)
            config = self.build_config_from_gui()
            if config is None:
                return

            # Log the actual configuration used
            logger.info("====== BACKTEST CONFIGURATION ======")
            logger.info("Using TRUE INCREMENTAL PROCESSING (row-by-row)")
            logger.info("Batch processing completely eliminated")
            for section, params in config.items():
                if isinstance(params, dict):
                    logger.info(f"{section}: {params}")

            # Create and run backtest with GUI config
            backtest = BacktestRunner(config=config)
            results = backtest.run()

            # Display results
            self.display_backtest_results(results)

            # Optional: Save preferences after successful run
            self.save_user_preferences()

        except Exception as e:
            logger.exception(f"Backtest failed: {e}")
            messagebox.showerror("Backtest Error", f"Failed to run backtest: {e}")

    # --- Forward Test Tab ---
    def _build_forward_test_tab(self):
        frame = self.ft_tab
        frame.columnconfigure(1, weight=1)
        row = 0

        # Symbol Cache Section
        ttk.Label(frame, text="Symbol Management", font=('Arial', 12, 'bold')).grid(row=row, column=0, columnspan=3, sticky="w", pady=(10,5))
        row += 1

        # Authentication Status
        ttk.Label(frame, text="SmartAPI Authentication: Automatic (uses saved session)", font=('Arial', 9), foreground="blue").grid(row=row, column=0, columnspan=3, sticky="w", padx=5, pady=2)
        ttk.Label(frame, text="Note: If no session exists, system will run in paper trading mode", font=('Arial', 8), foreground="gray").grid(row=row+1, column=0, columnspan=3, sticky="w", padx=5, pady=2)
        row += 2

        ttk.Button(frame, text="Refresh Symbol Cache", command=self._ft_refresh_cache).grid(row=row, column=0, pady=3)
        self.ft_cache_status = tk.StringVar(value="Cache not loaded")
        ttk.Label(frame, textvariable=self.ft_cache_status).grid(row=row, column=1, columnspan=2, sticky="w", padx=5)
        row += 1

        ttk.Label(frame, text="Exchange:").grid(row=row, column=0, sticky="e", padx=5, pady=2)
        self.ft_exchange = tk.StringVar(value="NSE_FO")
        exchanges = ["NSE_FO", "NSE_CM", "BSE_CM"]
        ttk.Combobox(frame, textvariable=self.ft_exchange, values=exchanges, width=10, state='readonly').grid(row=row, column=1, sticky="w", padx=5, pady=2)
        row += 1

        # Replace the combobox implementation with a listbox approach like angelalgo windsurf
        symbol_frame = ttk.Frame(frame)
        symbol_frame.grid(row=row, column=0, columnspan=3, sticky="w", padx=5, pady=2)

        # Top row with label, entry and filter button
        ttk.Label(symbol_frame, text="Symbol:").grid(row=0, column=0, sticky="e", padx=5, pady=2)
        self.ft_symbol = tk.StringVar()
        self.ft_symbol_entry = ttk.Entry(symbol_frame, textvariable=self.ft_symbol, width=32)
        self.ft_symbol_entry.grid(row=0, column=1, sticky="w", padx=5, pady=2)
        ttk.Button(symbol_frame, text="Filter & Load Symbols", command=self._ft_load_symbols).grid(row=0, column=2, padx=5, pady=2)

        # Second row with listbox for filtered symbols
        self.ft_symbols_listbox = tk.Listbox(symbol_frame, width=50, height=6)
        self.ft_symbols_listbox.grid(row=1, column=0, columnspan=3, sticky="w", padx=5, pady=2)
        self.ft_symbols_listbox.bind("<<ListboxSelect>>", self._ft_update_symbol_details)

        # Add scrollbar to the listbox
        listbox_scrollbar = ttk.Scrollbar(symbol_frame, orient="vertical", command=self.ft_symbols_listbox.yview)
        listbox_scrollbar.grid(row=1, column=3, sticky="ns")
        self.ft_symbols_listbox.configure(yscrollcommand=listbox_scrollbar.set)

        row += 2  # Increase row count to account for the listbox

        # Token field (auto-filled, read-only)
        ttk.Label(frame, text="Token:").grid(row=row, column=0, sticky="e", padx=5, pady=2)
        self.ft_token = tk.StringVar()
        ttk.Entry(frame, textvariable=self.ft_token, width=20, state="readonly").grid(row=row, column=1, sticky="w", padx=5, pady=2)
        row += 1

        ttk.Label(frame, text="Feed Type:").grid(row=row, column=0, sticky="e", padx=5, pady=2)
        self.ft_feed_type = tk.StringVar(value="Quote")
        feed_types = ["LTP", "Quote", "SnapQuote"]
        ttk.Combobox(frame, textvariable=self.ft_feed_type, values=feed_types, width=12, state='readonly').grid(row=row, column=1, sticky="w", padx=5, pady=2)
        row += 1


        # Strategy Configuration
        ttk.Label(frame, text="Strategy Configuration", font=('Arial', 12, 'bold')).grid(row=row, column=0, columnspan=3, sticky="w", pady=(15,5))
        row += 1

        # Indicator Toggles
        ttk.Label(frame, text="Indicators:", font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky="w", padx=5, pady=2)
        row += 1

        indicators_frame = ttk.Frame(frame)
        indicators_frame.grid(row=row, column=0, columnspan=3, sticky="w", padx=5, pady=2)

        self.ft_use_ema_crossover = tk.BooleanVar(value=True)
        self.ft_use_macd = tk.BooleanVar(value=True)
        self.ft_use_vwap = tk.BooleanVar(value=True)
        self.ft_use_rsi_filter = tk.BooleanVar(value=False)
        self.ft_use_htf_trend = tk.BooleanVar(value=True)
        self.ft_use_bollinger_bands = tk.BooleanVar(value=False)
        self.ft_use_stochastic = tk.BooleanVar(value=False)
        self.ft_use_atr = tk.BooleanVar(value=True)

        ttk.Checkbutton(indicators_frame, text="EMA Crossover", variable=self.ft_use_ema_crossover).grid(row=0, column=0, sticky="w", padx=5)
        ttk.Checkbutton(indicators_frame, text="MACD", variable=self.ft_use_macd).grid(row=0, column=1, sticky="w", padx=5)
        ttk.Checkbutton(indicators_frame, text="VWAP", variable=self.ft_use_vwap).grid(row=0, column=2, sticky="w", padx=5)
        ttk.Checkbutton(indicators_frame, text="RSI Filter", variable=self.ft_use_rsi_filter).grid(row=0, column=3, sticky="w", padx=5)
        ttk.Checkbutton(indicators_frame, text="HTF Trend", variable=self.ft_use_htf_trend).grid(row=1, column=0, sticky="w", padx=5)
        ttk.Checkbutton(indicators_frame, text="Bollinger Bands", variable=self.ft_use_bollinger_bands).grid(row=1, column=1, sticky="w", padx=5)
        ttk.Checkbutton(indicators_frame, text="Stochastic", variable=self.ft_use_stochastic).grid(row=1, column=2, sticky="w", padx=5)
        ttk.Checkbutton(indicators_frame, text="ATR", variable=self.ft_use_atr).grid(row=1, column=3, sticky="w", padx=5)
        row += 1

        # Parameters
        ttk.Label(frame, text="Parameters:", font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky="w", padx=5, pady=(10,2))
        row += 1

        self.ft_param_frame = ttk.LabelFrame(self.ft_tab, text="Parameters")
        self.ft_param_frame.grid(row=row, column=0, columnspan=3, sticky="w", padx=5, pady=2)

        params_frame = ttk.Frame(frame)
        params_frame.grid(row=row, column=0, columnspan=3, sticky="w", padx=5, pady=2)

        # EMA Parameters
        ttk.Label(params_frame, text="Fast EMA:").grid(row=0, column=0, sticky="e", padx=2)
        self.ft_fast_ema = tk.StringVar(value="9")
        ttk.Entry(params_frame, textvariable=self.ft_fast_ema, width=8).grid(row=0, column=1, padx=2)

        ttk.Label(params_frame, text="Slow EMA:").grid(row=0, column=2, sticky="e", padx=2)
        self.ft_slow_ema = tk.StringVar(value="21")
        ttk.Entry(params_frame, textvariable=self.ft_slow_ema, width=8).grid(row=0, column=3, padx=2)

        # MACD Parameters
        ttk.Label(params_frame, text="MACD Fast:").grid(row=1, column=0, sticky="e", padx=2)
        self.ft_macd_fast = tk.StringVar(value="12")
        ttk.Entry(params_frame, textvariable=self.ft_macd_fast, width=8).grid(row=1, column=1, padx=2)

        ttk.Label(params_frame, text="MACD Slow:").grid(row=1, column=2, sticky="e", padx=2)
        self.ft_macd_slow = tk.StringVar(value="26")
        ttk.Entry(params_frame, textvariable=self.ft_macd_slow, width=8).grid(row=1, column=3, padx=2)

        ttk.Label(params_frame, text="MACD Signal:").grid(row=1, column=4, sticky="e", padx=2)
        self.ft_macd_signal = tk.StringVar(value="9")
        ttk.Entry(params_frame, textvariable=self.ft_macd_signal, width=8).grid(row=1, column=5, padx=2)

        # RSI Parameters
        ttk.Label(params_frame, text="RSI Length:").grid(row=2, column=0, sticky="e", padx=2)
        self.ft_rsi_length = tk.StringVar(value="14")
        ttk.Entry(params_frame, textvariable=self.ft_rsi_length, width=8).grid(row=2, column=1, padx=2)

        ttk.Label(params_frame, text="RSI Oversold:").grid(row=2, column=2, sticky="e", padx=2)
        self.ft_rsi_oversold = tk.StringVar(value="30")
        ttk.Entry(params_frame, textvariable=self.ft_rsi_oversold, width=8).grid(row=2, column=3, padx=2)

        ttk.Label(params_frame, text="RSI Overbought:").grid(row=2, column=4, sticky="e", padx=2)
        self.ft_rsi_overbought = tk.StringVar(value="70")
        ttk.Entry(params_frame, textvariable=self.ft_rsi_overbought, width=8).grid(row=2, column=5, padx=2)

        # HTF Parameters
        ttk.Label(params_frame, text="HTF Period:").grid(row=3, column=0, sticky="e", padx=2)
        self.ft_htf_period = tk.StringVar(value="20")
        ttk.Entry(params_frame, textvariable=self.ft_htf_period, width=8).grid(row=3, column=1, padx=2)
        # Consecutive Green Bars
        ttk.Label(params_frame, text="Green Bars Req:").grid(row=3, column=2, sticky="e", padx=2)
        ttk.Entry(params_frame, textvariable=self.bt_consecutive_green_bars, width=8).grid(row=3, column=3, padx=2)
        row += 1

        # Risk Management
        ttk.Label(frame, text="Risk Management:", font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky="w", padx=5, pady=(10,2))
        row += 1

        risk_frame = ttk.Frame(frame)
        risk_frame.grid(row=row, column=0, columnspan=3, sticky="w", padx=5, pady=2)

        ttk.Label(risk_frame, text="Stop Loss Points:").grid(row=0, column=0, sticky="e", padx=2)
        self.ft_base_sl_points = tk.StringVar(value="15")
        ttk.Entry(risk_frame, textvariable=self.ft_base_sl_points, width=8).grid(row=0, column=1, padx=2)

        ttk.Label(risk_frame, text="TP1 Points:").grid(row=0, column=2, sticky="e", padx=2)
        ttk.Entry(risk_frame, textvariable=self.bt_tp_points[0], width=8).grid(row=0, column=3, padx=2)
        ttk.Label(risk_frame, text="TP2 Points:").grid(row=0, column=4, sticky="e", padx=2)
        ttk.Entry(risk_frame, textvariable=self.bt_tp_points[1], width=8).grid(row=0, column=5, padx=2)
        ttk.Label(risk_frame, text="TP3 Points:").grid(row=1, column=0, sticky="e", padx=2)
        ttk.Entry(risk_frame, textvariable=self.bt_tp_points[2], width=8).grid(row=1, column=1, padx=2)

        ttk.Label(risk_frame, text="TP4 Points:").grid(row=1, column=2, sticky="e", padx=2)
        ttk.Entry(risk_frame, textvariable=self.bt_tp_points[3], width=8).grid(row=1, column=3, padx=2)

        self.ft_use_trail_stop = tk.BooleanVar(value=True)
        ttk.Checkbutton(risk_frame, text="Use Trailing Stop", variable=self.ft_use_trail_stop).grid(row=1, column=4, columnspan=2, sticky="w", padx=5)

        ttk.Label(risk_frame, text="Trail Activation Points:").grid(row=2, column=0, sticky="e", padx=2)
        self.ft_trail_activation_points = tk.StringVar(value="25")
        ttk.Entry(risk_frame, textvariable=self.ft_trail_activation_points, width=8).grid(row=2, column=1, padx=2)

        ttk.Label(risk_frame, text="Trail Distance Points:").grid(row=2, column=2, sticky="e", padx=2)
        self.ft_trail_distance_points = tk.StringVar(value="10")
        ttk.Entry(risk_frame, textvariable=self.ft_trail_distance_points, width=8).grid(row=2, column=3, padx=2)

        ttk.Label(risk_frame, text="Risk % per Trade:").grid(row=2, column=4, sticky="e", padx=2)
        self.ft_risk_per_trade_percent = tk.StringVar(value="1.0")
        ttk.Entry(risk_frame, textvariable=self.ft_risk_per_trade_percent, width=8).grid(row=2, column=5, padx=2)
        row += 1

        # --- Instrument Settings ---
        ttk.Label(frame, text="Instrument Settings:", font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky="w", padx=5, pady=(10,2))
        row += 1
        instrument_frame = ttk.Frame(frame)
        instrument_frame.grid(row=row, column=0, columnspan=3, sticky="w", padx=5, pady=2)
        ttk.Label(instrument_frame, text="Symbol:").grid(row=0, column=0, sticky="e", padx=2)
        ttk.Entry(instrument_frame, textvariable=self.bt_symbol, width=16).grid(row=0, column=1, padx=2)
        ttk.Label(instrument_frame, text="Exchange:").grid(row=0, column=2, sticky="e", padx=2)
        ttk.Entry(instrument_frame, textvariable=self.bt_exchange, width=10).grid(row=0, column=3, padx=2)
        ttk.Label(instrument_frame, text="Lot Size:").grid(row=0, column=4, sticky="e", padx=2)
        ttk.Entry(instrument_frame, textvariable=self.bt_lot_size, width=8).grid(row=0, column=5, padx=2)
        row += 1

        # --- Capital Settings ---
        ttk.Label(frame, text="Capital Settings:", font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky="w", padx=5, pady=(10,2))
        row += 1
        capital_frame = ttk.Frame(frame)
        capital_frame.grid(row=row, column=0, columnspan=3, sticky="w", padx=5, pady=2)
        ttk.Label(capital_frame, text="Initial Capital:").grid(row=0, column=0, sticky="e", padx=2)
        ttk.Entry(capital_frame, textvariable=self.bt_initial_capital, width=14).grid(row=0, column=1, padx=2)
        row += 1

        # --- Session Settings ---
        ttk.Label(frame, text="Session Settings:", font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky="w", padx=5, pady=(10,2))
        row += 1
        session_frame = ttk.Frame(frame)
        session_frame.grid(row=row, column=0, columnspan=3, sticky="w", padx=5, pady=2)
        ttk.Label(session_frame, text="Start (HH:MM):").grid(row=0, column=0, sticky="e", padx=2)
        ttk.Entry(session_frame, textvariable=self.bt_session_start_hour, width=4).grid(row=0, column=1, padx=1)
        ttk.Label(session_frame, text=":").grid(row=0, column=2)
        ttk.Entry(session_frame, textvariable=self.bt_session_start_min, width=4).grid(row=0, column=3, padx=1)
        ttk.Label(session_frame, text="End (HH:MM):").grid(row=0, column=4, sticky="e", padx=2)
        ttk.Entry(session_frame, textvariable=self.bt_session_end_hour, width=4).grid(row=0, column=5, padx=1)
        ttk.Label(session_frame, text=":").grid(row=0, column=6)
        ttk.Entry(session_frame, textvariable=self.bt_session_end_min, width=4).grid(row=0, column=7, padx=1)
        ttk.Label(session_frame, text="Intraday:").grid(row=1, column=0, sticky="e", padx=2)
        ttk.Checkbutton(session_frame, variable=self.bt_is_intraday).grid(row=1, column=1, sticky="w", padx=2)
        row += 1

        # Trading Controls
        ttk.Label(frame, text="Trading Controls", font=('Arial', 12, 'bold')).grid(row=row, column=0, columnspan=3, sticky="w", pady=(15,5))
        row += 1

        self.ft_paper_trading = tk.BooleanVar(value=True)
        ttk.Checkbutton(frame, text="Simulation Mode (No Real Orders)", variable=self.ft_paper_trading, state="disabled").grid(row=row, column=0, sticky="w", padx=5, pady=2)
        ttk.Label(frame, text="Order execution is simulation-only.", foreground="red").grid(row=row, column=1, columnspan=2, sticky="w", padx=5, pady=2)
        row += 2

        ttk.Button(frame, text="Start Forward Test", command=self._ft_run_forward_test).grid(row=row, column=0, pady=5)
        ttk.Button(frame, text="Stop", command=self._ft_stop_forward_test).grid(row=row, column=1, pady=5)
        row += 1

        self.ft_result_box = tk.Text(frame, height=16, width=110, state="disabled")
        self.ft_result_box.grid(row=row, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")
        frame.rowconfigure(row, weight=1)

    def _ft_refresh_cache(self):
        try:
            count = refresh_symbol_cache()
            self.ft_cache_status.set(f"Cache refreshed: {count} symbols loaded.")
            messagebox.showinfo("Cache Refreshed", f"Symbol cache updated successfully. Loaded {count} symbols.")
        except Exception as e:
            error_msg = f"Cache refresh failed: {e}"
            self.ft_cache_status.set(error_msg)
            messagebox.showerror("Cache Error", f"Could not refresh cache: {e}")

    def _refresh_symbols_thread(self):
        """Background thread to refresh symbol cache"""
        try:
            # Define run_once for the callback if not already defined
            def run_once(func):
                has_run = {'value': False}
                def wrapper(*args, **kwargs):
                    if not has_run['value']:
                        has_run['value'] = True
                        return func(*args, **kwargs)
                return wrapper

            symbols = refresh_symbol_cache(force_refresh=True, progress_callback=run_once(self._update_refresh_status))

            # Update the symbol listbox with new data
            self.ft_symbols_listbox.delete(0, tk.END)  # Clear existing entries
            for symbol in sorted(symbols.keys()):
                self.ft_symbols_listbox.insert(tk.END, symbol)

            self.ft_cache_status.set(f"Cache refreshed: {len(symbols)} symbols")
            logger.info(f"Symbol cache refreshed: {len(symbols)} symbols")
        except Exception as e:
            error_msg = f"Failed to refresh symbols: {e}"
            self.ft_cache_status.set(error_msg)
            logger.error(error_msg)

    def _ft_load_symbols(self):
        """Load symbols exactly like angelalgo windsurf approach"""
        try:
            # Load the simple symbol:token mapping
            symbol_token_map = load_symbol_cache()

            if not symbol_token_map:
                messagebox.showwarning("No Symbols", "No symbols found. Try refreshing the cache first.")
                return

            # Store the mapping for later use
            self.symbol_token_map = symbol_token_map

            # Get text typed in symbol box
            typed_text = self.ft_symbol.get().upper()

            # Filter symbols matching the typed text
            if typed_text:
                # First try exact matches
                exact_matches = [s for s in symbol_token_map.keys() if s.upper() == typed_text]
                if exact_matches:
                    matching_symbols = exact_matches
                else:
                    # Then try contains matches
                    matching_symbols = [s for s in symbol_token_map.keys() if typed_text in s.upper()]

                # Sort and limit results
                matching_symbols = sorted(matching_symbols)[:100]  # Limit to 100 for performance
            else:
                # If no text entered, show first 50 symbols as preview
                matching_symbols = sorted(symbol_token_map.keys())[:50]

            # Update dropdown with filtered symbols
            self.ft_symbols_listbox.delete(0, tk.END)  # Clear existing entries
            for symbol in matching_symbols:
                self.ft_symbols_listbox.insert(tk.END, symbol)

            # Show dropdown if there are matches
            if matching_symbols:
                self.ft_symbols_listbox.event_generate('<Down>')

            # Update status
            if typed_text:
                self.ft_cache_status.set(f"Found {len(matching_symbols)} symbols matching '{typed_text}'")
            else:
                self.ft_cache_status.set(f"Loaded {len(symbol_token_map)} symbols. Type to search...")

        except Exception as e:
            error_msg = f"Failed to load symbols: {e}"
            self.ft_cache_status.set(error_msg)
            logger.error(error_msg)

    def _ft_update_symbol_details(self, event=None):
        """Update token field when symbol is selected (exactly like angelalgo windsurf)"""
        try:
            selected_symbol = self.ft_symbols_listbox.get(self.ft_symbols_listbox.curselection())

            # Clear token first
            self.ft_token.set("")

            if hasattr(self, 'symbol_token_map') and selected_symbol in self.symbol_token_map:
                # Direct match found
                token = self.symbol_token_map[selected_symbol]
                self.ft_token.set(token)
                logger.info(f"Selected symbol: {selected_symbol}, Token: {token}")
            elif hasattr(self, 'symbol_token_map') and selected_symbol:
                # Try to find exact matches first
                exact_matches = [s for s in self.symbol_token_map.keys() if s.upper() == selected_symbol.upper()]
                if exact_matches:
                    exact_symbol = exact_matches[0]
                    token = self.symbol_token_map[exact_symbol]
                    self.ft_symbol.set(exact_symbol)  # Update to exact symbol name
                    self.ft_token.set(token)
                    logger.info(f"Auto-corrected to exact match: {exact_symbol}, Token: {token}")
                else:
                    # Try partial matches if no exact match found
                    matching_symbols = [s for s in self.symbol_token_map.keys() if selected_symbol.upper() in s.upper()]
                    if len(matching_symbols) == 1:
                        single_match = matching_symbols[0]
                        token = self.symbol_token_map[single_match]
                        self.ft_symbol.set(single_match)  # Update to matched symbol
                        self.ft_token.set(token)
                        logger.info(f"Auto-corrected to partial match: {single_match}, Token: {token}")
                    elif len(matching_symbols) > 1:
                        # Multiple matches - update dropdown with these matches
                        self.ft_symbols_listbox.delete(0, tk.END)  # Clear existing entries
                        for symbol in sorted(matching_symbols)[:100]:
                            self.ft_symbols_listbox.insert(tk.END, symbol)
                        self.ft_symbols_listbox.event_generate('<Down>')  # Show dropdown
                        logger.info(f"Found {len(matching_symbols)} matches for '{selected_symbol}'")
                    else:
                        logger.warning(f"Symbol '{selected_symbol}' not found in cache")

        except Exception as e:
            logger.warning(f"Symbol details update error: {e}")
            self.ft_token.set("")

    def _ft_run_forward_test(self):
        """Start forward test with proper nested configuration"""
        if self._forward_thread and self._forward_thread.is_alive():
            messagebox.showwarning("Warning", "Forward test already running")
            return

        # Build proper nested configuration structure for forward test
        gui_config = {
            # === STRATEGY SECTION ===
            'strategy': {
                'use_ema_crossover': self.ft_use_ema_crossover.get(),
                'use_macd': self.ft_use_macd.get(),
                'use_vwap': self.ft_use_vwap.get(),
                'use_rsi_filter': self.ft_use_rsi_filter.get(),
                'use_htf_trend': self.ft_use_htf_trend.get(),
                'use_bollinger_bands': self.ft_use_bollinger_bands.get(),
                'use_stochastic': self.ft_use_stochastic.get(),
                'use_atr': self.ft_use_atr.get(),
                'fast_ema': int(self.ft_fast_ema.get()),
                'slow_ema': int(self.ft_slow_ema.get()),
                'macd_fast': int(self.ft_macd_fast.get()),
                'macd_slow': int(self.ft_macd_slow.get()),
                'macd_signal': int(self.ft_macd_signal.get()),
                'rsi_length': int(self.ft_rsi_length.get()),
                'rsi_oversold': int(self.ft_rsi_oversold.get()),
                'rsi_overbought': int(self.ft_rsi_overbought.get()),
                'htf_period': int(self.ft_htf_period.get()),
                'indicator_update_mode': 'tick',
                # --- ADD THIS LINE ---
                'strategy_version': DEFAULT_CONFIG['strategy'].get('strategy_version', 1)
                # ---------------------
            },

            # === RISK MANAGEMENT SECTION ===
            'risk': {
                'base_sl_points': float(self.ft_base_sl_points.get()),
                'tp_points': [
                    float(self.ft_tp1_points.get()),
                    float(self.ft_tp2_points.get()),
                    float(self.ft_tp3_points.get()),
                    float(self.ft_tp4_points.get())
                ],
                'tp_percents': [0.25, 0.25, 0.25, 0.25],
                'use_trail_stop': self.ft_use_trail_stop.get(),
                'trail_activation_points': float(self.ft_trail_activation_points.get()),
                'trail_distance_points': float(self.ft_trail_distance_points.get()),
                'risk_per_trade_percent': float(self.ft_risk_per_trade_percent.get()),
                'commission_percent': 0.03,
                'commission_per_trade': 0.0
            },

            # === CAPITAL SECTION ===
            'capital': {
                'initial_capital': float(self.ft_initial_capital.get())
            },

            # === INSTRUMENT SECTION ===
            'instrument': {
                'symbol': self.ft_symbol.get(),
                'exchange': self.ft_exchange.get(),
                'lot_size': int(self.bt_lot_size.get()),
                'tick_size': 0.05,
                'product_type': 'INTRADAY'
            },

            # === SESSION SECTION ===
            'session': {
                'is_intraday': True,
                'start_hour': int(self.ft_session_start_hour.get()),
                'start_min': int(self.ft_session_start_min.get()),
                'end_hour': int(self.ft_session_end_hour.get()),
                'end_min': int(self.ft_session_end_min.get()),
                'start_buffer_minutes': int(self.ft_start_buffer.get()),
                'end_buffer_minutes': int(self.ft_end_buffer.get()),
                'timezone': self.ft_timezone.get()
            },

            # === LIVE TRADING SECTION ===
            'live': {
                'paper_trading': True,
                'exchange_type': self.ft_exchange.get(),
                'feed_type': self.ft_feed_type.get(),
                'log_ticks': False,
                'visual_indicator': True
            },

            # === BACKTEST SECTION (for compatibility) ===
            'backtest': {
                'allow_short': False,
                'close_at_session_end': True,
                'save_results': True,
                'results_dir': 'forward_test_results',
                'log_level': 'INFO'
            }
        }

        # Validate and freeze GUI-built config using authoritative validator
        config = self.build_config_from_gui()
        if config is None:
            return

        logger.info("Using nested, validated & frozen configuration for forward test")
        logger.debug(f"Forward test config: {dict(config) if not isinstance(config, dict) else config}")

        try:
            self.ft_result_box.config(state="normal")
            self.ft_result_box.delete("1.0", "end")
            self.ft_result_box.insert("end", f"Starting forward test for {config['instrument']['symbol']}...\n")
            self.ft_result_box.config(state="disabled")

            trader = LiveTrader(config_dict=config)
            self._forward_thread = threading.Thread(target=trader.start)
            self._forward_thread.start()
        except Exception as e:
            logger.error(f"Error starting forward test: {e}")
            messagebox.showerror("Forward Test Error", f"Failed to start forward test: {str(e)}")

    def _ft_stop_forward_test(self):
        """Stop the running forward test"""
        try:
            if self._forward_thread and self._forward_thread.is_alive():
                # Set a stop flag if the trader has one
                if hasattr(self, '_stop_forward_test_flag'):
                    self._stop_forward_test_flag = True
            
                self.ft_result_box.config(state="normal")
                self.ft_result_box.insert("end", "Stopping forward test...\n")
                self.ft_result_box.config(state="disabled")
            
                logger.info("Forward test stop requested")
                messagebox.showinfo("Stop", "Stop signal sent to forward test.")
            else:
                messagebox.showinfo("Stop", "No forward test is currently running.")
        except Exception as e:
            logger.error(f"Error stopping forward test: {e}")
            messagebox.showerror("Error", f"Failed to stop forward test: {e}")

    # --- Status Tab ---
    def _build_log_tab(self):
        frame = self.log_tab
        row = 0

        ttk.Label(frame, text="Unified Trading System Status & Logs", font=('Arial', 14, 'bold')).grid(row=row, column=0, sticky="w", pady=10)
        row += 1

        ttk.Label(frame, text=f"Log File: {LOG_FILENAME}").grid(row=row, column=0, sticky="w", pady=2)
        row += 1

        # Add log level overrides section
        ttk.Label(frame, text="Logger Level Overrides", font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky="w", padx=5, pady=(10,2))
        row += 1
        
        log_levels_frame = ttk.Frame(frame)
        log_levels_frame.grid(row=row, column=0, columnspan=3, sticky="w", padx=5, pady=2)
        row += 1
        
        # Add some common loggers that users might want to override
        common_loggers = [
            "core.indicators", 
            "core.researchStrategy",
            "backtest.backtest_runner",
            "utils.simple_loader"
        ]
        
        # Create controls for each logger
        for i, logger_name in enumerate(common_loggers):
            ttk.Label(log_levels_frame, text=f"{logger_name}:").grid(row=i//2, column=(i%2)*2, sticky="e", padx=5)
            if not hasattr(self, 'logger_levels'):
                self.logger_levels = {}
            if logger_name not in self.logger_levels:
                self.logger_levels[logger_name] = tk.StringVar(value="DEFAULT")
            ttk.Combobox(
                log_levels_frame,
                textvariable=self.logger_levels[logger_name],
                values=["DEFAULT", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                width=10,
                state='readonly'
            ).grid(row=i//2, column=(i%2)*2+1, sticky="w", padx=5, pady=2)

        # Tick log interval control (SSOT editable via GUI only)
        ttk.Label(frame, text="Tick Log Interval (ticks):").grid(row=row, column=0, sticky="e", padx=5, pady=(8,2))
        ttk.Entry(frame, textvariable=self.logger_tick_interval, width=10).grid(row=row, column=1, sticky="w", padx=5, pady=(8,2))
        row += 1

        ttk.Button(frame, text="View Log File", command=self._open_log_file).grid(row=row, column=0, sticky="w", pady=5)
        row += 1

        self.status_text = tk.Text(frame, height=25, width=110, state='disabled')
        self.status_text.grid(row=row, column=0, padx=5, pady=5, sticky="nsew")
        frame.rowconfigure(row, weight=1)
        frame.columnconfigure(0, weight=1)

        self._update_status_box()

    def _update_status_box(self):
        self.status_text.config(state="normal")
        self.status_text.delete("1.0", "end")

        status_info = (
            "UNIFIED TRADING SYSTEM STATUS\n"
            + "=" * 50 + "\n\n"
            "System Status: Ready\n"
            "Trading Mode: Simulation Only (No Real Orders)\n"
            "Available Modes: Backtest & Forward Test\n\n"
            f"Current Time: {now_ist().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            "BACKTEST MODE:\n"
            "- Load historical CSV data\n"
            "- Configure strategy parameters\n"
            "- Run complete simulation\n"
            "- View detailed results\n\n"
            "FORWARD TEST MODE:\n"
            "- Connect to SmartAPI for live data\n"
            "- Manual symbol cache management\n"
            "- Real-time tick processing\n"
            "- Simulated order execution\n\n"
            "Recent Activity:\n"
        )

        self.status_text.insert("end", status_info)

        # Add recent log entries
        try:
            if os.path.exists(LOG_FILENAME):
                with open(LOG_FILENAME, "r") as f:
                    lines = f.readlines()[-10:]  # Last 10 lines
                    for line in lines:
                        self.status_text.insert("end", line)
        except Exception:
            self.status_text.insert("end", "No recent log entries.\n")

        self.status_text.config(state="disabled")

    def _open_log_file(self):
        import subprocess
        import sys

        if os.path.exists(LOG_FILENAME):
            if sys.platform.startswith('darwin'):  # macOS
                subprocess.call(('open', LOG_FILENAME))
            elif os.name == 'nt':  # Windows
                os.startfile(LOG_FILENAME)
            elif os.name == 'posix':  # Linux
                subprocess.call(('xdg-open', LOG_FILENAME))
        else:
            messagebox.showinfo("Log File", "No log file found yet.")

    def _on_close(self):
        if messagebox.askokcancel("Exit", "Do you want to quit?"):
            # Stop any running threads
            if self._backtest_thread and self._backtest_thread.is_alive():
                logger.info("Stopping backtest thread...")
            if self._forward_thread and self._forward_thread.is_alive():
                logger.info("Stopping forward test thread...")
            self.destroy()

    def _update_capital_calculations(self, event=None):
        """Update all capital calculations in real-time with lot-based display"""
        try:
            available_capital = float(self.bt_initial_capital.get().replace(',', ''))
            risk_percentage = float(self.bt_risk_per_trade_percent.get())
            lot_size = int(self.bt_lot_size.get())
            # Remove default/fallback for current_price, as price comes from data in backtest/forward test
            current_price = float(self.bt_current_price.get())
            stop_loss_points = float(self.bt_base_sl_points.get())

            risk_per_unit = stop_loss_points
            max_risk_amount = available_capital * (risk_percentage / 100)
            raw_quantity = int(max_risk_amount / risk_per_unit) if risk_per_unit > 0 else 0

            if lot_size > 1:
                max_affordable_lots = int((available_capital * 0.95) // (lot_size * current_price))
                risk_based_lots = max(1, raw_quantity // lot_size) if raw_quantity > 0 else 0
                recommended_lots = min(max_affordable_lots, risk_based_lots)
                recommended_quantity = recommended_lots * lot_size
            else:
                recommended_lots = raw_quantity
                recommended_quantity = raw_quantity
                max_affordable_lots = recommended_lots

            if hasattr(self, 'recommended_lots'):
                self.recommended_lots.set(f"{recommended_lots} lots ({recommended_quantity:,} total units)")
            if hasattr(self, 'max_lots'):
                self.max_lots.set(f"{max_affordable_lots} lots max")
            if hasattr(self, 'position_value'):
                position_value = recommended_quantity * current_price
                self.position_value.set(f"â‚¹{position_value:,.0f}")

            logger.info(f"Position Sizing: {recommended_lots} lots = {recommended_quantity:,} units @ â‚¹{current_price:.2f}")

        except (ValueError, ZeroDivisionError) as e:
            logger.error(f"Position calculation error: {e}")

    def _validate_position_parameters(self) -> dict:
        """Validate all position parameters and provide feedback"""

        try:
            capital = float(self.bt_available_capital.get().replace(',', ''))
            risk_pct = float(self.bt_risk_percentage.get())
            price = float(self.bt_current_price.get())
            sl_points = float(self.bt_base_sl_points.get())
            lot_size = int(self.bt_lot_size.get())

            warnings = []
            errors = []

            # Capital validation
            if capital < 10000:
                errors.append("Minimum capital requirement: â‚¹10,000")

            # Risk validation
            if risk_pct < 0.1:
                warnings.append("Very low risk percentage may limit trading opportunities")
            elif risk_pct > 5.0:
                warnings.append("Risk percentage above 5% is aggressive")

            # Position size validation
            min_position_value = lot_size * price
            if min_position_value > capital * 0.95:
                errors.append(f"Insufficient capital for even 1 lot (â‚¹{min_position_value:,.0f} required)")

            # Stop loss validation
            if sl_points <= 0:
                errors.append("Stop loss must be positive")
            elif sl_points > price * 0.1:
                warnings.append("Stop loss seems very wide (>10% of price)")

            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "capital": capital,
                "risk_pct": risk_pct,
                "lot_size": lot_size,
                "price": price,
                "sl_points": sl_points
            }

        except ValueError:
            return {
                "valid": False,
                "errors": ["Please enter valid numeric values"],
                "warnings": []
            }

    def _build_instrument_panel(self, frame, row):
        """Build instrument selection and configuration panel"""

        instrument_frame = ttk.LabelFrame(frame, text="Instrument Configuration", padding=5)
        instrument_frame.grid(row=row, column=0, columnspan=3, sticky="ew", pady=5)

        # Instrument presets
        ttk.Label(instrument_frame, text="Instrument:").grid(row=0, column=0, sticky="e", padx=5)

        self.bt_instrument_type = tk.StringVar(value="NIFTY")
        instrument_combo = ttk.Combobox(instrument_frame, textvariable=self.bt_instrument_type,
                                       values=["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX", "BANKEX", "CUSTOM"],
                                       width=12, state="readonly")
        instrument_combo.grid(row=0, column=1, padx=5)
        instrument_combo.bind('<<ComboboxSelected>>', self._on_instrument_change)

        # Lot size gets auto-updated based on instrument
        ttk.Label(instrument_frame, text="Lot Size:").grid(row=0, column=2, sticky="e", padx=5)
        self.bt_lot_size_display = ttk.Label(instrument_frame, text="75", relief="sunken", width=10)
        self.bt_lot_size_display.grid(row=0, column=3, padx=5)

        return row + 1

    def _on_instrument_change(self, event=None):
        """Update lot size and other parameters when instrument changes"""
        instrument = self.bt_instrument_type.get()

        lot_sizes = {
            "NIFTY": 75,
            "BANKNIFTY": 25,
            "FINNIFTY": 25,
            "SENSEX": 10,
            "BANKEX": 15,
            "CUSTOM": 75, # Default for custom
            "STOCK":1
        }

        lot_size = lot_sizes.get(instrument, 75)
        self.bt_lot_size.set(str(lot_size))
        self.bt_lot_size_display.config(text=str(lot_size))

        # Trigger capital recalculation
        self._update_capital_calculations()

    def start_backtest(self):
        """Start backtesting with current configuration"""
        try:
            # Validate the configuration before starting backtest
            self._validate_indicator_configuration()

             # Get config from GUI elements
            config = self._get_backtest_config()

             # Start backtest process...
        except Exception as e:
            messagebox.showerror("Backtest Error", str(e))

    def _validate_indicator_configuration(self):
        """Ensure at least one indicator is enabled and configuration is valid"""
        enabled_indicators = [
            self.bt_use_ema_crossover.get(),
            self.bt_use_macd.get(),
            self.bt_use_vwap.get(),
            self.bt_use_rsi_filter.get(),
            self.bt_use_bb.get(),
            self.bt_use_htf_trend.get()
        ]

        if not any(enabled_indicators):
            raise ValueError("At least one indicator must be enabled")

        # Validate that required data exists for enabled indicators
        data_file = self.bt_data_path.get()
        if self.bt_use_vwap.get():
            # Check if data file has volume data for VWAP calculation
            try:
                self._validate_data_columns(data_file, ['volume', 'high', 'low'])
            except Exception:
                raise ValueError("Selected data file doesn't have required columns for VWAP calculation")
        logger.info(f"EMA: {self.bt_use_ema_crossover.get()}, MACD: {self.bt_use_macd.get()}, VWAP: {self.bt_use_vwap.get()}, HTF: {self.bt_use_htf_trend.get()}, ATR: {self.bt_use_atr.get()}")

    def _build_session_timing_panel(self, frame, row):
        """Build comprehensive user-controlled session timing panel"""

        # Session Timing Header
        ttk.Label(frame, text="Session Timing", font=('Arial', 10, 'bold')).grid(
            row=row, column=0, sticky="w", padx=5, pady=(10,2)
        )
        row += 1

        session_frame = ttk.Frame(frame)
        session_frame.grid(row=row, column=0, columnspan=3, sticky="w", padx=5, pady=2)
        row += 1

        # Session Start
        ttk.Label(session_frame, text="Session Start:").grid(row=0, column=0, sticky="e", padx=2)
        ttk.Entry(session_frame, textvariable=self.session_start_hour, width=4).grid(row=0, column=1, padx=2)
        ttk.Label(session_frame, text=":").grid(row=0, column=2)
        ttk.Entry(session_frame, textvariable=self.session_start_min, width=4).grid(row=0, column=3, padx=2)

        # Session End
        ttk.Label(session_frame, text="Session End:").grid(row=0, column=4, sticky="e", padx=(10,2))
        ttk.Entry(session_frame, textvariable=self.session_end_hour, width=4).grid(row=0, column=5, padx=2)
        ttk.Label(session_frame, text=":").grid(row=0, column=6)
        ttk.Entry(session_frame, textvariable=self.session_end_min, width=4).grid(row=0, column=7, padx=2)

        # Buffers
        ttk.Label(session_frame, text="Start Buffer (min):").grid(row=1, column=0, sticky="e", padx=2)
        ttk.Entry(session_frame, textvariable=self.start_buffer, width=6).grid(row=1, column=1, columnspan=3, padx=2)

        ttk.Label(session_frame, text="End Buffer (min):").grid(row=1, column=4, sticky="e", padx=(10,2))
        ttk.Entry(session_frame, textvariable=self.end_buffer, width=6).grid(row=1, column=5, columnspan=3, padx=2)

        # Session validation status and check button
        ttk.Label(session_frame, textvariable=self.session_status).grid(
            row=2, column=0, columnspan=4, sticky="w", pady=(5,0))
        ttk.Button(session_frame, text="Check Configuration",
                  command=self._check_session_configuration).grid(
            row=2, column=4, columnspan=4, pady=(5,0))

        # Timezone selector
        ttk.Label(session_frame, text="Timezone:").grid(row=3, column=0, sticky="e", padx=2, pady=(5,0))
        timezone_entry = ttk.Entry(session_frame, textvariable=self.timezone, width=15)
        timezone_entry.grid(row=3, column=1, columnspan=7, sticky="w", padx=2, pady=(5,0))

        return row

    def _check_session_configuration(self):
        """Check session configuration with warnings only"""
        try:
            # Get values from UI
            start_hour = int(self.session_start_hour.get())
            start_min = int(self.session_start_min.get())
            end_hour = int(self.session_end_hour.get())
            end_min = int(self.session_end_min.get())
            start_buffer = int(self.start_buffer.get())
            end_buffer = int(self.end_buffer.get())

            # Check for potential issues
            warnings = []

            # Time format validation
            if not (0 <= start_hour <= 23 and 0 <= end_hour <= 23):
                warnings.append("Hours should be between 0-23")

            if not (0 <= start_min <= 59 and 0 <= end_min <= 59):
                warnings.append("Minutes should be between 0-59")

            # Start must be before end
            start_minutes = start_hour * 60 + start_min
            end_minutes = end_hour * 60 + end_min
            if start_minutes >= end_minutes:
                warnings.append("Session end must be after session start")

            # Check if session is outside typical market hours
            if start_hour < 9 or (start_hour == 9 and start_min < 15):
                warnings.append(f"Session start {start_hour:02d}:{start_min:02d} is earlier than standard market open (09:15)")

            if end_hour > 15 or (end_hour == 15 and end_min > 30):
                warnings.append(f"Session end {end_hour:02d}:{end_min:02d} is later than standard market close (15:30)")

            # Check if buffers are reasonable
            session_duration = end_minutes - start_minutes
            total_buffers = start_buffer + end_buffer
            if total_buffers >= session_duration:
                warnings.append(
                    f"Total buffers ({total_buffers}min) should be less than session duration ({session_duration}min)")

            # Effective trading window calculation
            effective_minutes = session_duration - total_buffers

            # Show warnings but allow proceeding
            if warnings:
                result = messagebox.askokcancel(
                    "Session Configuration Warnings",
                    "The following potential issues were found:\n\n" +
                    "\n".join([f"â€¢ {w}" for w in warnings]) +
                    f"\n\nEffective trading window: {effective_minutes} minutes" +
                    "\n\nDo you want to use this configuration anyway?"
                )

                if result:  # User confirmed
                    self._apply_session_config(start_hour, start_min, end_hour, end_min,
                                             start_buffer, end_buffer)
                    self.session_status.set("Using with warnings")
                else:
                    self.session_status.set("Review recommended")
            else:
                self._apply_session_config(start_hour, start_min, end_hour, end_min,
                                         start_buffer, end_buffer)
                self.session_status.set("Configuration looks good")

        except ValueError:
            messagebox.showwarning("Input Error", "Please enter valid numbers")
            self.session_status.set("âš ï¸ Invalid number format")

    def _apply_session_config(self, start_hour, start_min, end_hour, end_min,
                         start_buffer, end_buffer):
        """Apply user configuration regardless of validation status"""
        # Ensure config attribute exists
        if not hasattr(self, 'config'):
            self.config = {}

        # Ensure session section exists
        if 'session' not in self.config:
            self.config['session'] = {}

        # Apply all settings
        self.config['session'].update({
            'start_hour': start_hour,
            'start_min': start_min,
            'end_hour': end_hour,
            'end_min': end_min,
            'start_buffer_minutes': start_buffer,
            'end_buffer_minutes': end_buffer,
            'timezone': self.timezone.get()
        })

        # Calculate effective window for informational purposes
        start_minutes = start_hour * 60 + start_min
        end_minutes = end_hour * 60 + end_min
        effective_minutes = (end_minutes - start_minutes) - (start_buffer + end_buffer)

        logger.info(f"User defined session: {start_hour:02d}:{start_min:02d}-{end_hour:02d}:{end_min:02d} " +
                   f"with {start_buffer}+{end_buffer}min buffers (effective: {effective_minutes}min)")

    def _initialize_all_variables(self):
        """Initialize all variables used by GUI components"""
        # Thread management
        self._backtest_thread = None
        self._forward_thread = None
        self.symbol_token_map = {}
        
        # Capital management variables
        self.capital_usable = tk.StringVar(value="â‚¹0 (0%)")
        self.max_lots = tk.StringVar(value="0 lots (0 shares)")
        self.max_risk = tk.StringVar(value="â‚¹0 (0%)")
        self.recommended_lots = tk.StringVar(value="0 lots (0 shares)")

        # Session configuration variables
        self.session_start_hour = tk.StringVar(value="9")
        self.session_start_min = tk.StringVar(value="15")
        self.session_end_hour = tk.StringVar(value="15")
        self.session_end_min = tk.StringVar(value="30")
        self.start_buffer = tk.StringVar(value="5")
        self.end_buffer = tk.StringVar(value="20")
        self.timezone = tk.StringVar(value="Asia/Kolkata")
        self.session_status = tk.StringVar(value="Not checked")

        # Forward test session configuration variables
        self.ft_session_start_hour = tk.StringVar(value="9")
        self.ft_session_start_min = tk.StringVar(value="15")
        self.ft_session_end_hour = tk.StringVar(value="15")
        self.ft_session_end_min = tk.StringVar(value="30")
        # Missing forward-test buffer/timezone variables (previously caused NameError)
        session_config = self.runtime_config.get('session', {})
        risk_config = self.runtime_config.get('risk', {})

        self.ft_start_buffer = tk.StringVar(value=str(session_config['start_buffer_minutes']))
        self.ft_end_buffer = tk.StringVar(value=str(session_config['end_buffer_minutes']))
        self.ft_timezone = tk.StringVar(value=session_config['timezone'])

        # Add missing forward test TP variables (fixes NameError in _ft_run_forward_test)
        tp_points = risk_config['tp_points']
        self.ft_tp1_points = tk.StringVar(value=str(tp_points[0]))
        self.ft_tp2_points = tk.StringVar(value=str(tp_points[1]))
        self.ft_tp3_points = tk.StringVar(value=str(tp_points[2]))
        self.ft_tp4_points = tk.StringVar(value=str(tp_points[3]))

        # Logger level overrides - ADD THIS SECTION
        self.logger_levels = {}
        for logger_name in ["core.indicators", "core.researchStrategy", "backtest.backtest_runner", "utils.simple_loader"]:
            self.logger_levels[logger_name] = tk.StringVar(value="DEFAULT")
        # Tick logging interval (SSOT-controlled value shown/edited in GUI)
        # Stored as stringvar for the widget; converted to int when building config
        self.logger_tick_interval = tk.StringVar(
            value=str(DEFAULT_CONFIG.get('logging', {}).get('tick_log_interval', 100))
        )
    def _create_gui_framework(self):
        """Create the core GUI framework - notebook and tabs"""
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self)

        # Create tab frames
        self.bt_tab = ttk.Frame(self.notebook)
        self.ft_tab = ttk.Frame(self.notebook)
        self.log_tab = ttk.Frame(self.notebook)

        # Add tabs to notebook
        self.notebook.add(self.bt_tab, text="Backtest")
        self.notebook.add(self.ft_tab, text="Forward Test")
        self.notebook.add(self.log_tab, text="Logs")

        # Pack notebook
        self.notebook.pack(expand=1, fill="both")

    def _build_backtest_tab(self):
        """Build the backtest tab with all controls"""
        frame = self.bt_tab
        frame.columnconfigure(1, weight=1)
        row = 0

        # Data file selection
        ttk.Label(frame, text="Data File (.csv, .log):").grid(row=row, column=0, sticky="e")
        self.bt_data_file = tk.StringVar()
        ttk.Entry(frame, textvariable=self.bt_data_file, width=55).grid(row=row, column=1, padx=5, pady=5)
        ttk.Button(frame, text="Browse", command=self._bt_browse_csv).grid(row=row, column=2, padx=5, pady=5)
        row += 1

        # Run Backtest button        ttk.Button(frame, text="Run Backtest", command=self._bt_run_backtest, style="Accent.TButton").grid(row=row, column=0, columnspan=3, pady=10)
        row += 1

        # Strategy Configuration
        ttk.Label(frame, text="Strategy Configuration", font=('Arial', 12, 'bold')).grid(row=row, column=0, columnspan=3, sticky="w", pady=(15,5))
        row += 1

        # Indicator Toggles
        ttk.Label(frame, text="Indicators:", font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky="w", padx=5, pady=2)
        row += 1
        bt_indicators_frame = ttk.Frame(frame)
        bt_indicators_frame.grid(row=row, column=0, columnspan=3, sticky="w", padx=5, pady=2)
        ttk.Checkbutton(bt_indicators_frame, text="EMA Crossover", variable=self.bt_use_ema_crossover).grid(row=0, column=0, sticky="w", padx=5)
        ttk.Checkbutton(bt_indicators_frame, text="MACD", variable=self.bt_use_macd).grid(row=0, column=1, sticky="w", padx=5)
        ttk.Checkbutton(bt_indicators_frame, text="VWAP", variable=self.bt_use_vwap).grid(row=0, column=2, sticky="w", padx=5)
        ttk.Checkbutton(bt_indicators_frame, text="RSI Filter", variable=self.bt_use_rsi_filter).grid(row=0, column=3, sticky="w", padx=5)
        ttk.Checkbutton(bt_indicators_frame, text="HTF Trend", variable=self.bt_use_htf_trend).grid(row=1, column=0, sticky="w", padx=5)
        ttk.Checkbutton(bt_indicators_frame, text="Bollinger Bands", variable=self.bt_use_bollinger_bands).grid(row=1, column=1, sticky="w", padx=5)
        ttk.Checkbutton(bt_indicators_frame, text="Stochastic", variable=self.bt_use_stochastic).grid(row=1, column=2, sticky="w", padx=5)
        ttk.Checkbutton(bt_indicators_frame, text="ATR", variable=self.bt_use_atr).grid(row=1, column=3, sticky="w", padx=5)
        row += 1

        # Parameters
        ttk.Label(frame, text="Parameters:", font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky="w", padx=5, pady=(10,2))
        row += 1
        bt_params_frame = ttk.Frame(frame)
        bt_params_frame.grid(row=row, column=0, columnspan=3, sticky="w", padx=5, pady=2)

        # EMA Parameters
        ttk.Label(bt_params_frame, text="Fast EMA:").grid(row=0, column=0, sticky="e", padx=2)
        ttk.Entry(bt_params_frame, textvariable=self.bt_fast_ema, width=8).grid(row=0, column=1, padx=2)

        ttk.Label(bt_params_frame, text="Slow EMA:").grid(row=0, column=2, sticky="e", padx=2)
        ttk.Entry(bt_params_frame, textvariable=self.bt_slow_ema, width=8).grid(row=0, column=3, padx=2)

        # MACD Parameters
        ttk.Label(bt_params_frame, text="MACD Fast:").grid(row=1, column=0, sticky="e", padx=2)
        ttk.Entry(bt_params_frame, textvariable=self.bt_macd_fast, width=8).grid(row=1, column=1, padx=2)

        ttk.Label(bt_params_frame, text="MACD Slow:").grid(row=1, column=2, sticky="e", padx=2)
        ttk.Entry(bt_params_frame, textvariable=self.bt_macd_slow, width=8).grid(row=1, column=3, padx=2)

        ttk.Label(bt_params_frame, text="MACD Signal:").grid(row=1, column=4, sticky="e", padx=2)
        ttk.Entry(bt_params_frame, textvariable=self.bt_macd_signal, width=8).grid(row=1, column=5, padx=2)

        # RSI Parameters
        ttk.Label(bt_params_frame, text="RSI Length:").grid(row=2, column=0, sticky="e", padx=2)
        ttk.Entry(bt_params_frame, textvariable=self.bt_rsi_length, width=8).grid(row=2, column=1, padx=2)

        ttk.Label(bt_params_frame, text="RSI Oversold:").grid(row=2, column=2, sticky="e", padx=2)
        ttk.Entry(bt_params_frame, textvariable=self.bt_rsi_oversold, width=8).grid(row=2, column=3, padx=2)

        ttk.Label(bt_params_frame, text="RSI Overbought:").grid(row=2, column=4, sticky="e", padx=2)
        ttk.Entry(bt_params_frame, textvariable=self.bt_rsi_overbought, width=8).grid(row=2, column=5, padx=2)

        # HTF Parameters
        ttk.Label(bt_params_frame, text="HTF Period:").grid(row=3, column=0, sticky="e", padx=2)
        ttk.Entry(bt_params_frame, textvariable=self.bt_htf_period, width=8).grid(row=3, column=1, padx=2)
        # Consecutive Green Bars
        ttk.Label(bt_params_frame, text="Green Bars Req:").grid(row=3, column=2, sticky="e", padx=2)
        ttk.Entry(bt_params_frame, textvariable=self.bt_consecutive_green_bars, width=8).grid(row=3, column=3, padx=2)
        row += 1

        # Risk Management
        ttk.Label(frame, text="Risk Management:", font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky="w", padx=5, pady=(10,2))
        row += 1
        bt_risk_frame = ttk.Frame(frame)
        bt_risk_frame.grid(row=row, column=0, columnspan=3, sticky="w", padx=5, pady=2)
        ttk.Label(bt_risk_frame, text="Stop Loss Points:").grid(row=0, column=0, sticky="e", padx=2)
        ttk.Entry(bt_risk_frame, textvariable=self.bt_base_sl_points, width=8).grid(row=0, column=1, padx=2)
        # TP Points
        ttk.Label(bt_risk_frame, text="TP1 Points:").grid(row=0, column=2, sticky="e", padx=2)
        ttk.Entry(bt_risk_frame, textvariable=self.bt_tp_points[0], width=8).grid(row=0, column=3, padx=2)
        ttk.Label(bt_risk_frame, text="TP2 Points:").grid(row=0, column=4, sticky="e", padx=2)
        ttk.Entry(bt_risk_frame, textvariable=self.bt_tp_points[1], width=8).grid(row=0, column=5, padx=2)
        ttk.Label(bt_risk_frame, text="TP3 Points:").grid(row=1, column=0, sticky="e", padx=2)
        ttk.Entry(bt_risk_frame, textvariable=self.bt_tp_points[2], width=8).grid(row=1, column=1, padx=2)

        ttk.Label(bt_risk_frame, text="TP4 Points:").grid(row=1, column=2, sticky="e", padx=2)
        ttk.Entry(bt_risk_frame, textvariable=self.bt_tp_points[3], width=8).grid(row=1, column=3, padx=2)

        self.ft_use_trail_stop = tk.BooleanVar(value=True)
        ttk.Checkbutton(bt_risk_frame, text="Use Trailing Stop", variable=self.bt_use_trail_stop).grid(row=1, column=4, columnspan=2, sticky="w", padx=5)

        ttk.Label(bt_risk_frame, text="Trail Activation Points:").grid(row=2, column=0, sticky="e", padx=2)
        ttk.Entry(bt_risk_frame, textvariable=self.bt_trail_activation, width=8).grid(row=2, column=1, padx=2)
        ttk.Label(bt_risk_frame, text="Trail Distance Points:").grid(row=2, column=2, sticky="e", padx=2)
        ttk.Entry(bt_risk_frame, textvariable=self.bt_trail_distance, width=8).grid(row=2, column=3, padx=2)
        ttk.Label(bt_risk_frame, text="Risk % per Trade:").grid(row=2, column=4, sticky="e", padx=2)
        ttk.Entry(bt_risk_frame, textvariable=self.bt_risk_per_trade_percent, width=8).grid(row=2, column=5, padx=2)
        row += 1

        # --- Instrument Settings ---
        ttk.Label(frame, text="Instrument Settings:", font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky="w", padx=5, pady=(10,2))
        row += 1
        instrument_frame = ttk.Frame(frame)
        instrument_frame.grid(row=row, column=0, columnspan=3, sticky="w", padx=5, pady=2)
        ttk.Label(instrument_frame, text="Symbol:").grid(row=0, column=0, sticky="e", padx=2)
        ttk.Entry(instrument_frame, textvariable=self.bt_symbol, width=16).grid(row=0, column=1, padx=2)
        ttk.Label(instrument_frame, text="Exchange:").grid(row=0, column=2, sticky="e", padx=2)
        ttk.Entry(instrument_frame, textvariable=self.bt_exchange, width=10).grid(row=0, column=3, padx=2)
        ttk.Label(instrument_frame, text="Lot Size:").grid(row=0, column=4, sticky="e", padx=2)
        ttk.Entry(instrument_frame, textvariable=self.bt_lot_size, width=8).grid(row=0, column=5, padx=2)
        row += 1

        # --- Capital Settings ---
        ttk.Label(frame, text="Capital Settings:", font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky="w", padx=5, pady=(10,2))
        row += 1
        capital_frame = ttk.Frame(frame)
        capital_frame.grid(row=row, column=0, columnspan=3, sticky="w", padx=5, pady=2)
        ttk.Label(capital_frame, text="Initial Capital:").grid(row=0, column=0, sticky="e", padx=2)
        ttk.Entry(capital_frame, textvariable=self.bt_initial_capital, width=14).grid(row=0, column=1, padx=2)
        row += 1

        # --- Session Settings ---
        ttk.Label(frame, text="Session Settings:", font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky="w", padx=5, pady=(10,2))
        row += 1
        session_frame = ttk.Frame(frame)
        session_frame.grid(row=row, column=0, columnspan=3, sticky="w", padx=5, pady=2)
        ttk.Label(session_frame, text="Start (HH:MM):").grid(row=0, column=0, sticky="e", padx=2)
        ttk.Entry(session_frame, textvariable=self.bt_session_start_hour, width=4).grid(row=0, column=1, padx=1)
        ttk.Label(session_frame, text=":").grid(row=0, column=2)
        ttk.Entry(session_frame, textvariable=self.bt_session_start_min, width=4).grid(row=0, column=3, padx=1)
        ttk.Label(session_frame, text="End (HH:MM):").grid(row=0, column=4, sticky="e", padx=2)
        ttk.Entry(session_frame, textvariable=self.bt_session_end_hour, width=4).grid(row=0, column=5, padx=1)
        ttk.Label(session_frame, text=":").grid(row=0, column=6)
        ttk.Entry(session_frame, textvariable=self.bt_session_end_min, width=4).grid(row=0, column=7, padx=1)
        ttk.Label(session_frame, text="Intraday:").grid(row=1, column=0, sticky="e", padx=2)
        ttk.Checkbutton(session_frame, variable=self.bt_is_intraday).grid(row=1, column=1, sticky="w", padx=2)
        row += 1

        # Results area
        self.bt_result_box = tk.Text(frame, height=20, state="disabled", wrap="word")
        self.bt_result_box.grid(row=row, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")
        frame.rowconfigure(row, weight=1)

    def _bt_browse_csv(self):
        """Browse for CSV file"""
        file = filedialog.askopenfilename(
            title="Select Data File",
            filetypes=[
                ("CSV and LOG files", "*.csv;*.log"),
                ("CSV files", "*.csv"),
                ("LOG files", "*.log"),
                ("All files", "*.*")
            ]
        )
        if file:
            self.bt_data_file.set(file)

    def _bt_run_backtest(self):
        """Run backtest with GUI configuration (enforces frozen config)"""
        try:
            frozen_config = self.build_config_from_gui()
            if frozen_config is None:
                logger.warning("Backtest aborted: invalid or unfrozen configuration")
                return
 
            # Data path: prefer backtest.data_path in config, fallback to file chooser input
            data_path = None
            try:
                data_path = frozen_config.get("backtest", {}).get("data_path") or self.bt_data_file.get()
            except Exception:
                # frozen_config is MappingProxyType; use dict() to inspect if needed
                data_path = dict(frozen_config).get("backtest", {}).get("data_path") or self.bt_data_file.get()
 
            if not data_path:
                messagebox.showerror("Missing Data", "Please select a data file for backtest.")
                return
 
            # Construct runner with frozen config (strict)
            runner = BacktestRunner(config=frozen_config, data_path=data_path)
            results = runner.run()
            self.display_backtest_results(results)
        except Exception as e:
            logger.exception("Backtest run failed: %s", e)
            messagebox.showerror("Backtest Error", f"Backtest failed: {e}")

    def _validate_nested_config(self, config):
        """Validate the nested configuration structure"""
        required_sections = ['strategy', 'risk', 'capital', 'instrument', 'session']
        for section in required_sections:
            if section not in config:
                raise ValueError(f"Missing required configuration section: {section}")
        logger.info("Configuration validation passed")

    def display_backtest_results(self, results):
        """Display backtest results in the results box"""
        if hasattr(self, 'bt_result_box'):
            self.bt_result_box.config(state="normal")
            self.bt_result_box.delete(1.0, tk.END)
            self.bt_result_box.insert(tk.END, f"Backtest Results:\n{results}\n")
            self.bt_result_box.config(state="disabled")

    def _merge_user_preferences_into_runtime_config(self):
        """Load and merge user preferences into runtime_config BEFORE widget initialization"""
        prefs_file = "user_preferences.json"
        if os.path.exists(prefs_file):
            try:
                with open(prefs_file, 'r') as f:
                    content = f.read().strip()
                    if not content:
                        logger.warning(f"Empty preferences file: {prefs_file}")
                        return
                    user_prefs = json.loads(content)

                # Shallow merge per-section (preserve keys not represented in prefs)
                for section, params in user_prefs.items():
                    if section in self.runtime_config and isinstance(params, dict):
                        self.runtime_config[section].update(params)

                logger.info(f"User preferences merged into runtime config from {prefs_file}")
            except Exception:
                logger.exception("Failed to merge user preferences into runtime config")

    def _initialize_variables_from_runtime_config(self):
        """Initialize GUI variables systematically from runtime_config (replaces _initialize_variables_from_defaults)"""
        # This method is called in __init__ but was missing
        strategy_config = self.runtime_config.get('strategy', {})
        risk_config = self.runtime_config.get('risk', {})
        capital_config = self.runtime_config.get('capital', {})
        instrument_config = self.runtime_config.get('instrument', {})
        session_config = self.runtime_config.get('session', {})
        
        # Strategy variables - systematic initialization from runtime config
        self.bt_use_ema_crossover = tk.BooleanVar(value=strategy_config.get('use_ema_crossover', True))
        self.bt_use_macd = tk.BooleanVar(value=strategy_config.get('use_macd', True))
        self.bt_use_vwap = tk.BooleanVar(value=strategy_config.get('use_vwap', True))
        self.bt_use_rsi_filter = tk.BooleanVar(value=strategy_config.get('use_rsi_filter', False))
        self.bt_use_htf_trend = tk.BooleanVar(value=strategy_config.get('use_htf_trend', False))
        self.bt_use_bollinger_bands = tk.BooleanVar(value=strategy_config.get('use_bollinger_bands', False))
        self.bt_use_stochastic = tk.BooleanVar(value=strategy_config.get('use_stochastic', False))
        self.bt_use_atr = tk.BooleanVar(value=strategy_config.get('use_atr', True))
        
        # EMA parameters
        self.bt_fast_ema = tk.StringVar(value=str(strategy_config.get('fast_ema', 9)))
        self.bt_slow_ema = tk.StringVar(value=str(strategy_config.get('slow_ema', 21)))
        
        # MACD parameters
        self.bt_macd_fast = tk.StringVar(value=str(strategy_config.get('macd_fast', 12)))
        self.bt_macd_slow = tk.StringVar(value=str(strategy_config.get('macd_slow', 26)))
        self.bt_macd_signal = tk.StringVar(value=str(strategy_config.get('macd_signal', 9)))
        
        # RSI parameters
        self.bt_rsi_length = tk.StringVar(value=str(strategy_config.get('rsi_length', 14)))
        self.bt_rsi_oversold = tk.StringVar(value=str(strategy_config.get('rsi_oversold', 30)))
        self.bt_rsi_overbought = tk.StringVar(value=str(strategy_config.get('rsi_overbought', 70)))
        
        # HTF parameter
        self.bt_htf_period = tk.StringVar(value=str(strategy_config.get('htf_period', 20)))
        self.bt_consecutive_green_bars = tk.StringVar(value=strategy_config.get('consecutive_green_bars', 3))
        
        # Risk management
        self.bt_base_sl_points = tk.StringVar(value=str(risk_config.get('base_sl_points', 15.0)))
        tp_points = risk_config.get('tp_points', [10.0, 25.0, 50.0, 100.0])
        self.bt_tp_points = [tk.StringVar(value=str(p)) for p in tp_points]
        tp_percents = risk_config.get('tp_percents', [0.25, 0.25, 0.25, 0.25])
        self.bt_tp_percents = [tk.StringVar(value=str(p*100)) for p in tp_percents]
        self.bt_use_trail_stop = tk.BooleanVar(value=risk_config.get('use_trail_stop', False))
        self.bt_trail_activation = tk.StringVar(value=str(risk_config.get('trail_activation_points', 5.0)))
        self.bt_trail_distance = tk.StringVar(value=str(risk_config.get('trail_distance_points', 7.0)))
        self.bt_risk_per_trade_percent = tk.StringVar(value=str(risk_config.get('risk_per_trade_percent', 1.0)))
        
        # Capital settings
        self.bt_initial_capital = tk.StringVar(value=str(capital_config.get('initial_capital', 100000.0)))
        
        # Instrument settings
        self.bt_symbol = tk.StringVar(value=instrument_config.get('symbol', 'NIFTY'))
        self.bt_exchange = tk.StringVar(value=instrument_config.get('exchange', 'NSE_FO'))
        self.bt_lot_size = tk.StringVar(value=str(instrument_config.get('lot_size', 75)))
        
        # Session settings
        self.bt_is_intraday = tk.BooleanVar(value=session_config.get('is_intraday', True))
        self.bt_session_start_hour = tk.StringVar(value=str(session_config.get('start_hour', 9)))
        self.bt_session_start_min = tk.StringVar(value=str(session_config.get('start_min', 15)))
        self.bt_session_end_hour = tk.StringVar(value=str(session_config.get('end_hour', 15)))
        self.bt_session_end_min = tk.StringVar(value=str(session_config.get('end_min', 30)))

    def _validate_data_columns(self, data_file, required_columns):
        """Validate that CSV file has required columns"""
        try:
            import pandas as pd
            df = pd.read_csv(data_file, nrows=1)  # Read just header
            available_columns = [col.lower() for col in df.columns]
            missing_columns = []
            
            for col in required_columns:
                if col.lower() not in available_columns:
                    missing_columns.append(col)
            
            if missing_columns:
                raise ValueError(f"Missing required columns: {missing_columns}")
            
            logger.info(f"Data validation passed for {data_file}")
            return True
        except Exception as e:
            logger.error(f"Data validation failed: {e}")
            raise

    def _update_refresh_status(self, status_message):
        """Update refresh status for symbol cache operations"""
        if hasattr(self, 'ft_cache_status'):
            self.ft_cache_status.set(status_message)
        logger.info(f"Symbol cache status: {status_message}")
def main():
    """Main entry point for the unified trading GUI"""
    try:
        app = UnifiedTradingGUI()
        app.mainloop()
    except Exception as e:
        print(f"Failed to start GUI application: {e}")

if __name__ == "__main__":
    main()