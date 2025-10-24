"""
PERFORMANCE TESTING VIA GUI WORKFLOW

Summary: Route performance testing through the GUI's established workflow instead
of creating parallel authentication/configuration paths.

================================================================================
PROBLEM WITH OLD APPROACH (scripts/test_live_performance.py)
================================================================================

The old test script created a PARALLEL workflow:
- ❌ Separate authentication path
- ❌ Separate config building
- ❌ Separate trader instantiation
- ❌ Bypassed GUI validation
- ❌ Different credential loading
- ❌ No token handling (caused WebSocket failures)

Result: Tests a synthetic workflow, not the actual production workflow.

================================================================================
NEW APPROACH: HOOK INTO GUI WORKFLOW
================================================================================

Implementation:
1. **Performance Test Hook** (myQuant/utils/performance_test_hook.py)
   - Singleton hook that can be enabled before GUI launch
   - Automatically injects instrumentation when GUI creates trader
   - Monitors tick progress and auto-stops at target
   - Generates reports when complete

2. **GUI Integration** (myQuant/gui/noCamel1.py)
   - Checks for enabled performance hook when creating LiveTrader
   - Calls hook.inject_into_trader(trader) if enabled
   - Hook wraps tick callback to monitor progress
   - No changes to GUI's normal workflow

3. **Test Scripts**
   - test_live_via_gui.py: Manual mode (user clicks "Start Forward Test")
   - test_live_programmatic.py: Automated mode (auto-configures GUI)

================================================================================
HOW IT WORKS
================================================================================

┌─────────────────────────────────────────────────────────────────────┐
│ Test Script                                                         │
│ ─────────────────────────────────────────────────────────────────  │
│ 1. Enable performance hook BEFORE GUI launches                     │
│ 2. Launch GUI normally                                              │
└─────────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│ GUI (noCamel1.py)                                                   │
│ ─────────────────────────────────────────────────────────────────  │
│ 3. User configures parameters (or auto-configured)                 │
│ 4. User clicks "Start Forward Test"                                │
│ 5. GUI validates config                                             │
│ 6. GUI builds frozen config (with token from symbol cache)         │
│ 7. GUI creates LiveTrader                                           │
│ 8. GUI checks for performance hook → HOOK DETECTED                 │
│ 9. GUI calls hook.inject_into_trader(trader)                       │
└─────────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Performance Hook                                                    │
│ ─────────────────────────────────────────────────────────────────  │
│ 10. Inject pre-convergence instrumentor → WebSocket/Broker/Trader  │
│ 11. Inject post-convergence instrumentor → Strategy                │
│ 12. Wrap trader's tick callback to monitor progress                │
└─────────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Normal Trading Flow                                                 │
│ ─────────────────────────────────────────────────────────────────  │
│ 13. WebSocket connects (with token from GUI config)                │
│ 14. Ticks flow through instrumented path                           │
│ 15. Hook monitors tick count                                        │
│ 16. Hook auto-stops at target (e.g., 1000 ticks)                   │
│ 17. Hook generates performance reports                             │
└─────────────────────────────────────────────────────────────────────┘

================================================================================
KEY ADVANTAGES
================================================================================

✅ Tests ACTUAL production workflow (not synthetic parallel path)
✅ Uses GUI's authentication (credentials, session management)
✅ Uses GUI's config building (validation, freezing, token handling)
✅ Uses GUI's trader instantiation (proper initialization)
✅ Token automatically populated from symbol cache (WebSocket works)
✅ Non-intrusive hook pattern (GUI workflow pristine)
✅ Can be disabled by simply not calling enable_performance_testing()

================================================================================
USAGE EXAMPLES
================================================================================

**Manual Mode (User Control)**
```bash
python scripts/test_live_via_gui.py --ticks 1000
```
- GUI launches with performance testing enabled
- User configures parameters manually
- User selects symbol from cache (token populated automatically)
- User clicks "Start Forward Test"
- Hook automatically instruments and monitors
- Auto-stops at 1000 ticks and generates reports

**Automated Mode (Programmatic)**
```bash
python scripts/test_live_programmatic.py --ticks 1000 --symbol NIFTY
```
- GUI launches with performance testing enabled
- Script auto-configures GUI settings
- User just clicks "Start Forward Test"
- Fully automated from there

================================================================================
TOKEN HANDLING (CRITICAL FIX)
================================================================================

**Problem**: Old script had NO token in config → WebSocket init check failed

**Solution**: GUI workflow handles token automatically:
1. User selects symbol from dropdown (GUI line ~2245)
2. GUI loads token from symbol cache (GUI line 2252)
   `token = cache[selected_symbol]`
3. GUI validates token exists for live trading (GUI line 2351)
4. GUI adds token to config (GUI line 2387)
   `config_dict["instrument"]["token"] = user_token`
5. Config frozen and passed to trader
6. Broker adapter gets token from config (broker_adapter line 419)
7. WebSocket init check passes (broker_adapter line 390)

Result: WebSocket connects successfully, no polling fallback

================================================================================
FAIL-FIRST IMPROVEMENTS
================================================================================

Updated broker_adapter.py to FAIL-FIRST instead of silent polling fallback:

**Before**:
```python
if self.WebSocketTickStreamer and self.instrument.get("token"):
    self._initialize_websocket_streaming(self.session_info)
else:
    logger.info("📊 WebSocket not available, using polling mode")
    self.streaming_mode = False  # Silent fallback
```

**After**:
```python
# FAIL-FIRST: WebSocket is MANDATORY
if not self.WebSocketTickStreamer:
    raise RuntimeError("WebSocket required but not available")

if not self.instrument.get("token"):
    raise ValueError("Token missing - WebSocket requires valid token")

# Initialize WebSocket (MANDATORY path, no fallback)
self._initialize_websocket_streaming(self.session_info)
```

Result: System crashes immediately if WebSocket unavailable or token missing
        (Better than silent failure with wrong data path)

================================================================================
TESTING WORKFLOW
================================================================================

1. **Enable Performance Hook**
   ```python
   from myQuant.utils.performance_test_hook import enable_performance_testing
   hook = enable_performance_testing(target_ticks=1000)
   ```

2. **Launch GUI**
   ```python
   from myQuant.gui.noCamel1 import main as gui_main
   gui_main()
   ```

3. **GUI Workflow Proceeds Normally**
   - Configure strategy
   - Select symbol (token auto-populated)
   - Click "Start Forward Test"

4. **Hook Automatically Injects**
   - Pre-convergence instrumentation
   - Post-convergence instrumentation
   - Tick monitoring wrapper

5. **Auto-Stop and Report**
   - Monitors tick count
   - Stops at target (e.g., 1000)
   - Generates performance reports

================================================================================
COMPLIANCE WITH COPILOT INSTRUCTIONS
================================================================================

✅ "Route through GUI so separate route for authentication/symbol input not required"
✅ "Test actual workflow, not parallel workflow wherever possible"
✅ "Live WebSocket is paramount - never compromise for backtest compatibility"
✅ "Fail-first, not fail-safe - crash loudly if WebSocket unavailable"
✅ "defaults.py is SSOT - no hardcoded fallbacks"
✅ "Frozen configs - immutable after validation"

================================================================================
FILES MODIFIED/CREATED
================================================================================

**Created**:
- myQuant/utils/performance_test_hook.py (hook implementation)
- scripts/test_live_via_gui.py (manual test script)
- scripts/test_live_programmatic.py (automated test script)
- documentation/PERFORMANCE_TEST_GUI_WORKFLOW.md (this file)

**Modified**:
- myQuant/gui/noCamel1.py (added hook detection and injection)
- myQuant/live/broker_adapter.py (fail-first WebSocket validation)

**Preserved**:
- GUI's authentication workflow
- GUI's config building workflow
- GUI's trader instantiation workflow
- GUI's symbol/token handling
- WebSocket streaming path (pristine, non-intrusive)

================================================================================
"""