"""
analyze_performance.py - Analyze WebSocket Performance from Test Results

This script analyzes the GUI log output to identify performance bottlenecks
and calculate actual per-tick latency.
"""
import re
from datetime import datetime
from pathlib import Path
import sys

def parse_gui_log(log_text):
    """Parse GUI log to extract tick timing information"""
    
    # Pattern to match WebSocket tick received and callback processed
    tick_received_pattern = r'(\d{2}:\d{2}:\d{2}).*WebSocket tick #(\d+) received, price: ₹([\d.]+)'
    tick_processed_pattern = r'(\d{2}:\d{2}:\d{2}).*Processing tick #(\d+), price: ₹([\d.]+)'
    strategy_called_pattern = r'(\d{2}:\d{2}:\d{2}).*strategy\.on_tick\(\) for tick #(\d+)'
    
    ticks = []
    
    lines = log_text.split('\n')
    current_tick = {}
    
    for line in lines:
        # WebSocket tick received
        match = re.search(tick_received_pattern, line)
        if match:
            time_str, tick_num, price = match.groups()
            tick_num = int(tick_num)
            if tick_num not in [t.get('num') for t in ticks]:
                current_tick = {
                    'num': tick_num,
                    'received_time': time_str,
                    'price': float(price)
                }
                ticks.append(current_tick)
        
        # Tick processing started
        match = re.search(tick_processed_pattern, line)
        if match:
            time_str, tick_num, price = match.groups()
            tick_num = int(tick_num)
            for tick in ticks:
                if tick['num'] == tick_num:
                    tick['processed_time'] = time_str
                    break
        
        # Strategy called
        match = re.search(strategy_called_pattern, line)
        if match:
            time_str, tick_num = match.groups()
            tick_num = int(tick_num)
            for tick in ticks:
                if tick['num'] == tick_num:
                    tick['strategy_time'] = time_str
                    break
    
    return ticks


def calculate_latencies(ticks):
    """Calculate latency metrics from tick data"""
    
    latencies = []
    
    for tick in ticks:
        if 'received_time' in tick and 'strategy_time' in tick:
            # Parse times (assuming same day)
            received = datetime.strptime(tick['received_time'], '%H:%M:%S')
            strategy = datetime.strptime(tick['strategy_time'], '%H:%M:%S')
            
            # Calculate latency in milliseconds
            latency_ms = (strategy - received).total_seconds() * 1000
            
            if latency_ms >= 0:  # Sanity check
                latencies.append({
                    'tick_num': tick['num'],
                    'latency_ms': latency_ms,
                    'price': tick.get('price', 0)
                })
    
    return latencies


def generate_report(latencies):
    """Generate performance report"""
    
    if not latencies:
        print("❌ No latency data available")
        return
    
    latency_values = [l['latency_ms'] for l in latencies]
    latency_values.sort()
    
    n = len(latency_values)
    avg_latency = sum(latency_values) / n
    min_latency = latency_values[0]
    max_latency = latency_values[-1]
    p50 = latency_values[int(n * 0.50)]
    p95 = latency_values[int(n * 0.95)]
    p99 = latency_values[int(n * 0.99)]
    
    print("\n" + "="*80)
    print("📊 WEBSOCKET PERFORMANCE ANALYSIS")
    print("="*80)
    print(f"\nTicks Analyzed: {n}")
    print(f"\nLatency Statistics (WebSocket receive → Strategy entry):")
    print(f"  Average: {avg_latency:.2f} ms")
    print(f"  Minimum: {min_latency:.2f} ms")
    print(f"  Maximum: {max_latency:.2f} ms")
    print(f"  P50 (Median): {p50:.2f} ms")
    print(f"  P95: {p95:.2f} ms")
    print(f"  P99: {p99:.2f} ms")
    
    # Performance assessment
    print(f"\n🎯 Performance Assessment:")
    if avg_latency < 10:
        print("  ✅ EXCELLENT - Latency under 10ms")
    elif avg_latency < 50:
        print("  ✅ GOOD - Latency under 50ms target")
    elif avg_latency < 100:
        print("  ⚠️  ACCEPTABLE - Latency under 100ms but could be better")
    else:
        print("  ❌ POOR - Latency exceeds 100ms, needs optimization")
    
    # Identify worst cases
    print(f"\n🔍 Worst Latency Ticks:")
    worst_10 = sorted(latencies, key=lambda x: x['latency_ms'], reverse=True)[:10]
    for i, tick in enumerate(worst_10, 1):
        print(f"  #{i}: Tick {tick['tick_num']} - {tick['latency_ms']:.2f} ms @ ₹{tick['price']}")
    
    print("\n" + "="*80)


def main():
    """Main entry point"""
    
    print("📊 Performance Analysis Tool")
    print("=" * 80)
    
    # Try to read from clipboard or file
    log_file = Path("performance_test_log.txt")
    
    if log_file.exists():
        print(f"Reading log from: {log_file}")
        log_text = log_file.read_text(encoding='utf-8')
    else:
        print("\n❌ No log file found!")
        print(f"Expected file: {log_file.absolute()}")
        print("\nPlease paste the GUI log output below and press Ctrl+Z (Windows) or Ctrl+D (Linux/Mac):")
        print("-" * 80)
        
        lines = []
        try:
            while True:
                line = input()
                lines.append(line)
        except EOFError:
            pass
        
        log_text = '\n'.join(lines)
    
    print(f"\n✓ Log text loaded: {len(log_text)} characters")
    
    # Parse and analyze
    print("Parsing tick data...")
    ticks = parse_gui_log(log_text)
    print(f"✓ Found {len(ticks)} ticks")
    
    print("Calculating latencies...")
    latencies = calculate_latencies(ticks)
    print(f"✓ Calculated latencies for {len(latencies)} ticks")
    
    # Generate report
    generate_report(latencies)


if __name__ == "__main__":
    main()
