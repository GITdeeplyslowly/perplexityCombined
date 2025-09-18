"""
unified_gui.py - Unified Trading Interface for both Backtesting and Live Trading

Provides a comprehensive GUI for:
- Configuring strategy parameters
- Running backtests
- Starting/stopping live trading
- Visualizing results
- Managing configurations
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import json
from datetime import datetime
import logging
import numpy as np
import pytz
from utils.cache_manager import refresh_symbol_cache, load_symbol_cache
from live.trader import LiveTrader

# Add import for defaults
from config.defaults import DEFAULT_CONFIG
from utils.config_helper import ConfigAccessor, create_config_from_defaults
from utils.logger_setup import setup_logger, setup_logging_from_config
import logging
import json
import os
from backtest.backtest_runner import BacktestRunner

LOG_FILENAME = "unified_gui.log"
# Minimal fallback logger until runtime logging is configured in __init__
logger = setup_logger(log_file=LOG_FILENAME, log_level=logging.INFO)

# Add now_ist function
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
        self._initialize_variables_from_defaults()

        # 5. Configure logging according to runtime config (best-effort)
        try:
            setup_logging_from_config(self.runtime_config)
            # refresh module logger after reconfiguring logging
            logger = logging.getLogger(__name__)
        except Exception:
            logger.exception("setup_logging_from_config failed; using fallback logger")

        # 6. Create GUI components and tabs
        self._create_gui_framework()
        self._build_backtest_tab()
        self._build_forward_test_tab()
        self._build_log_tab()

        logger.info("GUI initialized successfully with runtime config")

    def _initialize_variables_from_defaults(self):
        """Initialize all GUI variables from runtime_config (single source for widgets)"""
        # Read sections from the runtime_config which already merges defaults + user prefs
        strategy_defaults = self.runtime_config['strategy']
        risk_defaults = self.runtime_config['risk']
        capital_defaults = self.runtime_config['capital']
        instrument_defaults = self.runtime_config['instrument']
        session_defaults = self.runtime_config['session']

        # --- Strategy variables ---
        self.bt_use_ema_crossover = tk.BooleanVar(value=strategy_defaults['use_ema_crossover'])
        self.bt_use_macd = tk.BooleanVar(value=strategy_defaults['use_macd'])
        self.bt_use_vwap = tk.BooleanVar(value=strategy_defaults['use_vwap'])
        self.bt_use_rsi_filter = tk.BooleanVar(value=strategy_defaults['use_rsi_filter'])
        self.bt_use_htf_trend = tk.BooleanVar(value=strategy_defaults['use_htf_trend'])
        self.bt_use_bollinger_bands = tk.BooleanVar(value=strategy_defaults['use_bollinger_bands'])
        self.bt_use_stochastic = tk.BooleanVar(value=strategy_defaults['use_stochastic'])
        self.bt_use_atr = tk.BooleanVar(value=strategy_defaults['use_atr'])
        
        # EMA parameters
        self.bt_fast_ema = tk.StringVar(value=str(strategy_defaults['fast_ema']))
        self.bt_slow_ema = tk.StringVar(value=str(strategy_defaults['slow_ema']))
        
        # MACD parameters - NO fallback defaults
        self.bt_macd_fast = tk.StringVar(value=str(strategy_defaults['macd_fast']))
        self.bt_macd_slow = tk.StringVar(value=str(strategy_defaults['macd_slow']))
        self.bt_macd_signal = tk.StringVar(value=str(strategy_defaults['macd_signal']))
        
        # RSI parameters - NO fallback defaults
        self.bt_rsi_length = tk.StringVar(value=str(strategy_defaults['rsi_length']))
        self.bt_rsi_oversold = tk.StringVar(value=str(strategy_defaults['rsi_oversold']))
        self.bt_rsi_overbought = tk.StringVar(value=str(strategy_defaults['rsi_overbought']))
        
        
        # HTF parameter - NO fallback defaults
        self.bt_htf_period = tk.StringVar(value=str(strategy_defaults['htf_period']))
        
        # Consecutive Green Bars parameter - NO fallback defaults
        self.bt_consecutive_green_bars = tk.StringVar(value=str(strategy_defaults['consecutive_green_bars']))

        # --- Risk management - NO fallback defaults ---
        self.bt_base_sl_points = tk.StringVar(value=str(risk_defaults['base_sl_points']))
        self.bt_tp_points = [tk.StringVar(value=str(p)) for p in risk_defaults['tp_points']]
        self.bt_tp_percents = [tk.StringVar(value=str(p*100)) for p in risk_defaults['tp_percents']]
        self.bt_use_trail_stop = tk.BooleanVar(value=risk_defaults['use_trail_stop'])
        self.bt_trail_activation = tk.StringVar(value=str(risk_defaults['trail_activation_points']))
        self.bt_trail_distance = tk.StringVar(value=str(risk_defaults['trail_distance_points']))
        self.bt_risk_per_trade_percent = tk.StringVar(value=str(risk_defaults['risk_per_trade_percent']))

        # --- Capital settings - NO fallback defaults ---
        self.bt_initial_capital = tk.StringVar(value=str(capital_defaults['initial_capital']))

        # --- Instrument settings - NO fallback defaults ---
        self.bt_symbol = tk.StringVar(value=instrument_defaults['symbol'])
        self.bt_exchange = tk.StringVar(value=instrument_defaults['exchange'])
        self.bt_lot_size = tk.StringVar(value=str(instrument_defaults['lot_size']))

        # --- Session settings - NO fallback defaults ---
        self.bt_is_intraday = tk.BooleanVar(value=session_defaults['is_intraday'])
        self.bt_session_start_hour = tk.StringVar(value=str(session_defaults['start_hour']))
        self.bt_session_start_min = tk.StringVar(value=str(session_defaults['start_min']))
        self.bt_session_end_hour = tk.StringVar(value=str(session_defaults['end_hour']))
        self.bt_session_end_min = tk.StringVar(value=str(session_defaults['end_min']))

        

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
        """Apply saved preferences to GUI controls"""
        # Map JSON preferences to GUI variables
        # Process only preferences that differ from defaults

        # Strategy parameters
        if 'strategy' in preferences:
            try:
                for k, v in preferences['strategy'].items():
                    self._set_if_exists(getattr(self, f"bt_{k}", None) or getattr(self, f"ft_{k}", None), k, preferences['strategy'])
            except Exception:
                pass


        # Risk parameters
        if 'risk' in preferences:
            risk_prefs = preferences['risk']
            self._set_if_exists(self.bt_base_sl_points, 'base_sl_points', risk_prefs)
            self._set_if_exists(self.bt_use_trail_stop, 'use_trail_stop', risk_prefs)
            self._set_if_exists(self.bt_trail_activation, 'trail_activation_points', risk_prefs)
            self._set_if_exists(self.bt_trail_distance, 'trail_distance_points', risk_prefs)
            
            # Handle tp_points and tp_percents arrays
            if 'tp_points' in risk_prefs and len(risk_prefs['tp_points']) == len(self.bt_tp_points):
                for i, tp in enumerate(risk_prefs['tp_points']):
                    self.bt_tp_points[i].set(str(tp))
            
            if 'tp_percents' in risk_prefs and len(risk_prefs['tp_percents']) == len(self.bt_tp_percents):
                for i, tp in enumerate(risk_prefs['tp_percents']):
                    self.bt_tp_percents[i].set(str(tp*100))  # Convert back to percentage display
        
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
                inst = preferences['instrument']
                if 'symbol' in inst and hasattr(self, 'bt_symbol'):
                    self.bt_symbol.set(inst['symbol'])
                if 'exchange' in inst and hasattr(self, 'bt_exchange'):
                    self.bt_exchange.set(inst['exchange'])
                # Ensure lot_size is applied as string for the StringVar
                if 'lot_size' in inst and hasattr(self, 'bt_lot_size'):
                    self.bt_lot_size.set(str(inst['lot_size']))
            except Exception:
                logger.exception("Failed to apply instrument preferences to GUI")


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
                if isinstance(var, tk.StringVar) or isinstance(var, tk.BooleanVar):
                    var.set(str(prefs_dict[key]))
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
        # Include logging defaults so the enable_smart_logger flag and verbosity
        # flow from GUI/defaults into the runner. Later expose GUI controls to edit these.
        #        from config.defaults import DEFAULT_CONFIG
        config['logging'] = DEFAULT_CONFIG.get('logging', {}).copy()

        return config

    def _validate_all_inputs_on_submit(self):
        """ONLY validation point - comprehensive validation when user submits"""
        errors = []
        warnings = []
        
        try:
            # Strategy validation
            fast_ema = int(self.bt_fast_ema.get())
            slow_ema = int(self.bt_slow_ema.get())
            
            if fast_ema >= slow_ema:
                errors.append("Fast EMA must be less than Slow EMA")
            
            if fast_ema <= 0 or slow_ema <= 0:
                errors.append("EMA periods must be positive")
            
            # MACD validation
            macd_fast = int(self.bt_macd_fast.get())
            macd_slow = int(self.bt_macd_slow.get())
            macd_signal = int(self.bt_macd_signal.get())
            
            if macd_fast >= macd_slow:
                errors.append("MACD fast must be less than MACD slow")
            
            # Risk validation
            capital = float(self.bt_initial_capital.get())
            if capital <= 0:
                errors.append("Initial capital must be positive")
            
            if capital < 10000:
                warnings.append("Capital below recommended minimum of ₹10,000")
            
            risk_pct = float(self.bt_risk_per_trade_percent.get())
            if risk_pct <= 0 or risk_pct > 100:
                errors.append("Risk percentage must be between 0 and 100")
            
            sl_points = float(self.bt_base_sl_points.get())
            if sl_points <= 0:
                errors.append("Stop loss points must be positive")
            
            # TP validation
            tp_points = [float(var.get()) for var in self.bt_tp_points]
            if any(tp <= 0 for tp in tp_points):
                errors.append("All take profit points must be positive")
            
            if any(tp <= sl_points for tp in tp_points):
                errors.append("Take profit points must be greater than stop loss")
            
            # Session validation
            start_hour = int(self.bt_session_start_hour.get())
            start_min = int(self.bt_session_start_min.get())
            end_hour = int(self.bt_session_end_hour.get())
            end_min = int(self.bt_session_end_min.get())
            
            if not (0 <= start_hour <= 23 and 0 <= end_hour <= 23):
                errors.append("Hours must be between 0 and 23")
            
            if not (0 <= start_min <= 59 and 0 <= end_min <= 59):
                errors.append("Minutes must be between 0 and 59")
            
            start_minutes = start_hour * 60 + start_min
            end_minutes = end_hour * 60 + end_min
            
            if start_minutes >= end_minutes:
                errors.append("Session start must be before session end")
            
            # Instrument validation
            lot_size = int(self.bt_lot_size.get())
            if lot_size <= 0:
                errors.append("Lot size must be positive")
            
        except ValueError as e:
            errors.append(f"Invalid numeric input: {e}")
        
        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}

    def run_backtest(self):
        """Run backtest with GUI configuration - VALIDATE ONLY HERE"""
        # SINGLE VALIDATION POINT
        validation = self._validate_all_inputs_on_submit()
        
        if not validation["valid"]:
            error_msg = "\n".join(validation["errors"])
            messagebox.showerror("Validation Failed", f"Please fix the following errors:\n\n{error_msg}")
            return
        
        # Show warnings if any
        if validation["warnings"]:
            warning_msg = "\n".join(validation["warnings"])
            if not messagebox.askyesno("Warnings", f"Found warnings:\n\n{warning_msg}\n\nContinue anyway?"):
                return
        
        try:
            # Get configuration directly from GUI
            config = self.build_config_from_gui()

            # Log the actual configuration used
            logger.info("====== BACKTEST CONFIGURATION ======")
            logger.info("Using TRUE INCREMENTAL PROCESSING (row-by-row)")
            logger.info("Batch processing completely eliminated")
            for section, params in config.items():
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
            if symbols is not None:
                self._update_symbol_listbox(symbols)
                logger.info(f"Symbol cache refreshed: {len(symbols)} symbols loaded")
            else:
                logger.warning("Symbol cache refresh completed with no new symbols")
        except Exception as e:
            logger.exception(f"Error refreshing symbol cache: {e}")

    def _update_refresh_status(self, count):
        """Update the refresh status label (thread-safe)"""
        if hasattr(self, 'ft_cache_status'):
            self.ft_cache_status.set(f"Cache refreshed: {count} symbols loaded.")

    def _update_symbol_listbox(self, symbols):
        """Update the symbol listbox with new data (thread-safe)"""
        if hasattr(self, 'ft_symbols_listbox'):
            # Clear existing items
            self.ft_symbols_listbox.delete(0, tk.END)
            # Insert new items
            for symbol in symbols:
                self.ft_symbols_listbox.insert(tk.END, symbol)
            logger.info(f"Symbol listbox updated with {len(symbols)} symbols")
        else:
            logger.warning("ft_symbols_listbox attribute not found")

    def _ft_load_symbols(self):
        """Load symbols from cache based on filter"""
        try:
            filter_text = self.ft_symbol.get().strip()
            exchange = self.ft_exchange.get()

            # Validate exchange selection
            if exchange not in ["NSE_FO", "NSE_CM", "BSE_CM"]:
                messagebox.showerror("Invalid Exchange", "Please select a valid exchange")
                return

            # Load symbols from cache
            all_symbols = load_symbol_cache()
            if all_symbols is None:
                messagebox.showerror("Cache Error", "Symbol cache is empty or not found")
                return

            # Filter symbols by exchange and search text
            filtered_symbols = [s for s in all_symbols if s.startswith(exchange) and filter_text in s]

            # Update the listbox with filtered symbols
            self.ft_symbols_listbox.delete(0, tk.END)
            for symbol in filtered_symbols:
                self.ft_symbols_listbox.insert(tk.END, symbol)

            self.ft_cache_status.set(f"Loaded {len(filtered_symbols)} symbols")
            logger.info(f"Loaded {len(filtered_symbols)} symbols for {exchange} with filter '{filter_text}'")
        except Exception as e:
            logger.exception(f"Error loading symbols: {e}")
            messagebox.showerror("Load Symbols Error", f"Failed to load symbols: {e}")

    def _ft_update_symbol_details(self, event):
        """Update token and other details when a symbol is selected"""
        try:
            selected_symbol = self.ft_symbols_listbox.get(self.ft_symbols_listbox.curselection())
            if not selected_symbol:
                return

            # Extract token using the symbol-to-token map
            token = self.symbol_token_map.get(selected_symbol, None)
            if token:
                self.ft_token.set(token)
            else:
                # If token not found, clear the token field
                self.ft_token.set("")

            logger.info(f"Updated details for selected symbol: {selected_symbol}")
        except Exception as e:
            logger.exception(f"Error updating symbol details: {e}")

    def _ft_run_forward_test(self):
        """Start the forward test process"""
        try:
            # Validate that at least one symbol is selected
            selected_symbols = [self.ft_symbols_listbox.get(i) for i in self.ft_symbols_listbox.curselection()]
            if not selected_symbols:
                messagebox.showerror("No Symbol Selected", "Please select at least one symbol to test")
                return

            # Confirm with the user before starting the forward test
            if not messagebox.askyesno("Confirm Forward Test", "This will start the forward test with the selected symbols. Proceed?"):
                return

            # Disable controls to prevent changes during testing
            self._set_forward_test_controls_state(tk.DISABLED)

            # --- CRITICAL: Use the updated symbol list for testing ---
            symbols_to_test = [self.ft_symbols_listbox.get(i) for i in range(self.ft_symbols_listbox.size())]
            logger.info(f"Starting forward test for symbols: {symbols_to_test}")

            # Start the forward test in a new thread
            self._forward_thread = threading.Thread(target=self._run_forward_test_process, args=(symbols_to_test,), daemon=True)
            self._forward_thread.start()

            messagebox.showinfo("Forward Test Started", "The forward test has been started in the background.")
        except Exception as e:
            logger.exception(f"Error starting forward test: {e}")
            messagebox.showerror("Forward Test Error", f"Failed to start forward test: {e}")

    def _run_forward_test_process(self, symbols):
        """The main process for running the forward test"""
        try:
            # --- CRITICAL: Use the updated symbol list directly ---
            for symbol in symbols:
                # Skip empty symbols
                if not symbol.strip():
                    continue

                # For debugging: Log each symbol being processed
                logger.info(f"Processing symbol: {symbol}")

                # Here you would add the logic to run the forward test for each symbol
                # This is highly dependent on how the forward testing is implemented
                # For example, you might call a method like:
                # result = self.forward_tester.run(symbol, self.bt_current_price.get(), ...)

                # Simulate some processing time
                import time
                time.sleep(1)  # Remove or adjust this in the real implementation

            logger.info("Forward test process completed")
        except Exception as e:
            logger.exception(f"Error in forward test process: {e}")

        # Re-enable the controls after the test is complete
        self._set_forward_test_controls_state(tk.NORMAL)

    def _set_forward_test_controls_state(self, state):
        """Enable or disable the forward test controls"""
        for widget in [self.ft_symbol_entry, self.ft_exchange, self.ft_symbols_listbox, self.ft_token,
                        self.ft_feed_type, self.ft_use_ema_crossover, self.ft_use_macd, self.ft_use_vwap,
                        self.ft_use_rsi_filter, self.ft_use_htf_trend, self.ft_use_bollinger_bands,
                        self.ft_use_stochastic, self.ft_use_atr, self.ft_fast_ema, self.ft_slow_ema,
                        self.ft_macd_fast, self.ft_macd_slow, self.ft_macd_signal, self.ft_rsi_length,
                        self.ft_rsi_oversold, self.ft_rsi_overbought, self.ft_htf_period, self.bt_consecutive_green_bars,
                        self.ft_base_sl_points, self.bt_tp_points[0], self.bt_tp_points[1], self.bt_tp_points[2],
                        self.bt_tp_points[3], self.ft_use_trail_stop, self.ft_trail_activation_points,
                        self.ft_trail_distance_points, self.ft_risk_per_trade_percent, self.ft_initial_capital,
                        self.bt_session_start_hour, self.bt_session_start_min, self.bt_session_end_hour,
                        self.bt_session_end_min]:
            widget.configure(state=state)

    def _ft_stop_forward_test(self):
        """Stop the forward test process"""
        try:
            if self._forward_thread and self._forward_thread.is_alive():
                # Signal the thread to stop (implement a proper stop mechanism in the thread)
                logger.info("Stopping forward test thread...")
                # You might need to set a flag or use another mechanism to stop the thread gracefully
                # For example:
                # self.forward_tester.stop()
                
                # Wait for the thread to finish
                self._forward_thread.join(timeout=5)
                logger.info("Forward test thread stopped")
            else:
                logger.warning("No active forward test thread to stop")
        except Exception as e:
            logger.exception(f"Error stopping forward test: {e}")

    def _build_log_tab(self):
        frame = self.log_tab
        frame.columnconfigure(0, weight=1)
        row = 0

        # Log file selection
        ttk.Label(frame, text="Log File:").grid(row=row, column=0, sticky="e")
        self.log_file_var = tk.StringVar(value=LOG_FILENAME)
        ttk.Entry(frame, textvariable=self.log_file_var, width=55).grid(row=row, column=1, padx=5, pady=5)
        ttk.Button(frame, text="Open Log", command=self._open_log_file).grid(row=row, column=2, padx=5, pady=5)
        row += 1

        # Log level selection
        ttk.Label(frame, text="Log Level:").grid(row=row, column=0, sticky="e")
        self.log_level_var = tk.StringVar(value="INFO")
        log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        ttk.Combobox(frame, textvariable=self.log_level_var, values=log_levels, width=10, state='readonly').grid(row=row, column=1, sticky="w", padx=5, pady=5)
        row += 1

        # Log text box
        self.log_text = tk.Text(frame, height=20, state="disabled", wrap="word")
        self.log_text.grid(row=row, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")
        frame.rowconfigure(row, weight=1)

        # Load initial log file
        self._load_log_file()

    def _open_log_file(self):
        """Open the log file in the default text editor"""
        try:
            log_file = self.log_file_var.get()
            if os.path.exists(log_file):
                os.startfile(log_file)
                logger.info(f"Opened log file: {log_file}")
            else:
                messagebox.showerror("File Not Found", f"Log file not found: {log_file}")
        except Exception as e:
            logger.exception(f"Error opening log file: {e}")
            messagebox.showerror("Open File Error", f"Failed to open log file: {e}")

    def _load_log_file(self):
        """Load the log file and display its content in the text box"""
        try:
            log_file = self.log_file_var.get()
            if os.path.exists(log_file):
                with open(log_file, "r") as f:
                    log_content = f.read()
                self.log_text.config(state="normal")
                self.log_text.delete(1.0, tk.END)
                self.log_text.insert(tk.END, log_content)
                self.log_text.config(state="disabled")
                logger.info(f"Loaded log file: {log_file}")
            else:
                messagebox.showerror("File Not Found", f"Log file not found: {log_file}")
        except Exception as e:
            logger.exception(f"Error loading log file: {e}")
            messagebox.showerror("Load File Error", f"Failed to load log file: {e}")

    def _merge_user_preferences_into_runtime_config(self):
        """Load and merge user preferences into runtime_config BEFORE widget initialization"""
        prefs_file = "user_preferences.json"
        if os.path.exists(prefs_file):
            try:
                with open(prefs_file, 'r') as f:
                    user_prefs = json.load(f)

                # Shallow merge per-section (preserve keys not represented in prefs)
                for section, params in user_prefs.items():
                    if section in self.runtime_config and isinstance(params, dict):
                        self.runtime_config[section].update(params)

                logger.info(f"User preferences merged into runtime config from {prefs_file}")
            except Exception:
                logger.exception("Failed to merge user preferences into runtime config")

    def _initialize_all_variables(self):
        """Initialize all variables used by GUI components"""
        # Thread management
        self._backtest_thread = None
        self._forward_thread = None
        self.symbol_token_map = {}

        # Capital management variables
        self.capital_usable = tk.StringVar(value="₹0 (0%)")
        self.max_lots = tk.StringVar(value="0 lots (0 shares)")
        self.max_risk = tk.StringVar(value="₹0 (0%)")
        self.recommended_lots = tk.StringVar(value="0 lots (0 shares)")
        self.position_value = tk.StringVar(value="₹0")

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
        self.ft_start_buffer = tk.StringVar(value="5")
        self.ft_end_buffer = tk.StringVar(value="20")
        self.ft_timezone = tk.StringVar(value="Asia/Kolkata")

        # CRITICAL: Add missing forward test TP variables
        self.ft_tp1_points = tk.StringVar(value="20")
        self.ft_tp2_points = tk.StringVar(value="35")
        self.ft_tp3_points = tk.StringVar(value="50")
        self.ft_tp4_points = tk.StringVar(value="75")
        
        # CRITICAL: Add missing current price variable
        self.bt_current_price = tk.StringVar(value="100")
        
        # CRITICAL: Add missing capital variables
        self.bt_available_capital = tk.StringVar(value="100000")
        self.bt_risk_percentage = tk.StringVar(value="1.0")
        
        # CRITICAL: Add missing forward test capital variable
        self.ft_initial_capital = tk.StringVar(value="100000")

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
        ttk.Button(frame, text="Run Backtest", command=self._bt_run_backtest, style="Accent.TButton").grid(row=row, column=0, columnspan=3, pady=10)
        row += 1

        # Strategy Configuration
        ttk.Label(frame, text="Strategy Configuration", font=('Arial', 12, 'bold')).grid(row=row, column=0, columnspan=3, sticky="w", pady=(15,5))
        row += 1

def main():
    """Main entry point for the unified trading GUI"""
    try:
        app = UnifiedTradingGUI()
        app.mainloop()
    except Exception as e:
        print(f"Failed to start GUI application: {e}")

if __name__ == "__main__":
    main()