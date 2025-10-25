"""
Windows-safe log file handler to prevent permission errors during rotation.
"""

import os
import logging
import logging.handlers
from typing import Optional
import datetime


class WindowsSafeRotatingFileHandler(logging.handlers.RotatingFileHandler):
    """
    A Windows-safe version of RotatingFileHandler that handles file locking issues.
    """
    
    def __init__(self, filename, mode='a', maxBytes=0, backupCount=0, encoding=None, delay=True):
        """Initialize with delay=True to avoid immediate file creation."""
        super().__init__(filename, mode, maxBytes, backupCount, encoding, delay)
        self._rotation_failed_count = 0
        self._max_rotation_failures = 3
    
    def doRollover(self):
        """
        Override rollover to handle Windows file locking gracefully.
        """
        if self.stream:
            self.stream.close()
            self.stream = None
            
        try:
            # Original rotation logic
            super().doRollover()
            self._rotation_failed_count = 0  # Reset on success
        except (PermissionError, OSError) as e:
            self._rotation_failed_count += 1
            
            # If rotation keeps failing, switch to timestamped files
            if self._rotation_failed_count >= self._max_rotation_failures:
                self._fallback_to_timestamped_file()
            else:
                # Try to continue without rotation
                try:
                    self.stream = self._open()
                except Exception:
                    # Last resort: create new timestamped file
                    self._fallback_to_timestamped_file()
    
    def _fallback_to_timestamped_file(self):
        """Create a new file with timestamp when rotation fails."""
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name, ext = os.path.splitext(self.baseFilename)
            new_filename = f"{base_name}_{timestamp}{ext}"
            self.baseFilename = new_filename
            self.stream = self._open()
            self._rotation_failed_count = 0
        except Exception:
            # Ultimate fallback: disable file logging for this handler
            self.stream = None


def create_safe_file_handler(logfile: str, max_bytes: int, backup_count: int, 
                           formatter: logging.Formatter) -> Optional[logging.Handler]:
    """
    Create a Windows-safe file handler with fallback options.
    """
    try:
        # First try: Windows-safe rotating handler
        handler = WindowsSafeRotatingFileHandler(
            logfile,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8',
            delay=True
        )
        handler.setFormatter(formatter)
        handler.setLevel(logging.DEBUG)
        return handler
        
    except Exception:
        try:
            # Fallback: Simple file handler without rotation
            handler = logging.FileHandler(logfile, encoding='utf-8', delay=True)
            handler.setFormatter(formatter)
            handler.setLevel(logging.DEBUG)
            return handler
            
        except Exception:
            # Last resort: Return None to disable file logging
            return None


def cleanup_old_logs(log_directory: str, days_to_keep: int = 7) -> None:
    """
    Clean up old log files to prevent disk space issues.
    """
    try:
        if not os.path.exists(log_directory):
            return
            
        cutoff_time = datetime.datetime.now() - datetime.timedelta(days=days_to_keep)
        
        for filename in os.listdir(log_directory):
            if filename.endswith('.log') or filename.endswith('.log.1'):
                filepath = os.path.join(log_directory, filename)
                try:
                    file_time = datetime.datetime.fromtimestamp(os.path.getmtime(filepath))
                    if file_time < cutoff_time:
                        os.remove(filepath)
                except (OSError, PermissionError):
                    # Skip files that can't be deleted
                    continue
                    
    except Exception:
        # Don't let cleanup errors affect the main application
        pass