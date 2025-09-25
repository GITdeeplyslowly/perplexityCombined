"""
config_helper.py - Configuration helpers (SSOT via config.defaults)

Workflow enforced:
- GUI: create_config_from_defaults() -> mutate -> validate_config(cfg) -> freeze_config(cfg)
- Runners/strategies: receive frozen MappingProxyType and use ConfigAccessor(frozen_cfg)
- No legacy adapter/wrapper present.
"""
import logging
from typing import Dict, Any
from copy import deepcopy
from types import MappingProxyType

logger = logging.getLogger(__name__)

# Logging verbosity helpers (GUI dropdown + resolver)
LOG_VERBOSITY_OPTIONS = ['minimal', 'normal', 'verbose', 'debug']

# ---- Added: small, safe config factory, validator, freezer and accessor ----
try:
    from config.defaults import DEFAULT_CONFIG
except Exception:
    DEFAULT_CONFIG = {}

def create_config_from_defaults() -> Dict[str, Any]:
    """
    Produce a mutable runtime config copied from DEFAULT_CONFIG (SSOT).
    GUI uses this to build runtime config before validation and freeze.
    """
    if not isinstance(DEFAULT_CONFIG, dict):
        raise RuntimeError("DEFAULT_CONFIG missing or invalid")
    return deepcopy(DEFAULT_CONFIG)

def validate_config(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Perform lightweight validation and return a dict containing:
      { "valid": bool, "errors": [..], "warnings": [..] }
    This is intentionally conservative - detailed validation can be implemented later.
    """
    result = {"valid": True, "errors": [], "warnings": []}
    if not isinstance(cfg, dict):
        result["valid"] = False
        result["errors"].append("Config must be a dictionary")
        return result

    # Minimal required sections (strict)
    required_sections = ['strategy', 'risk', 'capital', 'instrument', 'session']
    for sec in required_sections:
        if sec not in cfg:
            result["valid"] = False
            result["errors"].append(f"Missing required section: {sec}")

    # Logging section validation (must include canonical keys)
    if 'logging' in cfg:
        logging_cfg = cfg['logging'] or {}
        for key in ("logfile", "verbosity", "console_output", "file_rotation"):
            if key not in logging_cfg:
                result["valid"] = False
                result["errors"].append(f"logging.{key} missing")
    else:
        result["valid"] = False
        result["errors"].append("Missing logging section")

    return result

def freeze_config(cfg: Dict[str, Any]) -> MappingProxyType:
    """
    Return an immutable MappingProxyType copy of the provided config.
    Caller should validate before freezing.
    """
    if not isinstance(cfg, dict):
        raise TypeError("freeze_config expects a dict")
    return MappingProxyType(deepcopy(cfg))

class ConfigAccessor:
    """
    Small helper to read frozen mapping proxy with dot-path and nested access.
    Example: accessor.get('strategy.fast_ema') -> value
    """
    def __init__(self, frozen_cfg: MappingProxyType):
        if not isinstance(frozen_cfg, MappingProxyType):
            raise TypeError("ConfigAccessor expects a MappingProxyType")
        self._cfg = frozen_cfg

    def get(self, path: str, default: Any = None):
        """Get nested configuration value by dot-separated path."""
        if not path:
            return default
        cur = self._cfg
        for part in path.split('.'):
            if isinstance(cur, MappingProxyType) or isinstance(cur, dict):
                cur = cur.get(part, default)
            else:
                return default
            if cur is default:
                return default
        return cur