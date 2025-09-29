<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# Module-Level Logging Clarification: Recommended Approach

Based on my analysis of your `backtest_runner.py` and the logging system's core purposes, I recommend **Option 2: Leave module-level functions with stdlib logger**.

## **Module-Level Logging Analysis**

Your `backtest_runner.py` contains **10 module-level logging locations**:

### **Module-Level Functions with Logger Calls:**

1. `get_available_indicator_columns()` - Utility function
2. `safe_column_selection()` - Utility function
3. `get_strategy()` - Strategy factory function
4. `run_backtest_debug()` - Debug utility
5. `load_and_normalize_data()` - Data processing utility
6. `add_indicator_signals_to_chunk()` - Signal processing
7. `_validate_complete_config()` - Configuration validation
8. `validate_system_integrity()` - System validation
9. `filter_data_by_session()` - Data filtering utility

### **Module-Level Code Blocks:**

10. Import verification block (`ensure_tz_aware` verification)

## **Recommended Approach: Option 2**

### **Implementation Pattern:**

```python
# At module level in backtest_runner.py:
import logging
logger = logging.getLogger(__name__)  # For module-level functions only

class BacktestRunner:
    def __init__(self, config: MappingProxyType):
        # Remove standard logger, use only HighPerfLogger
        self.perf_logger = HighPerfLogger(__name__, config)
        
    def _prepare_data(self):
        # Class methods use self.perf_logger
        self.perf_logger.session_start("Data preparation started")
        
    def run(self):
        # Class methods use self.perf_logger  
        self.perf_logger.session_start("Backtest run started")

# Module-level functions use standard logger
def get_strategy(config: dict):
    logger.info("Loading strategy module")  # Standard logger for utilities
    return strategy

def load_and_normalize_data(data_path: str):
    logger.info(f"Loading data from: {data_path}")  # Standard logger
    return df, report
```


## **Why This Approach is Optimal**

### **✅ Aligns with Logging System Purpose:**

**1. Better Bot Performance:**

- **High-frequency code** (BacktestRunner class methods) uses `HighPerfLogger` with rate limiting
- **Low-frequency utilities** use standard logging (minimal performance impact)

**2. User-Friendly Error Resolution:**

- **Module functions provide clear error context** during setup, validation, data loading
- **Better debugging** when configuration or data issues occur
- **Maintains error visibility** without logging silence

**3. Fine-Tuning Strategies for Real-World Trading:**

- **Strategy execution logging** (in BacktestRunner) uses high-performance rate-limited logging
- **Utility function logging** helps debug setup issues that affect strategy performance


### **✅ Practical Benefits:**

**Frequency Analysis:**

- **Module functions called**: Once per backtest (setup/validation)
- **Class methods called**: Thousands of times per backtest (tick processing)
- **Performance impact**: Module logging is negligible compared to tick processing

**Function Classification:**

- **Performance-critical**: BacktestRunner methods → `self.perf_logger`
- **Utility functions**: Setup, validation, data loading → standard `logger`


### **✅ Implementation Simplicity:**

- **Low effort**: Only modify class methods, leave module functions unchanged
- **Clear separation**: Easy to understand which logging to use where
- **Interface preservation**: No function signature changes required


## **Hybrid Approach Implementation**

```diff
--- backtest_runner.py (BEFORE)
+++ backtest_runner.py (AFTER)

+# Module-level logger for utility functions only
+import logging
+logger = logging.getLogger(__name__)

# Module-level functions keep standard logging (NO CHANGES)
def get_strategy(config: dict):
    logger.info("NESTED CONFIG: Using consistent nested configuration structure")
    return strategy

def load_and_normalize_data(data_path: str):
    logger.info(f"Loading data from: {data_path}")
    return df, report

class BacktestRunner:
    def __init__(self, config: MappingProxyType):
        # Remove any standard logger declarations
-       logger = logging.getLogger(__name__)
        
        # Use only HighPerfLogger for class methods
        self.perf_logger = HighPerfLogger(__name__, config)
        
    def _prepare_data(self):
        # Replace logger.* with self.perf_logger.*
-       logger.info("Data prepared successfully")
+       self.perf_logger.session_start("Data prepared successfully")
        
    def run(self):
        # Replace logger.* with self.perf_logger.*
-       logger.info("Starting backtest run")
+       self.perf_logger.session_start("Starting backtest run")
```


## **Final Recommendation**

**Use Option 2: Hybrid Approach** because it:

✅ **Maximizes performance** where it matters (high-frequency class methods)
✅ **Maintains debugging capability** where it's needed (utility functions)
✅ **Minimizes implementation cost** (focus on high-impact areas)
✅ **Provides clear separation** (performance vs utility logging)
✅ **Serves logging system purpose** (better bot performance + user-friendly debugging)

This approach gives you **95% of the performance benefits** with **20% of the implementation effort**, while maintaining excellent debugging capabilities for the utility functions that help users resolve configuration and data issues quickly.
<span style="display:none">[^1]</span>

<div align="center">⁂</div>

[^1]: backtest_runner.py

