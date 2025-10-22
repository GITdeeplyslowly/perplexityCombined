"""
Live WebSocket Performance Test with Instrumentation

Measures actual live WebSocket latency including:
- Pre-convergence: WebSocket → Broker → Trader (Phase 1.5)
- Post-convergence: Strategy processing (Phase 1)

Uses existing authentication workflow:
- load_live_trading_credentials() from config.defaults
- BrokerAdapter handles session management internally
- LiveTrader orchestrates tick processing

Usage:
    python scripts/test_live_performance.py [--ticks 1000] [--symbol NIFTY]

Example:
    python scripts/test_live_performance.py --ticks 1000
"""

import sys
import os
import argparse
import json
import time
from pathlib import Path
from datetime import datetime
from copy import deepcopy

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import instrumentation
from myQuant.utils.performance_metrics import PreConvergenceInstrumentor, PerformanceInstrumentor

# Import live trading components
from myQuant.live import websocket_stream, broker_adapter, trader
from myQuant.config.defaults import DEFAULT_CONFIG, load_live_trading_credentials
from myQuant.utils.config_helper import freeze_config

import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


def test_live_performance(ticks_to_process: int = 1000, symbol: str = "NIFTY"):
    """
    Run live WebSocket performance test with full instrumentation.
    
    Uses existing credential workflow:
    1. load_live_trading_credentials() loads from .env.trading or environment
    2. Credentials added to config
    3. BrokerAdapter/LiveTrader handle session management internally
    """
    print("=" * 76)
    print("LIVE WEBSOCKET PERFORMANCE TEST")
    print("=" * 76)
    print(f"Target ticks: {ticks_to_process}")
    print(f"Symbol: {symbol}")
    print(f"Mode: Paper Trading (no real orders)\n")
    
    # Step 1: Create instrumentors
    pre_instrumentor = PreConvergenceInstrumentor(window_size=ticks_to_process)
    post_instrumentor = PerformanceInstrumentor(window_size=ticks_to_process)
    
    print("✓ Performance instrumentors created")
    
    # Step 2: Enable instrumentation in live components
    websocket_stream.set_pre_convergence_instrumentor(pre_instrumentor)
    broker_adapter.set_pre_convergence_instrumentor(pre_instrumentor)
    trader.set_pre_convergence_instrumentor(pre_instrumentor)
    
    print("✓ Pre-convergence instrumentation enabled")
    
    # Step 3: Load credentials using existing workflow (mirrors GUI pattern)
    print("\nLoading SmartAPI credentials...")
    credentials = load_live_trading_credentials()
    
    if not credentials.get('api_key') or not credentials.get('client_code'):
        print("\n❌ ERROR: Missing credentials!")
        print("   Please provide credentials via:")
        print("   1. .env.trading file at: C:\\Users\\user\\projects\\angelalgo\\.env.trading")
        print("   2. Environment variables: API_KEY, CLIENT_ID, PASSWORD, SMARTAPI_TOTP_SECRET")
        print("   3. Or configure in myQuant/config/defaults.py")
        return
    
    print(f"✓ Credentials loaded: api_key={'✅' if credentials.get('api_key') else '❌'}, "
          f"client_code={'✅' if credentials.get('client_code') else '❌'}")
    
    # Step 4: Prepare configuration (mirrors GUI pattern)
    config = deepcopy(DEFAULT_CONFIG)
    
    # Update live config with credentials
    config['live'].update(credentials)
    
    # Enable paper trading (safety)
    config['live']['paper_trading'] = True
    
    # Configure target symbol
    config['instrument']['symbol'] = symbol
    
    # Enable post-convergence instrumentation
    if 'performance' not in config:
        config['performance'] = {}
    config['performance']['instrumentation_enabled'] = True
    config['performance']['instrumentation_window_size'] = ticks_to_process
    
    frozen_config = freeze_config(config)
    
    print("✓ Configuration prepared (session management delegated to BrokerAdapter)")
    
    # Step 6: Create strategy with post-convergence instrumentation
    import importlib
    strat_module = importlib.import_module("myQuant.core.liveStrategy")
    ind_mod = importlib.import_module("myQuant.core.indicators")
    
    # Create strategy (will use instrumentor internally if enabled)
    strategy = strat_module.ModularIntradayStrategy(frozen_config, ind_mod)
    
    # Inject post-convergence instrumentor
    if hasattr(strategy, 'instrumentor'):
        strategy.instrumentor = post_instrumentor
        print("✓ Post-convergence instrumentation enabled")
    
    print("✓ Strategy initialized")
    
    # Step 7: Create LiveTrader with instrumented components
    print("\nStarting live WebSocket stream...")
    
    live_trader = trader.LiveTrader(frozen_config=frozen_config)
    
    # Enable direct callback mode for best performance
    live_trader.use_direct_callbacks = True
    
    print("✓ LiveTrader initialized")
    print("✓ Direct callback mode enabled\n")
    
    # Step 8: Start live trading and collect ticks
    print("=" * 76)
    print("COLLECTING LIVE TICKS...")
    print("=" * 76)
    print("(This will connect to SmartAPI WebSocket and process real ticks)")
    print("(Press Ctrl+C to stop early)\n")
    
    try:
        # Track tick count
        tick_count = 0
        start_time = time.time()
        
        # Custom callback to count ticks
        def performance_callback(status_msg):
            nonlocal tick_count
            tick_count += 1
            
            if tick_count % 100 == 0:
                elapsed = time.time() - start_time
                rate = tick_count / elapsed if elapsed > 0 else 0
                print(f"  Processed {tick_count}/{ticks_to_process} ticks... ({rate:.1f} ticks/sec)")
            
            # Stop after target ticks
            if tick_count >= ticks_to_process:
                live_trader.stop()
        
        # Start trading (will run until stopped)
        live_trader.run(
            performance_callback=performance_callback,
            run_once=True  # Stop after one session
        )
        
        elapsed = time.time() - start_time
        print(f"\n✓ Collected {tick_count} ticks in {elapsed:.1f} seconds")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        live_trader.stop()
    except Exception as e:
        print(f"\n\n❌ Error during test: {e}")
        logger.exception("Test error:")
        return
    
    # Step 9: Generate reports
    print("\n" + "=" * 76)
    print("GENERATING PERFORMANCE REPORTS...")
    print("=" * 76)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = project_root / "results"
    results_dir.mkdir(exist_ok=True)
    
    # Pre-convergence report (Phase 1.5)
    pre_report = pre_instrumentor.get_report()
    pre_json = results_dir / f"live_preconvergence_report_{timestamp}.json"
    with open(pre_json, 'w') as f:
        json.dump(pre_report, f, indent=2)
    
    pre_csv = results_dir / f"live_preconvergence_metrics_{timestamp}.csv"
    pre_instrumentor.save_detailed_metrics(str(pre_csv))
    
    print(f"✓ Pre-convergence report: {pre_json}")
    print(f"✓ Pre-convergence metrics: {pre_csv}")
    
    # Post-convergence report (Phase 1)
    post_report = post_instrumentor.get_baseline_report()
    post_json = results_dir / f"live_postconvergence_report_{timestamp}.json"
    with open(post_json, 'w') as f:
        json.dump(post_report, f, indent=2)
    
    post_csv = results_dir / f"live_postconvergence_metrics_{timestamp}.csv"
    post_instrumentor.save_detailed_metrics(str(post_csv))
    
    print(f"✓ Post-convergence report: {post_json}")
    print(f"✓ Post-convergence metrics: {post_csv}")
    
    # Combined summary
    print("\n" + "=" * 76)
    print("LIVE PERFORMANCE SUMMARY")
    print("=" * 76)
    
    # Pre-convergence
    pre_latency = pre_report['latency']
    print(f"\nPRE-CONVERGENCE (WebSocket → Broker → Trader):")
    print(f"  Average: {pre_latency['avg_ms']:.3f} ms")
    print(f"  Min: {pre_latency['min_ms']:.3f} ms")
    print(f"  Max: {pre_latency['max_ms']:.3f} ms")
    print(f"  Target: {pre_latency['target_ms']:.1f} ms")
    print(f"  Status: {'✓ PASS' if pre_latency['meets_target'] else '✗ FAIL'}")
    
    # Component breakdown
    print(f"\n  Component Breakdown:")
    pre_breakdown = pre_report['component_breakdown']
    sorted_pre = sorted(pre_breakdown.items(), key=lambda x: x[1]['percent'], reverse=True)
    for name, stats in sorted_pre[:5]:
        if 'total' not in name.lower():
            print(f"    {name:30s}: {stats['percent']:5.1f}% ({stats['avg_ms']:.3f}ms)")
    
    # Post-convergence
    post_latency = post_report['latency']
    print(f"\nPOST-CONVERGENCE (Strategy Processing):")
    print(f"  Average: {post_latency['avg_ms']:.3f} ms")
    print(f"  Min: {post_latency['min_ms']:.3f} ms")
    print(f"  Max: {post_latency['max_ms']:.3f} ms")
    print(f"  Target: {post_latency['target_ms']:.1f} ms")
    print(f"  Status: {'✓ PASS' if post_latency['meets_target'] else '✗ FAIL'}")
    
    print(f"\n  Component Breakdown:")
    post_breakdown = post_report['component_breakdown']
    sorted_post = sorted(post_breakdown.items(), key=lambda x: x[1]['percent'], reverse=True)
    for name, stats in sorted_post[:5]:
        print(f"    {name:30s}: {stats['percent']:5.1f}% ({stats['avg_ms']:.3f}ms)")
    
    # Total latency
    total_avg = pre_latency['avg_ms'] + post_latency['avg_ms']
    total_max = pre_latency['max_ms'] + post_latency['max_ms']
    
    print(f"\nTOTAL END-TO-END LATENCY:")
    print(f"  Average: {total_avg:.3f} ms")
    print(f"  Max: {total_max:.3f} ms")
    print(f"  Target: <5.0 ms")
    print(f"  Status: {'✓ PASS' if total_avg < 5.0 else '✗ FAIL'}")
    
    print(f"\nTHROUGHPUT:")
    throughput = post_report['throughput']['ticks_per_second']
    print(f"  Actual: {throughput:.1f} ticks/sec")
    print(f"  Target: >{post_report['throughput']['target_tps']} ticks/sec")
    print(f"  Status: {'✓ PASS' if post_report['throughput']['meets_target'] else '✗ FAIL'}")
    
    # Save combined summary
    combined_summary = {
        'test_date': datetime.now().isoformat(),
        'ticks_processed': tick_count,
        'symbol': symbol,
        'pre_convergence': pre_report,
        'post_convergence': post_report,
        'total_latency_ms': {
            'avg': total_avg,
            'max': total_max,
            'target': 5.0,
            'meets_target': total_avg < 5.0
        }
    }
    
    combined_json = results_dir / f"live_combined_performance_{timestamp}.json"
    with open(combined_json, 'w') as f:
        json.dump(combined_summary, f, indent=2)
    
    print(f"\n✓ Combined summary: {combined_json}")
    
    print("\n" + "=" * 76)
    print("TEST COMPLETE")
    print("=" * 76)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Live WebSocket Performance Test")
    parser.add_argument('--ticks', type=int, default=1000, help='Number of ticks to collect (default: 1000)')
    parser.add_argument('--symbol', type=str, default='NIFTY', help='Symbol to stream (default: NIFTY)')
    
    args = parser.parse_args()
    
    test_live_performance(ticks_to_process=args.ticks, symbol=args.symbol)
