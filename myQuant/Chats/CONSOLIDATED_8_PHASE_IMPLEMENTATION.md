# Consolidated 8-Phase Performance Optimization Implementation Plan
## Evidence-Driven Trading System Optimization

**Document Version**: 1.0  
**Created**: October 22, 2025  
**Status**: Phase 1 Ready for Implementation

---

## Executive Summary

This plan optimizes the myQuant trading system through 8 phases, with **Phase 1 being the critical measurement baseline** that determines which subsequent phases are necessary.

### Phase Classification

**ALWAYS IMPLEMENT**:
- **Phase 0**: Critical Bug Fixes (PROVEN issues)
- **Phase 1**: Comprehensive Performance Baseline (Measurement foundation)

**CONDITIONAL** (Implement based on Phase 1 evidence):
- **Phase 2**: Async Logging (if logging latency >40%)
- **Phase 3**: Ring Buffer (if CSV writes >30%)
- **Phase 4**: Lock-Free Queues (if queue contention >20%)
- **Phase 5**: Batch DataFrame Ops (if DataFrame overhead >25%)

**ALWAYS IMPLEMENT** (After conditionals):
- **Phase 6**: System Monitoring & Alerting
- **Phase 7**: Production Hardening

**DEFERRED**:
- **Phase 8**: Advanced Optimizations (Only after 3+ months production data)

---

## Overall Framework Structure

```
Phase 0: Critical Fixes (2-3 hours)
    ↓
Phase 1: Baseline Measurement (1 day)
    ↓
Phase 1.5: ANALYSIS & DECISION GATE ⚠️
    ↓
    ├─→ Phase 2: Async Logging (IF needed - 1 day)
    ├─→ Phase 3: Ring Buffer (IF needed - 1 day)  
    ├─→ Phase 4: Lock-Free Queues (IF needed - 1 day)
    └─→ Phase 5: DataFrame Batch Ops (IF needed - 1 day)
    ↓
Phase 6: Monitoring (1 day)
    ↓
Phase 7: Production Hardening (1 day)
    ↓
Phase 8: Deferred (3+ months later)
```

---

# PHASE 0: Critical Bug Fixes (ALWAYS)
**Status**: ✅ COMPLETE  
**Duration**: 2-3 hours  
**Evidence**: Position sizing at 100%, indicator warm-up needed

## Overview
Fixed known critical issues before measurement phase.

## Changes Implemented
1. **Position Sizing**: `max_position_value_percent` from 100% → 30%
2. **Position Sizing Calculation**: Updated `compute_number_of_lots()` to use allocatable capital
3. **Indicator Warm-up**: 50 tick minimum before trading starts

## Implementation Details

See `PHASE_0_IMPLEMENTATION_COMPLETE.md` for full details.

### Key Changes:
- **defaults.py**: Position sizing (30%), min_warmup_ticks (50)
- **position_manager.py**: Updated compute_number_of_lots() calculation
- **liveStrategy.py**: Warm-up period tracking and enforcement

### Exit Logic Notes:
- **Current**: Simple comparisons (current_price >= tp_level, current_price <= sl_level)
- **Live Trading Reality**: Can ONLY exit at current market price (LTP)
- **Trade #4 Investigation**: Deferred as separate corner case (₹14.75→₹0.10 scenario)

---
    
    # Update indicators regardless of warm-up status
    self._update_indicators(tick)
    
    # Check warm-up completion
    if not self.warmup_complete:
        if self.tick_count >= self.min_warmup_ticks:
            self.warmup_complete = True
            logger.info(f"Indicator warm-up complete after {self.tick_count} ticks")
        else:
            return  # Skip trading during warm-up
    
    # ... rest of trading logic ...
```

**File**: `config/defaults.py`
```python
"strategy": {
    # ... existing params ...
    "min_warmup_ticks": 50,  # Minimum ticks before trading starts
}
```

### 4. Control-Side SL
**File**: `config/defaults.py`
```python
"risk": {
    # ... existing params ...
    "control_base_sl": True,  # Use control-side stop loss if True
}
```

**File**: `core/position_manager.py`
```python
def _calculate_sl_price(self, entry_price: float, side: str) -> float:
    """Calculate SL price with control_base_sl support."""
    use_control_sl = self.config_accessor.get_risk_param('control_base_sl')
    
    if use_control_sl:
        # Control-side logic: SL as percentage below entry
        sl_percent = self.config_accessor.get_risk_param('stop_loss_percent')
        return entry_price * (1 - sl_percent / 100)
    else:
        # Original indicator-based logic
        return self._calculate_indicator_based_sl(entry_price, side)
```

## Verification
- [ ] Position size limited to 30% of capital
- [ ] Price-crossing exits catch gap scenarios
- [ ] Strategy waits for warm-up before trading
- [ ] Control-side SL works as expected
- [ ] All changes in defaults.py
- [ ] No hardcoded fallbacks introduced

---

# PHASE 1: Comprehensive Performance Baseline (ALWAYS)
**Status**: MEASUREMENT FOUNDATION - Must Complete Before Proceeding  
**Duration**: 1 day  
**Goal**: Measure ALL potential bottlenecks to determine which optimizations are needed

## Overview

Phase 1 is the **critical decision gate**. We instrument the system to measure every suspected bottleneck, then use evidence to determine which of Phases 2-5 are actually necessary.

**PRIMARY FOCUS**: The main concern is reducing API tick latency and tick processing speed.

## What We're Measuring

### Primary Metrics (CRITICAL FOCUS)
1. **API Tick Latency**:
   - Time from market event to tick arrival in system
   - WebSocket receive time
   - Network latency measurement
   - Tick queue depth and wait times
   - Broker API → System ingestion time

2. **Tick Processing Breakdown**:
   - Indicator update time (incremental calculations)
   - Signal evaluation time
   - Position management time
   - Total tick processing time

### Secondary Metrics (Conditional Optimizations)
3. **System Overhead**:
   - Logging time
   - CSV write time
   - DataFrame operations time
   - Queue operations time

4. **System Resource Usage**:
   - Memory consumption (per component)
   - CPU utilization (per component)
   - Queue depths
   - GC pauses (lightweight correlation check)

5. **Throughput Metrics**:
   - Ticks processed per second
   - Callback vs polling performance
   - End-to-end latency (market event → decision)

## Implementation: Step-by-Step

### Step 1: Create Performance Instrumentation Module

**File**: `utils/performance_metrics.py` (NEW FILE)

```python
"""
Performance measurement and instrumentation utilities.
Evidence-driven optimization foundation.
"""
import time
import logging
from typing import Dict, Optional, List
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
import psutil
import os

logger = logging.getLogger(__name__)


@dataclass
class TickMetrics:
    """Metrics captured for a single tick processing cycle."""
    tick_id: int
    timestamp: datetime
    
    # Latency breakdown (milliseconds)
    indicator_update_ms: float = 0.0
    signal_eval_ms: float = 0.0
    position_mgmt_ms: float = 0.0
    logging_ms: float = 0.0
    csv_write_ms: float = 0.0
    dataframe_ops_ms: float = 0.0
    queue_ops_ms: float = 0.0
    total_ms: float = 0.0
    
    # Resource usage
    memory_mb: float = 0.0
    cpu_percent: float = 0.0


@dataclass
class ComponentStats:
    """Aggregated statistics for a component."""
    name: str
    call_count: int = 0
    total_time_ms: float = 0.0
    min_time_ms: float = float('inf')
    max_time_ms: float = 0.0
    avg_time_ms: float = 0.0
    percent_of_total: float = 0.0
    
    def update(self, duration_ms: float):
        """Update stats with new measurement."""
        self.call_count += 1
        self.total_time_ms += duration_ms
        self.min_time_ms = min(self.min_time_ms, duration_ms)
        self.max_time_ms = max(self.max_time_ms, duration_ms)
        self.avg_time_ms = self.total_time_ms / self.call_count


class PerformanceInstrumentor:
    """
    Central performance measurement system.
    
    Usage:
        instrumentor = PerformanceInstrumentor()
        
        with instrumentor.measure('component_name'):
            # Code to measure
            do_work()
        
        results = instrumentor.get_baseline_report()
    """
    
    def __init__(self, window_size: int = 1000):
        self.window_size = window_size
        self.tick_metrics: deque = deque(maxlen=window_size)
        self.component_stats: Dict[str, ComponentStats] = defaultdict(
            lambda: ComponentStats(name='')
        )
        
        self.current_tick_metrics: Optional[TickMetrics] = None
        self.tick_counter = 0
        
        # Process info for resource monitoring
        self.process = psutil.Process(os.getpid())
        
        # Context tracking
        self._context_stack = []
        self._start_times = {}
        
    def start_tick(self):
        """Start measuring a new tick cycle."""
        self.tick_counter += 1
        self.current_tick_metrics = TickMetrics(
            tick_id=self.tick_counter,
            timestamp=datetime.now()
        )
        self._tick_start_time = time.perf_counter()
        
    def end_tick(self):
        """Finalize current tick measurements."""
        if self.current_tick_metrics is None:
            return
            
        # Calculate total time
        total_time = (time.perf_counter() - self._tick_start_time) * 1000
        self.current_tick_metrics.total_ms = total_time
        
        # Capture resource usage
        self.current_tick_metrics.memory_mb = self.process.memory_info().rss / 1024 / 1024
        self.current_tick_metrics.cpu_percent = self.process.cpu_percent()
        
        # Store metrics
        self.tick_metrics.append(self.current_tick_metrics)
        self.current_tick_metrics = None
        
    def measure(self, component_name: str):
        """
        Context manager for measuring component execution time.
        
        Usage:
            with instrumentor.measure('indicator_update'):
                update_indicators()
        """
        return _MeasurementContext(self, component_name)
        
    def record_measurement(self, component_name: str, duration_ms: float):
        """Record a measurement for a component."""
        # Update component stats
        if component_name not in self.component_stats:
            self.component_stats[component_name] = ComponentStats(name=component_name)
        self.component_stats[component_name].update(duration_ms)
        
        # Store in current tick metrics
        if self.current_tick_metrics is not None:
            if component_name == 'indicator_update':
                self.current_tick_metrics.indicator_update_ms = duration_ms
            elif component_name == 'signal_eval':
                self.current_tick_metrics.signal_eval_ms = duration_ms
            elif component_name == 'position_mgmt':
                self.current_tick_metrics.position_mgmt_ms = duration_ms
            elif component_name == 'logging':
                self.current_tick_metrics.logging_ms = duration_ms
            elif component_name == 'csv_write':
                self.current_tick_metrics.csv_write_ms = duration_ms
            elif component_name == 'dataframe_ops':
                self.current_tick_metrics.dataframe_ops_ms = duration_ms
            elif component_name == 'queue_ops':
                self.current_tick_metrics.queue_ops_ms = duration_ms
                
    def get_baseline_report(self) -> Dict:
        """
        Generate comprehensive baseline report.
        
        Returns:
            Dict with all measurements and recommendations.
        """
        if not self.tick_metrics:
            return {'error': 'No measurements collected'}
            
        # Calculate aggregates
        total_ticks = len(self.tick_metrics)
        
        # Component breakdown
        total_time_all = sum(stat.total_time_ms for stat in self.component_stats.values())
        for stat in self.component_stats.values():
            if total_time_all > 0:
                stat.percent_of_total = (stat.total_time_ms / total_time_all) * 100
                
        # Per-tick statistics
        total_times = [m.total_ms for m in self.tick_metrics]
        avg_tick_time = sum(total_times) / len(total_times)
        max_tick_time = max(total_times)
        min_tick_time = min(total_times)
        
        # Throughput
        throughput_tps = 1000 / avg_tick_time if avg_tick_time > 0 else 0
        
        # Resource usage
        memory_values = [m.memory_mb for m in self.tick_metrics]
        avg_memory = sum(memory_values) / len(memory_values)
        max_memory = max(memory_values)
        
        # Build report
        report = {
            'measurement_window': {
                'total_ticks': total_ticks,
                'window_size': self.window_size,
            },
            'latency_summary': {
                'avg_tick_ms': round(avg_tick_time, 3),
                'min_tick_ms': round(min_tick_time, 3),
                'max_tick_ms': round(max_tick_time, 3),
                'target_ms': 5.0,
                'meets_target': avg_tick_time < 5.0,
            },
            'throughput': {
                'avg_ticks_per_second': round(throughput_tps, 1),
                'target_tps': 100,
                'meets_target': throughput_tps >= 100,
            },
            'component_breakdown': {},
            'resource_usage': {
                'avg_memory_mb': round(avg_memory, 2),
                'max_memory_mb': round(max_memory, 2),
            },
            'recommendations': [],
        }
        
        # Component details
        sorted_components = sorted(
            self.component_stats.values(),
            key=lambda s: s.percent_of_total,
            reverse=True
        )
        
        for stat in sorted_components:
            report['component_breakdown'][stat.name] = {
                'call_count': stat.call_count,
                'total_time_ms': round(stat.total_time_ms, 2),
                'avg_time_ms': round(stat.avg_time_ms, 3),
                'min_time_ms': round(stat.min_time_ms, 3),
                'max_time_ms': round(stat.max_time_ms, 3),
                'percent_of_total': round(stat.percent_of_total, 1),
            }
            
        # Generate recommendations
        report['recommendations'] = self._generate_recommendations(report)
        
        return report
        
    def _generate_recommendations(self, report: Dict) -> List[Dict]:
        """Generate optimization recommendations based on measurements."""
        recommendations = []
        
        breakdown = report['component_breakdown']
        
        # Check each conditional phase threshold
        if 'logging' in breakdown and breakdown['logging']['percent_of_total'] > 40:
            recommendations.append({
                'phase': 2,
                'name': 'Async Logging',
                'reason': f"Logging takes {breakdown['logging']['percent_of_total']:.1f}% of time (>40% threshold)",
                'priority': 'HIGH',
                'implement': True,
            })
        else:
            recommendations.append({
                'phase': 2,
                'name': 'Async Logging',
                'reason': f"Logging only {breakdown.get('logging', {}).get('percent_of_total', 0):.1f}% (<40% threshold)",
                'priority': 'LOW',
                'implement': False,
            })
            
        if 'csv_write' in breakdown and breakdown['csv_write']['percent_of_total'] > 30:
            recommendations.append({
                'phase': 3,
                'name': 'Ring Buffer',
                'reason': f"CSV writes take {breakdown['csv_write']['percent_of_total']:.1f}% of time (>30% threshold)",
                'priority': 'HIGH',
                'implement': True,
            })
        else:
            recommendations.append({
                'phase': 3,
                'name': 'Ring Buffer',
                'reason': f"CSV writes only {breakdown.get('csv_write', {}).get('percent_of_total', 0):.1f}% (<30% threshold)",
                'priority': 'LOW',
                'implement': False,
            })
            
        if 'queue_ops' in breakdown and breakdown['queue_ops']['percent_of_total'] > 20:
            recommendations.append({
                'phase': 4,
                'name': 'Lock-Free Queues',
                'reason': f"Queue operations take {breakdown['queue_ops']['percent_of_total']:.1f}% of time (>20% threshold)",
                'priority': 'MEDIUM',
                'implement': True,
            })
        else:
            recommendations.append({
                'phase': 4,
                'name': 'Lock-Free Queues',
                'reason': f"Queue operations only {breakdown.get('queue_ops', {}).get('percent_of_total', 0):.1f}% (<20% threshold)",
                'priority': 'LOW',
                'implement': False,
            })
            
        if 'dataframe_ops' in breakdown and breakdown['dataframe_ops']['percent_of_total'] > 25:
            recommendations.append({
                'phase': 5,
                'name': 'Batch DataFrame Ops',
                'reason': f"DataFrame operations take {breakdown['dataframe_ops']['percent_of_total']:.1f}% of time (>25% threshold)",
                'priority': 'MEDIUM',
                'implement': True,
            })
        else:
            recommendations.append({
                'phase': 5,
                'name': 'Batch DataFrame Ops',
                'reason': f"DataFrame operations only {breakdown.get('dataframe_ops', {}).get('percent_of_total', 0):.1f}% (<25% threshold)",
                'priority': 'LOW',
                'implement': False,
            })
            
        return recommendations
        
    def save_detailed_metrics(self, filepath: str):
        """Save detailed per-tick metrics to CSV for analysis."""
        import csv
        
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'tick_id', 'timestamp', 'total_ms',
                'indicator_update_ms', 'signal_eval_ms', 'position_mgmt_ms',
                'logging_ms', 'csv_write_ms', 'dataframe_ops_ms', 'queue_ops_ms',
                'memory_mb', 'cpu_percent'
            ])
            
            for m in self.tick_metrics:
                writer.writerow([
                    m.tick_id, m.timestamp.isoformat(), m.total_ms,
                    m.indicator_update_ms, m.signal_eval_ms, m.position_mgmt_ms,
                    m.logging_ms, m.csv_write_ms, m.dataframe_ops_ms, m.queue_ops_ms,
                    m.memory_mb, m.cpu_percent
                ])
                
        logger.info(f"Detailed metrics saved to {filepath}")


class _MeasurementContext:
    """Context manager for component measurements."""
    
    def __init__(self, instrumentor: PerformanceInstrumentor, component_name: str):
        self.instrumentor = instrumentor
        self.component_name = component_name
        self.start_time = None
        
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.perf_counter() - self.start_time) * 1000
        self.instrumentor.record_measurement(self.component_name, duration_ms)
        return False
```

**Install Dependencies** (if not already present):
```bash
pip install psutil
```

### Step 2: Integrate Instrumentation into Live Strategy

**File**: `core/liveStrategy.py`

Add imports:
```python
from utils.performance_metrics import PerformanceInstrumentor
```

Update `__init__`:
```python
def __init__(self, config, indicators_module):
    # ... existing init code ...
    
    # Performance instrumentation (Phase 1)
    self.instrumentor = PerformanceInstrumentor(window_size=1000)
    self.instrumentation_enabled = True  # Control flag
```

Update `on_tick` method to wrap components:
```python
def on_tick(self, tick: Dict):
    """Process incoming tick with performance measurement."""
    
    # Start tick measurement
    if self.instrumentation_enabled:
        self.instrumentor.start_tick()
    
    try:
        # Indicator updates
        if self.instrumentation_enabled:
            with self.instrumentor.measure('indicator_update'):
                self._update_indicators(tick)
        else:
            self._update_indicators(tick)
        
        # Warm-up check
        if not self.warmup_complete:
            if self.tick_count >= self.min_warmup_ticks:
                self.warmup_complete = True
                if self.instrumentation_enabled:
                    with self.instrumentor.measure('logging'):
                        logger.info(f"Warm-up complete after {self.tick_count} ticks")
                else:
                    logger.info(f"Warm-up complete after {self.tick_count} ticks")
            else:
                if self.instrumentation_enabled:
                    self.instrumentor.end_tick()
                return
        
        # Signal evaluation
        if self.instrumentation_enabled:
            with self.instrumentor.measure('signal_eval'):
                signal = self._evaluate_signals(tick)
        else:
            signal = self._evaluate_signals(tick)
        
        # Position management
        if self.instrumentation_enabled:
            with self.instrumentor.measure('position_mgmt'):
                self._handle_position_logic(tick, signal)
        else:
            self._handle_position_logic(tick, signal)
            
    finally:
        # End tick measurement
        if self.instrumentation_enabled:
            self.instrumentor.end_tick()
```

### Step 3: Integrate Instrumentation into Data Handlers

**File**: `live/forward_test_results.py`

Add instrumentation to CSV writes:
```python
def __init__(self, config, strategy):
    # ... existing init ...
    self.instrumentor = getattr(strategy, 'instrumentor', None)

def log_trade(self, trade: Dict):
    """Log trade with performance measurement."""
    if self.instrumentor:
        with self.instrumentor.measure('csv_write'):
            self._write_trade_to_csv(trade)
    else:
        self._write_trade_to_csv(trade)
```

**File**: `live/broker_adapter.py`

Add queue operation measurement:
```python
def _enqueue_tick(self, tick: Dict):
    """Enqueue tick with measurement."""
    if hasattr(self, 'instrumentor') and self.instrumentor:
        with self.instrumentor.measure('queue_ops'):
            self.tick_queue.put(tick)
    else:
        self.tick_queue.put(tick)
```

### Step 4: Create Baseline Analysis Script

**File**: `scripts/run_phase1_baseline.py` (NEW FILE)

```python
"""
Phase 1: Baseline Performance Measurement Runner
Run this script to collect baseline metrics and generate recommendations.
"""
import sys
import os
from pathlib import Path
import json
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from myQuant.core.liveStrategy import ModularIntradayStrategy
from myQuant.live.data_simulator import DataSimulator
from myQuant.config.defaults import create_config_from_defaults
from myQuant.utils.config_helper import validate_config, freeze_config
import myQuant.core.indicators as indicators_module


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
    config = create_config_from_defaults()
    validation = validate_config(config)
    
    if not validation.get('valid', False):
        print("ERROR: Invalid configuration")
        for error in validation.get('errors', []):
            print(f"  - {error}")
        return
    
    frozen_config = freeze_config(config)
    
    # Create strategy with instrumentation
    strategy = ModularIntradayStrategy(frozen_config, indicators_module)
    strategy.instrumentation_enabled = True
    print(f"✓ Strategy initialized with instrumentation enabled")
    print(f"  Window size: {strategy.instrumentor.window_size} ticks")
    print()
    
    # Simulate data
    print("Processing ticks...")
    simulator = DataSimulator(csv_file)
    
    tick_count = 0
    for tick in simulator.stream_ticks():
        strategy.on_tick(tick)
        tick_count += 1
        
        if tick_count % 100 == 0:
            print(f"  Processed {tick_count}/{num_ticks} ticks...")
        
        if tick_count >= num_ticks:
            break
    
    print(f"✓ Processed {tick_count} ticks")
    print()
    
    # Generate baseline report
    print("Generating baseline report...")
    report = strategy.instrumentor.get_baseline_report()
    
    # Save detailed metrics
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    metrics_file = project_root / f"results/phase1_detailed_metrics_{timestamp}.csv"
    report_file = project_root / f"results/phase1_baseline_report_{timestamp}.json"
    
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


if __name__ == '__main__':
    # Example usage
    csv_file = project_root / "path/to/your/tick_data.csv"
    
    if not csv_file.exists():
        print(f"ERROR: CSV file not found: {csv_file}")
        print()
        print("Usage: python run_phase1_baseline.py")
        print("Update the csv_file path in the script to point to your tick data.")
        sys.exit(1)
    
    run_baseline_measurement(str(csv_file), num_ticks=1000)
```

### Step 5: Create Configuration for Phase 1

**File**: `config/defaults.py`

Add Phase 1 settings:
```python
"performance": {
    "instrumentation_enabled": True,  # Enable performance measurement
    "instrumentation_window_size": 1000,  # Number of ticks to track
    "baseline_measurement_ticks": 1000,  # Ticks for baseline measurement
}
```

### Step 6: Run Phase 1 Baseline

**Execution Steps**:

1. **Update CSV path** in `scripts/run_phase1_baseline.py`
   ```python
   csv_file = project_root / "path/to/your/tick_data.csv"
   ```

2. **Run baseline measurement**:
   ```bash
   cd c:\Users\user\projects\PerplexityCombinedTest
   python scripts\run_phase1_baseline.py
   ```

3. **Review outputs**:
   - `results/phase1_baseline_report_TIMESTAMP.json` - Full analysis
   - `results/phase1_detailed_metrics_TIMESTAMP.csv` - Per-tick data
   - Console output with recommendations

4. **Analyze recommendations**:
   - Check which phases have `"implement": true`
   - Note priority levels (HIGH/MEDIUM/LOW)
   - Review percentage breakdowns

### Step 7: Decision Gate (Phase 1.5)

Based on Phase 1 results, make implementation decisions:

**Decision Matrix**:
```
IF logging_percent > 40% → Implement Phase 2 (Async Logging)
IF csv_write_percent > 30% → Implement Phase 3 (Ring Buffer)
IF queue_ops_percent > 20% → Implement Phase 4 (Lock-Free Queues)
IF dataframe_ops_percent > 25% → Implement Phase 5 (Batch DataFrame Ops)

ELSE → Skip to Phase 6 (Monitoring)
```

**Document your decision** in a file:
```
results/phase1_decision_TIMESTAMP.txt
```

Example content:
```
Phase 1 Baseline Results: 2025-10-22 14:30:00

Measurements:
- Logging: 45.2% of time → IMPLEMENT Phase 2
- CSV writes: 15.3% of time → SKIP Phase 3
- Queue ops: 8.1% of time → SKIP Phase 4
- DataFrame ops: 12.5% of time → SKIP Phase 5

Decision: Implement Phase 2 only, then proceed to Phase 6.
```

## Phase 1 Verification Checklist

- [ ] `utils/performance_metrics.py` created with instrumentation classes
- [ ] `psutil` installed
- [ ] `liveStrategy.py` integrated with instrumentation
- [ ] `forward_test_results.py` measures CSV writes
- [ ] `broker_adapter.py` measures queue operations
- [ ] `scripts/run_phase1_baseline.py` created
- [ ] Configuration updated in `defaults.py`
- [ ] Baseline measurement executed successfully
- [ ] Results files generated (JSON + CSV)
- [ ] Recommendations reviewed
- [ ] Decision documented for Phase 1.5

## Expected Outcomes

After Phase 1 completion, you will have:

1. ✅ **Quantitative evidence** of all bottlenecks
2. ✅ **Percentage breakdown** of time spent per component
3. ✅ **Clear recommendations** for which phases to implement
4. ✅ **Baseline metrics** for before/after comparison
5. ✅ **Per-tick data** for deep analysis if needed

## Troubleshooting

### Issue: High memory usage during instrumentation
**Solution**: Reduce `instrumentation_window_size` in config from 1000 to 500.

### Issue: Instrumentation slows down processing
**Expected**: Instrumentation adds ~5-10% overhead, which is acceptable for baseline measurement.
**Solution**: Set `instrumentation_enabled = False` after baseline collection.

### Issue: Missing components in breakdown
**Solution**: Ensure all code paths wrap operations with `instrumentor.measure('component_name')`.

---

# PHASE 2-5: Conditional Optimizations (FRAMEWORK ONLY)

These phases are **conditional** based on Phase 1 evidence. Full implementation details will be provided ONLY if Phase 1 results indicate they're needed.

## Phase 2: Async Logging (IF logging >40%)
**Duration**: 1 day  
**Evidence Required**: Logging consumes >40% of per-tick time

### Overview
Move logging operations to background thread with bounded queue.

### Key Changes
- Implement `AsyncLoggingHandler` with queue
- Replace synchronous logger calls
- Add log queue monitoring

### Implementation Trigger
```python
if baseline_report['component_breakdown']['logging']['percent_of_total'] > 40:
    print("Phase 2 NEEDED: Implement async logging")
```

---

## Phase 3: Ring Buffer for Results (IF CSV writes >30%)
**Duration**: 1 day  
**Evidence Required**: CSV writes consume >30% of per-tick time

### Overview
Buffer results in memory, batch write to CSV.

### Key Changes
- Implement ring buffer for trade results
- Batch CSV writes (10-20 trades per write)
- Add buffer overflow protection

### Implementation Trigger
```python
if baseline_report['component_breakdown']['csv_write']['percent_of_total'] > 30:
    print("Phase 3 NEEDED: Implement ring buffer")
```

---

## Phase 4: Lock-Free Queues (IF queue contention >20%)
**Duration**: 1 day  
**Evidence Required**: Queue operations consume >20% of per-tick time

### Overview
Replace `queue.Queue` with lock-free alternatives.

### Key Changes
- Use `multiprocessing.Queue` or custom ring buffer
- Minimize lock contention
- Add queue depth monitoring

### Implementation Trigger
```python
if baseline_report['component_breakdown']['queue_ops']['percent_of_total'] > 20:
    print("Phase 4 NEEDED: Implement lock-free queues")
```

---

## Phase 5: Batch DataFrame Operations (IF DataFrame ops >25%)
**Duration**: 1 day  
**Evidence Required**: DataFrame operations consume >25% of per-tick time

### Overview
Batch DataFrame operations instead of per-tick updates.

### Key Changes
- Accumulate data in lists
- Periodic DataFrame creation (every 100 ticks)
- Maintain incremental indicators separately

### Implementation Trigger
```python
if baseline_report['component_breakdown']['dataframe_ops']['percent_of_total'] > 25:
    print("Phase 5 NEEDED: Batch DataFrame operations")
```

---

# PHASE 6: System Monitoring & Alerting (ALWAYS)
**Duration**: 1 day  
**Status**: Implement after conditional phases

### Overview
Production monitoring for live trading.

### Key Components
1. Real-time health dashboard
2. Alert system (email/SMS)
3. Performance degradation detection
4. Trade execution monitoring

### Implementation Checklist
- [ ] Health check endpoint
- [ ] Alert configuration
- [ ] Monitoring dashboard
- [ ] Log aggregation

*(Detailed implementation provided when Phase 6 is reached)*

---

# PHASE 7: Production Hardening (ALWAYS)
**Duration**: 1 day  
**Status**: Final phase before live deployment

### Overview
Ensure system stability and resilience.

### Key Components
1. Graceful shutdown handling
2. Connection retry logic
3. Data validation guards
4. Configuration freeze verification

### Implementation Checklist
- [ ] Signal handlers
- [ ] Reconnection logic
- [ ] Input validation
- [ ] Configuration audit

*(Detailed implementation provided when Phase 7 is reached)*

---

# PHASE 8: Advanced Optimizations (DEFERRED)
**Status**: Defer until 3+ months production data

### Future Optimizations
- Cython/Numba for indicators
- JIT compilation
- Advanced memory pooling
- SIMD operations

**Requirement**: Must have production evidence before implementing.

---

# Execution Roadmap

## Week 1
- **Day 1**: Phase 0 (Critical fixes) + Start Phase 1 setup
- **Day 2**: Complete Phase 1 baseline measurement
- **Day 3**: Phase 1.5 analysis and decision gate
- **Day 4-5**: Implement conditional phases (if needed)

## Week 2
- **Day 1**: Phase 6 (Monitoring)
- **Day 2**: Phase 7 (Production hardening)
- **Day 3-5**: Integration testing and validation

---

# Success Criteria

## Phase 1 Success
- ✅ Baseline report generated
- ✅ All components measured
- ✅ Clear recommendations provided
- ✅ Decision gate completed

## Overall Success
- ✅ Average tick latency <5ms
- ✅ Throughput >100 ticks/second
- ✅ 99.9% uptime
- ✅ No silent failures
- ✅ Evidence-backed optimizations only

---

# Appendix: Measurement Thresholds

| Component | Threshold | Phase | Priority |
|-----------|-----------|-------|----------|
| Logging | >40% | 2 | HIGH |
| CSV writes | >30% | 3 | HIGH |
| Queue ops | >20% | 4 | MEDIUM |
| DataFrame ops | >25% | 5 | MEDIUM |

---

**END OF PHASE 1 IMPLEMENTATION**

**Next Steps**: Run Phase 1 baseline, review results, proceed to Phase 1.5 decision gate.
