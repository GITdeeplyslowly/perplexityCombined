"""
Performance measurement and instrumentation utilities.
Evidence-driven optimization foundation for Phase 1 baseline measurement.
"""
import time
import logging
from typing import Dict, Optional, List
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
import os

# Optional psutil for memory tracking (graceful degradation if not installed)
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("psutil not installed - memory tracking disabled. Install with: pip install psutil")

logger = logging.getLogger(__name__)


@dataclass
class TickMetrics:
    """Metrics captured for a single tick processing cycle."""
    tick_id: int
    timestamp: datetime
    
    # Latency breakdown (milliseconds)
    api_receive_ms: float = 0.0
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
        
        # Process info for resource monitoring (optional)
        self.process = psutil.Process(os.getpid()) if PSUTIL_AVAILABLE else None
        
        # Context tracking
        self._tick_start_time = None
        
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
        
        # Capture resource usage (if psutil available)
        if self.process:
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
            if component_name == 'api_receive':
                self.current_tick_metrics.api_receive_ms = duration_ms
            elif component_name == 'indicator_update':
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
                'api_receive_ms', 'indicator_update_ms', 'signal_eval_ms', 'position_mgmt_ms',
                'logging_ms', 'csv_write_ms', 'dataframe_ops_ms', 'queue_ops_ms',
                'memory_mb', 'cpu_percent'
            ])
            
            for m in self.tick_metrics:
                writer.writerow([
                    m.tick_id, m.timestamp.isoformat(), m.total_ms,
                    m.api_receive_ms, m.indicator_update_ms, m.signal_eval_ms, m.position_mgmt_ms,
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


# ============================================================================
# PHASE 1.5: PRE-CONVERGENCE INSTRUMENTATION
# ============================================================================

@dataclass
class PreConvergenceMetrics:
    """Metrics for pre-convergence path (WebSocket → Broker → Callback)."""
    tick_id: int
    timestamp: datetime
    
    # Pre-convergence breakdown (milliseconds)
    websocket_json_parse_ms: float = 0.0
    websocket_dict_creation_ms: float = 0.0
    websocket_total_ms: float = 0.0
    
    broker_tick_counting_ms: float = 0.0  # NEW: Counter init and logging check
    broker_timestamp_ops_ms: float = 0.0
    broker_csv_logging_ms: float = 0.0
    broker_queue_ops_ms: float = 0.0
    broker_callback_check_ms: float = 0.0  # NEW: Callback existence check
    broker_logging_ms: float = 0.0  # NEW: Actual logging operations
    broker_callback_invoke_ms: float = 0.0
    broker_total_ms: float = 0.0
    
    trader_session_check_ms: float = 0.0
    trader_signal_prep_ms: float = 0.0  # NEW: Logging prep before strategy
    trader_strategy_call_ms: float = 0.0  # NEW: strategy.on_tick() call overhead
    trader_signal_handling_ms: float = 0.0  # NEW: Signal processing (BUY/CLOSE)
    trader_position_mgmt_ms: float = 0.0  # NEW: Position management (TP/SL)
    trader_callback_invoke_ms: float = 0.0
    trader_total_ms: float = 0.0
    
    # Total pre-convergence time
    total_pre_convergence_ms: float = 0.0
    
    # Resource snapshot
    memory_mb: float = 0.0


class PreConvergenceInstrumentor:
    """
    Phase 1.5: Measure latency BEFORE strategy.on_tick() convergence point.
    
    Measures the live WebSocket path:
        SmartAPI → WebSocket._on_data → BrokerAdapter._handle_websocket_tick → 
        LiveTrader._on_tick_direct → [CONVERGENCE: strategy.on_tick()]
    
    Usage:
        # In websocket_stream.py
        instrumentor.start_websocket_tick()
        with instrumentor.measure_websocket('json_parse'):
            data = json.loads(message)
        with instrumentor.measure_websocket('dict_creation'):
            tick = {...}
        instrumentor.end_websocket_tick()
        
        # In broker_adapter.py
        instrumentor.start_broker_tick()
        with instrumentor.measure_broker('csv_logging'):
            self._log_tick_to_csv(tick)
        instrumentor.end_broker_tick()
    """
    
    def __init__(self, window_size: int = 1000):
        self.window_size = window_size
        self.metrics: deque = deque(maxlen=window_size)
        self.component_stats: Dict[str, ComponentStats] = {}
        
        self.current_metrics: Optional[PreConvergenceMetrics] = None
        self.tick_counter = 0
        
        self.process = psutil.Process(os.getpid()) if PSUTIL_AVAILABLE else None
        
        # Timing trackers
        self._websocket_start = None
        self._broker_start = None
        self._trader_start = None
        self._websocket_measurements = {}
        self._broker_measurements = {}
        self._trader_measurements = {}
        
    def start_websocket_tick(self):
        """Start measuring WebSocket tick processing."""
        self.tick_counter += 1
        self.current_metrics = PreConvergenceMetrics(
            tick_id=self.tick_counter,
            timestamp=datetime.now()
        )
        self._websocket_start = time.perf_counter()
        self._websocket_measurements = {}
        
    def measure_websocket(self, component: str):
        """Context manager for WebSocket component measurement."""
        return _PreConvergenceContext(self, 'websocket', component)
    
    def end_websocket_tick(self):
        """Finalize WebSocket measurements."""
        if self._websocket_start is not None:
            self.current_metrics.websocket_total_ms = (
                time.perf_counter() - self._websocket_start
            ) * 1000
            
            # Store individual measurements
            self.current_metrics.websocket_json_parse_ms = (
                self._websocket_measurements.get('json_parse', 0)
            )
            self.current_metrics.websocket_dict_creation_ms = (
                self._websocket_measurements.get('dict_creation', 0)
            )
            
    def start_broker_tick(self):
        """Start measuring broker tick processing."""
        self._broker_start = time.perf_counter()
        self._broker_measurements = {}
        
    def measure_broker(self, component: str):
        """Context manager for broker component measurement."""
        return _PreConvergenceContext(self, 'broker', component)
    
    def end_broker_tick(self):
        """Finalize broker measurements."""
        if self._broker_start is not None:
            self.current_metrics.broker_total_ms = (
                time.perf_counter() - self._broker_start
            ) * 1000
            
            # Store individual measurements
            self.current_metrics.broker_tick_counting_ms = (
                self._broker_measurements.get('tick_counting', 0)
            )
            self.current_metrics.broker_timestamp_ops_ms = (
                self._broker_measurements.get('timestamp_ops', 0)
            )
            self.current_metrics.broker_csv_logging_ms = (
                self._broker_measurements.get('csv_logging', 0)
            )
            self.current_metrics.broker_queue_ops_ms = (
                self._broker_measurements.get('queue_ops', 0)
            )
            self.current_metrics.broker_callback_check_ms = (
                self._broker_measurements.get('callback_check', 0)
            )
            self.current_metrics.broker_logging_ms = (
                self._broker_measurements.get('logging', 0)
            )
            self.current_metrics.broker_callback_invoke_ms = (
                self._broker_measurements.get('callback_invoke', 0)
            )
            
    def start_trader_tick(self):
        """Start measuring trader tick processing."""
        self._trader_start = time.perf_counter()
        self._trader_measurements = {}
        
    def measure_trader(self, component: str):
        """Context manager for trader component measurement."""
        return _PreConvergenceContext(self, 'trader', component)
    
    def end_trader_tick(self):
        """Finalize trader measurements and store complete metrics."""
        if self._trader_start is not None:
            self.current_metrics.trader_total_ms = (
                time.perf_counter() - self._trader_start
            ) * 1000
            
            # Store individual measurements
            self.current_metrics.trader_session_check_ms = (
                self._trader_measurements.get('session_check', 0)
            )
            self.current_metrics.trader_signal_prep_ms = (
                self._trader_measurements.get('signal_prep', 0)
            )
            self.current_metrics.trader_strategy_call_ms = (
                self._trader_measurements.get('strategy_call', 0)
            )
            self.current_metrics.trader_signal_handling_ms = (
                self._trader_measurements.get('signal_handling', 0)
            )
            self.current_metrics.trader_position_mgmt_ms = (
                self._trader_measurements.get('position_mgmt', 0)
            )
            self.current_metrics.trader_callback_invoke_ms = (
                self._trader_measurements.get('callback_invoke', 0)
            )
            
        # Calculate total pre-convergence time
        self.current_metrics.total_pre_convergence_ms = (
            self.current_metrics.websocket_total_ms +
            self.current_metrics.broker_total_ms +
            self.current_metrics.trader_total_ms
        )
        
        # Capture memory snapshot (if psutil available)
        if self.process:
            self.current_metrics.memory_mb = self.process.memory_info().rss / 1024 / 1024
        
        # Store metrics
        self.metrics.append(self.current_metrics)
        
        # Update component stats
        self._update_component_stats()
        
    def _update_component_stats(self):
        """Update aggregated component statistics."""
        m = self.current_metrics
        
        components = {
            'websocket_json_parse': m.websocket_json_parse_ms,
            'websocket_dict_creation': m.websocket_dict_creation_ms,
            'websocket_total': m.websocket_total_ms,
            'broker_tick_counting': m.broker_tick_counting_ms,
            'broker_timestamp_ops': m.broker_timestamp_ops_ms,
            'broker_csv_logging': m.broker_csv_logging_ms,
            'broker_queue_ops': m.broker_queue_ops_ms,
            'broker_callback_check': m.broker_callback_check_ms,
            'broker_logging': m.broker_logging_ms,
            'broker_callback_invoke': m.broker_callback_invoke_ms,
            'broker_total': m.broker_total_ms,
            'trader_session_check': m.trader_session_check_ms,
            'trader_signal_prep': m.trader_signal_prep_ms,
            'trader_strategy_call': m.trader_strategy_call_ms,
            'trader_signal_handling': m.trader_signal_handling_ms,
            'trader_position_mgmt': m.trader_position_mgmt_ms,
            'trader_callback_invoke': m.trader_callback_invoke_ms,
            'trader_total': m.trader_total_ms,
            'total_pre_convergence': m.total_pre_convergence_ms,
        }
        
        for name, duration_ms in components.items():
            if duration_ms > 0:
                if name not in self.component_stats:
                    self.component_stats[name] = ComponentStats(name=name)
                self.component_stats[name].update(duration_ms)
    
    def record_measurement(self, layer: str, component: str, duration_ms: float):
        """Record a measurement for a specific layer and component."""
        if layer == 'websocket':
            self._websocket_measurements[component] = duration_ms
        elif layer == 'broker':
            self._broker_measurements[component] = duration_ms
        elif layer == 'trader':
            self._trader_measurements[component] = duration_ms
            
    def get_report(self) -> Dict:
        """Generate Phase 1.5 pre-convergence performance report."""
        if not self.metrics:
            return {'error': 'No metrics collected'}
        
        # Calculate aggregates
        total_metrics = list(self.metrics)
        n = len(total_metrics)
        
        avg_total = sum(m.total_pre_convergence_ms for m in total_metrics) / n
        min_total = min(m.total_pre_convergence_ms for m in total_metrics)
        max_total = max(m.total_pre_convergence_ms for m in total_metrics)
        
        # Component breakdown
        breakdown = {}
        for name, stats in self.component_stats.items():
            if stats.call_count > 0:
                # Calculate percentage of total pre-convergence time
                stats.percent_of_total = (stats.avg_time_ms / avg_total * 100) if avg_total > 0 else 0
                breakdown[name] = {
                    'avg_ms': round(stats.avg_time_ms, 3),
                    'min_ms': round(stats.min_time_ms, 3),
                    'max_ms': round(stats.max_time_ms, 3),
                    'percent': round(stats.percent_of_total, 1)
                }
        
        # Memory stats
        avg_memory = sum(m.memory_mb for m in total_metrics) / n
        peak_memory = max(m.memory_mb for m in total_metrics)
        
        report = {
            'phase': '1.5',
            'description': 'Pre-Convergence Latency Analysis',
            'measurement_window': n,
            'latency': {
                'avg_ms': round(avg_total, 3),
                'min_ms': round(min_total, 3),
                'max_ms': round(max_total, 3),
                'target_ms': 1.0,  # Target: <1ms pre-convergence
                'meets_target': avg_total < 1.0
            },
            'component_breakdown': breakdown,
            'memory': {
                'avg_mb': round(avg_memory, 2),
                'peak_mb': round(peak_memory, 2)
            },
            'timestamp': datetime.now().isoformat()
        }
        
        # Add optimization recommendations
        report['recommendations'] = self._generate_recommendations(breakdown, avg_total)
        
        return report
    
    def _generate_recommendations(self, breakdown: Dict, avg_total_ms: float) -> List[Dict]:
        """Generate optimization recommendations based on measurements."""
        recommendations = []
        
        # Check CSV logging (Phase 3 threshold: >30%)
        csv_pct = breakdown.get('broker_csv_logging', {}).get('percent', 0)
        if csv_pct > 30:
            recommendations.append({
                'priority': 'HIGH',
                'phase': 3,
                'component': 'CSV Logging',
                'current_pct': csv_pct,
                'threshold_pct': 30,
                'recommendation': 'Implement async CSV logging or ring buffer (Phase 3)',
                'implement': True
            })
        
        # Check queue operations (Phase 4 threshold: >20%)
        queue_pct = breakdown.get('broker_queue_ops', {}).get('percent', 0)
        if queue_pct > 20:
            recommendations.append({
                'priority': 'MEDIUM',
                'phase': 4,
                'component': 'Queue Operations',
                'current_pct': queue_pct,
                'threshold_pct': 20,
                'recommendation': 'Optimize queue operations or skip in callback mode',
                'implement': True
            })
        
        # Check timestamp operations
        timestamp_pct = breakdown.get('broker_timestamp_ops', {}).get('percent', 0)
        if timestamp_pct > 10:
            recommendations.append({
                'priority': 'MEDIUM',
                'component': 'Timestamp Operations',
                'current_pct': timestamp_pct,
                'recommendation': 'Eliminate duplicate timestamp calls',
                'implement': True
            })
        
        # Check total pre-convergence time
        if avg_total_ms > 1.0:
            recommendations.append({
                'priority': 'HIGH',
                'component': 'Total Pre-Convergence',
                'current_ms': avg_total_ms,
                'target_ms': 1.0,
                'recommendation': f'Pre-convergence latency {avg_total_ms:.2f}ms exceeds 1ms target',
                'implement': True
            })
        
        return recommendations
    
    def save_detailed_metrics(self, filepath: str):
        """Save detailed pre-convergence metrics to CSV."""
        import csv
        
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'tick_id', 'timestamp', 'total_pre_convergence_ms',
                'websocket_json_parse_ms', 'websocket_dict_creation_ms', 'websocket_total_ms',
                'broker_tick_counting_ms', 'broker_timestamp_ops_ms', 'broker_csv_logging_ms', 
                'broker_queue_ops_ms', 'broker_callback_check_ms', 'broker_logging_ms',
                'broker_callback_invoke_ms', 'broker_total_ms',
                'trader_session_check_ms', 'trader_signal_prep_ms', 'trader_strategy_call_ms',
                'trader_signal_handling_ms', 'trader_position_mgmt_ms', 'trader_callback_invoke_ms', 'trader_total_ms',
                'memory_mb'
            ])
            
            for m in self.metrics:
                writer.writerow([
                    m.tick_id, m.timestamp.isoformat(), m.total_pre_convergence_ms,
                    m.websocket_json_parse_ms, m.websocket_dict_creation_ms, m.websocket_total_ms,
                    m.broker_tick_counting_ms, m.broker_timestamp_ops_ms, m.broker_csv_logging_ms, 
                    m.broker_queue_ops_ms, m.broker_callback_check_ms, m.broker_logging_ms,
                    m.broker_callback_invoke_ms, m.broker_total_ms,
                    m.trader_session_check_ms, m.trader_signal_prep_ms, m.trader_strategy_call_ms,
                    m.trader_signal_handling_ms, m.trader_position_mgmt_ms, m.trader_callback_invoke_ms, m.trader_total_ms,
                    m.memory_mb
                ])
                
        logger.info(f"Phase 1.5 detailed metrics saved to {filepath}")


class _PreConvergenceContext:
    """Context manager for pre-convergence component measurements."""
    
    def __init__(self, instrumentor: PreConvergenceInstrumentor, layer: str, component: str):
        self.instrumentor = instrumentor
        self.layer = layer
        self.component = component
        self.start_time = None
        
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.perf_counter() - self.start_time) * 1000
        self.instrumentor.record_measurement(self.layer, self.component, duration_ms)
        return False
