# Enhanced Debug Logging for WebSocket Tick Flow

## Changes Applied

### 1. broker_adapter.py - WebSocket Tick Reception Logging

**Location**: `_handle_websocket_tick()` method (lines ~385-410)

**Purpose**: Track if WebSocket is delivering ticks to broker_adapter

**Code Added**:
```python
# Track tick reception
if not hasattr(self, '_broker_tick_count'):
    self._broker_tick_count = 0
self._broker_tick_count += 1

# Log every 100 ticks
if self._broker_tick_count % 100 == 1:
    logger.info(f"🌐 [BROKER] WebSocket tick #{self._broker_tick_count} received, price: ₹{tick.get('price', 'N/A')}")

# Check if callback is registered
if self.on_tick_callback:
    if self._broker_tick_count % 100 == 1:
        logger.info(f"🔗 [BROKER] Calling on_tick_callback for tick #{self._broker_tick_count}")
    try:
        self.on_tick_callback(tick, symbol)
    except Exception as e:
        logger.error(f"🔥 [BROKER] Error in tick callback: {type(e).__name__}: {e}", exc_info=True)
else:
    if self._broker_tick_count % 100 == 1:
        logger.warning(f"⚠️ [BROKER] on_tick_callback is None! Callback not registered!")
```

### 2. trader.py - Callback Processing Logging

**Location**: `_on_tick_direct()` method (lines ~463-470)

**Purpose**: Track if trader is receiving callbacks from broker

**Code Added**:
```python
# Track actual tick count (separate from heartbeat)
if not hasattr(self, '_callback_tick_count'):
    self._callback_tick_count = 0
self._callback_tick_count += 1

# Log every 100 ticks
if self._callback_tick_count % 100 == 1:
    logger.info(f"🔍 [CALLBACK] Processing tick #{self._callback_tick_count}, price: ₹{tick.get('price', 'N/A')}, keys: {list(tick.keys())}")
```

### 3. trader.py - Strategy Call Logging

**Location**: `_on_tick_direct()` method (lines ~488-498)

**Purpose**: Confirm strategy.on_tick() is being called and track results

**Code Added**:
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

### 4. liveStrategy.py - Strategy Execution Logging

**Location**: `on_tick()` method (lines ~547-553)

**Purpose**: Confirm strategy method is reached and processing ticks

**Code Already Added**:
```python
# DEBUG: Log every 300 ticks to verify on_tick is being called
if not hasattr(self, '_ontick_call_count'):
    self._ontick_call_count = 0
self._ontick_call_count += 1

if self._ontick_call_count % 300 == 1:
    logger.info(f"📊 [STRATEGY] on_tick called #{self._ontick_call_count}, tick keys: {list(tick.keys())}")
```

---

## Expected Log Outputs

### Scenario A: WebSocket NOT Delivering Ticks
**Would see**:
- ✅ Heartbeat logs (showing system is running)
- ❌ NO "🌐 [BROKER] WebSocket tick #1 received"

**Diagnosis**: WebSocket connection established but not delivering data
**Fix**: Check WebSocket subscription, feed type, or SmartAPI issues

---

### Scenario B: Callback NOT Registered
**Would see**:
- ✅ Heartbeat logs
- ✅ "🌐 [BROKER] WebSocket tick #1 received"
- ❌ "⚠️ [BROKER] on_tick_callback is None! Callback not registered!"
- ❌ NO "🔍 [CALLBACK] Processing tick"

**Diagnosis**: `self.broker.on_tick_callback` not set in trader.start()
**Fix**: Check `self.use_direct_callbacks` is True before broker.connect()

---

### Scenario C: Callback Crashing
**Would see**:
- ✅ Heartbeat logs
- ✅ "🌐 [BROKER] WebSocket tick #1 received"
- ✅ "🔗 [BROKER] Calling on_tick_callback"
- ❌ "🔥 [BROKER] Error in tick callback: TypeError: ..."
- ❌ NO "🔍 [CALLBACK] Processing tick"

**Diagnosis**: Exception in `_on_tick_direct()` before logging
**Fix**: Check tick structure, timestamp handling, or data types

---

### Scenario D: Strategy NOT Called
**Would see**:
- ✅ Heartbeat logs
- ✅ "🌐 [BROKER] WebSocket tick #1 received"
- ✅ "🔗 [BROKER] Calling on_tick_callback"
- ✅ "🔍 [CALLBACK] Processing tick #1"
- ❌ NO "📊 [CALLBACK] Calling strategy.on_tick()"
- ❌ NO "📊 [STRATEGY] on_tick called"

**Diagnosis**: Code path in `_on_tick_direct()` returning early or exception before strategy call
**Fix**: Check session time check, timestamp handling, or early returns

---

### Scenario E: Everything Working ✅
**Would see**:
```
[HEARTBEAT] Callback mode - 100 cycles, position: False, price: ₹154.45
🌐 [BROKER] WebSocket tick #1 received, price: ₹154.45
🔗 [BROKER] Calling on_tick_callback for tick #1
🔍 [CALLBACK] Processing tick #1, price: ₹154.45, keys: ['timestamp', 'price', 'volume', 'symbol', 'exchange', 'raw']

[HEARTBEAT] Callback mode - 200 cycles, position: False, price: ₹156.00
🌐 [BROKER] WebSocket tick #101 received, price: ₹156.00
🔗 [BROKER] Calling on_tick_callback for tick #101
🔍 [CALLBACK] Processing tick #101, price: ₹156.00, keys: [...]

[HEARTBEAT] Callback mode - 300 cycles, position: False, price: ₹155.90
🌐 [BROKER] WebSocket tick #201 received, price: ₹155.90
🔗 [BROKER] Calling on_tick_callback for tick #201
🔍 [CALLBACK] Processing tick #201, price: ₹155.90, keys: [...]
📊 [CALLBACK] Calling strategy.on_tick() for tick #301
📊 [STRATEGY] on_tick called #301, tick keys: ['timestamp', 'price', 'volume', ...]
🚫 ENTRY BLOCKED (#300): Need 3 green ticks, have 0, NIFTY20OCT2525300CE @ ₹155.90
⏸️ [CALLBACK] Strategy returned None (no entry signal)
```

---

## Diagnostic Flow Chart

```
Start Forward Test
    ↓
Check: Do HEARTBEAT logs appear?
    NO → System not running (check GUI/start button)
    YES ↓
        
Check: Do "🌐 [BROKER] WebSocket tick" logs appear?
    NO → WebSocket not delivering ticks
         → Scenario A (WebSocket delivery issue)
    YES ↓
        
Check: Do "🔗 [BROKER] Calling on_tick_callback" logs appear?
    NO → See "⚠️ [BROKER] on_tick_callback is None"
         → Scenario B (Callback not registered)
    YES ↓
        
Check: Do "🔍 [CALLBACK] Processing tick" logs appear?
    NO → Exception in callback before logging
         → Scenario C (Callback crashing)
    YES ↓
        
Check: Do "📊 [CALLBACK] Calling strategy.on_tick()" logs appear?
    NO → Early return in _on_tick_direct()
         → Scenario D (Code path issue)
    YES ↓
        
Check: Do "📊 [STRATEGY] on_tick called" logs appear?
    NO → Exception in strategy.on_tick()
         → Check error logs for exceptions
    YES ↓
        
Check: Do "🚫 ENTRY BLOCKED" logs appear?
    NO → Strategy skipping entry checks
         → Check can_enter_new_position() logic
    YES ↓
        
✅ FULL TICK FLOW WORKING
Strategy is processing ticks correctly!
```

---

## Next Steps

**After restarting the forward test**:

1. **Wait 1 minute** (~1000 ticks at 10 ticks/second)

2. **Look for these specific logs** in sequence:
   - "🌐 [BROKER] WebSocket tick #1"
   - "🔗 [BROKER] Calling on_tick_callback"
   - "🔍 [CALLBACK] Processing tick #1"
   - "📊 [CALLBACK] Calling strategy.on_tick()"
   - "📊 [STRATEGY] on_tick called #1"
   - "🚫 ENTRY BLOCKED (#1)"

3. **Identify which log is missing** to determine the exact break point

4. **Share the first 50 lines of logs** after "Forward test initiated" to see the flow

---

## Critical Questions These Logs Will Answer

1. **Is WebSocket delivering ticks?** → Check for "🌐 [BROKER]" logs
2. **Is callback registered?** → Check for "🔗 [BROKER]" or "⚠️ on_tick_callback is None"
3. **Is trader receiving callbacks?** → Check for "🔍 [CALLBACK]" logs
4. **Is strategy being called?** → Check for "📊 [CALLBACK/STRATEGY]" logs
5. **Is strategy evaluating entry?** → Check for "🚫 ENTRY BLOCKED" logs

**Every log has a specific emoji to make it easy to scan visually!**
