"""
performance_test_hook.py - Performance Testing via GUI Workflow

This module enables performance testing by hooking into the GUI's established
workflow instead of creating parallel authentication/configuration paths.

Core Principle: Test the actual workflow, not a synthetic one.
"""
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class PerformanceTestConfig:
    """Configuration for performance testing session"""
    target_ticks: int = 1000
    enable_pre_convergence: bool = True
    enable_post_convergence: bool = True
    auto_stop_after_target: bool = True
    generate_report: bool = True
    

class PerformanceTestHook:
    """
    Hooks into GUI workflow to enable performance measurement without
    creating parallel authentication/configuration paths.
    
    Usage:
        # In test script
        hook = PerformanceTestHook(gui_instance)
        hook.enable_testing(target_ticks=1000)
        
        # GUI workflow proceeds normally
        gui.run_forward_test_wrapper()
        
        # Hook intercepts and instruments the workflow
    """
    
    def __init__(self, gui_instance=None):
        """
        Initialize performance testing hook
        
        Args:
            gui_instance: TradingGUI instance (if available)
        """
        self.gui = gui_instance
        self.enabled = False
        self.config = PerformanceTestConfig()
        
        # Instrumentation
        self.pre_instrumentor = None
        self.post_instrumentor = None
        
        # Statistics
        self.tick_count = 0
        self.start_time = None
        self.test_complete = False
        
    def enable_testing(
        self, 
        target_ticks: int = 1000,
        enable_pre: bool = True,
        enable_post: bool = True,
        auto_stop: bool = True
    ):
        """
        Enable performance testing mode
        
        Args:
            target_ticks: Number of ticks to collect before stopping
            enable_pre: Enable pre-convergence instrumentation
            enable_post: Enable post-convergence instrumentation
            auto_stop: Automatically stop after target_ticks reached
        """
        self.enabled = True
        self.config.target_ticks = target_ticks
        self.config.enable_pre_convergence = enable_pre
        self.config.enable_post_convergence = enable_post
        self.config.auto_stop_after_target = auto_stop
        
        logger.info(f"🔬 Performance testing ENABLED - Target: {target_ticks} ticks")
        
        # Create instrumentors if needed
        if enable_pre:
            from myQuant.utils.performance_metrics import PreConvergenceInstrumentor
            self.pre_instrumentor = PreConvergenceInstrumentor(window_size=target_ticks)
            logger.info("✓ Pre-convergence instrumentation ready")
            
        if enable_post:
            from myQuant.utils.performance_metrics import PerformanceInstrumentor
            self.post_instrumentor = PerformanceInstrumentor(window_size=target_ticks)
            logger.info("✓ Post-convergence instrumentation ready")
    
    def inject_into_trader(self, trader):
        """
        Inject instrumentation into LiveTrader instance
        
        This is called automatically when GUI creates the trader.
        
        Args:
            trader: LiveTrader instance from GUI workflow
        """
        if not self.enabled:
            return
            
        logger.info("🔌 Injecting performance instrumentation into LiveTrader...")
        
        # Inject pre-convergence instrumentation at MODULE level (not instance level)
        if self.config.enable_pre_convergence and self.pre_instrumentor:
            try:
                # CRITICAL: Import modules using BOTH possible paths due to Python import inconsistencies
                # broker_adapter.py imports as "live.websocket_stream" (without myQuant prefix)
                # We need to inject into the ACTUAL module that gets used, not an alternate import path
                
                # Try to inject into the "live.*" path first (what broker_adapter actually uses)
                websocket_injected = False
                broker_injected = False
                trader_injected = False
                
                try:
                    import live.websocket_stream as websocket_stream
                    if hasattr(websocket_stream, 'set_pre_convergence_instrumentor'):
                        websocket_stream.set_pre_convergence_instrumentor(self.pre_instrumentor)
                        logger.info("  ✓ Pre-convergence instrumentation → WebSocket (live.websocket_stream)")
                        websocket_injected = True
                except ImportError:
                    pass
                
                # Fallback to myQuant.live.* path if needed
                if not websocket_injected:
                    try:
                        import myQuant.live.websocket_stream as websocket_stream
                        if hasattr(websocket_stream, 'set_pre_convergence_instrumentor'):
                            websocket_stream.set_pre_convergence_instrumentor(self.pre_instrumentor)
                            logger.info("  ✓ Pre-convergence instrumentation → WebSocket (myQuant.live.websocket_stream)")
                            websocket_injected = True
                    except ImportError:
                        pass
                
                # Same for broker_adapter
                try:
                    import live.broker_adapter as broker_adapter
                    if hasattr(broker_adapter, 'set_pre_convergence_instrumentor'):
                        broker_adapter.set_pre_convergence_instrumentor(self.pre_instrumentor)
                        logger.info("  ✓ Pre-convergence instrumentation → BrokerAdapter (live.broker_adapter)")
                        broker_injected = True
                except ImportError:
                    pass
                
                if not broker_injected:
                    try:
                        import myQuant.live.broker_adapter as broker_adapter
                        if hasattr(broker_adapter, 'set_pre_convergence_instrumentor'):
                            broker_adapter.set_pre_convergence_instrumentor(self.pre_instrumentor)
                            logger.info("  ✓ Pre-convergence instrumentation → BrokerAdapter (myQuant.live.broker_adapter)")
                            broker_injected = True
                    except ImportError:
                        pass
                
                # Same for trader
                try:
                    import live.trader as trader_module
                    if hasattr(trader_module, 'set_pre_convergence_instrumentor'):
                        trader_module.set_pre_convergence_instrumentor(self.pre_instrumentor)
                        logger.info("  ✓ Pre-convergence instrumentation → Trader (live.trader)")
                        trader_injected = True
                except ImportError:
                    pass
                
                if not trader_injected:
                    try:
                        import myQuant.live.trader as trader_module
                        if hasattr(trader_module, 'set_pre_convergence_instrumentor'):
                            trader_module.set_pre_convergence_instrumentor(self.pre_instrumentor)
                            logger.info("  ✓ Pre-convergence instrumentation → Trader (myQuant.live.trader)")
                            trader_injected = True
                    except ImportError:
                        pass
                # Extra safety: some runtimes import modules under alternate package keys
                # (e.g. 'live.websocket_stream' vs 'myQuant.live.websocket_stream'). Ensure
                # we set the instrumentor on any already-loaded module objects directly
                # so there are not two separate module instances with different globals.
                try:
                    import sys
                    for mod_key in ("live.websocket_stream", "myQuant.live.websocket_stream"):
                        mod = sys.modules.get(mod_key)
                        if mod is not None:
                            # If module exposes setter, use it; otherwise set global directly
                            if hasattr(mod, 'set_pre_convergence_instrumentor'):
                                try:
                                    mod.set_pre_convergence_instrumentor(self.pre_instrumentor)
                                    logger.info(f"  ✓ Pre-convergence instrumentation → {mod_key} (via sys.modules)")
                                except Exception:
                                    # Best-effort: set attribute directly
                                    setattr(mod, '_pre_convergence_instrumentor', self.pre_instrumentor)
                                    logger.info(f"  ✓ Pre-convergence instrumentation → {mod_key} (direct setattr)")
                            else:
                                setattr(mod, '_pre_convergence_instrumentor', self.pre_instrumentor)
                                logger.info(f"  ✓ Pre-convergence instrumentation → {mod_key} (direct setattr, no setter)")
                except Exception:
                    # Don't let instrumentation helper crash the GUI flow
                    logger.debug("Could not set instrumentor directly on sys.modules entries", exc_info=True)
                    
            except ImportError as e:
                logger.warning(f"⚠️ Could not import modules for pre-convergence instrumentation: {e}")
        
        # Inject post-convergence instrumentation
        if self.config.enable_post_convergence and self.post_instrumentor:
            if hasattr(trader, 'strategy') and trader.strategy:
                if hasattr(trader.strategy, 'instrumentor'):
                    trader.strategy.instrumentor = self.post_instrumentor
                    # CRITICAL: Enable instrumentation flag so strategy actually uses it
                    trader.strategy.instrumentation_enabled = True
                    logger.info("  ✓ Post-convergence instrumentation → Strategy (enabled=True)")
        
        # Wrap tick callback to monitor progress
        if self.config.auto_stop_after_target:
            self._wrap_tick_callback(trader)
        
        self.start_time = datetime.now()
        logger.info(f"🎯 Performance testing active - will collect {self.config.target_ticks} ticks")
    
    def _wrap_tick_callback(self, trader):
        """Wrap trader's WebSocket direct callback to monitor progress and auto-stop"""
        if not hasattr(trader, '_on_tick_direct'):
            logger.warning("⚠️ Could not find trader._on_tick_direct method")
            return
        
        original_on_tick = trader._on_tick_direct
        hook_self = self  # Capture self reference for closure
        
        def instrumented_on_tick(tick, symbol):
            """Wrapped callback that monitors tick count"""
            # Call original
            result = original_on_tick(tick, symbol)
            
            # Track progress
            hook_self.tick_count += 1
            
            # Log progress every 100 ticks
            if hook_self.tick_count % 100 == 0:
                elapsed = (datetime.now() - hook_self.start_time).total_seconds()
                tps = hook_self.tick_count / elapsed if elapsed > 0 else 0
                logger.info(f"📊 Progress: {hook_self.tick_count}/{hook_self.config.target_ticks} ticks "
                          f"({tps:.1f} ticks/sec)")
            
            # Generate report when target reached (but DON'T stop - robustness priority)
            if hook_self.tick_count >= hook_self.config.target_ticks and not hook_self.test_complete:
                hook_self.test_complete = True
                logger.info(f"🎯 Target reached: {hook_self.tick_count} ticks collected")
                logger.info("📊 Generating performance report (stream continues running)...")
                
                # Generate reports only - DO NOT STOP
                if hook_self.config.generate_report:
                    hook_self._generate_reports()
                
                logger.info("✅ Report complete - stream still active for robustness")
                logger.info("⚠️  To stop: User must click 'Stop Forward Test' and confirm")
            
            return result
        
        # Replace callback - this will be set as broker.on_tick_callback in trader.start()
        trader._on_tick_direct = instrumented_on_tick
        logger.info("✓ WebSocket direct callback wrapped for progress monitoring")
    
    def _generate_reports(self):
        """Generate performance test reports"""
        logger.info("\n" + "="*80)
        logger.info("📊 PERFORMANCE TEST COMPLETE")
        logger.info("="*80)
        
        elapsed = (datetime.now() - self.start_time).total_seconds()
        tps = self.tick_count / elapsed if elapsed > 0 else 0
        
        logger.info(f"Ticks Processed: {self.tick_count}")
        logger.info(f"Time Elapsed: {elapsed:.2f}s")
        logger.info(f"Throughput: {tps:.1f} ticks/sec")
        
        # Pre-convergence report
        if self.pre_instrumentor:
            logger.info("\n--- PRE-CONVERGENCE METRICS ---")
            report = self.pre_instrumentor.get_report()
            self._log_report(report)
        
        # Post-convergence report
        if self.post_instrumentor:
            logger.info("\n--- POST-CONVERGENCE METRICS ---")
            report = self.post_instrumentor.get_baseline_report()
            self._log_report(report)
        
        logger.info("="*80 + "\n")
    
    def _log_report(self, report: Dict[str, Any]):
        """Log performance report metrics"""
        if not report:
            logger.warning("No report data available")
            return
        
        for key, value in report.items():
            if isinstance(value, dict):
                logger.info(f"{key}:")
                for sub_key, sub_value in value.items():
                    logger.info(f"  {sub_key}: {sub_value}")
            else:
                logger.info(f"{key}: {value}")


# Global singleton for easy access
_global_hook: Optional[PerformanceTestHook] = None


def get_performance_hook() -> PerformanceTestHook:
    """Get or create global performance test hook"""
    global _global_hook
    if _global_hook is None:
        _global_hook = PerformanceTestHook()
    return _global_hook


def enable_performance_testing(target_ticks: int = 1000, **kwargs):
    """
    Convenience function to enable performance testing
    
    Args:
        target_ticks: Number of ticks to collect
        **kwargs: Additional config options
    """
    hook = get_performance_hook()
    hook.enable_testing(target_ticks=target_ticks, **kwargs)
    return hook
