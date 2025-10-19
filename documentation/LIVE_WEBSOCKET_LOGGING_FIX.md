# Live WebSocket Strategy Logging Investigation

## Problem Identified

**User Report**: Live WebSocket mode shows NO strategy interaction logging, while file simulation shows rich logging including:
- "ENTRY BLOCKED (#1): Need 3 green ticks, have 0"
- Trade executions
- Position management updates

**Root Cause Analysis**: The strategy logging exists but is not appearing in live WebSocket mode, suggesting either:
1. `strategy.on_tick()` is not being called
2. Ticks are malformed/missing required fields
3. Exceptions are being silently swallowed
4. Logging frequency settings prevent output

## Changes Applied

### 1. Added Debug Logging in `trader.py` (Line ~479)

**Purpose**: Verify if `strategy.on_tick()` is actually being called from the callback handler.

```python
# DEBUG: Log every 100 ticks to verify strategy is being called
if self.heartbeat_counter % 100 == 0:
    logger.debug(f"[DEBUG] Calling strategy.on_tick() with tick: {tick.keys()}")
```

**Expected Output**: Every 100 cycles (every ~10 seconds), should log:
```
[DEBUG] Calling strategy.on_tick() with tick: dict_keys(['price', 'timestamp', 'ltp', ...])
```

### 2. Enhanced Logging in `liveStrategy.py` `on_tick()` Method (Lines ~547-560)

**Purpose**: Track strategy execution and catch any silent failures.

```python
# DEBUG: Log every 300 ticks to verify on_tick is being called
if not hasattr(self, '_ontick_call_count'):
    self._ontick_call_count = 0
self._ontick_call_count += 1

if self._ontick_call_count % 300 == 1:
    logger.info(f"📊 [STRATEGY] on_tick called #{self._ontick_call_count}, tick keys: {list(tick.keys())}")
```

**Expected Output**: Every 300 calls (~30 seconds), should log:
```
📊 [STRATEGY] on_tick called #1, tick keys: ['price', 'timestamp', 'ltp']
📊 [STRATEGY] on_tick called #301, tick keys: ['price', 'timestamp', 'ltp']
...
```

### 3. Added Timestamp Validation Logging (Line ~563)

**Purpose**: Detect if ticks are missing timestamps (which would cause silent returns).

```python
if 'timestamp' not in tick:
    logger.warning(f"⚠️ [STRATEGY] Tick missing timestamp, skipping. Tick keys: {list(tick.keys())}")
    return None
```

**Expected Output** (if timestamp missing):
```
⚠️ [STRATEGY] Tick missing timestamp, skipping. Tick keys: ['price', 'ltp']
```

### 4. Added Exception Logging (Line ~572)

**Purpose**: Make exceptions visible before error handler processes them.

```python
except Exception as e:
    logger.error(f"🔥 [STRATEGY] Exception in on_tick: {type(e).__name__}: {e}", exc_info=True)
    return self.error_handler.handle_error(...)
```

**Expected Output** (if exception occurs):
```
🔥 [STRATEGY] Exception in on_tick: KeyError: 'close'
Traceback...
```

## Existing Logging That Should Be Visible

### From `can_enter_new_position()` (line 235 of liveStrategy.py)
```python
self.perf_logger.entry_blocked(reason_text)  # Logs every 300 blocks
```

**Expected Output**:
```
🚫 ENTRY BLOCKED (#1): Need 3 green ticks, have 0, NIFTY20OCT2525300CE @ ₹174.05
🚫 ENTRY BLOCKED (#300): Need 3 green ticks, have 0, NIFTY20OCT2525300CE @ ₹166.90
```

### From `entry_signal()` (lines 476-479 of liveStrategy.py)
```python
logger.info(f"📊 ENTRY EVALUATION @ ₹{price}: Enabled checks: {', '.join(checks_performed)}")
logger.info(f"   ❌ Entry REJECTED - Failed: {'; '.join(failed_checks)}")
```

**Expected Output** (every 300 ticks or 30 seconds):
```
📊 ENTRY EVALUATION @ ₹174.05: Enabled checks: EMA Crossover, VWAP, MACD
   ❌ Entry REJECTED - Failed: EMA: fast(173.2) ≤ slow(175.8); VWAP: not calculated yet
```

## Testing Instructions

### Step 1: Restart Live Forward Test
```bash
py -m gui.noCamel1
```

1. Select symbol (e.g., NIFTY20OCT2525300CE)
2. Start Forward Test (Live WebStream mode)
3. Let it run for ~1 minute (600+ cycles)

### Step 2: Check Logs for New Debug Output

**Look for:**
1. `[DEBUG] Calling strategy.on_tick()` - Every 100 cycles
2. `📊 [STRATEGY] on_tick called #` - Every 300 calls
3. `🚫 ENTRY BLOCKED (#)` - Every 300 blocks
4. `📊 ENTRY EVALUATION @` - Every 300 ticks or 30 seconds

**If you DON'T see these logs**, it means:
- `strategy.on_tick()` is not being called at all
- Ticks are not reaching the strategy
- Something is blocking the callback chain

### Step 3: Compare with File Simulation

Run file simulation and verify logs appear normally:
- Select "File Simulation" in GUI
- Choose a CSV file
- Start Forward Test
- Should see all expected logs

## Diagnostic Scenarios

### Scenario A: NO logs appear (not even debug logs)
**Diagnosis**: `strategy.on_tick()` is never being called
**Possible Causes**:
- Callback registration failed
- WebSocket not delivering ticks to callback
- Trader loop not processing ticks

### Scenario B: Debug logs appear, but NO strategy logs
**Diagnosis**: `on_tick()` is called but failing early
**Possible Causes**:
- Exception in `process_tick_or_bar()` being silently caught
- Timestamp missing from ticks
- Error handler suppressing exceptions

### Scenario C: Strategy logs appear but NO entry evaluation logs
**Diagnosis**: Strategy running but not reaching entry checks
**Possible Causes**:
- `can_enter_new_position()` returning False immediately
- Green tick requirement not met
- Session time restrictions

## Next Steps

After testing with new logging:

1. **Share the new log output** - Especially lines containing:
   - `[DEBUG] Calling strategy.on_tick()`
   - `📊 [STRATEGY] on_tick called`
   - `🚫 ENTRY BLOCKED`
   - `⚠️ [STRATEGY] Tick missing timestamp`
   - `🔥 [STRATEGY] Exception`

2. **If no logs appear**: We need to investigate the WebSocket callback registration

3. **If exception logs appear**: We'll fix the specific error

4. **If entry blocked logs appear**: We'll analyze why entry conditions are failing

## File Changes Summary

**Files Modified:**
1. `myQuant/live/trader.py` - Line ~479: Added debug log in callback handler
2. `myQuant/core/liveStrategy.py` - Lines ~547-575: Added comprehensive logging in on_tick()

**No Breaking Changes**: All changes are additive logging only.
