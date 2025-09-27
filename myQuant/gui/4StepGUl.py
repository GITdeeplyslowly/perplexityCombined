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
from datetime import datetime
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
        """Initialize all GUI variables from a provided config (single source for widgets).

        Merge DEFAULT_CONFIG (SSOT) with provided `config` so no literals are introduced here.
        Set values on the pre-created tk.Variable instances (do NOT reassign them).
        """
        # Merge per-section defaults: provided config overrides DEFAULT_CONFIG
        def merged_section(section):
            base = DEFAULT_CONFIG.get(section, {}) or {}
            overlay = config.get(section, {}) or {}
            merged = base.copy()
            merged.update(overlay)
            return merged

        strategy_defaults = merged_section('strategy')
        risk_defaults = merged_section('risk')
        capital_defaults = merged_section('capital')
        instrument_defaults = merged_section('instrument')
        session_defaults = merged_section('session')

        # --- Strategy variables: set values on pre-created tk.Variable instances ---
        self.bt_use_ema_crossover.set(bool(strategy_defaults.get('use_ema_crossover', False)))
        self.bt_use_macd.set(bool(strategy_defaults.get('use_macd', False)))
        self.bt_use_vwap.set(bool(strategy_defaults.get('use_vwap', False)))
        self.bt_use_rsi_filter.set(bool(strategy_defaults.get('use_rsi_filter', False)))
        self.bt_use_htf_trend.set(bool(strategy_defaults.get('use_htf_trend', False)))
        self.bt_use_bollinger_bands.set(bool(strategy_defaults.get('use_bollinger_bands', False)))
        self.bt_use_stochastic.set(bool(strategy_defaults.get('use_stochastic', False)))
        self.bt_use_atr.set(bool(strategy_defaults.get('use_atr', False)))

        # EMA parameters
        self.bt_fast_ema.set(str(strategy_defaults.get('fast_ema', '')))
        self.bt_slow_ema.set(str(strategy_defaults.get('slow_ema', '')))

        # MACD parameters
        self.bt_macd_fast.set(str(strategy_defaults.get('macd_fast', '')))
        self.bt_macd_slow.set(str(strategy_defaults.get('macd_slow', '')))
        self.bt_macd_signal.set(str(strategy_defaults.get('macd_signal', '')))

        # RSI parameters
        self.bt_rsi_length.set(str(strategy_defaults.get('rsi_length', '')))
        self.bt_rsi_oversold.set(str(strategy_defaults.get('rsi_oversold', '')))
        self.bt_rsi_overbought.set(str(strategy_defaults.get('rsi_overbought', '')))

        # HTF and consecutive green bars
        self.bt_htf_period.set(str(strategy_defaults.get('htf_period', '')))
        self.bt_consecutive_green_bars.set(str(strategy_defaults.get('consecutive_green_bars', '')))

        # --- Risk management ---
        self.bt_base_sl_points.set(str(risk_defaults.get('base_sl_points', '')))
        tp_points = risk_defaults.get('tp_points', [])
        for i in range(len(self.bt_tp_points)):
            if i < len(tp_points):
                self.bt_tp_points[i].set(str(tp_points[i]))
            else:
                # if DEFAULT_CONFIG has fewer entries, set to empty so GUI stays driven by SSOT
                self.bt_tp_points[i].set('')

        tp_percents = risk_defaults.get('tp_percents', [])
        for i in range(len(self.bt_tp_percents)):
            if i < len(tp_percents):
                # present in percent in GUI
                self.bt_tp_percents[i].set(str(tp_percents[i] * 100))
            else:
                self.bt_tp_percents[i].set('')

        self.bt_use_trail_stop.set(bool(risk_defaults.get('use_trail_stop', False)))
        self.bt_trail_activation.set(str(risk_defaults.get('trail_activation_points', '')))
        self.bt_trail_distance.set(str(risk_defaults.get('trail_distance_points', '')))
        self.bt_risk_per_trade_percent.set(str(risk_defaults.get('risk_per_trade_percent', '')))

        # --- Capital settings ---
        self.bt_initial_capital.set(str(capital_defaults.get('initial_capital', '')))

        # --- Instrument settings ---
        self.bt_symbol.set(str(instrument_defaults.get('symbol', '')))
        self.bt_exchange.set(str(instrument_defaults.get('exchange', '')))
        self.bt_lot_size.set(str(instrument_defaults.get('lot_size', '')))

        # --- Session settings ---
        self.bt_is_intraday.set(bool(session_defaults.get('is_intraday', False)))
        self.bt_session_start_hour.set(str(session_defaults.get('start_hour', '')))
        self.bt_session_start_min.set(str(session_defaults.get('start_min', '')))
        self.bt_session_end_hour.set(str(session_defaults.get('end_hour', '')))
        self.bt_session_end_min.set(str(session_defaults.get('end_min', '')))
    # persistence helpers removed per simplified 4-stage workflow (no user_preferences.json)
    # (Removed incomplete method stubs and stray hyphens that produced syntax errors)
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

    def _build_backtest_tab(self):
        """Create the Backtest tab UI with all components."""
        frame = self.bt_tab
        frame.columnconfigure(1, weight=1)
        row = 0
        
        ttk.Label(frame, text="Backtest Configuration", font=('Arial', 14, 'bold')).grid(row=row, column=0, sticky="w", pady=10)
        row += 1
        
        # Data file selection
        ttk.Label(frame, text="Historical Data File:").grid(row=row, column=0, sticky="e", padx=5, pady=2)
        ttk.Entry(frame, textvariable=self.bt_data_file, width=60).grid(row=row, column=1, padx=5, pady=2, sticky="w")
        ttk.Button(frame, text="Browse", command=self._bt_browse_csv).grid(row=row, column=2, padx=5, pady=2, sticky="w")
        row += 1
        
        # --- Strategy Configuration ---
        ttk.Label(frame, text="Strategy Configuration", font=('Arial', 12, 'bold')).grid(row=row, column=0, columnspan=3, sticky="w", pady=(15,5))
        row += 1

        # Indicator Toggles
        ttk.Label(frame, text="Indicators:", font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky="w", padx=5, pady=2)
        row += 1

        indicators_frame = ttk.Frame(frame)
        indicators_frame.grid(row=row, column=0, columnspan=3, sticky="w", padx=5, pady=2)

        # Use Variables already created/initialized in _initialize_all_variables/_initialize_variables_from_config
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

        # Make params_frame a child of the LabelFrame so its widgets appear inside the labelled box
        params_frame = ttk.Frame(self.bt_param_frame)
        params_frame.grid(row=0, column=0, sticky="w", padx=5, pady=2)

        # EMA Parameters
        ttk.Label(params_frame, text="Fast EMA:").grid(row=0, column=0, sticky="e", padx=2)
        ttk.Entry(params_frame, textvariable=self.bt_fast_ema, width=8).grid(row=0, column=1, padx=2)

        ttk.Label(params_frame, text="Slow EMA:").grid(row=0, column=2, sticky="e", padx=2)
        ttk.Entry(params_frame, textvariable=self.bt_slow_ema, width=8).grid(row=0, column=3, padx=2)

        # MACD Parameters
        ttk.Label(params_frame, text="MACD Fast:").grid(row=1, column=0, sticky="e", padx=2)
        ttk.Entry(params_frame, textvariable=self.bt_macd_fast, width=8).grid(row=1, column=1, padx=2)
 
        ttk.Label(params_frame, text="MACD Slow:").grid(row=1, column=2, sticky="e", padx=2)
        ttk.Entry(params_frame, textvariable=self.bt_macd_slow, width=8).grid(row=1, column=3, padx=2)
 
        ttk.Label(params_frame, text="MACD Signal:").grid(row=1, column=4, sticky="e", padx=2)
        ttk.Entry(params_frame, textvariable=self.bt_macd_signal, width=8).grid(row=1, column=5, padx=2)
 
        # RSI Parameters
        ttk.Label(params_frame, text="RSI Length:").grid(row=2, column=0, sticky="e", padx=2)
        ttk.Entry(params_frame, textvariable=self.bt_rsi_length, width=8).grid(row=2, column=1, padx=2)
 
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

        # Risk Management
        ttk.Label(frame, text="Risk Management:", font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky="w", padx=5, pady=(10,2))
        row += 1

        risk_frame = ttk.Frame(frame)
        risk_frame.grid(row=row, column=0, columnspan=3, sticky="w", padx=5, pady=2)
 
        ttk.Label(risk_frame, text="Stop Loss Points:").grid(row=0, column=0, sticky="e", padx=2)
        ttk.Entry(risk_frame, textvariable=self.bt_base_sl_points, width=8).grid(row=0, column=1, padx=2)

        ttk.Label(risk_frame, text="TP1 Points:").grid(row=0, column=2, sticky="e", padx=2)
        ttk.Entry(risk_frame, textvariable=self.bt_tp_points[0], width=8).grid(row=0, column=3, padx=2)
        ttk.Label(risk_frame, text="TP2 Points:").grid(row=0, column=4, sticky="e", padx=2)
        ttk.Entry(risk_frame, textvariable=self.bt_tp_points[1], width=8).grid(row=0, column=5, padx=2)
        ttk.Label(risk_frame, text="TP3 Points:").grid(row=1, column=0, sticky="e", padx=2)
        ttk.Entry(risk_frame, textvariable=self.bt_tp_points[2], width=8).grid(row=1, column=1, padx=2)

        ttk.Label(risk_frame, text="TP4 Points:").grid(row=1, column=2, sticky="e", padx=2)
        ttk.Entry(risk_frame, textvariable=self.bt_tp_points[3], width=8).grid(row=1, column=3, padx=2)

        ttk.Checkbutton(risk_frame, text="Use Trailing Stop", variable=self.bt_use_trail_stop).grid(row=1, column=4, columnspan=2, sticky="w", padx=5)

        ttk.Label(risk_frame, text="Trail Activation Points:").grid(row=2, column=0, sticky="e", padx=2)
        ttk.Entry(risk_frame, textvariable=self.bt_trail_activation, width=8).grid(row=2, column=1, padx=2)

        ttk.Label(risk_frame, text="Trail Distance Points:").grid(row=2, column=2, sticky="e", padx=2)
        ttk.Entry(risk_frame, textvariable=self.bt_trail_distance, width=8).grid(row=2, column=3, padx=2)

        ttk.Label(risk_frame, text="Risk % per Trade:").grid(row=2, column=4, sticky="e", padx=2)
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

        # Results area
        self.bt_result_box = tk.Text(frame, height=20, state="disabled", wrap="word")
        self.bt_result_box.grid(row=row, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")
        frame.rowconfigure(row, weight=1)
        row += 1
        
        # Backtest controls
        ttk.Button(frame, text="Run Backtest", command=self._bt_run_backtest).grid(row=row, column=0, padx=5, pady=5, sticky="w")
        ttk.Button(frame, text="Show Config", command=lambda: self._show_config(mode='backtest')).grid(row=row, column=1, padx=5, pady=5, sticky="w")

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

        # Use Variables already created/initialized in _initialize_all_variables/_initialize_variables_from_config
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

        # params_frame must be a child of ft_param_frame and use existing ft_* vars
        params_frame = ttk.Frame(self.ft_param_frame)
        params_frame.grid(row=0, column=0, sticky="w", padx=5, pady=2)

        # EMA Parameters
        ttk.Label(params_frame, text="Fast EMA:").grid(row=0, column=0, sticky="e", padx=2)
        ttk.Entry(params_frame, textvariable=self.ft_fast_ema, width=8).grid(row=0, column=1, padx=2)

        ttk.Label(params_frame, text="Slow EMA:").grid(row=0, column=2, sticky="e", padx=2)
        ttk.Entry(params_frame, textvariable=self.ft_slow_ema, width=8).grid(row=0, column=3, padx=2)
 
        # MACD Parameters
        ttk.Label(params_frame, text="MACD Fast:").grid(row=1, column=0, sticky="e", padx=2)
        ttk.Entry(params_frame, textvariable=self.ft_macd_fast, width=8).grid(row=1, column=1, padx=2)
 
        ttk.Label(params_frame, text="MACD Slow:").grid(row=1, column=2, sticky="e", padx=2)
        ttk.Entry(params_frame, textvariable=self.ft_macd_slow, width=8).grid(row=1, column=3, padx=2)
 
        ttk.Label(params_frame, text="MACD Signal:").grid(row=1, column=4, sticky="e", padx=2)
        ttk.Entry(params_frame, textvariable=self.ft_macd_signal, width=8).grid(row=1, column=5, padx=2)
 
        # RSI Parameters
        ttk.Label(params_frame, text="RSI Length:").grid(row=2, column=0, sticky="e", padx=2)
        ttk.Entry(params_frame, textvariable=self.ft_rsi_length, width=8).grid(row=2, column=1, padx=2)
 
        ttk.Label(params_frame, text="RSI Oversold:").grid(row=2, column=2, sticky="e", padx=2)
        ttk.Entry(params_frame, textvariable=self.ft_rsi_oversold, width=8).grid(row=2, column=3, padx=2)
 
        ttk.Label(params_frame, text="RSI Overbought:").grid(row=2, column=4, sticky="e", padx=2)
        ttk.Entry(params_frame, textvariable=self.ft_rsi_overbought, width=8).grid(row=2, column=5, padx=2)
 
        # HTF Parameters
        ttk.Label(params_frame, text="HTF Period:").grid(row=3, column=0, sticky="e", padx=2)
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
        ttk.Entry(risk_frame, textvariable=self.ft_base_sl_points, width=8).grid(row=0, column=1, padx=2)

        ttk.Label(risk_frame, text="TP1 Points:").grid(row=0, column=2, sticky="e", padx=2)
        ttk.Entry(risk_frame, textvariable=self.bt_tp_points[0], width=8).grid(row=0, column=3, padx=2)
        ttk.Label(risk_frame, text="TP2 Points:").grid(row=0, column=4, sticky="e", padx=2)
        ttk.Entry(risk_frame, textvariable=self.bt_tp_points[1], width=8).grid(row=0, column=5, padx=2)
        ttk.Label(risk_frame, text="TP3 Points:").grid(row=1, column=0, sticky="e", padx=2)
        ttk.Entry(risk_frame, textvariable=self.bt_tp_points[2], width=8).grid(row=1, column=1, padx=2)

        ttk.Label(risk_frame, text="TP4 Points:").grid(row=1, column=2, sticky="e", padx=2)
        ttk.Entry(risk_frame, textvariable=self.bt_tp_points[3], width=8).grid(row=1, column=3, padx=2)

        ttk.Checkbutton(risk_frame, text="Use Trailing Stop", variable=self.ft_use_trail_stop).grid(row=1, column=4, columnspan=2, sticky="w", padx=5)

        ttk.Label(risk_frame, text="Trail Activation Points:").grid(row=2, column=0, sticky="e", padx=2)
        ttk.Entry(risk_frame, textvariable=self.ft_trail_activation_points, width=8).grid(row=2, column=1, padx=2)

        ttk.Label(risk_frame, text="Trail Distance Points:").grid(row=2, column=2, sticky="e", padx=2)
        ttk.Entry(risk_frame, textvariable=self.ft_trail_distance_points, width=8).grid(row=2, column=3, padx=2)

        ttk.Label(risk_frame, text="Risk % per Trade:").grid(row=2, column=4, sticky="e", padx=2)
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

        # Results area
        self.bt_result_box = tk.Text(frame, height=20, state="disabled", wrap="word")
        self.bt_result_box.grid(row=row, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")
        frame.rowconfigure(row, weight=1)
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

        # Map TP variables to the backtest TP StringVars to avoid duplication
        self.ft_tp1_points = self.bt_tp_points[0]
        self.ft_tp2_points = self.bt_tp_points[1] 
        self.ft_tp3_points = self.bt_tp_points[2]
        self.ft_tp4_points = self.bt_tp_points[3]

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

        # Get validated and frozen config using the same workflow as backtest
        config = self.build_config_from_gui(mode='forward_test')
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
        messagebox.showinfo("Stop", "Forward test stop functionality not yet implemented.")

    # --- Status Tab ---
    def _build_log_tab(self):
        frame = self.log_tab
        row = 0

        ttk.Label(frame, text="Unified Trading System Status & Logs", font=('Arial', 14, 'bold')).grid(row=row, column=0, sticky="w", pady=10)
        row += 1

        ttk.Label(frame, text=f"Log File: {LOG_FILENAME}").grid(row=row, column=0, sticky="w", pady=2)
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
        # Session and results widgets are built during GUI initialization (_build_backtest_tab)

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
            frozen_cfg = self.build_config_from_gui()
            if frozen_cfg is None:
                logger.warning("Backtest aborted: invalid or unfrozen configuration")
                return

            # Data path: prefer backtest.data_path in config, fallback to file chooser input
            data_path = None
            try:
                data_path = frozen_cfg.get('backtest', {}).get('data_path') or self.bt_data_file.get()
            except Exception:
                # frozen_cfg is MappingProxyType; use dict() to inspect if needed
                data_path = dict(frozen_cfg).get('backtest', {}).get('data_path') or self.bt_data_file.get()

            if not data_path:
                messagebox.showerror("Missing Data", "Please select a data file for backtest.")
                return

            # Construct runner with frozen config (strict)
            runner = BacktestRunner(config=frozen_cfg, data_path=data_path)
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

    def apply_gui_state_to_config(self, config):
        """Copy current Backtest GUI widget values into provided config dict (mutating it)."""
        # Strategy
        config.setdefault('strategy', {})
        config['strategy']['use_ema_crossover'] = self.bt_use_ema_crossover.get()
        config['strategy']['use_macd'] = self.bt_use_macd.get()
        config['strategy']['use_vwap'] = self.bt_use_vwap.get()
        config['strategy']['use_rsi_filter'] = self.bt_use_rsi_filter.get()
        config['strategy']['use_htf_trend'] = self.bt_use_htf_trend.get()
        config['strategy']['use_bollinger_bands'] = self.bt_use_bollinger_bands.get()
        config['strategy']['use_stochastic'] = self.bt_use_stochastic.get()
        config['strategy']['use_atr'] = self.bt_use_atr.get()
        config['strategy']['fast_ema'] = int(self.bt_fast_ema.get())
        config['strategy']['slow_ema'] = int(self.bt_slow_ema.get())
        config['strategy']['macd_fast'] = int(self.bt_macd_fast.get())
        config['strategy']['macd_slow'] = int(self.bt_macd_slow.get())
        config['strategy']['macd_signal'] = int(self.bt_macd_signal.get())
        config['strategy']['consecutive_green_bars'] = int(self.bt_consecutive_green_bars.get())
        config['strategy']['strategy_version'] = DEFAULT_CONFIG['strategy'].get('strategy_version', 1)

        # Risk
        config.setdefault('risk', {})
        config['risk']['base_sl_points'] = float(self.bt_base_sl_points.get())
        config['risk']['use_trail_stop'] = self.bt_use_trail_stop.get()
        config['risk']['trail_activation_points'] = float(self.bt_trail_activation.get())
        config['risk']['trail_distance_points'] = float(self.bt_trail_distance.get())
        config['risk']['tp_points'] = [float(v.get()) for v in self.bt_tp_points]
        config['risk']['tp_percents'] = [float(v.get())/100.0 for v in self.bt_tp_percents]

        # Capital
        config.setdefault('capital', {})
        config['capital']['initial_capital'] = float(self.bt_initial_capital.get())

        # Instrument
        config.setdefault('instrument', {})
        config['instrument']['symbol'] = self.bt_symbol.get()
        config['instrument']['exchange'] = self.bt_exchange.get()
        config['instrument']['lot_size'] = int(self.bt_lot_size.get())

        # Session
        config.setdefault('session', {})
        config['session']['is_intraday'] = self.bt_is_intraday.get()
        config['session']['start_hour'] = int(self.bt_session_start_hour.get())
        config['session']['start_min'] = int(self.bt_session_start_min.get())
        config['session']['end_hour'] = int(self.bt_session_end_hour.get())
        config['session']['end_min'] = int(self.bt_session_end_min.get())

        # Backtest & logging
        config.setdefault('backtest', {})
        config['backtest']['data_path'] = self.bt_data_file.get() if hasattr(self, 'bt_data_file') else ""
        config['logging'] = DEFAULT_CONFIG.get('logging', {}).copy()

    def apply_forward_gui_state_to_config(self, config):
        """Copy current Forward Test GUI widget values into provided config dict (mutating it)."""
        config.setdefault('strategy', {})
        config['strategy']['use_ema_crossover'] = self.ft_use_ema_crossover.get()
        config['strategy']['use_macd'] = self.ft_use_macd.get()
        config['strategy']['use_vwap'] = self.ft_use_vwap.get()
        config['strategy']['use_rsi_filter'] = self.ft_use_rsi_filter.get()
        config['strategy']['use_htf_trend'] = self.ft_use_htf_trend.get()
        config['strategy']['use_bollinger_bands'] = self.ft_use_bollinger_bands.get()
        config['strategy']['use_stochastic'] = self.ft_use_stochastic.get()
        config['strategy']['use_atr'] = self.ft_use_atr.get()
        # forward test strategy params (guard .get() on textvars)
        try:
            config['strategy']['fast_ema'] = int(self.ft_fast_ema.get())
            config['strategy']['slow_ema'] = int(self.ft_slow_ema.get())
            config['strategy']['macd_fast'] = int(self.ft_macd_fast.get())
            config['strategy']['macd_slow'] = int(self.ft_macd_slow.get())
            config['strategy']['macd_signal'] = int(self.ft_macd_signal.get())
            config['strategy']['rsi_length'] = int(self.ft_rsi_length.get())
            config['strategy']['htf_period'] = int(self.ft_htf_period.get())
        except Exception:
            # leave defaults if parsing fails; validation will catch invalid types
            logger.debug("Forward GUI: some numeric strategy fields could not be parsed; leaving defaults")

        # risk
        config.setdefault('risk', {})
        try:
            config['risk']['base_sl_points'] = float(self.ft_base_sl_points.get())
            config['risk']['use_trail_stop'] = self.ft_use_trail_stop.get()
            config['risk']['trail_activation_points'] = float(self.ft_trail_activation_points.get())
            config['risk']['trail_distance_points'] = float(self.ft_trail_distance_points.get())
            config['risk']['tp_points'] = [
                float(self.ft_tp1_points.get()),
                float(self.ft_tp2_points.get()),
                float(self.ft_tp3_points.get()),
                float(self.ft_tp4_points.get())
            ]
        except Exception:
            logger.debug("Forward GUI: some numeric risk fields could not be parsed; leaving defaults")

        # capital
        config.setdefault('capital', {})
        try:
            config['capital']['initial_capital'] = float(self.ft_initial_capital.get())
        except Exception:
            logger.debug("Forward GUI: initial capital parse failed; leaving default")

        # instrument / live / session
        config.setdefault('instrument', {})
        config['instrument']['symbol'] = self.ft_symbol.get() or config['instrument'].get('symbol')
        config.setdefault('live', {})
        config['live']['exchange_type'] = self.ft_exchange.get() or config['live'].get('exchange_type')
        config['live']['feed_type'] = self.ft_feed_type.get() or config['live'].get('feed_type')
        config.setdefault('session', {})
       
       

        try:
            if self.ft_session_start_hour.get():
                config['session']['start_hour'] = int(self.ft_session_start_hour.get())
            if self.ft_session_start_min.get():
                config['session']['start_min'] = int(self.ft_session_start_min.get())
            if self.ft_session_end_hour.get():
                config['session']['end_hour'] = int(self.ft_session_end_hour.get())
            if self.ft_session_end_min.get():
                config['session']['end_min'] = int(self.ft_session_end_min.get())
            config['session']['start_buffer_minutes'] = int(self.ft_start_buffer.get())
            config['session']['end_buffer_minutes'] = int(self.ft_end_buffer.get())
            config['session']['timezone'] = self.ft_timezone.get() or config['session'].get('timezone')
        except Exception:
            logger.debug("Forward GUI: session parsing issues; leaving defaults")

        # logging defaults preserved
        config['logging'] = DEFAULT_CONFIG.get('logging', {}).copy()

    def build_config_from_gui(self, mode='backtest'):
        """
        Collect GUI values into a dict, validate, and return frozen config.
        Returns None if validation fails (with error message shown to user).
        
        Args:
            mode: 'backtest' or 'forward_test' to determine which GUI variables to use
        """
        try:
            # start from a fresh copy of defaults (SSOT)
            config = create_config_from_defaults()

            if mode == 'backtest':
                # copy backtest GUI state into config
                self.apply_gui_state_to_config(config)
                # ensure data_path reflects chosen file
                if self.bt_data_file.get():
                    config.setdefault('backtest', {})['data_path'] = self.bt_data_file.get()
            elif mode == 'forward_test':
                # copy forward-test GUI state into config
                self.apply_forward_gui_state_to_config(config)
            else:
                raise ValueError(f"Unknown mode '{mode}'")

            validation_result = validate_config(config)
            if not validation_result.get('valid', False):
                error_msg = "Configuration validation failed:\n" + "\n".join(validation_result.get('errors', []))
                messagebox.showerror("Configuration Error", error_msg)
                logger.error("Config validation failed: %s", validation_result.get('errors', []))
                return None

            frozen_config = freeze_config(config)
            logger.info("Configuration built and validated successfully from GUI (mode=%s)", mode)
            return frozen_config

        except Exception as e:
            error_msg = f"Failed to build configuration from GUI: {str(e)}"
            messagebox.showerror("Configuration Error", error_msg)
            logger.exception("build_config_from_gui failed: %s", e)
            return None

    def _create_gui_framework(self):
        """Create the main notebook and tabs used by the GUI."""
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Create tabs
        self.bt_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.bt_tab, text="Backtest")
        
        self.ft_tab = ttk.Frame(self.notebook) 
        self.notebook.add(self.ft_tab, text="Forward Test")
        
        self.log_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.log_tab, text="Status / Logs")
        
        # Bind close handler
        self.protocol("WM_DELETE_WINDOW", self._on_close)

def main():
    """Main entry point for the unified trading GUI"""
    try:
        app = UnifiedTradingGUI()
        app.mainloop()
    except Exception as e:
        print(f"Failed to start GUI application: {e}")
    

if __name__ == "__main__":
    main()