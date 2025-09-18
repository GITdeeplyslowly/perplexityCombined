"""
config_helper.py - Configuration helpers (SSOT via config.defaults)

Workflow enforced:
- GUI: create_config_from_defaults() -> mutate -> validate_config(cfg) -> freeze_config(cfg)
- Runners/strategies: receive frozen MappingProxyType and use ConfigAccessor(frozen_cfg)
- No legacy adapter/wrapper present.
"""
from typing import Dict, Any, Optional, List
from copy import deepcopy
from types import MappingProxyType
import logging

logger = logging.getLogger(__name__)

# Logging verbosity helpers (GUI dropdown + resolver)
LOG_VERBOSITY_OPTIONS = ['minimal', 'normal', 'verbose', 'debug']
LOG_VERBOSITY_MAP = {
    'minimal': logging.WARNING,
    'normal': logging.INFO,
    'verbose': logging.DEBUG,
    'debug': logging.DEBUG
}

def get_logging_verbosity_options() -> List[str]:
    return LOG_VERBOSITY_OPTIONS.copy()

def resolve_logging_level(verbosity: Optional[Any], default=logging.INFO) -> int:
    if verbosity is None:
        return default
    try:
        if isinstance(verbosity, (int, float)):
            return int(verbosity)
        vs = str(verbosity).lower()
        if vs.isdigit():
            return int(vs)
        return LOG_VERBOSITY_MAP.get(vs, default)
    except Exception:
        return default

def create_config_from_defaults() -> Dict[str, Any]:
    """Return a deep copy of DEFAULT_CONFIG (SSOT)."""
    try:
        from config.defaults import DEFAULT_CONFIG
    except Exception as e:
        logger.exception("Could not import DEFAULT_CONFIG from config.defaults: %s", e)
        return {}
    return deepcopy(DEFAULT_CONFIG)

def validate_config(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Authoritative, GUI-facing validation.
    Returns: {'valid': bool, 'errors': [str,...]}
    Keep checks explicit: presence of expected sections/keys. Extend checks as project stabilizes.
    """
    errors: List[str] = []
    if not isinstance(cfg, dict):
        return {'valid': False, 'errors': ['config must be a dict']}

    required = {
        'strategy': [
            'fast_ema', 'slow_ema', 'macd_fast', 'macd_slow', 'macd_signal',
            'atr_len', 'consecutive_green_bars', 'use_ema_crossover', 'use_macd',
            'use_vwap', 'use_rsi_filter'
        ],
        'risk': [
            'max_positions_per_day', 'base_sl_points', 'tp_points', 'tp_percents',
            'use_trail_stop', 'trail_activation_points', 'trail_distance_points',
            'risk_per_trade_percent', 'commission_percent', 'commission_per_trade',
            'tick_size', 'max_position_value_percent', 'stt_percent',
            'exchange_charges_percent', 'gst_percent', 'slippage_points'
        ],
        'capital': ['initial_capital'],
        'instrument': ['symbol', 'lot_size', 'tick_size', 'product_type'],
        'session': ['is_intraday', 'start_hour', 'start_min', 'end_hour', 'end_min', 'timezone'],
        'logging': ['verbosity', 'log_to_file', 'log_file']
    }

    for section, keys in required.items():
        if section not in cfg or not isinstance(cfg[section], dict):
            errors.append(f"missing or invalid section: {section}")
            continue
        for k in keys:
            if k not in cfg[section]:
                errors.append(f"missing key: {section}.{k}")

    return {'valid': len(errors) == 0, 'errors': errors}

def freeze_config(cfg: Dict[str, Any]) -> MappingProxyType:
    """
    Return a read-only MappingProxyType view for the top-level config.
    Shallow freeze: top-level mapping is read-only. GUI should not mutate nested dicts after freeze.
    """
    try:
        return MappingProxyType(cfg)
    except Exception:
        logger.exception("freeze_config failed - returning original dict")
        return cfg  # type: ignore

class ConfigAccessor:
    """
    Strict accessor for a validated frozen config dict (MappingProxyType).
    Raises KeyError on missing sections/keys (fail-fast).
    """

    def __init__(self, config: Optional[Dict[str, Any]]):
        if not isinstance(config, MappingProxyType):
            logger.error(
                "ConfigAccessor requires a frozen MappingProxyType produced by freeze_config(). Received: %s",
                type(config)
            )
            raise ValueError(
                "Config must be a frozen MappingProxyType. Use create_config_from_defaults() -> validate_config(cfg) -> freeze_config(cfg)."
            )
        self.config = config

    def get_section_param(self, section: str, key: str) -> Any:
        sec = self.config.get(section)
        if sec is None or not isinstance(sec, dict):
            logger.error("Missing or invalid section in config: %s", section)
            raise KeyError(section)
        if key not in sec:
            logger.error("Missing key in config: %s.%s", section, key)
            raise KeyError(f"{section}.{key}")
        return sec[key]

    def get(self, path: str) -> Any:
        """Support 'section.key' access or top-level keys."""
        if '.' not in path:
            if path in self.config:
                return self.config[path]
            logger.error("Missing top-level key in config: %s", path)
            raise KeyError(path)
        section, key = path.split('.', 1)
        return self.get_section_param(section, key)

    # Typed getters used across the codebase
    def get_strategy_param(self, key: str) -> Any:
        return self.get_section_param('strategy', key)

    def get_risk_param(self, key: str) -> Any:
        return self.get_section_param('risk', key)

    def get_instrument_param(self, key: str) -> Any:
        return self.get_section_param('instrument', key)

    def get_session_param(self, key: str) -> Any:
        return self.get_section_param('session', key)

    def get_capital_param(self, key: str) -> Any:
        return self.get_section_param('capital', key)

    def get_logging_param(self, key: str) -> Any:
        return self.get_section_param('logging', key)