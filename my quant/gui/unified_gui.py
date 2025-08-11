"""
gui/unified_gui.py

Unified GUI for both Backtest and Forward (Live) Test modes:
- Tab 1: Backtest mode (CSV selection, config, run backtest, show results)
- Tab 2: Forward Test mode (SmartAPI login, manual symbol cache refresh, symbol/feed select, start/stop simulated live)
- Tab 3: Status/Logs (view latest logs and info)

All orders are simulated; no real trading occurs in this GUI.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
from datetime import datetime
import logging
import yaml

from backtest.backtest_runner import run_backtest
from live.trader import LiveTrader
from utils.cache_manager import load_symbol_cache, refresh_symbol_cache, get_token_for_symbol
from utils.simple_loader import load_data_simple
from utils.time_utils import now_ist

LOG_FILENAME = "unified_gui.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)8s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILENAME, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class UnifiedTradingGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Unified Quantitative Trading System")
        self.geometry("950x700")
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.tabControl = ttk.Notebook(self)
        self.tab_backtest = ttk.Frame(self.tabControl)
        self.tab_forward = ttk.Frame(self.tabControl)
        self.tab_status = ttk.Frame(self.tabControl)

        self.tabControl.add(self.tab_backtest, text="Backtest")
        self.tabControl.add(self.tab_forward, text="Forward Test")
        self.tabControl.add(self.tab_status, text="Status / Logs")
        self.tabControl.pack(expand=1, fill="both")

        self._build_backtest_tab()
        self._build_forward_test_tab()
        self._build_status_tab()

        self._backtest_thread = None
        self._forward_thread = None
        self.symbol_token_map = {}  # Initialize simple symbol-to-token mapping

        self.capital_usable = tk.StringVar(value="₹0 (0%)")
        self.max_lots = tk.StringVar(value="0 lots (0 shares)")
        self.max_risk = tk.StringVar(value="₹0 (0%)")
        self.recommended_lots = tk.StringVar(value="0 lots (0 shares)")

        # Session configuration variables
        self.session_start_hour = tk.StringVar(value="9")
        self.session_start_min = tk.StringVar(value="15")
        self.session_end_hour = tk.StringVar(value="15")
        self.session_end_min = tk.StringVar(value="30")
        self.start_buffer = tk.StringVar(value="5")
        self.end_buffer = tk.StringVar(value="20")
        self.timezone = tk.StringVar(value="Asia/Kolkata")
        self.session_status = tk.StringVar(value="⚠️ Not checked")

    # --- Backtest Tab ---
    def _build_backtest_tab(self):
        frame = self.tab_backtest
        frame.columnconfigure(1, weight=1)
        row = 0
        
        ttk.Label(frame, text="Data File (.csv, .log):").grid(row=row, column=0, sticky="e")
        self.bt_data_file = tk.StringVar()
        ttk.Entry(frame, textvariable=self.bt_data_file, width=55).grid(row=row, column=1, padx=5, pady=5)
        ttk.Button(frame, text="Browse", command=self._bt_browse_csv).grid(row=row, column=2, padx=5, pady=5)
        row += 1

        # Strategy Configuration for Backtest
        ttk.Label(frame, text="Strategy Configuration", font=('Arial', 12, 'bold')).grid(row=row, column=0, columnspan=3, sticky="w", pady=(15,5))
        row += 1

        # Indicator Toggles
        ttk.Label(frame, text="Indicators:", font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky="w", padx=5, pady=2)
        row += 1
        
        bt_indicators_frame = ttk.Frame(frame)
        bt_indicators_frame.grid(row=row, column=0, columnspan=3, sticky="w", padx=5, pady=2)
        
        self.bt_use_ema_crossover = tk.BooleanVar(value=True)
        self.bt_use_macd = tk.BooleanVar(value=True)
        self.bt_use_vwap = tk.BooleanVar(value=True)
        self.bt_use_rsi_filter = tk.BooleanVar(value=False)
        self.bt_use_htf_trend = tk.BooleanVar(value=True)
        self.bt_use_bollinger_bands = tk.BooleanVar(value=False)
        self.bt_use_stochastic = tk.BooleanVar(value=False)
        self.bt_use_atr = tk.BooleanVar(value=True)
        
        ttk.Checkbutton(bt_indicators_frame, text="EMA Crossover", variable=self.bt_use_ema_crossover).grid(row=0, column=0, sticky="w", padx=5)
        ttk.Checkbutton(bt_indicators_frame, text="MACD", variable=self.bt_use_macd).grid(row=0, column=1, sticky="w", padx=5)
        ttk.Checkbutton(bt_indicators_frame, text="VWAP", variable=self.bt_use_vwap).grid(row=0, column=2, sticky="w", padx=5)
        ttk.Checkbutton(bt_indicators_frame, text="RSI Filter", variable=self.bt_use_rsi_filter).grid(row=0, column=3, sticky="w", padx=5)
        ttk.Checkbutton(bt_indicators_frame, text="HTF Trend", variable=self.bt_use_htf_trend).grid(row=1, column=0, sticky="w", padx=5)
        ttk.Checkbutton(bt_indicators_frame, text="Bollinger Bands", variable=self.bt_use_bollinger_bands).grid(row=1, column=1, sticky="w", padx=5)
        ttk.Checkbutton(bt_indicators_frame, text="Stochastic", variable=self.bt_use_stochastic).grid(row=1, column=2, sticky="w", padx=5)
        ttk.Checkbutton(bt_indicators_frame, text="ATR", variable=self.bt_use_atr).grid(row=1, column=3, sticky="w", padx=5)
        row += 1

        # --- Strategy version selector ---------------------------------
        ttk.Label(frame, text="Strategy Version:", font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky="w", padx=5, pady=(10,2))
        row += 1

        self.bt_strategy_version = tk.StringVar(value="research")   # default for backtest
        ttk.Combobox(frame,
                     textvariable=self.bt_strategy_version,
                     values=["research", "live"],
                     width=12,
                     state="readonly").grid(row=row, column=0, sticky="w", padx=5, pady=2)
        row += 1

        # Parameters
        ttk.Label(frame, text="Parameters:", font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky="w", padx=5, pady=(10,2))
        row += 1
        
        self.bt_param_frame = ttk.LabelFrame(self.bt_tab, text="Parameters")
        self.bt_param_frame.grid(row=row, column=0, columnspan=3, sticky="w", padx=5, pady=2)
        
        bt_params_frame = ttk.Frame(frame)
        bt_params_frame.grid(row=row, column=0, columnspan=3, sticky="w", padx=5, pady=2)
        
        # EMA Parameters
        ttk.Label(bt_params_frame, text="Fast EMA:").grid(row=0, column=0, sticky="e", padx=2)
        self.bt_fast_ema = tk.StringVar(value="9")
        ttk.Entry(bt_params_frame, textvariable=self.bt_fast_ema, width=8).grid(row=0, column=1, padx=2)
        
        ttk.Label(bt_params_frame, text="Slow EMA:").grid(row=0, column=2, sticky="e", padx=2)
        self.bt_slow_ema = tk.StringVar(value="21")
        ttk.Entry(bt_params_frame, textvariable=self.bt_slow_ema, width=8).grid(row=0, column=3, padx=2)
 
         # MACD Parameters
        ttk.Label(bt_params_frame, text="MACD Fast:").grid(row=1, column=0, sticky="e", padx=2)
        self.bt_macd_fast = tk.StringVar(value="12")
        ttk.Entry(bt_params_frame, textvariable=self.bt_macd_fast, width=8).grid(row=1, column=1, padx=2)
        
        ttk.Label(bt_params_frame, text="MACD Slow:").grid(row=1, column=2, sticky="e", padx=2)
        self.bt_macd_slow = tk.StringVar(value="26")
        ttk.Entry(bt_params_frame, textvariable=self.bt_macd_slow, width=8).grid(row=1, column=3, padx=2)
        
        ttk.Label(bt_params_frame, text="MACD Signal:").grid(row=1, column=4, sticky="e", padx=2)
        self.bt_macd_signal = tk.StringVar(value="9")
        ttk.Entry(bt_params_frame, textvariable=self.bt_macd_signal, width=8).grid(row=1, column=5, padx=2)
        
        # RSI Parameters
        ttk.Label(bt_params_frame, text="RSI Length:").grid(row=2, column=0, sticky="e", padx=2)
        self.bt_rsi_length = tk.StringVar(value="14")
        ttk.Entry(bt_params_frame, textvariable=self.bt_rsi_length, width=8).grid(row=2, column=1, padx=2)
        
        ttk.Label(bt_params_frame, text="RSI Oversold:").grid(row=2, column=2, sticky="e", padx=2)
        self.bt_rsi_oversold = tk.StringVar(value="30")
        ttk.Entry(bt_params_frame, textvariable=self.bt_rsi_oversold, width=8).grid(row=2, column=3, padx=2)
        
        ttk.Label(bt_params_frame, text="RSI Overbought:").grid(row=2, column=4, sticky="e", padx=2)
        self.bt_rsi_overbought = tk.StringVar(value="70")
        ttk.Entry(bt_params_frame, textvariable=self.bt_rsi_overbought, width=8).grid(row=2, column=5, padx=2)
        
        # HTF Parameters
        ttk.Label(bt_params_frame, text="HTF Period:").grid(row=3, column=0, sticky="e", padx=2)
        self.bt_htf_period = tk.StringVar(value="20")
        ttk.Entry(bt_params_frame, textvariable=self.bt_htf_period, width=8).grid(row=3, column=1, padx=2)
        row += 1

        # Risk Management
        ttk.Label(frame, text="Risk Management:", font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky="w", padx=5, pady=(10,2))
        row += 1
        
        bt_risk_frame = ttk.Frame(frame)
        bt_risk_frame.grid(row=row, column=0, columnspan=3, sticky="w", padx=5, pady=2)
        
        ttk.Label(bt_risk_frame, text="Stop Loss Points:").grid(row=0, column=0, sticky="e", padx=2)
        self.bt_base_sl_points = tk.StringVar(value="15")
        ttk.Entry(bt_risk_frame, textvariable=self.bt_base_sl_points, width=8).grid(row=0, column=1, padx=2)
        
        ttk.Label(bt_risk_frame, text="TP1 Points:").grid(row=0, column=2, sticky="e", padx=2)
        self.bt_tp1_points = tk.StringVar(value="10")
        ttk.Entry(bt_risk_frame, textvariable=self.bt_tp1_points, width=8).grid(row=0, column=3, padx=2)
        
        ttk.Label(bt_risk_frame, text="TP2 Points:").grid(row=0, column=4, sticky="e", padx=2)
        self.bt_tp2_points = tk.StringVar(value="25")
        ttk.Entry(bt_risk_frame, textvariable=self.bt_tp2_points, width=8).grid(row=0, column=5, padx=2)
        
        ttk.Label(bt_risk_frame, text="TP3 Points:").grid(row=1, column=0, sticky="e", padx=2)
        self.bt_tp3_points = tk.StringVar(value="50")
        ttk.Entry(bt_risk_frame, textvariable=self.bt_tp3_points, width=8).grid(row=1, column=1, padx=2)
        
        ttk.Label(bt_risk_frame, text="TP4 Points:").grid(row=1, column=2, sticky="e", padx=2)
        self.bt_tp4_points = tk.StringVar(value="100")
        ttk.Entry(bt_risk_frame, textvariable=self.bt_tp4_points, width=8).grid(row=1, column=3, padx=2)
        
        self.bt_use_trail_stop = tk.BooleanVar(value=True)
        ttk.Checkbutton(bt_risk_frame, text="Use Trailing Stop", variable=self.bt_use_trail_stop).grid(row=1, column=4, columnspan=2, sticky="w", padx=5)
        
        ttk.Label(bt_risk_frame, text="Trail Activation Points:").grid(row=2, column=0, sticky="e", padx=2)
        self.bt_trail_activation_points = tk.StringVar(value="25")
        ttk.Entry(bt_risk_frame, textvariable=self.bt_trail_activation_points, width=8).grid(row=2, column=1, padx=2)
        
        ttk.Label(bt_risk_frame, text="Trail Distance Points:").grid(row=2, column=2, sticky="e", padx=2)
        self.bt_trail_distance_points = tk.StringVar(value="10")
        ttk.Entry(bt_risk_frame, textvariable=self.bt_trail_distance_points, width=8).grid(row=2, column=3, padx=2)
        
        ttk.Label(bt_risk_frame, text="Risk % per Trade:").grid(row=2, column=4, sticky="e", padx=2)
        self.bt_risk_per_trade_percent = tk.StringVar(value="1.0")
        ttk.Entry(bt_risk_frame, textvariable=self.bt_risk_per_trade_percent, width=8).grid(row=2, column=5, padx=2)
        
        ttk.Label(bt_risk_frame, text="Initial Capital:").grid(row=3, column=0, sticky="e", padx=2)
        self.bt_initial_capital = tk.StringVar(value="100000")
        ttk.Entry(bt_risk_frame, textvariable=self.bt_initial_capital, width=12).grid(row=3, column=1, padx=2)
        row += 1

        # Add instrument panel before capital management
        row = self._build_instrument_panel(frame, row)

        # Add session timing panel between instrument panel and capital management
        row = self._build_session_timing_panel(frame, row)

        # Add capital management panel after risk management
        row = self._build_capital_management_panel(frame, row)

        ttk.Button(frame, text="Run Backtest", command=self._bt_run_backtest).grid(row=row, column=0, columnspan=3, pady=10)
        row += 1

        self.bt_result_box = tk.Text(frame, height=20, state="disabled", wrap="word")
        self.bt_result_box.grid(row=row, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")
        frame.rowconfigure(row, weight=1)

    def _build_capital_management_panel(self, frame, row):
        """Build comprehensive capital management panel"""
        
        # Capital Management Header
        ttk.Label(frame, text="Capital Management:", font=('Arial', 10, 'bold')).grid(
            row=row, column=0, sticky="w", padx=5, pady=(10,2)
        )
        row += 1
        
        capital_frame = ttk.Frame(frame)
        capital_frame.grid(row=row, column=0, columnspan=3, sticky="w", padx=5, pady=2)
        
        # User Input Fields
        ttk.Label(capital_frame, text="Available Capital:").grid(row=0, column=0, sticky="e", padx=2)
        self.bt_available_capital = tk.StringVar(value="100000")
        capital_entry = ttk.Entry(capital_frame, textvariable=self.bt_available_capital, width=12)
        capital_entry.grid(row=0, column=1, padx=2)
        capital_entry.bind('<KeyRelease>', self._update_capital_calculations)
        
        ttk.Label(capital_frame, text="Risk % per Trade:").grid(row=0, column=2, sticky="e", padx=2)
        self.bt_risk_percentage = tk.StringVar(value="1.0")
        risk_entry = ttk.Entry(capital_frame, textvariable=self.bt_risk_percentage, width=8)
        risk_entry.grid(row=0, column=3, padx=2)
        risk_entry.bind('<KeyRelease>', self._update_capital_calculations)
        
        # Instrument Configuration
        ttk.Label(capital_frame, text="Lot Size:").grid(row=1, column=0, sticky="e", padx=2)
        self.bt_lot_size = tk.StringVar(value="75")  # NIFTY default
        lot_entry = ttk.Entry(capital_frame, textvariable=self.bt_lot_size, width=8)
        lot_entry.grid(row=1, column=1, padx=2)
        lot_entry.bind('<KeyRelease>', self._update_capital_calculations)
        
        ttk.Label(capital_frame, text="Price per Unit:").grid(row=1, column=2, sticky="e", padx=2)
        self.bt_current_price = tk.StringVar(value="154.00")  # Sample price
        price_entry = ttk.Entry(capital_frame, textvariable=self.bt_current_price, width=8)
        price_entry.grid(row=1, column=3, padx=2)
        price_entry.bind('<KeyRelease>', self._update_capital_calculations)
        
        # Real-time Capital Display (Read-only)
        display_frame = ttk.LabelFrame(capital_frame, text="Capital Analysis", padding=5)
        display_frame.grid(row=2, column=0, columnspan=4, sticky="ew", pady=(10,0))
        
        # Capital Usage Display
        self.capital_usable = tk.StringVar(value="₹95,000 (95%)")
        ttk.Label(display_frame, text="Capital Usable:").grid(row=0, column=0, sticky="w")
        ttk.Label(display_frame, textvariable=self.capital_usable, foreground="blue").grid(
            row=0, column=1, sticky="w", padx=10
        )
        
        self.max_lots = tk.StringVar(value="8 lots (600 shares)")
        ttk.Label(display_frame, text="Max Affordable Lots:").grid(row=0, column=2, sticky="w", padx=10)
        ttk.Label(display_frame, textvariable=self.max_lots, foreground="green").grid(
            row=0, column=3, sticky="w", padx=10
        )
        
        self.max_risk = tk.StringVar(value="₹1,000 (1%)")
        ttk.Label(display_frame, text="Max Capital at Risk:").grid(row=1, column=0, sticky="w")
        ttk.Label(display_frame, textvariable=self.max_risk, foreground="red").grid(
            row=1, column=1, sticky="w", padx=10
        )
        
        self.recommended_lots = tk.StringVar(value="1 lot (75 shares)")
        ttk.Label(display_frame, text="Recommended Position:").grid(row=1, column=2, sticky="w", padx=10)
        ttk.Label(display_frame, textvariable=self.recommended_lots, foreground="purple").grid(
            row=1, column=3, sticky="w", padx=10
        )
        
        return row + 1

    def _bt_browse_csv(self):
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
        """Run backtest with proper nested configuration structure"""
        if not self.bt_data_file.get():
            messagebox.showerror("Error", "Please select a data file")
            return
        
        if self._backtest_thread and self._backtest_thread.is_alive():
            messagebox.showwarning("Warning", "Backtest already running")
            return

        # FIXED: Build proper nested configuration structure
        gui_config = {
            # === STRATEGY SECTION ===
            'strategy': {
                'strategy_version': self.bt_strategy_version.get(),
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
                'rsi_oversold': int(self.bt_rsi_oversold.get()),
                'rsi_overbought': int(self.bt_rsi_overbought.get()),
                'htf_period': int(self.bt_htf_period.get()),
                'indicator_update_mode': 'tick'
            },
            
            # === RISK MANAGEMENT SECTION ===
            'risk': {
                'base_sl_points': float(self.bt_base_sl_points.get()),
                'tp_points': [
                    float(self.bt_tp1_points.get()),
                    float(self.bt_tp2_points.get()),
                    float(self.bt_tp3_points.get()),
                    float(self.bt_tp4_points.get())
                ],
                'tp_percents': [0.25, 0.25, 0.25, 0.25],
                'use_trail_stop': self.bt_use_trail_stop.get(),
                'trail_activation_points': float(self.bt_trail_activation_points.get()),
                'trail_distance_points': float(self.bt_trail_distance_points.get()),
                'risk_per_trade_percent': float(self.bt_risk_per_trade_percent.get()),
                'commission_percent': 0.03,
                'commission_per_trade': 0.0
            },
            
            # === CAPITAL SECTION ===
            'capital': {
                'initial_capital': float(self.bt_initial_capital.get())
            },
            
            # === INSTRUMENT SECTION ===
            'instrument': {
                'symbol': self.bt_instrument_type.get(),
                'exchange': 'NSE_FO',
                'lot_size': int(self.bt_lot_size.get()),
                'tick_size': 0.05,
                'product_type': 'INTRADAY'
            },
            
            # === SESSION SECTION ===
            'session': {
                'is_intraday': True,
                'start_hour': int(self.session_start_hour.get()),
                'start_min': int(self.session_start_min.get()),
                'end_hour': int(self.session_end_hour.get()),
                'end_min': int(self.session_end_min.get()),
                'start_buffer_minutes': int(self.start_buffer.get()),
                'end_buffer_minutes': int(self.end_buffer.get()),
                'timezone': self.timezone.get()
            },
            
            # === BACKTEST SECTION ===
            'backtest': {
                'max_drawdown_pct': 0,
                'allow_short': False,
                'close_at_session_end': True,
                'save_results': True,
                'results_dir': 'backtest_results',
                'log_level': 'INFO'
            }
        }

        logger.info(f"Config being sent: {gui_config}")
 
        try:
            self.bt_result_box.config(state="normal")
            self.bt_result_box.delete(1.0, tk.END)
            
            # Validate configuration structure before running
            self._validate_nested_config(gui_config)
            logger.info("Using nested configuration structure for backtest")
            
            from backtest.backtest_runner import run_backtest
            
            logger.info("Starting backtest execution...")
            trades_df, metrics = run_backtest(gui_config, self.bt_data_file.get())
            
            # Display results in the text box
            self.bt_result_box.insert(tk.END, "Backtest completed successfully!\n")
            self.bt_result_box.insert(tk.END, f"Total Trades: {metrics['total_trades']}\n")
            self.bt_result_box.insert(tk.END, f"Winning Trades: {metrics['winning_trades']}\n")
            self.bt_result_box.insert(tk.END, f"Losing Trades: {metrics['losing_trades']}\n")
            self.bt_result_box.insert(tk.END, f"Total Profit/Loss: ₹{metrics['total_pnl']:.2f}\n")
            self.bt_result_box.insert(tk.END, f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}\n")
            self.bt_result_box.insert(tk.END, f"Max Drawdown: {metrics['max_drawdown']:.2f}%\n")
            self.bt_result_box.insert(tk.END, "Trade metrics saved to 'trade_metrics.csv'\n")
            
            # Enable the result box for user interaction
            self.bt_result_box.config(state="normal")
        except Exception as e:
            logger.error(f"Error in backtest execution: {e}")
            messagebox.showerror("Backtest Error", f"An error occurred during backtest: {e}")

    def _validate_nested_config(self, config):
        """Validate that the configuration has the expected nested structure"""
        required_sections = ['strategy', 'risk', 'capital', 'instrument', 'session', 'backtest']
        missing_sections = [section for section in required_sections if section not in config]
        
        if missing_sections:
            raise ValueError(f"Missing configuration sections: {missing_sections}")
        
        # Log validation success
        logger.info(f"Configuration validation passed - all required sections present")
        return True

    # --- Forward Test Tab ---
    def _build_forward_test_tab(self):
        frame = self.tab_forward
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

        # --- Strategy version selector ---------------------------------
        ttk.Label(frame, text="Strategy Version:", font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky="w", padx=5, pady=(10,2))
        row += 1

        self.ft_strategy_version = tk.StringVar(value="live")       # default for forward test
        ttk.Combobox(frame,
                     textvariable=self.ft_strategy_version,
                     values=["research", "live"],
                     width=12,
                     state="readonly").grid(row=row, column=0, sticky="w", padx=5, pady=2)
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
        self.ft_tp1_points = tk.StringVar(value="10")
        ttk.Entry(risk_frame, textvariable=self.ft_tp1_points, width=8).grid(row=0, column=3, padx=2)
        
        ttk.Label(risk_frame, text="TP2 Points:").grid(row=0, column=4, sticky="e", padx=2)
        self.ft_tp2_points = tk.StringVar(value="25")
        ttk.Entry(risk_frame, textvariable=self.ft_tp2_points, width=8).grid(row=0, column=5, padx=2)
        
        ttk.Label(risk_frame, text="TP3 Points:").grid(row=1, column=0, sticky="e", padx=2)
        self.ft_tp3_points = tk.StringVar(value="50")
        ttk.Entry(risk_frame, textvariable=self.ft_tp3_points, width=8).grid(row=1, column=1, padx=2)
        
        ttk.Label(risk_frame, text="TP4 Points:").grid(row=1, column=2, sticky="e", padx=2)
        self.ft_tp4_points = tk.StringVar(value="100")
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
        
        ttk.Label(risk_frame, text="Initial Capital:").grid(row=3, column=0, sticky="e", padx=2)
        self.ft_initial_capital = tk.StringVar(value="100000")
        ttk.Entry(risk_frame, textvariable=self.ft_initial_capital, width=12).grid(row=3, column=1, padx=2)
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
            
            self.ft_cache_status.set(f"Cache loaded: {len(symbols)} symbols")
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
                'strategy_version': self.ft_strategy_version.get(),
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
                'indicator_update_mode': 'tick'
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
                'start_hour': int(self.session_start_hour.get()),
                'start_min': int(self.session_start_min.get()),
                'end_hour': int(self.session_end_hour.get()),
                'end_min': int(self.session_end_min.get()),
                'start_buffer_minutes': int(self.start_buffer.get()),
                'end_buffer_minutes': int(self.end_buffer.get()),
                'timezone': self.timezone.get()
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
                'max_drawdown_pct': 0,
                'allow_short': False,
                'close_at_session_end': True,
                'save_results': True,
                'results_dir': 'forward_test_results',
                'log_level': 'INFO'
            }
        }

        # Validate configuration structure
        self._validate_nested_config(gui_config)
        logger.info("Using nested configuration structure for forward test")
        logger.info(f"Forward test config: {gui_config}")

        try:
            self.ft_result_box.config(state="normal")
            self.ft_result_box.delete("1.0", "end")
            self.ft_result_box.insert("end", f"Starting forward test for {gui_config['instrument']['symbol']}...\n")
            self.ft_result_box.config(state="disabled")

            trader = LiveTrader(config_dict=gui_config)
            self._forward_thread = threading.Thread(target=trader.start)
            self._forward_thread.start()
        except Exception as e:
            logger.error(f"Error starting forward test: {e}")
            messagebox.showerror("Forward Test Error", f"Failed to start forward test: {str(e)}")

    def _ft_stop_forward_test(self):
        messagebox.showinfo("Stop", "Forward test stop functionality not yet implemented.")

    # --- Status Tab ---
    def _build_status_tab(self):
        frame = self.tab_status
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
            "=" * 50 + "\n\n"
            "✅ System Status: Ready\n"
            "🔒 Trading Mode: Simulation Only (No Real Orders)\n"
            "📊 Available Modes: Backtest & Forward Test\n\n"
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
        """Update all capital calculations in real-time"""
        try:
            # Get user inputs
            available_capital = float(self.bt_available_capital.get().replace(',', ''))
            risk_percentage = float(self.bt_risk_percentage.get())
            lot_size = int(self.bt_lot_size.get())
            current_price = float(self.bt_current_price.get())
            stop_loss_points = float(self.bt_base_sl_points.get())
            
            # Calculate usable capital (95% rule)
            usable_capital = available_capital * 0.95
            self.capital_usable.set(f"₹{usable_capital:,.0f} ({usable_capital/available_capital*100:.0f}%)")
            
            # Calculate maximum affordable lots
            max_affordable_shares = int(usable_capital / current_price)
            max_lots_count = max_affordable_shares // lot_size
            max_lots_shares = max_lots_count * lot_size
            self.max_lots.set(f"{max_lots_count} lots ({max_lots_shares:,} shares)")
            
            # Calculate risk-based position sizing
            max_risk_amount = available_capital * (risk_percentage / 100)
            risk_per_share = stop_loss_points
            risk_based_shares = int(max_risk_amount / risk_per_share) if risk_per_share > 0 else 0
            risk_based_lots = risk_based_shares // lot_size
            
            # Choose the smaller (more conservative) approach
            recommended_lots_count = min(max_lots_count, risk_based_lots)
            recommended_shares = recommended_lots_count * lot_size
            
            self.max_risk.set(f"₹{max_risk_amount:,.0f} ({risk_percentage}%)")
            self.recommended_lots.set(f"{recommended_lots_count} lots ({recommended_shares:,} shares)")
            
        except (ValueError, ZeroDivisionError):
            # Handle invalid inputs gracefully
            self.capital_usable.set("Invalid Input")
            self.max_lots.set("Invalid Input")
            self.max_risk.set("Invalid Input") 
            self.recommended_lots.set("Invalid Input")

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
                errors.append("Minimum capital requirement: ₹10,000")
            
            # Risk validation
            if risk_pct < 0.1:
                warnings.append("Very low risk percentage may limit trading opportunities")
            elif risk_pct > 5.0:
                warnings.append("Risk percentage above 5% is aggressive")
            
            # Position size validation
            min_position_value = lot_size * price
            if min_position_value > capital * 0.95:
                errors.append(f"Insufficient capital for even 1 lot (₹{min_position_value:,.0f} required)")
            
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
            "CUSTOM": 75  # Default for custom
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
                    "\n".join([f"• {w}" for w in warnings]) + 
                    f"\n\nEffective trading window: {effective_minutes} minutes" +
                    "\n\nDo you want to use this configuration anyway?"
                )
                
                if result:  # User confirmed
                    self._apply_session_config(start_hour, start_min, end_hour, end_min, 
                                             start_buffer, end_buffer)
                    self.session_status.set("⚠️ Using with warnings")
                else:
                    self.session_status.set("⚠️ Review recommended")
            else:
                self._apply_session_config(start_hour, start_min, end_hour, end_min, 
                                         start_buffer, end_buffer)
                self.session_status.set("✅ Configuration looks good")
                
        except ValueError:
            messagebox.showwarning("Input Error", "Please enter valid numbers")
            self.session_status.set("⚠️ Invalid number format")
    
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
if __name__ == "__main__":
    app = UnifiedTradingGUI()
    app.mainloop()
