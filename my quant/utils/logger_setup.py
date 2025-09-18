# filepath: utils/logger_setup.py
import logging
from typing import Dict, Any

def setup_logger(log_file: str = "unified_gui.log", log_level: int = logging.INFO):
    """
    Lightweight logger initializer for legacy code paths.
    Prefer setup_logging_from_config for config-driven behavior.
    """
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    logging.getLogger().setLevel(log_level)
    return logging.getLogger()

def setup_logging_from_config(config: Dict[str, Any]):
    """
    Configure logging from config dict (defaults.py is SSOT).
    Expects config['logging']['verbosity'] to be one of:
      'minimal' | 'detailed' | 'debug'  (or equivalent strings)
    Applies optional per-component overrides in config['logging']['log_level_overrides'].
    """
    level_map = {
        'minimal': logging.WARNING,
        'detailed': logging.INFO,
        'info': logging.INFO,
        'debug': logging.DEBUG,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'critical': logging.CRITICAL
    }

    logging_cfg = (config or {}).get('logging', {}) or {}
    verbosity = str(logging_cfg.get('verbosity', '')).lower()
    root_level = level_map.get(verbosity, logging.INFO)

    logging.basicConfig(
        level=root_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    logging.getLogger().setLevel(root_level)

    overrides = logging_cfg.get('log_level_overrides', {}) or {}
    for logger_name, lvl in overrides.items():
        try:
            if isinstance(lvl, str):
                lvl_val = getattr(logging, lvl.upper(), None) or level_map.get(str(lvl).lower())
            else:
                lvl_val = int(lvl)
        except Exception:
            lvl_val = None
        if lvl_val is not None:
            logging.getLogger(logger_name).setLevel(lvl_val)