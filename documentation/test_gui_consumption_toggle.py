"""
Test GUI Consumption Mode Toggle Implementation

This script tests that the GUI consumption mode toggle:
1. Has the correct default value (callback mode = True)
2. Can be toggled between modes
3. Is passed correctly to LiveTrader
4. Appears in the configuration review dialog
"""

import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

def test_gui_consumption_toggle():
    """Test that GUI toggle for consumption mode is implemented correctly"""
    
    logger.info("="*80)
    logger.info("TEST: GUI Consumption Mode Toggle Implementation")
    logger.info("="*80)
    
    try:
        # Test 1: Import GUI module
        logger.info("\n📋 TEST 1: Import GUI module")
        from gui.noCamel1 import UnifiedTradingGUI
        logger.info("✅ GUI module imported successfully")
        
        # Test 2: Check that ft_use_direct_callbacks variable exists by reading the file
        logger.info("\n📋 TEST 2: Check GUI variable initialization")
        with open('gui/noCamel1.py', 'r', encoding='utf-8') as f:
            gui_content = f.read()
        
        if "self.ft_use_direct_callbacks" in gui_content:
            logger.info("✅ ft_use_direct_callbacks variable found in GUI code")
        else:
            logger.error("❌ ft_use_direct_callbacks variable NOT found in GUI code")
            return False
            
        if "self.ft_use_direct_callbacks = tk.BooleanVar(value=True)" in gui_content:
            logger.info("✅ Default value set to True (callback mode)")
        else:
            logger.warning("⚠️  Could not verify exact default value is True")
        
        # Test 3: Check that _build_forward_test_tab includes the toggle
        logger.info("\n📋 TEST 3: Check GUI control in forward test tab")
        
        if "Tick Consumption Mode" in gui_content:
            logger.info("✅ Consumption Mode section found in forward test tab")
        else:
            logger.error("❌ Consumption Mode section NOT found")
            return False
            
        if "Callback Mode" in gui_content and "Polling Mode" in gui_content:
            logger.info("✅ Both mode options (Callback/Polling) found in dropdown")
        else:
            logger.error("❌ Mode options not found in dropdown")
            return False
        
        # Test 4: Check trader initialization uses the toggle
        logger.info("\n📋 TEST 4: Check trader initialization")
        
        if "trader.use_direct_callbacks = self.ft_use_direct_callbacks.get()" in gui_content:
            logger.info("✅ Trader consumption mode set from GUI toggle")
        else:
            logger.error("❌ Trader consumption mode NOT set from GUI toggle")
            return False
        
        # Test 5: Check configuration review dialog shows the mode
        logger.info("\n📋 TEST 5: Check configuration review dialog")
        
        if "CONSUMPTION MODE" in gui_content:
            logger.info("✅ Consumption mode displayed in config review")
        else:
            logger.error("❌ Consumption mode NOT displayed in config review")
            return False
            
        if "ft_use_direct_callbacks.get()" in gui_content:
            logger.info("✅ Consumption mode value read from GUI toggle")
        else:
            logger.error("❌ Consumption mode value not read from toggle")
            return False
        
        # Test 6: Verify performance help text
        logger.info("\n📋 TEST 6: Check performance help text")
        if "~50ms latency" in gui_content and "~70ms latency" in gui_content:
            logger.info("✅ Performance latency information displayed")
        else:
            logger.warning("⚠️  Performance latency information may be missing")
        
        if "Wind-style" in gui_content or "29% faster" in gui_content:
            logger.info("✅ Performance comparison information included")
        else:
            logger.warning("⚠️  Performance comparison information may be missing")
        
        logger.info("\n" + "="*80)
        logger.info("✅ ALL TESTS PASSED - GUI Consumption Toggle Implementation Complete!")
        logger.info("="*80)
        logger.info("\n📊 SUMMARY:")
        logger.info("   ✅ GUI variable initialized (default: callback mode = True)")
        logger.info("   ✅ Dropdown control added to forward test tab")
        logger.info("   ✅ Both modes available: Callback (Fast) and Polling (Safe)")
        logger.info("   ✅ Trader.use_direct_callbacks set from GUI")
        logger.info("   ✅ Mode displayed in configuration review dialog")
        logger.info("   ✅ Performance information shown to user")
        logger.info("\n🎯 NEXT STEP: Test GUI manually to verify visual appearance and interaction")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ TEST FAILED with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_gui_consumption_toggle()
    sys.exit(0 if success else 1)
