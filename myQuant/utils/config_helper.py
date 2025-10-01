"""
config_helper.py - Configuration helpers (SSOT via config.defaults)
Enforces: create -> validate -> freeze (MappingProxyType) workflow.
"""
from typing import Dict, Any
from copy import deepcopy
from types import MappingProxyType
import logging
import json
import os

logger = logging.getLogger(__name__)

try:
    from config.defaults import DEFAULT_CONFIG
except Exception:
    DEFAULT_CONFIG = {}

MISSING = object()

def create_config_from_defaults() -> Dict[str, Any]:
    """Return a deep copy of DEFAULT_CONFIG for GUI mutation."""
    if not isinstance(DEFAULT_CONFIG, dict):
        raise RuntimeError("DEFAULT_CONFIG missing or invalid")
    return deepcopy(DEFAULT_CONFIG)

def validate_config(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Minimal validator: checks required top-level sections and logging presence.
    Returns {'valid': bool, 'errors': [...]}.
    GUI should run full validation before freeze.
    """
    errors = []
    required_sections = ['strategy', 'risk', 'capital', 'instrument', 'session', 'logging']
    for s in required_sections:
        if s not in cfg:
            errors.append(f"Missing section: {s}")
    # logging: enforce canonical key 'logfile'
    try:
        log = cfg['logging']
        if 'logfile' not in log or not log['logfile']:
            errors.append("logging.logfile is required")
    except Exception:
        errors.append("Invalid logging section")

    return {"valid": len(errors) == 0, "errors": errors}

def freeze_config(cfg: Dict[str, Any]) -> MappingProxyType:
    """Return an immutable MappingProxyType of the config (deepcopy then freeze)."""
    if not isinstance(cfg, dict):
        raise TypeError("freeze_config expects a dict")
    # persist a copy for reproducibility
    try:
        os.makedirs("results", exist_ok=True)
        # do not overwrite existing snapshot; caller should save with run_id
    except Exception:
        pass
    return MappingProxyType(deepcopy(cfg))

class ConfigAccessor:
    """Strict accessor to read from frozen MappingProxyType; raises on missing keys."""
    def __init__(self, frozen_cfg: MappingProxyType):
        if not isinstance(frozen_cfg, MappingProxyType):
            raise TypeError("ConfigAccessor requires a frozen MappingProxyType")
        self._cfg = frozen_cfg

    def get(self, path: str, default=MISSING):
        """
        Path like 'strategy.fast_ema' returns value or raises KeyError if missing and no default.
        """
        parts = path.split('.')
        curr = self._cfg
        for p in parts:
            if isinstance(curr, MappingProxyType) and p in curr:
                curr = curr[p]
            elif isinstance(curr, dict) and p in curr:
                curr = curr[p]
            else:
                if default is MISSING:
                    raise KeyError(f"Missing config key: {path}")
                return default
        return curr

    # Backwards-compatible convenience helpers for common sections.
    # These keep callers throughout the codebase working (e.g. researchStrategy).
    def _section_get(self, section: str, param: str, default=MISSING):
        """Internal helper: map section+param -> get('section.param')."""
        return self.get(f"{section}.{param}", default)

    def get_strategy_param(self, param: str, default=MISSING):
        """Get value from the 'strategy' section."""
        return self._section_get("strategy", param, default)

    def get_risk_param(self, param: str, default=MISSING):
        return self._section_get("risk", param, default)

    def get_capital_param(self, param: str, default=MISSING):
        return self._section_get("capital", param, default)

    def get_instrument_param(self, param: str, default=MISSING):
        return self._section_get("instrument", param, default)

    def get_session_param(self, param: str, default=MISSING):
        return self._section_get("session", param, default)

    def get_logging_param(self, param: str, default=MISSING):
        return self._section_get("logging", param, default)

    def get_backtest_param(self, param: str, default=MISSING):
        """Get value from the 'backtest' section (convenience for backtest callers)."""
        return self._section_get("backtest", param, default)
