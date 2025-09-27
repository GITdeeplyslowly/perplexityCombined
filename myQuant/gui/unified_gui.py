# ...existing code...
"""
unified_gui.py - Unified Trading Interface for Backtesting, Forward Testing and Live Trading

Merged version: restores validation, background refresh, preferences loader/apply,
missing variables, and UI elements from previous copy while keeping new fixes.
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
import time

from utils.cache_manager import refresh_symbol_cache, load_symbol_cache
from live.trader import LiveTrader
from backtest.backtest_runner import BacktestRunner

from config.defaults import DEFAULT_CONFIG
from utils.config_helper import ConfigAccessor, create_config_from_defaults
from utils.logger_setup import setup_logger, setup_logging_from_config

LOG_FILENAME = "unified_gui.log"
logger = setup_logger(log_file=LOG_FILENAME, log_level=logging.INFO)


def now_ist():
    return datetime.now(pytz.timezone('Asia/Kolkata'))


class UnifiedTradingGUI(tk.Tk):
    def __init__(self, master=None):
        super().__init__(master)
        self.title("Unified Trading System")
        self.geometry("1200x800")
        self.minsize(1000, 700)

        # 1. Build runtime config from defaults
        self.runtime_config = create_config_from_defaults()

        # 2. Merge persisted user preferences into runtime_config BEFORE widget creation
        self._merge_user_preferences_into_runtime_config()

        # 3. Initialize all GUI-only variables
        self._initialize_all_variables()

        # 4. Initialize GUI variables from runtime_config (single source for widgets)
        self._initialize_variables_from_defaults()

        # 5. Configure logging according to runtime config (best-effort)
        try:
            setup_logging_from_config(self.runtime_config)
        except Exception:
            logger.exception("setup_logging_from_config failed; using fallback logger")

        # 6. Create GUI
        self._create_gui_framework()
        self._build_backtest_tab()
        self._build_forward_test_tab()
        self._build_log_tab()

        # 7. Optionally apply any legacy user preference mapping to GUI variables
        self._load_user_preferences()

        logger.info("GUI initialized successfully")

    # --------------------
    # Variable initialization
    # --------------------
    def _initialize_all_variables(self):
        """Initialize GUI-only variables (no defaults from config)."""
        # Thread, state
        self._backtest_thread = None
        self._forward_thread = None
        self.symbol_token_map = {}

        # Log
        self.log_file_var = tk.StringVar(value=LOG_FILENAME)
        self.log_level_var = tk.StringVar(value="INFO")

        # Data / backtest
        self.bt_data_file = tk.StringVar()

        # Capital management variables (UI-only)
        self.capital_usable = tk.StringVar(value="₹0 (0%)")
        self.max_lots = tk.StringVar(value="0 lots (0 shares)")
        self.max_risk = tk.StringVar(value="₹0 (0%)")
        self.recommended_lots = tk.StringVar(value="0 lots (0 shares)")
        self.position_value = tk.StringVar(value="₹0")
        self.bt_current_price = tk.StringVar(value="100")
        self.bt_available_capital = tk.StringVar(value="100000")
        self.bt_risk_percentage = tk.StringVar(value="1.0")

        # Session configuration variables (UI-only defaults)
        self.session_start_hour = tk.StringVar(value="9")
        self.session_start_min = tk.StringVar(value="15")
        self.session_end_hour = tk.StringVar(value="15")
        self.session_end_min = tk.StringVar(value="30")
        self.start_buffer = tk.StringVar(value="5")
        self.end_buffer = tk.StringVar(value="20")
        self.timezone = tk.StringVar(value="Asia/Kolkata")
        self.session_status = tk.StringVar(value="Not checked")

        # Forward test session config UI-only
        self.ft_session_start_hour = tk.StringVar(value="9")
        self.ft_session_start_min = tk.StringVar(value="15")
        self.ft_session_end_hour = tk.StringVar(value="15")
        self.ft_session_end_min = tk.StringVar(value="30")
        self.ft_start_buffer = tk.StringVar(value="5")
        self.ft_end_buffer = tk.StringVar(value="20")
        self.ft_timezone = tk.StringVar(value="Asia/Kolkata")

        # Individual forward-test TP variables (legacy/missing ones)
        self.ft_tp1_points = tk.StringVar(value="20")
        self.ft_tp2_points = tk.StringVar(value="35")
        self.ft_tp3_points = tk.StringVar(value="50")
        self.ft_tp4_points = tk.StringVar(value="75")

        # Forward test flags
        self.ft_paper_trading = tk.BooleanVar(value=True)

        # Placeholders that will usually be overridden by _initialize_variables_from_defaults
        self.ft_feed_type = tk.StringVar(value="Quote")
        self.ft_symbol = tk.StringVar(value="")
        self.ft_exchange = tk.StringVar(value="NSE_FO")
        self.ft_token = tk.StringVar(value="")
        self.ft_cache_status = tk.StringVar(value="Cache not loaded")

    def _initialize_variables_from_defaults(self):
        """Initialize all widget variables from runtime_config (single source)."""
        # Guard: ensure runtime_config has expected sections
        rd = self.runtime_config
        strategy_defaults = rd.get('strategy', {})
        risk_defaults = rd.get('risk', {})
        capital_defaults = rd.get('capital', {})
        instrument_defaults = rd.get('instrument', {})
        session_defaults = rd.get('session', {})

        # --- Backtest (bt_) variables from defaults ---
        self.bt_use_ema_crossover = tk.BooleanVar(value=strategy_defaults.get('use_ema_crossover', False))
        self.bt_use_macd = tk.BooleanVar(value=strategy_defaults.get('use_macd', False))
        self.bt_use_vwap = tk.BooleanVar(value=strategy_defaults.get('use_vwap', False))
        self.bt_use_rsi_filter = tk.BooleanVar(value=strategy_defaults.get('use_rsi_filter', False))
        self.bt_use_htf_trend = tk.BooleanVar(value=strategy_defaults.get('use_htf_trend', False))
        self.bt_use_bollinger_bands = tk.BooleanVar(value=strategy_defaults.get('use_bollinger_bands', False))
        self.bt_use_stochastic = tk.BooleanVar(value=strategy_defaults.get('use_stochastic', False))
        self.bt_use_atr = tk.BooleanVar(value=strategy_defaults.get('use_atr', False))

        self.bt_fast_ema = tk.StringVar(value=str(strategy_defaults.get('fast_ema', 9)))
        self.bt_slow_ema = tk.StringVar(value=str(strategy_defaults.get('slow_ema', 21)))
        self.bt_macd_fast = tk.StringVar(value=str(strategy_defaults.get('macd_fast', 12)))
        self.bt_macd_slow = tk.StringVar(value=str(strategy_defaults.get('macd_slow', 26)))
        self.bt_macd_signal = tk.StringVar(value=str(strategy_defaults.get('macd_signal', 9)))
        self.bt_rsi_length = tk.StringVar(value=str(strategy_defaults.get('rsi_length', 14)))
        self.bt_rsi_oversold = tk.StringVar(value=str(strategy_defaults.get('rsi_oversold', 30)))
        self.bt_rsi_overbought = tk.StringVar(value=str(strategy_defaults.get('rsi_overbought', 70)))
        self.bt_htf_period = tk.StringVar(value=str(strategy_defaults.get('htf_period', 20)))
        self.bt_consecutive_green_bars = tk.StringVar(value=str(strategy_defaults.get('consecutive_green_bars', 0)))

        # Risk defaults
        self.bt_base_sl_points = tk.StringVar(value=str(risk_defaults.get('base_sl_points', 15)))
        self.bt_tp_points = [tk.StringVar(value=str(p)) for p in risk_defaults.get('tp_points', [20, 35, 50, 75])]
        # ensure bt_tp_percents length matches
        self.bt_tp_percents = [tk.StringVar(value=str(p * 100)) for p in risk_defaults.get('tp_percents', [0.5, 0.3, 0.2, 0.0])]
        self.bt_use_trail_stop = tk.BooleanVar(value=risk_defaults.get('use_trail_stop', True))
        self.bt_trail_activation = tk.StringVar(value=str(risk_defaults.get('trail_activation_points', 25)))
        self.bt_trail_distance = tk.StringVar(value=str(risk_defaults.get('trail_distance_points', 10)))
        self.bt_risk_per_trade_percent = tk.StringVar(value=str(risk_defaults.get('risk_per_trade_percent', 1.0)))

        # Capital defaults
        self.bt_initial_capital = tk.StringVar(value=str(capital_defaults.get('initial_capital', 100000)))

        # Instrument defaults
        self.bt_symbol = tk.StringVar(value=instrument_defaults.get('symbol', ''))
        self.bt_exchange = tk.StringVar(value=instrument_defaults.get('exchange', 'NSE_FO'))
        self.bt_lot_size = tk.StringVar(value=str(instrument_defaults.get('lot_size', 1)))

        # Session defaults
        self.bt_is_intraday = tk.BooleanVar(value=session_defaults.get('is_intraday', True))
        self.bt_session_start_hour = tk.StringVar(value=str(session_defaults.get('start_hour', 9)))
        self.bt_session_start_min = tk.StringVar(value=str(session_defaults.get('start_min', 15)))
        self.bt_session_end_hour = tk.StringVar(value=str(session_defaults.get('end_hour', 15)))
        self.bt_session_end_min = tk.StringVar(value=str(session_defaults.get('end_min', 30)))

        # === Forward test (ft_) variables - use same defaults (SSOT) ===
        self.ft_tp_points = [tk.StringVar(value=str(p)) for p in risk_defaults.get('tp_points', [20, 35, 50, 75])]

        self.ft_fast_ema = tk.StringVar(value=str(strategy_defaults.get('fast_ema', 9)))
        self.ft_slow_ema = tk.StringVar(value=str(strategy_defaults.get('slow_ema', 21)))
        self.ft_macd_fast = tk.StringVar(value=str(strategy_defaults.get('macd_fast', 12)))
        self.ft_macd_slow = tk.StringVar(value=str(strategy_defaults.get('macd_slow', 26)))
        self.ft_macd_signal = tk.StringVar(value=str(strategy_defaults.get('macd_signal', 9)))
        self.ft_rsi_length = tk.StringVar(value=str(strategy_defaults.get('rsi_length', 14)))
        self.ft_rsi_oversold = tk.StringVar(value=str(strategy_defaults.get('rsi_oversold', 30)))
        self.ft_rsi_overbought = tk.StringVar(value=str(strategy_defaults.get('rsi_overbought', 70)))
        self.ft_htf_period = tk.StringVar(value=str(strategy_defaults.get('htf_period', 20)))

        self.ft_base_sl_points = tk.StringVar(value=str(risk_defaults.get('base_sl_points', 15)))
        self.ft_trail_activation_points = tk.StringVar(value=str(risk_defaults.get('trail_activation_points', 25)))
        self.ft_trail_distance_points = tk.StringVar(value=str(risk_defaults.get('trail_distance_points', 10)))
        self.ft_risk_per_trade_percent = tk.StringVar(value=str(risk_defaults.get('risk_per_trade_percent', 1.0)))

        self.ft_use_ema_crossover = tk.BooleanVar(value=strategy_defaults.get('use_ema_crossover', True))
        self.ft_use_macd = tk.BooleanVar(value=strategy_defaults.get('use_macd', True))
        self.ft_use_vwap = tk.BooleanVar(value=strategy_defaults.get('use_vwap', True))
        self.ft_use_rsi_filter = tk.BooleanVar(value=strategy_defaults.get('use_rsi_filter', False))
        self.ft_use_htf_trend = tk.BooleanVar(value=strategy_defaults.get('use_htf_trend', True))
        self.ft_use_bollinger_bands = tk.BooleanVar(value=strategy_defaults.get('use_bollinger_bands', False))
        self.ft_use_stochastic = tk.BooleanVar(value=strategy_defaults.get('use_stochastic', False))
        self.ft_use_atr = tk.BooleanVar(value=strategy_defaults.get('use_atr', True))
        self.ft_use_trail_stop = tk.BooleanVar(value=risk_defaults.get('use_trail_stop', True))

        self.ft_initial_capital = tk.StringVar(value=str(capital_defaults.get('initial_capital', 100000)))
        self.ft_symbol.set(instrument_defaults.get('symbol', ''))
        self.ft_exchange.set(instrument_defaults.get('exchange', 'NSE_FO'))
        self.ft_feed_type = tk.StringVar(value=self.runtime_config.get('forward', {}).get('feed_type', 'Quote'))
        self.ft_token = tk.StringVar(value="")
        self.ft_cache_status = tk.StringVar(value="Cache not loaded")

    # --------------------
    # Preferences loading / applying helpers
    # --------------------
    def _merge_user_preferences_into_runtime_config(self):
        """Load and merge user preferences into runtime_config BEFORE widget initialization"""
        prefs_file = "user_preferences.json"
        if os.path.exists(prefs_file):
            try:
                with open(prefs_file, 'r') as f:
                    user_prefs = json.load(f)
                for section, params in user_prefs.items():
                    if section in self.runtime_config and isinstance(params, dict):
                        self.runtime_config[section].update(params)
                logger.info(f"User preferences merged into runtime config from {prefs_file}")
            except Exception:
                logger.exception("Failed to merge user preferences into runtime config")

    def _load_user_preferences(self):
        """Load legacy preferences and apply to GUI variables where applicable"""
        prefs_file = "user_preferences.json"
        if os.path.exists(prefs_file):
            try:
                with open(prefs_file, 'r') as f:
                    prefs = json.load(f)
                self._apply_preferences_to_gui(prefs)
                logger.info("User preferences applied to GUI (legacy mapping)")
            except Exception:
                logger.exception("Failed to load/apply user preferences")

    def _apply_preferences_to_gui(self, preferences):
        """Apply saved preferences to GUI controls (legacy mapping)"""
        try:
            if 'strategy' in preferences:
                for k, v in preferences['strategy'].items():
                    var = getattr(self, f"bt_{k}", None) or getattr(self, f"ft_{k}", None)
                    self._set_if_exists(var, k, preferences['strategy'])
        except Exception:
            pass

        # Risk params
        if 'risk' in preferences:
            risk_prefs = preferences['risk']
            self._set_if_exists(self.bt_base_sl_points, 'base_sl_points', risk_prefs)
            self._set_if_exists(self.bt_use_trail_stop, 'use_trail_stop', risk_prefs)
            self._set_if_exists(self.bt_trail_activation, 'trail_activation_points', risk_prefs)
            self._set_if_exists(self.bt_trail_distance, 'trail_distance_points', risk_prefs)

            if 'tp_points' in risk_prefs and len(risk_prefs['tp_points']) == len(self.bt_tp_points):
                for i, tp in enumerate(risk_prefs['tp_points']):
                    self.bt_tp_points[i].set(str(tp))

            if 'tp_percents' in risk_prefs and len(risk_prefs['tp_percents']) == len(self.bt_tp_percents):
                for i, tp in enumerate(risk_prefs['tp_percents']):
                    self.bt_tp_percents[i].set(str(tp * 100))
        # Capital
        if 'capital' in preferences:
            try:
                if 'initial_capital' in preferences['capital']:
                    self.bt_initial_capital.set(str(preferences['capital']['initial_capital']))
            except Exception:
                pass
        # Instrument
        if 'instrument' in preferences:
            inst = preferences['instrument']
            if 'symbol' in inst:
                self.bt_symbol.set(inst['symbol'])
                self.ft_symbol.set(inst['symbol'])
            if 'exchange' in inst:
                self.bt_exchange.set(inst['exchange'])
                self.ft_exchange.set(inst['exchange'])
            if 'lot_size' in inst:
                self.bt_lot_size.set(str(inst['lot_size']))

        # Session
        if 'session' in preferences:
            s = preferences['session']
            if 'start_hour' in s:
                self.bt_session_start_hour.set(str(s['start_hour']))
                self.ft_session_start_hour.set(str(s['start_hour']))
            if 'start_min' in s:
                self.bt_session_start_min.set(str(s['start_min']))
                self.ft_session_start_min.set(str(s['start_min']))
            if 'end_hour' in s:
                self.bt_session_end_hour.set(str(s['end_hour']))
                self.ft_session_end_hour.set(str(s['end_hour']))
            if 'end_min' in s:
                self.bt_session_end_min.set(str(s['end_min']))
                self.ft_session_end_min.set(str(s['end_min']))

    def _set_if_exists(self, var, key, prefs_dict):
        """Safely set a tkinter Variable if preference key exists"""
        if key in prefs_dict and var is not None:
            try:
                if isinstance(var, (tk.StringVar, tk.BooleanVar)):
                    var.set(str(prefs_dict[key]))
            except Exception:
                pass

    # --------------------
    # GUI framework creation
    # --------------------
    def _create_gui_framework(self):
        self.notebook = ttk.Notebook(self)
        self.bt_tab = ttk.Frame(self.notebook)
        self.ft_tab = ttk.Frame(self.notebook)
        self.log_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.bt_tab, text="Backtest")
        self.notebook.add(self.ft_tab, text="Forward Test")
        self.notebook.add(self.log_tab, text="Logs")
        self.notebook.pack(expand=1, fill="both")

    # --------------------
    # Backtest tab
    # --------------------
    def _build_backtest_tab(self):
        frame = self.bt_tab
        frame.columnconfigure(1, weight=1)
        row = 0

        ttk.Label(frame, text="Data File (.csv, .log):").grid(row=row, column=0, sticky="e")
        ttk.Entry(frame, textvariable=self.bt_data_file, width=55).grid(row=row, column=1, padx=5, pady=5)
        ttk.Button(frame, text="Browse", command=self._bt_browse_csv).grid(row=row, column=2, padx=5, pady=5)
        row += 1

        ttk.Button(frame, text="Run Backtest", command=self.run_backtest, style="Accent.TButton").grid(row=row, column=0, columnspan=3, pady=10)
        row += 1

        ttk.Label(frame, text="Strategy Configuration", font=('Arial', 12, 'bold')).grid(row=row, column=0, columnspan=3, sticky="w", pady=(15, 5))
        row += 1

        # Indicators frame (backtest uses same variables as forward)
        indicators_frame = ttk.Frame(frame)
        indicators_frame.grid(row=row, column=0, columnspan=3, sticky="w", padx=5, pady=2)
        ttk.Checkbutton(indicators_frame, text="EMA Crossover", variable=self.bt_use_ema_crossover).grid(row=0, column=0, sticky="w", padx=5)
        ttk.Checkbutton(indicators_frame, text="MACD", variable=self.bt_use_macd).grid(row=0, column=1, sticky="w", padx=5)
        ttk.Checkbutton(indicators_frame, text="VWAP", variable=self.bt_use_vwap).grid(row=0, column=2, sticky="w", padx=5)
        ttk.Checkbutton(indicators_frame, text="RSI Filter", variable=self.bt_use_rsi_filter).grid(row=0, column=3, sticky="w", padx=5)
        row += 1

        params_frame = ttk.Frame(frame)
        params_frame.grid(row=row, column=0, columnspan=3, sticky="w", padx=5, pady=2)
        ttk.Label(params_frame, text="Fast EMA:").grid(row=0, column=0, sticky="e", padx=2)
        ttk.Entry(params_frame, textvariable=self.bt_fast_ema, width=8).grid(row=0, column=1, padx=2)
        ttk.Label(params_frame, text="Slow EMA:").grid(row=0, column=2, sticky="e", padx=2)
        ttk.Entry(params_frame, textvariable=self.bt_slow_ema, width=8).grid(row=0, column=3, padx=2)
        row += 1

        # Simple placeholders for results
        self.bt_result_box = tk.Text(frame, height=10, width=110, state="disabled")
        self.bt_result_box.grid(row=row, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")
        frame.rowconfigure(row, weight=1)

    def _bt_browse_csv(self):
        path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv"), ("Log files", "*.log"), ("All files", "*.*")])
        if path:
            self.bt_data_file.set(path)

    # --------------------
    # Validation + run backtest
    # --------------------
    def _validate_all_inputs_on_submit(self):
        errors = []
        warnings = []
        try:
            fast_ema = int(self.bt_fast_ema.get())
            slow_ema = int(self.bt_slow_ema.get())
            if fast_ema <= 0 or slow_ema <= 0:
                errors.append("EMA periods must be positive")
            if fast_ema >= slow_ema:
                errors.append("Fast EMA must be less than Slow EMA")

            macd_fast = int(self.bt_macd_fast.get())
            macd_slow = int(self.bt_macd_slow.get())
            macd_signal = int(self.bt_macd_signal.get())
            if macd_fast <= 0 or macd_slow <= 0 or macd_signal <= 0:
                errors.append("MACD parameters must be positive")
            if macd_fast >= macd_slow:
                errors.append("MACD fast must be less than MACD slow")

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

            tp_points = [float(var.get()) for var in self.bt_tp_points]
            if any(tp <= 0 for tp in tp_points):
                errors.append("All take profit points must be positive")
            if any(tp <= sl_points for tp in tp_points):
                errors.append("Take profit points must be greater than stop loss")

            start_hour = int(self.bt_session_start_hour.get())
            start_min = int(self.bt_session_start_min.get())
            end_hour = int(self.bt_session_end_hour.get())
            end_min = int(self.bt_session_end_min.get())
            if not (0 <= start_hour <= 23 and 0 <= end_hour <= 23):
                errors.append("Hours must be between 0 and 23")
            if not (0 <= start_min <= 59 and 0 <= end_min <= 59):
                errors.append("Minutes must be between 0 and 59")
            if start_hour * 60 + start_min >= end_hour * 60 + end_min:
                errors.append("Session start must be before session end")

            lot_size = int(self.bt_lot_size.get())
            if lot_size <= 0:
                errors.append("Lot size must be positive")

        except ValueError as e:
            errors.append(f"Invalid numeric input: {e}")

        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}

    def run_backtest(self):
        """Validated backtest entry point"""
        validation = self._validate_all_inputs_on_submit()
        if not validation["valid"]:
            messagebox.showerror("Validation Failed", "Please fix:\n\n" + "\n".join(validation["errors"]))
            return
        if validation["warnings"]:
            if not messagebox.askyesno("Warnings", "Warnings:\n\n" + "\n".join(validation["warnings"]) + "\n\nContinue?"):
                return
        try:
            config = self.build_config_from_gui()
            logger.info("====== BACKTEST CONFIGURATION ======")
            for section, params in config.items():
                logger.info(f"{section}: {params}")
            backtest = BacktestRunner(config=config)
            results = backtest.run()
            self.display_backtest_results(results)
            self.save_user_preferences()
        except Exception as e:
            logger.exception(f"Backtest failed: {e}")
            messagebox.showerror("Backtest Error", f"Failed to run backtest: {e}")

    # Backwards compatibility wrapper
    def _bt_run_backtest(self):
        self.run_backtest()

    def display_backtest_results(self, results):
        try:
            self.bt_result_box.config(state="normal")
            self.bt_result_box.delete(1.0, tk.END)
            self.bt_result_box.insert(tk.END, "Backtest completed. Results summary below:\n")
            # minimal placeholder; real implementation should format results
            self.bt_result_box.insert(tk.END, str(results))
            self.bt_result_box.config(state="disabled")
        except Exception:
            logger.exception("Failed to display backtest results")

    # --------------------
    # Forward test tab & logic
    # --------------------
    def _build_forward_test_tab(self):
        frame = self.ft_tab
        frame.columnconfigure(1, weight=1)
        row = 0

        ttk.Label(frame, text="Symbol Management", font=('Arial', 12, 'bold')).grid(row=row, column=0, columnspan=3, sticky="w", pady=(10, 5))
        row += 1

        ttk.Label(frame, text="SmartAPI Authentication: Automatic (uses saved session)", font=('Arial', 9), foreground="blue").grid(row=row, column=0, columnspan=3, sticky="w", padx=5, pady=2)
        ttk.Label(frame, text="Note: If no session exists, system will run in paper trading mode", font=('Arial', 8), foreground="gray").grid(row=row+1, column=0, columnspan=3, sticky="w", padx=5, pady=2)
        row += 2

        ttk.Button(frame, text="Refresh Symbol Cache", command=self._ft_refresh_cache).grid(row=row, column=0, pady=3)
        ttk.Label(frame, textvariable=self.ft_cache_status).grid(row=row, column=1, columnspan=2, sticky="w", padx=5)
        row += 1

        ttk.Label(frame, text="Exchange:").grid(row=row, column=0, sticky="e", padx=5, pady=2)
        exchanges = ["NSE_FO", "NSE_CM", "BSE_CM"]
        ttk.Combobox(frame, textvariable=self.ft_exchange, values=exchanges, width=10, state='readonly').grid(row=row, column=1, sticky="w", padx=5, pady=2)
        row += 1

        symbol_frame = ttk.Frame(frame)
        symbol_frame.grid(row=row, column=0, columnspan=3, sticky="w", padx=5, pady=2)
        ttk.Label(symbol_frame, text="Symbol:").grid(row=0, column=0, sticky="e", padx=5, pady=2)
        self.ft_symbol_entry = ttk.Entry(symbol_frame, textvariable=self.ft_symbol, width=32)
        self.ft_symbol_entry.grid(row=0, column=1, sticky="w", padx=5, pady=2)
        ttk.Button(symbol_frame, text="Filter & Load Symbols", command=self._ft_load_symbols).grid(row=0, column=2, padx=5, pady=2)

        self.ft_symbols_listbox = tk.Listbox(symbol_frame, width=50, height=6)
        self.ft_symbols_listbox.grid(row=1, column=0, columnspan=3, sticky="w", padx=5, pady=2)
        self.ft_symbols_listbox.bind("<<ListboxSelect>>", self._ft_update_symbol_details)
        listbox_scrollbar = ttk.Scrollbar(symbol_frame, orient="vertical", command=self.ft_symbols_listbox.yview)
        listbox_scrollbar.grid(row=1, column=3, sticky="ns")
        self.ft_symbols_listbox.configure(yscrollcommand=listbox_scrollbar.set)
        row += 2

        ttk.Label(frame, text="Token:").grid(row=row, column=0, sticky="e", padx=5, pady=2)
        ttk.Entry(frame, textvariable=self.ft_token, width=20, state="readonly").grid(row=row, column=1, sticky="w", padx=5, pady=2)
        row += 1

        ttk.Label(frame, text="Feed Type:").grid(row=row, column=0, sticky="e", padx=5, pady=2)
        feed_types = ["LTP", "Quote", "SnapQuote"]
        ttk.Combobox(frame, textvariable=self.ft_feed_type, values=feed_types, width=12, state='readonly').grid(row=row, column=1, sticky="w", padx=5, pady=2)
        row += 1

        ttk.Label(frame, text="Strategy Configuration", font=('Arial', 12, 'bold')).grid(row=row, column=0, columnspan=3, sticky="w", pady=(15, 5))
        row += 1

        indicators_frame = ttk.Frame(frame)
        indicators_frame.grid(row=row, column=0, columnspan=3, sticky="w", padx=5, pady=2)
        ttk.Checkbutton(indicators_frame, text="EMA Crossover", variable=self.ft_use_ema_crossover).grid(row=0, column=0, sticky="w", padx=5)
        ttk.Checkbutton(indicators_frame, text="MACD", variable=self.ft_use_macd).grid(row=0, column=1, sticky="w", padx=5)
        ttk.Checkbutton(indicators_frame, text="VWAP", variable=self.ft_use_vwap).grid(row=0, column=2, sticky="w", padx=5)
        ttk.Checkbutton(indicators_frame, text="RSI Filter", variable=self.ft_use_rsi_filter).grid(row=0, column=3, sticky="w", padx=5)
        row += 1

        params_frame = ttk.Frame(frame)
        params_frame.grid(row=row, column=0, columnspan=3, sticky="w", padx=5, pady=2)
        ttk.Label(params_frame, text="Fast EMA:").grid(row=0, column=0, sticky="e", padx=2)
        ttk.Entry(params_frame, textvariable=self.ft_fast_ema, width=8).grid(row=0, column=1, padx=2)
        ttk.Label(params_frame, text="Slow EMA:").grid(row=0, column=2, sticky="e", padx=2)
        ttk.Entry(params_frame, textvariable=self.ft_slow_ema, width=8).grid(row=0, column=3, padx=2)

        ttk.Label(params_frame, text="MACD Fast:").grid(row=1, column=0, sticky="e", padx=2)
        ttk.Entry(params_frame, textvariable=self.ft_macd_fast, width=8).grid(row=1, column=1, padx=2)
        ttk.Label(params_frame, text="MACD Slow:").grid(row=1, column=2, sticky="e", padx=2)
        ttk.Entry(params_frame, textvariable=self.ft_macd_slow, width=8).grid(row=1, column=3, padx=2)
        ttk.Label(params_frame, text="MACD Signal:").grid(row=1, column=4, sticky="e", padx=2)
        ttk.Entry(params_frame, textvariable=self.ft_macd_signal, width=8).grid(row=1, column=5, padx=2)

        ttk.Label(params_frame, text="RSI Length:").grid(row=2, column=0, sticky="e", padx=2)
        ttk.Entry(params_frame, textvariable=self.ft_rsi_length, width=8).grid(row=2, column=1, padx=2)
        ttk.Label(params_frame, text="RSI Oversold:").grid(row=2, column=2, sticky="e", padx=2)
        ttk.Entry(params_frame, textvariable=self.ft_rsi_oversold, width=8).grid(row=2, column=3, padx=2)
        ttk.Label(params_frame, text="RSI Overbought:").grid(row=2, column=4, sticky="e", padx=2)
        ttk.Entry(params_frame, textvariable=self.ft_rsi_overbought, width=8).grid(row=2, column=5, padx=2)

        ttk.Label(params_frame, text="HTF Period:").grid(row=3, column=0, sticky="e", padx=2)
        ttk.Entry(params_frame, textvariable=self.ft_htf_period, width=8).grid(row=3, column=1, padx=2)
        ttk.Label(params_frame, text="Green Bars Req:").grid(row=3, column=2, sticky="e", padx=2)
        ttk.Entry(params_frame, textvariable=self.bt_consecutive_green_bars, width=8).grid(row=3, column=3, padx=2)
        row += 1

        # Risk frame
        risk_frame = ttk.Frame(frame)
        risk_frame.grid(row=row, column=0, columnspan=3, sticky="w", padx=5, pady=2)
        ttk.Label(risk_frame, text="Stop Loss Points:").grid(row=0, column=0, sticky="e", padx=2)
        ttk.Entry(risk_frame, textvariable=self.ft_base_sl_points, width=8).grid(row=0, column=1, padx=2)

        ttk.Label(risk_frame, text="TP1 Points:").grid(row=0, column=2, sticky="e", padx=2)
        ttk.Entry(risk_frame, textvariable=self.ft_tp_points[0], width=8).grid(row=0, column=3, padx=2)
        ttk.Label(risk_frame, text="TP2 Points:").grid(row=0, column=4, sticky="e", padx=2)
        ttk.Entry(risk_frame, textvariable=self.ft_tp_points[1], width=8).grid(row=0, column=5, padx=2)
        ttk.Label(risk_frame, text="TP3 Points:").grid(row=1, column=0, sticky="e", padx=2)
        ttk.Entry(risk_frame, textvariable=self.ft_tp_points[2], width=8).grid(row=1, column=1, padx=2)
        ttk.Label(risk_frame, text="TP4 Points:").grid(row=1, column=2, sticky="e", padx=2)
        ttk.Entry(risk_frame, textvariable=self.ft_tp_points[3], width=8).grid(row=1, column=3, padx=2)

        ttk.Checkbutton(risk_frame, text="Use Trailing Stop", variable=self.ft_use_trail_stop).grid(row=1, column=4, columnspan=2, sticky="w", padx=5)
        ttk.Label(risk_frame, text="Trail Activation Points:").grid(row=2, column=0, sticky="e", padx=2)
        ttk.Entry(risk_frame, textvariable=self.ft_trail_activation_points, width=8).grid(row=2, column=1, padx=2)
        ttk.Label(risk_frame, text="Trail Distance Points:").grid(row=2, column=2, sticky="e", padx=2)
        ttk.Entry(risk_frame, textvariable=self.ft_trail_distance_points, width=8).grid(row=2, column=3, padx=2)
        ttk.Label(risk_frame, text="Risk % per Trade:").grid(row=2, column=4, sticky="e", padx=2)
        ttk.Entry(risk_frame, textvariable=self.ft_risk_per_trade_percent, width=8).grid(row=2, column=5, padx=2)
        row += 1

        # Instrument and capital
        ttk.Label(frame, text="Instrument Settings:", font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky="w", padx=5, pady=(10, 2))
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

        ttk.Label(frame, text="Capital Settings:", font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky="w", padx=5, pady=(10, 2))
        row += 1
        capital_frame = ttk.Frame(frame)
        capital_frame.grid(row=row, column=0, columnspan=3, sticky="w", padx=5, pady=2)
        ttk.Label(capital_frame, text="Initial Capital:").grid(row=0, column=0, sticky="e", padx=2)
        ttk.Entry(capital_frame, textvariable=self.ft_initial_capital, width=14).grid(row=0, column=1, padx=2)
        row += 1

        ttk.Label(frame, text="Session Settings:", font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky="w", padx=5, pady=(10, 2))
        row += 1
        session_frame = ttk.Frame(frame)
        session_frame.grid(row=row, column=0, columnspan=3, sticky="w", padx=5, pady=2)
        ttk.Label(session_frame, text="Start (HH:MM):").grid(row=0, column=0, sticky="e", padx=2)
        ttk.Entry(session_frame, textvariable=self.ft_session_start_hour, width=4).grid(row=0, column=1, padx=1)
        ttk.Label(session_frame, text=":").grid(row=0, column=2)
        ttk.Entry(session_frame, textvariable=self.ft_session_start_min, width=4).grid(row=0, column=3, padx=1)
        ttk.Label(session_frame, text="End (HH:MM):").grid(row=0, column=4, sticky="e", padx=2)
        ttk.Entry(session_frame, textvariable=self.ft_session_end_hour, width=4).grid(row=0, column=5, padx=1)
        ttk.Label(session_frame, text=":").grid(row=0, column=6)
        ttk.Entry(session_frame, textvariable=self.ft_session_end_min, width=4).grid(row=0, column=7, padx=1)
        ttk.Label(session_frame, text="Intraday:").grid(row=1, column=0, sticky="e", padx=2)
        ttk.Checkbutton(session_frame, variable=self.bt_is_intraday).grid(row=1, column=1, sticky="w", padx=2)
        row += 1

        ttk.Button(frame, text="Start Forward Test", command=self._ft_run_forward_test).grid(row=row, column=0, pady=5)
        ttk.Button(frame, text="Stop", command=self._ft_stop_forward_test).grid(row=row, column=1, pady=5)
        row += 1

        self.ft_result_box = tk.Text(frame, height=16, width=110, state="disabled")
        self.ft_result_box.grid(row=row, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")
        frame.rowconfigure(row, weight=1)

    def _ft_refresh_cache(self):
        """Trigger background refresh safely"""
        try:
            # start background thread so UI doesn't block
            t = threading.Thread(target=self._refresh_symbols_thread, daemon=True)
            t.start()
            messagebox.showinfo("Refresh", "Symbol refresh started in background.")
        except Exception:
            logger.exception("Failed to start symbol refresh thread")
            messagebox.showerror("Error", "Failed to start symbol refresh")

    def _refresh_symbols_thread(self):
        """Background thread to refresh symbol cache and update UI"""
        try:
            def run_once(func):
                has_run = {'value': False}
                def wrapper(*args, **kwargs):
                    if not has_run['value']:
                        has_run['value'] = True
                        return func(*args, **kwargs)
                return wrapper

            symbols = refresh_symbol_cache(force_refresh=True, progress_callback=run_once(self._update_refresh_status))
            if symbols:
                self._update_symbol_listbox(symbols)
                logger.info(f"Symbol cache refreshed: {len(symbols)} symbols loaded")
            else:
                logger.warning("Symbol cache refresh completed with no symbols")
        except Exception:
            logger.exception("Error refreshing symbol cache")

    def _update_refresh_status(self, count):
        if hasattr(self, 'ft_cache_status'):
            try:
                self.ft_cache_status.set(f"Cache refreshed: {count} symbols loaded.")
            except Exception:
                pass

    def _update_symbol_listbox(self, symbols):
        if hasattr(self, 'ft_symbols_listbox'):
            try:
                self.ft_symbols_listbox.delete(0, tk.END)
                for s in symbols:
                    self.ft_symbols_listbox.insert(tk.END, s)
                logger.info(f"Symbol listbox updated with {len(symbols)} symbols")
            except Exception:
                logger.exception("Failed to update symbol listbox")

    def _ft_load_symbols(self):
        """Load symbols from cache based on filter with validations"""
        try:
            filter_text = self.ft_symbol.get().strip()
            exchange = self.ft_exchange.get()
            if exchange not in ["NSE_FO", "NSE_CM", "BSE_CM"]:
                messagebox.showerror("Invalid Exchange", "Please select a valid exchange")
                return
            all_symbols = load_symbol_cache()
            if all_symbols is None:
                messagebox.showerror("Cache Error", "Symbol cache is empty or not found")
                return
            filtered = [s for s in all_symbols if s.startswith(exchange) and filter_text in s]
            self.ft_symbols_listbox.delete(0, tk.END)
            for s in filtered:
                self.ft_symbols_listbox.insert(tk.END, s)
            self.ft_cache_status.set(f"Loaded {len(filtered)} symbols")
            logger.info(f"Loaded {len(filtered)} symbols for {exchange} with filter '{filter_text}'")
        except Exception:
            logger.exception("Error loading symbols")
            messagebox.showerror("Load Symbols Error", "Failed to load symbols")

    def _ft_update_symbol_details(self, event):
        try:
            sel = self.ft_symbols_listbox.curselection()
            if not sel:
                return
            sym = self.ft_symbols_listbox.get(sel[0])
            token = self.symbol_token_map.get(sym, "")
            self.ft_token.set(token)
        except Exception:
            logger.exception("Error updating symbol details")

    def _ft_run_forward_test(self):
        try:
            selected = [self.ft_symbols_listbox.get(i) for i in self.ft_symbols_listbox.curselection()]
            if not selected:
                messagebox.showerror("No Symbol Selected", "Please select at least one symbol to test")
                return
            if not messagebox.askyesno("Confirm Forward Test", "Start forward test with selected symbols?"):
                return
            self._set_forward_test_controls_state(tk.DISABLED)

            # Use full listbox contents as the authoritative list if you prefer
            symbols_to_test = [self.ft_symbols_listbox.get(i) for i in range(self.ft_symbols_listbox.size())]
            logger.info(f"Starting forward test for symbols: {symbols_to_test}")

            self._forward_thread = threading.Thread(target=self._run_forward_test_process, args=(symbols_to_test,), daemon=True)
            self._forward_thread.start()
            messagebox.showinfo("Forward Test Started", "Forward test started in background.")
        except Exception:
            logger.exception("Error starting forward test")
            messagebox.showerror("Forward Test Error", "Failed to start forward test")

    def _run_forward_test_process(self, symbols):
        try:
            for symbol in symbols:
                if not symbol.strip():
                    continue
                logger.info(f"Processing forward test symbol: {symbol}")
                # Replace below with actual forward test/integration
                time.sleep(0.5)
            logger.info("Forward test process completed")
        except Exception:
            logger.exception("Error during forward test")
        finally:
            self._set_forward_test_controls_state(tk.NORMAL)

    def _set_forward_test_controls_state(self, state):
        widgets = [
            getattr(self, 'ft_symbol_entry', None), getattr(self, 'ft_symbols_listbox', None), getattr(self, 'ft_exchange', None),
            getattr(self, 'ft_token', None), getattr(self, 'ft_feed_type', None), getattr(self, 'ft_fast_ema', None), getattr(self, 'ft_slow_ema', None),
            getattr(self, 'ft_macd_fast', None), getattr(self, 'ft_macd_slow', None), getattr(self, 'ft_macd_signal', None), getattr(self, 'ft_rsi_length', None),
            getattr(self, 'ft_rsi_oversold', None), getattr(self, 'ft_rsi_overbought', None), getattr(self, 'ft_htf_period', None),
            getattr(self, 'ft_base_sl_points', None), (getattr(self, 'ft_tp_points', None) or [None, None, None, None])[0],
            (getattr(self, 'ft_tp_points', None) or [None, None, None, None])[1], (getattr(self, 'ft_tp_points', None) or [None, None, None, None])[2],
            (getattr(self, 'ft_tp_points', None) or [None, None, None, None])[3], getattr(self, 'ft_use_trail_stop', None),
            getattr(self, 'ft_trail_activation_points', None), getattr(self, 'ft_trail_distance_points', None), getattr(self, 'ft_risk_per_trade_percent', None),
            getattr(self, 'ft_initial_capital', None), getattr(self, 'ft_session_start_hour', None), getattr(self, 'ft_session_start_min', None),
            getattr(self, 'ft_session_end_hour', None), getattr(self, 'ft_session_end_min', None)
        ]
        for w in widgets:
            if w is None:
                continue
            try:
                # If widget is a tkinter Widget
                w.configure(state=state)
            except Exception:
                # Might be a tk.Variable; skip
                pass

    def _ft_stop_forward_test(self):
        try:
            if self._forward_thread and self._forward_thread.is_alive():
                # no safe stop implemented; join with timeout
                self._forward_thread.join(timeout=5)
                logger.info("Forward test thread stopped/joined")
            else:
                logger.warning("No active forward test thread")
        except Exception:
            logger.exception("Error stopping forward test")

    # --------------------
    # Log tab
    # --------------------
    def _build_log_tab(self):
        frame = self.log_tab
        frame.columnconfigure(0, weight=1)
        row = 0

        ttk.Label(frame, text="Log File:").grid(row=row, column=0, sticky="e")
        ttk.Entry(frame, textvariable=self.log_file_var, width=55).grid(row=row, column=1, padx=5, pady=5)
        ttk.Button(frame, text="Open Log", command=self._open_log_file).grid(row=row, column=2, padx=5, pady=5)
        row += 1

        ttk.Label(frame, text="Log Level:").grid(row=row, column=0, sticky="e")
        ttk.Combobox(frame, textvariable=self.log_level_var, values=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], width=10, state='readonly').grid(row=row, column=1, sticky="w", padx=5, pady=5)
        row += 1

        self.log_text = tk.Text(frame, height=20, state="disabled", wrap="word")
        self.log_text.grid(row=row, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")
        frame.rowconfigure(row, weight=1)
        self._load_log_file()

    def _open_log_file(self):
        log_file = self.log_file_var.get()
        if os.path.exists(log_file):
            try:
                os.startfile(log_file)
                logger.info(f"Opened log file: {log_file}")
            except Exception:
                logger.exception("Failed to open log file")
                messagebox.showerror("Open Log", "Failed to open log file")
        else:
            messagebox.showerror("File Not Found", f"Log file not found: {log_file}")

    def _load_log_file(self):
        try:
            log_file = self.log_file_var.get()
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    content = f.read()
                self.log_text.config(state="normal")
                self.log_text.delete(1.0, tk.END)
                self.log_text.insert(tk.END, content)
                self.log_text.config(state="disabled")
                logger.info(f"Loaded log file: {log_file}")
            else:
                logger.info(f"Log file not found: {log_file}")
        except Exception:
            logger.exception("Failed to load log file")

    # --------------------
    # Build config from GUI and save prefs
    # --------------------
    def build_config_from_gui(self):
        config = create_config_from_defaults()

        config['strategy']['use_ema_crossover'] = bool(self.bt_use_ema_crossover.get())
        config['strategy']['use_macd'] = bool(self.bt_use_macd.get())
        config['strategy']['use_vwap'] = bool(self.bt_use_vwap.get())
        config['strategy']['use_rsi_filter'] = bool(self.bt_use_rsi_filter.get())
        config['strategy']['use_htf_trend'] = bool(self.bt_use_htf_trend.get())
        config['strategy']['use_bollinger_bands'] = bool(self.bt_use_bollinger_bands.get())
        config['strategy']['use_stochastic'] = bool(self.bt_use_stochastic.get())
        config['strategy']['use_atr'] = bool(self.bt_use_atr.get())

        config['strategy']['fast_ema'] = int(self.bt_fast_ema.get())
        config['strategy']['slow_ema'] = int(self.bt_slow_ema.get())
        config['strategy']['macd_fast'] = int(self.bt_macd_fast.get())
        config['strategy']['macd_slow'] = int(self.bt_macd_slow.get())
        config['strategy']['macd_signal'] = int(self.bt_macd_signal.get())
        config['strategy']['consecutive_green_bars'] = int(self.bt_consecutive_green_bars.get())
        config['strategy']['strategy_version'] = DEFAULT_CONFIG['strategy'].get('strategy_version', 1)

        config['risk']['base_sl_points'] = float(self.bt_base_sl_points.get())
        config['risk']['use_trail_stop'] = bool(self.bt_use_trail_stop.get())
        config['risk']['trail_activation_points'] = float(self.bt_trail_activation.get())
        config['risk']['trail_distance_points'] = float(self.bt_trail_distance.get())
        config['risk']['tp_points'] = [float(var.get()) for var in self.bt_tp_points]
        config['risk']['tp_percents'] = [float(var.get()) / 100.0 for var in self.bt_tp_percents]

        config['capital']['initial_capital'] = float(self.bt_initial_capital.get())

        config['instrument']['symbol'] = self.bt_symbol.get()
        config['instrument']['exchange'] = self.bt_exchange.get()
        config['instrument']['lot_size'] = int(self.bt_lot_size.get())

        config['session']['is_intraday'] = bool(self.bt_is_intraday.get())
        config['session']['start_hour'] = int(self.bt_session_start_hour.get())
        config['session']['start_min'] = int(self.bt_session_start_min.get())
        config['session']['end_hour'] = int(self.bt_session_end_hour.get())
        config['session']['end_min'] = int(self.bt_session_end_min.get())

        config['backtest']['data_path'] = self.bt_data_file.get()
        config['logging'] = DEFAULT_CONFIG.get('logging', {}).copy()
        return config

    def save_user_preferences(self):
        try:
            prefs = self.build_config_from_gui()
            diff = self._get_config_diff(prefs, DEFAULT_CONFIG)
            with open("user_preferences.json", "w") as f:
                json.dump(diff, f, indent=2)
            logger.info("User preferences saved")
        except Exception:
            logger.exception("Failed to save user preferences")

    def _get_config_diff(self, current, defaults):
        diff = {}
        for section, params in current.items():
            if not isinstance(params, dict):
                continue
            for k, v in params.items():
                default_v = defaults.get(section, {}).get(k)
                if v != default_v:
                    diff.setdefault(section, {})[k] = v
        return diff

# --------------------
# Entrypoint
# --------------------
def main():
    try:
        app = UnifiedTradingGUI()
        app.mainloop()
    except Exception as e:
        print(f"Failed to start GUI application: {e}")


if __name__ == "__main__":
    main()
# ...existing code...