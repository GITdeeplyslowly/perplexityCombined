"""
Enhanced Error Handler for Development vs Production

Provides configurable error handling that adapts to different environments:
- Full debugging in development
- Performance optimization in production  
- Configurable error tolerance levels
"""

import logging
import traceback
import time
from typing import Optional, Dict, Any, Callable
from enum import Enum
from dataclasses import dataclass

class ErrorSeverity(Enum):
    """Error severity classification for tolerance decisions"""
    CRITICAL = "CRITICAL"    # Never suppress - halt trading
    HIGH = "HIGH"           # Log always, raise in dev
    MEDIUM = "MEDIUM"       # Log in dev, suppress in prod  
    LOW = "LOW"             # Suppress in production

class Environment(Enum):
    """Runtime environment types"""
    DEVELOPMENT = "DEVELOPMENT"
    TESTING = "TESTING" 
    PRODUCTION = "PRODUCTION"

@dataclass
class ErrorStats:
    """Track error statistics for monitoring"""
    total_errors: int = 0
    errors_by_severity: Dict[ErrorSeverity, int] = None
    errors_by_context: Dict[str, int] = None
    last_reset_time: float = 0
    
    def __post_init__(self):
        if self.errors_by_severity is None:
            self.errors_by_severity = {severity: 0 for severity in ErrorSeverity}
        if self.errors_by_context is None:
            self.errors_by_context = {}

class DevelopmentAwareErrorHandler:
    """
    Smart error handler that provides full debugging visibility during development
    while maintaining high performance in production environments.
    """
    
    def __init__(self, config: Dict[str, Any], logger_name: str = "enhanced_strategy"):
        self.config = config
        self.logger = logging.getLogger(logger_name)
        self.stats = ErrorStats()
        self.stats.last_reset_time = time.time()
        
        # Parse environment from config
        env_str = config.get('environment', 'DEVELOPMENT').upper()
        try:
            self.environment = Environment(env_str)
        except ValueError:
            self.environment = Environment.DEVELOPMENT
            self.logger.warning(f"Unknown environment '{env_str}', defaulting to DEVELOPMENT")
            
        # Configuration flags
        self.log_all_errors = config.get('log_all_errors', True)
        self.suppress_low = config.get('suppress_low_severity', False) 
        self.suppress_medium = config.get('suppress_medium_severity', False)
        self.performance_mode = config.get('performance_mode', False)
        self.max_errors_per_minute = config.get('max_errors_per_minute', 100)
        self.detailed_logging = config.get('detailed_green_tick_logging', True)
        self.halt_on_critical = config.get('halt_on_critical_errors', True)
        
    def handle_error(self, 
                    error: Exception, 
                    context: str,
                    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                    default_return: Any = None,
                    suppress_in_production: bool = None) -> Any:
        """
        Handle error based on environment configuration and severity level.
        
        Args:
            error: The exception that occurred
            context: Description of where/why error occurred
            severity: Criticality level of the error
            default_return: Value to return if error is suppressed
            suppress_in_production: Override production suppression behavior
            
        Returns:
            default_return if error suppressed, otherwise raises exception
        """
        
        # Update statistics
        self._update_stats(severity, context)
        
        # Rate limiting check
        if not self._should_process_error():
            return default_return
            
        # CRITICAL errors are never suppressed in any environment
        if severity == ErrorSeverity.CRITICAL:
            self._handle_critical_error(error, context)
            if self.halt_on_critical:
                raise error
            return default_return
            
        # Environment-specific handling
        if self.environment == Environment.DEVELOPMENT:
            return self._handle_development_error(error, context, severity, default_return)
        elif self.environment == Environment.PRODUCTION:
            return self._handle_production_error(error, context, severity, default_return, suppress_in_production)
        else:  # TESTING
            return self._handle_testing_error(error, context, severity, default_return)
    
    def _update_stats(self, severity: ErrorSeverity, context: str):
        """Update error statistics for monitoring"""
        # Reset counters every minute
        current_time = time.time()
        if current_time - self.stats.last_reset_time > 60:
            self.stats.errors_by_severity = {s: 0 for s in ErrorSeverity}
            self.stats.errors_by_context.clear()
            self.stats.last_reset_time = current_time
            
        self.stats.total_errors += 1
        self.stats.errors_by_severity[severity] += 1
        self.stats.errors_by_context[context] = self.stats.errors_by_context.get(context, 0) + 1
    
    def _should_process_error(self) -> bool:
        """Check if we should process this error (rate limiting)"""
        total_in_window = sum(self.stats.errors_by_severity.values())
        return total_in_window < self.max_errors_per_minute
    
    def _handle_critical_error(self, error: Exception, context: str):
        """Handle critical errors that must never be suppressed"""
        self.logger.error(f"🚨 CRITICAL ERROR in {context}")
        self.logger.error(f"🚨 Exception: {type(error).__name__}: {error}")
        if self.detailed_logging:
            self.logger.error(f"🚨 Full traceback:\n{traceback.format_exc()}")
    
    def _handle_development_error(self, error: Exception, context: str, 
                                severity: ErrorSeverity, default_return: Any) -> Any:
        """Development environment: Full visibility, selective raising"""
        
        # Always log with full details in development
        severity_emoji = {"CRITICAL": "🚨", "HIGH": "🔥", "MEDIUM": "⚠️", "LOW": "ℹ️"}
        emoji = severity_emoji.get(severity.value, "❓")
        
        self.logger.error(f"{emoji} DEV ERROR [{severity.value}] in {context}")
        self.logger.error(f"{emoji} Exception: {type(error).__name__}: {error}")
        
        if self.detailed_logging:
            self.logger.error(f"{emoji} Full traceback:\n{traceback.format_exc()}")
        
        # In development, raise HIGH and CRITICAL errors for debugging
        if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            raise error
            
        return default_return
    
    def _handle_production_error(self, error: Exception, context: str, 
                               severity: ErrorSeverity, default_return: Any,
                               suppress_override: Optional[bool]) -> Any:
        """Production environment: Performance-focused, selective logging"""
        
        # Check if we should suppress this error
        should_suppress = suppress_override
        if should_suppress is None:
            should_suppress = self._should_suppress_in_production(severity)
        
        if not should_suppress:
            # Log with minimal overhead in production
            if not self.performance_mode:
                self.logger.warning(f"⚠️ [{severity.value}] {context}: {type(error).__name__}")
            
            # Only raise HIGH severity errors in production
            if severity == ErrorSeverity.HIGH:
                raise error
        
        return default_return
    
    def _handle_testing_error(self, error: Exception, context: str, 
                            severity: ErrorSeverity, default_return: Any) -> Any:
        """Testing environment: Controlled logging, no raising"""
        
        # Log for test analysis but don't raise (unless critical)
        self.logger.info(f"🧪 TEST ERROR [{severity.value}] in {context}: {type(error).__name__}: {error}")
        
        if severity == ErrorSeverity.CRITICAL:
            raise error
            
        return default_return
    
    def _should_suppress_in_production(self, severity: ErrorSeverity) -> bool:
        """Determine if error should be suppressed in production"""
        if severity == ErrorSeverity.LOW and self.suppress_low:
            return True
        if severity == ErrorSeverity.MEDIUM and self.suppress_medium:
            return True
        return False
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get current error statistics for monitoring"""
        return {
            "total_errors": self.stats.total_errors,
            "errors_by_severity": dict(self.stats.errors_by_severity),
            "errors_by_context": dict(self.stats.errors_by_context),
            "environment": self.environment.value,
            "performance_mode": self.performance_mode
        }
    
    def create_safe_wrapper(self, func: Callable, context: str, 
                           severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                           default_return: Any = None) -> Callable:
        """
        Create a wrapper function that handles errors for any callable.
        Useful for wrapping indicator calculations, signal generation, etc.
        """
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                return self.handle_error(e, context, severity, default_return)
        
        return wrapper

def create_error_handler_from_config(config: Dict[str, Any], logger_name: str = "strategy") -> DevelopmentAwareErrorHandler:
    """
    Factory function to create error handler from configuration.
    
    Args:
        config: Configuration dictionary (should have 'debug' section)
        logger_name: Name for the logger instance
        
    Returns:
        Configured DevelopmentAwareErrorHandler instance
    """
    debug_config = config.get('debug', {})
    
    # Default to development settings if no debug config
    if not debug_config:
        debug_config = {
            "environment": "DEVELOPMENT",
            "log_all_errors": True,
            "suppress_low_severity": False,
            "suppress_medium_severity": False,
            "performance_mode": False,
            "max_errors_per_minute": 1000,
            "detailed_green_tick_logging": True,
            "halt_on_critical_errors": True
        }
    
    return DevelopmentAwareErrorHandler(debug_config, logger_name)

# Convenience decorators for common error handling patterns
def safe_tick_processing(error_handler: DevelopmentAwareErrorHandler):
    """Decorator for tick processing methods"""
    def decorator(func):
        return error_handler.create_safe_wrapper(
            func, 
            f"tick_processing_{func.__name__}", 
            ErrorSeverity.HIGH, 
            None
        )
    return decorator

def safe_indicator_calculation(error_handler: DevelopmentAwareErrorHandler):
    """Decorator for indicator calculation methods"""
    def decorator(func):
        return error_handler.create_safe_wrapper(
            func,
            f"indicator_{func.__name__}",
            ErrorSeverity.MEDIUM,
            None
        )
    return decorator

def safe_logging_operation(error_handler: DevelopmentAwareErrorHandler):
    """Decorator for logging operations"""
    def decorator(func):
        return error_handler.create_safe_wrapper(
            func,
            f"logging_{func.__name__}",
            ErrorSeverity.LOW,
            None
        )
    return decorator