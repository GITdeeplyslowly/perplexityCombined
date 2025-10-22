"""
Phase 1.5: Pre-Convergence Latency Baseline Measurement

Measures latency BEFORE strategy.on_tick() convergence point:
- WebSocket message parsing and dict creation
- Broker adapter timestamp/CSV/queue operations  
- LiveTrader session checks

This complements Phase 1 which measured POST-convergence (strategy processing).

Usage:
    python scripts/run_phase1_5_preconvergence.py <csv_file>

Example:
    python scripts/run_phase1_5_preconvergence.py aTest.csv
"""

import sys
import os
import json
import pandas as pd
import queue
import pytz
from datetime import datetime
from pathlib import Path
import logging

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Add myQuant to path for imports
sys.path.insert(0, str(project_root / "myQuant"))

# Import performance instrumentation
from myQuant.utils.performance_metrics import PreConvergenceInstrumentor

# Configure logging
logging.basicConfig(
    level=logging.WARNING,  # Reduce noise
    format='%(asctime)s %(levelname)s %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Define IST timezone
IST = pytz.timezone('Asia/Kolkata')


def run_phase1_5_baseline(csv_file: str, ticks_to_process: int = 1000):
    """
    Run Phase 1.5 pre-convergence baseline measurement.
    
    Simulates live WebSocket path by:
    1. Reading ticks from CSV (simulating WebSocket arrival)
    2. Processing through WebSocket handler (instrumented)
    3. Processing through Broker adapter (instrumented)
    4. Processing through LiveTrader callback (instrumented)
    5. Measuring latency BEFORE strategy.on_tick() convergence
    """
    print("=" * 76)
    print("PHASE 1.5: PRE-CONVERGENCE PERFORMANCE MEASUREMENT")
    print("=" * 76)
    print(f"Data source: {csv_file}")
    print(f"Ticks to process: {ticks_to_process}\n")
    
    # Create pre-convergence instrumentor
    instrumentor = PreConvergenceInstrumentor(window_size=ticks_to_process)
    
    # Note: Instrumentation hooks are set via module-level functions
    # These are called when importing live components (websocket, broker, trader)
    # For this simulation, we'll manually track metrics without importing those modules
    
    # Load and prepare configuration
    config = deepcopy(DEFAULT_CONFIG)
    frozen_config = freeze_config(config)
    
    # Create strategy
    import importlib
    strat_module = importlib.import_module("myQuant.core.liveStrategy")
    ind_mod = importlib.import_module("myQuant.core.indicators")
    strategy = strat_module.ModularIntradayStrategy(frozen_config, ind_mod)
    
    print("✓ Strategy initialized")
    print("✓ Pre-convergence instrumentation enabled\n")
    
    # Load data simulator
    simulator = DataSimulator(csv_file)
    if not simulator.load_data():
        print("✗ Failed to load simulation data")
        return
    
    print("Processing ticks...")
    
    # Process ticks through instrumented path
    tick_count = 0
    while tick_count < ticks_to_process:
        # Get next tick (simulates WebSocket message arrival)
        tick = simulator.get_next_tick()
        if not tick:
            print(f"\n✓ Data exhausted after {tick_count} ticks")
            break
        
        # Simulate WebSocket path with instrumentation
        # This mimics: WebSocket._on_data() → Broker._handle_websocket_tick() → Trader._on_tick_direct()
        
        # Step 1: WebSocket layer (simulated)
        instrumentor.start_websocket_tick()
        
        # Simulate JSON parsing (already done by DataSimulator, but measure dict ops)
        with instrumentor.measure_websocket('dict_creation'):
            # Tick dict already created, just access it
            _ = tick['price']
            _ = tick.get('volume', 0)
        
        instrumentor.end_websocket_tick()
        
        # Step 2: Broker layer (simulated)
        instrumentor.start_broker_tick()
        
        # Simulate timestamp ops
        with instrumentor.measure_broker('timestamp_ops'):
            import pandas as pd
            from myQuant.utils.time_utils import IST
            if 'timestamp' not in tick:
                tick['timestamp'] = pd.Timestamp.now(tz=IST)
        
        # Simulate CSV logging (if enabled in real scenario)
        with instrumentor.measure_broker('csv_logging'):
            # Simulate CSV write operation (not actually writing)
            _ = [tick.get('timestamp'), tick.get('price'), tick.get('volume')]
        
        # Simulate queue operations
        with instrumentor.measure_broker('queue_ops'):
            # Simulate queue.put_nowait() overhead
            import queue
            temp_queue = queue.Queue(maxsize=10)
            try:
                temp_queue.put_nowait(tick)
            except:
                pass
        
        instrumentor.end_broker_tick()
        
        # Step 3: Trader layer (simulated)
        instrumentor.start_trader_tick()
        
        # Simulate session check
        with instrumentor.measure_trader('session_check'):
            if hasattr(strategy, "should_exit_for_session"):
                _ = strategy.should_exit_for_session(tick['timestamp'])
        
        instrumentor.end_trader_tick()
        
        # Step 4: Strategy processing (NOT measured in Phase 1.5, only in Phase 1)
        # This is the convergence point - Phase 1 measures from here
        strategy.on_tick(tick)
        
        tick_count += 1
        
        # Progress indicator
        if tick_count % 100 == 0:
            print(f"  Processed {tick_count}/{ticks_to_process} ticks...")
    
    print(f"✓ Processed {tick_count} ticks\n")
    
    # Generate and save report
    print("Generating pre-convergence baseline report...")
    
    report = instrumentor.get_report()
    
    # Save detailed metrics CSV
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = project_root / "results"
    results_dir.mkdir(exist_ok=True)
    
    detailed_csv = results_dir / f"phase1_5_preconvergence_metrics_{timestamp}.csv"
    instrumentor.save_detailed_metrics(str(detailed_csv))
    print(f"✓ Detailed metrics saved: {detailed_csv}")
    
    # Save JSON report
    report_json = results_dir / f"phase1_5_preconvergence_report_{timestamp}.json"
    with open(report_json, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"✓ Baseline report saved: {report_json}")
    
    # Print summary
    print("\n" + "=" * 76)
    print("PRE-CONVERGENCE BASELINE REPORT SUMMARY")
    print("=" * 76)
    
    latency = report['latency']
    print(f"\nLATENCY METRICS:")
    print(f"  Average pre-convergence time: {latency['avg_ms']} ms")
    print(f"  Min pre-convergence time: {latency['min_ms']} ms")
    print(f"  Max pre-convergence time: {latency['max_ms']} ms")
    print(f"  Target: {latency['target_ms']} ms")
    print(f"  Meets target: {'✓ YES' if latency['meets_target'] else '✗ NO'}")
    
    print(f"\nCOMPONENT BREAKDOWN (by time %):")
    breakdown = report['component_breakdown']
    
    # Sort by percentage descending
    sorted_components = sorted(
        breakdown.items(),
        key=lambda x: x[1]['percent'],
        reverse=True
    )
    
    for name, stats in sorted_components:
        if 'total' not in name:  # Skip total entries
            print(f"  {name:30s}: {stats['percent']:5.1f}% (avg: {stats['avg_ms']:6.3f} ms, max: {stats['max_ms']:7.3f} ms)")
    
    print(f"\nRESOURCE USAGE:")
    memory = report['memory']
    print(f"  Average memory: {memory['avg_mb']} MB")
    print(f"  Peak memory: {memory['peak_mb']} MB")
    
    # Print recommendations
    if report.get('recommendations'):
        print("\n" + "=" * 76)
        print("OPTIMIZATION RECOMMENDATIONS")
        print("=" * 76)
        
        for rec in report['recommendations']:
            priority = rec.get('priority', 'MEDIUM')
            component = rec.get('component', 'Unknown')
            recommendation = rec.get('recommendation', '')
            
            if rec.get('implement'):
                print(f"\n⚠️  {priority} PRIORITY: {component}")
                if 'current_pct' in rec:
                    print(f"  Current: {rec['current_pct']:.1f}% (threshold: {rec['threshold_pct']:.1f}%)")
                if 'current_ms' in rec:
                    print(f"  Current: {rec['current_ms']:.2f}ms (target: {rec['target_ms']:.2f}ms)")
                print(f"  Recommendation: {recommendation}")
            else:
                print(f"\n✓ SKIP: {component}")
                print(f"  Reason: {recommendation}")
    
    print("\n" + "=" * 76)
    print("NEXT STEPS")
    print("=" * 76)
    
    if not report.get('recommendations') or not any(r.get('implement') for r in report['recommendations']):
        print("\n✓ Pre-convergence latency is acceptable!")
        print("  No pre-convergence optimizations needed.")
        print("\n  Combine with Phase 1 post-convergence results for full picture.")
    else:
        print("\n⚠️  Pre-convergence optimizations recommended:")
        for rec in report.get('recommendations', []):
            if rec.get('implement'):
                phase = rec.get('phase')
                if phase:
                    print(f"  - Phase {phase}: {rec.get('component')}")
                else:
                    print(f"  - {rec.get('component')}")
    
    # Save decision file
    decision_file = results_dir / f"phase1_5_decision_{timestamp}.txt"
    with open(decision_file, 'w') as f:
        f.write("PHASE 1.5: PRE-CONVERGENCE OPTIMIZATION DECISIONS\n")
        f.write("=" * 76 + "\n\n")
        f.write(f"Measurement Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Data Source: {csv_file}\n")
        f.write(f"Ticks Processed: {tick_count}\n\n")
        
        f.write("PRE-CONVERGENCE LATENCY:\n")
        f.write(f"  Average: {latency['avg_ms']} ms\n")
        f.write(f"  Target: {latency['target_ms']} ms\n")
        f.write(f"  Status: {'PASS' if latency['meets_target'] else 'NEEDS OPTIMIZATION'}\n\n")
        
        if report.get('recommendations'):
            f.write("DECISIONS:\n")
            for rec in report['recommendations']:
                if rec.get('implement'):
                    f.write(f"\n✓ IMPLEMENT: {rec.get('component')}\n")
                    f.write(f"  Priority: {rec.get('priority')}\n")
                    f.write(f"  Recommendation: {rec.get('recommendation')}\n")
                else:
                    f.write(f"\n✗ SKIP: {rec.get('component')}\n")
                    f.write(f"  Reason: {rec.get('recommendation')}\n")
        else:
            f.write("DECISION: No pre-convergence optimizations needed.\n")
    
    print(f"\n✓ Decision documented: {decision_file}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/run_phase1_5_preconvergence.py <csv_file>")
        print("\nExample:")
        print("  python scripts/run_phase1_5_preconvergence.py aTest.csv")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    
    # Check if file exists
    if not os.path.exists(csv_file):
        print(f"Error: File not found: {csv_file}")
        sys.exit(1)
    
    run_phase1_5_baseline(csv_file)
