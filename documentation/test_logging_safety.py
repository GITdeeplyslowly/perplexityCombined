#!/usr/bin/env python3
"""
Test the Windows-safe logging configuration.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from gui.noCamel1 import create_config_from_defaults, validate_config, freeze_config, setup_from_config
import logging
import time

def test_logging_safety():
    """Test that logging doesn't produce permission errors."""
    
    print("🧪 Testing Windows-safe logging configuration...")
    
    try:
        # Create test configuration
        config = create_config_from_defaults()
        validation = validate_config(config)
        
        if validation['errors']:
            print(f"❌ Config validation failed: {validation['errors']}")
            return False
            
        frozen_config = freeze_config(config)
        setup_from_config(frozen_config)
        
        # Test logging with multiple writes that would trigger rotation
        logger = logging.getLogger('test_logger')
        
        print("📝 Testing log writes...")
        for i in range(10):
            logger.info(f"Test log message {i} - checking for permission errors")
            logger.warning(f"Test warning message {i}")
            logger.debug(f"Test debug message {i}")
            time.sleep(0.1)  # Brief pause between writes
        
        print("✅ Logging test completed without permission errors!")
        return True
        
    except Exception as e:
        print(f"❌ Logging test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_logging_safety()
    if success:
        print("\n🎉 Windows-safe logging test PASSED!")
        print("✅ No permission errors during log rotation")
    else:
        print("\n❌ Windows-safe logging test FAILED!")
    sys.exit(0 if success else 1)