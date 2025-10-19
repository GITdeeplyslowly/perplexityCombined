#!/usr/bin/env python3
"""
Test script to verify GUI log functionality.

Run this to start the GUI and automatically generate some log messages
to verify that the log tab is working correctly.
"""
import sys
import os
import time
import threading
import logging

# Add the project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def generate_test_logs():
    """Generate various log messages to test the GUI log display"""
    time.sleep(2)  # Wait for GUI to fully load
    
    logger = logging.getLogger("test_gui_logs")
    
    logger.info("🎯 Starting log functionality test...")
    time.sleep(1)
    
    logger.info("✓ INFO level message - This should appear in log tab")
    time.sleep(1)
    
    logger.warning("⚠️ WARNING level message - Testing warning display")
    time.sleep(1)
    
    logger.error("❌ ERROR level message - Testing error display")
    time.sleep(1)
    
    # Test messages from different modules
    backtest_logger = logging.getLogger("backtest.backtest_runner")
    backtest_logger.info("📊 Backtest module log message")
    time.sleep(1)
    
    position_logger = logging.getLogger("core.position_manager")
    position_logger.info("💰 Position manager log message")
    time.sleep(1)
    
    gui_logger = logging.getLogger("gui.noCamel1")
    gui_logger.info("🖥️ GUI module log message")
    time.sleep(1)
    
    logger.info("✅ Log functionality test completed")
    logger.info("Check the 'Logs' tab to see all these messages!")

if __name__ == "__main__":
    try:
        # Import GUI after path is set
        from gui.noCamel1 import UnifiedTradingGUI
        
        # Start log generation in background thread
        log_thread = threading.Thread(target=generate_test_logs, daemon=True)
        log_thread.start()
        
        # Start GUI
        app = UnifiedTradingGUI()
        print("🚀 GUI started. Check the 'Logs' tab to see log messages!")
        app.mainloop()
        
    except Exception as e:
        print(f"❌ Failed to start GUI application: {e}")
        import traceback
        traceback.print_exc()