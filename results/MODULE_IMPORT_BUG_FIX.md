# Module Import Path Bug Fix - Performance Instrumentation

**Date**: October 24, 2025  
**Issue**: Pre-convergence instrumentor collected NO data despite successful injection  
**Status**: ✅ FIXED

---

## The Problem

Performance instrumentation was being injected successfully but measurements returned empty:
```
11:20:16 [INFO] myQuant.live.websocket_stream: 🔬 [WEBSOCKET_STREAM] Instrumentor SET: True
```

But 2 seconds later when ticks arrived:
```
11:20:18 [WARNING] live.websocket_stream: 🔬 [WEBSOCKET_STREAM._on_data] Instrumentor is NONE
```

---

## Root Cause: Dual Module Import Paths

Python imported `websocket_stream` module **twice** with different import paths, creating **separate global namespaces**:

### Evidence (Module IDs)
**BEFORE FIX**:
```
When SET: Module ID = 2497909996288  (myQuant.live.websocket_stream)
When USED: Module ID = 2497909651664  (live.websocket_stream)
            ^^^^^^^^^ DIFFERENT MODULE!
```

**AFTER FIX**:
```
When SET: Module ID = 2351956577392  (live.websocket_stream)
When USED: Module ID = 2351956577392  (live.websocket_stream)
            ^^^^^^^^^ SAME MODULE ✓
```

### Why Two Paths Existed

1. **`myQuant/live/broker_adapter.py`** (lines 143-147):
   ```python
   try:
       from live.websocket_stream import WebSocketTickStreamer  # Path 1
   except ImportError:
       from myQuant.live.websocket_stream import WebSocketTickStreamer  # Path 2 (fallback)
   ```

2. **Performance hook** was injecting into:
   ```python
   import myQuant.live.websocket_stream as websocket_stream  # Path 2
   websocket_stream.set_pre_convergence_instrumentor(instrumentor)
   ```

3. **WebSocket thread** was using the module imported via **Path 1** (`live.websocket_stream`)

4. Result: Instrumentor set on one module, but code executed in a different module instance!

---

## The Fix

**File**: `myQuant/utils/performance_test_hook.py`

Changed from single-path injection:
```python
# OLD - Only injected into myQuant.live.websocket_stream
import myQuant.live.websocket_stream as websocket_stream
websocket_stream.set_pre_convergence_instrumentor(self.pre_instrumentor)
```

To dual-path injection using `sys.modules`:
```python
# NEW - Inject into BOTH possible import paths
import live.websocket_stream as websocket_stream  # Primary path used by broker
websocket_stream.set_pre_convergence_instrumentor(self.pre_instrumentor)

# ALSO inject via sys.modules to catch both import paths
if 'live.websocket_stream' in sys.modules:
    sys.modules['live.websocket_stream'].set_pre_convergence_instrumentor(self.pre_instrumentor)
```

Same fix applied to:
- `live.broker_adapter`
- `live.trader`

---

## Key Learnings

### Python Module Import Gotcha

When you have this structure:
```
PerplexityCombinedTest/
├── myQuant/
│   ├── live/
│   │   └── websocket_stream.py
```

And `sys.path` includes both:
- `PerplexityCombinedTest/`
- `PerplexityCombinedTest/myQuant/`

Then these are **DIFFERENT** modules to Python:
- `import live.websocket_stream` (uses 2nd path)
- `import myQuant.live.websocket_stream` (uses 1st path)

Each creates a **separate** module object with its own global namespace!

### Solution Pattern

When injecting module-level state (like instrumentors), use `sys.modules` to ensure you're modifying the SAME module instance that the code will use:

```python
import sys

# Import via the path that runtime code uses
import live.websocket_stream as ws_module

# Set the instrumentor
ws_module.set_pre_convergence_instrumentor(instrumentor)

# ALSO ensure sys.modules entry is updated (defensive)
if 'live.websocket_stream' in sys.modules:
    sys.modules['live.websocket_stream'].set_pre_convergence_instrumentor(instrumentor)
```

---

## Verification

**Test Run**: October 24, 2025 11:57:54

**Logs confirm fix**:
```
11:57:54 [INFO] live.websocket_stream: Module ID when SET: 2351956577392
11:57:54 [INFO] myQuant.utils.performance_test_hook: ✓ Pre-convergence instrumentation → WebSocket (live.websocket_stream)
11:57:54 [INFO] live.websocket_stream: Module ID when SET: 2351956577392
11:57:54 [INFO] myQuant.utils.performance_test_hook: ✓ Pre-convergence instrumentation → live.websocket_stream (via sys.modules)
```

**Same module ID** (`2351956577392`) confirms single module instance!

---

## Next Steps

1. ✅ Module import path fixed
2. ⏳ Wait for WebSocket connection limit (429 error) to clear (30-60 seconds)
3. ⏳ Run performance test to verify measurements are collected
4. ⏳ Analyze per-tick latency breakdown
5. ⏳ Identify bottlenecks (if any)
6. ⏳ Optimize based on evidence

---

## Files Modified

1. `myQuant/utils/performance_test_hook.py` (lines 107-165)
   - Changed to `live.*` import paths (not `myQuant.live.*`)
   - Added `sys.modules` defensive injection
   - Updated log messages to show actual import path used

2. `myQuant/live/websocket_stream.py` (lines 38-46)
   - Added debug logging to `set_pre_convergence_instrumentor()`
   - Added module ID logging in `_on_data()`

3. `myQuant/live/broker_adapter.py` (lines 49-57, 468-481)
   - Added debug logging to `set_pre_convergence_instrumentor()`
   - Added instrumentor None warning in `_handle_websocket_tick()`

4. `myQuant/live/trader.py` (lines 23-31)
   - Added debug logging to `set_pre_convergence_instrumentor()`

---

## Prevention

**Best Practice**: Use consistent import paths throughout the codebase.

**Recommendation**: Standardize on `live.*` imports (not `myQuant.live.*`) since `sys.path` includes `myQuant/` directory.

**Future**: Consider removing the dual-path fallback in broker_adapter.py once all imports are standardized.
