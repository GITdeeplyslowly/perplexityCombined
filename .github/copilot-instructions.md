# GitHub Copilot Instructions - myQuant Trading System

## Project Overview

**myQuant** is a production-grade algorithmic trading system designed for real-world deployment with actual capital. The system processes market data tick-by-tick, executes long-only intraday strategies, and is currency-agnostic.

---

## Core Vision & Principles

### 1. Single Source of Truth (SSOT) - defaults.py

**CRITICAL**: `config/defaults.py` is the ONLY source for configuration defaults.

```python
# CORRECT - No fallbacks
value = config['strategy']['fast_ema']  # Will crash if missing

# WRONG - Silent fallbacks hide bugs
value = config.get('strategy', {}).get('fast_ema', 18)  # NEVER DO THIS
```

**Rules**:
- NO default values anywhere in business logic
- NO fallback values in strategy/indicator code
- NO `.get()` methods with default parameters in config access
- ALL parameters must exist in `defaults.py`

**Exception**: Validation result dictionaries (not configuration) can use `.get()` because they're parsing validation outputs, not configuration values.

### 2. Configuration Flow - Validate, Freeze, Transmit

**Flow**:
```
defaults.py → GUI modifications → validate_config() → freeze_config() → Immutable downstream
```

**Implementation**:
```python
# GUI modifies config based on user input
config = create_config_from_defaults()
config['strategy']['fast_ema'] = user_value

# Validate before freezing
validation = validate_config(config)
if not validation.get('valid', False):
    # Show errors to user, let them fix
    show_errors(validation.get('errors'))
    return

# Freeze once valid
frozen_config = freeze_config(deepcopy(config))  # MappingProxyType

# Pass immutable config downstream
strategy = ModularIntradayStrategy(frozen_config, indicators_module)
```

**Rules**:
- User modifications ONLY through GUI
- Config validated BEFORE freezing
- Once frozen (MappingProxyType), config is immutable
- Downstream consumers (liveStrategy.py, backtest_runner.py) receive frozen config
- NO overrides allowed downstream

### 3. Fail-First, Not Fail-Safe

**In trading systems, silent failures cost money. Crash loudly and immediately.**

```python
# CORRECT - Fail-first
if 'required_param' not in config:
    raise ValueError("Missing required_param - check defaults.py")

# WRONG - Silent fallback
value = config.get('required_param', default_value)  # Hides bugs!
```

**Rules**:
- Missing configuration → STOP immediately
- Invalid data → STOP immediately (except live streaming quality issues)
- Any configuration drift → STOP immediately
- Error messages must explain WHAT went wrong AND HOW to fix it

**Exception**: Live data streaming quality issues (missing ticks, delayed data) should be handled gracefully to maintain trading continuity. Use NaN thresholds and recovery logic for streaming issues.

### 4. Tick-by-Tick Processing (NO Bar Aggregation)

**CRITICAL**: This system processes EVERY tick individually. No OHLCV bar aggregation.

```python
# CORRECT - Tick-by-tick
def on_tick(self, tick: Dict):
    price = tick['price']
    self.ema_tracker.update(price)  # Incremental update
    signal = self.evaluate_entry(tick)

# WRONG - Bar aggregation
def on_bar(self, bar: OHLCV):  # We don't do this!
    self.calculate_indicators(bar.close)
```

**Rules**:
- Process one tick at a time
- NO bar buffering or aggregation
- ALL indicators must be incremental (update on each tick)
- Target latency: <50ms per tick
- Handles large datasets by processing row-by-row

### 5. Incremental Indicators

**ALL indicator calculations must be incremental** - whether backtesting or forward testing.

```python
# CORRECT - Incremental EMA
class IncrementalEMA:
    def update(self, price: float) -> float:
        if self.ema is None:
            self.ema = price
        else:
            self.ema = (price * self.alpha) + (self.ema * (1 - self.alpha))
        return self.ema

# WRONG - Recalculating from history
def calculate_ema(prices: List[float]) -> float:
    return pandas.DataFrame(prices).ewm(span=20).mean()  # Too slow!
```

**Rules**:
- Update indicators on EVERY tick
- NO recalculation from historical buffers
- Memory-efficient (O(1) space per indicator)
- Same incremental logic in backtest AND live

### 6. Live Webstream is Paramount

**Live trading performance is NEVER compromised for anything else.**

**Priority Hierarchy**:
1. **Live WebSocket streaming** - Mission critical, pristine code path
2. **Live polling mode** - Secondary live trading path
3. **Forward testing** - Simulates live trading
4. **Backtesting** - Optimization and research

**Rules**:
- WebSocket workflow is sacred - keep it pristine and non-intrusive
- NEVER compromise live performance for backtest compatibility
- Update `researchStrategy.py` periodically to mirror `liveStrategy.py`
- Make backtest TRY to keep up with live, not the other way around
- File simulation must be completely separate, non-intrusive to live paths

**Code Paths**:
```python
# Live WebSocket (PRIMARY)
WebSocket → Broker Adapter → Callback/Queue → Strategy.on_tick() → Position Manager

# File Simulation (SEPARATE)
CSV File → Data Simulator → Broker Adapter → Same downstream path
```

### 7. Backtest Must Mirror Live Trading

**Purpose**: Learnings from backtest should translate directly to live trading.

**Rules**:
- `researchStrategy.py` mirrors `liveStrategy.py` in strategy logic
- Same indicators, same parameters, same calculations
- Incremental indicators in BOTH backtest and live
- Backtest results should predict live performance
- `liveStrategy.py` is optimized for live streaming
- `researchStrategy.py` is optimized for batch processing
- Periodically sync backtest to match live (not vice versa)

### 8. Modularity, Maintainability, Scalability

**Code Quality Standards**:
- **Modular**: Clear separation of concerns (strategy, indicators, risk, data)
- **Maintainable**: Self-documenting code, clear naming, proper structure
- **Scalable**: Handles high-frequency data without performance degradation
- **Not Bloated**: Remove dead code, avoid over-engineering

**Patterns**:
- Dependency injection (pass config, don't import)
- Single Responsibility Principle (one class, one job)
- Type hints on all function signatures
- Docstrings for public APIs

### 9. User Feedback & Strategy Testing

**The bot exists to test and fine-tune trading strategies for real deployment.**

**Critical Requirements**:
a. **Complete feedback** in easily consumable format
b. **Precise inference** possible from results
c. **Accurate strategy implementation** matching user intent
d. **Easy modification** of strategies/parameters/indicators

**Implementation**:
- Excel results files with comprehensive metrics
- Configuration section shows EXACT parameters used
- Trade-by-trade breakdown with entry/exit reasons
- Performance summary for quick assessment
- Dialog box text copied to results (SSOT for config display)

### 10. System Characteristics

**Trading Profile**:
- **Long Only**: No short positions
- **Intraday**: All positions closed by session end
- **Currency Agnostic**: Works with any currency denomination

**Architecture**:
- Frozen configurations (MappingProxyType)
- Fail-first error handling
- Tick-by-tick processing
- Incremental indicators
- Live WebSocket primary, file simulation secondary

---

## Code Patterns & Standards

### Configuration Access

```python
# CORRECT - Direct access, fail if missing
fast_ema = self.config_accessor.get_strategy_param('fast_ema')

# Inside ConfigAccessor:
def get_strategy_param(self, param: str):
    if param not in self.config['strategy']:
        raise KeyError(f"Missing required parameter: strategy.{param}")
    return self.config['strategy'][param]

# WRONG - Fallback hides missing config
fast_ema = config.get('strategy', {}).get('fast_ema', 18)
```

### Error Handling

```python
# CORRECT - Clear, actionable error
if not tick.get('price'):
    raise ValueError(
        "Missing 'price' in tick data. "
        "Check data source configuration in broker_adapter.py"
    )

# WRONG - Vague error
if not tick.get('price'):
    raise ValueError("Invalid tick")  # What's wrong? How to fix?
```

### Type Hints

```python
# REQUIRED - All function signatures
def on_tick(self, tick: Dict[str, Any]) -> Optional[TradingSignal]:
    pass

# NOT ALLOWED - No type hints
def on_tick(self, tick):  # Missing types!
    pass
```

### Logging

```python
# CORRECT - Structured logging
logger.info(f"Position opened: {position_id}, qty={quantity}, price={price}")

# WRONG - Print statements
print("Position opened")  # Not allowed in production code
```

### Code Organization

```python
# Project Structure
myQuant/
├── config/
│   └── defaults.py          # SSOT for all parameters
├── core/
│   ├── liveStrategy.py      # Live trading strategy (OPTIMIZED)
│   ├── researchStrategy.py  # Backtest strategy (mirrors live)
│   ├── indicators.py        # Incremental indicator implementations
│   └── position_manager.py  # Risk management
├── live/
│   ├── broker_adapter.py    # Data source interface
│   ├── trader.py            # Live trading orchestration
│   └── forward_test_results.py  # Results export
├── gui/
│   └── noCamel1.py         # User interface (config SSOT)
└── utils/
    ├── config_helper.py    # Config validation/freezing
    └── time_utils.py       # Time handling utilities
```

---

## Implementation Guidelines

### When Adding New Features

1. **Add parameter to defaults.py FIRST**
   ```python
   # config/defaults.py
   "strategy": {
       "new_parameter": 50,  # Add here first
   }
   ```

2. **Update GUI to expose parameter** (if user-facing)

3. **Access via fail-first pattern**
   ```python
   new_value = self.config_accessor.get_strategy_param('new_parameter')
   ```

4. **NO hardcoded fallbacks anywhere**

### When Modifying Indicators

1. **Ensure incremental implementation**
   - Must work tick-by-tick
   - O(1) time complexity per update
   - Minimal memory footprint

2. **Update both live AND backtest**
   - Change `liveStrategy.py` first (priority)
   - Update `researchStrategy.py` to mirror

3. **Test with file simulation**
   - Verify correct calculation
   - Check performance with large datasets

### When Handling Errors

1. **Configuration errors → STOP immediately**
   ```python
   raise ValueError("Clear error with fix instructions")
   ```

2. **Live streaming issues → Handle gracefully**
   ```python
   self.nan_streak += 1
   if self.nan_streak > threshold:
       logger.error("Excessive NaN streak - stopping")
       self.stop()
   ```

3. **Always log context**
   ```python
   logger.error(f"Error in {context}: {error}", exc_info=True)
   ```

---

## What NOT to Do

### Forbidden Patterns

❌ **Hardcoded defaults outside defaults.py**
```python
# NEVER DO THIS
macd_fast = config.get('macd_fast', 12)  # Hardcoded 12!
```

❌ **Bar aggregation in live trading**
```python
# NEVER DO THIS
def aggregate_ticks_to_bars(ticks: List) -> OHLCV:
    # We process tick-by-tick, not bars!
```

❌ **Mutable configs after freezing**
```python
# NEVER DO THIS
frozen_config['strategy']['fast_ema'] = 20  # Will crash (good!)
```

❌ **Silent fallbacks**
```python
# NEVER DO THIS
value = config.get('key', default)  # Hides missing config
```

❌ **Regenerating already-generated data**
```python
# NEVER DO THIS - Generate once, reuse
dialog_text = self._build_config_summary()  # Generated in GUI
# Later...
dialog_text = self._rebuild_config_summary()  # NO! Just reuse
```

❌ **Print statements in production**
```python
# NEVER DO THIS
print("Debug message")  # Use logger.debug() instead
```

❌ **Compromising live performance**
```python
# NEVER DO THIS
if is_live_mode:
    time.sleep(0.1)  # To make backtest sync - NO!
```

---

## Communication Expectations

### When Providing Code Changes

**Required Format**:
1. **Number all diffs** if multiple changes
2. **Name the target file** for each diff
3. **List new variables** and reasons for adding them
4. **Explain what changed** and why
5. **List any deviations** from user suggestions
6. **Maintain existing patterns** - don't introduce new styles
7. **NO emojis** in code or variable names
8. **Keep code clean** - minimize error potential

### Large Changes

If a change is large or unwieldy:
- **Break into multiple steps**
- **Implement incrementally**
- **Verify each step** before proceeding

### Documentation

- Save related documentation in: `C:\Users\user\projects\Perplexity Combined\documentation`
- Update relevant .md files when architecture changes
- Keep copilot-instructions.md current with new patterns

---

## Current System State

### Active Features
- Hybrid tick processing (callback + polling modes)
- File simulation for historical data testing
- GUI configuration with validation/freezing
- Excel results export with SSOT config display
- Incremental indicators (EMA, MACD, VWAP, RSI, HTF, ATR)
- Position management with TP/SL/trailing stop
- NaN streak handling for live streaming quality

### Performance Targets
- Tick processing latency: <50ms
- GUI responsiveness: <100ms updates
- File simulation: ~1000 ticks/sec (with GUI yield)
- Live WebSocket: Unrestricted (primary mission)

### Key Files
- `config/defaults.py` - Configuration SSOT
- `core/liveStrategy.py` - Live trading strategy
- `live/broker_adapter.py` - Data source interface
- `gui/noCamel1.py` - User interface
- `live/forward_test_results.py` - Results export

---

## Summary: Golden Rules

1. **defaults.py is SSOT** - No fallbacks anywhere
2. **Fail-first** - Crash loudly, fix immediately
3. **Tick-by-tick** - No bar aggregation
4. **Incremental indicators** - Update on every tick
5. **Frozen configs** - Immutable after validation
6. **Live performance paramount** - Never compromise
7. **Backtest mirrors live** - Not the other way around
8. **Clear errors** - Explain what and how to fix
9. **No emojis** - Clean, professional code
10. **WebSocket sacred** - Keep primary path pristine

---

**When in doubt**: Check defaults.py, fail-first, keep it simple, prioritize live performance.
