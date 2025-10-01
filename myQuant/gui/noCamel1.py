"""
unified_gui.py - Unified Trading Interface for both Backtesting and Live Trading

Provides a comprehensive GUI for:
- Configuring strategy parameters
- Running backtests
- Starting/stopping live trading
- Visualizing results
- Managing configurations
"""
import subprocess
import os
import json
import threading
import logging
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
import numpy as np
import pytz
import pandas as pd
import numpy as np
from datetime import datetime

from types import MappingProxyType
from typing import Dict, Any

from utils.config_helper import create_config_from_defaults, validate_config, freeze_config, ConfigAccessor
from backtest.backtest_runner import BacktestRunner
from utils.cache_manager import refresh_symbol_cache, load_symbol_cache
from live.trader import LiveTrader

from config.defaults import DEFAULT_CONFIG
from utils.logger import setup_from_config

# Build, validate and freeze the canonical config (FAIL-FAST if defaults are invalid).
# This ensures setup_from_config receives a proper MappingProxyType.
base_cfg = create_config_from_defaults()
validation = validate_config(base_cfg)
if not validation.get('valid', False):
    errs = validation.get('errors', []) or ["Unknown validation failure"]
    raise RuntimeError("DEFAULT_CONFIG validation failed:\n" + "\n".join(errs))
frozen_cfg = freeze_config(base_cfg)
setup_from_config(frozen_cfg)
logger = logging.getLogger(__name__)

# Add: canonical log filename from SSOT defaults (no hardcoded fallback outside defaults.py)
# use 'logfile' canonical key from defaults.py
LOG_FILENAME = DEFAULT_CONFIG.get('logging', {}).get('logfile')
if not LOG_FILENAME:
    # defensive fallback only for developer convenience (DEFAULT_CONFIG should supply this)
    LOG_FILENAME = os.path.join('logs', 'trading.log')

def now_ist():
    """Return current time in India Standard Time"""
    return datetime.now(pytz.timezone('Asia/Kolkata'))

class UnifiedTradingGUI(tk.Tk):
    
    def _initialize_all_variables(self):
        """Create minimal tkinter Variable placeholders from runtime_config (SSOT) — fail fast."""
        # runtime_config is created in __init__ before this is called
        try:
            strategy_config = self.runtime_config['strategy']
            risk_config = self.runtime_config['risk']
            capital_config = self.runtime_config['capital']
            instrument_config = self.runtime_config['instrument']
            session_config = self.runtime_config['session']
            logging_config = self.runtime_config['logging']
        except KeyError as e:
            missing = str(e).strip("'")
            logger.error("DEFAULT_CONFIG missing required section/key: %s", missing)
            messagebox.showerror("Configuration Error", f"DEFAULT_CONFIG missing required section/key: {missing}")
            raise

        # Strategy toggles / params (placeholders)
        self.bt_use_ema_crossover = tk.BooleanVar(value=strategy_config['use_ema_crossover'])
        self.bt_use_macd = tk.BooleanVar(value=strategy_config['use_macd'])
        self.bt_use_vwap = tk.BooleanVar(value=strategy_config['use_vwap'])
        self.bt_use_rsi_filter = tk.BooleanVar(value=strategy_config['use_rsi_filter'])
        self.bt_use_htf_trend = tk.BooleanVar(value=strategy_config['use_htf_trend'])
        self.bt_use_bollinger_bands = tk.BooleanVar(value=strategy_config['use_bollinger_bands'])
        self.bt_use_stochastic = tk.BooleanVar(value=strategy_config['use_stochastic'])
        self.bt_use_atr = tk.BooleanVar(value=strategy_config['use_atr'])

        self.bt_fast_ema = tk.StringVar(value=str(strategy_config['fast_ema']))
        self.bt_slow_ema = tk.StringVar(value=str(strategy_config['slow_ema']))
        self.bt_macd_fast = tk.StringVar(value=str(strategy_config['macd_fast']))
        self.bt_macd_slow = tk.StringVar(value=str(strategy_config['macd_slow']))
        self.bt_macd_signal = tk.StringVar(value=str(strategy_config['macd_signal']))
        self.bt_rsi_length = tk.StringVar(value=str(strategy_config['rsi_length']))
        self.bt_rsi_oversold = tk.StringVar(value=str(strategy_config['rsi_oversold']))
        self.bt_rsi_overbought = tk.StringVar(value=str(strategy_config['rsi_overbought']))
        self.bt_htf_period = tk.StringVar(value=str(strategy_config['htf_period']))
        self.bt_consecutive_green_bars = tk.StringVar(value=str(strategy_config['consecutive_green_bars']))

        # Risk placeholders (required — no fallbacks)
        self.bt_base_sl_points = tk.StringVar(value=str(risk_config['base_sl_points']))
        self.bt_use_trail_stop = tk.BooleanVar(value=risk_config['use_trail_stop'])
        self.bt_trail_activation = tk.StringVar(value=str(risk_config['trail_activation_points']))
        self.bt_trail_distance = tk.StringVar(value=str(risk_config['trail_distance_points']))
        self.bt_risk_per_trade_percent = tk.StringVar(value=str(risk_config['risk_per_trade_percent']))

        tp_points = risk_config['tp_points']
        self.bt_tp_points = [tk.StringVar(value=str(pt)) for pt in tp_points]
        tp_percents = risk_config['tp_percents']
        self.bt_tp_percents = [tk.StringVar(value=str(int(p * 100))) for p in tp_percents]

        # Instrument placeholders (required)
        self.bt_symbol = tk.StringVar(value=str(instrument_config['symbol']))
        self.bt_exchange = tk.StringVar(value=str(instrument_config['exchange']))
        self.bt_lot_size = tk.StringVar(value=str(instrument_config['lot_size']))

        # Capital placeholders (required)
        self.bt_initial_capital = tk.StringVar(value=str(capital_config['initial_capital']))
        self.bt_available_capital = tk.StringVar(value=str(capital_config['initial_capital']))

        # Session placeholders (required)
        self.bt_is_intraday = tk.BooleanVar(value=session_config['is_intraday'])
        self.bt_session_start_hour = tk.StringVar(value=str(session_config['start_hour']))
        self.bt_session_start_min = tk.StringVar(value=str(session_config['start_min']))
        self.bt_session_end_hour = tk.StringVar(value=str(session_config['end_hour']))
        self.bt_session_end_min = tk.StringVar(value=str(session_config['end_min']))

        # Data / misc placeholders
        self.bt_data_file = tk.StringVar(value="")
        self.bt_current_price = tk.StringVar(value="0")

        # Logger UI placeholders
        self.logger_levels = {}
        for logger_name in ["core.indicators", "core.researchStrategy", "backtest.backtest_runner", "utils.simple_loader"]:
            self.logger_levels[logger_name] = tk.StringVar(value="DEFAULT")
        self.logger_tick_interval = tk.StringVar(value=str(logging_config['tick_log_interval']))

        # Noise filter placeholders (strategy section)
        self.bt_noise_filter_enabled = tk.BooleanVar(value=strategy_config.get('noise_filter_enabled', False))
        self.bt_noise_filter_percentage = tk.StringVar(value=strategy_config.get('noise_filter_percentage', 0.0) * 100)
        self.bt_noise_filter_min_ticks = tk.StringVar(value=strategy_config.get('noise_filter_min_ticks', 1.0))

        # mark placeholders ready
        self._widgets_initialized = True

    def __init__(self, master=None):
        super().__init__(master)

        self.title("Unified Trading System")
        self.geometry("1200x800")
        self.minsize(1000, 700)

        # === SINGLE POINT OF CONFIGURATION (FIXED FLOW) ===
        # 1. Build runtime config from defaults (factory may apply normalization & user prefs)
        self.runtime_config = create_config_from_defaults()

        # 2. Initialize all GUI variables (this sets tk.Variable instances)
        #    Must happen before applying user prefs which write into tk.Variables.
        self._initialize_all_variables()

        # 3. Merge persisted user preferences into runtime_config and apply to widgets
        self._merge_user_preferences_into_runtime_config()

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

        # Add noise filter settings (no hardcoded defaults)
        config['strategy']['noise_filter_enabled'] = self.bt_noise_filter_enabled.get()
        config['strategy']['noise_filter_percentage'] = float(self.bt_noise_filter_percentage.get()) / 100.0  # Convert from percentage display
        config['strategy']['noise_filter_min_ticks'] = float(self.bt_noise_filter_min_ticks.get())

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
        ttk.Entry(params_frame, textvariable=self.bt_rsi_oversold, width=8).grid(row=2, column=3, padx=2)

        ttk.Label(params_frame, text="RSI Overbought:").grid(row=2, column=4, sticky="e", padx=2)
        ttk.Entry(params_frame, textvariable=self.bt_rsi_overbought, width=8).grid(row=2, column=5, padx=2)

        # HTF Parameters
        ttk.Label(params_frame, text="HTF Period:").grid(row=3, column=0, sticky="e", padx=2)
        ttk.Entry(params_frame, textvariable=self.bt_htf_period, width=8).grid(row=3, column=1, padx=2)
        # Consecutive Green Bars
        ttk.Label(params_frame, text="Green Bars Req:").grid(row=3, column=2, sticky="e", padx=2)
        ttk.Entry(params_frame, textvariable=self.bt_consecutive_green_bars, width=8).grid(row=3, column=3, padx=2)
        row += 1

        # Add Run Forward Test button
        ttk.Button(frame, text="Run Forward Test", command=self._ft_run_forward_test).grid(row=row, column=0, columnspan=3, pady=10)

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
        # Variables are initialized in _initialize_all_variables() to avoid duplication
        pass

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

        # Run Backtest button
        ttk.Button(frame, text="Run Backtest", command=self._bt_run_backtest).grid(row=row, column=0, columnspan=3, pady=10)
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
        row += 1

        ttk.Label(bt_risk_frame, text="Stop Loss Points:").grid(row=0, column=0, sticky="e", padx=2)
        ttk.Entry(bt_risk_frame, textvariable=self.bt_base_sl_points, width=8).grid(row=0, column=1, padx=2)

        ttk.Label(bt_risk_frame, text="TP1 Points:").grid(row=0, column=2, sticky="e", padx=2)
        ttk.Entry(bt_risk_frame, textvariable=self.bt_tp_points[0], width=8).grid(row=0, column=3, padx=2)
        ttk.Label(bt_risk_frame, text="TP2 Points:").grid(row=0, column=4, sticky="e", padx=2)
        ttk.Entry(bt_risk_frame, textvariable=self.bt_tp_points[1], width=8).grid(row=0, column=5, padx=2)
        ttk.Label(bt_risk_frame, text="TP3 Points:").grid(row=1, column=0, sticky="e", padx=2)
        ttk.Entry(bt_risk_frame, textvariable=self.bt_tp_points[2], width=8).grid(row=1, column=1, padx=2)

        ttk.Label(bt_risk_frame, text="TP4 Points:").grid(row=1, column=2, sticky="e", padx=2)
        ttk.Entry(bt_risk_frame, textvariable=self.bt_tp_points[3], width=8).grid(row=1, column=3, padx=2)

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

        # Noise Filter Section
        ttk.Label(frame, text="Noise Filter Settings:", font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky="w", padx=5, pady=(10, 0))
        row += 1

        noise_filter_frame = ttk.Frame(frame)
        noise_filter_frame.grid(row=row, column=0, columnspan=3, sticky="w", padx=5, pady=2)
        row += 1

        # Noise Filter Enable Checkbox
        ttk.Checkbutton(
            noise_filter_frame, 
            text="Enable Noise Filter", 
            variable=self.bt_noise_filter_enabled
        ).grid(row=0, column=0, sticky="w", padx=5)

        # Noise Filter Percentage
        ttk.Label(noise_filter_frame, text="Filter Threshold (%):").grid(row=0, column=1, sticky="e", padx=5)
        ttk.Entry(noise_filter_frame, textvariable=self.bt_noise_filter_percentage, width=10).grid(row=0, column=2, sticky="w", padx=5)

        # Min Ticks
        ttk.Label(noise_filter_frame, text="Min Ticks:").grid(row=0, column=3, sticky="e", padx=5)
        ttk.Entry(noise_filter_frame, textvariable=self.bt_noise_filter_min_ticks, width=10).grid(row=0, column=4, sticky="w", padx=5)
        row += 1

    def _build_log_tab(self):
        """Build the logging tab"""
        frame = self.log_tab
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        
        # Create scrolled text widget for logs
        self.log_text = tk.Text(frame, wrap="word", state="disabled")
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        scrollbar.grid(row=0, column=1, sticky="ns", pady=5)

    def _ft_refresh_cache(self):
        """Refresh symbol cache for forward testing"""
        try:
            refresh_symbol_cache()
            self.ft_cache_status.set("Cache refreshed successfully")
            logger.info("Symbol cache refreshed")
        except Exception as e:
            self.ft_cache_status.set(f"Cache refresh failed: {e}")
            logger.error(f"Cache refresh failed: {e}")

    def _ft_load_symbols(self):
        """Load and filter symbols based on user input"""
        try:
            symbol_filter = self.ft_symbol.get().strip().upper()
            if not symbol_filter:
                messagebox.showwarning("Input Required", "Please enter a symbol filter")
                return
                
            # Load symbol cache
            cache = load_symbol_cache()
            if not cache:
                messagebox.showerror("Cache Error", "Symbol cache not loaded. Please refresh cache first.")
                return
                
            # Filter symbols
            matching_symbols = [symbol for symbol in cache.keys() if symbol_filter in symbol]
            
            # Clear and populate listbox
            self.ft_symbols_listbox.delete(0, tk.END)
            for symbol in sorted(matching_symbols)[:100]:  # Limit to 100 results
                self.ft_symbols_listbox.insert(tk.END, symbol)
                
            self.ft_cache_status.set(f"Found {len(matching_symbols)} matches for '{symbol_filter}'")
            logger.info(f"Loaded {len(matching_symbols)} symbols matching '{symbol_filter}'")
            
        except Exception as e:
            self.ft_cache_status.set(f"Symbol loading failed: {e}")
            logger.error(f"Symbol loading failed: {e}")

    def _ft_update_symbol_details(self, event):
        """Update symbol details when selection changes"""
        try:
            selection = self.ft_symbols_listbox.curselection()
            if not selection:
                return
                
            selected_symbol = self.ft_symbols_listbox.get(selection[0])
            self.ft_symbol.set(selected_symbol)
            
            # Load token information
            cache = load_symbol_cache()
            if cache and selected_symbol in cache:
                token_info = cache[selected_symbol]
                self.ft_token.set(str(token_info.get('token', '')))
                logger.info(f"Selected symbol: {selected_symbol}, Token: {token_info.get('token', 'N/A')}")
            
        except Exception as e:
            logger.warning(f"Symbol details update error: {e}")
            self.ft_token.set("")

    def _ft_run_forward_test(self):
        """Run forward test with current configuration"""
        try:
            # Build configuration from GUI
            config = self.build_config_from_gui()
            if config is None:
                return
                
            # Validate required fields
            if not self.ft_symbol.get().strip():
                messagebox.showerror("Missing Symbol", "Please select a symbol for forward testing")
                return
                
            if not self.ft_token.get().strip():
                messagebox.showerror("Missing Token", "Please select a valid symbol with token information")
                return
            
            # Start forward test (this would integrate with your live trading system)
            messagebox.showinfo("Forward Test", "Forward test functionality will be implemented here")
            logger.info("Forward test initiated")
            
        except Exception as e:
            logger.exception(f"Forward test failed: {e}")
            messagebox.showerror("Forward Test Error", f"Failed to start forward test: {e}")


if __name__ == "__main__":
    try:
        app = UnifiedTradingGUI()
        logger.info("Starting GUI main loop")
        app.mainloop()
    except Exception as e:
        logger.exception("Failed to start GUI application: %s", e)
        print(f"Failed to start GUI application: {e}")