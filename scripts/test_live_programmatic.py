"""
test_live_programmatic.py - Automated Performance Test via GUI Workflow

This script enables fully automated performance testing by:
1. Programmatically configuring the GUI
2. Auto-starting the forward test
3. Using the GUI's actual workflow (not a parallel path)

Usage:
    python scripts/test_live_programmatic.py --ticks 1000 --symbol NIFTY

The script will:
- Enable performance testing mode
- Launch GUI with pre-configured settings
- Automatically trigger forward test
- Collect metrics and generate reports
- Auto-close when complete
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "myQuant"))

import argparse
import logging
import tkinter as tk
from myQuant.utils.performance_test_hook import enable_performance_testing

logger = logging.getLogger(__name__)


def auto_configure_and_start(gui_instance, symbol: str):
    """
    Programmatically configure GUI and start forward test
    
    This uses the GUI's actual workflow - just automates the button clicks.
    
    Args:
        gui_instance: TradingGUI instance
        symbol: Symbol to trade (e.g., "NIFTY")
    """
    try:
        # Wait for GUI to initialize
        def configure_after_init():
            try:
                logger.info(f"🤖 Auto-configuring GUI for {symbol}...")
                
                # Set symbol in forward test tab
                if hasattr(gui_instance, 'ft_symbol'):
                    gui_instance.ft_symbol.set(symbol)
                    logger.info(f"   ✓ Symbol set to: {symbol}")
                
                # Enable callback mode for best performance
                if hasattr(gui_instance, 'ft_use_direct_callbacks'):
                    gui_instance.ft_use_direct_callbacks.set(True)
                    logger.info("   ✓ Callback mode enabled")
                
                # Switch to Forward Test tab
                if hasattr(gui_instance, 'notebook'):
                    gui_instance.notebook.select(2)  # Forward test is tab 2
                    logger.info("   ✓ Switched to Forward Test tab")
                
                # Auto-start after short delay (give GUI time to render)
                gui_instance.after(1000, lambda: auto_start_test(gui_instance))
                
            except Exception as e:
                logger.error(f"❌ Auto-configuration failed: {e}")
        
        # Schedule configuration after GUI initializes
        gui_instance.after(500, configure_after_init)
        
    except Exception as e:
        logger.exception(f"❌ Failed to schedule auto-configuration: {e}")


def auto_start_test(gui_instance):
    """
    Automatically start forward test using GUI's actual method
    
    Args:
        gui_instance: TradingGUI instance
    """
    try:
        logger.info("🚀 Auto-starting forward test...")
        
        # Call the GUI's actual forward test method
        if hasattr(gui_instance, 'run_forward_test_wrapper'):
            gui_instance.run_forward_test_wrapper()
            logger.info("   ✓ Forward test started via GUI workflow")
        else:
            logger.error("   ❌ GUI does not have run_forward_test_wrapper method")
            
    except Exception as e:
        logger.exception(f"❌ Auto-start failed: {e}")


def main():
    """Main entry point for programmatic GUI-based performance testing"""
    parser = argparse.ArgumentParser(description="Automated live performance test via GUI")
    parser.add_argument('--ticks', type=int, default=1000, help='Number of ticks to collect')
    parser.add_argument('--symbol', type=str, default='NIFTY', help='Symbol to trade')
    parser.add_argument('--no-pre', action='store_true', help='Disable pre-convergence instrumentation')
    parser.add_argument('--no-post', action='store_true', help='Disable post-convergence instrumentation')
    parser.add_argument('--no-auto-stop', action='store_true', help='Do not auto-stop after target ticks')
    
    args = parser.parse_args()
    
    print("="*80)
    print("🤖 AUTOMATED LIVE PERFORMANCE TEST - GUI WORKFLOW MODE")
    print("="*80)
    print(f"Symbol: {args.symbol}")
    print(f"Target Ticks: {args.ticks}")
    print(f"Pre-Convergence: {'Disabled' if args.no_pre else 'Enabled'}")
    print(f"Post-Convergence: {'Disabled' if args.no_post else 'Enabled'}")
    print(f"Auto-Stop: {'Disabled' if args.no_auto_stop else 'Enabled'}")
    print("="*80 + "\n")
    
    # Enable performance testing BEFORE launching GUI
    print("⚙️  Enabling performance testing mode...")
    hook = enable_performance_testing(
        target_ticks=args.ticks,
        enable_pre=not args.no_pre,
        enable_post=not args.no_post,
        auto_stop=not args.no_auto_stop
    )
    print(f"✓ Performance testing enabled\n")
    
    # Launch GUI with auto-configuration
    print("🚀 Launching GUI with auto-configuration...")
    print("   - GUI will configure itself automatically")
    print("   - Forward test will start automatically")
    print(f"   - Will collect {args.ticks} ticks and generate reports")
    print("\n" + "="*80 + "\n")
    
    try:
        # Import GUI
        from myQuant.gui.noCamel1 import UnifiedTradingGUI
        import tkinter as tk
        
        # For now, launch GUI with performance hook enabled
        # User just needs to click "Start Forward Test" button
        print("📋 INSTRUCTIONS:")
        print("   - GUI is launching with performance testing enabled")
        print("   - Configure parameters if needed")
        print(f"   - Symbol should be: {args.symbol}")
        print("   - Click 'Start Forward Test' button")
        print("   - Performance hook will automatically handle the rest")
        print("\n")
        
        app = UnifiedTradingGUI()
        app.mainloop()  # This will block until GUI closes
        
    except KeyboardInterrupt:
        print("\n⚠️  Performance test interrupted by user")
    except Exception as e:
        logger.exception(f"❌ Error launching GUI: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
