<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# Precise Diffs for Logging Standardization

After analyzing your updated files, I've identified exactly **3 files** that need logging standardization and **6 files** that are already correctly implemented. Here are the precise diffs:

## **Files Requiring Updates: 3**

### **1. BACKTEST_RUNNER.PY - Remove Mixed Patterns**

**Issues Found**: Mixed imports (both HighPerfLogger and smart_logger), standard logger declaration

```diff
--- backtest_runner.py (BEFORE)
+++ backtest_runner.py (AFTER)

# Remove old imports completely
-from utils.smart_logger import create_smart_logger

# Keep only new high-performance imports  
 from utils.logger import setup_from_config, HighPerfLogger

# Remove standard logger declaration
-logger = logging.getLogger(__name__)

class BacktestRunner:
    def __init__(self, config: MappingProxyType, data_path: str = ""):
        # ... existing validation code ...
        
        # Initialize logging from frozen config (idempotent)
        setup_from_config(self.config)
        
-       # Module logger
-       logger = logging.getLogger(__name__)
-       globals()['logger'] = logger
        
        # High-performance logger for backtest events
        self.perf_logger = HighPerfLogger(__name__, self.config)
        
        from utils.config_helper import ConfigAccessor
        self.config_accessor = ConfigAccessor(self.config)
+       # Use performance logger for initialization messages
+       self.perf_logger.session_start(f"BacktestRunner initialized")

    def _prepare_data(self):
        """Load and prepare data for backtesting"""
        try:
            self.data = load_data_simple(self.data_path, process_as_ticks=True)
            if self.data is None or self.data.empty:
                raise ValueError(f"No data loaded from {self.data_path}")
                
-           logger.info(f"Data loaded: {len(self.data)} rows")
+           self.perf_logger.session_start(f"Data loaded: {len(self.data)} rows")
            
        except Exception as e:
-           logger.exception(f"Error preparing data: {e}")
+           # Let exceptions propagate for proper error handling
            raise

    def run(self):
        """Run backtest with current configuration."""
        try:
-           logger.info("Starting backtest run")
+           self.perf_logger.session_start("Starting backtest run")
            
            # ... existing logic ...
            
-           logger.info("Backtest completed successfully")
+           self.perf_logger.session_end("Backtest completed successfully")
            return self.results
            
        except Exception as e:
-           logger.exception(f"Error running backtest: {e}")
            raise
```


### **2. LIVESTRATEGY.PY - Remove Standard Logger**

**Issues Found**: Mixed HighPerfLogger (correct) with standard logger (remove)

```diff
--- liveStrategy.py (BEFORE)  
+++ liveStrategy.py (AFTER)

 from utils.logger import HighPerfLogger, increment_tick_counter, get_tick_counter, format_tick_message

# Remove standard logger completely
-logger = logging.getLogger(__name__)

class ModularIntradayStrategy:
    def __init__(self, config: MappingProxyType, indicators_module=None):
        self.config = config
        
        # Use high-performance logger (already correctly initialized)
        self.perf_logger = HighPerfLogger(__name__, config)
        
        # ... existing initialization code ...
        
-       logger.info(f"Strategy initialized: {self.name} v{self.version}")
+       self.perf_logger.session_start(f"Strategy initialized: {self.name} v{self.version}")

    def open_long(self, row: pd.Series, now: datetime, position_manager) -> Optional[str]:
        # ... existing logic ...
        
        if position_id:
            # Already correctly using perf_logger
            self.perf_logger.trade_executed("BUY", entry_price, lot_size, "Strategy signal")
            return position_id
            
-       logger.warning("Position manager returned None")
        return None
```


### **3. RESEARCHSTRATEGY.PY - Remove Standard Logger**

**Issues Found**: Mixed HighPerfLogger (correct) with standard logger (remove)

```diff  
--- researchStrategy.py (BEFORE)
+++ researchStrategy.py (AFTER)

 from utils.logger import HighPerfLogger, increment_tick_counter, get_tick_counter, format_tick_message

# Remove standard logger completely
-logger = logging.getLogger(__name__)

class ModularIntradayStrategy:
    def __init__(self, frozen_config: MappingProxyType):
        self.config = frozen_config
        
        # Use high-performance logger (already correctly initialized)
        self.perf_logger = HighPerfLogger(__name__, frozen_config)
        
        # ... existing initialization code ...
        
-       logger.info("Strategy initialized: %s v%s", self.name, self.version)
+       self.perf_logger.session_start(f"Strategy initialized: {self.name} v{self.version}")

    def calculate_indicators(self, df):
        """TRUE INCREMENTAL PROCESSING: Process data row-by-row to mirror real-time trading."""
-       logger.info("=== STARTING TRUE INCREMENTAL PROCESSING ===")
-       logger.info(f"Processing {len(df)} rows incrementally (row-by-row)")
+       self.perf_logger.session_start(f"Incremental processing: {len(df)} rows")
        
        # ... existing processing logic ...
        
-       logger.info(f"=== INCREMENTAL PROCESSING COMPLETE: {rows_processed} rows ===")
+       self.perf_logger.session_end(f"Incremental processing complete: {rows_processed} rows")
        return df

    def should_exit_for_session(self, now: datetime) -> bool:
        """Check if positions should be exited based on session end"""
        if not self.is_trading_session(now):
-           logger.debug(f"Should exit: Not in trading session {now}")
            return True
```


## **✅ Files Correct As-Is: 6**

These files appropriately use standard logging for their use cases and **require no changes**:

- **`position_manager.py`** - Correct use of standard logging for trade execution
- **`results.py`** - Correct use for results processing
- **`trader.py`** - Correct use for live trader coordination
- **`broker_adapter.py`** - Correct use for broker communication
- **`websocket_stream.py`** - Correct use for WebSocket events
- **`login.py`** - Correct use for authentication


## **Implementation Summary**

### **Module Classification**

- **High-Frequency (HighPerfLogger)**: Strategy modules, backtest runner, tick processing
- **Low-Frequency (Standard Logging)**: Position management, results, network, authentication


### **Result After Implementation**

✅ **Single import pattern**: All modules use consistent patterns
✅ **Standardized usage**: Clear separation by frequency requirements
✅ **No mixed patterns**: Each module uses one approach consistently
✅ **Performance optimized**: Zero overhead when logging disabled

This completes the logging standardization with **minimal changes** to just 3 files while maintaining appropriate logging patterns for all module types. The consolidation achieves your goals of eliminating mixed patterns and ensuring consistent, high-performance logging throughout the system.
<span style="display:none">[^1][^10][^2][^3][^4][^5][^6][^7][^8][^9]</span>

<div align="center">⁂</div>

[^1]: position_manager.py

[^2]: backtest_runner.py

[^3]: liveStrategy.py

[^4]: researchStrategy.py

[^5]: trader.py

[^6]: broker_adapter.py

[^7]: websocket_stream.py

[^8]: login.py

[^9]: results.py

[^10]: https://ppl-ai-code-interpreter-files.s3.amazonaws.com/web/direct-files/e0365d991f9b75567b0b52a8d20235bc/48068a31-10d0-4b84-9a01-cf8768103ea3/1832a7e8.md

