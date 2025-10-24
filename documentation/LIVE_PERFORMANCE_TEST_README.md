# Live Performance Testing - GUI Workflow Mode

## Quick Start

### Option 1: Manual Mode (Recommended for First-Time Use)
```bash
python scripts/test_live_via_gui.py --ticks 1000
```

1. GUI launches with performance testing enabled
2. Configure your parameters (or use defaults)
3. Select symbol from dropdown (token auto-populated)
4. Click **"Start Forward Test"** button
5. System automatically:
   - Instruments the trader
   - Monitors tick progress
   - Stops after 1000 ticks
   - Generates performance reports

### Option 2: Programmatic Mode (For Automation)
```bash
python scripts/test_live_programmatic.py --ticks 1000 --symbol NIFTY
```

Similar to manual mode, but with pre-configured settings.

## What This Tests

✅ **Actual production workflow** (not synthetic test path)  
✅ **GUI authentication** (credentials, session management)  
✅ **GUI configuration** (validation, freezing, token handling)  
✅ **WebSocket streaming** (with proper token from symbol cache)  
✅ **Tick-by-tick processing** (full latency measurement)  
✅ **Pre-convergence metrics** (WebSocket → Broker → Trader)  
✅ **Post-convergence metrics** (Strategy execution)

## How It Works

1. **Enable Performance Hook** (before GUI launch)
   - Creates instrumentors for measurement
   - Registers hook globally

2. **GUI Workflow Proceeds Normally**
   - User (or script) configures parameters
   - Selects symbol → token auto-populated
   - Clicks "Start Forward Test"

3. **Hook Injects Automatically**
   - Detects enabled hook when creating LiveTrader
   - Injects instrumentation into tick processing path
   - Wraps tick callback to monitor progress

4. **Auto-Stop and Report**
   - Monitors tick count
   - Stops at target (e.g., 1000 ticks)
   - Generates comprehensive performance reports

## Requirements

- **Market hours**: Must test during live market hours
- **Credentials**: SmartAPI credentials configured
- **Symbol cache**: Symbol must exist in cache with valid token
- **WebSocket**: System requires WebSocket mode (polling disabled)

## Command Line Options

```bash
python scripts/test_live_via_gui.py [OPTIONS]

Options:
  --ticks N              Number of ticks to collect (default: 1000)
  --no-pre               Disable pre-convergence instrumentation
  --no-post              Disable post-convergence instrumentation
  --no-auto-stop         Do not auto-stop after target ticks
```

## Performance Reports

Reports are generated automatically when target tick count is reached:

- **Pre-Convergence Report**: WebSocket → Broker → Trader latency
- **Post-Convergence Report**: Strategy execution latency
- **Total Latency**: End-to-end tick processing time

Reports show:
- Average latency per stage
- P50, P95, P99 percentiles
- Max latency spikes
- Throughput (ticks/sec)

## Troubleshooting

**"WebSocket unavailable" error**:
- Check that `myQuant/live/websocket_stream.py` exists
- Verify import paths are correct

**"Token missing" error**:
- Select symbol from dropdown in GUI
- Token should auto-populate from symbol cache
- Verify symbol exists in cache (`utils/cache_manager.py`)

**No ticks received**:
- Verify market is open
- Check SmartAPI credentials
- Review WebSocket connection logs

## Architecture

```
Test Script
    ↓
GUI Launch (with hook enabled)
    ↓
User Configures → Selects Symbol → Clicks Start
    ↓
GUI Validates → Builds Config → Creates Trader
    ↓
Hook Detects → Injects Instrumentation
    ↓
WebSocket Stream (instrumented)
    ↓
Broker Adapter (instrumented)
    ↓
Trader (instrumented)
    ↓
Strategy (instrumented)
    ↓
Auto-Stop → Generate Reports
```

## Key Differences from Old Approach

| Aspect | Old (test_live_performance.py) | New (test_live_via_gui.py) |
|--------|-------------------------------|----------------------------|
| Authentication | Parallel path | GUI workflow |
| Config Building | Separate builder | GUI builder |
| Token Handling | Missing/hardcoded | From symbol cache |
| Validation | Bypassed | Full GUI validation |
| Trader Creation | Direct instantiation | GUI workflow |
| WebSocket | Failed (no token) | Works (token populated) |
| Testing Scope | Synthetic path | Production path |

## Related Documentation

- [PERFORMANCE_TEST_GUI_WORKFLOW.md](../documentation/PERFORMANCE_TEST_GUI_WORKFLOW.md) - Detailed architecture
- [.github/copilot-instructions.md](../.github/copilot-instructions.md) - Project principles
- [myQuant/utils/performance_test_hook.py](../myQuant/utils/performance_test_hook.py) - Hook implementation

## Next Steps After Testing

1. Review performance reports
2. Identify bottlenecks (if any)
3. Measure before optimizing (Phase 1 baseline principle)
4. Implement conditional optimizations based on evidence
5. Re-test with optimizations to verify improvements
