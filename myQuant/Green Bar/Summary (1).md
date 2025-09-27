
## Summary

The error you're encountering is due to missing methods in the `ModularIntradayStrategy` class in `researchStrategy.py`. The class is trying to call `_update_green_bars_count` and `_check_consecutive_green_bars` methods that don't exist.

### The Problem:

- The `researchStrategy.py` file is missing two critical methods that are referenced in the code
- These methods exist in `liveStrategy.py` but were not copied over to `researchStrategy.py`
- The methods are needed for the "consecutive green bars" feature


### The Solution:

I've created two files to help you fix this issue:

1. **`fix-missing-methods.md`**  - Contains detailed manual instructions[^1]
2. **`fix_missing_methods.py`**  - An automated script to apply the fix[^2]

### Quick Fix Steps:

**Option 1: Use the automated script (Recommended)**

```bash
python fix_missing_methods.py
```

**Option 2: Manual fix**

1. Open `core/researchStrategy.py`
2. Add to the `__init__` method (around line 90):
```python
# --- NEW: Consecutive green bars tracking ---
self.green_bars_count = 0
self.last_bar_data = None
```

3. Add these two methods at the end of the class:
```python
def _check_consecutive_green_bars(self) -> bool:
    """Check if we have enough consecutive green bars for re-entry."""
    if self.green_bars_count >= self.consecutive_green_bars_required:
        return True
    else:
        return False

def _update_green_bars_count(self, row: pd.Series):
    """Update the count of consecutive green bars based on current bar data."""
    try:
        current_close = row.get('close', 0)
        current_open = row.get('open', current_close)
        
        if current_open == current_close and self.last_bar_data is not None:
            current_open = self.last_bar_data.get('close', current_close)
        
        is_green_bar = current_close > current_open
        
        if is_green_bar:
            self.green_bars_count += 1
        else:
            self.green_bars_count = 0
        
        self.last_bar_data = {
            'open': current_open,
            'close': current_close,
            'timestamp': row.name if hasattr(row, 'name') else None
        }
    except Exception as e:
        logger.warning(f"Error updating green bars count: {e}")
```

4. Update the `reset()` method to include:
```python
self.green_bars_count = 0
self.last_bar_data = None
```

After applying this fix, your backtest should run without the missing method errors and potentially generate trading signals.

<div style="text-align: center">⁂</div>

[^1]: backtest_runner.py

[^2]: results.py

[^3]: defaults.py

[^4]: indicators.py

[^5]: liveStrategy.py

[^6]: position_manager.py

[^7]: researchStrategy.py

[^8]: unified_gui.py

[^9]: broker_adapter.py

[^10]: login.py

[^11]: trader.py

[^12]: websocket_stream.py

[^13]: cache_manager.py

[^14]: config_helper.py

[^15]: config_loader.py

[^16]: logger_setup.py

[^17]: logging_utils.py

[^18]: simple_loader.py

[^19]: time_utils.py

[^20]: https://ppl-ai-code-interpreter-files.s3.amazonaws.com/web/direct-files/b40afca340e52bdf75d2565e55f5a8a9/2949b9ae-81d3-45a4-aa51-34d7077427ce/e4ee2b1b.md

[^21]: https://ppl-ai-code-interpreter-files.s3.amazonaws.com/web/direct-files/b40afca340e52bdf75d2565e55f5a8a9/a9142276-1542-4e72-b5fa-ac0f854e0a03/8d240c33.py

