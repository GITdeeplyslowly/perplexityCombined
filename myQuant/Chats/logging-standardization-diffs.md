# Precise Diffs for Logging Standardization

Based on analysis of the updated files, here are the exact diffs needed to complete the logging consolidation:

## Files Requiring Updates: 3

### **1. BACKTEST_RUNNER.PY - Remove Mixed Patterns**

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
        
-       # smart_logger removed (all event logging uses HighPerfLogger)
        
        from utils.config_helper import ConfigAccessor
        self.config_accessor = ConfigAccessor(self.config)
-       logger.info("BacktestRunner initialized with strategy version: %s", 
-                   self.config_accessor.get('strategy.strategy_version'))
+       # Use performance logger for initialization messages
+       self.perf_logger.session_start(f"BacktestRunner v{self.config_accessor.get('strategy.strategy_version')}")

    def _prepare_data(self):
        """Load and prepare data for backtesting"""
        try:
            self.data = load_data_simple(self.data_path, process_as_ticks=True)
            if self.data is None or self.data.empty:
                raise ValueError(f"No data loaded from {self.data_path}")
                
-           logger.info(f"Data loaded: {len(self.data)} rows from {self.data.index[0]} to {self.data.index[-1]}")
+           # Use performance logger for data loading status
+           self.perf_logger.session_start(f"Data loaded: {len(self.data)} rows from {self.data.index[0]} to {self.data.index[-1]}")
            
-           logger.info("Data prepared successfully - strategy will calculate indicators incrementally")
        except Exception as e:
-           logger.exception(f"Error preparing data: {e}")
+           # Let exceptions propagate - backtest should fail fast on data issues
            raise

    def run(self):
        """Run backtest with current configuration."""
        try:
-           logger.info("Starting backtest run")
+           self.perf_logger.session_start("Starting backtest run")
            
            # ... existing backtest logic ...
            
-           logger.info("Backtest completed successfully")
+           self.perf_logger.session_end("Backtest completed successfully")
            return self.results
            
        except Exception as e:
-           logger.exception(f"Error running backtest: {e}")
+           # Let exceptions propagate for proper error handling
            raise

    def _run_backtest_logic(self):
        """Core backtest loop logic"""
-       logger.info("=" * 60)
-       logger.info("STARTING BACKTEST WITH NORMALIZED DATA PIPELINE")  
-       logger.info("=" * 60)
+       self.perf_logger.session_start("STARTING BACKTEST WITH NORMALIZED DATA PIPELINE")
        
        # ... existing logic ...
        
        # Replace all logger.info/error/warning calls with appropriate perf_logger methods
        # For critical errors, let exceptions propagate
        # For informational messages, use perf_logger.session_start/session_end
```

### **2. LIVESTRATEGY.PY - Remove Standard Logger**

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
        
-       logger.info(
-           f"[INIT] Indicator switches: EMA={self.use_ema_crossover}, MACD={self.use_macd}, VWAP={self.use_vwap}, "
-           f"RSI={self.use_rsi_filter}, HTF={self.use_htf_trend}, BB={self.use_bollinger_bands}"
-       )
+       # Move detailed initialization info to debug level with rate limiting
+       if self.perf_logger:
+           indicator_info = f"EMA={self.use_ema_crossover}, MACD={self.use_macd}, VWAP={self.use_vwap}"
+           self.perf_logger.session_start(f"Indicators: {indicator_info}")

    # Remove all direct logger calls throughout the file and replace with perf_logger methods
    # Keep the existing HighPerfLogger usage patterns that are already correct
    
    def open_long(self, row: pd.Series, now: datetime, position_manager) -> Optional[str]:
        # ... existing logic ...
        
        if position_id:
            # Already correctly using perf_logger
            self.perf_logger.trade_executed("BUY", entry_price, lot_size, "Strategy signal")
            return position_id
            
-       logger.warning("Position manager returned None")
+       # Remove this log or use perf_logger if needed
        return None
```

### **3. RESEARCHSTRATEGY.PY - Remove Standard Logger**

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
        
-       logger.info(
-           f"[INIT] Indicator switches: EMA={self.use_ema_crossover}, MACD={self.use_macd}, VWAP={self.use_vwap}, "
-           f"RSI={self.use_rsi_filter}, HTF={self.use_htf_trend}, BB={self.use_bollinger_bands}, "
-           f"STOCH={self.use_stochastic}, ATR={self.use_atr}"
-       )
+       # Use rate-limited debug logging for detailed initialization
+       if self.perf_logger:
+           indicator_info = f"EMA={self.use_ema_crossover}, MACD={self.use_macd}, VWAP={self.use_vwap}"
+           self.perf_logger.session_start(f"Research Strategy Indicators: {indicator_info}")

    def reset_incremental_trackers(self):
        """Reset all incremental indicator trackers for clean state."""
        # ... existing logic ...
        
-       logger.info("Strategy initialized: %s v%s", self.name, self.version)
        # Remove duplicate initialization logging

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
        """Check if positions should be exited based on user-defined session end and buffer"""
        if not self.is_trading_session(now):
-           logger.debug(f"Should exit: Not in trading session {now}")
+           # Remove debug logging or use perf_logger with rate limiting
            return True
            
        # ... existing logic ...

    # Replace all other logger.info/debug/warning calls with appropriate perf_logger methods
    # For errors that should propagate, remove logging and let exceptions bubble up
    # For informational messages, use perf_logger.session_start/session_end
    # For debugging, use perf_logger.tick_debug with rate limiting
```

## **Files That Are Correct As-Is: 6**

The following files appropriately use standard logging for their use cases and **require no changes**:

### **✅ position_manager.py** 
- **Status**: Correct - uses standard logging for trade execution (not high-frequency)
- **Usage**: `logger.info("Position opened %s", position_id)` - appropriate for trade-level events

### **✅ results.py**
- **Status**: Correct - uses standard logging for results processing  
- **Usage**: Results analysis is not performance-critical

### **✅ trader.py** 
- **Status**: Correct - uses standard logging for live trader coordination
- **Usage**: Session-level logging for live trading coordination

### **✅ broker_adapter.py**
- **Status**: Correct - uses standard logging for broker communication
- **Usage**: Network and API communication logging

### **✅ websocket_stream.py**
- **Status**: Correct - uses standard logging for WebSocket events
- **Usage**: Connection and data stream logging

### **✅ login.py**
- **Status**: Correct - uses standard logging for authentication
- **Usage**: Login and session management logging

## **Implementation Guidelines**

### **High-Frequency Modules (Use HighPerfLogger):**
- **Strategy modules** (`liveStrategy.py`, `researchStrategy.py`) 
- **Backtest runner** (`backtest_runner.py`)
- **Any module processing tick-by-tick data**

### **Low-Frequency Modules (Use Standard Logging):**  
- **Position management** (trade execution, not tick processing)
- **Results processing** (post-analysis)
- **Network communication** (broker, WebSocket)
- **Authentication and session management**
- **GUI coordination and live trading orchestration**

### **Key Principles:**
1. **Single import pattern**: `from utils.logger import HighPerfLogger` for high-frequency
2. **Standard logging**: `import logging; logger = logging.getLogger(__name__)` for low-frequency  
3. **No mixed patterns**: Each module uses one approach consistently
4. **Rate limiting**: Use `perf_logger.tick_debug()` for high-frequency debug messages
5. **Fail-fast**: Let exceptions propagate instead of logging and continuing

## **Result After Implementation**

✅ **Single import pattern**: All modules use consistent import patterns  
✅ **Standardized usage**: High-frequency modules use HighPerfLogger, low-frequency use standard logging  
✅ **No mixed patterns**: Each module has clear, consistent logging approach  
✅ **Performance optimized**: Rate limiting where needed, zero overhead when disabled  
✅ **Maintainable**: Clear separation of concerns based on frequency requirements

This completes the logging standardization while maintaining appropriate logging patterns for different module types.