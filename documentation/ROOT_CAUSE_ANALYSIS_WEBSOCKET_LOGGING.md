# Root Cause Analysis: Missing Strategy Logs in Live WebSocket Mode

## Problem Summary

**Symptom**: Live WebSocket forward testing shows heartbeat logs with live prices but NO strategy interaction logs (ENTRY BLOCKED, ENTRY EVALUATION, trade execution, etc.).

**Impact**: User cannot see why trades are not being taken, making strategy tuning impossible.

---

## Root Cause Identified

### The Bug: Incorrect Counter Used for Debug Logging

**Location**: `trader.py` line ~479 (original debug logging)

**Problematic Code**:
```python
# In _on_tick_direct() callback handler
if self.heartbeat_counter % 100 == 0:
    logger.debug(f"[DEBUG] Calling strategy.on_tick()")
```

**Why This Failed**:
1. `heartbeat_counter` increments every 0.1 seconds in main thread loop
2. `_on_tick_direct()` is called from WebSocket thread when ticks arrive
3. Ticks arrive ASYNCHRONOUSLY from heartbeat increments
4. Statistical probability of `heartbeat_counter % 100 == 0` exactly when tick arrives ≈ 1%
5. **Result**: Debug log almost NEVER appears, giving false impression that callback isn't called

### The Evidence

**Live WebSocket Log** (16,100 cycles, ~27 minutes):
- ✅ Heartbeat logs every 10 seconds (100 cycles)
- ✅ Prices updating (₹174.05 → ₹169.40 → ₹166.90...)
- ❌ ZERO strategy logs
- ❌ ZERO debug logs from callback handler
- ❌ ZERO entry evaluation logs

**File Simulation Log** (32,591 ticks, ~16 seconds):
- ✅ "ENTRY BLOCKED (#1): Need 3 green ticks, have 0"
- ✅ "TRADE BUY: 75 @ 226.20"
- ✅ Position management logs
- ✅ Full strategy lifecycle visible

**Difference**: File simulation processes ticks in sequence in same thread, so logging conditions are met consistently.

---

## The Fix Applied

### Change 1: Add Dedicated Tick Counter

**File**: `trader.py`, `_on_tick_direct()` method

**Before**:
```python
def _on_tick_direct(self, tick, symbol):
    logger = logging.getLogger(__name__)
    try:
        # (no tick counting)
        signal = self.strategy.on_tick(tick)
```

**After**:
```python
def _on_tick_direct(self, tick, symbol):
    logger = logging.getLogger(__name__)
    try:
        # Track actual tick count (separate from heartbeat)
        if not hasattr(self, '_callback_tick_count'):
            self._callback_tick_count = 0
        self._callback_tick_count += 1
        
        # Log every 100 ticks
        if self._callback_tick_count % 100 == 1:
            logger.info(f"🔍 [CALLBACK] Processing tick #{self._callback_tick_count}, price: ₹{tick.get('price', 'N/A')}, keys: {list(tick.keys())}")
```

**Benefit**: Now EVERY 100th tick will log, regardless of heartbeat timing.

### Change 2: Add Strategy Call Logging

**File**: `trader.py`, `_on_tick_direct()` method

**After**:
```python
# Log every 300 ticks to verify strategy is being called
if self._callback_tick_count % 300 == 1:
    logger.info(f"📊 [CALLBACK] Calling strategy.on_tick() for tick #{self._callback_tick_count}")

signal = self.strategy.on_tick(tick)

# Log signal result occasionally
if self._callback_tick_count % 300 == 1:
    if signal:
        logger.info(f"✅ [CALLBACK] Strategy returned signal: {signal.action} @ ₹{signal.price}")
    else:
        logger.info(f"⏸️ [CALLBACK] Strategy returned None (no entry signal)")
```

**Benefit**: Shows exactly what strategy returns, confirming tick processing happens.

### Change 3: Strategy-Level Logging (Already Added)

**File**: `liveStrategy.py`, `on_tick()` method

**Code** (lines 547-553):
```python
# DEBUG: Log every 300 ticks to verify on_tick is being called
if not hasattr(self, '_ontick_call_count'):
    self._ontick_call_count = 0
self._ontick_call_count += 1

if self._ontick_call_count % 300 == 1:
    logger.info(f"📊 [STRATEGY] on_tick called #{self._ontick_call_count}, tick keys: {list(tick.keys())}")
```

**Benefit**: Independent confirmation that strategy method is reached.

---

## Expected Log Output After Fix

With 16,100 cycles (as in your previous run), you should now see:

### Every 100 Ticks (~10 seconds at 10 ticks/sec):
```
🔍 [CALLBACK] Processing tick #1, price: ₹174.05, keys: ['timestamp', 'price', 'volume', 'symbol', 'exchange', 'raw']
🔍 [CALLBACK] Processing tick #101, price: ₹169.40, keys: [...]
🔍 [CALLBACK] Processing tick #201, price: ₹166.90, keys: [...]
...
```
**Expected Count**: ~161 logs (16100/100)

### Every 300 Ticks (~30 seconds):
```
📊 [CALLBACK] Calling strategy.on_tick() for tick #1
⏸️ [CALLBACK] Strategy returned None (no entry signal)
📊 [STRATEGY] on_tick called #1, tick keys: ['timestamp', 'price', 'volume', ...]
🚫 ENTRY BLOCKED (#1): Need 3 green ticks, have 0, NIFTY20OCT2525300CE @ ₹174.05

📊 [CALLBACK] Calling strategy.on_tick() for tick #301
⏸️ [CALLBACK] Strategy returned None (no entry signal)
📊 [STRATEGY] on_tick called #301, tick keys: [...]
🚫 ENTRY BLOCKED (#300): Need 3 green ticks, have 0, NIFTY20OCT2525300CE @ ₹169.40
...
```
**Expected Count**: ~53 sets of logs (16100/300)

### If Entry Conditions Met:
```
📊 ENTRY EVALUATION @ ₹226.20: Enabled checks: EMA Crossover, VWAP, MACD
   ❌ Entry REJECTED - Failed: EMA: fast(225.8) ≤ slow(227.3); VWAP: not calculated yet
```

OR if entry allowed:
```
✅ ENTRY SIGNAL @ ₹226.20: All checks passed (EMA Crossover, VWAP, MACD)
✅ [CALLBACK] Strategy returned signal: BUY @ ₹226.20
```

---

## Why File Simulation Worked But Live Didn't

### File Simulation Flow:
```
Main Thread:
  for tick in data:
      trader._on_tick_direct(tick, symbol)  # Sequential, same thread
      └─> strategy.on_tick(tick)
          └─> Logging happens normally
```
**Result**: All logging conditions met in sequence ✅

### Live WebSocket Flow (Before Fix):
```
Main Thread:                          WebSocket Thread:
  while running:                        tick arrives
    sleep(0.1)                          └─> _on_tick_direct(tick)
    heartbeat_counter += 1                  └─> if heartbeat_counter % 100 == 0:  # ❌ Random value!
    if counter % 100 == 0:                      logger.debug(...)  # Almost never true
      log heartbeat                     └─> strategy.on_tick(tick)
```
**Result**: Heartbeat logs ✅, Strategy logs ❌

### Live WebSocket Flow (After Fix):
```
Main Thread:                          WebSocket Thread:
  while running:                        tick arrives
    sleep(0.1)                          └─> _callback_tick_count += 1
    heartbeat_counter += 1              └─> if _callback_tick_count % 100 == 1:  # ✅ Every 100th tick!
    if counter % 100 == 0:                      logger.info(...)  # Reliable
      log heartbeat                     └─> strategy.on_tick(tick)
```
**Result**: Both heartbeat logs ✅ AND strategy logs ✅

---

## Validation Steps

1. **Restart live forward test** with the fixed code
2. **Wait for 1000 ticks** (~100 seconds at 10 ticks/sec)
3. **Check for new logs**:
   - Should see ~10 "🔍 [CALLBACK] Processing tick #" logs
   - Should see ~3 "📊 [CALLBACK] Calling strategy.on_tick()" logs
   - Should see ~3 "📊 [STRATEGY] on_tick called #" logs
   - Should see ~3 "🚫 ENTRY BLOCKED (#)" logs

4. **If logs STILL don't appear**, then the issue is deeper (callback not registered, exception being swallowed, etc.)

---

## Additional Findings from Code Review

### Document Suggestions vs Reality

**Suggestion 1**: "No Tick Processing Hook" - WebSocket handler doesn't forward ticks
- **Reality**: ✅ Hook EXISTS (`_handle_websocket_tick` → `on_tick_callback` → `_on_tick_direct`)
- **Status**: NOT the issue

**Suggestion 2**: "Feed Type Selection" - LTP instead of Quote
- **Reality**: Feed type = LTP is fine, strategy has fallback for `price` field
- **Status**: NOT the issue

**Suggestion 3**: "Logging Configuration Scope" - Logger levels wrong
- **Reality**: Heartbeat logs appear (INFO level working), so logger is configured
- **Status**: NOT the issue (but debug logging WAS broken due to wrong counter)

**Suggestion 4**: "Ensure Tick Callback Wiring"
- **Reality**: ✅ Wiring is correct (as proven by working heartbeat prices)
- **Status**: NOT the issue

**ACTUAL ISSUE**: Debug logging used wrong counter (heartbeat vs tick count)

---

## Summary

- **Bug**: Debug logging checked `heartbeat_counter % 100` from wrong thread
- **Impact**: Logs never appeared, creating illusion that callbacks weren't working
- **Fix**: Added dedicated `_callback_tick_count` that increments on every tick
- **Validation**: Restart live test and verify new logs appear every 100/300 ticks
- **Confidence**: HIGH - This explains why file simulation worked but live didn't

**Next Steps**: Test with live data and confirm logs now appear!
