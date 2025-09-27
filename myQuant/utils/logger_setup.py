# filepath: utils/logger_setup.py
import logging
from typing import Dict, Any

def setup_logger(log_file: str = "unified_gui.log", log_level: int = logging.INFO):
    """
    Compatibility wrapper that delegates to utils.logging_utils.setup_logging.
    Fail-fast: raise if delegation is not possible.
    """
    from .logging_utils import setup_logging  # let ImportError propagate on serious issues

    lvl = log_level if isinstance(log_level, int) else getattr(logging, str(log_level).upper(), None)
    if lvl is None:
        raise ValueError(f"Invalid log level: {log_level}")

    # Delegate without fallback
    return setup_logging(log_level=lvl, log_file=log_file, console_output=True, file_rotation=True, module_name="logger_setup")

def setup_logging_from_config(config: Dict[str, Any]):
    """
    Configure logging strictly from config dict. Raise if required keys missing.
    """
    if not isinstance(config, dict):
        raise TypeError("setup_logging_from_config expects a dict")

    logging_cfg = config.get("logging", {}) or {}
    required = ["logfile", "verbosity", "console_output", "file_rotation"]
    missing = [k for k in required if k not in logging_cfg]
    if missing:
        raise RuntimeError(f"Logging configuration missing keys: {missing}")

    from .logging_utils import setup_logging
    return setup_logging(
        log_level=str(logging_cfg["verbosity"]),
        log_file=str(logging_cfg["logfile"]),
        console_output=bool(logging_cfg["console_output"]),
        file_rotation=bool(logging_cfg["file_rotation"]),
        module_name="logger_setup"
    )