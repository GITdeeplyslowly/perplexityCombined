"""
Phase 1: Baseline Performance Measurement Runner
Run this script to collect baseline metrics and generate recommendations.
"""
import sys
import os
from pathlib import Path
import json
from datetime import datetime
from copy import deepcopy

# Add project root and myQuant to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "myQuant"))

from core.liveStrategy import ModularIntradayStrategy
from live.data_simulator import DataSimulator
from config.defaults import DEFAULT_CONFIG
from utils.config_helper import validate_config, freeze_config
import core.indicators as indicators_module


def run_baseline_measurement(csv_file: str, num_ticks: int = 1000):
    """
    Run baseline measurement on historical data.
    
    Args:
        csv_file: Path to CSV file with tick data
        num_ticks: Number of ticks to process (default 1000)
    """
    print("=" * 80)
    print("PHASE 1: BASELINE PERFORMANCE MEASUREMENT")
    print("=" * 80)
    print(f"Data source: {csv_file}")
    print(f"Ticks to process: {num_ticks}")
    print()
    
    # Create and validate config
    config = deepcopy(DEFAULT_CONFIG)
    
    # Enable instrumentation for Phase 1
    if 'performance' not in config:
        config['performance'] = {}
    config['performance']['instrumentation_enabled'] = True
    
    validation = validate_config(config)
    
    if not validation.get('valid', False):
        print("ERROR: Invalid configuration")
        for error in validation.get('errors', []):
            print(f"  - {error}")
        return
    
    frozen_config = freeze_config(config)
    
    # Create strategy with instrumentation
    strategy = ModularIntradayStrategy(frozen_config, indicators_module)
    strategy.instrumentation_enabled = True  # Enable instrumentation
    print(f"✓ Strategy initialized with instrumentation enabled")
    print(f"  Window size: {strategy.instrumentor.window_size} ticks")
    print()
    
    # Simulate data
    print("Processing ticks...")
    simulator = DataSimulator(csv_file)
    simulator.load_data()
    
    tick_count = 0
    while tick_count < num_ticks:
        tick = simulator.get_next_tick()
        if tick is None:
            print(f"  Reached end of data at {tick_count} ticks")
            break
            
        strategy.on_tick(tick)
        tick_count += 1
        
        if tick_count % 100 == 0:
            print(f"  Processed {tick_count}/{num_ticks} ticks...")
    
    print(f"✓ Processed {tick_count} ticks")
    print()
    
    # Generate baseline report
    print("Generating baseline report...")
    report = strategy.instrumentor.get_baseline_report()
    
    # Create results directory
    results_dir = project_root / "results"
    results_dir.mkdir(exist_ok=True)
    
    # Save detailed metrics
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    metrics_file = results_dir / f"phase1_detailed_metrics_{timestamp}.csv"
    report_file = results_dir / f"phase1_baseline_report_{timestamp}.json"
    
    strategy.instrumentor.save_detailed_metrics(str(metrics_file))
    
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"✓ Detailed metrics saved: {metrics_file}")
    print(f"✓ Baseline report saved: {report_file}")
    print()
    
    # Display results
    print("=" * 80)
    print("BASELINE REPORT SUMMARY")
    print("=" * 80)
    print()
    
    # Latency
    latency = report['latency_summary']
    print("LATENCY METRICS:")
    print(f"  Average tick time: {latency['avg_tick_ms']:.3f} ms")
    print(f"  Min tick time: {latency['min_tick_ms']:.3f} ms")
    print(f"  Max tick time: {latency['max_tick_ms']:.3f} ms")
    print(f"  Target: {latency['target_ms']:.1f} ms")
    print(f"  Meets target: {'✓ YES' if latency['meets_target'] else '✗ NO'}")
    print()
    
    # Throughput
    throughput = report['throughput']
    print("THROUGHPUT METRICS:")
    print(f"  Ticks per second: {throughput['avg_ticks_per_second']:.1f}")
    print(f"  Target: {throughput['target_tps']}")
    print(f"  Meets target: {'✓ YES' if throughput['meets_target'] else '✗ NO'}")
    print()
    
    # Component breakdown
    print("COMPONENT BREAKDOWN (by time %):")
    breakdown = report['component_breakdown']
    for name, stats in sorted(breakdown.items(), key=lambda x: x[1]['percent_of_total'], reverse=True):
        print(f"  {name:20s}: {stats['percent_of_total']:5.1f}% "
              f"(avg: {stats['avg_time_ms']:6.3f} ms, "
              f"max: {stats['max_time_ms']:6.3f} ms)")
    print()
    
    # Resources
    resources = report['resource_usage']
    print("RESOURCE USAGE:")
    print(f"  Average memory: {resources['avg_memory_mb']:.2f} MB")
    print(f"  Peak memory: {resources['max_memory_mb']:.2f} MB")
    print()
    
    # Recommendations
    print("=" * 80)
    print("OPTIMIZATION RECOMMENDATIONS (CONDITIONAL PHASES)")
    print("=" * 80)
    print()
    
    implement_phases = []
    skip_phases = []
    
    for rec in report['recommendations']:
        if rec['implement']:
            implement_phases.append(rec)
            print(f"✓ IMPLEMENT Phase {rec['phase']}: {rec['name']}")
            print(f"  Priority: {rec['priority']}")
            print(f"  Reason: {rec['reason']}")
            print()
        else:
            skip_phases.append(rec)
            print(f"✗ SKIP Phase {rec['phase']}: {rec['name']}")
            print(f"  Reason: {rec['reason']}")
            print()
    
    # Summary
    print("=" * 80)
    print("NEXT STEPS")
    print("=" * 80)
    print()
    
    if implement_phases:
        print(f"Implement {len(implement_phases)} conditional phase(s):")
        for rec in implement_phases:
            print(f"  - Phase {rec['phase']}: {rec['name']}")
    else:
        print("✓ No conditional optimizations needed!")
        print("  System performance is within acceptable thresholds.")
    
    print()
    print("After conditional phases (if any), proceed to:")
    print("  - Phase 6: System Monitoring & Alerting")
    print("  - Phase 7: Production Hardening")
    print()
    
    # Save decision file
    decision_file = results_dir / f"phase1_decision_{timestamp}.txt"
    with open(decision_file, 'w') as f:
        f.write(f"Phase 1 Baseline Results: {timestamp}\n\n")
        f.write("Measurements:\n")
        for name, stats in sorted(breakdown.items(), key=lambda x: x[1]['percent_of_total'], reverse=True):
            f.write(f"- {name}: {stats['percent_of_total']:.1f}% of time\n")
        f.write("\nRecommendations:\n")
        for rec in report['recommendations']:
            action = "IMPLEMENT" if rec['implement'] else "SKIP"
            f.write(f"{action} Phase {rec['phase']}: {rec['name']}\n")
            f.write(f"  {rec['reason']}\n")
    
    print(f"✓ Decision documented: {decision_file}")
    print()


if __name__ == '__main__':
    # Example usage - UPDATE THIS PATH
    csv_file = project_root / "path/to/your/tick_data.csv"
    
    # Check if user provided CSV path as argument
    if len(sys.argv) > 1:
        csv_file = Path(sys.argv[1])
    
    if not csv_file.exists():
        print(f"ERROR: CSV file not found: {csv_file}")
        print()
        print("Usage: python run_phase1_baseline.py [path/to/tick_data.csv]")
        print("Update the csv_file path in the script or provide as argument.")
        sys.exit(1)
    
    run_baseline_measurement(str(csv_file), num_ticks=1000)
