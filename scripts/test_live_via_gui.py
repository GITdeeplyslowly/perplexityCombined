"""
test_live_via_gui.py - Live Performance Test via GUI Workflow

This script enables performance testing by using the GUI's actual workflow
instead of creating parallel authentication/configuration paths.

Usage:
    python scripts/test_live_via_gui.py --ticks 1000

The script will:
1. Enable performance testing mode
2. Launch the GUI with pre-configured settings
3. Automatically trigger forward test via GUI workflow
4. Collect performance metrics
5. Generate reports when target tick count is reached
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
from myQuant.utils.performance_test_hook import enable_performance_testing

logger = logging.getLogger(__name__)


def main():
    """Main entry point for GUI-based performance testing"""
    parser = argparse.ArgumentParser(description="Live performance test via GUI workflow")
    parser.add_argument('--ticks', type=int, default=1000, help='Number of ticks to collect (default: 1000)')
    parser.add_argument('--no-pre', action='store_true', help='Disable pre-convergence instrumentation')
    parser.add_argument('--no-post', action='store_true', help='Disable post-convergence instrumentation')
    parser.add_argument('--no-auto-stop', action='store_true', help='Do not auto-stop after target ticks')
    
    args = parser.parse_args()
    
    print("="*80)
    print("🔬 LIVE PERFORMANCE TEST - GUI WORKFLOW MODE")
    print("="*80)
    print(f"Target Ticks: {args.ticks}")
    print(f"Pre-Convergence: {'Disabled' if args.no_pre else 'Enabled'}")
    print(f"Post-Convergence: {'Disabled' if args.no_post else 'Enabled'}")
    print(f"Report Generation: {'At target only' if args.no_auto_stop else 'Auto-stop after report'}")
    print("="*80 + "\n")
    
    # Enable performance testing BEFORE launching GUI
    print("⚙️  Enabling performance testing mode...")
    hook = enable_performance_testing(
        target_ticks=args.ticks,
        enable_pre=not args.no_pre,
        enable_post=not args.no_post,
        auto_stop=not args.no_auto_stop
    )
    print(f"✓ Performance testing enabled - hook will inject into GUI workflow\n")
    
    # Now launch the GUI - it will use its normal workflow
    print("🚀 Launching GUI with performance testing enabled...")
    print("📋 INSTRUCTIONS:")
    print("   1. Configure your strategy parameters in the GUI")
    print("   2. Enter your credentials (or they'll be loaded from defaults)")
    print("   3. Click 'Start Forward Test' button")
    print("   4. Performance hook will automatically:")
    print("      - Inject instrumentation into the trader")
    print("      - Monitor tick progress")
    print(f"      - Generate performance report at {args.ticks} ticks")
    print("      - ⚠️  Stream continues running (robustness priority)")
    print("      - To stop: Click 'Stop' and confirm dialog")
    print("\n" + "="*80 + "\n")
    
    # Import and launch GUI
    try:
        from myQuant.gui.noCamel1 import UnifiedTradingGUI
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
