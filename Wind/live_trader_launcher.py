import tkinter as tk
from tkinter import ttk, messagebox
import threading
import requests
import json
import os
from datetime import datetime, timedelta
import subprocess, sys
try:
    from .visual_price_tick_indicator import start_visual_price_tick_indicator
except ImportError:
    from visual_price_tick_indicator import start_visual_price_tick_indicator

# Import the refactored bot class and the strategy class to get defaults
try:
    from .live_trader import LiveTradingBot
    from .strategy import ModularIntradayStrategy
except ImportError:
    from live_trader import LiveTradingBot
    from strategy import ModularIntradayStrategy

class LiveTraderGUI:
    def _load_symbol_token_map(self):
        """Load symbol-token mapping from cache or fetch online if not present."""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    cache_data = json.load(f)
                    symbol_token_map = cache_data.get('symbols', {})
                    print(f"Loaded {len(symbol_token_map)} symbols from cache")
                    return symbol_token_map
            except Exception as e:
                print(f"Error reading cache: {e}")
        # Cache doesn't exist or failed, fetch from online
        return self._fetch_and_cache_symbols()
    def stop_trading(self):
        """Stops the running trading bot and saves price tick data to a symbol-named CSV file."""
        if hasattr(self, 'bot_instance') and self.bot_instance:
            self.bot_instance.stop(is_manual_stop=True)
            if hasattr(self, 'bot_thread') and self.bot_thread and self.bot_thread.is_alive():
                self.bot_thread.join(timeout=5)
        # Save price tick data to CSV named after the symbol
        try:
            symbol = self.symbol_var.get() or self.instrument_token.get()
            # Clean symbol for filename
            safe_symbol = symbol.replace(':', '_').replace('/', '_').replace(' ', '_')
            tick_log_path = os.path.join(os.path.dirname(__file__), "price_ticks.log")
            if os.path.exists(tick_log_path):
                csv_dir = os.path.join(os.path.dirname(__file__), "data")
                os.makedirs(csv_dir, exist_ok=True)
                csv_path = os.path.join(csv_dir, f"{safe_symbol}.csv")
                with open(tick_log_path, "r") as fin, open(csv_path, "a", encoding="utf-8") as fout:
                    for line in fin:
                        fout.write(line)
                print(f"[INFO] Price tick data saved to {csv_path}")
        except Exception as e:
            print(f"[ERROR] Failed to save price tick data: {e}")

        # Log trading session (if needed, you can add more logging here)
        try:
            params = self.get_params_from_gui()
            self.log_applied_parameters(params, self.symbol_var.get(), self.exchange_type.get(), self.feed_type.get())
        except Exception as e:
            print(f"[ERROR] Failed to log trading session: {e}")
    def __init__(self, root):
        self.root = root
        self.root.title("Live Trader Launcher v2")
        self.cache_file = "smartapi/symbol_cache.json"

        # Get default parameters from the strategy class itself
        default_strategy = ModularIntradayStrategy()

        # --- GUI Variables ---
        self.instrument_token = tk.StringVar(value="49483") # Default to NIFTY24JUL2524900CE
        self.symbol_var = tk.StringVar()
        self.exchange_type = tk.StringVar(value="NSE_FO")
        self.feed_type = tk.StringVar(value="Quote") # Default to Quote for VWAP
        self.log_ticks = tk.BooleanVar(value=False) # Default to not logging ticks

        # Indicator toggles
        self.use_macd = tk.BooleanVar(value=default_strategy.use_macd)
        self.use_ema_crossover = tk.BooleanVar(value=default_strategy.use_ema_crossover)
        self.use_rsi_filter = tk.BooleanVar(value=default_strategy.use_rsi_filter)
        self.use_vwap = tk.BooleanVar(value=default_strategy.use_vwap)
        self.use_htf_trend = tk.BooleanVar(value=True) # Default to using HTF trend
        self.htf_period = tk.IntVar(value=20)  # Default HTF period, adjust as needed
        self.ema_points_threshold = tk.DoubleVar(value=2.0)  # Default EMA threshold, adjust as needed

        # MACD parameters
        self.macd_short_window = tk.IntVar(value=default_strategy.macd_short_window)
        self.macd_long_window = tk.IntVar(value=default_strategy.macd_long_window)
        self.macd_signal_window = tk.IntVar(value=default_strategy.macd_signal_window)
        # Indicator parameters
        self.atr_len = tk.IntVar(value=default_strategy.atr_len)
        self.atr_mult = tk.DoubleVar(value=default_strategy.atr_mult)
        self.fast_ema = tk.IntVar(value=default_strategy.fast_ema)
        self.slow_ema = tk.IntVar(value=default_strategy.slow_ema)
        self.rsi_length = tk.IntVar(value=default_strategy.rsi_length)
        self.rsi_overbought = tk.IntVar(value=default_strategy.rsi_overbought)
        self.rsi_oversold = tk.IntVar(value=default_strategy.rsi_oversold)

        # Stop loss and targets
        self.base_sl_points = tk.IntVar(value=default_strategy.base_sl_points)
        self.tp1_points = tk.IntVar(value=default_strategy.tp1_points)
        self.tp2_points = tk.IntVar(value=default_strategy.tp2_points)
        self.tp3_points = tk.IntVar(value=default_strategy.tp3_points)
        
        # Trail Stop
        self.use_trail_stop = tk.BooleanVar(value=default_strategy.use_trail_stop)
        self.trail_activation_points = tk.IntVar(value=default_strategy.trail_activation_points)
        self.trail_distance_points = tk.IntVar(value=default_strategy.trail_distance_points)

        # Other parameters
        self.initial_capital = tk.IntVar(value=default_strategy.initial_capital)
        self.risk_per_trade_percent = tk.DoubleVar(value=default_strategy.risk_per_trade_percent)
        self.exit_before_close = tk.IntVar(value=default_strategy.exit_before_close)

        # Defer symbol-token map loading until user requests
        self.symbol_token_map = None
        self.symbols_list = []

        # --- Fast Symbol Filter Section ---
        self.filter_frame = tk.Frame(self.root)
        self.filter_frame.pack(pady=4)
        tk.Label(self.filter_frame, text="Symbol Filter (fast):").pack(side="left")
        self.filter_textbox = tk.Entry(self.filter_frame, width=24)
        self.filter_textbox.pack(side="left", padx=2)
        self.filter_button = tk.Button(self.filter_frame, text="Filter & Load", command=self.filter_and_load_symbols)
        self.filter_button.pack(side="left", padx=2)
        self.symbol_listbox = tk.Listbox(self.filter_frame, height=6, width=32)
        self.symbol_listbox.pack(side="left", padx=4)
        self.symbol_listbox.bind('<<ListboxSelect>>', self.on_symbol_listbox_select)

        self.create_widgets()
        # Handle window close event to stop trading cleanly
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def filter_and_load_symbols(self):
        """Filter the cache file before loading, for fast GUI startup."""
        filter_text = self.filter_textbox.get().strip().lower()
        filtered = []
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    symbols = cache_data.get('symbols', {})
                    for sym, token in symbols.items():
                        if filter_text in sym.lower():
                            filtered.append((sym, token))
            except Exception as e:
                print(f"[ERROR] Could not filter cache: {e}")
        self.symbol_listbox.delete(0, tk.END)
        for sym, token in filtered:
            self.symbol_listbox.insert(tk.END, f"{sym} | {token}")
        # Optionally, update the main symbol combo with filtered
        self.symbols_list = [sym for sym, _ in filtered]
        if hasattr(self, 'symbol_combo'):
            self.symbol_combo['values'] = self.symbols_list

    def on_symbol_listbox_select(self, event=None):
        """When a symbol is selected in the fast filter listbox, update the symbol_var and token."""
        selection = self.symbol_listbox.curselection()
        if selection:
            value = self.symbol_listbox.get(selection[0])
            if '|' in value:
                sym, token = value.split('|', 1)
                self.symbol_var.set(sym.strip())
                self.instrument_token.set(token.strip())

    def setup_loggers(self):
        # Placeholder for future logging setup
        pass


    def validate_and_display_params(self):
        """Validate and display all parameters before starting trading."""
        params = self.get_params_from_gui()
        validation_errors = []
        # Check numerical ranges
        if params['atr_len'] <= 0:
            validation_errors.append("ATR Length must be > 0")
        if params['atr_mult'] <= 0:
            validation_errors.append("ATR Multiplier must be > 0")
        if params['fast_ema'] >= params['slow_ema']:
            validation_errors.append("Fast EMA must be < Slow EMA")
        if params['rsi_length'] <= 0:
            validation_errors.append("RSI Length must be > 0")
        if not (0 < params['rsi_overbought'] < 100):
            validation_errors.append("RSI Overbought must be between 0-100")
        if not (0 < params['rsi_oversold'] < 100):
            validation_errors.append("RSI Oversold must be between 0-100")
        if params['rsi_oversold'] >= params['rsi_overbought']:
            validation_errors.append("RSI Oversold must be < RSI Overbought")
        # Check stop loss and targets
        if params['base_sl_points'] <= 0:
            validation_errors.append("Base SL Points must be > 0")
        if params['tp1_points'] <= 0:
            validation_errors.append("TP1 Points must be > 0")
        if params['tp2_points'] <= params['tp1_points']:
            validation_errors.append("TP2 must be > TP1")
        if params['tp3_points'] <= params['tp2_points']:
            validation_errors.append("TP3 must be > TP2")
        # Check trail stop
        if params['use_trail_stop']:
            if params['trail_activation_points'] <= 0:
                validation_errors.append("Trail Activation Points must be > 0")
            if params['trail_distance_points'] <= 0:
                validation_errors.append("Trail Distance Points must be > 0")
        # Check other parameters
        if params['initial_capital'] <= 0:
            validation_errors.append("Initial Capital must be > 0")
        if 'risk_per_trade_percent' in params and not (0 < params['risk_per_trade_percent'] <= 100):
            validation_errors.append("Risk per Trade must be between 0-100%")
        if validation_errors:
            messagebox.showerror("Parameter Validation Failed", "\n".join(validation_errors))
        return {
            "use_macd": True,
            "macd_short_window": 12,
            "macd_long_window": 26,
            "macd_signal_window": 9,
            "use_ema_crossover": self.use_ema_crossover.get(),
            "use_rsi_filter": self.use_rsi_filter.get(),
            "use_vwap": self.use_vwap.get(),
            "atr_len": self.atr_len.get(), "atr_mult": self.atr_mult.get(),
            "fast_ema": self.fast_ema.get(), "slow_ema": self.slow_ema.get(),
            "rsi_length": self.rsi_length.get(), "rsi_overbought": self.rsi_overbought.get(),
            "rsi_oversold": self.rsi_oversold.get(), "base_sl_points": self.base_sl_points.get(),
            "tp1_points": self.tp1_points.get(), "tp2_points": self.tp2_points.get(),
            "tp3_points": self.tp3_points.get(), "use_trail_stop": self.use_trail_stop.get(),
            "trail_activation_points": self.trail_activation_points.get(),
            "trail_distance_points": self.trail_distance_points.get(),
            "initial_capital": self.initial_capital.get(),
            "risk_per_trade_percent": self.risk_per_trade_percent.get(),
            "exit_before_close": self.exit_before_close.get(),
        }
        
        # Cache doesn't exist, fetch from online
        return self._fetch_and_cache_symbols()

    def _fetch_and_cache_symbols(self):
        """Fetch symbols from online and save to cache."""
        try:
            url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
            print("Fetching symbols from online source...")
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            
            # Parse the JSON data
            data = response.json()
            symbol_token_map = {}
            
            for item in data:
                symbol = item.get('symbol', '')
                token = item.get('token', '')
                if symbol and token:
                    symbol_token_map[symbol] = token
            
            # Save to cache
            self._save_cache(symbol_token_map)
            
            print(f"Loaded {len(symbol_token_map)} symbols from online source and cached")
            return symbol_token_map
            
        except Exception as e:
            print(f"Error fetching symbols: {e}")
            messagebox.showwarning("Warning", f"Could not load symbol list from online source: {e}\nYou can still manually enter the token.")
            return {}

    def _save_cache(self, symbol_token_map):
        """Save symbol-token mapping to cache file."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'symbols': symbol_token_map
            }
            
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
                
        except Exception as e:
            print(f"Error saving cache: {e}")

    def refresh_symbol_cache(self):
        """Manually refresh the symbol cache from online source."""
        print("Manually refreshing symbol cache...")
        self.symbol_token_map = self._fetch_and_cache_symbols()
        self.symbols_list = sorted(self.symbol_token_map.keys()) if self.symbol_token_map else []
        
        # Update the combobox values
        if hasattr(self, 'symbol_combo'):
            self.symbol_combo['values'] = self.symbols_list
        
        messagebox.showinfo("Cache Refresh", f"Symbol cache refreshed. Loaded {len(self.symbol_token_map)} symbols.")

    def _on_symbol_select(self, event=None):
        """When a symbol is selected from dropdown, update the token field."""
        selected_symbol = self.symbol_var.get()
        if selected_symbol in self.symbol_token_map:
            token = self.symbol_token_map[selected_symbol]
            self.instrument_token.set(token)
            print(f"Selected symbol: {selected_symbol}, Token: {token}")

    def _filter_symbols(self, event=None):
        """Filter symbols based on user input for autocomplete."""
        current_text = self.symbol_var.get().upper()
        if current_text:
            filtered_symbols = [s for s in self.symbols_list if current_text in s.upper()]
            self.symbol_combo['values'] = filtered_symbols
        else:
            self.symbol_combo['values'] = self.symbols_list

    def create_widgets(self):
        notebook = ttk.Notebook(self.root)
        notebook.pack(pady=10, padx=10, fill="both", expand=True)

        f_main = ttk.Frame(notebook, padding="10")
        f_indicators = ttk.Frame(notebook, padding="10")
        f_risk = ttk.Frame(notebook, padding="10")

        notebook.add(f_main, text='Main Settings')
        notebook.add(f_indicators, text='Indicators')
        notebook.add(f_risk, text='Risk & TP/SL')

        # --- Main Settings Frame ---
        # 1. Exchange field at the top
        ttk.Label(f_main, text="Exchange:", font=('Helvetica', 10, 'bold')).grid(row=0, column=0, sticky="w", pady=5)
        exchange_map = {"NSE_CM": 1, "NSE_FO": 2, "BSE_CM": 3, "BSE_FO": 4, "MCX_FO": 5, "NCDEX_FO": 7}
        self.exchange_combo = ttk.Combobox(f_main, textvariable=self.exchange_type, values=list(exchange_map.keys()), width=12)
        self.exchange_combo.grid(row=0, column=1, sticky="w")
        # 2. (Moved) symbol filter button now on symbol row

        # 3. Symbol field (disabled until tokens loaded); add filter button next to it
        ttk.Label(f_main, text="Symbol:", font=('Helvetica', 10, 'bold')).grid(row=1, column=0, sticky="w", pady=5)
        self.symbol_combo = ttk.Combobox(f_main, textvariable=self.symbol_var, values=self.symbols_list, width=20, state="normal")
        self.symbol_combo.grid(row=1, column=1, sticky="w", padx=(0, 5))
        self.symbol_combo.bind('<KeyRelease>', self._filter_symbols)
        self.symbol_combo.bind('<<ComboboxSelected>>', self._on_symbol_select)

        # Add filter symbols button based on symbol text
        ttk.Button(f_main, text="🔄 Filter symbols", command=self.retrieve_symbols_for_exchange, width=18).grid(row=1, column=2, sticky="w", padx=(0, 5))
        # Add refresh cache button (optional, can be kept for manual refresh)
        ttk.Button(f_main, text="🔄 Refresh token cache", command=self.refresh_symbol_cache, width=16).grid(row=1, column=3, sticky="w", padx=(8, 0))

        ttk.Label(f_main, text="Instrument Token:", font=('Helvetica', 10, 'bold')).grid(row=2, column=0, sticky="w", pady=5)
        ttk.Entry(f_main, textvariable=self.instrument_token, width=15).grid(row=2, column=1, sticky="w")

        ttk.Label(f_main, text="Feed Type:", font=('Helvetica', 10, 'bold')).grid(row=3, column=0, sticky="w", pady=5)
        feed_map = {"LTP": 1, "Quote": 2, "SnapQuote": 3}
        self.feed_combo = ttk.Combobox(f_main, textvariable=self.feed_type, values=list(feed_map.keys()), width=12)
        self.feed_combo.grid(row=3, column=1, sticky="w")

        ttk.Label(f_main, text="Initial Capital:").grid(row=4, column=0, sticky="w", pady=2)
        ttk.Entry(f_main, textvariable=self.initial_capital, width=15).grid(row=4, column=1, sticky="w")

        ttk.Label(f_main, text="Exit Before Close (min):").grid(row=5, column=0, sticky="w", pady=2)
        ttk.Entry(f_main, textvariable=self.exit_before_close, width=15).grid(row=5, column=1, sticky="w")

        ttk.Checkbutton(f_main, text="Log Live Ticks to Console", variable=self.log_ticks).grid(row=6, column=0, columnspan=2, sticky="w", pady=10)

        # --- Parameter Verification Buttons ---
        verify_frame = ttk.Frame(f_main)
        verify_frame.grid(row=7, column=0, columnspan=3, pady=10, sticky="w")
        ttk.Button(verify_frame, text="📝 Verify Parameters", command=self.validate_and_display_params, width=18).pack(side="left", padx=5)
        ttk.Button(verify_frame, text="🔍 Monitor Parameters", command=self.show_parameter_monitor, width=18).pack(side="left", padx=5)

        # --- Indicator Frame ---
        ttk.Checkbutton(f_indicators, text="Use EMA Crossover", variable=self.use_ema_crossover).grid(row=0, column=0, sticky="w")
        ttk.Checkbutton(f_indicators, text="Use RSI Filter", variable=self.use_rsi_filter).grid(row=1, column=0, sticky="w")
        ttk.Checkbutton(f_indicators, text="Use VWAP", variable=self.use_vwap).grid(row=2, column=0, sticky="w")

        # --- MACD Indicator ---
        ttk.Checkbutton(f_indicators, text="Use MACD", variable=self.use_macd).grid(row=3, column=0, sticky="w")
        ttk.Label(f_indicators, text="MACD Short:").grid(row=3, column=2, sticky="e", padx=5)
        ttk.Entry(f_indicators, textvariable=self.macd_short_window, width=8).grid(row=3, column=3, sticky="w")
        ttk.Label(f_indicators, text="MACD Long:").grid(row=3, column=4, sticky="e", padx=5)
        ttk.Entry(f_indicators, textvariable=self.macd_long_window, width=8).grid(row=3, column=5, sticky="w")
        ttk.Label(f_indicators, text="MACD Signal:").grid(row=3, column=6, sticky="e", padx=5)
        ttk.Entry(f_indicators, textvariable=self.macd_signal_window, width=8).grid(row=3, column=7, sticky="w")

        ttk.Label(f_indicators, text="ATR Len:").grid(row=0, column=2, sticky="e", padx=5)
        ttk.Entry(f_indicators, textvariable=self.atr_len, width=8).grid(row=0, column=3, sticky="w")
        ttk.Label(f_indicators, text="ATR Mult:").grid(row=0, column=4, sticky="e", padx=5)
        ttk.Entry(f_indicators, textvariable=self.atr_mult, width=8).grid(row=0, column=5, sticky="w")
        ttk.Label(f_indicators, text="Fast EMA:").grid(row=1, column=2, sticky="e", padx=5)
        ttk.Entry(f_indicators, textvariable=self.fast_ema, width=8).grid(row=1, column=3, sticky="w")
        ttk.Label(f_indicators, text="Slow EMA:").grid(row=1, column=4, sticky="e", padx=5)
        ttk.Entry(f_indicators, textvariable=self.slow_ema, width=8).grid(row=1, column=5, sticky="w")
        ttk.Label(f_indicators, text="RSI Len:").grid(row=2, column=2, sticky="e", padx=5)
        ttk.Entry(f_indicators, textvariable=self.rsi_length, width=8).grid(row=2, column=3, sticky="w")
        ttk.Label(f_indicators, text="RSI High:").grid(row=2, column=4, sticky="e", padx=5)
        ttk.Entry(f_indicators, textvariable=self.rsi_overbought, width=8).grid(row=2, column=5, sticky="w")
        ttk.Label(f_indicators, text="RSI Low:").grid(row=2, column=6, sticky="e", padx=5)
        ttk.Entry(f_indicators, textvariable=self.rsi_oversold, width=8).grid(row=2, column=7, sticky="w")

        # --- HTF Trend Indicator ---
        ttk.Label(f_indicators, text="HTF Trend Period:").grid(row=4, column=2, sticky="e", padx=5)
        ttk.Entry(f_indicators, textvariable=self.htf_period, width=8).grid(row=4, column=3, sticky="w")

        # --- EMA Points Threshold ---
        ttk.Label(f_indicators, text="EMA Points Threshold:").grid(row=5, column=2, sticky="e", padx=5)
        ttk.Entry(f_indicators, textvariable=self.ema_points_threshold, width=8).grid(row=5, column=3, sticky="w")

        # --- Risk & TP/SL Frame ---
        ttk.Label(f_risk, text="Risk Per Trade (%):").grid(row=0, column=0, sticky="w", pady=2)
        ttk.Entry(f_risk, textvariable=self.risk_per_trade_percent, width=10).grid(row=0, column=1, sticky="w")
        ttk.Label(f_risk, text="Base SL (Points):").grid(row=1, column=0, sticky="w", pady=2)
        ttk.Entry(f_risk, textvariable=self.base_sl_points, width=10).grid(row=1, column=1, sticky="w")
        ttk.Label(f_risk, text="TP1 (Points):").grid(row=2, column=0, sticky="w", pady=2); ttk.Entry(f_risk, textvariable=self.tp1_points, width=10).grid(row=2, column=1, sticky="w")
        ttk.Label(f_risk, text="TP2 (Points):").grid(row=3, column=0, sticky="w", pady=2); ttk.Entry(f_risk, textvariable=self.tp2_points, width=10).grid(row=3, column=1, sticky="w")
        ttk.Label(f_risk, text="TP3 (Points):").grid(row=4, column=0, sticky="w", pady=2); ttk.Entry(f_risk, textvariable=self.tp3_points, width=10).grid(row=4, column=1, sticky="w")
        ttk.Separator(f_risk, orient='horizontal').grid(row=5, column=0, columnspan=4, sticky='ew', pady=10)
        ttk.Checkbutton(f_risk, text="Use Trailing Stop", variable=self.use_trail_stop).grid(row=6, column=0, sticky="w")
        ttk.Label(f_risk, text="Trail Activation (Pts):").grid(row=7, column=0, sticky="w", pady=2); ttk.Entry(f_risk, textvariable=self.trail_activation_points, width=10).grid(row=7, column=1, sticky="w")
        ttk.Label(f_risk, text="Trail Distance (Pts):").grid(row=8, column=0, sticky="w", pady=2); ttk.Entry(f_risk, textvariable=self.trail_distance_points, width=10).grid(row=8, column=1, sticky="w")

        # --- Action Buttons ---
        button_frame = ttk.Frame(self.root)
        button_frame.pack(pady=10)
        self.start_button = ttk.Button(button_frame, text="Start Live Trading", command=self.start_trading)
        self.start_button.pack(side="left", padx=5)
        self.stop_button = ttk.Button(button_frame, text="Stop Trading", command=self.stop_trading, state="disabled")
        self.stop_button.pack(side="left", padx=5)

        # --- Status Monitor Button ---
        status_frame = ttk.Frame(self.root)
        status_frame.pack(pady=5)
        self.status_button = ttk.Button(status_frame, text="📊 Open Status Monitor", command=self.open_status_monitor)
        self.status_button.pack(side="left", padx=5)

    def retrieve_symbols_for_exchange(self):
        """Filter and load symbols based on the text entered in the symbol field."""
        # Ensure full symbol-token map is loaded
        if self.symbol_token_map is None:
            self.symbol_token_map = self._load_symbol_token_map()
        all_symbols = self.symbol_token_map or {}
        # Use the current symbol entry text for filtering (case-insensitive)
        filter_text = self.symbol_var.get().strip().upper()
        if filter_text:
            filtered = {k: v for k, v in all_symbols.items() if filter_text in k.upper()}
            info_msg = f"Found {len(filtered)} symbols matching '{filter_text}'."
        else:
            filtered = all_symbols
            info_msg = f"Loaded all {len(filtered)} symbols."
        # Update the combobox with filtered symbols
        self.symbol_token_map = filtered
        self.symbols_list = sorted(filtered.keys())
        self.symbol_combo['values'] = self.symbols_list
        self.symbol_combo.config(state="normal")
        messagebox.showinfo("Symbols Filtered", info_msg)

    def get_params_from_gui(self):
        """Collects all parameters from the GUI fields into a dictionary."""
        return {
            "use_macd": self.use_macd.get(),
            "macd_short_window": self.macd_short_window.get(),
            "macd_long_window": self.macd_long_window.get(),
            "macd_signal_window": self.macd_signal_window.get(),
            "use_ema_crossover": self.use_ema_crossover.get(),
            "use_rsi_filter": self.use_rsi_filter.get(),
            "use_vwap": self.use_vwap.get(),
            "atr_len": self.atr_len.get(), "atr_mult": self.atr_mult.get(),
            "fast_ema": self.fast_ema.get(), "slow_ema": self.slow_ema.get(),
            "rsi_length": self.rsi_length.get(), "rsi_overbought": self.rsi_overbought.get(),
            "rsi_oversold": self.rsi_oversold.get(), "base_sl_points": self.base_sl_points.get(),
            "tp1_points": self.tp1_points.get(), "tp2_points": self.tp2_points.get(),
            "tp3_points": self.tp3_points.get(), "use_trail_stop": self.use_trail_stop.get(),
            "trail_activation_points": self.trail_activation_points.get(),
            "trail_distance_points": self.trail_distance_points.get(),
            "initial_capital": self.initial_capital.get(),
            "risk_per_trade_percent": self.risk_per_trade_percent.get(),
            "exit_before_close": self.exit_before_close.get(),
            "use_htf_trend": self.use_htf_trend.get(),
            "ema_points_threshold": self.ema_points_threshold.get(),
        }

    def start_trading(self):
        """Modified start_trading method with validation and confirmation dialog."""
        # Validate parameters before starting
        if not self.validate_and_display_params():
            return
        # Ensure instrument token is set
        token = self.instrument_token.get().strip()
        if not token:
            messagebox.showerror("Error", "Instrument token is empty.")
            return
        # Prepare parameters and mapping
        params = self.get_params_from_gui()
        exchange_map = {"NSE_CM": 1, "NSE_FO": 2, "BSE_CM": 3, "BSE_FO": 4, "MCX_FO": 5, "NCDEX_FO": 7}
        feed_map = {"LTP": 1, "Quote": 2, "SnapQuote": 3}
        exchange_code = exchange_map.get(self.exchange_type.get(), None)
        feed_code = feed_map.get(self.feed_type.get(), None)
        # Instantiate and start the trading bot in a background thread
        self.bot_instance = LiveTradingBot(
            instrument_token=token,
            strategy_params=params,
            exchange_type=exchange_code,
            feed_mode=feed_code,
            log_ticks=self.log_ticks.get(),
            symbol=self.symbol_var.get() or None
        )
        self.bot_thread = threading.Thread(target=self.bot_instance.run, daemon=True)
        self.bot_thread.start()
        # Update button states
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
    def create_widgets(self):
        notebook = ttk.Notebook(self.root)
        notebook.pack(pady=10, padx=10, fill="both", expand=True)

        f_main = ttk.Frame(notebook, padding="10")
        f_indicators = ttk.Frame(notebook, padding="10")
        f_risk = ttk.Frame(notebook, padding="10")

        notebook.add(f_main, text='Main Settings')
        notebook.add(f_indicators, text='Indicators')
        notebook.add(f_risk, text='Risk & TP/SL')

        # --- Main Settings Frame ---
        # 1. Exchange field at the top
        ttk.Label(f_main, text="Exchange:", font=('Helvetica', 10, 'bold')).grid(row=0, column=0, sticky="w", pady=5)
        exchange_map = {"NSE_CM": 1, "NSE_FO": 2, "BSE_CM": 3, "BSE_FO": 4, "MCX_FO": 5, "NCDEX_FO": 7}
        self.exchange_combo = ttk.Combobox(f_main, textvariable=self.exchange_type, values=list(exchange_map.keys()), width=12)
        self.exchange_combo.grid(row=0, column=1, sticky="w")
        # 2. (Moved) symbol filter button now on symbol row

        # 3. Symbol field (disabled until tokens loaded); add filter button next to it
        ttk.Label(f_main, text="Symbol:", font=('Helvetica', 10, 'bold')).grid(row=1, column=0, sticky="w", pady=5)
        self.symbol_combo = ttk.Combobox(f_main, textvariable=self.symbol_var, values=self.symbols_list, width=20, state="normal")
        self.symbol_combo.grid(row=1, column=1, sticky="w", padx=(0, 5))
        self.symbol_combo.bind('<KeyRelease>', self._filter_symbols)
        self.symbol_combo.bind('<<ComboboxSelected>>', self._on_symbol_select)

        # Add filter symbols button based on symbol text
        ttk.Button(f_main, text="🔄 Filter symbols", command=self.retrieve_symbols_for_exchange, width=18).grid(row=1, column=2, sticky="w", padx=(0, 5))
        # Add refresh cache button (optional, can be kept for manual refresh)
        ttk.Button(f_main, text="🔄 Refresh token cache", command=self.refresh_symbol_cache, width=16).grid(row=1, column=3, sticky="w", padx=(8, 0))

        ttk.Label(f_main, text="Instrument Token:", font=('Helvetica', 10, 'bold')).grid(row=2, column=0, sticky="w", pady=5)
        ttk.Entry(f_main, textvariable=self.instrument_token, width=15).grid(row=2, column=1, sticky="w")

        ttk.Label(f_main, text="Feed Type:", font=('Helvetica', 10, 'bold')).grid(row=3, column=0, sticky="w", pady=5)
        feed_map = {"LTP": 1, "Quote": 2, "SnapQuote": 3}
        self.feed_combo = ttk.Combobox(f_main, textvariable=self.feed_type, values=list(feed_map.keys()), width=12)
        self.feed_combo.grid(row=3, column=1, sticky="w")

        ttk.Label(f_main, text="Initial Capital:").grid(row=4, column=0, sticky="w", pady=2)
        ttk.Entry(f_main, textvariable=self.initial_capital, width=15).grid(row=4, column=1, sticky="w")

        ttk.Label(f_main, text="Exit Before Close (min):").grid(row=5, column=0, sticky="w", pady=2)
        ttk.Entry(f_main, textvariable=self.exit_before_close, width=15).grid(row=5, column=1, sticky="w")

        ttk.Checkbutton(f_main, text="Log Live Ticks to Console", variable=self.log_ticks).grid(row=6, column=0, columnspan=2, sticky="w", pady=10)

        # --- Parameter Verification Buttons ---
        verify_frame = ttk.Frame(f_main)
        verify_frame.grid(row=7, column=0, columnspan=3, pady=10, sticky="w")
        ttk.Button(verify_frame, text="📝 Verify Parameters", command=self.validate_and_display_params, width=18).pack(side="left", padx=5)
        ttk.Button(verify_frame, text="🔍 Monitor Parameters", command=self.show_parameter_monitor, width=18).pack(side="left", padx=5)

        # --- Indicator Frame ---
        ttk.Checkbutton(f_indicators, text="Use EMA Crossover", variable=self.use_ema_crossover).grid(row=0, column=0, sticky="w")
        ttk.Checkbutton(f_indicators, text="Use RSI Filter", variable=self.use_rsi_filter).grid(row=1, column=0, sticky="w")
        ttk.Checkbutton(f_indicators, text="Use VWAP", variable=self.use_vwap).grid(row=2, column=0, sticky="w")

        # --- MACD Indicator ---
        ttk.Checkbutton(f_indicators, text="Use MACD", variable=self.use_macd).grid(row=3, column=0, sticky="w")
        ttk.Label(f_indicators, text="MACD Short:").grid(row=3, column=2, sticky="e", padx=5)
        ttk.Entry(f_indicators, textvariable=self.macd_short_window, width=8).grid(row=3, column=3, sticky="w")
        ttk.Label(f_indicators, text="MACD Long:").grid(row=3, column=4, sticky="e", padx=5)
        ttk.Entry(f_indicators, textvariable=self.macd_long_window, width=8).grid(row=3, column=5, sticky="w")
        ttk.Label(f_indicators, text="MACD Signal:").grid(row=3, column=6, sticky="e", padx=5)
        ttk.Entry(f_indicators, textvariable=self.macd_signal_window, width=8).grid(row=3, column=7, sticky="w")

        ttk.Label(f_indicators, text="ATR Len:").grid(row=0, column=2, sticky="e", padx=5)
        ttk.Entry(f_indicators, textvariable=self.atr_len, width=8).grid(row=0, column=3, sticky="w")
        ttk.Label(f_indicators, text="ATR Mult:").grid(row=0, column=4, sticky="e", padx=5)
        ttk.Entry(f_indicators, textvariable=self.atr_mult, width=8).grid(row=0, column=5, sticky="w")
        ttk.Label(f_indicators, text="Fast EMA:").grid(row=1, column=2, sticky="e", padx=5)
        ttk.Entry(f_indicators, textvariable=self.fast_ema, width=8).grid(row=1, column=3, sticky="w")
        ttk.Label(f_indicators, text="Slow EMA:").grid(row=1, column=4, sticky="e", padx=5)
        ttk.Entry(f_indicators, textvariable=self.slow_ema, width=8).grid(row=1, column=5, sticky="w")
        ttk.Label(f_indicators, text="RSI Len:").grid(row=2, column=2, sticky="e", padx=5)
        ttk.Entry(f_indicators, textvariable=self.rsi_length, width=8).grid(row=2, column=3, sticky="w")
        ttk.Label(f_indicators, text="RSI High:").grid(row=2, column=4, sticky="e", padx=5)
        ttk.Entry(f_indicators, textvariable=self.rsi_overbought, width=8).grid(row=2, column=5, sticky="w")
        ttk.Label(f_indicators, text="RSI Low:").grid(row=2, column=6, sticky="e", padx=5)
        ttk.Entry(f_indicators, textvariable=self.rsi_oversold, width=8).grid(row=2, column=7, sticky="w")

        # --- HTF Trend Indicator ---
        ttk.Label(f_indicators, text="HTF Trend Period:").grid(row=4, column=2, sticky="e", padx=5)
        ttk.Entry(f_indicators, textvariable=self.htf_period, width=8).grid(row=4, column=3, sticky="w")

        # --- EMA Points Threshold ---
        ttk.Label(f_indicators, text="EMA Points Threshold:").grid(row=5, column=2, sticky="e", padx=5)
        ttk.Entry(f_indicators, textvariable=self.ema_points_threshold, width=8).grid(row=5, column=3, sticky="w")

        # --- Risk & TP/SL Frame ---
        ttk.Label(f_risk, text="Risk Per Trade (%):").grid(row=0, column=0, sticky="w", pady=2)
        ttk.Entry(f_risk, textvariable=self.risk_per_trade_percent, width=10).grid(row=0, column=1, sticky="w")
        ttk.Label(f_risk, text="Base SL (Points):").grid(row=1, column=0, sticky="w", pady=2)
        ttk.Entry(f_risk, textvariable=self.base_sl_points, width=10).grid(row=1, column=1, sticky="w")
        ttk.Label(f_risk, text="TP1 (Points):").grid(row=2, column=0, sticky="w", pady=2); ttk.Entry(f_risk, textvariable=self.tp1_points, width=10).grid(row=2, column=1, sticky="w")
        ttk.Label(f_risk, text="TP2 (Points):").grid(row=3, column=0, sticky="w", pady=2); ttk.Entry(f_risk, textvariable=self.tp2_points, width=10).grid(row=3, column=1, sticky="w")
        ttk.Label(f_risk, text="TP3 (Points):").grid(row=4, column=0, sticky="w", pady=2); ttk.Entry(f_risk, textvariable=self.tp3_points, width=10).grid(row=4, column=1, sticky="w")
        ttk.Separator(f_risk, orient='horizontal').grid(row=5, column=0, columnspan=4, sticky='ew', pady=10)
        ttk.Checkbutton(f_risk, text="Use Trailing Stop", variable=self.use_trail_stop).grid(row=6, column=0, sticky="w")
        ttk.Label(f_risk, text="Trail Activation (Pts):").grid(row=7, column=0, sticky="w", pady=2); ttk.Entry(f_risk, textvariable=self.trail_activation_points, width=10).grid(row=7, column=1, sticky="w")
        ttk.Label(f_risk, text="Trail Distance (Pts):").grid(row=8, column=0, sticky="w", pady=2); ttk.Entry(f_risk, textvariable=self.trail_distance_points, width=10).grid(row=8, column=1, sticky="w")

        # --- Action Buttons ---
        button_frame = ttk.Frame(self.root)
        button_frame.pack(pady=10)
        self.start_button = ttk.Button(button_frame, text="Start Live Trading", command=self.start_trading)
        self.start_button.pack(side="left", padx=5)
        self.stop_button = ttk.Button(button_frame, text="Stop Trading", command=self.stop_trading, state="disabled")
        self.stop_button.pack(side="left", padx=5)

        # --- Status Monitor Button ---
        status_frame = ttk.Frame(self.root)
        status_frame.pack(pady=5)
        self.status_button = ttk.Button(status_frame, text="📊 Open Status Monitor", command=self.open_status_monitor)
        self.status_button.pack(side="left", padx=5)

    def log_applied_parameters(self, params, symbol, exchange_type, feed_type):
        """Log all applied parameters to console and file."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"""\n{'='*60}\nTRADING SESSION STARTED - {timestamp}\n{'='*60}\nINSTRUMENT: {symbol} (Token: {self.instrument_token.get()})\nEXCHANGE: {self.exchange_type.get()} (Code: {exchange_type})\nFEED TYPE: {self.feed_type.get()} (Code: {feed_type})\nLOG TICKS: {self.log_ticks.get()}\n\nSTRATEGY PARAMETERS APPLIED:\n{'-'*30}\n"""
        for key, value in params.items():
            log_message += f"{key.upper().replace('_', ' ')}: {value}\n"
        log_message += f"{'='*60}\n"
        print(log_message)
        try:
            with open("smartapi/strategy_config.log", "a") as f:
                f.write(log_message)
        except:
            pass

    def stop_trading(self):
        """Stops the running trading bot and saves price tick data to a symbol-named CSV file."""
        if self.bot_instance:
            self.bot_instance.stop(is_manual_stop=True)
            if self.bot_thread and self.bot_thread.is_alive():
                self.bot_thread.join(timeout=5)
        # Save price tick data to CSV named after the symbol
        try:
            symbol = self.symbol_var.get() or self.instrument_token.get()
            # Clean symbol for filename
            safe_symbol = symbol.replace(':', '_').replace('/', '_').replace(' ', '_')
            tick_log_path = os.path.join(os.path.dirname(__file__), "price_ticks.log")
            if os.path.exists(tick_log_path):
                csv_dir = os.path.join(os.path.dirname(__file__), "data")
                os.makedirs(csv_dir, exist_ok=True)
                csv_path = os.path.join(csv_dir, f"{safe_symbol}.csv")
                with open(tick_log_path, "r") as fin, open(csv_path, "a", encoding="utf-8") as fout:
                    for line in fin:
                        fout.write(line)
                print(f"[INFO] Price tick data saved to {csv_path}")
        except Exception as e:
            print(f"[ERROR] Failed to save price tick data: {e}")
        

    def show_parameter_monitor(self):
        """Show a live parameter monitor window."""
        monitor_window = tk.Toplevel(self.root)
        monitor_window.title("Parameter Monitor")
        monitor_window.geometry("500x600")
        text_frame = tk.Frame(monitor_window)
        text_frame.pack(fill="both", expand=True, padx=10, pady=10)
        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side="right", fill="y")
        text_widget = tk.Text(text_frame, wrap="word", yscrollcommand=scrollbar.set)
        text_widget.pack(fill="both", expand=True)
        scrollbar.config(command=text_widget.yview)
        params = self.get_params_from_gui()
        param_lines = [f"{k}: {v}" for k, v in params.items()]
        param_lines_str = "\n".join(param_lines)
        param_text = f"""LIVE STRATEGY PARAMETERS
{'='*40}

{param_lines_str}

Symbol: {self.symbol_var.get()}
Token: {self.instrument_token.get()}
Exchange: {self.exchange_type.get()}
Feed Type: {self.feed_type.get()}
Log Ticks: {self.log_ticks.get()}
"""
        text_widget.insert("1.0", param_text)
        text_widget.config(state="disabled")
    
    def open_status_monitor(self):
        
        """Opens the visual price tick indicator for status monitoring as a separate process."""
        import subprocess
        import sys
        import os

        # Find the absolute path to visual_price_tick_indicator.py
        script_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '..', 'visual_price_tick_indicator.py')
        )

        # Use the current Python executable
        python_exe = sys.executable

        # Pass initial_capital and log_path as arguments if needed
        initial_capital = str(self.initial_capital.get())
        log_path = os.path.abspath("smartapi/price_ticks.log")

        try:
            # Launch as a new process
            subprocess.Popen(
                [python_exe, script_path, initial_capital, log_path],
                close_fds=True
            )
            # Optionally, show a message
            from tkinter import messagebox
            messagebox.showinfo(
                "Status Monitor",
                "Status monitor opened in a new window!\n\n"
                "Close the monitor window to stop monitoring."
            )
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Error", f"Failed to open status monitor: {e}")

    # Handle window close event to cleanly stop trading
    def on_closing(self):
        """Handle window close event by stopping trading and closing the window."""
        if messagebox.askokcancel("Quit", "Do you want to exit and stop trading?"):
            try:
                self.stop_trading()
            except Exception:
                pass
            # Quit main loop then destroy window
            self.root.quit()
            self.root.destroy()

if __name__ == "__main__":
    import tkinter as tk
    root = tk.Tk()
    app = LiveTraderGUI(root)
    root.mainloop()
