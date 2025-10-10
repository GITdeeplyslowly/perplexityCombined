#!/usr/bin/env python3
"""
Development vs Production Error Handling Strategy

Creates a configurable error handling system that provides:
- Full debugging visibility during development
- High performance with minimal logging in production
- Configurable tolerance levels for different error types
"""

import logging
from typing import Optional, Dict, Any
from enum import Enum
from dataclasses import dataclass
import traceback
import time

class ErrorSeverity(Enum):
    """Error severity levels for tolerance classification"""
    CRITICAL = "CRITICAL"      # Must never be suppressed - trading halts
    HIGH = "HIGH"             # Important but trading can continue  
    MEDIUM = "MEDIUM"         # Degraded functionality but operational
    LOW = "LOW"               # Minor issues, can be ignored in production

class Environment(Enum):
    """Runtime environment types"""
    DEVELOPMENT = "DEVELOPMENT"
    TESTING = "TESTING" 
    PRODUCTION = "PRODUCTION"

@dataclass
class ErrorConfig:
    """Configuration for error handling behavior"""
    environment: Environment
    log_all_errors: bool = True
    suppress_low_severity: bool = False
    suppress_medium_severity: bool = False
    performance_mode: bool = False
    max_errors_per_minute: int = 100
    
    @classmethod
    def development_config(cls):
        """Full debugging configuration for development"""
        return cls(
            environment=Environment.DEVELOPMENT,
            log_all_errors=True,
            suppress_low_severity=False,
            suppress_medium_severity=False,
            performance_mode=False,
            max_errors_per_minute=1000  # High limit for debugging
        )
    
    @classmethod 
    def production_config(cls):
        """Optimized configuration for live trading"""
        return cls(
            environment=Environment.PRODUCTION,
            log_all_errors=False,
            suppress_low_severity=True,
            suppress_medium_severity=True,
            performance_mode=True,
            max_errors_per_minute=10  # Low limit for performance
        )

class DevelopmentAwareErrorHandler:
    """
    Smart error handler that adapts behavior based on environment
    """
    
    def __init__(self, config: ErrorConfig, logger_name: str = "strategy"):
        self.config = config
        self.logger = logging.getLogger(logger_name)
        self.error_counts = {}
        self.last_reset = time.time()
        
    def handle_error(self, error: Exception, context: str, 
                    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                    default_return: Any = None) -> Any:
        """
        Handle error based on environment and severity
        
        Args:
            error: The exception that occurred
            context: Description of where/why error occurred  
            severity: How critical this error is
            default_return: What to return if error is suppressed
            
        Returns:
            default_return if error suppressed, otherwise raises
        """
        
        # Rate limiting check
        if not self._should_process_error():
            return default_return
            
        # Always log CRITICAL errors regardless of config
        if severity == ErrorSeverity.CRITICAL:
            self._log_critical_error(error, context)
            raise error  # Never suppress critical errors
            
        # Development mode: Log everything and raise
        if self.config.environment == Environment.DEVELOPMENT:
            self._log_development_error(error, context, severity)
            if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
                raise error
            return default_return
            
        # Production mode: Selective handling
        if self.config.environment == Environment.PRODUCTION:
            should_suppress = self._should_suppress_in_production(severity)
            
            if not should_suppress:
                self._log_production_error(error, context, severity)
                if severity == ErrorSeverity.HIGH:
                    raise error
                    
            return default_return
            
        # Testing mode: Log but don't raise
        self._log_testing_error(error, context, severity)
        return default_return
        
    def _should_process_error(self) -> bool:
        """Rate limiting to prevent error spam"""
        current_time = time.time()
        if current_time - self.last_reset > 60:  # Reset every minute
            self.error_counts.clear()
            self.last_reset = current_time
            
        total_errors = sum(self.error_counts.values())
        return total_errors < self.config.max_errors_per_minute
        
    def _should_suppress_in_production(self, severity: ErrorSeverity) -> bool:
        """Determine if error should be suppressed in production"""
        if severity == ErrorSeverity.LOW and self.config.suppress_low_severity:
            return True
        if severity == ErrorSeverity.MEDIUM and self.config.suppress_medium_severity:
            return True
        return False
        
    def _log_critical_error(self, error: Exception, context: str):
        """Always log critical errors with full details"""
        self.logger.error(f"🚨 CRITICAL ERROR in {context}: {error}")
        self.logger.error(f"🚨 Stack trace: {traceback.format_exc()}")
        
    def _log_development_error(self, error: Exception, context: str, severity: ErrorSeverity):
        """Full debugging information for development"""
        self.logger.error(f"🔧 DEV ERROR [{severity.value}] in {context}:")
        self.logger.error(f"🔧 Exception: {type(error).__name__}: {error}")
        self.logger.error(f"🔧 Stack trace: {traceback.format_exc()}")
        
    def _log_production_error(self, error: Exception, context: str, severity: ErrorSeverity):
        """Minimal logging for production performance"""
        if not self.config.performance_mode:
            self.logger.warning(f"⚠️ [{severity.value}] {context}: {type(error).__name__}")
            
    def _log_testing_error(self, error: Exception, context: str, severity: ErrorSeverity):
        """Testing environment logging"""
        self.logger.info(f"🧪 TEST ERROR [{severity.value}] in {context}: {error}")

def create_enhanced_strategy_error_handling():
    """
    Example of how to integrate this into the strategy classes
    """
    
    print("📋 ENHANCED STRATEGY ERROR HANDLING IMPLEMENTATION")
    print("=" * 80)
    
    print("""
🔧 DEVELOPMENT VERSION (liveStrategy.py):

```python
class ModularIntradayStrategy:
    def __init__(self, config: MappingProxyType):
        # Determine environment from config
        env_type = Environment.DEVELOPMENT if config.get('debug_mode', True) else Environment.PRODUCTION
        error_config = ErrorConfig.development_config() if env_type == Environment.DEVELOPMENT else ErrorConfig.production_config()
        
        self.error_handler = DevelopmentAwareErrorHandler(error_config, "live_strategy")
        # ... rest of init
        
    def _update_green_tick_count(self, current_price: float):
        try:
            # ... green tick logic ...
            
        except Exception as e:
            # Smart error handling based on environment
            return self.error_handler.handle_error(
                error=e,
                context="green_tick_count_update", 
                severity=ErrorSeverity.MEDIUM,  # Can continue trading without this
                default_return=None
            )
            
    def on_tick(self, tick: Dict[str, Any]) -> Optional[TradingSignal]:
        try:
            # ... tick processing ...
            
        except Exception as e:
            # Critical path - higher severity
            return self.error_handler.handle_error(
                error=e,
                context="tick_processing",
                severity=ErrorSeverity.HIGH,  # Important for trading
                default_return=None
            )
```

🎯 ERROR CLASSIFICATION STRATEGY:

CRITICAL (Never suppress):
- Configuration validation failures
- Position manager initialization errors
- Broker connection failures

HIGH (Log always, raise in dev):
- Signal generation failures
- Position entry/exit errors
- Critical indicator calculation failures

MEDIUM (Log in dev, suppress in prod):
- Green tick counting errors
- Non-critical indicator failures
- Logging system errors

LOW (Suppress in production):
- Performance logging failures
- Debug message formatting errors
- Statistics calculation errors
""")

def create_configuration_examples():
    """Show configuration examples for different scenarios"""
    
    print("\n📊 CONFIGURATION EXAMPLES")
    print("=" * 80)
    
    print("""
🔧 DEVELOPMENT CONFIGURATION (defaults.py):
```python
'debug_config': {
    'environment': 'DEVELOPMENT',
    'log_all_errors': True,
    'suppress_low_severity': False,
    'suppress_medium_severity': False, 
    'performance_mode': False,
    'max_errors_per_minute': 1000,
    'detailed_green_tick_logging': True,
    'detailed_signal_logging': True
}
```

🚀 PRODUCTION CONFIGURATION (defaults.py):
```python
'debug_config': {
    'environment': 'PRODUCTION',
    'log_all_errors': False,
    'suppress_low_severity': True,
    'suppress_medium_severity': True,
    'performance_mode': True, 
    'max_errors_per_minute': 10,
    'detailed_green_tick_logging': False,
    'detailed_signal_logging': False
}
```

🧪 TESTING CONFIGURATION (defaults.py):
```python
'debug_config': {
    'environment': 'TESTING',
    'log_all_errors': True,
    'suppress_low_severity': False,
    'suppress_medium_severity': False,
    'performance_mode': False,
    'max_errors_per_minute': 500,
    'detailed_green_tick_logging': True,
    'detailed_signal_logging': False  # Less noise in tests
}
```
""")

def show_implementation_benefits():
    """Show the benefits of this approach"""
    
    print("\n✅ BENEFITS OF DEVELOPMENT-AWARE ERROR HANDLING")
    print("=" * 80)
    
    print("""
🔧 DEVELOPMENT BENEFITS:
✅ Full error visibility for debugging
✅ Complete stack traces for root cause analysis  
✅ Detailed logging of all operations
✅ No silent failures - everything is visible
✅ Easy to identify what errors can be tolerated

🚀 PRODUCTION BENEFITS:
✅ High performance with minimal logging overhead
✅ Graceful degradation for non-critical errors
✅ Rate limiting prevents error spam
✅ Critical errors still halt trading when necessary
✅ Configurable tolerance levels

🧪 TESTING BENEFITS:
✅ Controlled error injection for testing
✅ Validation of error handling paths
✅ Performance testing under error conditions
✅ Verification of production configuration

🎯 ERROR TOLERANCE STRATEGY:
✅ Critical errors: Never tolerate (halt trading)
✅ High severity: Tolerate briefly, then investigate  
✅ Medium severity: Tolerate during trading hours, fix between sessions
✅ Low severity: Tolerate indefinitely, batch fix during maintenance
""")

def main():
    """Main demonstration"""
    
    print("🚨 DEVELOPMENT vs PRODUCTION ERROR HANDLING STRATEGY")
    print("=" * 80)
    print("Configurable error handling for robust development and high-performance production")
    print()
    
    create_enhanced_strategy_error_handling()
    create_configuration_examples()
    show_implementation_benefits()
    
    print("\n" + "=" * 80)
    print("📋 IMPLEMENTATION PLAN")
    print("=" * 80)
    
    print("""
PHASE 1: Add error classification to existing strategy
PHASE 2: Implement development-aware error handler
PHASE 3: Add configuration-driven error tolerance
PHASE 4: Create environment-specific configs
PHASE 5: Test error handling in all environments

This approach gives you full debugging visibility during development
while maintaining production performance and stability.
""")

if __name__ == "__main__":
    main()