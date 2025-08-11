

# Create the diffs to apply solution 1, to be applied through co-pilot in vs code.

Based on the previous conversation history, I can see that the issue is with hardcoded logging that tries to access the `vwap` column when VWAP is disabled in your configuration. Here are the exact diffs for **Solution 1 (Dynamic Column Detection)** to be applied through VS Code Copilot:

## Diff 1: Add the dynamic column detection function

```diff
@@ -25,6 +25,19 @@
 
 logger = logging.getLogger(__name__)
 
+def get_available_indicator_columns(df, max_columns=6):
+    """Get available indicator columns for logging in priority order"""
+    priority_order = ['close', 'fast_ema', 'slow_ema', 'vwap', 'macd', 'rsi', 'htf_ema', 'atr', 'volume']
+    available = [col for col in priority_order if col in df.columns]
+    return available[:max_columns]
+
+def safe_column_selection(df, desired_columns):
+    """Return only columns that actually exist in the DataFrame"""
+    return [col for col in desired_columns if col in df.columns]
+
 try:
 # Verify the function exists and comes from time_utils
 assert callable(ensure_tz_aware)
```


## Diff 2: Fix the problematic logging section (around line 260)

```diff
@@ -257,8 +270,10 @@
     
     # Log final indicator status for verification
     logger.info("Indicators calculated. Final 5 rows:")
-    if 'fast_ema' in df_with_indicators.columns and 'slow_ema' in df_with_indicators.columns:
-        logger.info(f"\n{df_with_indicators[['close', 'fast_ema', 'slow_ema', 'vwap']].tail(5).to_string()}")
+    # Dynamically build column list based on what's available
+    log_columns = get_available_indicator_columns(df_with_indicators)
+    if len(log_columns) > 1:  # More than just 'close'
+        logger.info(f"\n{df_with_indicators[log_columns].tail(5).to_string()}")
     else:
         logger.info(f"\n{df_with_indicators[['close', 'volume']].tail(5).to_string()}")
```


## Diff 3: Add safe logging for EMA diagnostic section (around line 268)

```diff
@@ -268,7 +283,8 @@
     # Quick EMA diagnostic
     if 'fast_ema' in df_with_indicators.columns:
         fast_above_slow = (df_with_indicators['fast_ema'] > df_with_indicators['slow_ema']).sum()
         total_rows = len(df_with_indicators)
         logger.info(f"EMA DIAGNOSTIC: {fast_above_slow} out of {total_rows} rows have fast > slow ({fast_above_slow/total_rows*100:.1f}%)")
         
-        # Show a sample of EMA values
-        sample = df_with_indicators[['fast_ema', 'slow_ema']].dropna().head(10)
+        # Show a sample of available indicator values
+        available_for_sample = safe_column_selection(df_with_indicators, ['fast_ema', 'slow_ema', 'vwap', 'macd'])
+        sample = df_with_indicators[available_for_sample].dropna().head(10)
         logger.info(f"Sample EMA values:\n{sample.to_string()}")
```


## Diff 4: Fix the fallback logging section (around line 275)

```diff
@@ -275,7 +291,8 @@
         logger.info(f"Sample EMA values:\n{sample.to_string()}")
 
     else:
-        logger.info(f"\n{df_with_indicators[['close', 'volume']].tail(5).to_string()}")
+        # Use safe column selection for fallback logging
+        fallback_columns = safe_column_selection(df_with_indicators, ['close', 'volume'])
+        logger.info(f"\n{df_with_indicators[fallback_columns].tail(5).to_string()}")
```


## Summary

These diffs implement **Solution 1 (Dynamic Column Detection)** which:

✅ **Adds a robust `get_available_indicator_columns()` function** that automatically detects which indicators are present
✅ **Replaces hardcoded column lists** with dynamic detection
✅ **Provides fallback logic** when no indicators are available
✅ **Maintains logging quality** while preventing crashes
✅ **Future-proofs** the code against configuration changes

After applying these diffs, your backtest will:

- ✅ Complete successfully with only enabled indicators
- ✅ Show appropriate logging based on what's actually calculated
- ✅ Never crash due to missing VWAP or other disabled indicators
- ✅ Automatically adapt when you enable/disable different indicators

Apply these diffs in sequence through VS Code Copilot, and your backtest should run without the KeyError for missing `vwap` column.

<div style="text-align: center">⁂</div>

[^1]: backtest_runner.py

[^2]: strategy_config.yaml

[^3]: indicators.py

[^4]: position_manager.py

[^5]: researchStrategy.py

[^6]: unified_gui.py

[^7]: cache_manager.py

[^8]: config_helper.py

[^9]: config_loader.py

[^10]: logging_utils.py

[^11]: simple_loader.py

[^12]: time_utils.py

