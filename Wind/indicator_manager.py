import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional, List, Dict, Any, Union

# GUI parameter monitor (optional, for GUI integration)
try:
    import tkinter as tk
    from tkinter import messagebox
except ImportError:
    tk = None
    messagebox = None

class ParameterMonitor:
    """Real-time parameter monitoring window."""

    def __init__(self, parent_gui):
        self.parent_gui = parent_gui
        self.monitor_window = None
        self.is_monitoring = False
        self.update_interval = 1000  # 1 second

    def open_monitor(self):
        """Open the parameter monitor window."""
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

        self.text_widget = tk.Text(
            main_frame,
            wrap="word",
            yscrollcommand=scrollbar.set,
            font=('Courier', 10)
        )
        self.text_widget.pack(fill="both", expand=True)
        scrollbar.config(command=self.text_widget.yview)

        button_frame = tk.Frame(self.monitor_window)
        button_frame.pack(fill="x", padx=10, pady=5)

        tk.Button(
            button_frame,
            text="📊 Refresh Now",
            command=self.update_display
        ).pack(side="left", padx=5)
        tk.Button(
            button_frame,
            text="💾 Save to File",
            command=self.save_to_file
        ).pack(side="left", padx=5)
        tk.Button(
            button_frame,
            text="🔄 Auto-refresh",
            command=self.toggle_auto_refresh
        ).pack(side="left", padx=5)

        self.status_label = tk.Label(
            self.monitor_window,
            text="Manual refresh mode"
        )
        self.status_label.pack(pady=5)

        self.update_display()

    def close_monitor(self):
        """Close the monitor window."""
        self.is_monitoring = False
        if self.monitor_window:
            self.monitor_window.destroy()
            self.monitor_window = None

    def toggle_auto_refresh(self):
        """Toggle automatic refresh."""
        self.is_monitoring = not self.is_monitoring
        if self.is_monitoring:
            self.status_label.config(text="Auto-refresh: ON")
            self.auto_refresh()
        else:
            self.status_label.config(text="Auto-refresh: OFF")

    def auto_refresh(self):
        """Automatically refresh the display."""
        if self.is_monitoring and self.monitor_window:
            self.update_display()
            self.monitor_window.after(self.update_interval, self.auto_refresh)

    def update_display(self):
        """Update the parameter display."""
        if not self.monitor_window:
            return

        current_params = self.parent_gui.get_params_from_gui()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        bot_status = "Not Started"
        if hasattr(self.parent_gui, 'bot_instance') and self.parent_gui.bot_instance:
            if hasattr(self.parent_gui.bot_instance, 'is_running'):
                bot_status = "Running" if self.parent_gui.bot_instance.is_running else "Stopped"
            else:
                bot_status = "Running"

        display_text = f"""REAL-TIME PARAMETER MONITOR
Last Updated: {timestamp}
Bot Status: {bot_status}
{'='*50}

CURRENT GUI SETTINGS:
{'='*20}
Symbol: {getattr(self.parent_gui, 'symbol_var', None) and self.parent_gui.symbol_var.get() or 'Not selected'}
Token: {getattr(self.parent_gui, 'instrument_token', None) and self.parent_gui.instrument_token.get() or ''}
Exchange: {getattr(self.parent_gui, 'exchange_type', None) and self.parent_gui.exchange_type.get() or ''}
Feed Type: {getattr(self.parent_gui, 'feed_type', None) and self.parent_gui.feed_type.get() or ''}
Log Ticks: {getattr(self.parent_gui, 'log_ticks', None) and self.parent_gui.log_ticks.get() or ''}

INDICATORS STATUS:
{'='*18}
✓ MACD: {current_params.get('use_macd', '')} (Short: {current_params.get('macd_short_window', '')}, Long: {current_params.get('macd_long_window', '')}, Signal: {current_params.get('macd_signal_window', '')})
✓ EMA Crossover: {current_params.get('use_ema_crossover', '')} (Fast: {current_params.get('fast_ema', '')}, Slow: {current_params.get('slow_ema', '')})
✓ RSI Filter: {current_params.get('use_rsi_filter', '')} (Length: {current_params.get('rsi_length', '')}, OB: {current_params.get('rsi_overbought', '')}, OS: {current_params.get('rsi_oversold', '')})
✓ VWAP: {current_params.get('use_vwap', '')}

RISK PARAMETERS:
{'='*16}
Initial Capital: ₹{current_params.get('initial_capital', ''):,}
Risk per Trade: {current_params.get('risk_per_trade_percent', '')}%
Base SL: {current_params.get('base_sl_points', '')} points
TP1: {current_params.get('tp1_points', '')} | TP2: {current_params.get('tp2_points', '')} | TP3: {current_params.get('tp3_points', '')}

TRAILING STOP:
{'='*14}
Enabled: {current_params.get('use_trail_stop', '')}
Activation: {current_params.get('trail_activation_points', '')} points
Distance: {current_params.get('trail_distance_points', '')} points

OTHER SETTINGS:
{'='*15}
Exit Before Close: {current_params.get('exit_before_close', '')} minutes

"""
        self.text_widget.config(state="normal")
        self.text_widget.delete("1.0", tk.END)
        self.text_widget.insert("1.0", display_text)
        self.text_widget.config(state="disabled")

    def save_to_file(self):
        """Save current parameter state to file."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"smartapi/parameter_snapshot_{timestamp}.txt"
            with open(filename, "w") as f:
                f.write(self.text_widget.get("1.0", tk.END))
            messagebox.showinfo("Saved", f"Parameter snapshot saved to {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save file: {e}")

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
try:
    from .indicators import (
        MACDIndicator, EMAIndicator, RSIIndicator, VWAPIndicator,
        ATRIndicator, HTFTrendIndicator
    )
except ImportError:
    from indicators import (
        MACDIndicator, EMAIndicator, RSIIndicator, VWAPIndicator,
        ATRIndicator, HTFTrendIndicator
    )


class IndicatorManager:
    """Manages all indicators and their calculations."""
    
    def __init__(self, strategy_params: Dict[str, Any]):
        """Initialize the indicator manager with strategy parameters."""
        self.indicators: Dict[str, Any] = {}
        self.bar_history: List[Dict[str, Any]] = []
        self.current_bar_data: Dict[str, Any] = {
            'open': None, 'high': None, 'low': None, 'close': None, 
            'volume': 0, 'timestamp': None
        }
        self.last_processed_minute: Optional[datetime] = None
        self.max_bar_history_length = 100
        
        # Initialize indicators based on strategy parameters
        self._initialize_indicators(strategy_params)
    
    def _initialize_indicators(self, params: Dict[str, Any]) -> None:
        """Initialize indicators based on strategy parameters."""
        # MACD indicator
        if params.get('use_macd', True):
            self.indicators['macd'] = MACDIndicator(
                short_window=params.get('macd_short_window', 12),
                long_window=params.get('macd_long_window', 26),
                signal_window=params.get('macd_signal_window', 9),
                enabled=True
            )
        # VWAP indicator (tick-based)
        if params.get('use_vwap', True):
            self.indicators['vwap'] = VWAPIndicator(enabled=True)
        # EMA indicators
        if params.get('use_ema_crossover', True):
            self.indicators['ema_fast'] = EMAIndicator(
                period=params.get('fast_ema', 9),
                enabled=True
            )
            self.indicators['ema_slow'] = EMAIndicator(
                period=params.get('slow_ema', 21),
                enabled=True
            )
        # RSI indicator
        if params.get('use_rsi_filter', True):
            self.indicators['rsi'] = RSIIndicator(
                length=params.get('rsi_length', 14),
                enabled=True
            )
        # HTF Trend indicator
        if params.get('use_htf_trend', True):
            self.indicators['htf_trend'] = HTFTrendIndicator(
                period=params.get('htf_period', 20),
                enabled=True
            )
        # ATR indicator (for reference)
        self.indicators['atr'] = ATRIndicator(
            length=params.get('atr_len', 10),
            enabled=True
        )
    
    def update_current_bar(self, timestamp: datetime, price: float, volume: int) -> None:
        """Update the current bar being formed."""
        if self.current_bar_data['open'] is None:
            self.current_bar_data['open'] = price
            self.current_bar_data['high'] = price
            self.current_bar_data['low'] = price
            self.current_bar_data['timestamp'] = timestamp.replace(second=0, microsecond=0)
        else:
            self.current_bar_data['high'] = max(self.current_bar_data['high'], price)
            self.current_bar_data['low'] = min(self.current_bar_data['low'], price)
        
        self.current_bar_data['close'] = price
        self.current_bar_data['volume'] += volume
    
    def close_current_bar(self, bar_timestamp: datetime) -> None:
        """Close the current bar and add it to history."""
        if self.current_bar_data['open'] is None:
            return
        
        completed_bar = self.current_bar_data.copy()
        completed_bar['timestamp'] = bar_timestamp
        self.bar_history.append(completed_bar)
        
        # Maintain history length
        if len(self.bar_history) > self.max_bar_history_length:
            self.bar_history.pop(0)
        
        # Reset current bar
        self.current_bar_data = {
            'open': None, 'high': None, 'low': None, 'close': None, 
            'volume': 0, 'timestamp': None
        }
        
        # Calculate bar-based indicators
        self._calculate_bar_indicators()
    
    def _calculate_bar_indicators(self) -> None:
        """Calculate all bar-based indicators on the latest completed bar."""
        if not self.bar_history:
            return
        
        # Calculate each bar-based indicator
        for name, indicator in self.indicators.items():
            if hasattr(indicator, 'can_calculate') and indicator.can_calculate(self.bar_history):
                value = indicator.calculate(self.bar_history)
                # Store the value in the latest bar
                self.bar_history[-1][name] = value
    
    def update_tick_indicators(self, timestamp: datetime, price: float, volume: int) -> float:
        """Update tick-based indicators."""
        tick_data = {
            'price': price,
            'volume': volume,
            'timestamp': timestamp
        }
        
        # Update VWAP
        if 'vwap' in self.indicators:
            vwap_value = self.indicators['vwap'].calculate(tick_data)
            return vwap_value
        
        return np.nan
    
    def get_indicator_value(self, indicator_name: str) -> float:
        """Get the current value of a specific indicator."""
        if indicator_name in self.indicators:
            return self.indicators[indicator_name].get_value()
        return np.nan
    
    def get_latest_bar_data(self) -> Dict[str, Any]:
        """Get the latest completed bar data with all indicator values."""
        if self.bar_history:
            return self.bar_history[-1].copy()
        return {}
    
    def get_bar_history(self) -> List[Dict[str, Any]]:
        """Get the complete bar history."""
        return self.bar_history.copy()
    
    def get_bar_history_df(self) -> pd.DataFrame:
        """Get bar history as a pandas DataFrame."""
        if not self.bar_history:
            return pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
        
        df = pd.DataFrame(self.bar_history)
        if 'timestamp' in df.columns:
            df.set_index('timestamp', inplace=True)
            df.index = pd.to_datetime(df.index)
        return df
    
    def has_enough_history(self, min_bars: int) -> bool:
        """Check if we have enough bar history."""
        return len(self.bar_history) >= min_bars
    
    def reset_all_indicators(self) -> None:
        """Reset all indicators to their initial state."""
        for indicator in self.indicators.values():
            if hasattr(indicator, 'reset_state'):
                indicator.reset_state()
        
        self.bar_history = []
        self.current_bar_data = {
            'open': None, 'high': None, 'low': None, 'close': None, 
            'volume': 0, 'timestamp': None
        }
        self.last_processed_minute = None
    
    def get_enabled_indicators(self) -> List[str]:
        """Get list of enabled indicators."""
        return [name for name, indicator in self.indicators.items() if indicator.is_enabled()]
    
    def enable_indicator(self, indicator_name: str) -> None:
        """Enable a specific indicator."""
        if indicator_name in self.indicators:
            self.indicators[indicator_name].enable()
    
    def disable_indicator(self, indicator_name: str) -> None:
        """Disable a specific indicator."""
        if indicator_name in self.indicators:
            self.indicators[indicator_name].disable()
    
    def add_indicator(self, name: str, indicator: Any) -> None:
        """Add a new indicator to the manager."""
        self.indicators[name] = indicator
    
    def remove_indicator(self, name: str) -> None:
        """Remove an indicator from the manager."""
        if name in self.indicators:
            del self.indicators[name]
    
    def is_ema_positive_signal(self, points_threshold: float) -> bool:
        """Returns True if fast EMA is more than points_threshold above slow EMA."""
        ema_fast = self.get_indicator_value('ema_fast')
        ema_slow = self.get_indicator_value('ema_slow')
        if ema_fast is not None and ema_slow is not None:
            return (ema_fast - ema_slow) > points_threshold
        return False