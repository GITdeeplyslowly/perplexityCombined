<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# List out all the cases -  Default Value Fallbacks

Multiple .get() calls with default values throughout codebase
VIOLATION: "NO FALLBACKS IN TRADING SYSTEMS" principle
FIX: Replace all .get(key, default) with strict [key] access that fails fast

Below are the key occurrences of `.get(key, default)` across the codebase that must be replaced with strict key access:

1. **core/broker_adapter.py**

```python
config = load_config(config_path)
self.params = config.get('live', {})               # <- VIOLATION
```

2. **utils/config_loader.py** (to be removed)

```python
config = create_config_from_defaults()
…
user_prefs = config.get('user_preferences', {})    # <- VIOLATION
```

3. **core/simple_loader.py**

```python
params = cfg.get('data_feed', {'type': 'file'})    # <- VIOLATION
```

4. **core/backtest_runner.py**

```python
data_source = config.get('data', {}).get('historical', None)  # <- VIOLATION
runner_opts = config.get('runner_options', {})                # <- VIOLATION
```

5. **core/researchStrategy.py**

```python
strategy_cfg = cfg.get('strategy', {})                 # <- VIOLATION
indicators = strategy_cfg.get('indicators', [])         # <- VIOLATION
```

6. **core/liveStrategy.py**

```python
risk_cfg = cfg.get('risk', {}).get('max_drawdown', 0.02)  # <- VIOLATION
```

7. **core/position_manager.py**

```python
lot_size = cfg.get('instrument', {}).get('lot_size', 1)  # <- VIOLATION
tick_size = cfg.get('instrument', {}).get('tick_size', 0.05)  # <- VIOLATION
```

8. **core/cache_manager.py**

```python
cache_path = cfg.get('cache', {}).get('symbol_cache_path', DEFAULTCACHEPATH)  # <- VIOLATION
```

9. **core/logger.py**

```python
logfile = cfg.get('logging', {}).get('logfile', 'trading_bot.log')  # <- VIOLATION
verbosity = cfg.get('logging', {}).get('verbosity', 'INFO')        # <- VIOLATION
```

10. **core/websocket_stream.py**

```python
reconnect = cfg.get('stream', {}).get('reconnect_attempts', 3)     # <- VIOLATION
```


Each of these must be refactored from:

```python
value = cfg.get('section', {}).get('param', default)
```

to:

```python
value = cfg['section']['param']  # fails fast if missing
```

