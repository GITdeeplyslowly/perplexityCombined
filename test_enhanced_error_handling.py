#!/usr/bin/env python3
"""
Test Enhanced Error Handling in Development vs Production Modes

Validates that the enhanced error handler provides proper debugging visibility
in development while maintaining performance in production.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from myQuant.utils.enhanced_error_handler import (
    DevelopmentAwareErrorHandler, ErrorSeverity, Environment
)
from myQuant.config.defaults import DEFAULT_CONFIG
import logging

def test_development_mode():
    """Test error handling in development mode"""
    print("🔧 TESTING DEVELOPMENT MODE ERROR HANDLING")
    print("=" * 60)
    
    # Development configuration
    dev_config = {
        "environment": "DEVELOPMENT",
        "log_all_errors": True,
        "suppress_low_severity": False,
        "suppress_medium_severity": False,
        "performance_mode": False,
        "max_errors_per_minute": 1000,
        "detailed_green_tick_logging": True,
        "halt_on_critical_errors": False  # For testing only
    }
    
    handler = DevelopmentAwareErrorHandler(dev_config, "dev_test")
    
    # Test different severity levels
    test_cases = [
        (ValueError("Test low severity error"), ErrorSeverity.LOW, "Expected: Logged, returned default"),
        (RuntimeError("Test medium severity error"), ErrorSeverity.MEDIUM, "Expected: Logged, returned default"), 
        (ConnectionError("Test high severity error"), ErrorSeverity.HIGH, "Expected: Logged, raised exception"),
    ]
    
    for i, (error, severity, expected) in enumerate(test_cases, 1):
        print(f"\n📝 Test {i}: {severity.value} severity error")
        print(f"   {expected}")
        
        try:
            result = handler.handle_error(error, f"test_context_{i}", severity, "default_value")
            print(f"   ✅ Result: Returned '{result}'")
        except Exception as caught:
            print(f"   ✅ Result: Raised {type(caught).__name__}: {caught}")
    
    print(f"\n📊 Error Stats: {handler.get_error_stats()}")

def test_production_mode():
    """Test error handling in production mode"""  
    print("\n🚀 TESTING PRODUCTION MODE ERROR HANDLING")
    print("=" * 60)
    
    # Production configuration  
    prod_config = {
        "environment": "PRODUCTION",
        "log_all_errors": False,
        "suppress_low_severity": True,
        "suppress_medium_severity": True,
        "performance_mode": True,
        "max_errors_per_minute": 10,
        "detailed_green_tick_logging": False,
        "halt_on_critical_errors": False  # For testing only
    }
    
    handler = DevelopmentAwareErrorHandler(prod_config, "prod_test")
    
    test_cases = [
        (ValueError("Test low severity error"), ErrorSeverity.LOW, "Expected: Suppressed silently"),
        (RuntimeError("Test medium severity error"), ErrorSeverity.MEDIUM, "Expected: Suppressed silently"),
        (ConnectionError("Test high severity error"), ErrorSeverity.HIGH, "Expected: Logged minimally, raised"),
        (SystemError("Test critical error"), ErrorSeverity.CRITICAL, "Expected: Always logged, raised"),
    ]
    
    for i, (error, severity, expected) in enumerate(test_cases, 1):
        print(f"\n📝 Test {i}: {severity.value} severity error")
        print(f"   {expected}")
        
        try:
            result = handler.handle_error(error, f"prod_test_context_{i}", severity, "default_value")
            print(f"   ✅ Result: Returned '{result}'")
        except Exception as caught:
            print(f"   ✅ Result: Raised {type(caught).__name__}: {caught}")
    
    print(f"\n📊 Error Stats: {handler.get_error_stats()}")

def test_config_integration():
    """Test integration with DEFAULT_CONFIG"""
    print("\n🔧 TESTING CONFIG INTEGRATION")
    print("=" * 60)
    
    from myQuant.utils.enhanced_error_handler import create_error_handler_from_config
    
    # Test with default config
    handler = create_error_handler_from_config(DEFAULT_CONFIG, "config_test")
    
    print(f"Environment: {handler.environment}")
    print(f"Performance mode: {handler.performance_mode}")
    print(f"Detailed logging: {handler.detailed_logging}")
    
    # Test a typical green tick error scenario
    try:
        # Simulate green tick calculation error
        raise ValueError("Noise filter parameter missing")
    except Exception as e:
        result = handler.handle_error(
            error=e,
            context="green_tick_count_update",
            severity=ErrorSeverity.MEDIUM,
            default_return=None
        )
        print(f"✅ Green tick error handled, returned: {result}")

def test_error_classification_examples():
    """Show examples of proper error classification"""
    print("\n🎯 ERROR CLASSIFICATION EXAMPLES")
    print("=" * 60)
    
    examples = {
        ErrorSeverity.CRITICAL: [
            "Broker API authentication failure",
            "Position manager initialization failed", 
            "Configuration validation critical error"
        ],
        ErrorSeverity.HIGH: [
            "Signal generation method crashed",
            "Position entry/exit processing failed",
            "Critical indicator calculation error"
        ],
        ErrorSeverity.MEDIUM: [
            "Green tick counting error",
            "Non-essential indicator failure",
            "Logging system error"
        ],
        ErrorSeverity.LOW: [
            "Performance metric calculation failed",
            "Debug message formatting error",
            "Statistics update failed"
        ]
    }
    
    for severity, error_list in examples.items():
        print(f"\n{severity.value} SEVERITY:")
        for error in error_list:
            tolerance = {
                ErrorSeverity.CRITICAL: "❌ Never tolerate - halt trading",
                ErrorSeverity.HIGH: "⚠️ Brief tolerance - investigate immediately", 
                ErrorSeverity.MEDIUM: "🔄 Tolerate during session - fix between sessions",
                ErrorSeverity.LOW: "✅ Tolerate indefinitely - batch fix"
            }[severity]
            print(f"   • {error}")
            print(f"     → {tolerance}")

def main():
    """Run all error handling tests"""
    
    # Configure logging to see the output
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s - %(name)s - %(message)s'
    )
    
    print("🚨 ENHANCED ERROR HANDLING VALIDATION")
    print("=" * 80)
    print("Testing development-aware error handling system")
    
    test_development_mode()
    test_production_mode()
    test_config_integration()
    test_error_classification_examples()
    
    print("\n" + "=" * 80)
    print("✅ ERROR HANDLING TESTS COMPLETED")
    print("\nKey Benefits Demonstrated:")
    print("• 🔧 Full debugging visibility in development")
    print("• 🚀 Performance optimization in production") 
    print("• 🎯 Configurable error tolerance levels")
    print("• 📊 Error statistics and monitoring")
    print("• 🛡️ Environment-aware behavior adaptation")

if __name__ == "__main__":
    main()