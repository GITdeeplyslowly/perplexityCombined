"""
core/strategy.py - Unified Long-Only, Intraday Strategy for Trading Bot and Backtest

- F&O-ready, multi-indicator, live-driven.
- No shorting, no overnight risk, all config/param driven.
- Handles all signal, entry, exit, and session rules.
"""

import pandas as pd
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, time, timedelta
from utils.time_utils import now_ist, normalize_datetime_to_ist, is_time_to_exit, is_within_session, ensure_tz_aware, apply_buffer_to_time
import logging
import pytz

from utils.config_helper import ConfigAccessor
from core.indicators import IncrementalEMA, IncrementalMACD, IncrementalVWAP, IncrementalATR
from dataclasses import dataclass

logger = logging.getLogger(__name__)

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
    
    def __init__(self, config: Dict[str, Any], indicators_module=None):
        """
        Initialize strategy with parameters.
        
        Args:
            config: Strategy parameters from config
            indicators_module: Optional module for calculating indicators
        """
        self.config = config
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

        # Validate configuration
        validation = self.config_accessor.validate_required_params()
        if not validation['valid']:
            logger.error(f"Configuration validation failed: {validation['errors']}")
            raise ValueError(f"Invalid configuration: {validation['errors']}")

        # Extract feature flags
        self.use_ema_crossover = self.config_accessor.get_strategy_param('use_ema_crossover', False)
        self.use_macd = self.config_accessor.get_strategy_param('use_macd', False)
        self.use_vwap = self.config_accessor.get_strategy_param('use_vwap', False)
        self.use_htf_trend = self.config_accessor.get_strategy_param('use_htf_trend', False)
        self.use_rsi_filter = self.config_accessor.get_strategy_param('use_rsi_filter', False)
        self.use_bollinger_bands = self.config_accessor.get_strategy_param('use_bollinger_bands', False)

        # Session/session exit config
        self.session_params = self.config_accessor.get_session_params()
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

        # Get timezone setting
        tz_name = self.config_accessor.get_session_param('timezone')
        try:
            self.timezone = pytz.timezone(tz_name)
        except:
            self.timezone = pytz.timezone('Asia/Kolkata')
            logger.warning(f"Invalid timezone {tz_name}, using Asia/Kolkata")
            
        logger.info(f"Session configured: {self.session_start.strftime('%H:%M')} to "
                   f"{self.session_end.strftime('%H:%M')} with "
                   f"buffers: +{self.start_buffer_minutes}/-{self.end_buffer_minutes} min")

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
        
        # --- NEW: Consecutive green bars for re-entry ---
        self.consecutive_green_bars_required = self.config_accessor.get_strategy_param('consecutive_green_bars')
        self.green_bars_count = 0
        self.last_bar_data = None
        
        # Set name and version
        self.name = "Modular Intraday Long-Only Strategy"
        self.version = "3.0"
        
        logger.info(f"Strategy initialized: {self.name} v{self.version}")
        logger.info(
            f"[INIT] Indicator switches: EMA={self.use_ema_crossover}, MACD={self.use_macd}, VWAP={self.use_vwap}, "
            f"RSI={self.use_rsi_filter}, HTF={self.use_htf_trend}, BB={self.use_bollinger_bands}"
        )
        logger.info(
            f"[INIT] Indicator params: fast_ema={self.fast_ema}, slow_ema={self.slow_ema}, "
            f"MACD=({self.macd_fast}, {self.macd_slow}, {self.macd_signal}), "
            f"Green Bars Req={self.consecutive_green_bars_required}"
        )
        logger.info(
            f"[INIT] Session: {self.session_start.strftime('%H:%M')}–{self.session_end.strftime('%H:%M')}, "
            f"Buffers: +{self.start_buffer_minutes}/-{self.end_buffer_minutes}, "
            f"no_trade_start={self.no_trade_start_minutes} no_trade_end={self.no_trade_end_minutes}, "
            f"Max/day={self.max_positions_per_day}"
        )

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
        if self.last_signal_time and not self._check_consecutive_green_bars():
            gating_reasons.append(f"Not enough green bars ({self.green_bars_count} < {self.consecutive_green_bars_required})")
        if gating_reasons:
            logger.info(f"[ENTRY BLOCKED] at {current_time}: {' | '.join(gating_reasons)}")
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
            logger.debug(f"✅ Should exit: Not in trading session {now}")
            return True
        
        # Get effective end time with buffer
        _, buffer_end = self.get_effective_session_times()
        
        if now.time() >= buffer_end:
            logger.debug(f"✅ Should exit: After buffer end {buffer_end}")
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

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate all technical indicators."""
        if self.indicators is None:
            logger.warning("No indicators module provided, returning data unchanged")
            return data
        return self.indicators.calculate_all_indicators(data, self.config)

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
        
        # Use ConfigAccessor to get instrument config, but don't provide a default
        # to ensure explicit configuration is required
        instrument_config = self.config_accessor.get_param('instrument', {})
        symbol = instrument_config.get('symbol')
        
        # No fallback - must have explicit symbol configuration
        if not symbol:
            logger.error("No instrument symbol configured - cannot open position")
            return None
    
        # lot size and tick size must be passed from config (for F&O)
        lot_size = self.config_accessor.get_risk_param('lot_size')
        tick_size = self.config_accessor.get_risk_param('tick_size')
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
            
            logger.info(f"✅ Position opened: {position_id} @ {entry_price}")
            return position_id
        else:
            logger.warning("❌ Position manager returned None")
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
                logger.info(f"✅ Strategy exit executed: {position_id} @ {price:.2f} - {reason}")
                self.in_position = False
                self.position_id = None
                self.position_entry_time = None
                self.position_entry_price = None
            return success
        except Exception as e:
            logger.error(f"❌ Strategy exit failed: {e}")
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
        logger.info(f"Daily counters reset for {now.date()}")

    def validate_parameters(self) -> List[str]:
        """
        Validate strategy parameters.
        
        Returns:
ṇ            List of validation errors (empty if valid)
        """
        errors = []
        # Typical validation rules
        if self.use_ema_crossover:
            if self.fast_ema >= self.slow_ema:
                errors.append("fast_ema must be less than slow_ema")
        if self.use_htf_trend:
            htf_period = self.config_accessor.get_strategy_param('htf_period')
            if htf_period <= 0:
                errors.append("htf_period must be positive")
        
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
                logger.error(f"MISSING METHOD: {method}")
                return False
            else:
                logger.info(f"✅ Method exists: {method}")
        
        return True

    def process_tick_or_bar(self, row: pd.Series):
        """
        Update all incremental indicators with the latest tick/bar data.
        This is used for live trading where we get one data point at a time.
        
        Args:
            row: Latest price data with OHLCV values
        
        Returns:
            Updated row with indicator values
        """
        try:
            # For EMA
            fast_ema_val = self.ema_fast_tracker.update(row['close'])
            slow_ema_val = self.ema_slow_tracker.update(row['close'])
            # Calculate derived EMA values
            row['ema_bullish'] = fast_ema_val > slow_ema_val

            # For MACD
            macd_val, macd_signal_val, macd_hist_val = self.macd_tracker.update(row['close'])
            # Calculate derived MACD values
            row['macd_bullish'] = macd_val > macd_signal_val
            row['macd_histogram_positive'] = macd_hist_val > 0

            # For VWAP
            vwap_val = self.vwap_tracker.update(
                price=row['close'], volume=row['volume'],
                high=row.get('high'), low=row.get('low'), close=row.get('close')
            )

            # For ATR
            atr_val = self.atr_tracker.update(
                high=row['high'], low=row['low'], close=row['close']
            )

            # Update row/signal state as required
            row['fast_ema'] = fast_ema_val
            row['slow_ema'] = slow_ema_val
            row['macd'] = macd_val
            row['macd_signal'] = macd_signal_val
            row['macd_histogram'] = macd_hist_val
            row['vwap'] = vwap_val
            row['atr'] = atr_val
            
            # Update green bars counter
            self._update_green_bars_count(row)
            
            return row
        except Exception as e:
            logger.error(f"Error processing tick/bar data: {e}")
            return row

    # --- NEW: Consecutive green bars logic ---
    def _check_consecutive_green_bars(self) -> bool:
        """
        Check if we have enough consecutive green bars for re-entry.
        Returns True if enough consecutive green bars, False otherwise.
        """
        return self.green_bars_count >= self.consecutive_green_bars_required

    def _update_green_bars_count(self, row: pd.Series):
        """
        Update the count of consecutive green bars based on current bar data.
        A green bar is one where close > open.
        """
        try:
            current_close = row.get('close', 0)
            current_open = row.get('open', current_close)

            # For tick data, compare with previous close if no open available
            if current_open == current_close and self.last_bar_data is not None:
                current_open = self.last_bar_data.get('close', current_close)

            is_green_bar = current_close > current_open

            if is_green_bar:
                self.green_bars_count += 1
            else:
                self.green_bars_count = 0

            # Store current bar for next comparison
            self.last_bar_data = {
                'open': current_open,
                'close': current_close,
                'timestamp': row.name if hasattr(row, 'name') else None
            }

        except Exception as e:
            logger.error(f"Error updating green bars count: {e}")

    def should_exit(self, row, timestamp, position_manager):
        """Check if we should close position"""
        # Ensure timezone-aware timestamp
        timestamp = ensure_tz_aware(timestamp)
        
        # Always exit at session end
        if self.should_exit_for_session(timestamp):
            return True
        
        # Let position manager handle stop loss, take profit, and trailing stops
        return False

    def generate_entry_signal(self, row: pd.Series, current_time: datetime) -> TradingSignal:
        """
        Port from researchStrategy - comprehensive signal generation with reasoning.
        This is the CRITICAL method that was missing.
        """
        # --- NEW: Update green bars count for this bar ---
        self._update_green_bars_count(row)

        # Check if we can enter
        if not self.can_enter_new_position(current_time):
            return TradingSignal('HOLD', current_time, row['close'],
                               reason="Cannot enter new position")

        # Collect all signal conditions
        signal_conditions = []
        signal_reasons = []
        confidence = 1.0

        # === EMA CROSSOVER SIGNAL ===
        if self.use_ema_crossover:
            if 'ema_bullish' in row:
                if row['ema_bullish']:
                    signal_conditions.append(True)
                    signal_reasons.append(f"EMA: Fast ({row.get('fast_ema', 0):.2f}) above Slow ({row.get('slow_ema', 0):.2f})")
                else:
                    signal_conditions.append(False)
                    signal_reasons.append(f"EMA: Fast not above Slow EMA")
            else:
                signal_conditions.append(False)
                signal_reasons.append("EMA Cross: Data not available")

        # === MACD SIGNAL ===
        if self.use_macd:
            if ('macd_bullish' in row and 'macd_histogram_positive' in row):
                macd_bullish = row.get('macd_bullish', False)
                histogram_positive = row.get('macd_histogram_positive', False)
                macd_signal = macd_bullish and histogram_positive
                signal_conditions.append(macd_signal)
                if macd_signal:
                    signal_reasons.append("MACD: Bullish (line > signal & histogram > 0)")
                else:
                    signal_reasons.append(f"MACD: Not bullish")
            else:
                signal_conditions.append(False)
                signal_reasons.append("MACD: Data not available")

        # === VWAP SIGNAL ===
        if self.use_vwap:
            if 'vwap' in row and not pd.isna(row['vwap']):
                vwap_bullish = row['close'] > row['vwap']
                signal_conditions.append(vwap_bullish)
                if vwap_bullish:
                    signal_reasons.append(f"VWAP: Bullish ({row['close']:.2f} > {row['vwap']:.2f})")
                else:
                    signal_reasons.append(f"VWAP: Bearish ({row['close']:.2f} <= {row['vwap']:.2f})")
            else:
                signal_conditions.append(False)
                signal_reasons.append("VWAP: Data not available")

        # === HTF TREND SIGNAL ===
        if self.use_htf_trend:
            if 'htf_ema' in row and not pd.isna(row['htf_ema']):
                htf_bullish = row['close'] > row['htf_ema']
                signal_conditions.append(htf_bullish)
                if htf_bullish:
                    signal_reasons.append(f"HTF Trend: Bullish ({row['close']:.2f} > {row['htf_ema']:.2f})")
                else:
                    signal_reasons.append(f"HTF Trend: Bearish ({row['close']:.2f} <= {row['htf_ema']:.2f})")
            else:
                signal_conditions.append(False)
                signal_reasons.append("HTF Trend: Data not available")

        # === RSI FILTER ===
        if self.use_rsi_filter:
            if 'rsi' in row and not pd.isna(row['rsi']):
                rsi = row['rsi']
                rsi_ok = self.config_accessor.get_strategy_param('rsi_oversold') < rsi < self.config_accessor.get_strategy_param('rsi_overbought')
                signal_conditions.append(rsi_ok)
                if rsi_ok:
                    signal_reasons.append(f"RSI: Neutral ({rsi:.1f})")
                else:
                    signal_reasons.append(f"RSI: Extreme ({rsi:.1f})")
            else:
                signal_conditions.append(False)
                signal_reasons.append("RSI: Data not available")

        # === BOLLINGER BANDS FILTER ===
        if self.use_bollinger_bands:
            if all(col in row for col in ['bb_upper', 'bb_lower', 'bb_middle']):
                bb_ok = row['bb_lower'] < row['close'] < row['bb_upper']
                signal_conditions.append(bb_ok)
                if bb_ok:
                    signal_reasons.append("BB: Price within bands")
                else:
                    signal_reasons.append("BB: Price outside bands")
            else:
                signal_conditions.append(False)
                signal_reasons.append("Bollinger Bands: Data not available")

        # === FINAL SIGNAL DECISION ===
        if signal_conditions and all(signal_conditions):
            # Calculate stop loss
            stop_loss_price = row['close'] - self.config_accessor.get_risk_param('base_sl_points')

            # Update tracking
            self.last_signal_time = current_time

            return TradingSignal(
                action='BUY',
                timestamp=current_time,
                price=row['close'],
                confidence=confidence,
                reason="; ".join(signal_reasons),
                stop_loss=stop_loss_price
            )
        else:
            # Log why signal failed
            failed_reasons = [reason for i, reason in enumerate(signal_reasons)
                            if i < len(signal_conditions) and not signal_conditions[i]]
            return TradingSignal(
                action='HOLD',
                timestamp=current_time,
                price=row['close'],
                confidence=0.0,
                reason=f"Entry blocked: {'; '.join(failed_reasons[:3])}"
            )

    def get_signal_description(self, row: pd.Series) -> str:
        """Port from research strategy - debugging method"""
        descriptions = []

        if self.use_ema_crossover and 'fast_ema' in row and 'slow_ema' in row:
            fast_ema = row['fast_ema']
            slow_ema = row['slow_ema']
            if not pd.isna(fast_ema) and not pd.isna(slow_ema):
                descriptions.append(f"EMA {self.fast_ema}/{self.slow_ema}: {fast_ema:.2f}/{slow_ema:.2f}")

        if self.use_macd and 'macd' in row and 'macd_signal' in row:
            macd = row['macd']
            signal = row['macd_signal']
            if not pd.isna(macd) and not pd.isna(signal):
                descriptions.append(f"MACD: {macd:.3f}/{signal:.3f}")

        if self.use_vwap and 'vwap' in row:
            vwap = row['vwap']
            if not pd.isna(vwap):
                descriptions.append(f"VWAP: {row['close']:.2f} vs {vwap:.2f}")

        return "; ".join(descriptions) if descriptions else "No indicators"

    def validate_parameters(self) -> list:
        errors = []
        # Typical validation rules
        if self.use_ema_crossover:
            if self.fast_ema >= self.slow_ema:
                errors.append("fast_ema must be less than slow_ema")
        if self.use_htf_trend:
            htf_period = self.config_accessor.get_strategy_param('htf_period')
            if htf_period <= 0:
                errors.append("htf_period must be positive")
        return errors

    def can_open_long(self, row: pd.Series, now: datetime) -> bool:
        """PRODUCTION INTERFACE: Entry signal detection."""
        try:
            # Ensure timezone awareness
            now = ensure_tz_aware(now)
            
            # Update green bars count
            self._update_green_bars_count(row)
            
            # Check session timing and other constraints
            can_enter = self.can_enter_new_position(now)
            
            # In position check
            if self.in_position:
                return False
                
            # Check signal conditions
            should_enter = self.entry_signal(row)
            
            return can_enter and should_enter
            
        except Exception as e:
            logger.error(f"Error in can_open_long: {e}")
            return False

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
