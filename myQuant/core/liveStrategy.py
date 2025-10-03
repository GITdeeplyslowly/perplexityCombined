"""
core/strategy.py - Unified Long-Only, Intraday Strategy for Trading Bot and Backtest

- F&O-ready, multi-indicator, live-driven.
- No shorting, no overnight risk, all config/param driven.
- Handles all signal, entry, exit, and session rules.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, time, timedelta
import pytz
from utils.time_utils import now_ist, normalize_datetime_to_ist, is_time_to_exit, is_within_session, ensure_tz_aware, apply_buffer_to_time
from types import MappingProxyType
from utils.logger import HighPerfLogger, increment_tick_counter, get_tick_counter, format_tick_message

from utils.config_helper import ConfigAccessor
from core.indicators import IncrementalEMA, IncrementalMACD, IncrementalVWAP, IncrementalATR
from dataclasses import dataclass

@dataclass
class TradingSignal:
    """Represents a trading signal with all necessary information."""
    action: str  # 'BUY', 'CLOSE', 'HOLD'
    timestamp: datetime
    price: float
    confidence: float = 1.0
    reason: str = ""
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

class ModularIntradayStrategy:
    """
    Unified long-only intraday strategy supporting multiple indicators.
    
    Features:
    - Long-only, intraday-only trading strategy
    - Configurable indicator combinations (EMA, MACD, VWAP, RSI, etc.)
    - Session time management with buffers
    - Risk management parameters
    - Trade frequency limits
    - Consecutive green bars re-entry logic
    """
    
    def __init__(self, config: MappingProxyType, indicators_module=None):
        """
        Initialize strategy with parameters.
        
        Args:
            config: Strategy parameters from config
            indicators_module: Optional module for calculating indicators
        """
        self.config = config
        # STRICT / fail-fast: initialize HighPerfLogger (requires frozen MappingProxyType & prior setup).
        # Let any exception propagate so misconfiguration is detected immediately.
        # Use high-performance logger (FAIL-FAST: requires caller to have run setup_from_config)
        self.perf_logger = HighPerfLogger(__name__, config)
        self.config_accessor = ConfigAccessor(config)
        self.indicators = indicators_module
        self.in_position = False
        self.position_id = None
        self.position_entry_time = None
        self.position_entry_price = None
        self.last_signal_time = None
        # For metering daily trade count and other constraints
        self.daily_stats = {
            'trades_today': 0,
            'pnl_today': 0.0,
            'last_trade_time': None,
            'session_start_time': None
        }

        # --- Feature flags (read from validated config; GUI is SSOT) ---
        # These should exist in config.defaults.DEFAULT_CONFIG and be validated by the GUI.
        self.use_ema_crossover = self.config_accessor.get_strategy_param('use_ema_crossover')
        self.use_macd = self.config_accessor.get_strategy_param('use_macd')
        self.use_vwap = self.config_accessor.get_strategy_param('use_vwap')
        self.use_rsi_filter = self.config_accessor.get_strategy_param('use_rsi_filter')
        self.use_htf_trend = self.config_accessor.get_strategy_param('use_htf_trend')
        self.use_bollinger_bands = self.config_accessor.get_strategy_param('use_bollinger_bands')
        # optional toggles may be absent in older configs; GUI validation should add them,
        # but keep a safe default here if desired:
        self.use_atr = self.config_accessor.get_strategy_param('use_atr')
        
        # Validate configuration
        # Minimal fail-fast validation using the existing ConfigAccessor methods.
        required_keys = [
            ('strategy', 'fast_ema'),
            ('strategy', 'slow_ema'),
            ('strategy', 'macd_fast'),
            ('strategy', 'macd_slow'),
            ('strategy', 'macd_signal'),
            ('session', 'start_hour'),
            ('session', 'start_min'),
            ('session', 'end_hour'),
            ('session', 'end_min'),
            ('risk', 'max_positions_per_day'),
        ]
        missing = []
        for section, key in required_keys:
            try:
                # ConfigAccessor expects section/key accessors - use the explicit methods
                if section == 'strategy':
                    self.config_accessor.get_strategy_param(key)
                elif section == 'session':
                    self.config_accessor.get_session_param(key)
                elif section == 'risk':
                    self.config_accessor.get_risk_param(key)
            except KeyError:
                missing.append(f"{section}.{key}")
        if missing:
            raise ValueError(f"Invalid configuration - missing: {missing}")
 
        # Session/session exit config (populate using existing accessors)
        self.session_start = time(
            self.config_accessor.get_session_param('start_hour'),
            self.config_accessor.get_session_param('start_min')
        )
        self.session_end = time(
            self.config_accessor.get_session_param('end_hour'),
            self.config_accessor.get_session_param('end_min')
        )
        self.start_buffer_minutes = self.config_accessor.get_session_param('start_buffer_minutes')
        self.end_buffer_minutes = self.config_accessor.get_session_param('end_buffer_minutes')
        # Trading constraints
        self.max_positions_per_day = self.config_accessor.get_risk_param('max_positions_per_day')
        self.no_trade_start_minutes = self.config_accessor.get_session_param('no_trade_start_minutes')
        self.no_trade_end_minutes = self.config_accessor.get_session_param('no_trade_end_minutes')

        # Get timezone setting with fail-fast behavior
        try:
            tz_name = self.config_accessor.get_session_param('timezone')
            try:
                self.timezone = pytz.timezone(tz_name)
            except Exception as e:
                raise ValueError(f"Invalid timezone in config: {tz_name}")
        except KeyError as e:
            raise

        # Log session configuration via high-perf logger (concise lifecycle event)
        self.perf_logger.session_start(
            f"Session configured: {self.session_start.strftime('%H:%M')} to {self.session_end.strftime('%H:%M')} "
            f"buffers=+{self.start_buffer_minutes}/-{self.end_buffer_minutes}m"
        )

        # EMA parameters
        self.fast_ema = self.config_accessor.get_strategy_param('fast_ema')
        self.slow_ema = self.config_accessor.get_strategy_param('slow_ema')
        
        # MACD parameters
        self.macd_fast = self.config_accessor.get_strategy_param('macd_fast')
        self.macd_slow = self.config_accessor.get_strategy_param('macd_slow')
        self.macd_signal = self.config_accessor.get_strategy_param('macd_signal')

        # --- Incremental indicator trackers ---    
        self.ema_fast_tracker = IncrementalEMA(period=self.fast_ema)
        self.ema_slow_tracker = IncrementalEMA(period=self.slow_ema)
        self.macd_tracker = IncrementalMACD(
            fast=self.macd_fast,
            slow=self.macd_slow, 
            signal=self.macd_signal
        )
        self.vwap_tracker = IncrementalVWAP()
        self.atr_tracker = IncrementalATR(period=self.config_accessor.get_strategy_param('atr_len'))
        
        # --- Consecutive green bars for re-entry ---
        try:
            self.consecutive_green_bars_required = self.config_accessor.get_strategy_param('consecutive_green_bars')
            self.green_bars_count = 0
            self.last_bar_data = None
        except KeyError as e:
            raise
        
        # Set name and version
        self.name = "Modular Intraday Long-Only Strategy"
        self.version = "3.0"
        
        # Emit concise initialization event via high-perf logger
        self.perf_logger.session_start(f"Strategy initialized: {self.name} v{self.version}")
        # (Detailed indicator info intentionally not emitted via stdlib logger per standardization)

    def is_trading_session(self, current_time: datetime) -> bool:
        """
        Check if current time is within user-defined trading session
        """
        # Ensure current_time is timezone-aware
        if current_time.tzinfo is None and hasattr(self, 'timezone'):
            current_time = self.timezone.localize(current_time)
        
        # Direct comparison using the simplified function
        return is_within_session(current_time, self.session_start, self.session_end)

    def can_enter_new_position(self, current_time: datetime) -> bool:
        """
        Check if new positions can be entered.
        
        Args:
            current_time: Current timestamp
            
        Returns:
            True if can enter new position
        """
        gating_reasons = []
        if not self.is_trading_session(current_time):
            gating_reasons.append(f"Not in trading session (now={current_time.time()}, allowed={self.session_start}-{self.session_end})")
        buffer_start, buffer_end = self.get_effective_session_times()
        if current_time.time() < buffer_start:
            gating_reasons.append(f"Before buffer start ({current_time.time()} < {buffer_start})")
        if current_time.time() > buffer_end:
            gating_reasons.append(f"After buffer end ({current_time.time()} > {buffer_end})")
        if self.daily_stats['trades_today'] >= self.max_positions_per_day:
            gating_reasons.append(f"Exceeded max trades: {self.daily_stats['trades_today']} >= {self.max_positions_per_day}")
        session_start = ensure_tz_aware(datetime.combine(current_time.date(), self.session_start), current_time.tzinfo)
        session_end = ensure_tz_aware(datetime.combine(current_time.date(), self.session_end), current_time.tzinfo)
        if current_time < session_start + timedelta(minutes=self.no_trade_start_minutes):
            gating_reasons.append(f"In no-trade start period ({current_time.time()} < {session_start.time()} + {self.no_trade_start_minutes}m)")
        if current_time > session_end - timedelta(minutes=self.no_trade_end_minutes):
            gating_reasons.append(f"In no-trade end period ({current_time.time()} > {session_end.time()} - {self.no_trade_end_minutes}m)")
        if not self._check_consecutive_green_ticks():
            gating_reasons.append(f"Need {self.consecutive_green_bars_required} green ticks, have {self.green_bars_count}")
        if gating_reasons:
            self.perf_logger.entry_blocked('; '.join(gating_reasons))
            return False
        return True

    def get_effective_session_times(self):
        """
        Get effective session start and end times after applying buffers
        Returns tuple of (effective_start, effective_end) as time objects
        """
        effective_start = apply_buffer_to_time(
            self.session_start, self.start_buffer_minutes, is_start=True)
        effective_end = apply_buffer_to_time(
            self.session_end, self.end_buffer_minutes, is_start=False)
        return effective_start, effective_end

    def should_exit_for_session(self, now: datetime) -> bool:
        """
        Check if positions should be exited based on user-defined session end and buffer
        """
        if not self.is_trading_session(now):
            return True
        
        # Get effective end time with buffer
        _, buffer_end = self.get_effective_session_times()
        
        if now.time() >= buffer_end:
            return True
        
        return False

    def is_market_closed(self, current_time: datetime) -> bool:
        """Check if market is completely closed (after end time)"""
        return current_time.time() >= self.session_end

    def indicators_and_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        LEGACY: Backwards compatibility method.
        Redirects to calculate_indicators().
        """
        return self.calculate_indicators(data)

    def reset_incremental_trackers(self):
        """Re-init incremental trackers for deterministic runs."""
        self.ema_fast_tracker = IncrementalEMA(period=self.fast_ema)
        self.ema_slow_tracker = IncrementalEMA(period=self.slow_ema)
        self.macd_tracker = IncrementalMACD(
            fast=self.macd_fast,
            slow=self.macd_slow,
            signal=self.macd_signal
        )
        self.vwap_tracker = IncrementalVWAP()
        try:
            atr_len = self.config_accessor.get_strategy_param('atr_len')
        except Exception:
            atr_len = 14
        self.atr_tracker = IncrementalATR(period=atr_len)
        # reset green-bars tracking
        self.green_bars_count = 0
        self.last_bar_data = None
        
        # NEW: Initialize tick-to-tick price tracking
        self.prev_tick_price = None

    def reset_session_indicators(self):
        """Reset session-based indicators (like VWAP) for a new trading session."""
        try:
            self.vwap_tracker.reset()
            # Use perf_logger tick_debug for low-level debug in hot paths
            self.perf_logger.tick_debug(format_tick_message, get_tick_counter(), 0.0, None)
        except Exception as e:
            pass  # Suppress errors in reset

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Incremental processing: update incremental trackers row-by-row and return DataFrame with indicator cols."""
        if data is None or data.empty:
            return data

        # prefer strategy's own incremental processing rather than calling legacy batch function
        self.reset_incremental_trackers()

        df = data.copy()
        numeric_columns = ['fast_ema', 'slow_ema', 'macd', 'macd_signal', 'macd_histogram', 'vwap', 'htf_ema', 'rsi', 'atr']
        boolean_columns = ['ema_bullish', 'macd_bullish', 'macd_histogram_positive', 'vwap_bullish', 'htf_bullish']

        for col in numeric_columns:
            if col not in df.columns:
                df[col] = np.nan
        for col in boolean_columns:
            if col not in df.columns:
                df[col] = False

        for i, (idx, row) in enumerate(df.iterrows()):
            updated = self.process_tick_or_bar(row.copy())
            for col in numeric_columns + boolean_columns:
                if col in updated and col in df.columns:
                    df.iat[i, df.columns.get_loc(col)] = updated[col]

        return df

    def entry_signal(self, row: pd.Series) -> bool:
        """
        Check if entry signal is present based on enabled indicators.
        
        Args:
            row: Current data row with indicator values
            
        Returns:
            True if entry signal is present, False otherwise
        """
        # --- EMA CROSS ---
        pass_ema = True
        if self.use_ema_crossover:
            pass_ema = (
                row.get('fast_ema', None) is not None and
                row.get('slow_ema', None) is not None and
                row['fast_ema'] > row['slow_ema']
            )
        # --- VWAP ---
        pass_vwap = True
        if self.use_vwap:
            vwap_val = row.get('vwap', None)
            pass_vwap = (vwap_val is not None) and (row['close'] > vwap_val)
        # --- MACD ---
        pass_macd = True
        if self.use_macd:
            pass_macd = row.get('macd_bullish', False) and row.get('macd_histogram_positive', False)
        # --- HTF TREND ---
        pass_htf = True
        if self.use_htf_trend:
            htf_val = row.get('htf_ema', None)
            pass_htf = (htf_val is not None) and (row['close'] > htf_val)
        # --- RSI ---
        pass_rsi = True
        if self.use_rsi_filter:
            rsi_val = row.get('rsi', None)
            pass_rsi = (rsi_val is not None) and (
                self.config_accessor.get_strategy_param('rsi_oversold') < 
                rsi_val < 
                self.config_accessor.get_strategy_param('rsi_overbought')
            )
        # --- Bollinger Bands ---
        pass_bb = True
        if self.use_bollinger_bands:
            bb_lower = row.get('bb_lower', None)
            bb_upper = row.get('bb_upper', None)
            pass_bb = (bb_lower is not None and bb_upper is not None) and (bb_lower < row['close'] < bb_upper)
        # --- Construct final pass signal (all enabled must be True) ---
        logic_checks = [pass_ema, pass_vwap, pass_macd, pass_htf, pass_rsi, pass_bb]
        return all(logic_checks)

    def open_long(self, row: pd.Series, now: datetime, position_manager) -> Optional[str]:
        # For robust trade management, always use live/production-driven position config
        entry_price = row['close']

        # Get instrument config with fail-fast behavior
        try:
            instrument_config = self.config_accessor.get('instrument')
            if not instrument_config:
                raise KeyError('instrument')
            symbol = instrument_config.get('symbol')
            if not symbol:
                raise KeyError('instrument.symbol')
        except KeyError as e:
            return None

        # Use instrument SSOT for contract sizing (no risk.lot_size overrides)
        try:
            lot_size = int(self.config_accessor.get_instrument_param('lot_size'))
            tick_size = float(self.config_accessor.get_instrument_param('tick_size'))
        except KeyError as e:
            return None

        position_id = position_manager.open_position(
            symbol=symbol,
            entry_price=entry_price,
            timestamp=now,
            lot_size=lot_size,
            tick_size=tick_size
        )

        if position_id:
            self.in_position = True
            self.position_id = position_id
            self.position_entry_time = now
            self.position_entry_price = entry_price
            self.daily_stats['trades_today'] += 1
            self.last_signal_time = now

            self.perf_logger.trade_executed("BUY", entry_price, lot_size, "Strategy signal")
            return position_id
        # If position not opened, do not emit stdlib warning (standardization)
        return None

    def should_close(self, row: pd.Series, now: datetime, position_manager) -> bool:
        """
        FIXED: Method name compatibility for backtest runner.
        Redirects to should_exit() method.
        """
        return self.should_exit(row, now, position_manager)

    def handle_exit(self, position_id: str, price: float, now: datetime, position_manager, reason="Session End"):
        """
        FIXED: Added missing handle_exit method for backtest compatibility.
        """
        try:
            success = position_manager.close_position_full(position_id, price, now, reason=reason)
            if success:
                self.in_position = False
                self.position_id = None
                self.position_entry_time = None
                self.position_entry_price = None
            return success
        except Exception as e:
            return False

    def should_exit_position(self, row: pd.Series, position_type: str, 
                           current_time: Optional[datetime] = None) -> bool:
        """
        Check if should exit current position (for backtest compatibility).
        
        Args:
            row: Current data row
            position_type: Position type ('long' or 'short')
            current_time: Current timestamp
            
        Returns:
            True if should exit position
        """
        if current_time is None:
            current_time = row.name if hasattr(row, 'name') else datetime.now()
        
        # Always exit at session end
        if self.should_exit_for_session(current_time):
            return True
        
        # Let position manager handle stop loss, take profit, and trailing stops
        return False

    def reset_daily_counters(self, now: datetime):
        """
        Reset daily counters for a new trading session.
        
        Args:
            now: Current timestamp
        """
        self.daily_stats = {
            'trades_today': 0,
            'pnl_today': 0.0,
            'last_trade_time': None,
            'session_start_time': now
        }
        self.last_signal_time = None
        # Log daily reset via high-perf logger
        self.perf_logger.session_start(f"Daily counters reset for {now.date()}")

    def validate_parameters(self) -> List[str]:
        """
        Validate strategy parameters.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Check for required parameters
        required_params = [
            'fast_ema', 'slow_ema', 'macd_fast', 'macd_slow', 'macd_signal',
            'consecutive_green_bars', 'atr_len'
        ]
        
        for param in required_params:
            try:
                self.config_accessor.get_strategy_param(param)
            except KeyError:
                errors.append(f"Missing required parameter: {param}")
        
        # Typical validation rules
        if self.use_ema_crossover:
            if self.fast_ema >= self.slow_ema:
                errors.append("fast_ema must be less than slow_ema")
        if self.use_htf_trend:
            try:
                htf_period = self.config_accessor.get_strategy_param('htf_period')
                if htf_period <= 0:
                    errors.append("htf_period must be positive")
            except KeyError:
                errors.append("Missing required parameter: htf_period")
        
        # Validate risk parameters
        if self.max_positions_per_day <= 0:
            errors.append("max_positions_per_day must be positive")
        
        # Validate session parameters
        if self.session_start >= self.session_end:
            errors.append("Session start must be before session end")
            
        return errors

    def get_strategy_info(self) -> Dict[str, Any]:
        """
        Get strategy information (for backtest compatibility).
        
        Returns:
            Strategy information dictionary
        """
        return {
            'name': self.name,
            'version': self.version,
            'type': 'Long-Only Intraday',
            'indicators_enabled': {
                'ema_crossover': self.use_ema_crossover,
                'macd': self.use_macd,
                'vwap': self.use_vwap,
                'rsi_filter': self.use_rsi_filter,
                'htf_trend': self.use_htf_trend,
                'bollinger_bands': self.use_bollinger_bands
            },
            'parameters': {
                'fast_ema': self.fast_ema,
                'slow_ema': self.slow_ema,
                'base_sl_points': self.config_accessor.get_risk_param('base_sl_points')
            },
            'constraints': {
                'long_only': True,
                'intraday_only': True,
                'max_trades_per_day': self.max_positions_per_day
            },
            'session': {
                'start': self.session_start.strftime('%H:%M'),
                'end': self.session_end.strftime('%H:%M'),
                'start_buffer_minutes': self.start_buffer_minutes,
                'end_buffer_minutes': self.end_buffer_minutes
            },
            'daily_stats': self.daily_stats.copy()
        }

    def verify_backtest_interface(self):
        """Production verification of backtest interface."""
        required_methods = ['can_open_long', 'open_long', 'calculate_indicators', 'should_close']
        
        for method in required_methods:
            if not hasattr(self, method):
                return False
            else:
                pass  # Method exists
    
        return True

    def process_tick_or_bar(self, row: pd.Series):
        # Tick counter and hot-path perf logging
        increment_tick_counter()
        if self.perf_logger:
            self.perf_logger.tick_debug(
                format_tick_message,
                get_tick_counter(), 
                row.get('close', 0), 
                row.get('volume', None)
            )
        try:
            # Accept Series or single-row DataFrame
            if isinstance(row, pd.DataFrame):
                if len(row) == 1:
                    row = row.iloc[0]
                else:
                    return row

            def safe_extract(key, default=None):
                val = row.get(key, default)
                if isinstance(val, pd.Series):
                    return val.iloc[0] if len(val) else default
                return val

            close_price = safe_extract('close', safe_extract('price', None))
            if close_price is None:
                return row
            try:
                close_price = float(close_price)
            except Exception:
                return row
            if close_price <= 0:
                return row

            volume = safe_extract('volume', 0) or 0
            try:
                volume = int(volume)
            except Exception:
                volume = 0
            high_price = float(safe_extract('high', close_price))
            low_price = float(safe_extract('low', close_price))
            open_price = float(safe_extract('open', close_price))

            updated = row.copy()

            # EMA
            if getattr(self, 'use_ema_crossover', False):
                fast_ema_val = self.ema_fast_tracker.update(close_price)
                slow_ema_val = self.ema_slow_tracker.update(close_price)
                updated['fast_ema'] = fast_ema_val
                updated['slow_ema'] = slow_ema_val
                updated['ema_bullish'] = False if pd.isna(fast_ema_val) or pd.isna(slow_ema_val) else (fast_ema_val > slow_ema_val)

            # MACD
            if getattr(self, 'use_macd', False):
                macd_val, macd_signal_val, macd_hist_val = self.macd_tracker.update(close_price)
                updated['macd'] = macd_val
                updated['macd_signal'] = macd_signal_val
                updated['macd_histogram'] = macd_hist_val
                updated['macd_bullish'] = False if pd.isna(macd_val) or pd.isna(macd_signal_val) else (macd_val > macd_signal_val)
                updated['macd_histogram_positive'] = False if pd.isna(macd_hist_val) else (macd_hist_val > 0)

            # VWAP
            if getattr(self, 'use_vwap', False):
                vwap_val = self.vwap_tracker.update(price=close_price, volume=volume, high=high_price, low=low_price, close=close_price)
                updated['vwap'] = vwap_val
                updated['vwap_bullish'] = False if pd.isna(vwap_val) else (close_price > vwap_val)

            # HTF EMA (lazy init)
            if getattr(self, 'use_htf_trend', False):
                if not hasattr(self, 'htf_ema_tracker'):
                    self.htf_ema_tracker = IncrementalEMA(period=self.config_accessor.get_strategy_param('htf_period'))
                htf_ema_val = self.htf_ema_tracker.update(close_price)
                updated['htf_ema'] = htf_ema_val
                updated['htf_bullish'] = False if pd.isna(htf_ema_val) else (close_price > htf_ema_val)

            # ATR
            if getattr(self, 'use_atr', False):
                atr_val = self.atr_tracker.update(high=high_price, low=low_price, close=close_price)
                updated['atr'] = atr_val

            # Update green tick count and return
            self._update_green_tick_count(close_price)
            return updated
        except Exception as e:
            return row

    # Backwards-compatible aliases expected by backtest/other modules
    def can_open_long(self, row: pd.Series, timestamp: datetime) -> bool:
        """
        Backtest-compatible wrapper. For live use prefer can_enter_new_position(timestamp)
        and entry_signal(row).
        """
        try:
            # ensure timestamp is tz-aware if possible
            if timestamp is not None:
                timestamp = ensure_tz_aware(timestamp)
            # Combine session gating and entry signal
            return self.can_enter_new_position(timestamp) and bool(self.entry_signal(row))
        except Exception:
            return False

    def should_exit(self, row: pd.Series, timestamp: datetime, position_manager=None) -> bool:
        """
        Backtest-compatible exit check. Delegate to session-exit (and leave position manager
        to apply SL/TP/trailing logic).
        """
        try:
            timestamp = ensure_tz_aware(timestamp)
            # Exit at session buffer end or when session gating requires exit
            if self.should_exit_for_session(timestamp):
                return True
            return False
        except Exception:
            return True  # safe default: ask runner to close positions

    # alias for any callers expecting should_close
    def should_close(self, row: pd.Series, timestamp: datetime, position_manager=None) -> bool:
        return self.should_exit(row, timestamp, position_manager)

    def _update_green_tick_count(self, current_price: float):
        """
        Update consecutive green ticks counter based on tick-to-tick price movement.
        A green tick is defined as current_price > prev_tick_price with configurable noise filtering.
        """
        try:
            if self.prev_tick_price is None:
                # First tick of session or after reset
                self.green_bars_count = 0
                self.prev_tick_price = current_price
                return

            # Get noise filter parameters from config
            noise_filter_enabled = bool(self.config_accessor.get_strategy_param('noise_filter_enabled', True))
            noise_filter_percentage = float(self.config_accessor.get_strategy_param('noise_filter_percentage', 0.0001))
            noise_filter_min_ticks = float(self.config_accessor.get_strategy_param('noise_filter_min_ticks', 1.0))
            
            # Calculate minimum movement threshold
            min_movement = max(self.tick_size * noise_filter_min_ticks, 
                              self.prev_tick_price * noise_filter_percentage)
            
            # Apply noise filter if enabled
            if noise_filter_enabled:
                if current_price > (self.prev_tick_price + min_movement):
                    # Significant upward movement
                    self.green_bars_count += 1
                elif current_price < (self.prev_tick_price - min_movement):
                    # Significant downward movement
                    self.green_bars_count = 0
                else:
                    # Price within noise range - maintain current count
                    pass
            else:
                # Original behavior without noise filtering
                if current_price > self.prev_tick_price:
                    self.green_bars_count += 1
                else:
                    # Reset counter on price decrease or equal
                    self.green_bars_count = 0
            
            # Update previous price for next comparison
            self.prev_tick_price = current_price
        except Exception as e:
            pass  # Suppress errors in tick count update

    def _check_consecutive_green_ticks(self) -> bool:
        """Check if we have enough consecutive green ticks for entry."""
        return self.green_bars_count >= self.consecutive_green_bars_required

if __name__ == "__main__":
    # Minimal smoke test for development
    test_params = {
        'use_ema_crossover': True, 'fast_ema': 9, 'slow_ema': 21, 'ema_points_threshold': 2,
        'use_macd': True, 'macd_fast': 12, 'macd_slow': 26, 'macd_signal': 9,
        'use_vwap': True, 'use_htf_trend': True, 'htf_period': 20, 'symbol': 'NIFTY24DECFUT', 'lot_size': 15, 'tick_size': 0.05,
        'session': {'start_hour': 9, 'start_min': 15, 'end_hour': 15, 'end_min': 30, 'start_buffer_minutes': 5, 'end_buffer_minutes': 20, 'timezone': 'Asia/Kolkata'},
        'max_positions_per_day': 25,
        'base_sl_points': 15
    }
    import core.indicators as indicators
    strat = ModularIntradayStrategy(test_params, indicators)
    print("Parameter validation errors:", strat.validate_parameters())

"""
CONFIGURATION PARAMETER NAMING CONVENTION:
- Constructor parameter: __init__(self, config: Dict[str, Any], ...)
- Internal storage: self.config = config
- All parameter access: self.config.get('parameter_name', default)
- Session parameters extracted to dedicated variables in constructor

INTERFACE CONSISTENCY:
- Uses same parameter naming as researchStrategy.py
- calculate_indicators() passes self.config to indicators module
- Compatible with both backtest and live trading systems

CRITICAL: This file must maintain naming consistency with researchStrategy.py
- Both use 'config' parameter in constructor
- Both use self.config for internal parameter access
- Both pass self.config to calculate_all_indicators()
"""
