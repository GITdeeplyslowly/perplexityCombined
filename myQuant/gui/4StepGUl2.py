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
import copy
import threading
import os
import json
from datetime import datetime
import logging
import numpy as np
import pytz
from utils.cache_manager import refresh_symbol_cache, load_symbol_cache
from live.trader import LiveTrader

# Add import for defaults and strict config helpers
from config.defaults import DEFAULT_CONFIG
from utils.config_helper import (
    create_config_from_defaults,
    get_logging_verbosity_options,
    validate_config,
    freeze_config
)
from utils.logger_setup import setup_logger, setup_logging_from_config
from backtest.backtest_runner import BacktestRunner
from types import MappingProxyType

LOG_FILENAME = "unified_gui.log"
logger = setup_logger(log_file=LOG_FILENAME, log_level=logging.INFO)

def now_ist():
    """Return current time in India Standard Time"""
    return datetime.now(pytz.timezone('Asia/Kolkata'))

class UnifiedTradingGUI(tk.Tk):
    def __init__(self, master=None):
        super().__init__(master)

        self.title("Unified Trading System")
        self.geometry("1200x800")
        self.minsize(1000, 700)

        # === SINGLE POINT OF CONFIGURATION (SIMPLIFIED 4-STAGE FLOW) ===
        # Stage 1: Immutable defaults (read-only reference)
        self.default_config = MappingProxyType(copy.deepcopy(DEFAULT_CONFIG))
        # Stage 2: Mutable working config (user-updated during GUI usage)
        self.user_updated_config = copy.deepcopy(DEFAULT_CONFIG)

        # 3. Initialize all GUI variables (tk.Variable instances)
        self._initialize_all_variables()

        # 4. Initialize GUI variables from working config (single source for widget defaults)
        self._initialize_variables_from_config(self.user_updated_config)

        # 5. Configure logging according to runtime config (best-effort)
        try:
            setup_logging_from_config(self.user_updated_config)
        except Exception:
            logger.exception("setup_logging_from_config failed; using fallback logger")

        # 6. Create GUI components and tabs
        self._create_gui_framework()
        self._build_backtest_tab()
        self._build_forward_test_tab()
        self._build_log_tab()

        logger.info("GUI initialized successfully with runtime config")

    def _initialize_all_variables(self):
        """Initialize ALL GUI variables (tk.Variable instances) - called BEFORE loading from config"""
        # Thread handles
        self._backtest_thread = None
        self._forward_thread = None

        # Strategy variables
        self.bt_use_ema_crossover = tk.BooleanVar()
        self.bt_use_macd = tk.BooleanVar()
        self.bt_use_vwap = tk.BooleanVar()
        self.bt_use_rsi_filter = tk.BooleanVar()
        self.bt_use_htf_trend = tk.BooleanVar()
        self.bt_use_bollinger_bands = tk.BooleanVar()
        self.bt_use_stochastic = tk.BooleanVar()
        self.bt_use_atr = tk.BooleanVar()
        
        # EMA parameters
        self.bt_fast_ema = tk.StringVar()
        self.bt_slow_ema = tk.StringVar()
        
        # MACD parameters
        self.bt_macd_fast = tk.StringVar()
        self.bt_macd_slow = tk.StringVar()
        self.bt_macd_signal = tk.StringVar()
        
        # RSI parameters
        self.bt_rsi_length = tk.StringVar()
        self.bt_rsi_oversold = tk.StringVar()
        self.bt_rsi_overbought = tk.StringVar()
        
        # HTF parameter
        self.bt_htf_period = tk.StringVar()
        
        # ATR length (missing from original code)
        self.bt_atr_len = tk.StringVar()
        
        # Consecutive Green Bars
        self.bt_consecutive_green_bars = tk.StringVar()
        
        # Risk management
        self.bt_base_sl_points = tk.StringVar()
        self.bt_tp_points = [tk.StringVar() for _ in range(4)]  # 4 take profit levels
        self.bt_tp_percents = [tk.StringVar() for _ in range(4)]  # 4 percentages
        self.bt_use_trail_stop = tk.BooleanVar()
        self.bt_trail_activation = tk.StringVar()
        self.bt_trail_distance = tk.StringVar()
        self.bt_risk_per_trade_percent = tk.StringVar()
        self.bt_risk_percentage = tk.StringVar()  # Alias for bt_risk_per_trade_percent
        
        # Capital settings
        self.bt_initial_capital = tk.StringVar()
        self.bt_available_capital = tk.StringVar(value="100000.0")
        self.bt_current_price = tk.StringVar(value="1000.0")
        
        # Instrument settings
        self.bt_symbol = tk.StringVar()
        self.bt_exchange = tk.StringVar()
        self.bt_lot_size = tk.StringVar()
        
        # Session settings
        self.bt_is_intraday = tk.BooleanVar()
        self.bt_session_start_hour = tk.StringVar()
        self.bt_session_start_min = tk.StringVar()
        self.bt_session_end_hour = tk.StringVar()
        self.bt_session_end_min = tk.StringVar()
        
        # Forward test variables (matching backtest variables)
        self.ft_use_ema_crossover = tk.BooleanVar()
        self.ft_use_macd = tk.BooleanVar()
        self.ft_use_vwap = tk.BooleanVar()
        self.ft_use_rsi_filter = tk.BooleanVar()
        self.ft_use_htf_trend = tk.BooleanVar()
        self.ft_use_bollinger_bands = tk.BooleanVar()
        self.ft_use_stochastic = tk.BooleanVar()
        self.ft_use_atr = tk.BooleanVar()
        
        # Forward test parameters
        self.ft_fast_ema = tk.StringVar()
        self.ft_slow_ema = tk.StringVar()
        self.ft_macd_fast = tk.StringVar()
        self.ft_macd_slow = tk.StringVar()
        self.ft_macd_signal = tk.StringVar()
        self.ft_rsi_length = tk.StringVar()
        self.ft_rsi_oversold = tk.StringVar()
        self.ft_rsi_overbought = tk.StringVar()
        self.ft_htf_period = tk.StringVar()
        self.ft_atr_len = tk.StringVar()
        
        # Forward test risk management
        self.ft_base_sl_points = tk.StringVar()
        self.ft_use_trail_stop = tk.BooleanVar()
        self.ft_trail_activation_points = tk.StringVar()
        self.ft_trail_distance_points = tk.StringVar()
        self.ft_risk_per_trade_percent = tk.StringVar()
        
        # Forward test TPs (will be mapped to bt_tp_points in _build_forward_test_tab)
        self.ft_tp1_points = tk.StringVar(value="10.0")
        self.ft_tp2_points = tk.StringVar(value="25.0")
        self.ft_tp3_points = tk.StringVar(value="50.0")
        self.ft_tp4_points = tk.StringVar(value="100.0")
        
        # Forward test session variables
        self.ft_session_start_hour = tk.StringVar()
        self.ft_session_start_min = tk.StringVar()
        self.ft_session_end_hour = tk.StringVar()
        self.ft_session_end_min = tk.StringVar()
        self.ft_start_buffer = tk.StringVar(value="5")
        self.ft_end_buffer = tk.StringVar(value="20")
        self.ft_timezone = tk.StringVar(value="Asia/Kolkata")
        
        # Forward test exchange/symbol settings
        self.ft_exchange = tk.StringVar()
        self.ft_feed_type = tk.StringVar(value="LTP")
        self.ft_symbol = tk.StringVar()
        self.ft_token = tk.StringVar()
        self.ft_initial_capital = tk.StringVar()
        self.ft_cache_status = tk.StringVar(value="Cache not loaded")
        
        # File selection and display variables
        self.bt_data_file = tk.StringVar()
        self.recommended_lots = tk.StringVar()
        self.max_lots = tk.StringVar()
        self.position_value = tk.StringVar()
        
        # GUI components
        self.notebook = None
        self.bt_tab = None
        self.ft_tab = None
        self.log_tab = None
        self.session_frame = None

    def _initialize_variables_from_config(self, config):
        """Initialize all GUI variables from a provided config (single source for widgets)"""
        # sections from provided config
        strategy_defaults = config.get('strategy', {})
        risk_defaults = config.get('risk', {})
        capital_defaults = config.get('capital', {})
        instrument_defaults = config.get('instrument', {})
        session_defaults = config.get('session', {})

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

    def build_config_from_gui(self, mode: str = 'backtest'):
        """Build config from GUI, validate, and freeze. Returns MappingProxyType or None."""
        try:
            config = copy.deepcopy(DEFAULT_CONFIG)
            if mode == 'forward_test':
                # Forward-test assignments (grouped by section)
                strategy_vars = {
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
                    'rsi_oversold': float(self.ft_rsi_oversold.get()),
                    'rsi_overbought': float(self.ft_rsi_overbought.get()),
                    'htf_period': int(self.ft_htf_period.get()),
                    'consecutive_green_bars': int(self.bt_consecutive_green_bars.get()),
                    'atr_len': int(self.ft_atr_len.get() or 14),
                    'indicator_update_mode': 'tick',
                    'strategy_version': 1
                }
                risk_vars = {
                    'max_positions_per_day': 25,
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
                    'commission_per_trade': 0.0,
                    'tick_size': 0.05,
                    'max_position_value_percent': 100.0,
                    'stt_percent': 0.025,
                    'exchange_charges_percent': 0.003,
                    'gst_percent': 18.0,
                    'slippage_points': 0.0
                }
                capital_vars = {'initial_capital': float(self.ft_initial_capital.get() or self.bt_initial_capital.get())}
                instrument_vars = {
                    'symbol': self.ft_symbol.get() or self.bt_symbol.get(),
                    'exchange': self.ft_exchange.get() or self.bt_exchange.get(),
                    'lot_size': int(self.bt_lot_size.get()),
                    'tick_size': 0.05,
                    'product_type': 'INTRADAY'
                }
                session_vars = {
                    'is_intraday': True,
                    'start_hour': int(self.ft_session_start_hour.get() or self.bt_session_start_hour.get()),
                    'start_min': int(self.ft_session_start_min.get() or self.bt_session_start_min.get()),
                    'end_hour': int(self.ft_session_end_hour.get() or self.bt_session_end_hour.get()),
                    'end_min': int(self.ft_session_end_min.get() or self.bt_session_end_min.get()),
                    'start_buffer_minutes': int(self.ft_start_buffer.get() or 5),
                    'end_buffer_minutes': int(self.ft_end_buffer.get() or 20),
                    'no_trade_start_minutes': 5,
                    'no_trade_end_minutes': 10,
                    'timezone': self.ft_timezone.get() or 'Asia/Kolkata'
                }
                live_vars = {
                    'paper_trading': True,
                    'exchange_type': self.ft_exchange.get() or 'NSE_FO',
                    'feed_type': self.ft_feed_type.get() or 'LTP',
                    'log_ticks': False,
                    'visual_indicator': True
                }
                config['strategy'].update(strategy_vars)
                config['risk'].update(risk_vars)
                config['capital'].update(capital_vars)
                config['instrument'].update(instrument_vars)
                config['session'].update(session_vars)
                config['live'].update(live_vars)
            else:
                # Backtest assignments (grouped by section)
                strategy_vars = {
                    'use_ema_crossover': self.bt_use_ema_crossover.get(),
                    'use_macd': self.bt_use_macd.get(),
                    'use_vwap': self.bt_use_vwap.get(),
                    'use_rsi_filter': self.bt_use_rsi_filter.get(),
                    'use_htf_trend': self.bt_use_htf_trend.get(),
                    'use_bollinger_bands': self.bt_use_bollinger_bands.get(),
                    'use_stochastic': self.bt_use_stochastic.get(),
                    'use_atr': self.bt_use_atr.get(),
                    'fast_ema': int(self.bt_fast_ema.get()),
                    'slow_ema': int(self.bt_slow_ema.get()),
                    'macd_fast': int(self.bt_macd_fast.get()),
                    'macd_slow': int(self.bt_macd_slow.get()),
                    'macd_signal': int(self.bt_macd_signal.get()),
                    'rsi_length': int(self.bt_rsi_length.get()),
                    'rsi_oversold': float(self.bt_rsi_oversold.get()),
                    'rsi_overbought': float(self.bt_rsi_overbought.get()),
                    'htf_period': int(self.bt_htf_period.get()),
                    'consecutive_green_bars': int(self.bt_consecutive_green_bars.get()),
                    'atr_len': int(self.bt_atr_len.get() or 14),
                    'indicator_update_mode': 'tick',
                    'strategy_version': 1
                }
                risk_vars = {
                    'max_positions_per_day': 25,
                    'base_sl_points': float(self.bt_base_sl_points.get()),
                    'tp_points': [float(v.get()) for v in self.bt_tp_points],
                    'tp_percents': [float(v.get())/100.0 for v in self.bt_tp_percents],
                    'use_trail_stop': self.bt_use_trail_stop.get(),
                    'trail_activation_points': float(self.bt_trail_activation.get()),
                    'trail_distance_points': float(self.bt_trail_distance.get()),
                    'risk_per_trade_percent': float(self.bt_risk_per_trade_percent.get()),
                    'commission_percent': 0.03,
                    'commission_per_trade': 0.0,
                    'tick_size': 0.05,
                    'max_position_value_percent': 100.0,
                    'stt_percent': 0.025,
                    'exchange_charges_percent': 0.003,
                    'gst_percent': 18.0,
                    'slippage_points': 0.0
                }
                capital_vars = {'initial_capital': float(self.bt_initial_capital.get())}
                instrument_vars = {
                    'symbol': self.bt_symbol.get(),
                    'exchange': self.bt_exchange.get(),
                    'lot_size': int(self.bt_lot_size.get()),
                    'tick_size': 0.05,
                    'product_type': 'INTRADAY'
                }
                session_vars = {
                    'is_intraday': self.bt_is_intraday.get(),
                    'start_hour': int(self.bt_session_start_hour.get()),
                    'start_min': int(self.bt_session_start_min.get()),
                    'end_hour': int(self.bt_session_end_hour.get()),
                    'end_min': int(self.bt_session_end_min.get()),
                    'start_buffer_minutes': 5,
                    'end_buffer_minutes': 20,
                    'no_trade_start_minutes': 5,
                    'no_trade_end_minutes': 10,
                    'timezone': 'Asia/Kolkata'
                }
                backtest_vars = {
                    'allow_short': False,
                    'close_at_session_end': True,
                    'save_results': True,
                    'results_dir': 'results',
                    'log_level': 'INFO',
                    'data_path': self.bt_data_file.get()
                }
                config['strategy'].update(strategy_vars)
                config['risk'].update(risk_vars)
                config['capital'].update(capital_vars)
                config['instrument'].update(instrument_vars)
                config['session'].update(session_vars)
                config['backtest'].update(backtest_vars)
            # Validate and freeze
            validation = validate_config(config)
            if isinstance(validation, dict) and not validation.get('valid', True):
                errors = validation.get('errors', [])
                messagebox.showerror("Configuration Error", "Invalid configuration:\n" + "\n".join(errors))
                return None
            return freeze_config(config)
        except Exception as e:
            logger.exception("build_config_from_gui failed: %s", e)
            messagebox.showerror("Configuration Error", f"Failed to build configuration: {e}")
            return None

    def run_backtest(self):
        """Run backtest with GUI configuration"""
        try:
            # Get validated and frozen config from GUI (returns None on validation failure)
            config = self.build_config_from_gui(mode='backtest')
            if config is None:
                return

            # Log the actual configuration used
            logger.info("====== BACKTEST CONFIGURATION ======")
            logger.info("Using TRUE INCREMENTAL PROCESSING (row-by-row)")
            logger.info("Batch processing completely eliminated")
            for section, params in config.items():
                if isinstance(params, dict):
                    logger.info(f"Section '{section}': {len(params)} parameters")
                
            # Create and run backtest with GUI config
            backtest = BacktestRunner(config=config)
            results = backtest.run()

            # Display results
            self.display_backtest_results(results)

        except Exception as e:
            logger.exception(f"Backtest failed: {e}")
            messagebox.showerror("Backtest Error", f"Failed to run backtest: {e}")

    def _bt_browse_csv(self):
        """Browse for a data file and set the path for backtest."""
        path = filedialog.askopenfilename(
            title="Select Data File",
            filetypes=[
                ("CSV and LOG files", "*.csv;*.log"),
                ("CSV files", "*.csv"),
                ("LOG files", "*.log"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self.bt_data_file.set(path)

    def _build_backtest_tab(self):
        """Create the Backtest tab UI with all components."""
        frame = self.bt_tab
        frame.columnconfigure(1, weight=1)
        row = 0

        ttk.Label(frame, text="Backtest Configuration", font=('Arial', 14, 'bold')).grid(row=row, column=0, sticky="w", pady=10)
        row += 1

        # Data file selection
        if not hasattr(self, 'bt_data_file'):
            self.bt_data_file = tk.StringVar()
        ttk.Label(frame, text="Historical Data File:").grid(row=row, column=0, sticky="e", padx=5, pady=2)
        ttk.Entry(frame, textvariable=self.bt_data_file, width=60).grid(row=row, column=1, padx=5, pady=2, sticky="w")
        ttk.Button(frame, text="Browse", command=self._bt_browse_csv).grid(row=row, column=2, padx=5, pady=2, sticky="w")
        row += 1

        # Strategy Configuration
        ttk.Label(frame, text="Strategy Configuration", font=('Arial', 12, 'bold')).grid(row=row, column=0, columnspan=3, sticky="w", pady=(15, 5))
        row += 1

        ttk.Label(frame, text="Indicators:", font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky="w", padx=5, pady=2)
        row += 1

        indicators_frame = ttk.Frame(frame)
        indicators_frame.grid(row=row, column=0, columnspan=3, sticky="w", padx=5, pady=2)
        row += 1

        # Use existing tk.BooleanVar's initialized from config; do not overwrite them here
        ttk.Checkbutton(indicators_frame, text="EMA Crossover", variable=self.bt_use_ema_crossover).grid(row=0, column=0, sticky="w", padx=5)
        ttk.Checkbutton(indicators_frame, text="MACD", variable=self.bt_use_macd).grid(row=0, column=1, sticky="w", padx=5)
        ttk.Checkbutton(indicators_frame, text="VWAP", variable=self.bt_use_vwap).grid(row=0, column=2, sticky="w", padx=5)
        ttk.Checkbutton(indicators_frame, text="RSI Filter", variable=self.bt_use_rsi_filter).grid(row=0, column=3, sticky="w", padx=5)
        ttk.Checkbutton(indicators_frame, text="HTF Trend", variable=self.bt_use_htf_trend).grid(row=1, column=0, sticky="w", padx=5)
        ttk.Checkbutton(indicators_frame, text="Bollinger Bands", variable=self.bt_use_bollinger_bands).grid(row=1, column=1, sticky="w", padx=5)
        ttk.Checkbutton(indicators_frame, text="Stochastic", variable=self.bt_use_stochastic).grid(row=1, column=2, sticky="w", padx=5)
        ttk.Checkbutton(indicators_frame, text="ATR", variable=self.bt_use_atr).grid(row=1, column=3, sticky="w", padx=5)

        row += 1

        # Parameters
        ttk.Label(frame, text="Parameters:", font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky="w", padx=5, pady=(10,2))
        row += 1

        self.bt_param_frame = ttk.LabelFrame(self.bt_tab, text="Parameters")
        self.bt_param_frame.grid(row=row, column=0, columnspan=3, sticky="w", padx=5, pady=2)

        params_frame = ttk.Frame(frame)
        params_frame.grid(row=row, column=0, columnspan=3, sticky="w", padx=5, pady=2)

        # EMA Parameters
        ttk.Label(params_frame, text="Fast EMA:").grid(row=0, column=0, sticky="e", padx=2)
        self.bt_fast_ema = tk.StringVar(value="9")
        ttk.Entry(params_frame, textvariable=self.bt_fast_ema, width=8).grid(row=0, column=1, padx=2)

        ttk.Label(params_frame, text="Slow EMA:").grid(row=0, column=2, sticky="e", padx=2)
        self.bt_slow_ema = tk.StringVar(value="21")
        ttk.Entry(params_frame, textvariable=self.bt_slow_ema, width=8).grid(row=0, column=3, padx=2)

        # MACD Parameters
        ttk.Label(params_frame, text="MACD Fast:").grid(row=1, column=0, sticky="e", padx=2)
        self.bt_macd_fast = tk.StringVar(value="12")
        ttk.Entry(params_frame, textvariable=self.bt_macd_fast, width=8).grid(row=1, column=1, padx=2)

        ttk.Label(params_frame, text="MACD Slow:").grid(row=1, column=2, sticky="e", padx=2)
        self.bt_macd_slow = tk.StringVar(value="26")
        ttk.Entry(params_frame, textvariable=self.bt_macd_slow, width=8).grid(row=1, column=3, padx=2)

        ttk.Label(params_frame, text="MACD Signal:").grid(row=1, column=4, sticky="e", padx=2)
        self.bt_macd_signal = tk.StringVar(value="9")
        ttk.Entry(params_frame, textvariable=self.bt_macd_signal, width=8).grid(row=1, column=5, padx=2)

        # RSI Parameters
        ttk.Label(params_frame, text="RSI Length:").grid(row=2, column=0, sticky="e", padx=2)
        self.bt_rsi_length = tk.StringVar(value="14")
        ttk.Entry(params_frame, textvariable=self.bt_rsi_length, width=8).grid(row=2, column=1, padx=2)

        ttk.Label(params_frame, text="RSI Oversold:").grid(row=2, column=2, sticky="e", padx=2)
        self.bt_rsi_oversold = tk.StringVar(value="30")
        ttk.Entry(params_frame, textvariable=self.bt_rsi_oversold, width=8).grid(row=2, column=3, padx=2)

        ttk.Label(params_frame, text="RSI Overbought:").grid(row=2, column=4, sticky="e", padx=2)
        self.bt_rsi_overbought = tk.StringVar(value="70")
        ttk.Entry(params_frame, textvariable=self.bt_rsi_overbought, width=8).grid(row=2, column=5, padx=2)

        # HTF Parameters
        ttk.Label(params_frame, text="HTF Period:").grid(row=3, column=0, sticky="e", padx=2)
        self.bt_htf_period = tk.StringVar(value="20")
        ttk.Entry(params_frame, textvariable=self.bt_htf_period, width=8).grid(row=3, column=1, padx=2)
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
        self.bt_base_sl_points = tk.StringVar(value="15")
        ttk.Entry(risk_frame, textvariable=self.bt_base_sl_points, width=8).grid(row=0, column=1, padx=2)

        ttk.Label(risk_frame, text="TP1 Points:").grid(row=0, column=2, sticky="e", padx=2)
        ttk.Entry(risk_frame, textvariable=self.bt_tp_points[0], width=8).grid(row=0, column=3, padx=2)
        ttk.Label(risk_frame, text="TP2 Points:").grid(row=0, column=4, sticky="e", padx=2)
        ttk.Entry(risk_frame, textvariable=self.bt_tp_points[1], width=8).grid(row=0, column=5, padx=2)
        ttk.Label(risk_frame, text="TP3 Points:").grid(row=1, column=0, sticky="e", padx=2)
        ttk.Entry(risk_frame, textvariable=self.bt_tp_points[2], width=8).grid(row=1, column=1, padx=2)

        ttk.Label(risk_frame, text="TP4 Points:").grid(row=1, column=2, sticky="e", padx=2)
        ttk.Entry(risk_frame, textvariable=self.bt_tp_points[3], width=8).grid(row=1, column=3, padx=2)

        self.bt_use_trail_stop = tk.BooleanVar(value=True)
        ttk.Checkbutton(risk_frame, text="Use Trailing Stop", variable=self.bt_use_trail_stop).grid(row=1, column=4, columnspan=2, sticky="w", padx=5)

        ttk.Label(risk_frame, text="Trail Activation Points:").grid(row=2, column=0, sticky="e", padx=2)
        self.bt_trail_activation = tk.StringVar(value="25")
        ttk.Entry(risk_frame, textvariable=self.bt_trail_activation, width=8).grid(row=2, column=1, padx=2)

        ttk.Label(risk_frame, text="Trail Distance Points:").grid(row=2, column=2, sticky="e", padx=2)
        self.bt_trail_distance = tk.StringVar(value="10")
        ttk.Entry(risk_frame, textvariable=self.bt_trail_distance, width=8).grid(row=2, column=3, padx=2)

        ttk.Label(risk_frame, text="Risk % per Trade:").grid(row=2, column=4, sticky="e", padx=2)
        self.bt_risk_per_trade_percent = tk.StringVar(value="1.0")
        ttk.Entry(risk_frame, textvariable=self.bt_risk_per_trade_percent, width=8).grid(row=2, column=5, padx=2)
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
        self.session_frame = ttk.Frame(frame)
        self.session_frame.grid(row=row, column=0, columnspan=3, sticky="w", padx=5, pady=2)
        ttk.Label(self.session_frame, text="Start (HH:MM):").grid(row=0, column=0, sticky="e", padx=2)
        ttk.Entry(self.session_frame, textvariable=self.bt_session_start_hour, width=4).grid(row=0, column=1, padx=1)
        ttk.Label(self.session_frame, text=":").grid(row=0, column=2)
        ttk.Entry(self.session_frame, textvariable=self.bt_session_start_min, width=4).grid(row=0, column=3, padx=1)
        ttk.Label(self.session_frame, text="End (HH:MM):").grid(row=0, column=4, sticky="e", padx=2)
        ttk.Entry(self.session_frame, textvariable=self.bt_session_end_hour, width=4).grid(row=0, column=5, padx=1)
        ttk.Label(self.session_frame, text=":").grid(row=0, column=6)
        ttk.Entry(self.session_frame, textvariable=self.bt_session_end_min, width=4).grid(row=0, column=7, padx=1)
        ttk.Label(self.session_frame, text="Intraday:").grid(row=1, column=0, sticky="e", padx=2)
        ttk.Checkbutton(self.session_frame, variable=self.bt_is_intraday).grid(row=1, column=1, sticky="w", padx=2)
        row += 1

        # Trading Controls
        ttk.Label(frame, text="Trading Controls", font=('Arial', 12, 'bold')).grid(row=row, column=0, columnspan=3, sticky="w", pady=(15,5))
        row += 1

        ttk.Button(frame, text="Start Backtest", command=self.run_backtest, style="Accent.TButton").grid(row=row, column=0, columnspan=3, pady=10)
        row += 1

        # Results box
        if not hasattr(self, 'bt_result_box'):
            self.bt_result_box = tk.Text(frame, height=20, state="disabled", wrap="word")
        self.bt_result_box.grid(row=row, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")
        frame.rowconfigure(row, weight=1)

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
        ttk.Entry(risk_frame, textvariable=self.ft_tp1_points, width=8).grid(row=0, column=3, padx=2)
        ttk.Label(risk_frame, text="TP2 Points:").grid(row=0, column=4, sticky="e", padx=2)
        ttk.Entry(risk_frame, textvariable=self.ft_tp2_points, width=8).grid(row=0, column=5, padx=2)
        ttk.Label(risk_frame, text="TP3 Points:").grid(row=1, column=0, sticky="e", padx=2)
        ttk.Entry(risk_frame, textvariable=self.ft_tp3_points, width=8).grid(row=1, column=1, padx=2)
        ttk.Label(risk_frame, text="TP4 Points:").grid(row=1, column=2, sticky="e", padx=2)
        ttk.Entry(risk_frame, textvariable=self.ft_tp4_points, width=8).grid(row=1, column=3, padx=2)

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
        ttk.Entry(instrument_frame, textvariable=self.ft_symbol, width=16).grid(row=0, column=1, padx=2)
        ttk.Label(instrument_frame, text="Exchange:").grid(row=0, column=2, sticky="e", padx=2)
        ttk.Entry(instrument_frame, textvariable=self.ft_exchange, width=10).grid(row=0, column=3, padx=2)
        ttk.Label(instrument_frame, text="Lot Size:").grid(row=0, column=4, sticky="e", padx=2)
        ttk.Entry(instrument_frame, textvariable=self.bt_lot_size, width=8).grid(row=0, column=5, padx=2)
        row += 1

        # --- Capital Settings ---
        ttk.Label(frame, text="Capital Settings:", font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky="w", padx=5, pady=(10,2))
        row += 1
        capital_frame = ttk.Frame(frame)
        capital_frame.grid(row=row, column=0, columnspan=3, sticky="w", padx=5, pady=2)
        ttk.Label(capital_frame, text="Initial Capital:").grid(row=0, column=0, sticky="e", padx=2)
        ttk.Entry(capital_frame, textvariable=self.ft_initial_capital, width=14).grid(row=0, column=1, padx=2)
        row += 1

        # --- Session Settings ---
        ttk.Label(frame, text="Session Settings:", font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky="w", padx=5, pady=(10,2))
        row += 1
        self.session_frame = ttk.Frame(frame)
        self.session_frame.grid(row=row, column=0, columnspan=3, sticky="w", padx=5, pady=2)
        ttk.Label(self.session_frame, text="Start (HH:MM):").grid(row=0, column=0, sticky="e", padx=2)
        ttk.Entry(self.session_frame, textvariable=self.ft_session_start_hour, width=4).grid(row=0, column=1, padx=1)
        ttk.Label(self.session_frame, text=":").grid(row=0, column=2)
        ttk.Entry(self.session_frame, textvariable=self.ft_session_start_min, width=4).grid(row=0, column=3, padx=1)
        ttk.Label(self.session_frame, text="End (HH:MM):").grid(row=0, column=4, sticky="e", padx=2)
        ttk.Entry(self.session_frame, textvariable=self.ft_session_end_hour, width=4).grid(row=0, column=5, padx=1)
        ttk.Label(self.session_frame, text=":").grid(row=0, column=6)
        ttk.Entry(self.session_frame, textvariable=self.ft_session_end_min, width=4).grid(row=0, column=7, padx=1)
        ttk.Label(self.session_frame, text="Intraday:").grid(row=1, column=0, sticky="e", padx=2)
        ttk.Checkbutton(self.session_frame, variable=self.bt_is_intraday).grid(row=1, column=1, sticky="w", padx=2)
        row += 1

        # Trading Controls
        ttk.Label(frame, text="Trading Controls", font=('Arial', 12, 'bold')).grid(row=row, column=0, columnspan=3, sticky="w", pady=(15,5))
        row += 1

        ttk.Button(frame, text="Start Backtest", command=self.run_backtest, style="Accent.TButton").grid(row=row, column=0, columnspan=3, pady=10)
        row += 1

        # Results box
        if not hasattr(self, 'bt_result_box'):
            self.bt_result_box = tk.Text(frame, height=20, state="disabled", wrap="word")
        self.bt_result_box.grid(row=row, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")
        frame.rowconfigure(row, weight=1)

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
        ttk.Entry(risk_frame, textvariable=self.ft_tp1_points, width=8).grid(row=0, column=3, padx=2)
        ttk.Label(risk_frame, text="TP2 Points:").grid(row=0, column=4, sticky="e", padx=2)
        ttk.Entry(risk_frame, textvariable=self.ft_tp2_points, width=8).grid(row=0, column=5, padx=2)
        ttk.Label(risk_frame, text="TP3 Points:").grid(row=1, column=0, sticky="e", padx=2)
        ttk.Entry(risk_frame, textvariable=self.ft_tp3_points, width=8).grid(row=1, column=1, padx=2)
        ttk.Label(risk_frame, text="TP4 Points:").grid(row=1, column=2, sticky="e", padx=2)
        ttk.Entry(risk_frame, textvariable=self.ft_tp4_points, width=8).grid(row=1, column=3, padx=2)

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
        ttk.Entry(instrument_frame, textvariable=self.ft_symbol, width=16).grid(row=0, column=1, padx=2)
        ttk.Label(instrument_frame, text="Exchange:").grid(row=0, column=2, sticky="e", padx=2)
        ttk.Entry(instrument_frame, textvariable=self.ft_exchange, width=10).grid(row=0, column=3, padx=2)
        ttk.Label(instrument_frame, text="Lot Size:").grid(row=0, column=4, sticky="e", padx=2)
        ttk.Entry(instrument_frame, textvariable=self.bt_lot_size, width=8).grid(row=0, column=5, padx=2)
        row += 1

        # --- Capital Settings ---
        ttk.Label(frame, text="Capital Settings:", font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky="w", padx=5, pady=(10,2))
        row += 1
        capital_frame = ttk.Frame(frame)
        capital_frame.grid(row=row, column=0, columnspan=3, sticky="w", padx=5, pady=2)
        ttk.Label(capital_frame, text="Initial Capital:").grid(row=0, column=0, sticky="e", padx=2)
        ttk.Entry(capital_frame, textvariable=self.ft_initial_capital, width=14).grid(row=0, column=1, padx=2)
        row += 1

        # --- Session Settings ---
        ttk.Label(frame, text="Session Settings:", font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky="w", padx=5, pady=(10,2))
        row += 1
        self.session_frame = ttk.Frame(frame)
        self.session_frame.grid(row=row, column=0, columnspan=3, sticky="w", padx=5, pady=2)
        ttk.Label(self.session_frame, text="Start (HH:MM):").grid(row=0, column=0, sticky="e", padx=2)
        ttk.Entry(self.session_frame, textvariable=self.ft_session_start_hour, width=4).grid(row=0, column=1, padx=1)
        ttk.Label(self.session_frame, text=":").grid(row=0, column=2)
        ttk.Entry(self.session_frame, textvariable=self.ft_session_start_min, width=4).grid(row=0, column=3, padx=1)
        ttk.Label(self.session_frame, text="End (HH:MM):").grid(row=0, column=4, sticky="e", padx=2)
        ttk.Entry(self.session_frame, textvariable=self.ft_session_end_hour, width=4).grid(row=0, column=5, padx=1)
        ttk.Label(self.session_frame, text=":").grid(row=0, column=6)
        ttk.Entry(self.session_frame, textvariable=self.ft_session_end_min, width=4).grid(row=0, column=7, padx=1)
        ttk.Label(self.session_frame, text="Intraday:").grid(row=1, column=0, sticky="e", padx=2)
        ttk.Checkbutton(self.session_frame, variable=self.bt_is_intraday).grid(row=1, column=1, sticky="w", padx=2)
        row += 1

        # Trading Controls
        ttk.Label(frame, text="Trading Controls", font=('Arial', 12, 'bold')).grid(row=row, column=0, columnspan=3, sticky="w", pady=(15,5))
        row += 1

        ttk.Button(frame, text="Start Backtest", command=self.run_backtest, style="Accent.TButton").grid(row=row, column=0, columnspan=3, pady=10)
        row += 1

        # Results box
        if not hasattr(self, 'bt_result_box'):
            self.bt_result_box = tk.Text(frame, height=20, state="disabled", wrap="word")
        self.bt_result_box.grid(row=row, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")
        frame.rowconfigure(row, weight=1)