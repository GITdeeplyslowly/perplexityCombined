# Fixed unified_gui_diff.py with all syntax errors and missing imports resolved

import os
import json
import logging
import tkinter as tk
from tkinter import ttk
from typing import Dict, Any

# Configure logging
logger = logging.getLogger(__name__)

# Placeholder function for create_config_from_defaults
def create_config_from_defaults():
    """Create default configuration"""
    return {
        'risk_management': {
            'max_position_size': 0.1,
            'stop_loss_pct': 0.02,
            'take_profit_pct': 0.04,
            'max_drawdown_pct': 0.05
        }
    }

class UnifiedGUI:
    def __init__(self):
        self.config = create_config_from_defaults()
        self.setup_gui()
    
    def load_config(self):
        """Load configuration from file"""
        config_file = "config.json"
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    loaded_config = json.load(f)
                    self.config.update(loaded_config)
                    logger.info(f"Configuration loaded from {config_file}")
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
        else:
            logger.info("Config file not found, using defaults")

    def setup_gui(self):
        """Setup the main GUI window"""
        self.root = tk.Tk()
        self.root.title("Trading Strategy GUI")
        self.root.geometry("800x600")
        
        # Create main frame
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Setup tabs
        self.setup_risk_management_tab()
        self.setup_trading_tab()
        self.setup_analysis_tab()
        
        # Control buttons frame
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Buttons
        save_btn = tk.Button(button_frame, text="Save Config", command=self.save_config)
        save_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        load_btn = tk.Button(button_frame, text="Load Config", command=self.load_config)
        load_btn.pack(side=tk.LEFT, padx=5)
        
        start_btn = tk.Button(button_frame, text="Start Strategy", command=self.start_strategy)
        start_btn.pack(side=tk.RIGHT)

    def setup_risk_management_tab(self):
        """Setup risk management configuration tab"""
        risk_frame = ttk.Frame(self.notebook)
        self.notebook.add(risk_frame, text="Risk Management")
        
        # Risk management variables
        self.max_position_var = tk.DoubleVar(value=self.config['risk_management']['max_position_size'])
        self.stop_loss_var = tk.DoubleVar(value=self.config['risk_management']['stop_loss_pct'])
        self.take_profit_var = tk.DoubleVar(value=self.config['risk_management']['take_profit_pct'])
        self.max_drawdown_var = tk.DoubleVar(value=self.config['risk_management']['max_drawdown_pct'])
        
        # Create labels and entries - FIXED SYNTAX ERRORS
        ttk.Label(risk_frame, text="Max Position Size:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(risk_frame, textvariable=self.max_position_var).grid(row=0, column=1, pady=5, padx=10)
        
        ttk.Label(risk_frame, text="Stop Loss %:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(risk_frame, textvariable=self.stop_loss_var).grid(row=1, column=1, pady=5, padx=10)
        
        ttk.Label(risk_frame, text="Take Profit %:").grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Entry(risk_frame, textvariable=self.take_profit_var).grid(row=2, column=1, pady=5, padx=10)
        
        ttk.Label(risk_frame, text="Max Drawdown %:").grid(row=3, column=0, sticky=tk.W, pady=5)
        ttk.Entry(risk_frame, textvariable=self.max_drawdown_var).grid(row=3, column=1, pady=5, padx=10)

        # These were the problematic lines 129-134 - now properly formatted as regular assignments
        max_position_entry = ttk.Entry(risk_frame, textvariable=self.max_position_var)
        stop_loss_entry = ttk.Entry(risk_frame, textvariable=self.stop_loss_var)
        take_profit_entry = ttk.Entry(risk_frame, textvariable=self.take_profit_var)
        max_drawdown_entry = ttk.Entry(risk_frame, textvariable=self.max_drawdown_var)
        position_size_label = ttk.Label(risk_frame, text="Position Size:")
        drawdown_label = ttk.Label(risk_frame, text="Max Drawdown:")
        
        # Grid the widgets
        max_position_entry.grid(row=4, column=1, pady=5)
        stop_loss_entry.grid(row=5, column=1, pady=5)
        
    def setup_trading_tab(self):
        """Setup trading configuration tab"""
        trading_frame = ttk.Frame(self.notebook)
        self.notebook.add(trading_frame, text="Trading")
        
        # Trading configuration widgets
        ttk.Label(trading_frame, text="Trading Parameters").pack(pady=10)
        
    def setup_analysis_tab(self):
        """Setup analysis tab"""
        analysis_frame = ttk.Frame(self.notebook)
        self.notebook.add(analysis_frame, text="Analysis")
        
        # Analysis widgets
        ttk.Label(analysis_frame, text="Strategy Analysis").pack(pady=10)
        
    def save_config(self):
        """Save current configuration to file"""
        try:
            # Update config with current GUI values
            self.config['risk_management'].update({
                'max_position_size': self.max_position_var.get(),
                'stop_loss_pct': self.stop_loss_var.get(),
                'take_profit_pct': self.take_profit_var.get(),
                'max_drawdown_pct': self.max_drawdown_var.get()
            })
            
            with open("config.json", 'w') as f:
                json.dump(self.config, f, indent=4)
            logger.info("Configuration saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
    
    def start_strategy(self):
        """Start the trading strategy"""
        logger.info("Starting trading strategy...")
        # Add strategy startup logic here
        
    def run(self):
        """Run the GUI application"""
        self.root.mainloop()

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

        # Add missing forward test TP variables
        self.ft_tp1_points = tk.StringVar(value="20")
        self.ft_tp2_points = tk.StringVar(value="35")
        self.ft_tp3_points = tk.StringVar(value="50")
        self.ft_tp4_points = tk.StringVar(value="75")
        
        # Add missing current price variable
        self.bt_current_price = tk.StringVar(value="100")
        
        # Add missing capital variables
        self.bt_available_capital = tk.StringVar(value="100000")
        self.bt_risk_percentage = tk.StringVar(value="1.0")

    def _initialize_variables_from_runtime_config(self):
        """Initialize all GUI variables from runtime_config (single source for widgets)"""
        # Read sections from the runtime_config which already merges defaults + user prefs
        strategy_defaults = self.runtime_config.get('strategy', {})
        risk_defaults = self.runtime_config.get('risk', {})
        capital_defaults = self.runtime_config.get('capital', {})
        instrument_defaults = self.runtime_config.get('instrument', {})
        session_defaults = self.runtime_config.get('session', {})

        # --- Strategy variables ---
        self.bt_use_ema_crossover = tk.BooleanVar(value=strategy_defaults.get('use_ema_crossover', True))
        self.bt_use_macd = tk.BooleanVar(value=strategy_defaults.get('use_macd', True))
        self.bt_use_vwap = tk.BooleanVar(value=strategy_defaults.get('use_vwap', True))
        self.bt_use_rsi_filter = tk.BooleanVar(value=strategy_defaults.get('use_rsi_filter', False))
        self.bt_use_htf_trend = tk.BooleanVar(value=strategy_defaults.get('use_htf_trend', True))
        self.bt_use_bollinger_bands = tk.BooleanVar(value=strategy_defaults.get('use_bollinger_bands', False))
        self.bt_use_stochastic = tk.BooleanVar(value=strategy_defaults.get('use_stochastic', False))
        self.bt_use_atr = tk.BooleanVar(value=strategy_defaults.get('use_atr', True))
        
        # EMA parameters
        self.bt_fast_ema = tk.StringVar(value=str(strategy_defaults.get('fast_ema', 9)))
        self.bt_slow_ema = tk.StringVar(value=str(strategy_defaults.get('slow_ema', 21)))
        
        # MACD parameters
        self.bt_macd_fast = tk.StringVar(value=str(strategy_defaults.get('macd_fast', 12)))
        self.bt_macd_slow = tk.StringVar(value=str(strategy_defaults.get('macd_slow', 26)))
        self.bt_macd_signal = tk.StringVar(value=str(strategy_defaults.get('macd_signal', 9)))
        
        # RSI parameters
        self.bt_rsi_length = tk.StringVar(value=str(strategy_defaults.get('rsi_length', 14)))
        self.bt_rsi_oversold = tk.StringVar(value=str(strategy_defaults.get('rsi_oversold', 30)))
        self.bt_rsi_overbought = tk.StringVar(value=str(strategy_defaults.get('rsi_overbought', 70)))
        
        # HTF parameter
        self.bt_htf_period = tk.StringVar(value=str(strategy_defaults.get('htf_period', 20)))
        
        # Consecutive Green Bars parameter
        self.bt_consecutive_green_bars = tk.StringVar(value=str(strategy_defaults.get('consecutive_green_bars', 3)))

        # --- Risk management ---
        self.bt_base_sl_points = tk.StringVar(value=str(risk_defaults.get('base_sl_points', 15)))
        
        # Initialize TP points properly
        tp_points_defaults = risk_defaults.get('tp_points', [20, 35, 50, 75])
        self.bt_tp_points = [tk.StringVar(value=str(p)) for p in tp_points_defaults]
        
        tp_percents_defaults = risk_defaults.get('tp_percents', [0.25, 0.25, 0.25, 0.25])
        self.bt_tp_percents = [tk.StringVar(value=str(p*100)) for p in tp_percents_defaults]
        
        self.bt_use_trail_stop = tk.BooleanVar(value=risk_defaults.get('use_trail_stop', True))
        self.bt_trail_activation = tk.StringVar(value=str(risk_defaults.get('trail_activation_points', 25)))
        self.bt_trail_distance = tk.StringVar(value=str(risk_defaults.get('trail_distance_points', 10)))
        self.bt_risk_per_trade_percent = tk.StringVar(value=str(risk_defaults.get('risk_per_trade_percent', 1.0)))

        # --- Capital settings ---
        self.bt_initial_capital = tk.StringVar(value=str(capital_defaults.get('initial_capital', 100000)))

        # --- Instrument settings ---
        self.bt_symbol = tk.StringVar(value=instrument_defaults.get('symbol', 'NIFTY'))
        self.bt_exchange = tk.StringVar(value=instrument_defaults.get('exchange', 'NSE_FO'))
        self.bt_lot_size = tk.StringVar(value=str(instrument_defaults.get('lot_size', 75)))

        # --- Session settings ---
        self.bt_is_intraday = tk.BooleanVar(value=session_defaults.get('is_intraday', True))
        self.bt_session_start_hour = tk.StringVar(value=str(session_defaults.get('start_hour', 9)))
        self.bt_session_start_min = tk.StringVar(value=str(session_defaults.get('start_min', 15)))
        self.bt_session_end_hour = tk.StringVar(value=str(session_defaults.get('end_hour', 15)))
        self.bt_session_end_min = tk.StringVar(value=str(session_defaults.get('end_min', 30)))