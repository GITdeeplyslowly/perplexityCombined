"""
utils/logger.py - Single high-performance logger (SSOT-driven)

- Enforces frozen MappingProxyType input (no internal fallbacks).
- Idempotent, thread-safe setup_from_config(...)
- Hot-loop helpers: increment_tick_counter, get_tick_counter, should_log_tick
- HighPerfLogger: lazy formatting + rate-limited tick_debug, guaranteed INFO for signals/trades
- Optional JSON event stream for reproducible backtest analysis
"""
from types import MappingProxyType
import logging
import logging.handlers
import os
import json
import threading
from typing import Optional, Any, Mapping

_config_lock = threading.RLock()
_setup_done = False

_tick_lock = threading.RLock()
_tick_counter = 0

def setup_from_config(frozen_cfg: MappingProxyType) -> logging.Logger:
    """
    Idempotent setup from frozen config. Requires MappingProxyType and 'logging' key.
    Raises TypeError/KeyError on invalid input to enforce SSOT.
    """
    global _setup_done
    if not isinstance(frozen_cfg, MappingProxyType):
        raise TypeError("setup_from_config expects a frozen MappingProxyType (SSOT)")

    log_cfg = frozen_cfg['logging']  # fail-fast if missing
    with _config_lock:
        if _setup_done:
            return logging.getLogger()

        root = logging.getLogger()
        level = getattr(logging, str(log_cfg.get('verbosity', 'INFO')).upper(), logging.INFO)
        root.setLevel(level)

        datefmt = "%Y-%m-%d %H:%M:%S"
        fmt_text = "%(asctime)s %(levelname)s %(name)s: %(message)s"
        formatter = logging.Formatter(fmt_text, datefmt)

        # File handler
        if bool(log_cfg.get('log_to_file', True)):
            logfile = str(log_cfg['logfile'])
            dirname = os.path.dirname(logfile)
            if dirname:
                os.makedirs(dirname, exist_ok=True)
            fh = logging.handlers.RotatingFileHandler(
                logfile,
                maxBytes=int(log_cfg.get('max_file_size', 10 * 1024 * 1024)),
                backupCount=int(log_cfg.get('backup_count', 5)),
                encoding='utf-8'
            )
            fh.setFormatter(formatter)
            fh.setLevel(logging.DEBUG)
            root.addHandler(fh)

        # Console
        if bool(log_cfg.get('console_output', True)):
            ch = logging.StreamHandler()
            ch.setFormatter(formatter)
            ch.setLevel(level)
            root.addHandler(ch)

        # Optional JSON event sink
        if bool(log_cfg.get('json_event_log', False)):
            evt_file = str(log_cfg.get('json_event_file', os.path.join("logs", "events.jsonl")))
            evt_dir = os.path.dirname(evt_file)
            if evt_dir:
                os.makedirs(evt_dir, exist_ok=True)
            eh = logging.handlers.RotatingFileHandler(evt_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding='utf-8')
            eh.setFormatter(logging.Formatter("%(message)s"))
            eh.setLevel(logging.INFO)
            root.addHandler(eh)

        # per-component overrides
        for name, lvl in (log_cfg.get('log_level_overrides') or {}).items():
            try:
                logging.getLogger(name).setLevel(getattr(logging, str(lvl).upper()))
            except Exception:
                pass

        root.info("Logging configured from frozen config")
        _setup_done = True
        return root

def increment_tick_counter() -> int:
    """Increment the global tick counter (thread-safe). Call once per tick."""
    global _tick_counter
    with _tick_lock:
        _tick_counter += 1
        return _tick_counter

def get_tick_counter() -> int:
    with _tick_lock:
        return _tick_counter

def should_log_tick(interval: int) -> bool:
    """True when tick counter % interval == 0. interval <= 0 => always True."""
    try:
        interval = int(interval)
    except Exception:
        return True
    if interval <= 0:
        return True
    with _tick_lock:
        return (_tick_counter % interval) == 0

class HighPerfLogger:
    """
    Lightweight logger optimized for hot loops.
    Usage: perf = HighPerfLogger(__name__, frozen_cfg)
           increment_tick_counter(); perf.tick_debug(lambda: format(...))
    """
    def __init__(self, name: str, frozen_cfg: MappingProxyType):
        if not isinstance(frozen_cfg, MappingProxyType):
            raise TypeError("HighPerfLogger requires a frozen MappingProxyType config")
        # ensure root configured
        setup_from_config(frozen_cfg)
        self.logger = logging.getLogger(name)
        self._cfg = frozen_cfg
        self._tick_interval = int(frozen_cfg['logging'].get('tick_log_interval', 1000))
        self._entry_block_count = 0
        self.event_logger = logging.getLogger(f"{name}.events")

    def tick_debug(self, lazy_msg_func, *args, **kwargs):
        """Evaluate lazy_msg_func only if DEBUG enabled and rate-limited."""
        try:
            if self.logger.isEnabledFor(logging.DEBUG) and should_log_tick(self._tick_interval):
                try:
                    msg = lazy_msg_func(*args, **kwargs)
                except Exception:
                    msg = "tick_debug: formatter error"
                try:
                    self.logger.debug(msg)
                except Exception:
                    pass
        except Exception:
            # defensive: never raise from hot-loop logging
            pass

    def entry_blocked(self, reason: str, summary_every: int = 100):
        self._entry_block_count += 1
        if (self._entry_block_count % summary_every) == 1:
            self.logger.info(f"ENTRY BLOCKED (#{self._entry_block_count}): {reason}")
        elif self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"Entry blocked #{self._entry_block_count}: {reason}")

    def signal_generated(self, signal_type: str, price: float, reason: str = "", run_id: Optional[str] = None):
        self.logger.info(f"SIGNAL {signal_type} @ {price:.2f}: {reason}")
        if bool(self._cfg['logging'].get('json_event_log', False)):
            evt = {"type": "signal", "name": self.logger.name, "signal": signal_type, "price": price, "reason": reason, "run_id": run_id}
            try:
                self.event_logger.info(json.dumps(evt))
            except Exception:
                pass

    def trade_executed(self, action: str, price: float, quantity: int, reason: str = "", trade_id: Optional[str] = None, run_id: Optional[str] = None):
        self.logger.info(f"TRADE {action}: {quantity} @ {price:.2f} - {reason}")
        if bool(self._cfg['logging'].get('json_event_log', False)):
            evt = {"type": "trade", "name": self.logger.name, "action": action, "price": price, "quantity": quantity, "reason": reason, "trade_id": trade_id, "run_id": run_id}
            try:
                self.event_logger.info(json.dumps(evt))
            except Exception:
                pass

    def session_start(self, session_info: str):
        self.logger.info(f"SESSION START: {session_info}")

    def session_end(self, session_summary: str):
        self.logger.info(f"SESSION END: {session_summary}")

# helper formatters
def format_tick_message(tick_num: int, price: float, volume: Optional[int] = None) -> str:
    if volume is not None:
        return f"Tick {tick_num}: {price:.2f} vol={volume}"
    return f"Tick {tick_num}: {price:.2f}"
