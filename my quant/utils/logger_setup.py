# filepath: utils/logger_setup.py
import logging

def setup_logger(log_file="unified_gui.log", log_level=logging.INFO):
    """
    Sets up logging to both a file and the console.
    Returns a logger instance.
    """
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Remove all handlers if already set up (prevents duplicate logs)
    if logger.hasHandlers():
        logger.handlers.clear()

    # File handler
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(log_level)
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(log_level)
    ch.setFormatter(logging.Formatter("%(levelname)s %(message)s"))

    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger