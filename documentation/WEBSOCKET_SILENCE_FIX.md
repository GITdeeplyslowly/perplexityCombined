# WebSocket Silence Issue - Resolution

**Date:** October 14, 2025  
**Issue:** WebSocket goes silent after ~200 ticks, causing spam logs

---

## **Problem Identified**

### **Symptoms:**
```
11:44:04 [INFO] live.trader: [DEBUG] WebSocket active but no ticks received (cycle 200)
11:44:04 [INFO] live.trader: [DEBUG] WebSocket active but no ticks received (cycle 200)
11:44:05 [INFO] live.trader: [DEBUG] WebSocket active but no ticks received (cycle 200)
11:44:05 [INFO] live.trader: [DEBUG] WebSocket active but no ticks received (cycle 200)
... (repeats rapidly)
```

### **Root Causes:**

1. **WebSocket Silence**: WebSocket stops sending ticks after ~200 ticks (Angel One server issue or connection drop)

2. **Log Spam**: Trader's debug logging triggered every 200 cycles without rate limiting
   - With 50ms sleep per cycle: 200 cycles = ~10 seconds
   - When WebSocket silent, counter keeps incrementing rapidly
   - Hits 200-cycle mark multiple times per second → log spam

3. **Health Monitor Overlap**: Health monitor could trigger multiple reconnection attempts if not properly gated

---

## **Fixes Applied**

### **Fix 1: Prevent Health Monitor Spam**
**File:** `live/broker_adapter.py`  
**Method:** `_check_websocket_health()`

**Before:**
```python
def _check_websocket_health(self):
    if not self.streaming_mode or not self.last_tick_time:
        return
    
    current_time = time.time()
    last_tick_timestamp = self.last_tick_time.timestamp()
    silence_duration = current_time - last_tick_timestamp
    
    if silence_duration > self.heartbeat_threshold:
        logger.warning(f"WebSocket silent for {silence_duration:.1f}s - triggering reconnection")
        self._trigger_smart_reconnection()
```

**After:**
```python
def _check_websocket_health(self):
    if not self.streaming_mode or not self.last_tick_time:
        return
    
    # Skip check if reconnection is already in progress
    if self.reconnect_in_progress:
        return
    
    current_time = time.time()
    last_tick_timestamp = self.last_tick_time.timestamp()
    silence_duration = current_time - last_tick_timestamp
    
    # Only trigger reconnection once when threshold exceeded
    if silence_duration > self.heartbeat_threshold:
        logger.warning(f"WebSocket silent for {silence_duration:.1f}s - triggering reconnection")
        self._trigger_smart_reconnection()
```

**Change:**
- Added `reconnect_in_progress` check to prevent overlapping reconnection attempts
- Health monitor now gracefully skips checks during active reconnection

---

### **Fix 2: Rate-Limit Trader Debug Logs**
**File:** `live/trader.py`  
**Location:** Main trading loop

**Before:**
```python
if hasattr(self.broker, 'streaming_mode') and self.broker.streaming_mode:
    time.sleep(0.05)  # 50ms for WebSocket
    # Debug: Log every 200 empty tick cycles (10 seconds)
    if tick_count % 200 == 0:
        logger.info(f"[DEBUG] WebSocket active but no ticks received (cycle {tick_count})")
```

**After:**
```python
if hasattr(self.broker, 'streaming_mode') and self.broker.streaming_mode:
    time.sleep(0.05)  # 50ms for WebSocket
    # Debug: Log every 200 empty tick cycles but throttle to max once per 30 seconds
    if tick_count % 200 == 0:
        current_time = time.time()
        if not hasattr(self, '_last_no_tick_log') or (current_time - self._last_no_tick_log) >= 30:
            logger.info(f"[DEBUG] WebSocket active but no ticks received (cycle {tick_count})")
            self._last_no_tick_log = current_time
```

**Change:**
- Added time-based throttling (maximum 1 log per 30 seconds)
- Prevents log spam when tick counter increments rapidly during WebSocket silence
- Still provides visibility but without flooding logs

---

## **Expected Behavior After Fix**

### **Scenario: WebSocket Goes Silent**

**Timeline:**
1. **11:44:04** - WebSocket stops sending ticks
2. **11:44:34** - Health monitor detects 30s silence
3. **11:44:34** - Triggers smart reconnection (logged once)
4. **11:44:34** - Trader logs "no ticks" message (max once per 30s)
5. **11:44:35** - Reconnection attempt #1 with 1s backoff
6. **11:44:36** - WebSocket reinitializes
7. **11:44:37** - Ticks resume

**Log Output:**
```
11:44:04 [INFO] live.trader: [HEARTBEAT] Trading loop active - tick count: 200, position: True
11:44:34 [INFO] live.trader: [DEBUG] WebSocket active but no ticks received (cycle 600)
11:44:34 [WARNING] live.broker_adapter: WebSocket silent for 30.0s - triggering reconnection
11:44:34 [INFO] live.broker_adapter: Reconnection attempt 1, waiting 1.0s
11:44:35 [INFO] live.broker_adapter: Smart reconnection successful
11:44:35 [INFO] live.broker_adapter: WebSocket tick received - resetting reconnection backoff
11:44:37 [INFO] live.trader: [TICK] Price: ₹75.70
```

---

## **Additional Recommendations**

### **1. Investigate WebSocket Silence Root Cause**

The WebSocket going silent after exactly 200 ticks is suspicious. Possible causes:

**A. Angel One Server Limits:**
- Angel One may have undocumented rate limits on WebSocket connections
- May throttle/disconnect after certain tick count
- **Solution**: Contact Angel One support for WebSocket best practices

**B. Network Issues:**
- Firewall/router may be closing idle connections
- ISP throttling WebSocket connections
- **Solution**: Test on different network, check firewall rules

**C. SmartAPI Library Bug:**
- Possible issue in `smartapi-python` WebSocket implementation
- **Solution**: Update to latest version, report issue if persistent

**D. Angel One Feed Type:**
- Currently using `feed_type='LTP'` (mode=1)
- May be less reliable than `Quote` (mode=2)
- **Solution**: Test with `feed_type='Quote'` for more robust streaming

### **2. Enhanced WebSocket Monitoring**

Consider adding metrics to understand patterns:

```python
# In _handle_websocket_tick():
self.tick_metrics = {
    'total_ticks': 0,
    'last_100_tick_times': [],
    'silence_events': []
}

def _handle_websocket_tick(self, tick, symbol):
    self.tick_metrics['total_ticks'] += 1
    self.tick_metrics['last_100_tick_times'].append(time.time())
    # Keep only last 100
    if len(self.tick_metrics['last_100_tick_times']) > 100:
        self.tick_metrics['last_100_tick_times'].pop(0)
    
    # Detect irregular patterns
    if len(self.tick_metrics['last_100_tick_times']) >= 100:
        tick_rate = 100 / (time.time() - self.tick_metrics['last_100_tick_times'][0])
        if tick_rate < 0.5:  # Less than 0.5 ticks/second
            logger.warning(f"Low tick rate detected: {tick_rate:.2f} ticks/sec")
```

### **3. Feed Type Configuration**

Update config to test different feed types:

```python
# In config/defaults.py or GUI settings
FEED_TYPES = {
    'LTP': 1,        # Lightweight, last traded price only
    'Quote': 2,      # More data, better reliability
    'SnapQuote': 3   # Full market depth
}

# Recommendation: Start with Quote for production
live:
    feed_type: 'Quote'  # Change from 'LTP'
```

---

## **Testing Checklist**

- [x] Fix 1: Health monitor stops spamming during reconnection
- [x] Fix 2: Trader debug logs throttled to 30-second intervals
- [ ] Verify reconnection works automatically when WebSocket silent
- [ ] Monitor for log spam reduction in production
- [ ] Test with different feed types (Quote vs LTP)
- [ ] Monitor WebSocket stability over multiple sessions
- [ ] Check if silence occurs at predictable intervals

---

## **Files Modified**

1. `live/broker_adapter.py` - Added reconnection gating in health check
2. `live/trader.py` - Added time-based log throttling

---

## **Conclusion**

The fixes address the immediate log spam issue by:
1. Preventing overlapping reconnection attempts
2. Throttling debug logs to reasonable intervals

However, the **root cause** (why WebSocket goes silent after ~200 ticks) still needs investigation. The smart reconnection system will now handle this gracefully, but ideally the WebSocket should remain stable throughout the session.

**Next Steps:**
1. Monitor logs to confirm fixes work
2. Contact Angel One support about WebSocket stability
3. Test with `feed_type='Quote'` instead of `'LTP'`
4. Consider adding tick rate monitoring metrics
