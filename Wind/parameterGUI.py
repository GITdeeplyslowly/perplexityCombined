import tkinter as tk
from tkinter import ttk, messagebox
from tabulate import tabulate
from datetime import datetime
import pandas as pd
import os

class StrategyParameterGUI:
    def get_params_from_gui(self):
        """Collect all parameters from the GUI fields into a dictionary."""
        return {
            "use_macd": self.use_macd.get(),
            "use_ema_crossover": self.use_ema_crossover.get(),
            "use_rsi_filter": self.use_rsi_filter.get(),
            "use_vwap": self.use_vwap.get(),
            "macd_short_window": self.macd_short_window.get(),
            "macd_long_window": self.macd_long_window.get(),
            "macd_signal_window": self.macd_signal_window.get(),
            "fast_ema": self.fast_ema.get(),
            "slow_ema": self.slow_ema.get(),
            "rsi_length": self.rsi_length.get(),
            "rsi_overbought": self.rsi_overbought.get(),
            "rsi_oversold": self.rsi_oversold.get(),
            "base_sl_points": self.base_sl_points.get(),
            "tp1_points": self.tp1_points.get(),
            "tp2_points": self.tp2_points.get(),
            "tp3_points": self.tp3_points.get(),
            "use_trail_stop": self.use_trail_stop.get(),
            "trail_activation_points": self.trail_activation_points.get(),
            "trail_distance_points": self.trail_distance_points.get(),
            "initial_capital": self.initial_capital.get(),
            "exit_before_close": self.exit_before_close.get(),
            "buy_buffer": self.buy_buffer.get(),
        }

    def validate_parameters(self, params):
        """Validate parameters before running backtest."""
        errors = []
        if params['atr_len'] <= 0:
            errors.append("ATR Length must be > 0")
        if params['atr_mult'] <= 0:
            errors.append("ATR Multiplier must be > 0")
        if params['fast_ema'] >= params['slow_ema']:
            errors.append("Fast EMA must be < Slow EMA")
        if params['rsi_length'] <= 0:
            errors.append("RSI Length must be > 0")
        if not (0 < params['rsi_overbought'] < 100):
            errors.append("RSI Overbought must be between 0-100")
        if not (0 < params['rsi_oversold'] < 100):
            errors.append("RSI Oversold must be between 0-100")
        if params['rsi_oversold'] >= params['rsi_overbought']:
            errors.append("RSI Oversold must be < RSI Overbought")
        if params['base_sl_points'] <= 0:
            errors.append("Base SL Points must be > 0")
        if params['tp1_points'] <= 0:
            errors.append("TP1 Points must be > 0")
        if params['tp2_points'] <= params['tp1_points']:
            errors.append("TP2 must be > TP1")
        if params['tp3_points'] <= params['tp2_points']:
            errors.append("TP3 must be > TP2")
        if params['use_trail_stop']:
            if params['trail_activation_points'] <= 0:
                errors.append("Trail Activation Points must be > 0")
            if params['trail_distance_points'] <= 0:
                errors.append("Trail Distance Points must be > 0")
        if params['initial_capital'] <= 0:
            errors.append("Initial Capital must be > 0")
        return errors

    def log_parameters(self, params, run_type="backtest"):
        """Log parameters to file and print to console."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"\n{'='*60}\n{run_type.upper()} RUN - {timestamp}\n{'='*60}\n"
        for k, v in params.items():
            log_message += f"{k}: {v}\n"
        log_message += f"{'='*60}\n"
        print(log_message)
        try:
            with open("smartapi/parameter_log.txt", "a") as f:
                f.write(log_message)
        except Exception as e:
            print(f"Error logging parameters: {e}")

    def compare_parameters(self, params1, params2):
        """Compare two parameter sets and show differences."""
        diffs = []
        for k in params1:
            if params1[k] != params2.get(k):
                diffs.append(f"{k}: {params1[k]} (current) vs {params2.get(k)} (previous)")
        return diffs

    def show_parameter_monitor(self):
        """Show a real-time parameter monitor window."""
        if not hasattr(self, 'param_monitor'):
            self.param_monitor = ParameterMonitor(self)
        self.param_monitor.open_monitor()
    def __init__(self, root):
        self.root = root
        self.root.title("Strategy Parameters")

        # Indicator toggles
        self.use_macd = tk.BooleanVar(value=True)
        self.use_ema_crossover = tk.BooleanVar(value=True)
        self.use_rsi_filter = tk.BooleanVar(value=True)
        self.use_vwap = tk.BooleanVar(value=False)

        # MACD parameters
        self.macd_short_window = tk.IntVar(value=12)
        self.macd_long_window = tk.IntVar(value=26)
        self.macd_signal_window = tk.IntVar(value=9)
        # Indicator parameters
        self.atr_len = tk.IntVar(value=10)
        self.fast_ema = tk.IntVar(value=9)
        self.slow_ema = tk.IntVar(value=21)
        self.rsi_length = tk.IntVar(value=14)
        self.rsi_overbought = tk.IntVar(value=70)
        self.rsi_oversold = tk.IntVar(value=30)

        # Stop loss and targets
        self.base_sl_points = tk.IntVar(value=5)
        self.tp1_points = tk.IntVar(value=25)
        self.tp2_points = tk.IntVar(value=45)
        self.tp3_points = tk.IntVar(value=100)

        # Trail stop parameters
        self.use_trail_stop = tk.BooleanVar(value=True)
        self.trail_activation_points = tk.IntVar(value=1)
        self.trail_distance_points = tk.IntVar(value=3)

        # Buy buffer parameter
        self.buy_buffer = tk.IntVar(value=5)

        # Other parameters
        self.initial_capital = tk.IntVar(value=100000)
        self.exit_before_close = tk.IntVar(value=20)

        # Data file selection
        self.data_file = tk.StringVar()
        self.data_files = self.load_data_files()

        row = 0

        # Data file selection
        ttk.Label(root, text="Data File:").grid(row=row, column=0, sticky="e")
        self.data_file_dropdown = ttk.Combobox(root, textvariable=self.data_file, values=self.data_files, width=30)
        self.data_file_dropdown.grid(row=row, column=1)
        if self.data_files:
            self.data_file.set(self.data_files[0])  # Set default value if files are available
        self.data_file_dropdown.bind("<KeyRelease>", self.autocomplete)  # Bind autocomplete
        row += 1
        
        # Add option to use price_ticks.log
        ttk.Label(root, text="Or use price_ticks.log:").grid(row=row, column=0, sticky="e")
        self.use_ticks_log = tk.BooleanVar(value=False)
        ttk.Checkbutton(root, text="Use price_ticks.log instead", variable=self.use_ticks_log).grid(row=row, column=1, sticky="w")
        row += 1

        # Indicator toggles
        ttk.Label(root, text="Indicators:").grid(row=row, column=0, sticky="w")
        row += 1
        ttk.Checkbutton(root, text="MACD", variable=self.use_macd).grid(row=row, column=0, sticky="w")
        row += 1
        ttk.Checkbutton(root, text="EMA Crossover", variable=self.use_ema_crossover).grid(row=row, column=0, sticky="w")
        row += 1
        ttk.Checkbutton(root, text="RSI Filter", variable=self.use_rsi_filter).grid(row=row, column=0, sticky="w")
        row += 1
        ttk.Checkbutton(root, text="VWAP", variable=self.use_vwap).grid(row=row, column=0, sticky="w")
        row += 1
        # MACD parameters
        ttk.Label(root, text="MACD Short Window:").grid(row=row, column=0, sticky="e")
        ttk.Entry(root, textvariable=self.macd_short_window, width=6).grid(row=row, column=1)
        row += 1
        ttk.Label(root, text="MACD Long Window:").grid(row=row, column=0, sticky="e")
        ttk.Entry(root, textvariable=self.macd_long_window, width=6).grid(row=row, column=1)
        row += 1
        ttk.Label(root, text="MACD Signal Window:").grid(row=row, column=0, sticky="e")
        ttk.Entry(root, textvariable=self.macd_signal_window, width=6).grid(row=row, column=1)
        row += 1
        ttk.Label(root, text="Fast EMA:").grid(row=row, column=0, sticky="e")
        ttk.Entry(root, textvariable=self.fast_ema, width=6).grid(row=row, column=1)
        row += 1
        ttk.Label(root, text="Slow EMA:").grid(row=row, column=0, sticky="e")
        ttk.Entry(root, textvariable=self.slow_ema, width=6).grid(row=row, column=1)
        row += 1
        ttk.Label(root, text="RSI Length:").grid(row=row, column=0, sticky="e")
        ttk.Entry(root, textvariable=self.rsi_length, width=6).grid(row=row, column=1)
        row += 1
        ttk.Label(root, text="RSI Overbought:").grid(row=row, column=0, sticky="e")
        ttk.Entry(root, textvariable=self.rsi_overbought, width=6).grid(row=row, column=1)
        row += 1
        ttk.Label(root, text="RSI Oversold:").grid(row=row, column=0, sticky="e")
        ttk.Entry(root, textvariable=self.rsi_oversold, width=6).grid(row=row, column=1)
        row += 1

        # Stop loss and targets
        ttk.Label(root, text="Stop Loss Points:").grid(row=row, column=0, sticky="e")
        ttk.Entry(root, textvariable=self.base_sl_points, width=6).grid(row=row, column=1)
        row += 1
        ttk.Label(root, text="TP1 Points:").grid(row=row, column=0, sticky="e")
        ttk.Entry(root, textvariable=self.tp1_points, width=6).grid(row=row, column=1)
        row += 1
        ttk.Label(root, text="TP2 Points:").grid(row=row, column=0, sticky="e")
        ttk.Entry(root, textvariable=self.tp2_points, width=6).grid(row=row, column=1)
        row += 1
        ttk.Label(root, text="TP3 Points:").grid(row=row, column=0, sticky="e")
        ttk.Entry(root, textvariable=self.tp3_points, width=6).grid(row=row, column=1)
        row += 1

        # Trail stop parameters
        ttk.Label(root, text="Use Trail Stop:").grid(row=row, column=0, sticky="w")
        ttk.Checkbutton(root, text="Activate trail stop", variable=self.use_trail_stop).grid(row=row, column=1, sticky="w")
        row += 1
        ttk.Label(root, text="Trail Activation Points:").grid(row=row, column=0, sticky="e")
        ttk.Entry(root, textvariable=self.trail_activation_points, width=6).grid(row=row, column=1)
        row += 1
        ttk.Label(root, text="Trail Distance Points:").grid(row=row, column=0, sticky="e")
        ttk.Entry(root, textvariable=self.trail_distance_points, width=6).grid(row=row, column=1)
        row += 1

        # Buy buffer parameter
        ttk.Label(root, text="Buy Buffer (Points):").grid(row=row, column=0, sticky="e")
        ttk.Entry(root, textvariable=self.buy_buffer, width=6).grid(row=row, column=1)
        row += 1

        # Other parameters
        ttk.Label(root, text="Initial Capital:").grid(row=row, column=0, sticky="e")
        ttk.Entry(root, textvariable=self.initial_capital, width=10).grid(row=row, column=1)
        row += 1
        ttk.Label(root, text="Exit Before Close (min):").grid(row=row, column=0, sticky="e")
        ttk.Entry(root, textvariable=self.exit_before_close, width=6).grid(row=row, column=1)
        row += 1

        ttk.Button(root, text="Run Backtest", command=self.run_backtest).grid(row=row, column=0, columnspan=2, pady=10)

    def load_data_files(self):
        data_dir = os.path.join(os.path.dirname(__file__), "data")
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
            return []  # Return empty list if the directory doesn't exist

        files = [f for f in os.listdir(data_dir) if f.endswith(".csv")]
        return files

    def autocomplete(self, event):
        """Enables autocomplete for the file selection dropdown."""
        value = self.data_file.get().lower()
        if value == "":
            self.data_file_dropdown['values'] = self.data_files
        else:
            new_values = [f for f in self.data_files if value in f.lower()]
            self.data_file_dropdown['values'] = new_values

    def run_backtest(self):
        from backtest import run_backtest_from_file
        params = self.get_params_from_gui()
        errors = self.validate_parameters(params)
        if errors:
            messagebox.showerror("Parameter Validation Failed", "\n".join(errors))
            return
        self.log_parameters(params, run_type="backtest")
        # Parameter comparison feature
        previous_params = getattr(self, 'previous_params', None)
        if previous_params:
            diffs = self.compare_parameters(params, previous_params)
            if diffs:
                messagebox.showinfo("Parameter Comparison", "Differences from previous run:\n" + "\n".join(diffs))
        self.previous_params = params.copy()
        # Check if user wants to use price_ticks.log
        if self.use_ticks_log.get():
            ticks_log_path = os.path.join(os.path.dirname(__file__), "price_ticks.log")
            if not os.path.exists(ticks_log_path):
                messagebox.showerror("Error", "price_ticks.log not found in smartapi directory.")
                return
            try:
                results, saved_files = run_backtest_from_file(ticks_log_path, params, 'ticks')
            except Exception as e:
                messagebox.showerror("Error", f"Error running backtest on price_ticks.log: {e}")
                return
        else:
            selected_file = self.data_file.get()
            if not selected_file:
                messagebox.showerror("Error", "Please select a data file or check 'Use price_ticks.log'.")
                return
            csv_path = os.path.join(os.path.dirname(__file__), "data", selected_file)
            if not os.path.exists(csv_path):
                messagebox.showerror("Error", f"File not found: {selected_file}")
                return
            try:
                results, saved_files = run_backtest_from_file(csv_path, params, 'csv')
            except Exception as e:
                messagebox.showerror("Error", f"Error running backtest: {e}")
                return
        if "error" not in results:
            script_dir = os.path.dirname(__file__)
            results_dir = os.path.join(script_dir, "results")
            os.makedirs(results_dir, exist_ok=True)
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            trades_df = results['trades_df']
            if isinstance(trades_df, pd.DataFrame) and not trades_df.empty:
                trades_filename = os.path.join(results_dir, f"trades_{timestamp_str}.csv")
                trades_df.to_csv(trades_filename, index=False)
                print(f"\n[SUCCESS] Detailed trades saved to: {trades_filename}")
            stats = [
                ["Total Trades", results['total_trades']],
                ["Win Rate (%)", f"{results['win_rate']:.2f}"],
                ["Total P&L", f"{results['total_pnl']:.2f}"],
                ["Total Return (%)", f"{results['total_return']:.2f}"],
                ["Max Drawdown (%)", f"{results['max_drawdown']:.2f}"],
                ["Profit Factor", f"{results['profit_factor']:.2f}"],
                ["Avg Win", f"{results['avg_win']:.2f}"],
                ["Avg Loss", f"{results['avg_loss']:.2f}"],
            ]
            summary_filename = os.path.join(results_dir, f"summary_{timestamp_str}.csv")
            summary_df = pd.DataFrame(stats, columns=pd.Index(["Metric", "Value"]))
            summary_df.to_csv(summary_filename, index=False)
            print(f"[SUCCESS] Summary statistics saved to: {summary_filename}")
            msg = (
                f"Total Trades: {results['total_trades']}\n"
                f"Win Rate: {results['win_rate']:.2f}%\n"
                f"Total P&L: {results['total_pnl']:.2f}\n"
                f"Total Return: {results['total_return']:.2f}%\n"
                f"Max Drawdown: {results['max_drawdown']:.2f}%\n\n"
                f"Results saved to CSV files in the 'results' folder."
            )
            messagebox.showinfo("Backtest Results", msg)
            print("\n=== STRATEGY RESULTS ===")
            print(tabulate(stats, tablefmt="github"))
            if isinstance(results['trades_df'], pd.DataFrame) and len(results['trades_df']) > 0:
                print("\n=== SAMPLE TRADES ===")
                print(tabulate(
                    results['trades_df'][['entry_price', 'exit_price', 'pnl',
                                          'trade_duration', 'reason']].head(),
                    headers="keys", tablefmt="github"
                ))
            if hasattr(results, "action_logs") and results.get('action_logs'):
                print("\n=== TRADE ACTION LOGS ===")
                headers = ["Action", "Timestamp", "Price", "Size/Qty%", "PnL", "Reason"]
                print(tabulate(results['action_logs'], headers=headers, tablefmt="github"))
        else:
            messagebox.showerror("Backtest Error", results["error"])

class ParameterMonitor:
    """Real-time parameter monitoring window."""
    def __init__(self, parent_gui):
        self.parent_gui = parent_gui
        self.monitor_window = None
        self.is_monitoring = False
        self.update_interval = 1000  # 1 second
    def open_monitor(self):
        if self.monitor_window is not None:
            self.monitor_window.focus()
            return
        self.monitor_window = tk.Toplevel(self.parent_gui.root)
        self.monitor_window.title("Real-time Parameter Monitor")
        self.monitor_window.geometry("500x600")
        self.monitor_window.protocol("WM_DELETE_WINDOW", self.close_monitor)
        main_frame = tk.Frame(self.monitor_window)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        scrollbar = tk.Scrollbar(main_frame)
        scrollbar.pack(side="right", fill="y")
        self.text_widget = tk.Text(main_frame, wrap="word", yscrollcommand=scrollbar.set,
                                  font=('Courier', 10))
        self.text_widget.pack(fill="both", expand=True)
        scrollbar.config(command=self.text_widget.yview)
        button_frame = tk.Frame(self.monitor_window)
        button_frame.pack(fill="x", padx=10, pady=5)
        tk.Button(button_frame, text="📊 Refresh Now", 
                 command=self.update_display).pack(side="left", padx=5)
        tk.Button(button_frame, text="💾 Save to File", 
                 command=self.save_to_file).pack(side="left", padx=5)
        tk.Button(button_frame, text="🔄 Auto-refresh", 
                 command=self.toggle_auto_refresh).pack(side="left", padx=5)
        self.status_label = tk.Label(self.monitor_window, text="Manual refresh mode")
        self.status_label.pack(pady=5)
        self.update_display()
    def close_monitor(self):
        self.is_monitoring = False
        if self.monitor_window:
            self.monitor_window.destroy()
            self.monitor_window = None
    def toggle_auto_refresh(self):
        self.is_monitoring = not self.is_monitoring
        if self.is_monitoring:
            self.status_label.config(text="Auto-refresh: ON")
            self.auto_refresh()
        else:
            self.status_label.config(text="Auto-refresh: OFF")
    def auto_refresh(self):
        if self.is_monitoring and self.monitor_window:
            self.update_display()
            self.monitor_window.after(self.update_interval, self.auto_refresh)
    def update_display(self):
        if not self.monitor_window:
            return
        current_params = self.parent_gui.get_params_from_gui()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        param_lines = [f"{k}: {v}" for k, v in current_params.items()]
        display_text = f"REAL-TIME PARAMETER MONITOR\nLast Updated: {timestamp}\n{'='*50}\n" + "\n".join(param_lines) + "\n"
        self.text_widget.config(state="normal")
        self.text_widget.delete("1.0", tk.END)
        self.text_widget.insert("1.0", display_text)
        self.text_widget.config(state="disabled")
    def save_to_file(self):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"smartapi/parameter_snapshot_{timestamp}.txt"
            with open(filename, "w") as f:
                f.write(self.text_widget.get("1.0", tk.END))
            messagebox.showinfo("Saved", f"Parameter snapshot saved to {filename}")
        except Exception as err:
            messagebox.showerror("Error", f"Failed to save file: {err}")

if __name__ == "__main__":
    root = tk.Tk()
    app = StrategyParameterGUI(root)
    root.mainloop()
