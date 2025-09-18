# ...existing code...
"""
unified_gui.py - Unified Trading Interface for both Backtesting and Live Trading

Provides a comprehensive GUI for:
- Configuring strategy parameters
- Running backtests
- Starting/stopping forward tests
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
import pytz

from utils.cache_manager import refresh_symbol_cache, load_symbol_cache
from live.trader import LiveTrader
from backtest.backtest_runner import BacktestRunner

# configuration helpers
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

        # Build runtime config from defaults and persisted user prefs
        self.runtime_config = create_config_from_defaults()
        self._merge_user_preferences_into_runtime_config()

        # Initialize variables and widgets
        self._initialize_all_variables()
        self._initialize_variables_from_defaults()

        try:
            setup_logging_from_config(self.runtime_config)
        except Exception:
            logger.exception("setup_logging_from_config failed; using fallback logger")

        self._create_gui_framework()
        self._build_backtest_tab()
        self._build_forward_test_tab()
        self._build_log_tab()

        logger.info("GUI initialized successfully")

    def _initialize_all_variables(self):
        """Initialize GUI-only variables (no defaults from config)."""
        # Thread management
        self._backtest_thread = None
        self._forward_thread = None
        self.symbol_token_map = {}

        # UI helpers
        self.log_file_var = tk.StringVar(value=LOG_FILENAME)

        # Generic session GUI fields (not defaults)
        self.bt_data_file = tk.StringVar()
        self.capital_usable = tk.StringVar(value="₹0 (0%)")
        self.max_lots = tk.StringVar(value="0 lots (0 shares)")
        self.position_value = tk.StringVar(value="₹0")

    def _initialize_variables_from_defaults(self):
        """Initialize all widget variables from runtime_config (single source)."""
        strategy_defaults = self.runtime_config['strategy']
        risk_defaults = self.runtime_config['risk']
        capital_defaults = self.runtime_config['capital']
        instrument_defaults = self.runtime_config['instrument']
        session_defaults = self.runtime_config['session']

        # --- Backtest (bt_) variables ---
        self.bt_use_ema_crossover = tk.BooleanVar(value=strategy_defaults['use_ema_crossover'])
        self.bt_use_macd = tk.BooleanVar(value=strategy_defaults['use_macd'])
        self.bt_use_vwap = tk.BooleanVar(value=strategy_defaults['use_vwap'])
        self.bt_use_rsi_filter = tk.BooleanVar(value=strategy_defaults['use_rsi_filter'])
        self.bt_use_htf_trend = tk.BooleanVar(value=strategy_defaults['use_htf_trend'])
        self.bt_use_bollinger_bands = tk.BooleanVar(value=strategy_defaults['use_bollinger_bands'])
        self.bt_use_stochastic = tk.BooleanVar(value=strategy_defaults['use_stochastic'])
        self.bt_use_atr = tk.BooleanVar(value=strategy_defaults['use_atr'])

        self.bt_fast_ema = tk.StringVar(value=str(strategy_defaults['fast_ema']))
        self.bt_slow_ema = tk.StringVar(value=str(strategy_defaults['slow_ema']))
        self.bt_macd_fast = tk.StringVar(value=str(strategy_defaults['macd_fast']))
        self.bt_macd_slow = tk.StringVar(value=str(strategy_defaults['macd_slow']))
        self.bt_macd_signal = tk.StringVar(value=str(strategy_defaults['macd_signal']))
        self.bt_rsi_length = tk.StringVar(value=str(strategy_defaults['rsi_length']))
        self.bt_rsi_oversold = tk.StringVar(value=str(strategy_defaults['rsi_oversold']))
        self.bt_rsi_overbought = tk.StringVar(value=str(strategy_defaults['rsi_overbought']))
        self.bt_htf_period = tk.StringVar(value=str(strategy_defaults['htf_period']))
        self.bt_consecutive_green_bars = tk.StringVar(value=str(strategy_defaults['consecutive_green_bars']))

        self.bt_base_sl_points = tk.StringVar(value=str(risk_defaults['base_sl_points']))
        self.bt_tp_points = [tk.StringVar(value=str(p)) for p in risk_defaults['tp_points']]
        self.bt_tp_percents = [tk.StringVar(value=str(p*100)) for p in risk_defaults['tp_percents']]
        self.bt_use_trail_stop = tk.BooleanVar(value=risk_defaults['use_trail_stop'])
        self.bt_trail_activation = tk.StringVar(value=str(risk_defaults['trail_activation_points']))
        self.bt_trail_distance = tk.StringVar(value=str(risk_defaults['trail_distance_points']))
        self.bt_risk_per_trade_percent = tk.StringVar(value=str(risk_defaults['risk_per_trade_percent']))

        self.bt_initial_capital = tk.StringVar(value=str(capital_defaults['initial_capital']))

        self.bt_symbol = tk.StringVar(value=instrument_defaults['symbol'])
        self.bt_exchange = tk.StringVar(value=instrument_defaults['exchange'])
        self.bt_lot_size = tk.StringVar(value=str(instrument_defaults['lot_size']))

        self.bt_is_intraday = tk.BooleanVar(value=session_defaults['is_intraday'])
        self.bt_session_start_hour = tk.StringVar(value=str(session_defaults['start_hour']))
        self.bt_session_start_min = tk.StringVar(value=str(session_defaults['start_min']))
        self.bt_session_end_hour = tk.StringVar(value=str(session_defaults['end_hour']))
        self.bt_session_end_min = tk.StringVar(value=str(session_defaults['end_min']))

        # === Forward test (ft_) variables - use same defaults (SSOT) ===
        self.ft_tp_points = [tk.StringVar(value=str(p)) for p in risk_defaults['tp_points']]

        self.ft_fast_ema = tk.StringVar(value=str(strategy_defaults['fast_ema']))
        self.ft_slow_ema = tk.StringVar(value=str(strategy_defaults['slow_ema']))
        self.ft_macd_fast = tk.StringVar(value=str(strategy_defaults['macd_fast']))
        self.ft_macd_slow = tk.StringVar(value=str(strategy_defaults['macd_slow']))
        self.ft_macd_signal = tk.StringVar(value=str(strategy_defaults['macd_signal']))
        self.ft_rsi_length = tk.StringVar(value=str(strategy_defaults['rsi_length']))
        self.ft_rsi_oversold = tk.StringVar(value=str(strategy_defaults['rsi_oversold']))
        self.ft_rsi_overbought = tk.StringVar(value=str(strategy_defaults['rsi_overbought']))
        self.ft_htf_period = tk.StringVar(value=str(strategy_defaults['htf_period']))

        self.ft_base_sl_points = tk.StringVar(value=str(risk_defaults['base_sl_points']))
        self.ft_trail_activation_points = tk.StringVar(value=str(risk_defaults['trail_activation_points']))
        self.ft_trail_distance_points = tk.StringVar(value=str(risk_defaults['trail_distance_points']))
        self.ft_risk_per_trade_percent = tk.StringVar(value=str(risk_defaults['risk_per_trade_percent']))

        self.ft_use_ema_crossover = tk.BooleanVar(value=strategy_defaults['use_ema_crossover'])
        self.ft_use_macd = tk.BooleanVar(value=strategy_defaults['use_macd'])
        self.ft_use_vwap = tk.BooleanVar(value=strategy_defaults['use_vwap'])
        self.ft_use_rsi_filter = tk.BooleanVar(value=strategy_defaults['use_rsi_filter'])
        self.ft_use_htf_trend = tk.BooleanVar(value=strategy_defaults['use_htf_trend'])
        self.ft_use_bollinger_bands = tk.BooleanVar(value=strategy_defaults['use_bollinger_bands'])
        self.ft_use_stochastic = tk.BooleanVar(value=strategy_defaults['use_stochastic'])
        self.ft_use_atr = tk.BooleanVar(value=strategy_defaults['use_atr'])
        self.ft_use_trail_stop = tk.BooleanVar(value=risk_defaults['use_trail_stop'])

        self.ft_initial_capital = tk.StringVar(value=str(capital_defaults['initial_capital']))
        self.ft_symbol = tk.StringVar(value=instrument_defaults['symbol'])
        self.ft_exchange = tk.StringVar(value=instrument_defaults['exchange'])
        self.ft_feed_type = tk.StringVar(value=self.runtime_config.get('forward', {}).get('feed_type', 'Quote'))

        self.ft_session_start_hour = tk.StringVar(value=str(session_defaults['start_hour']))
        self.ft_session_start_min = tk.StringVar(value=str(session_defaults['start_min']))
        self.ft_session_end_hour = tk.StringVar(value=str(session_defaults['end_hour']))
        self.ft_session_end_min = tk.StringVar(value=str(session_defaults['end_min']))

    def _create_gui_framework(self):
        self.notebook = ttk.Notebook(self)
        self.bt_tab = ttk.Frame(self.notebook)
        self.ft_tab = ttk.Frame(self.notebook)
        self.log_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.bt_tab, text="Backtest")
        self.notebook.add(self.ft_tab, text="Forward Test")
        self.notebook.add(self.log_tab, text="Logs")
        self.notebook.pack(expand=1, fill="both")

    def _build_backtest_tab(self):
        frame = self.bt_tab
        frame.columnconfigure(1, weight=1)
        row = 0
        ttk.Label(frame, text="Data File (.csv, .log):").grid(row=row, column=0, sticky="e")
        ttk.Entry(frame, textvariable=self.bt_data_file, width=55).grid(row=row, column=1, padx=5, pady=5)
        ttk.Button(frame, text="Browse", command=self._bt_browse_csv).grid(row=row, column=2, padx=5, pady=5)
        row += 1
        ttk.Button(frame, text="Run Backtest", command=self._bt_run_backtest, style="Accent.TButton").grid(row=row, column=0, columnspan=3, pady=10)

    def _build_forward_test_tab(self):
        frame = self.ft_tab
        frame.columnconfigure(1, weight=1)
        row = 0

        ttk.Label(frame, text="Symbol Management", font=('Arial', 12, 'bold')).grid(row=row, column=0, columnspan=3, sticky="w", pady=(10,5))
        row += 1

        ttk.Button(frame, text="Refresh Symbol Cache", command=self._ft_refresh_cache).grid(row=row, column=0, pady=3)
        self.ft_cache_status = tk.StringVar(value="Cache not loaded")
        ttk.Label(frame, textvariable=self.ft_cache_status).grid(row=row, column=1, columnspan=2, sticky="w", padx=5)
        row += 1

        ttk.Label(frame, text="Exchange:").grid(row=row, column=0, sticky="e", padx=5, pady=2)
        ttk.Combobox(frame, textvariable=self.ft_exchange, values=["NSE_FO", "NSE_CM", "BSE_CM"], width=10, state='readonly').grid(row=row, column=1, sticky="w", padx=5, pady=2)
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

        ttk.Label(frame, text="Strategy Configuration", font=('Arial', 12, 'bold')).grid(row=row, column=0, columnspan=3, sticky="w", pady=(15,5))
        row += 1

        indicators_frame = ttk.Frame(frame)
        indicators_frame.grid(row=row, column=0, columnspan=3, sticky="w", padx=5, pady=2)

        ttk.Checkbutton(indicators_frame, text="EMA Crossover", variable=self.ft_use_ema_crossover).grid(row=0, column=0, sticky="w", padx=5)
        ttk.Checkbutton(indicators_frame, text="MACD", variable=self.ft_use_macd).grid(row=0, column=1, sticky="w", padx=5)
        ttk.Checkbutton(indicators_frame, text="VWAP", variable=self.ft_use_vwap).grid(row=0, column=2, sticky="w", padx=5)
        ttk.Checkbutton(indicators_frame, text="RSI Filter", variable=self.ft_use_rsi_filter).grid(row=0, column=3, sticky="w", padx=5)
        ttk.Checkbutton(indicators_frame, text="HTF Trend", variable=self.ft_use_htf_trend).grid(row=1, column=0, sticky="w", padx=5)
        ttk.Checkbutton(indicators_frame, text="Bollinger Bands", variable=self.ft_use_bollinger_bands).grid(row=1, column=1, sticky="w", padx=5)
        ttk.Checkbutton(indicators_frame, text="Stochastic", variable=self.ft_use_stochastic).grid(row=1, column=2, sticky="w", padx=5)
        ttk.Checkbutton(indicators_frame, text="ATR", variable=self.ft_use_atr).grid(row=1, column=3, sticky="w", padx=5)
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

        ttk.Label(frame, text="Capital Settings:", font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky="w", padx=5, pady=(10,2))
        row += 1
        capital_frame = ttk.Frame(frame)
        capital_frame.grid(row=row, column=0, columnspan=3, sticky="w", padx=5, pady=2)
        ttk.Label(capital_frame, text="Initial Capital:").grid(row=0, column=0, sticky="e", padx=2)
        ttk.Entry(capital_frame, textvariable=self.ft_initial_capital, width=14).grid(row=0, column=1, padx=2)
        row += 1

        ttk.Label(frame, text="Session Settings:", font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky="w", padx=5, pady=(10,2))
        row += 1
        session_frame = ttk.Frame(frame)
        session_frame.grid(row=row, column=0, columnspan=3, sticky="w", padx=5, pady=2)
        ttk.Entry(session_frame, textvariable=self.ft_session_start_hour, width=4).grid(row=0, column=1, padx=1)
        ttk.Entry(session_frame, textvariable=self.ft_session_start_min, width=4).grid(row=0, column=3, padx=1)
        ttk.Entry(session_frame, textvariable=self.ft_session_end_hour, width=4).grid(row=0, column=5, padx=1)
        ttk.Entry(session_frame, textvariable=self.ft_session_end_min, width=4).grid(row=0, column=7, padx=1)
        ttk.Checkbutton(session_frame, variable=self.bt_is_intraday).grid(row=1, column=1, sticky="w", padx=2)

        ttk.Button(frame, text="Start Forward Test", command=self._ft_run_forward_test).grid(row=row+2, column=0, pady=5)
        ttk.Button(frame, text="Stop", command=self._ft_stop_forward_test).grid(row=row+2, column=1, pady=5)
        self.ft_result_box = tk.Text(frame, height=16, width=110, state="disabled")
        self.ft_result_box.grid(row=row+3, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")
        frame.rowconfigure(row+3, weight=1)

    def _build_log_tab(self):
        frame = self.log_tab
        frame.columnconfigure(0, weight=1)
        ttk.Label(frame, text="Log File:").grid(row=0, column=0, sticky="e")
        ttk.Entry(frame, textvariable=self.log_file_var, width=55).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(frame, text="Open Log", command=self._open_log_file).grid(row=0, column=2, padx=5, pady=5)
        self.log_text = tk.Text(frame, height=20, state="disabled", wrap="word")
        self.log_text.grid(row=1, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")
        frame.rowconfigure(1, weight=1)
        self._load_log_file()

    # --- Utility and event handlers ---
    def _bt_browse_csv(self):
        path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv"), ("Log files", "*.log"), ("All files", "*.*")])
        if path:
            self.bt_data_file.set(path)

    def _bt_run_backtest(self):
        try:
            # validate externally before running; this is minimal wrapper
            config = self.build_config_from_gui()
            backtest = BacktestRunner(config=config)
            results = backtest.run()
            self.display_backtest_results(results)
            self.save_user_preferences()
        except Exception as e:
            logger.exception(f"Backtest failed: {e}")
            messagebox.showerror("Backtest Error", f"Failed to run backtest: {e}")

    def display_backtest_results(self, results):
        # placeholder - real implementation should populate GUI
        logger.info("Backtest completed")

    def _ft_refresh_cache(self):
        try:
            count = refresh_symbol_cache()
            self.ft_cache_status.set(f"Cache refreshed: {count} symbols loaded.")
            messagebox.showinfo("Cache Refreshed", f"Symbol cache updated successfully. Loaded {count} symbols.")
        except Exception as e:
            logger.exception(f"Cache refresh failed: {e}")
            self.ft_cache_status.set("Cache refresh failed")

    def _ft_load_symbols(self):
        try:
            filter_text = self.ft_symbol.get().strip()
            exchange = self.ft_exchange.get()
            all_symbols = load_symbol_cache() or []
            filtered = [s for s in all_symbols if s.startswith(exchange) and filter_text in s]
            self.ft_symbols_listbox.delete(0, tk.END)
            for s in filtered:
                self.ft_symbols_listbox.insert(tk.END, s)
            self.ft_cache_status.set(f"Loaded {len(filtered)} symbols")
        except Exception as e:
            logger.exception(f"Error loading symbols: {e}")

    def _ft_update_symbol_details(self, event):
        try:
            sel = self.ft_symbols_listbox.curselection()
            if not sel:
                return
            sym = self.ft_symbols_listbox.get(sel[0])
            token = self.symbol_token_map.get(sym, "")
            self.ft_token.set(token)
        except Exception:
            pass

    def _ft_run_forward_test(self):
        try:
            selected = [self.ft_symbols_listbox.get(i) for i in self.ft_symbols_listbox.curselection()]
            if not selected:
                messagebox.showerror("No Symbol Selected", "Please select at least one symbol to test")
                return
            if not messagebox.askyesno("Confirm Forward Test", "Start forward test with selected symbols?"):
                return
            self._set_forward_test_controls_state(tk.DISABLED)
            self._forward_thread = threading.Thread(target=self._run_forward_test_process, args=(selected,), daemon=True)
            self._forward_thread.start()
            messagebox.showinfo("Forward Test Started", "Forward test started in background.")
        except Exception as e:
            logger.exception(f"Error starting forward test: {e}")
            messagebox.showerror("Forward Test Error", f"Failed to start forward test: {e}")

    def _run_forward_test_process(self, symbols):
        try:
            for symbol in symbols:
                if not symbol.strip():
                    continue
                logger.info(f"Processing forward test symbol: {symbol}")
                # placeholder: integrate forward tester
                import time
                time.sleep(0.5)
            logger.info("Forward test process completed")
        except Exception:
            logger.exception("Error during forward test")
        finally:
            self._set_forward_test_controls_state(tk.NORMAL)

    def _set_forward_test_controls_state(self, state):
        widgets = [
            self.ft_symbol_entry, self.ft_exchange, self.ft_symbols_listbox,
            self.ft_token, self.ft_feed_type, self.ft_fast_ema, self.ft_slow_ema,
            self.ft_macd_fast, self.ft_macd_slow, self.ft_macd_signal, self.ft_rsi_length,
            self.ft_rsi_oversold, self.ft_rsi_overbought, self.ft_htf_period,
            self.ft_base_sl_points, self.ft_tp_points[0], self.ft_tp_points[1],
            self.ft_tp_points[2], self.ft_tp_points[3], self.ft_use_trail_stop,
            self.ft_trail_activation_points, self.ft_trail_distance_points, self.ft_risk_per_trade_percent,
            self.ft_initial_capital, self.ft_session_start_hour, self.ft_session_start_min,
            self.ft_session_end_hour, self.ft_session_end_min
        ]
        for w in widgets:
            try:
                w.configure(state=state)
            except Exception:
                pass

    def _ft_stop_forward_test(self):
        try:
            if self._forward_thread and self._forward_thread.is_alive():
                # implement proper shutdown flag in long-running worker
                self._forward_thread.join(timeout=3)
        except Exception:
            logger.exception("Error stopping forward test")

    def _open_log_file(self):
        log_file = self.log_file_var.get()
        if os.path.exists(log_file):
            os.startfile(log_file)

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
        except Exception:
            pass

    def _merge_user_preferences_into_runtime_config(self):
        prefs_file = "user_preferences.json"
        if os.path.exists(prefs_file):
            try:
                with open(prefs_file, 'r') as f:
                    prefs = json.load(f)
                for section, params in prefs.items():
                    if section in self.runtime_config and isinstance(params, dict):
                        self.runtime_config[section].update(params)
                logger.info("User preferences merged into runtime config")
            except Exception:
                logger.exception("Failed to merge user preferences")

    def build_config_from_gui(self):
        config = create_config_from_defaults()
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

        config['risk']['base_sl_points'] = float(self.bt_base_sl_points.get())
        config['risk']['use_trail_stop'] = self.bt_use_trail_stop.get()
        config['risk']['trail_activation_points'] = float(self.bt_trail_activation.get())
        config['risk']['trail_distance_points'] = float(self.bt_trail_distance.get())
        config['risk']['tp_points'] = [float(var.get()) for var in self.bt_tp_points]
        config['risk']['tp_percents'] = [float(var.get())/100.0 for var in self.bt_tp_percents]

        config['capital']['initial_capital'] = float(self.bt_initial_capital.get())

        config['instrument']['symbol'] = self.bt_symbol.get()
        config['instrument']['exchange'] = self.bt_exchange.get()
        config['instrument']['lot_size'] = int(self.bt_lot_size.get())

        config['session']['is_intraday'] = self.bt_is_intraday.get()
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
# ...existing code...
def main():
    try:
        app = UnifiedTradingGUI()
        app.mainloop()
    except Exception as e:
        print(f"Failed to start GUI application: {e}")


if __name__ == "__main__":
    main()