# Pre-Convergence Latency Analysis: Live WebSocket Workflow

**Date**: October 22, 2025  
**Focus**: WebSocket tick arrival → `strategy.on_tick()` convergence point  
**Goal**: Identify optimization opportunities BEFORE strategy processing

---

## 🔍 Live WebSocket Workflow Breakdown

### Path: SmartAPI → WebSocket → Broker Adapter → Callback → Strategy

```
[Network] → [JSON Parse] → [Dict Creation] → [Logging] → [Queue] → [Callback] → [Strategy]
   ↓            ↓              ↓                ↓          ↓          ↓            ↓
  ???         ~0.1ms         ~0.05ms          ~0.5ms?    ~0.2ms?   ~0.05ms    [MEASURED: 2.8ms]
```

---

## 📊 Step-by-Step Latency Analysis

### **Step 1: SmartAPI WebSocket → `_on_data()` handler**
**Location**: `websocket_stream.py:104-143`

```python
def _on_data(self, ws, message):
    # 1. JSON parsing (if string)
    if isinstance(message, str):
        data = json.loads(message)  # POTENTIAL BOTTLENECK #1
    else:
        data = message
    
    # 2. Timestamp creation
    ts = datetime.now(IST)  # POTENTIAL BOTTLENECK #2
    
    # 3. Data extraction with .get() calls
    raw_price = data.get("ltp", data.get("last_traded_price", 0))
    
    # 4. Price conversion (float division)
    actual_price = float(raw_price) / 100.0
    
    # 5. Dict creation
    tick = {
        "timestamp": ts,
        "price": actual_price,
        "volume": int(data.get("volume", 0)),
        "symbol": data.get("tradingsymbol", data.get("symbol", "")),
        "exchange": data.get("exchange", ""),
        "raw": data  # STORES ENTIRE RAW MESSAGE
    }
    
    # 6. Price validation with logging
    if tick['price'] > 5000:
        logger.warning(...)  # CONDITIONAL LOGGING (only on anomalies)
    elif tick['price'] < 0.01:
        logger.warning(...)
    
    # 7. Callback invocation
    if self.on_tick:
        self.on_tick(tick, tick['symbol'])
```

**Estimated Latency**: 0.1-0.3ms
- JSON parsing: ~0.05-0.15ms (depends on message size)
- `datetime.now(IST)`: ~0.02-0.05ms
- Dict operations: ~0.02ms
- Conditional logging: 0ms (rarely triggered)

**Optimization Opportunities**:
1. ❓ **JSON parsing**: Is message pre-parsed by SmartAPI library?
2. ⚠️ **`raw: data`**: Storing entire raw message increases memory, potential GC pressure
3. ⚠️ **Nested `.get()` calls**: `data.get("ltp", data.get(...)` does TWO lookups on miss

---

### **Step 2: Broker Adapter → `_handle_websocket_tick()`**
**Location**: `broker_adapter.py:436-491`

```python
def _handle_websocket_tick(self, tick, symbol):
    # 1. Counter initialization check (only first tick)
    if not hasattr(self, '_broker_tick_count'):
        self._broker_tick_count = 0
        logger.info(...)  # ONE-TIME COST
    
    self._broker_tick_count += 1
    
    # 2. Conditional logging (every 100 ticks)
    if self._broker_tick_count == 1 or self._broker_tick_count % 100 == 0:
        logger.info(...)  # ONLY 1% OF TICKS
    
    # 3. Timestamp check and addition
    if 'timestamp' not in tick:
        tick['timestamp'] = pd.Timestamp.now(tz=IST)  # POTENTIAL BOTTLENECK #3
    
    # 4. State updates (atomic, no lock)
    self.last_price = float(tick.get('price', tick.get('ltp', 0)))
    self.last_tick_time = pd.Timestamp.now(tz=IST)  # DUPLICATE TIMESTAMP CALL
    
    # 5. CSV logging (buffered I/O)
    self._log_tick_to_csv(tick, symbol)  # POTENTIAL BOTTLENECK #4
    
    # 6. Direct callback (if registered)
    if self.on_tick_callback:
        if self._broker_tick_count == 1 or self._broker_tick_count % 100 == 0:
            logger.info(...)  # CONDITIONAL
        try:
            self.on_tick_callback(tick, symbol)  # → TRADER
        except Exception as e:
            logger.error(...)
    
    # 7. Queue buffering (ALWAYS happens, even with callback)
    try:
        self.tick_buffer.put_nowait(tick)  # POTENTIAL BOTTLENECK #5
    except queue.Full:
        self.tick_buffer.get_nowait()
        self.tick_buffer.put_nowait(tick)
```

**Estimated Latency**: 0.5-1.0ms
- Counter/logging: ~0.01ms (99% of ticks skip logging)
- Timestamp operations: ~0.05-0.1ms (TWO `pd.Timestamp.now()` calls!)
- CSV logging: ~0.3-0.5ms (buffered, but still I/O)
- Queue operations: ~0.1-0.2ms (put_nowait + potential get_nowait)
- Callback invocation: ~0.02ms

**Optimization Opportunities**:
1. 🚨 **DUPLICATE TIMESTAMP**: Two `pd.Timestamp.now(tz=IST)` calls (~0.05ms each)
2. 🚨 **CSV LOGGING**: Happens on EVERY tick (~0.3-0.5ms) - Phase 1 showed 0% because file simulation bypasses this
3. 🚨 **REDUNDANT QUEUE**: Queue operations happen even when using direct callback (unnecessary)
4. ⚠️ **Nested `.get()` fallback**: `tick.get('price', tick.get('ltp', 0))` does two lookups

---

### **Step 3: CSV Logging → `_log_tick_to_csv()`**
**Location**: `broker_adapter.py:493-512`

```python
def _log_tick_to_csv(self, tick, symbol):
    if self.tick_logging_enabled and self.tick_writer:
        try:
            # Extract data
            timestamp = tick.get('timestamp', datetime.now())
            price = tick.get('price', tick.get('ltp', 0))
            volume = tick.get('volume', 0)
            
            # Write row (buffered, but still blocking call)
            self.tick_writer.writerow([timestamp, price, volume, symbol])
```

**Estimated Latency**: 0.3-0.5ms
- Dict lookups: ~0.02ms
- CSV writerow (buffered): ~0.3-0.5ms

**Why Phase 1 Didn't Catch This**:
- File simulation bypasses `broker_adapter.py` entirely
- Goes directly: `DataSimulator.get_next_tick()` → `strategy.on_tick()`
- NO CSV logging in file simulation path

**Optimization Opportunities**:
1. 🚨 **BLOCKING I/O**: Even buffered, `writerow()` is synchronous
2. 🔥 **HIGH FREQUENCY**: Happens on EVERY tick (could be 100+ ticks/sec in live)
3. ⚠️ **Phase 3 candidate**: Should use ring buffer or async logging

---

### **Step 4: LiveTrader → `_on_tick_direct()`**
**Location**: `trader.py:450-500`

```python
def _on_tick_direct(self, tick, symbol):
    # Counter and logging (similar overhead as broker)
    if not hasattr(self, '_callback_tick_count'):
        self._callback_tick_count = 0
        logger.info(...)
    
    self._callback_tick_count += 1
    
    if self._callback_tick_count == 1 or self._callback_tick_count % 100 == 0:
        logger.info(...)
    
    # Timestamp check AGAIN
    if 'timestamp' not in tick:
        tick['timestamp'] = now_ist()  # THIRD TIMESTAMP CALL?
    
    now = tick['timestamp']
    
    # Update last price
    self.last_price = tick.get('price', tick.get('ltp', None))
    
    # Session check
    if hasattr(self.strategy, "should_exit_for_session"):
        if self.strategy.should_exit_for_session(now):
            self.close_position("Session End")
            return
    
    # Strategy call
    signal = self.strategy.on_tick(tick)
```

**Estimated Latency**: 0.1-0.2ms
- Counter/logging: ~0.01ms
- Timestamp check: ~0.02ms (likely no-op if already set)
- Session check: ~0.05ms
- Callback invocation: ~0.02ms

**Optimization Opportunities**:
1. ⚠️ **REDUNDANT SESSION CHECK**: Called on every tick, but only needed near session end
2. ⚠️ **Third timestamp check**: Defensive but likely unnecessary

---

## 🔥 Critical Findings: Hidden Latency Sources

### ❌ **Issue #1: CSV Logging NOT Measured in Phase 1**

**Problem**: Phase 1 baseline used file simulation which bypasses `broker_adapter.py`
- File simulation: `DataSimulator` → `strategy.on_tick()` (direct path)
- Live WebSocket: `WebSocket` → `broker_adapter._handle_websocket_tick()` → CSV logging → callback → `strategy.on_tick()`

**Impact**: CSV logging happens on EVERY live tick but was NOT included in baseline measurements!

**Estimated Hidden Latency**: 0.3-0.5ms per tick (30-50% overhead if strategy is 2.8ms)

---

### ❌ **Issue #2: Duplicate Timestamp Calls**

**Problem**: Multiple `pd.Timestamp.now(tz=IST)` / `datetime.now(IST)` calls in single tick path:
1. `websocket_stream._on_data()`: `ts = datetime.now(IST)` ✅ (needed)
2. `broker_adapter._handle_websocket_tick()`: Check `'timestamp' not in tick` (should be no-op)
3. `broker_adapter._handle_websocket_tick()`: `self.last_tick_time = pd.Timestamp.now(tz=IST)` ❌ (duplicate!)
4. `trader._on_tick_direct()`: Check `'timestamp' not in tick` again (redundant)

**Impact**: 2-3 unnecessary timestamp calls at ~0.05ms each = 0.1-0.15ms wasted

**Fix**: Reuse timestamp from step 1, eliminate redundant calls

---

### ❌ **Issue #3: Redundant Queue Operations**

**Problem**: Even when using direct callback mode, ticks are STILL added to `tick_buffer` queue:
```python
# After calling callback, STILL does this:
self.tick_buffer.put_nowait(tick)
```

**Impact**: Unnecessary queue overhead (~0.1-0.2ms) when using direct callbacks

**Fix**: Skip queue operations when `on_tick_callback` is registered

---

### ❌ **Issue #4: Nested `.get()` Fallbacks**

**Problem**: Multiple places do nested `.get()` calls:
```python
raw_price = data.get("ltp", data.get("last_traded_price", 0))  # Two lookups
price = tick.get('price', tick.get('ltp', 0))  # Two lookups
```

**Impact**: Minor (~0.01-0.02ms per occurrence), but happens 3+ times per tick

**Fix**: Single lookup with explicit fallback logic

---

### ⚠️ **Issue #5: Storing Raw Message Data**

**Problem**: WebSocket handler stores entire raw message:
```python
tick = {
    "timestamp": ts,
    "price": actual_price,
    "volume": int(data.get("volume", 0)),
    "symbol": data.get("tradingsymbol", data.get("symbol", "")),
    "exchange": data.get("exchange", ""),
    "raw": data  # ← ENTIRE RAW MESSAGE
}
```

**Impact**: 
- Increased memory per tick (could be 2-10KB per tick)
- More GC pressure at high frequencies
- Slower dict copying/passing

**Fix**: Remove `"raw": data` unless debugging mode enabled

---

## 📊 Estimated Total Pre-Convergence Latency

| Component | Estimated Latency | % of Total (if 3.5ms total) |
|-----------|-------------------|------------------------------|
| JSON parsing | 0.05-0.15ms | 1-4% |
| Timestamp calls (duplicate) | 0.1-0.15ms | 3-4% |
| **CSV logging** | **0.3-0.5ms** | **9-14%** 🚨 |
| Queue operations | 0.1-0.2ms | 3-6% |
| Dict operations | 0.05-0.1ms | 1-3% |
| Callback overhead | 0.05ms | 1-2% |
| Logging (conditional) | 0.01ms | <1% |
| **SUBTOTAL** | **0.66-1.15ms** | **19-33%** |

**Strategy processing**: 2.8ms (measured in Phase 1)  
**Expected total live latency**: 3.5-4.0ms per tick

---

## 🎯 Optimization Priorities (Evidence-Driven)

### **Priority 1: Measure Actual Live WebSocket Latency** 🔥
**Action**: Add instrumentation to `websocket_stream._on_data()` and `broker_adapter._handle_websocket_tick()`
**Reason**: Phase 1 didn't measure pre-convergence latency because it used file simulation
**Expected finding**: CSV logging will show 20-40% of pre-convergence time

### **Priority 2: CSV Logging Optimization** (if >30% of pre-convergence)
**Fix**: Implement async CSV logging or ring buffer (Phase 3 candidate)
**Impact**: Could reduce pre-convergence latency from ~1ms to ~0.5ms

### **Priority 3: Eliminate Duplicate Timestamps**
**Fix**: Pass timestamp from `_on_data()`, eliminate redundant `pd.Timestamp.now()` calls
**Impact**: Save ~0.1-0.15ms per tick

### **Priority 4: Skip Queue When Using Direct Callback**
**Fix**: Conditional queue operations only if no callback registered
**Impact**: Save ~0.1-0.2ms per tick in callback mode

### **Priority 5: Remove Raw Message Storage** (unless debugging)
**Fix**: Add `debug_mode` flag, only store `"raw": data` when debugging
**Impact**: Reduce memory, less GC pressure, faster dict operations

---

## 🚀 Next Steps

1. **Create Phase 1.5: Pre-Convergence Baseline**
   - Add instrumentation to `websocket_stream.py` and `broker_adapter.py`
   - Measure with LIVE WebSocket data (not file simulation)
   - Capture component breakdown BEFORE `strategy.on_tick()`

2. **Validate CSV Logging Impact**
   - Compare live WebSocket latency with/without CSV logging
   - Confirm if it exceeds 30% threshold for Phase 3 optimization

3. **Quick Wins (Low-Hanging Fruit)**
   - Remove duplicate timestamp calls
   - Skip queue operations in direct callback mode
   - Remove raw message storage in production mode

4. **Decision Gate**
   - If CSV logging >30%: Implement Phase 3 (Ring Buffer)
   - If total pre-convergence <1ms: Skip optimizations, proceed to Phase 6

---

## 📋 Summary

**Critical Discovery**: Phase 1 baseline measured ONLY post-convergence (strategy processing), NOT the live WebSocket path before convergence.

**Hidden Latency Sources**:
1. 🚨 CSV logging: ~0.3-0.5ms per tick (NOT measured in Phase 1)
2. 🚨 Duplicate timestamps: ~0.1-0.15ms per tick
3. ⚠️ Redundant queue operations: ~0.1-0.2ms per tick
4. ⚠️ Nested `.get()` calls: ~0.02-0.04ms per tick

**Estimated Total Pre-Convergence**: 0.66-1.15ms (19-33% overhead on top of strategy)

**Recommendation**: Implement Phase 1.5 to measure actual live WebSocket latency before deciding on optimization phases.
