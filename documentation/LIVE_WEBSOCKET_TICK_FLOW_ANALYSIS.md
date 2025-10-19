# Live WebSocket Tick Flow Analysis

## The Mystery

**Observation**: Live WebSocket shows NO strategy logs despite:
- ✅ WebSocket connected successfully
- ✅ Callback mode enabled
- ✅ Heartbeat showing live prices (₹174.05 → ₹162.90, etc.)
- ✅ 16,100+ cycles processed

**Expected but Missing Logs**:
```
📊 [STRATEGY] on_tick called #1, tick keys: [...]  # Every 300 ticks
🚫 ENTRY BLOCKED (#1): Need 3 green ticks...  # Every 300 blocks
📊 ENTRY EVALUATION @ ₹174.05: Enabled checks...  # Every 300 ticks or 30s
```

---

## The Tick Flow Chain

### Normal Flow (File Simulation - WORKING):
```
1. DataSimulator.get_next_tick()
   └─> Returns: {'timestamp': ..., 'price': 226.20, 'volume': 1000}

2. trader._on_tick_direct(tick, symbol)
   └─> Line 481: signal = self.strategy.on_tick(tick)

3. liveStrategy.on_tick(tick)
   └─> Line 552: logger.info(f"📊 [STRATEGY] on_tick called #{count}")
   └─> Line 557: tick_series = pd.Series(tick)
   └─> Line 560: updated_tick = self.process_tick_or_bar(tick_series)
   └─> Line 568: return self._generate_signal_from_tick(...)

4. liveStrategy._generate_signal_from_tick(...)
   └─> Line 580: if self.can_enter_new_position(timestamp):
       └─> Line 235: self.perf_logger.entry_blocked(reason)  # ✅ LOGS APPEAR

5. Results: Full strategy logs visible ✅
```

### Live WebSocket Flow (BROKEN):
```
1. WebSocket delivers tick
   └─> websocket_stream._on_data(ws, message)
       └─> Line 126: tick = {'timestamp': ts, 'price': actual_price, ...}
       └─> Line 141: self.on_tick(tick, tick['symbol'])

2. broker_adapter._handle_websocket_tick(tick, symbol)
   └─> Line 403: if self.on_tick_callback:
       └─> Line 405: self.on_tick_callback(tick, symbol)  # Calls trader._on_tick_direct

3. trader._on_tick_direct(tick, symbol)
   └─> Line 479: logger.debug(f"[DEBUG] Calling strategy.on_tick()")  # 🔍 CHECK IF THIS APPEARS
   └─> Line 481: signal = self.strategy.on_tick(tick)  # 🔍 CHECK IF THIS IS REACHED

4. liveStrategy.on_tick(tick)
   └─> Line 552: logger.info(f"📊 [STRATEGY] on_tick called")  # 🚫 NEVER APPEARS
   
5. Results: NO strategy logs ❌
```

---

## Hypothesis Testing

### Hypothesis A: callback is never called
**Test**: Add log at broker_adapter.py line 403
```python
if self.on_tick_callback:
    logger.info(f"🔍 [BROKER] Calling on_tick_callback with tick keys: {list(tick.keys())}")
    try:
        self.on_tick_callback(tick, symbol)
```

**Expected**: If this log appears, callback IS being called

### Hypothesis B: _on_tick_direct never reached
**Test**: Check trader.py line 479 debug log
```python
if self.heartbeat_counter % 100 == 0:
    logger.debug(f"[DEBUG] Calling strategy.on_tick() with tick: {tick.keys()}")
```

**Expected**: Should see `[DEBUG]` log every 100 cycles

### Hypothesis C: strategy.on_tick() crashes immediately
**Test**: Check trader.py line 487-493 exception handler
```python
except Exception as e:
    self.nan_streak += 1
    logger.warning(f"Tick processing failed (streak: {self.nan_streak}/{self.nan_threshold}): {e}")
```

**Expected**: If exception, should see "Tick processing failed" warnings

### Hypothesis D: on_tick() called but logging level wrong
**Test**: Check if logger.info() is working at all
```python
# At start of on_tick in liveStrategy.py
logger.critical("🚨 STRATEGY ON_TICK CALLED - THIS IS A TEST")  # Can't be missed
```

**Expected**: Should see CRITICAL log regardless of log level

---

## Most Likely Root Cause

Based on code analysis, **Hypothesis B** is most likely:

### The Heartbeat Counter Issue

In `trader.py` line 479:
```python
if self.heartbeat_counter % 100 == 0:
    logger.debug(f"[DEBUG] Calling strategy.on_tick()")
```

**BUT**: `self.heartbeat_counter` is only incremented in the heartbeat loop (line 322-333), NOT in the callback handler!

Look at `_run_callback_loop()` line 322-333:
```python
while self.is_running:
    time.sleep(0.1)
    self.heartbeat_counter = self.heartbeat_counter + 1 if hasattr(self, 'heartbeat_counter') else 1
    
    if self.heartbeat_counter % 100 == 0:
        position_status = "True" if self.active_position_id else "False"
        price_str = f"₹{self.last_price:.2f}" if self.last_price else "N/A"
        logger.info(f"[HEARTBEAT] Callback mode - {self.heartbeat_counter} cycles, position: {position_status}, price: {price_str}")
```

So:
- ✅ Heartbeat increments counter every 0.1 seconds
- ✅ Heartbeat logs every 100 increments
- ❌ **BUT `_on_tick_direct()` never checks/uses heartbeat_counter for its debug log!**

**The debug log at line 479 will NEVER appear** because when `_on_tick_direct()` is called (from WebSocket thread), `heartbeat_counter` might be at ANY value, and the `% 100 == 0` check will almost never be true at the exact moment a tick arrives!

---

## The Fix

### Option 1: Use tick counter instead of heartbeat counter

In `trader.py` `_on_tick_direct()`:
```python
def _on_tick_direct(self, tick, symbol):
    logger = logging.getLogger(__name__)
    
    try:
        # Track tick count (separate from heartbeat)
        if not hasattr(self, '_tick_count'):
            self._tick_count = 0
        self._tick_count += 1
        
        # Log every 100 ticks
        if self._tick_count % 100 == 0:
            logger.info(f"🔍 [CALLBACK] Processing tick #{self._tick_count}, price: {tick.get('price', 'N/A')}")
```

### Option 2: Add logging directly in strategy call

```python
# BEFORE calling strategy
logger.info(f"🔍 [CALLBACK] About to call strategy.on_tick(), tick keys: {list(tick.keys())}")

signal = self.strategy.on_tick(tick)

# AFTER calling strategy
if signal:
    logger.info(f"✅ [CALLBACK] Strategy returned signal: {signal.action}")
else:
    # Only log occasionally to avoid spam
    if self._tick_count % 300 == 1:
        logger.info(f"⏸️ [CALLBACK] Strategy returned None (no signal)")
```

---

## Immediate Action Items

1. **Add tick counter** in `_on_tick_direct()` to track actual ticks processed
2. **Add logging BEFORE `strategy.on_tick()` call** to prove it's being reached
3. **Test with logging level = DEBUG** to ensure debug logs appear
4. **Check if WebSocket ticks have correct structure** (timestamp, price, volume)

---

## Summary

**Root Cause**: The debug logging added to `_on_tick_direct()` uses `self.heartbeat_counter % 100 == 0`, but heartbeat counter increments independently of ticks. The log check will statistically almost never be true when a tick arrives.

**Evidence**: 
- Heartbeat shows 16,100 cycles in ~27 minutes = 10 cycles/second
- But WebSocket delivers ticks asynchronously from different thread
- Chance of `heartbeat_counter % 100 == 0` exactly when tick arrives ≈ 1%

**Solution**: Add separate `_tick_count` counter that increments on EVERY tick, not on heartbeat timer.
