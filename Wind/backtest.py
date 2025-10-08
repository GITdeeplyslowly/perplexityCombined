import pandas as pd
import numpy as np
from datetime import datetime, time, timedelta
import pytz
import warnings
import os
warnings.filterwarnings('ignore')
from tabulate import tabulate

class IndependentBacktestEngine:
    """
    Independent backtesting engine that doesn't depend on strategy.py.
    Implements its own backtesting logic for modularity.
    """
    def __init__(self, params=None):
        self.params = params or {}
        self.ist_tz = pytz.timezone('Asia/Kolkata')
        
        # Initialize strategy parameters from params
        self.use_supertrend = self.params.get('use_supertrend', True)
        self.use_ema_crossover = self.params.get('use_ema_crossover', True)
        self.use_rsi_filter = self.params.get('use_rsi_filter', True)
        self.use_vwap = self.params.get('use_vwap', True)
        
        # Indicator parameters
        self.atr_len = self.params.get('atr_len', 10)
        self.atr_mult = self.params.get('atr_mult', 3.0)
        self.fast_ema = self.params.get('fast_ema', 9)
        self.slow_ema = self.params.get('slow_ema', 21)
        self.rsi_length = self.params.get('rsi_length', 14)
        self.rsi_overbought = self.params.get('rsi_overbought', 70)
        self.rsi_oversold = self.params.get('rsi_oversold', 30)
        
        # Trading parameters
        self.base_sl_points = self.params.get('base_sl_points', 10)
        self.tp1_points = self.params.get('tp1_points', 10)
        self.tp2_points = self.params.get('tp2_points', 25)
        self.tp3_points = self.params.get('tp3_points', 50)
        self.initial_capital = self.params.get('initial_capital', 100000)
        self.exit_before_close = self.params.get('exit_before_close', 20)
        
        # Trailing stop parameters
        self.use_trail_stop = self.params.get('use_trail_stop', True)
        self.trail_activation_points = self.params.get('trail_activation_points', 5)
        self.trail_distance_points = self.params.get('trail_distance_points', 7)
        
        # Buy buffer parameter
        self.buy_buffer = self.params.get('buy_buffer', 0)

        # Pending buy state
        self.pending_buy_signal = None  # {'price': X, 'timestamp': Y, 'bar_data': ...}
        
        # Risk management
        self.risk_per_trade_percent = 1.0
        
        # Re-entry parameters
        self.reentry_price_buffer = 5
        self.reentry_momentum_lookback = 3
        self.reentry_min_green_candles = 1
        
        # Trading session parameters
        self.intraday_start_hour = 9
        self.intraday_start_min = 15
        self.intraday_end_hour = 15
        self.intraday_end_min = 15
        
        # Reset state
        self.reset_state()
        
    def reset_state(self):
        """Reset all trading state variables."""
        self.current_equity = self.initial_capital
        self.position_size = 0
        self.position_entry_price = 0
        self.position_entry_time = None
        self.position_high_price = 0
        self.base_stop_price = 0
        self.trail_stop_price = 0
        self.trailing_active = False
        self.tp1_filled = 0.0
        self.tp2_filled = 0.0
        self.last_exit_price = None
        self.last_entry_price = None
        self.last_exit_reason = ""
        self.last_time_exit_date = None
        
        # Results tracking
        self.trades = []
        self.equity_curve = []
        self.action_logs = []
        
        # Indicator data
        self.bar_history = []
        self.current_bar = None
        
    def load_csv_data(self, csv_path):
        """Load data from CSV file with standard OHLCV format."""
        try:
            df = pd.read_csv(
                csv_path,
                parse_dates=['timestamp'],
                date_parser=lambda x: pd.to_datetime(x, format='%Y%m%d %H:%M')
            )
            df.set_index('timestamp', inplace=True)
            return df
        except Exception as e:
            raise Exception(f"Error loading CSV data: {e}")
    
    def load_ticks_log(self, log_path):
        """Load data from price_ticks.log file and convert to OHLCV format."""
        if not os.path.exists(log_path):
            raise FileNotFoundError(f"Price ticks log file not found: {log_path}")
        
        print(f"Loading tick data from: {log_path}")
        
        # Get file size for progress tracking
        file_size = os.path.getsize(log_path)
        print(f"File size: {file_size / (1024*1024):.2f} MB")
        
        # Use pandas to read the file more efficiently
        try:
            # Read the file in chunks to avoid memory issues
            chunk_size = 10000  # Read 10k lines at a time
            chunks = []
            
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines_processed = 0
                chunk_data = []
                
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        # Parse: timestamp,price,volume
                        parts = line.split(',')
                        if len(parts) >= 2:
                            timestamp_str = parts[0]
                            price = float(parts[1])
                            volume = int(parts[2]) if len(parts) > 2 else 0
                            
                            # Parse timestamp (handle timezone)
                            if 'T' in timestamp_str:
                                # ISO format: 2025-07-03T09:22:58+05:30
                                timestamp = pd.to_datetime(timestamp_str)
                            else:
                                # Fallback format
                                timestamp = pd.to_datetime(timestamp_str)
                            
                            chunk_data.append({
                                'timestamp': timestamp,
                                'price': price,
                                'volume': volume
                            })
                            
                            lines_processed += 1
                            
                            # Process chunk when it reaches chunk_size
                            if len(chunk_data) >= chunk_size:
                                df_chunk = pd.DataFrame(chunk_data)
                                chunks.append(df_chunk)
                                chunk_data = []
                                
                                # Progress indicator
                                if lines_processed % 50000 == 0:
                                    print(f"Processed {lines_processed} lines...")
                    
                    except Exception as e:
                        # Skip problematic lines silently
                        continue
            
            # Add remaining data
            if chunk_data:
                df_chunk = pd.DataFrame(chunk_data)
                chunks.append(df_chunk)
            
            if not chunks:
                raise Exception("No valid tick data found in log file")
            
            # Combine all chunks
            df_ticks = pd.concat(chunks, ignore_index=True)
            df_ticks.set_index('timestamp', inplace=True)
            
            print(f"Loaded {len(df_ticks)} ticks from {df_ticks.index.min()} to {df_ticks.index.max()}")
            
            # Resample to 1-minute OHLCV bars
            print("Converting to 1-minute bars...")
            df_ohlcv = df_ticks['price'].resample('1T').ohlc()
            df_volume = df_ticks['volume'].resample('1T').sum()
            
            # Combine OHLC and volume
            if not isinstance(df_ohlcv, pd.DataFrame):
                df_ohlcv = pd.DataFrame(df_ohlcv)
            if not isinstance(df_volume, pd.DataFrame):
                df_volume = pd.DataFrame(df_volume)
            df = pd.concat([df_ohlcv, df_volume], axis=1)
            df.columns = ['open', 'high', 'low', 'close', 'volume']
            
            # Forward fill any missing values
            df = df.fillna(method='ffill')
            
            # Remove any remaining NaN rows
            df = df.dropna()
            
            print(f"Converted to {len(df)} 1-minute OHLCV bars")
            return df
            
        except Exception as e:
            print(f"Error in optimized loading: {e}")
            print("Falling back to original method...")
            return self._load_ticks_log_original(log_path)
    
    def _load_ticks_log_original(self, log_path):
        """Original tick loading method as fallback."""
        ticks_data = []
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                    
                try:
                    # Parse: timestamp,price,volume
                    parts = line.split(',')
                    if len(parts) >= 2:
                        timestamp_str = parts[0]
                        price = float(parts[1])
                        volume = int(parts[2]) if len(parts) > 2 else 0
                        
                        # Parse timestamp (handle timezone)
                        if 'T' in timestamp_str:
                            # ISO format: 2025-07-03T09:22:58+05:30
                            timestamp = pd.to_datetime(timestamp_str)
                        else:
                            # Fallback format
                            timestamp = pd.to_datetime(timestamp_str)
                        
                        ticks_data.append({
                            'timestamp': timestamp,
                            'price': price,
                            'volume': volume
                        })
                        
                except Exception as e:
                    print(f"Warning: Skipping line {line_num}: {line} - Error: {e}")
                    continue
        
        if not ticks_data:
            raise Exception("No valid tick data found in log file")
        
        # Convert to DataFrame
        df_ticks = pd.DataFrame(ticks_data)
        df_ticks.set_index('timestamp', inplace=True)
        
        print(f"Loaded {len(df_ticks)} ticks from {df_ticks.index.min()} to {df_ticks.index.max()}")
        
        # Resample to 1-minute OHLCV bars
        df_ohlcv = df_ticks['price'].resample('1T').ohlc()
        df_volume = df_ticks['volume'].resample('1T').sum()
        
        # Combine OHLC and volume
        if not isinstance(df_ohlcv, pd.DataFrame):
            df_ohlcv = pd.DataFrame(df_ohlcv)
        if not isinstance(df_volume, pd.DataFrame):
            df_volume = pd.DataFrame(df_volume)
        df = pd.concat([df_ohlcv, df_volume], axis=1)
        df.columns = ['open', 'high', 'low', 'close', 'volume']
        
        # Forward fill any missing values
        df = df.fillna(method='ffill')
        
        # Remove any remaining NaN rows
        df = df.dropna()
        
        print(f"Converted to {len(df)} 1-minute OHLCV bars")
        return df
    
    def calculate_indicators(self, bar_data):
        """Calculate indicators for the given bar data."""
        if len(self.bar_history) < max(self.atr_len, self.rsi_length, self.slow_ema):
            return {}
        
        # Calculate EMAs
        ema_fast = self._calculate_ema(self.fast_ema)
        ema_slow = self._calculate_ema(self.slow_ema)
        
        # Calculate RSI
        rsi = self._calculate_rsi()
        
        # Calculate Supertrend
        supertrend = self._calculate_supertrend()
        
        # Calculate VWAP
        vwap = self._calculate_vwap()
        
        return {
            'ema_fast': ema_fast,
            'ema_slow': ema_slow,
            'ema_bull': ema_fast > ema_slow if ema_fast is not None and ema_slow is not None else False,
            'rsi': rsi,
            'supertrend': supertrend,
            'vwap': vwap,
            'vwap_bull': bar_data['close'] > vwap if vwap is not None else False
        }
    
    def _calculate_ema(self, period):
        """Calculate EMA for the given period."""
        if len(self.bar_history) < period:
            return None
        
        prices = [bar['close'] for bar in self.bar_history[-period:]]
        alpha = 2.0 / (period + 1)
        ema = prices[0]
        for price in prices[1:]:
            ema = alpha * price + (1 - alpha) * ema
        return ema
    
    def _calculate_rsi(self):
        """Calculate RSI."""
        if len(self.bar_history) < self.rsi_length + 1:
            return 50
        
        prices = [bar['close'] for bar in self.bar_history[-self.rsi_length-1:]]
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_supertrend(self):
        """Calculate Supertrend indicator."""
        if len(self.bar_history) < self.atr_len:
            return 0
        
        # Calculate ATR
        highs = [bar['high'] for bar in self.bar_history[-self.atr_len:]]
        lows = [bar['low'] for bar in self.bar_history[-self.atr_len:]]
        closes = [bar['close'] for bar in self.bar_history[-self.atr_len:]]
        
        tr_values = []
        for i in range(1, len(highs)):
            tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
            tr_values.append(tr)
        
        atr = np.mean(tr_values)
        
        # Calculate Supertrend
        current_close = self.bar_history[-1]['close']
        current_high = self.bar_history[-1]['high']
        current_low = self.bar_history[-1]['low']
        
        upper_band = (current_high + current_low) / 2 + (self.atr_mult * atr)
        lower_band = (current_high + current_low) / 2 - (self.atr_mult * atr)
        
        # Simple Supertrend logic
        if current_close > upper_band:
            return 1  # Bullish
        elif current_close < lower_band:
            return -1  # Bearish
        else:
            return 0  # Neutral
    
    def _calculate_vwap(self):
        """Calculate VWAP."""
        if not self.bar_history:
            return None
        
        total_pv = 0
        total_volume = 0
        
        for bar in self.bar_history:
            typical_price = (bar['high'] + bar['low'] + bar['close']) / 3
            total_pv += typical_price * bar['volume']
            total_volume += bar['volume']
        
        if total_volume == 0:
            return None
        
        return total_pv / total_volume
    
    def is_in_session(self, timestamp):
        """Check if timestamp is within trading session."""
        ist_time = timestamp.astimezone(self.ist_tz).time()
        start_time = time(self.intraday_start_hour, self.intraday_start_min)
        end_time = time(self.intraday_end_hour, self.intraday_end_min)
        return start_time <= ist_time <= end_time
    
    def is_near_session_end(self, timestamp):
        """Check if we're near session end."""
        t = timestamp.astimezone(self.ist_tz)
        end_time = t.replace(hour=self.intraday_end_hour, minute=self.intraday_end_min, second=0, microsecond=0)
        time_to_end = (end_time - t).total_seconds() / 60
        return 0 < time_to_end <= self.exit_before_close
    
    def should_allow_new_entries(self, timestamp):
        """Check if new entries are allowed."""
        t = timestamp.astimezone(self.ist_tz)
        end_time = t.replace(hour=self.intraday_end_hour, minute=self.intraday_end_min, second=0, microsecond=0)
        time_to_end = (end_time - t).total_seconds() / 60
        return time_to_end > (self.exit_before_close + 30)
    
    def can_reenter(self, current_price, timestamp, indicators):
        """Check if re-entry is allowed based on previous exit reason and new conditions."""
        if self.last_exit_price is None:
            return True

        # Reset time-based exit restrictions on new trading days
        if self.last_time_exit_date is not None and timestamp.date() > self.last_time_exit_date:
            self.last_exit_reason = ""
            self.last_time_exit_date = None

        if self.last_exit_reason == "time" and self.last_time_exit_date == timestamp.date():
            return False

        if self.last_entry_price is not None:
            if not (current_price > (self.last_entry_price + self.reentry_price_buffer)):
                return False
            if self.use_ema_crossover and not indicators.get('ema_bull', False):
                return False

            # Check VWAP and Supertrend conditions
            vwap_bull = indicators.get('vwap_bull', False)
            supertrend_bull = indicators.get('supertrend') == 1
            
            indicator_bullish_check = (self.use_vwap and vwap_bull) or \
                                      (self.use_supertrend and supertrend_bull)
            if not indicator_bullish_check:
                return False

            # Check re-entry momentum (simplified version)
            if len(self.bar_history) >= self.reentry_momentum_lookback + 1:
                recent_bars = self.bar_history[-self.reentry_momentum_lookback:]
                price_increase = recent_bars[-1]['close'] > recent_bars[0]['close']
                green_candles = sum(1 for bar in recent_bars if bar['close'] > bar['open'])
                
                if not (price_increase and green_candles >= self.reentry_min_green_candles):
                    return False
            
            return True
        return False
    
    def enter_position(self, price, timestamp, reason="Buy Signal"):
        """Enter a long position and set up dual stop loss system"""
        if self.position_size == 0:
            capital_to_risk = self.current_equity * (self.risk_per_trade_percent / 100.0)
            position_size = int(capital_to_risk / self.base_sl_points)
            
            if position_size == 0:
                position_size = 1
            
            self.position_size = position_size
            self.position_entry_price = price
            self.position_entry_time = timestamp
            self.position_high_price = price
            self.base_stop_price = price - self.base_sl_points
            self.trail_stop_price = 0
            self.trailing_active = False
            self.tp1_filled = 0.0
            self.tp2_filled = 0.0
            
            log = ["ENTRY", timestamp, f"{price:.2f}", f"{self.position_size}", f"Base SL: {self.base_stop_price:.2f}", reason]
            self.action_logs.append(log)
            print(f"ENTRY: {timestamp} - Price: {price:.2f} - Size: {self.position_size}")
            print(f"  └─ BASE STOP (Fixed): {self.base_stop_price:.2f}")
            print(f"  └─ TRAIL STOP: Inactive (activates at +{self.trail_activation_points} points)")
    
    def update_trailing_stop(self, current_price, timestamp):
        """Update trailing stop loss based on current price"""
        if not self.use_trail_stop or self.position_size <= 0:
            return
            
        if current_price > self.position_high_price:
            self.position_high_price = current_price
            
        profit_points = current_price - self.position_entry_price
        
        if not self.trailing_active and profit_points >= self.trail_activation_points:
            self.trailing_active = True
            self.trail_stop_price = self.position_high_price - self.trail_distance_points
            print(f"TRAIL ACTIVATED: {timestamp} - Trail Stop: {self.trail_stop_price:.2f}")
        elif self.trailing_active:
            new_trail_stop = self.position_high_price - self.trail_distance_points
            if new_trail_stop > self.trail_stop_price:
                old_trail = self.trail_stop_price
                self.trail_stop_price = new_trail_stop
                print(f"TRAIL UPDATED: {old_trail:.2f} -> {self.trail_stop_price:.2f} (High: {self.position_high_price:.2f})")
    
    def get_effective_stop_price(self):
        """Get the higher of the base stop and the trail stop."""
        if not self.trailing_active or self.trail_stop_price <= 0:
            return self.base_stop_price
        return max(self.base_stop_price, self.trail_stop_price)
    
    def check_stop_loss_hit(self, current_price):
        """Check if any stop loss has been hit."""
        effective_stop = self.get_effective_stop_price()
        if current_price <= effective_stop:
            reason = "Trail Stop Loss" if self.trailing_active and self.trail_stop_price > self.base_stop_price else "Base Stop Loss"
            return True, reason
        return False, ""
    
    def exit_position(self, price, timestamp, qty_percent=100, reason="Exit", exit_classification=None):
        """Exit position (partial or full)."""
        if self.position_size > 0:
            exit_qty = self.position_size * (qty_percent / 100)
            if exit_qty > self.position_size:
                exit_qty = self.position_size
            
            pnl = (price - self.position_entry_price) * exit_qty
            self.current_equity += pnl
            self.position_size -= exit_qty
            
            log = ["EXIT", timestamp, f"{price:.2f}", f"{qty_percent}%", f"{pnl:.2f}", reason]
            self.action_logs.append(log)
            print(f"EXIT: {timestamp} - Price: {price:.2f} - Qty%: {qty_percent}% - PnL: {pnl:.2f} - Reason: {reason}")
            
            trade = {
                'entry_time': self.position_entry_time,
                'exit_time': timestamp,
                'entry_price': self.position_entry_price,
                'exit_price': price,
                'quantity': exit_qty,
                'pnl': pnl,
                'reason': reason
            }
            self.trades.append(trade)
            
            self.equity_curve.append({'timestamp': timestamp, 'equity': self.current_equity})

            if self.position_size <= 1e-9:  # Effectively zero
                self.last_exit_price = price
                self.last_entry_price = self.position_entry_price
                if exit_classification:
                    self.last_exit_reason = exit_classification
                self._reset_position_state()
    
    def _reset_position_state(self):
        """Reset position-related variables after a full exit."""
        self.position_size = 0
        self.position_entry_time = None
        self.position_high_price = 0
        self.base_stop_price = 0
        self.trail_stop_price = 0
        self.trailing_active = False
        self.tp1_filled = 0.0
        self.tp2_filled = 0.0
    
    def process_bar(self, timestamp, bar_data):
        """Process a single bar through the strategy."""
        # Add bar to history
        self.bar_history.append(bar_data)
        
        # Keep only recent bars for memory efficiency
        max_bars = max(self.atr_len, self.rsi_length, self.slow_ema, 50)
        if len(self.bar_history) > max_bars:
            self.bar_history = self.bar_history[-max_bars:]
        
        # Calculate indicators
        indicators = self.calculate_indicators(bar_data)
        
        # Check if we have enough history
        has_enough_history = len(self.bar_history) >= max(self.atr_len, self.rsi_length, self.slow_ema, 20)
        
        # ENTRY LOGIC
        if self.position_size == 0 and self.should_allow_new_entries(timestamp) and has_enough_history:
            buy_signal = True
            
            # Check Supertrend
            if self.use_supertrend and indicators.get('supertrend') != 1:
                buy_signal = False
            
            # Check VWAP
            if self.use_vwap and not indicators.get('vwap_bull', False):
                buy_signal = False
            
            # Check EMA crossover
            if self.use_ema_crossover and not indicators.get('ema_bull', False):
                buy_signal = False
            
            # Check RSI filter
            if self.use_rsi_filter:
                rsi_value = indicators.get('rsi', 50)
                if not (self.rsi_oversold < rsi_value < self.rsi_overbought):
                    buy_signal = False
            
            # Check HTF trend (simplified - using EMA trend)
            if not indicators.get('ema_bull', False):
                buy_signal = False
            
            can_reenter_flag = self.can_reenter(bar_data['close'], timestamp, indicators)
            
            if buy_signal and can_reenter_flag:
                # If buffer is 0, enter immediately
                if self.buy_buffer == 0:
                    self.enter_position(bar_data['close'], timestamp, "Immediate Entry (No Buffer)")
                else:
                    # Instead of entering immediately, set a pending buy trigger
                    self.pending_buy_signal = {
                        'signal_price': bar_data['close'],
                        'timestamp': timestamp,
                        'bar_data': bar_data.copy(),
                        'indicators': indicators.copy()
                    }
                    print(f"BUFFER SIGNAL SET: {timestamp} - Signal Price: {bar_data['close']:.2f}, Buffer: {self.buy_buffer}, Trigger Price: {bar_data['close'] + self.buy_buffer:.2f}")
            else:
                self.pending_buy_signal = None
        else:
            self.pending_buy_signal = None

        # If a pending buy exists, check if buffer is hit and signal is still valid
        if self.pending_buy_signal and self.position_size == 0:
            trigger_price = self.pending_buy_signal['signal_price'] + self.buy_buffer
            if bar_data['high'] >= trigger_price:
                print(f"BUFFER TRIGGERED: {timestamp} - High: {bar_data['high']:.2f} >= Trigger: {trigger_price:.2f}")
                # Re-check all buy conditions at this bar
                still_valid = True
                # (Repeat indicator checks as above)
                if self.use_supertrend and indicators.get('supertrend') != 1:
                    still_valid = False
                if self.use_vwap and not indicators.get('vwap_bull', False):
                    still_valid = False
                if self.use_ema_crossover and not indicators.get('ema_bull', False):
                    still_valid = False
                if self.use_rsi_filter:
                    rsi_value = indicators.get('rsi', 50)
                    if not (self.rsi_oversold < rsi_value < self.rsi_overbought):
                        still_valid = False
                if not indicators.get('ema_bull', False):
                    still_valid = False
                can_reenter_flag = self.can_reenter(bar_data['close'], timestamp, indicators)
                if not can_reenter_flag:
                    still_valid = False
                if still_valid:
                    # Use the actual high price that triggered the entry, not the trigger price
                    actual_entry_price = min(bar_data['high'], trigger_price)
                    self.enter_position(actual_entry_price, timestamp, f"Buffer Entry (Signal: {self.pending_buy_signal['signal_price']:.2f}, Buffer: {self.buy_buffer}, Trigger: {trigger_price:.2f})")
                    self.pending_buy_signal = None
                else:
                    self.pending_buy_signal = None
        
        # POSITION MANAGEMENT
        if self.position_size > 0:
            if self.is_near_session_end(timestamp):
                self.exit_position(bar_data['close'], timestamp, 100, "MANDATORY: Session End", "time")
                self.last_time_exit_date = timestamp.date()
                return

            self.update_trailing_stop(bar_data['close'], timestamp)
            
            stop_hit, stop_reason = self.check_stop_loss_hit(bar_data['close'])
            if stop_hit:
                self.exit_position(bar_data['close'], timestamp, 100, f"MANDATORY: {stop_reason}", stop_reason)
                return
            
            # Take profit logic
            entry_price = self.position_entry_price
            if self.tp1_filled == 0 and bar_data['close'] >= entry_price + self.tp1_points:
                self.exit_position(bar_data['close'], timestamp, 50, "TP1-Quick")
                self.tp1_filled = 1
            
            if self.tp2_filled == 0 and self.tp1_filled > 0 and self.position_size > 0 and bar_data['close'] >= entry_price + self.tp2_points:
                self.exit_position(bar_data['close'], timestamp, 60, "TP2-Medium")
                self.tp2_filled = 1
            
            if self.tp2_filled > 0 and self.position_size > 0 and bar_data['close'] >= entry_price + self.tp3_points:
                self.exit_position(bar_data['close'], timestamp, 100, "TP3-Runner", "profit")
                return
    
    def run_backtest(self, data_source, data_type='csv'):
        """Run backtest on the provided data source."""
        print(f"Starting backtest with {data_type} data source: {data_source}")
        print(f"Buy Buffer Setting: {self.buy_buffer} points")
        if self.buy_buffer > 0:
            print(f"  └─ Buffer Mode: Wait for price to move up {self.buy_buffer} points before entry")
        else:
            print(f"  └─ Buffer Mode: Immediate entry on signal")
        
        # Reset state
        self.reset_state()
        
        # Load data based on type
        if data_type == 'csv':
            df = self.load_csv_data(data_source)
        elif data_type == 'ticks':
            df = self.load_ticks_log(data_source)
        else:
            raise ValueError("data_type must be 'csv' or 'ticks'")
        
        # Ensure timezone is set
        if isinstance(df.index, pd.DatetimeIndex) and df.index.tz is None:
            df.index = df.index.tz_localize(self.ist_tz)
        
        print(f"Data loaded: {len(df)} bars from {df.index.min()} to {df.index.max()}")
        
        # Process each bar through the strategy
        print("Processing bars through strategy...")
        
        for i, (timestamp, row) in enumerate(df.iterrows()):
            bar_data = {
                'open': row['open'],
                'high': row['high'],
                'low': row['low'],
                'close': row['close'],
                'volume': row['volume']
            }
            self.process_bar(timestamp, bar_data)
        
        print("Backtest completed!")
        return self.generate_results()
    
    def generate_results(self):
        """Generate strategy results and statistics."""
        if not self.trades:
            return {"error": "No trades executed"}
        
        trades_df = pd.DataFrame(self.trades)
        trades_df['trade_duration'] = trades_df['exit_time'] - trades_df['entry_time']

        equity_df = pd.DataFrame(self.equity_curve)
        
        total_trades = len(trades_df)
        winning_trades = len(trades_df[trades_df['pnl'] > 0])
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
        
        total_pnl = trades_df['pnl'].sum()
        gross_profit = trades_df[trades_df['pnl'] > 0]['pnl'].sum()
        gross_loss = abs(trades_df[trades_df['pnl'] < 0]['pnl'].sum())
        
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        high_water_mark = equity_df['equity'].cummax()
        drawdown = (high_water_mark - equity_df['equity']) / high_water_mark
        max_drawdown = drawdown.max() * 100
        
        final_equity = self.current_equity
        total_return = ((final_equity - self.initial_capital) / self.initial_capital) * 100
        
        # Calculate average win and loss
        winning_trades_df = trades_df[trades_df['pnl'] > 0]
        losing_trades_df = trades_df[trades_df['pnl'] < 0]
        
        avg_win = winning_trades_df['pnl'].mean() if len(winning_trades_df) > 0 else 0
        avg_loss = losing_trades_df['pnl'].mean() if len(losing_trades_df) > 0 else 0
        
        return {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown,
            'total_return': total_return,
            'final_equity': final_equity,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'trades_df': trades_df,
            'equity_df': equity_df,
            'action_logs': self.action_logs
        }
    
    def save_results(self, results, output_dir="smartapi/results"):
        """Save backtest results to files."""
        if "error" in results:
            print(f"Error in results: {results['error']}")
            return
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save trades
        if 'trades_df' in results and not results['trades_df'].empty:
            trades_filename = os.path.join(output_dir, f"backtest_trades_{timestamp_str}.csv")
            results['trades_df'].to_csv(trades_filename, index=False)
            print(f"Trades saved to: {trades_filename}")
        
        # Save equity curve
        if 'equity_df' in results and not results['equity_df'].empty:
            equity_filename = os.path.join(output_dir, f"backtest_equity_{timestamp_str}.csv")
            results['equity_df'].to_csv(equity_filename, index=False)
            print(f"Equity curve saved to: {equity_filename}")
        
        # Save summary
        summary_data = [
            ["Total Trades", results['total_trades']],
            ["Win Rate (%)", f"{results['win_rate']:.2f}"],
            ["Total P&L", f"{results['total_pnl']:.2f}"],
            ["Total Return (%)", f"{results['total_return']:.2f}"],
            ["Max Drawdown (%)", f"{results['max_drawdown']:.2f}"],
            ["Profit Factor", f"{results['profit_factor']:.2f}"],
            ["Final Equity", f"{results['final_equity']:.2f}"]
        ]
        
        summary_filename = os.path.join(output_dir, f"backtest_summary_{timestamp_str}.csv")
        summary_df = pd.DataFrame(summary_data, columns=pd.Index(["Metric", "Value"]))
        summary_df.to_csv(summary_filename, index=False)
        print(f"Summary saved to: {summary_filename}")
        
        return {
            'trades_file': trades_filename if 'trades_df' in results else None,
            'equity_file': equity_filename if 'equity_df' in results else None,
            'summary_file': summary_filename
        }
    
    def print_results(self, results):
        """Print backtest results in a formatted table."""
        if "error" in results:
            print(f"Backtest Error: {results['error']}")
            return
        
        print("\n" + "="*60)
        print("BACKTEST RESULTS")
        print("="*60)
        
        # Summary statistics
        summary = [
            ["Total Trades", results['total_trades']],
            ["Win Rate", f"{results['win_rate']:.2f}%"],
            ["Total P&L", f"₹{results['total_pnl']:,.2f}"],
            ["Total Return", f"{results['total_return']:.2f}%"],
            ["Max Drawdown", f"{results['max_drawdown']:.2f}%"],
            ["Profit Factor", f"{results['profit_factor']:.2f}"],
            ["Final Equity", f"₹{results['final_equity']:,.2f}"]
        ]
        
        print(tabulate(summary, headers=["Metric", "Value"], tablefmt="grid"))
        
        # Sample trades
        if 'trades_df' in results and not results['trades_df'].empty:
            print(f"\nSample Trades (showing first 5 of {len(results['trades_df'])}):")
            sample_trades = results['trades_df'][['entry_time', 'exit_time', 'entry_price', 'exit_price', 'pnl', 'reason']].head()
            print(tabulate(sample_trades, headers="keys", tablefmt="grid"))
        
        # Action logs
        if 'action_logs' in results and results['action_logs']:
            print(f"\nTrade Action Logs (showing last 10 of {len(results['action_logs'])}):")
            headers = ["Action", "Timestamp", "Price", "Size/Qty%", "PnL", "Reason"]
            recent_logs = results['action_logs'][-10:]
            print(tabulate(recent_logs, headers=headers, tablefmt="grid"))


def run_backtest_from_file(data_file, params=None, data_type='auto'):
    """
    Convenience function to run backtest from a file.
    
    Args:
        data_file: Path to the data file
        params: Strategy parameters dictionary
        data_type: 'csv', 'ticks', or 'auto' (auto-detect based on file extension)
    """
    # Auto-detect data type
    if data_type == 'auto':
        if data_file.endswith('.log'):
            data_type = 'ticks'
        elif data_file.endswith('.csv'):
            data_type = 'csv'
        else:
            raise ValueError("Cannot auto-detect data type. Please specify 'csv' or 'ticks'")
    
    # Create backtest engine
    engine = IndependentBacktestEngine(params=params)
    
    # Run backtest
    results = engine.run_backtest(data_file, data_type)
    
    # Print and save results
    engine.print_results(results)
    saved_files = engine.save_results(results)
    
    return results, saved_files


if __name__ == "__main__":
    # Example usage
    print("Independent Backtest Engine - Example Usage")
    print("="*50)
    
    # Example 1: Backtest with CSV file
    print("\n1. Running backtest with CSV file...")
    try:
        csv_params = {
            'use_supertrend': True,
            'use_ema_crossover': True,
            'use_rsi_filter': True,
            'use_vwap': True,
            'initial_capital': 100000,
            'base_sl_points': 10,
            'tp1_points': 10,
            'tp2_points': 25,
            'tp3_points': 50
        }
        
        # Try to find a CSV file in the data directory
        data_dir = "smartapi/data"
        csv_files = [f for f in os.listdir(data_dir) if f.endswith('.csv')] if os.path.exists(data_dir) else []
        
        if csv_files:
            csv_file = os.path.join(data_dir, csv_files[0])
            print(f"Using CSV file: {csv_file}")
            results, files = run_backtest_from_file(csv_file, csv_params, 'csv')
        else:
            print("No CSV files found in data directory")
            
    except Exception as e:
        print(f"CSV backtest error: {e}")
    
    # Example 2: Backtest with price_ticks.log
    print("\n2. Running backtest with price_ticks.log...")
    try:
        ticks_params = {
            'use_supertrend': False,
            'use_ema_crossover': True,
            'use_rsi_filter': False,
            'use_vwap': True,
            'initial_capital': 100000,
            'base_sl_points': 7,
            'tp1_points': 10,
            'tp2_points': 25,
            'tp3_points': 50
        }
        
        ticks_file = "smartapi/price_ticks.log"
        if os.path.exists(ticks_file):
            print(f"Using ticks file: {ticks_file}")
            results, files = run_backtest_from_file(ticks_file, ticks_params, 'ticks')
        else:
            print("price_ticks.log not found")
            
    except Exception as e:
        print(f"Ticks backtest error: {e}")
    
    print("\nBacktest examples completed!")
