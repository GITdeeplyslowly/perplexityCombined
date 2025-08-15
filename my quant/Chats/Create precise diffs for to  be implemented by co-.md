
# Create precise diffs for to  be implemented by co-pilot in vs code.

Phase 1: Remove Strategy Selection Logic (Week 1)
**Core Changes:**
**Update defaults.py** - Remove strategy\_version parameter
**Hard-code backtest\_runner.py** to use researchStrategy only
**Hard-code live/trader.py** to use liveStrategy only
**Remove GUI selection elements** from unified\_gui.py

I'll create precise diffs for Phase 1 to remove the strategy selection logic. Here are the changes needed:

## 1. Update defaults.py - Remove strategy_version parameter

```diff
--- a/config/defaults.py
+++ b/config/defaults.py
@@ -8,7 +8,6 @@ This file contains all default values used by both GUI and non-GUI components.
 
 DEFAULT_CONFIG = {
     'strategy': {
-        'strategy_version': 'research',
         'use_ema_crossover': True,
         'use_macd': False,
         'use_vwap': False,
```


## 2. Hard-code backtest_runner.py to use researchStrategy only

```diff
--- a/backtest/backtest_runner.py
+++ b/backtest/backtest_runner.py
@@ -78,15 +78,8 @@ def load_config(config_path: str) -> dict:
 def get_strategy(config: dict):
     """
     Load strategy module with full configuration.
-    FIXED: Properly handles GUI's nested config structure
+    Hard-coded to use researchStrategy for backtesting.
     """
-    version = config.get("strategy", {}).get("strategy_version", "live").lower()
-    if version == "research":
-        strat_mod = importlib.import_module("core.researchStrategy")
-    else:
-        strat_mod = importlib.import_module("core.liveStrategy")
-    
+    strat_mod = importlib.import_module("core.researchStrategy")
     ind_mod = importlib.import_module("core.indicators")
 
     # FIXED: Keep nested structure, no more flattening
```


## 3. Hard-code live/trader.py to use liveStrategy only

```diff
--- a/live/trader.py
+++ b/live/trader.py
@@ -18,12 +18,8 @@ def load_config(config_path: str):
     return yaml.safe_load(f)
 
 def get_strategy(params):
-    version = params.get("strategy_version", "live").lower()
-    if version == "research":
-        strat_module = importlib.import_module("core.researchStrategy")
-    else:
-        strat_module = importlib.import_module("core.liveStrategy")
+    strat_module = importlib.import_module("core.liveStrategy")
     ind_mod = importlib.import_module("core.indicators")
     return strat_module.ModularIntradayStrategy(params, ind_mod)
 
 class LiveTrader:
```


## 4. Remove GUI selection elements from unified_gui.py

```diff
--- a/unified_gui.py
+++ b/unified_gui.py
@@ -392,17 +392,6 @@ class UnifiedTradingGUI(tk.Tk):
         
         row += 1
         
-        # --- Strategy version selector ---------------------------------
-        ttk.Label(frame, text="Strategy Version:", font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky="w", padx=5, pady=(10,2))
-        row += 1
-        self.ft_strategy_version = tk.StringVar(value="live") # default for forward test
-        ttk.Combobox(frame,
-                    textvariable=self.ft_strategy_version,
-                    values=["research", "live"],
-                    width=12,
-                    state="readonly").grid(row=row, column=0, sticky="w", padx=5, pady=2)
-        row += 1
-        
         # Strategy Configuration
         ttk.Label(frame, text="Strategy Configuration", font=('Arial', 12, 'bold')).grid(row=row, column=0, columnspan=3, sticky="w", pady=(15,5))
         row += 1
```


## 5. Clean up any remaining strategy_version references in unified_gui.py

```diff
--- a/unified_gui.py
+++ b/unified_gui.py
@@ -681,9 +681,6 @@ class UnifiedTradingGUI(tk.Tk):
         # Update with current GUI values
         # Strategy settings
         config['strategy']['use_ema_crossover'] = self.bt_use_ema_crossover.get()
-        # Remove any strategy_version assignments since it no longer exists
-        # config['strategy']['strategy_version'] = self.bt_strategy_version.get() # REMOVE THIS LINE
-        
         config['strategy']['use_macd'] = self.bt_use_macd.get()
         config['strategy']['use_vwap'] = self.bt_use_vwap.get()
         config['strategy']['use_rsi_filter'] = self.bt_use_rsi_filter.get()
```

These diffs will:

1. **Remove the strategy_version parameter** from the default configuration
2. **Hard-code backtest_runner.py** to always use `core.researchStrategy`
3. **Hard-code live/trader.py** to always use `core.liveStrategy`
4. **Remove the strategy version selector GUI elements** from the forward test tab
5. **Clean up any remaining references** to strategy_version in the GUI code

The changes ensure that:

- Backtests will always use the research strategy
- Live trading will always use the live strategy
- The GUI no longer shows confusing strategy selection options
- The code is simplified and more maintainable

After implementing these changes, you should test that:

1. Backtests still run correctly using the research strategy
2. Live trading functionality works with the live strategy
3. The GUI loads without the strategy selection dropdown
4. All existing functionality remains intact

<div style="text-align: center">⁂</div>

[^1]: cache_manager.py

[^2]: config_helper.py

[^3]: config_loader.py

[^4]: logger_setup.py

[^5]: logging_utils.py

[^6]: simple_loader.py

[^7]: time_utils.py

[^8]: broker_adapter.py

[^9]: login.py

[^10]: trader.py

[^11]: websocket_stream.py

[^12]: unified_gui.py

[^13]: indicators.py

[^14]: liveStrategy.py

[^15]: position_manager.py

[^16]: researchStrategy.py

[^17]: defaults.py

[^18]: backtest_runner.py

[^19]: results.py

