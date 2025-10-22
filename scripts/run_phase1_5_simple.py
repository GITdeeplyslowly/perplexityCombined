"""
Phase 1.5: Pre-Convergence Latency Baseline - Simplified

Measures simulated pre-convergence latency components:
- JSON parsing (simulated)
- Dict creation
- Timestamp operations  
- CSV write operations
- Queue operations
- Session checks

Outputs:
- JSON report with breakdown
- CSV with per-tick metrics
- Decision recommendations

Usage: python scripts/run_phase1_5_preconvergence.py aTest.csv
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'myQuant'))

import json
import pandas as pd
import queue
import pytz
import time
import csv as csv_module
from datetime import datetime
from pathlib import Path

# Import only the instrumentor
from utils.performance_metrics import PreConvergenceInstrumentor

IST = pytz.timezone('Asia/Kolkata')

def run_phase1_5_baseline(csv_file: str, ticks_to_process: int = 1000):
    """Run Phase 1.5 pre-convergence measurement."""
    print("=" * 76)
    print("PHASE 1.5: PRE-CONVERGENCE LATENCY BASELINE")
    print("=" * 76)
    print(f"Data source: {csv_file}")
    print(f"Ticks to process: {ticks_to_process}\n")
    
    # Create instrumentor
    instrumentor = PreConvergenceInstrumentor(window_size=ticks_to_process)
    print("✓ Pre-convergence instrumentor initialized\n")
    
    # Load CSV
    print(f"Loading data from {csv_file}...")
    data = pd.read_csv(csv_file)
    
    # Standardize columns
    if 'close' in data.columns:
        data['price'] = data['close']
    elif 'Close' in data.columns:
        data['price'] = data['Close']
    if 'volume' not in data.columns:
        data['volume'] = 1000
    
    print(f"✓ Loaded {len(data)} ticks\n")
    print("Processing ticks...")
    
    # Create temp queue and CSV writer for simulation
    temp_queue = queue.Queue(maxsize=1000)
    temp_csv_buffer = []
    
    # Process ticks
    tick_count = 0
    for idx, row in data.iterrows():
        if tick_count >= ticks_to_process:
            break
        
        # === WEBSOCKET LAYER ===
        instrumentor.start_websocket_tick()
        
        # Simulate JSON parsing (data already loaded, but measure dict access)
        with instrumentor.measure_websocket('json_parse'):
            # Simulate JSON.loads() overhead with dict comprehension
            raw_data = {
                'ltp': float(row['price']) * 100,  # Simulate paise format
                'volume': int(row.get('volume', 1000)),
                'tradingsymbol': 'NIFTY',
                'exchange': 'NFO'
            }
        
        # Simulate dict creation
        with instrumentor.measure_websocket('dict_creation'):
            ts = datetime.now(IST)
            actual_price = raw_data['ltp'] / 100.0
            tick = {
                'timestamp': ts,
                'price': actual_price,
                'volume': raw_data['volume'],
                'symbol': raw_data['tradingsymbol'],
                'exchange': raw_data['exchange']
            }
        
        instrumentor.end_websocket_tick()
        
        # === BROKER LAYER ===
        instrumentor.start_broker_tick()
        
        # Timestamp operations
        with instrumentor.measure_broker('timestamp_ops'):
            if 'timestamp' not in tick:
                tick['timestamp'] = pd.Timestamp.now(tz=IST)
            last_price = float(tick.get('price', 0))
            last_tick_time = pd.Timestamp.now(tz=IST)
        
        # CSV logging
        with instrumentor.measure_broker('csv_logging'):
            # Simulate CSV write
            csv_row = [tick['timestamp'], tick['price'], tick['volume'], tick['symbol']]
            temp_csv_buffer.append(csv_row)
        
        # Queue operations
        with instrumentor.measure_broker('queue_ops'):
            try:
                temp_queue.put_nowait(tick)
            except queue.Full:
                try:
                    temp_queue.get_nowait()
                    temp_queue.put_nowait(tick)
                except:
                    pass
        
        instrumentor.end_broker_tick()
        
        # === TRADER LAYER ===
        instrumentor.start_trader_tick()
        
        # Session check
        with instrumentor.measure_trader('session_check'):
            # Simulate session end check
            now = tick['timestamp']
            session_hour = 15
            session_min = 30
            _ = (now.hour == session_hour and now.minute >= session_min)
        
        instrumentor.end_trader_tick()
        
        tick_count += 1
        
        if tick_count % 100 == 0:
            print(f"  Processed {tick_count}/{ticks_to_process} ticks...")
    
    print(f"✓ Processed {tick_count} ticks\n")
    
    # Generate report
    print("Generating pre-convergence report...")
    
    report = instrumentor.get_report()
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = Path(__file__).parent.parent / "results"
    results_dir.mkdir(exist_ok=True)
    
    # Save detailed metrics CSV
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
    print("PRE-CONVERGENCE BASELINE SUMMARY")
    print("=" * 76)
    
    latency = report['latency']
    print(f"\nLATENCY METRICS:")
    print(f"  Average pre-convergence time: {latency['avg_ms']} ms")
    print(f"  Min: {latency['min_ms']} ms")
    print(f"  Max: {latency['max_ms']} ms")
    print(f"  Target: {latency['target_ms']} ms")
    print(f"  Meets target: {'✓ YES' if latency['meets_target'] else '✗ NO'}")
    
    print(f"\nCOMPONENT BREAKDOWN (by time %):")
    breakdown = report['component_breakdown']
    
    # Sort by percentage
    sorted_components = sorted(
        breakdown.items(),
        key=lambda x: x[1]['percent'],
        reverse=True
    )
    
    for name, stats in sorted_components[:15]:  # Top 15
        if 'total' not in name.lower():
            print(f"  {name:30s}: {stats['percent']:5.1f}% (avg: {stats['avg_ms']:6.3f} ms, max: {stats['max_ms']:7.3f} ms)")
    
    print(f"\nRESOURCE USAGE:")
    memory = report['memory']
    print(f"  Average memory: {memory['avg_mb']} MB")
    print(f"  Peak memory: {memory['peak_mb']} MB")
    
    # Recommendations
    if report.get('recommendations'):
        print("\n" + "=" * 76)
        print("OPTIMIZATION RECOMMENDATIONS")
        print("=" * 76)
        
        has_implement = False
        for rec in report['recommendations']:
            if rec.get('implement'):
                has_implement = True
                priority = rec.get('priority', 'MEDIUM')
                component = rec.get('component', 'Unknown')
                recommendation = rec.get('recommendation', '')
                
                print(f"\n⚠️  {priority} PRIORITY: {component}")
                if 'current_pct' in rec and 'threshold_pct' in rec:
                    print(f"  Current: {rec['current_pct']:.1f}% (threshold: {rec['threshold_pct']:.1f}%)")
                elif 'current_pct' in rec:
                    print(f"  Current: {rec['current_pct']:.1f}%")
                if 'current_ms' in rec and 'target_ms' in rec:
                    print(f"  Current: {rec['current_ms']:.2f}ms (target: {rec['target_ms']:.2f}ms)")
                elif 'current_ms' in rec:
                    print(f"  Current: {rec['current_ms']:.2f}ms")
                print(f"  Recommendation: {recommendation}")
        
        if not has_implement:
            print("\n✓ No optimizations needed - all components within thresholds")
    
    print("\n" + "=" * 76)
    print("NEXT STEPS")
    print("=" * 76)
    
    if latency['meets_target']:
        print("\n✓ Pre-convergence latency is acceptable!")
        print("  Total pre-convergence: {:.3f}ms < 1.0ms target".format(latency['avg_ms']))
        print("\n  Combine with Phase 1 post-convergence results for full picture:")
        print("  - Phase 1.5: Pre-convergence latency (this measurement)")
        print("  - Phase 1: Post-convergence strategy processing")
        print("  - Total = Pre-convergence + Post-convergence")
    else:
        print("\n⚠️  Pre-convergence latency exceeds 1ms target")
        print("  Implement recommended optimizations")
    
    # Save decision file
    decision_file = results_dir / f"phase1_5_decision_{timestamp}.txt"
    with open(decision_file, 'w', encoding='utf-8') as f:
        f.write("PHASE 1.5: PRE-CONVERGENCE OPTIMIZATION DECISIONS\n")
        f.write("=" * 76 + "\n\n")
        f.write(f"Measurement Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Data Source: {csv_file}\n")
        f.write(f"Ticks Processed: {tick_count}\n\n")
        
        f.write("PRE-CONVERGENCE LATENCY:\n")
        f.write(f"  Average: {latency['avg_ms']} ms\n")
        f.write(f"  Target: {latency['target_ms']} ms\n")
        f.write(f"  Status: {'PASS' if latency['meets_target'] else 'NEEDS OPTIMIZATION'}\n\n")
        
        f.write("COMPONENT BREAKDOWN:\n")
        for name, stats in sorted_components[:10]:
            if 'total' not in name.lower():
                f.write(f"  {name}: {stats['percent']:.1f}% ({stats['avg_ms']:.3f}ms avg)\n")
        
        f.write("\nDECISIONS:\n")
        if report.get('recommendations'):
            for rec in report['recommendations']:
                if rec.get('implement'):
                    f.write(f"\n✓ IMPLEMENT: {rec.get('component')}\n")
                    f.write(f"  Priority: {rec.get('priority')}\n")
                    f.write(f"  Recommendation: {rec.get('recommendation')}\n")
        else:
            f.write("No optimizations needed - all components within acceptable thresholds.\n")
    
    print(f"\n✓ Decision documented: {decision_file}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/run_phase1_5_preconvergence.py <csv_file>")
        print("\nExample:")
        print("  python scripts/run_phase1_5_preconvergence.py aTest.csv")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    
    if not os.path.exists(csv_file):
        print(f"Error: File not found: {csv_file}")
        sys.exit(1)
    
    run_phase1_5_baseline(csv_file)
