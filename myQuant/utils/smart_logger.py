"""
utils/smart_logger.py

Event-driven smart logger for trading systems (minimal, plain-text).
"""
import logging
import time
from datetime import datetime
from typing import Dict, List, Any
from collections import defaultdict


class TradingEventLogger:
    """
    Smart logger that tracks state changes and logs only significant events.
    Exposes .logger (standard logging.Logger) for compatibility.
    """

    def __init__(self, name: str, config: Dict[str, Any]):
        self.logger = logging.getLogger(name)
        self.config = config.get('logging', {}) if config else {}
        self.verbosity = self.config.get('verbosity', 'minimal')
        self.state = {
            'last_signal': None,
            'last_position': None,
            'consecutive_holds': 0,
            'last_progress_log': 0,
            'session_stats': defaultdict(int)
        }
        self.level_cache = {}
        self.batch_buffer = []
        self.last_batch_flush = time.time()

    def is_level_enabled(self, level: str) -> bool:
        level = level.upper()
        if level not in self.level_cache:
            try:
                self.level_cache[level] = self.logger.isEnabledFor(getattr(logging, level))
            except Exception:
                self.level_cache[level] = False
        return self.level_cache[level]

    def log_signal_event(self, action: str, timestamp: datetime,
                        conditions: List[str], price: float):
        max_reasons = self.config.get('max_signal_reasons', 2)
        ts = timestamp.strftime('%Y-%m-%d %H:%M:%S') if isinstance(timestamp, datetime) else str(timestamp)
        reasons = (conditions or [])[:max_reasons]

        if action == 'BUY' and self.state['last_signal'] != 'BUY':
            self.logger.info(f"ENTRY SIGNAL @ {ts} | Price={price:.2f} | Reasons: {'; '.join(reasons) if reasons else 'N/A'}")
            self.state['session_stats']['signals'] += 1
            self.state['last_signal'] = 'BUY'
            self.state['consecutive_holds'] = 0

        elif action == 'HOLD' and self.state['last_signal'] == 'BUY':
            failed = [c for c in (conditions or []) if any(w in c.lower() for w in ('not', 'blocked', 'failed', 'insufficient'))]
            reason = failed[0] if failed else 'Conditions not met'
            self.logger.info(f"SIGNAL LOST @ {ts} | {reason}")
            self.state['last_signal'] = 'HOLD'

        elif action == 'HOLD':
            self.state['consecutive_holds'] += 1
            if self.verbosity == 'debug' and (self.state['consecutive_holds'] % 5000 == 0):
                self.logger.debug(f"HOLD continuing @ {ts} ({self.state['consecutive_holds']} consecutive)")

    def log_position_event(self, action: str, details: Dict[str, Any]):
        if action == 'OPEN' and self.state['last_position'] != 'OPEN':
            self.logger.info(
                f"POSITION OPENED: {details.get('symbol','N/A')} {details.get('quantity',0)} units @ {details.get('price',0):.2f}"
            )
            self.state['session_stats']['entries'] += 1
            self.state['last_position'] = 'OPEN'
        elif action == 'CLOSE' and self.state['last_position'] == 'OPEN':
            pnl = details.get('pnl', 0)
            direction = "PROFIT" if pnl > 0 else "LOSS" if pnl < 0 else "BREAKEVEN"
            self.logger.info(
                f"POSITION CLOSED: {direction} | P&L={pnl:.2f} | Reason={details.get('reason','Unknown')}"
            )
            self.state['session_stats']['exits'] += 1
            self.state['session_stats']['total_pnl'] += pnl
            self.state['last_position'] = 'CLOSED'

    def log_progress_smart(self, current: int, total: int, trades: int = 0):
        if not self.config.get('log_progress', False) or total <= 0:
            return
        progress = (current / total) * 100
        milestones = (10, 25, 50, 75, 90, 95, 99)
        milestone_hit = any(abs(progress - m) < 0.1 for m in milestones)
        interval_hit = (current - self.state['last_progress_log']) >= 50000
        if milestone_hit or interval_hit:
            self.logger.info(
                f"Progress: {progress:.1f}% ({current}/{total}) | Trades: {trades} | Signals: {self.state['session_stats']['signals']}"
            )
            self.state['last_progress_log'] = current

    def log_session_summary(self):
        stats = self.state['session_stats']
        self.logger.info("=" * 60)
        self.logger.info("TRADING SESSION SUMMARY")
        self.logger.info("=" * 60)
        self.logger.info(f"Signals Generated: {stats.get('signals', 0)}")
        self.logger.info(f"Positions Opened: {stats.get('entries', 0)}")
        self.logger.info(f"Positions Closed: {stats.get('exits', 0)}")
        if stats.get('total_pnl', 0) != 0:
            self.logger.info(f"Total P&L: {stats.get('total_pnl', 0):.2f}")
        self.logger.info("=" * 60)

    def log_stage_transition(self, from_stage: str, to_stage: str, details: str = ""):
        if self.verbosity != 'minimal':
            self.logger.info(f"{from_stage} -> {to_stage}")
            if details and self.verbosity == 'debug':
                self.logger.debug(f"Details: {details}")

    def log_error_with_context(self, error: Exception, context: Dict[str, Any]):
        self.logger.error(
            f"ERROR: {error} | Context: Symbol={context.get('symbol','N/A')}, Price={context.get('price','N/A')}, Time={context.get('timestamp','N/A')}"
        )

    def log_unusual_condition(self, condition: str, details: str):
        self.logger.warning(f"UNUSUAL CONDITION: {condition} | {details}")

    def batch_log_debug(self, message: str):
        if not self.is_level_enabled('DEBUG'):
            return
        self.batch_buffer.append((time.time(), message))
        if len(self.batch_buffer) >= 100 or (time.time() - self.last_batch_flush) > 10:
            self._flush_debug_batch()

    def _flush_debug_batch(self):
        if not self.batch_buffer:
            return
        if len(self.batch_buffer) > 20:
            self.logger.debug(f"Debug batch: {len(self.batch_buffer)} messages (sample: {self.batch_buffer[-1][1]})")
        else:
            for _, msg in self.batch_buffer:
                self.logger.debug(msg)
        self.batch_buffer.clear()
        self.last_batch_flush = time.time()

    def conditional_log(self, condition: bool, level: str, message: str, *args, **kwargs):
        if condition and self.is_level_enabled(level):
            func = getattr(self.logger, level.lower())
            if args or kwargs:
                func(message.format(*args, **kwargs))
            else:
                func(message)


class BacktestEventLogger(TradingEventLogger):
    """Specialized logger for backtesting."""

    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.data_quality_stats = {}

    def log_data_loading(self, rows_loaded: int, rows_processed: int, time_range: tuple):
        quality_pct = (rows_processed / rows_loaded * 100) if rows_loaded > 0 else 0
        self.logger.info(
            f"DATA LOADED: {rows_processed}/{rows_loaded} rows ({quality_pct:.1f}% quality) | Range: {time_range[0]} to {time_range[1]}"
        )
        self.data_quality_stats = {'total': rows_loaded, 'processed': rows_processed, 'quality': quality_pct}

    def log_indicator_calculation(self, indicators_enabled: List[str], calculation_time: float):
        self.logger.info(f"INDICATORS CALCULATED: {', '.join(indicators_enabled)} ({calculation_time:.2f}s)")

    def log_backtest_completion(self, total_time: float, total_bars: int):
        bars_per_sec = total_bars / total_time if total_time > 0 else 0
        self.logger.info(f"BACKTEST COMPLETED: {total_bars} bars in {total_time:.2f}s ({bars_per_sec:.0f} bars/sec)")


def create_smart_logger(name: str, config: Dict[str, Any], logger_type: str = 'trading') -> TradingEventLogger:
    if logger_type == 'backtest':
        return BacktestEventLogger(name, config)
    return TradingEventLogger(name, config)
