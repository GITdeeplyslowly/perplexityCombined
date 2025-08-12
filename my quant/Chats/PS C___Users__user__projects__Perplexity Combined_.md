import logging
from typing import Dict, Any
# PS C:\\Users\\user\\projects\\Perplexity Combined\\my quant> py -m gui.unified\_gui
logger = logging.getLogger(__name__)
2025-08-12 09:02:04,593 [    INFO] **main**: Config being sent: {'strategy': {'strategy\_version': 'research', 'use\_ema\_crossover': True, 'use\_macd': False,
class ConfigAccessor:use\_rsi\_filter': False, 'use\_htf\_trend': False, 'use\_bollinger\_bands': False, 'use\_stochastic': False, 'use\_atr': False, 'fast\_ema': 9,
    def __init__(self, config: Dict[str, Any]):: 26, 'macd\_signal': 9, 'rsi\_length': 14, 'rsi\_oversold': 30, 'rsi\_overbought': 70, 'htf\_period': 20, 'indicator\_update\_mode': 'tick'}, 'risk': {'base\_sl\_points': 15.0, 'tp\_points': [10.0, 25.0, 50.0, 100.0], 'tp\_percents': [0.25, 0.25, 0.25, 0.25], 'use\_trail\_stop':
        self.config = configints': 25.0, 'trail\_distance\_points': 10.0, 'risk\_per\_trade\_percent': 1.0, 'commission\_percent': 0.03, 'commission\_per\_trade': 0.0}, 'capital': {'initial\_capital': 100000.0}, 'instrument': {'symbol': 'NIFTY', 'exchange': 'NSE\_FO', 'lot\_size': 75, 'tick\_size': 0.05, 'product\_type': 'INTRADAY'}, 'session': {'is\_intraday': True, 'start\_hour': 9, 'start\_min': 15, 'end\_hour': 15, 'end\_min': 30, 'start\_buffer\_minutes': 5, 'end\_buffer\_minutes':
20, 'timezone': 'Asia/Kolkata'}, 'backtest': {'max\_drawdown\_pct': 0, 'allow\_short': False, 'close\_at\_session\_end': True, 'save\_results': True, 'results\_dir': 'backtest\_results', 'log\_level': 'INFO'}}
    def get_strategy_param(self, key: str, default: Any = None) -> Any:assed - all required sections present
        return self.config.get('strategy', {}).get(key, default)uration structure for backtest
2025-08-12 09:02:04,613 [    INFO] **main**: Starting backtest execution...
    def get_risk_param(self, key: str, default: Any = None) -> Any:=======
        return self.config.get('risk', {}).get(key, default): STARTING BACKTEST WITH NORMALIZED DATA PIPELINE
2025-08-12 09:02:04,624 [    INFO] backtest.backtest\_runner: ============
    def get_capital_param(self, key: str, default: Any = None) -> Any: CONFIG STRUCTURE MAINTAINED =
        return self.config.get('capital', {}).get(key, default)ection 'strategy': 19 parameters
2025-08-12 09:02:04,628 [    INFO] backtest.backtest\_runner: Section 'risk': 9 parameters
    def get_instrument_param(self, key: str, default: Any = None) -> Any:pital': 1 parameters
        return self.config.get('instrument', {}).get(key, default)ion 'instrument': 5 parameters
2025-08-12 09:02:04,633 [    INFO] backtest.backtest\_runner: Section 'session': 8 parameters
    def get_session_param(self, key: str, default: Any = None) -> Any:'backtest': 6 parameters
        return self.config.get('session', {}).get(key, default)ESTED CONFIG: Using consistent nested configuration structure
2025-08-12 09:02:04,663 [    INFO] backtest.backtest\_runner: Strategy parameters found: ['strategy\_version', 'use\_ema\_crossover', 'use\_macd', 'use\_vwap', 'use\_rsi\_filter', 'use\_htf\_trend', 'use\_bollinger\_bands', 'use\_stochastic', 'use\_atr', 'fast\_ema', 'slow\_ema', 'macd\_fast', 'macd\_slow', 'macd\_signal', 'rsi\_length', 'rsi\_oversold', 'rsi\_overbought', 'htf\_period', 'indicator\_update\_mode']
    def get_backtest_param(self, key: str, default: Any = None) -> Any:gured:
        return self.config.get('backtest', {}).get(key, default)
2025-08-12 09:02:04,672 [    INFO] core.researchStrategy: Strategy initialized: Modular Intraday Long-Only Strategy v3.0
    def validate_required_params(self) -> Dict[str, Any]: Indicators enabled:
        validation = {VWAP=False, HTF=False, RSI=False
            'valid': True,   INFO] backtest.backtest\_runner: ✅ Strategy interf
            'errors': [],
            'warnings': []   INFO] backtest.backtest\_runner: = NESTED CONFIG PASSED TO POSITION MANAGER =
        }2 09:02:04,682 [    INFO] core.position\_manager: PositionManager initialized with capital: 100,000.0
        required_sections = ['strategy', 'risk', 'capital', 'instrument', 'session']ralized loader...
        for section in required_sections:st.backtest\_runner: Loading data from: C:/Users/user/Desktop/data/date-wise/live\_ticks\_20250721\_163044.csv
            if section not in self.config:imple\_loader: Loading data from: C:/Users/user/Desktop/data/date-wise/live\_ticks\_20250721\_163044.csv
                validation['errors'].append(f"Missing required section: {section}") data
                validation['valid'] = Falsemple\_loader: Loaded 36151 ticks
        critical_params = [  INFO] backtest.backtest\_runner: ================
            ('strategy', 'use_ema_crossover'),cktest\_runner: STAGE 1: RAW DATA SAMPLE (5 rows per 1000)
            ('risk', 'base_sl_points'),test.backtest\_runner: ================
            ('capital', 'initial_capital'),.backtest\_runner: Sampling 185 rows from 36151 total rows
            ('session', 'intraday_start_hour')cktest\_runner: Raw Row      0 (Sample  1): Time=2025-07-21 09:18:04+05:30, Close=  173.90, Volume=   150
        ]2 09:02:06,449 [    INFO] backtest.backtest\_runner: Raw Row    200 (Sample  2): Time=2025-07-21 09:20:07+05:30, Close=  186.40, Volume=    75
        for section, param in critical_params:cktest\_runner: Raw Row    400 (Sample  3): Time=2025-07-21 09:22:09+05:30, Close=  208.20, Volume=    75
            if section in self.config and param not in self.config[section]: (Sample  4): Time=2025-07-21 09:24:12+05:30, Close=  214.90, Volume=    75
                validation['warnings'].append(f"Missing parameter: {section}.{param}")5): Time=2025-07-21 09:26:15+05:30, Close=  227.90, Volume=    75
        return validation    INFO] backtest.backtest\_runner: Raw Row   1000 (Sample  6): Time=2025-07-21 09:28:17+05:30, Close=  224.40, Volume=    75
2025-08-12 09:02:06,466 [    INFO] backtest.backtest\_runner: Raw Row   1200 (Sample  7): Time=2025-07-21 09:30:22+05:30, Close=  218.85, Volume=    75
    def is_indicator_enabled(self, indicator_name: str) -> bool:le  8): Time=2025-07-21 09:32:25+05:30, Close=  225.00, Volume=    75
        """67 [    INFO] backtest.backtest\_runner: Raw Row   1600 (Sample  9): Time=2025-07-21 09:34:27+05:30, Close=  235.00, Volume=    75
        Check if a specific indicator is enabled in the strategy configuration. [    INFO] backtest.backtest\_runner: Raw Row   1800 (Sample 10): Time=2025-07-21 09:36:30+05:30, Close=  219.75, Volume=   225
        ,472 [    INFO] backtest.backtest\_runner: Raw Row   2000 (Sample 11): Time=2025-07-21 09:38:33+05:30, Close=  223.55, Volume=   150
        Args:3 [    INFO] backtest.backtest\_runner: Raw Row   2200 (Sample 12): Time=2025-07-21 09:40:36+05:30, Close=  219.45, Volume=    75
            indicator_name (str): Name of the indicator to check (e.g., 'rsi', 'macd', 'ema_crossover')    INFO] backtest.backtest\_runner: Raw Row   2400 (Sample 13): Time=2025-07-21 09:42:38+05:30, Close=  201.20, Volume=    75
        1 [    INFO] backtest.backtest\_runner: Raw Row   2600 (Sample 14): Time=2025-07-21 09:44:41+05:30, Close=  196.80, Volume=    75
        Returns:1 [    INFO] backtest.backtest\_runner: Raw Row   2800 (Sample 15): Time=2025-07-21 09:46:44+05:30, Close=  186.40, Volume=   225
            bool: True if the indicator is enabled, False otherwise08-12 09:02:06,482 [    INFO] backtest.backtest\_runner: Raw Row   3000 (Sample 16): Time=2025-07-21 09:48:46+05:30, Close=  163.20, Volume=    75
        """ [    INFO] backtest.backtest\_runner: Raw Row   3200 (Sample 17): Time=2025-07-21 09:50:52+05:30, Close=  155.30, Volume=    75
        # Map indicator names to their configuration keys): Time=2025-07-21 09:52:55+05:30, Close=  145.25, Volume=   150
        indicator_map = {e 19): Time=2025-07-21 09:54:57+05:30, Close=  134.45, Volume=   150
            'rsi': 'use_rsi_filter',mple 20): Time=2025-07-21 09:57:00+05:30, Close=  129.55, Volume=    75
            'ema_crossover': 'use_ema_crossover', ple 21): Time=2025-07-21 09:59:04+05:30, Close=  127.10, Volume=   225
            'macd': 'use_macd',08-12 09:02:06,488 [    INFO] backtest.backtest\_runner: Raw Row   4200 (Sample 22): Time=2025-07-21 10:01:08+05:30, Close=  130.55, Volume=    75
            'vwap': 'use_vwap',,488 [    INFO] backtest.backtest\_runner: Raw Row   4400 (Sample 23): Time=2025-07-21 10:03:10+05:30, Close=  125.75, Volume=    75
            'htf_trend': 'use_htf_trend', 4600 (Sample 24): Time=2025-07-21 10:05:13+05:30, Close=  123.85, Volume=    75
            'bollinger_bands': 'use_bollinger_bands',5): Time=2025-07-21 10:07:15+05:30, Close=  125.95, Volume=    75
            'stochastic': 'use_stochastic',============
            'atr': 'use_atr',08-12 09:02:06,499 [    INFO] backtest.backtest\_runner: STAGE 2: AFTER NORMALIZATION (Same Rows)
            'ma': 'use_ma',est.backtest\_runner: ================
            'volume_ma': 'use_volume_ma'1): Time=2025-07-21 09:18:04+05:30, Close=  173.90, Volume=   150
        }2 [    INFO] backtest.backtest\_runner: Norm Row    200 (Sample  2): Time=2025-07-21 09:20:07+05:30, Close=  186.40, Volume=    75
         400 (Sample  3): Time=2025-07-21 09:22:09+05:30, Close=  208.20, Volume=    75
        # Get the appropriate config key for this indicatorr: Norm Row    600 (Sample  4): Time=2025-07-21 09:24:12+05:30, Close=  214.90, Volume=    75
        config_key = indicator_map.get(indicator_name)08-12 09:02:06,504 [    INFO] backtest.backtest\_runner: Norm Row    800 (Sample  5): Time=2025-07-21 09:26:15+05:30, Close=  227.90, Volume=    75
        if config_key: [    INFO] backtest.backtest\_runner: Norm Row   1000 (Sample  6): Time=2025-07-21 09:28:17+05:30, Close=  224.40, Volume=    75
            return self.get_strategy_param(config_key, False) Row   1200 (Sample  7): Time=2025-07-21 09:30:22+05:30, Close=  218.85, Volume=    75
        st\_runner: Norm Row   1400 (Sample  8): Time=2025-07-21 09:32:25+05:30, Close=  225.00, Volume=    75
        # Fallback: try direct mapping with 'use_' prefix08-12 09:02:06,507 [    INFO] backtest.backtest\_runner: Norm Row   1600 (Sample  9): Time=2025-07-21 09:34:27+05:30, Close=  235.00, Volume=    75
        return self.get_strategy_param(f'use_{indicator_name}', False)08 [    INFO] backtest.backtest\_runner: Norm Row   1800 (Sample 10): Time=2025-07-21 09:36:30+05:30, Close=  219.75, Volume=   225
acktest.backtest\_runner: Norm Row   2000 (Sample 11): Time=2025-07-21 09:38:33+05:30, Close=  223.55, Volume=   150
def create_nested_config_from_flat(flat_config: Dict[str, Any]) -> Dict[str, Any]: INFO] backtest.backtest\_runner: Norm Row   2200 (Sample 12): Time=2025-07-21 09:40:36+05:30, Close=  219.45, Volume=    75
    nested_config = { backtest.backtest\_runner: Norm Row   2400 (Sample 13): Time=2025-07-21 09:42:38+05:30, Close=  201.20, Volume=    75
        'strategy': {},est.backtest\_runner: Norm Row   2600 (Sample 14): Time=2025-07-21 09:44:41+05:30, Close=  196.80, Volume=    75
        'risk': {}, backtest.backtest\_runner: Norm Row   2800 (Sample 15): Time=2025-07-21 09:46:44+05:30, Close=  186.40, Volume=   225
        'capital': {},backtest.backtest\_runner: Norm Row   3000 (Sample 16): Time=2025-07-21 09:48:46+05:30, Close=  163.20, Volume=    75
        'instrument': {},08-12 09:02:06,514 [    INFO] backtest.backtest\_runner: Norm Row   3200 (Sample 17): Time=2025-07-21 09:50:52+05:30, Close=  155.30, Volume=    75
        'session': {},_runner: Norm Row   3400 (Sample 18): Time=2025-07-21 09:52:55+05:30, Close=  145.25, Volume=   150
        'backtest': {}O] backtest.backtest\_runner: Norm Row   3600 (Sample 19): Time=2025-07-21 09:54:57+05:30, Close=  134.45, Volume=   150
    }acktest.backtest\_runner: Norm Row   3800 (Sample 20): Time=2025-07-21 09:57:00+05:30, Close=  129.55, Volume=    75
    strategy_params = [ Row   4000 (Sample 21): Time=2025-07-21 09:59:04+05:30, Close=  127.10, Volume=   225
        'use_ema_crossover', 'use_macd', 'use_vwap', 'use_rsi_filter', 'use_htf_trend',est.backtest\_runner: Norm Row   4200 (Sample 22): Time=2025-07-21 10:01:08+05:30, Close=  130.55, Volume=    75
        'use_bollinger_bands', 'use_stochastic', 'use_atr', 'fast_ema', 'slow_ema', (Sample 23): Time=2025-07-21 10:03:10+05:30, Close=  125.75, Volume=    75
        'macd_fast', 'macd_slow', 'macd_signal', 'rsi_length', 'rsi_overbought',orm Row   4600 (Sample 24): Time=2025-07-21 10:05:13+05:30, Close=  123.85, Volume=    75
        'rsi_oversold', 'htf_period', 'strategy_version', 'indicator_update_mode' 125.95, Volume=    75
    ][    INFO] backtest.backtest\_runner: = COMPLETE DATASET ANALYSIS =
































    return nested_config    logger.info(f"Converted flat config to nested: {len(flat_config)} → {sum(len(v) for v in nested_config.values())} parameters")            nested_config[section].update(flat_config[section])        if section in flat_config and isinstance(flat_config[section], dict):    for section in nested_config.keys():                nested_config[section][param] = flat_config[param]            if param in flat_config:        for param in param_list:    for section, param_list in param_mapping.items():    }        'backtest': backtest_params        'session': session_params,        'instrument': instrument_params,        'capital': capital_params,        'risk': risk_params,        'strategy': strategy_params,    param_mapping = {    ]        'save_results', 'results_dir', 'log_level'        'max_drawdown_pct', 'allow_short', 'close_at_session_end',    backtest_params = [    ]        'intraday_end_min', 'exit_before_close', 'timezone'        'intraday_start_hour', 'intraday_start_min', 'intraday_end_hour',    session_params = [    instrument_params = ['symbol', 'exchange', 'lot_size', 'tick_size', 'product_type']    capital_params = ['initial_capital']    ]        'commission_percent', 'commission_per_trade', 'buy_buffer'        'trail_distance_points', 'tp_points', 'tp_percents', 'risk_per_trade_percent',        'base_sl_points', 'use_trail_stop', 'trail_activation_points',     risk_params = [2025-08-12 09:02:06,528 [    INFO] backtest.backtest\_runner: Dataset shape: (36151, 6)
2025-08-12 09:02:06,530 [    INFO] backtest.backtest\_runner: Time range: 2025-07-21 09:18:04+05:30 to 2025-07-21 15:30:01+05:30
2025-08-12 09:02:06,535 [    INFO] backtest.backtest\_runner: Total duration: 0 days 06:11:57
2025-08-12 09:02:06,552 [    INFO] backtest.backtest\_runner: Hourly tick distribution:
2025-08-12 09:02:06,552 [    INFO] backtest.backtest\_runner:   Hour 09: 4,089
ticks
2025-08-12 09:02:06,553 [    INFO] backtest.backtest\_runner:   Hour 10: 5,841
ticks
2025-08-12 09:02:06,553 [    INFO] backtest.backtest\_runner:   Hour 11: 5,837
ticks
2025-08-12 09:02:06,553 [    INFO] backtest.backtest\_runner:   Hour 12: 5,815
ticks
2025-08-12 09:02:06,553 [    INFO] backtest.backtest\_runner:   Hour 13: 5,819
ticks
2025-08-12 09:02:06,554 [    INFO] backtest.backtest\_runner:   Hour 14: 5,844
ticks
2025-08-12 09:02:06,555 [    INFO] backtest.backtest\_runner:   Hour 15: 2,906
ticks
2025-08-12 09:02:06,556 [    INFO] backtest.backtest\_runner: First 10 rows:
2025-08-12 09:02:06,564 [    INFO] backtest.backtest\_runner:
close  volume
2025-07-21 09:18:04+05:30  173.90     150
2025-07-21 09:18:05+05:30  175.00      75
2025-07-21 09:18:05+05:30  174.10      75
2025-07-21 09:18:06+05:30  173.15      75
2025-07-21 09:18:07+05:30  174.05      75
2025-07-21 09:18:07+05:30  173.30      75
2025-07-21 09:18:08+05:30  174.30      75
2025-07-21 09:18:09+05:30  174.25     150
2025-07-21 09:18:09+05:30  174.60     150
2025-07-21 09:18:10+05:30  175.65     150
2025-08-12 09:02:06,565 [    INFO] backtest.backtest\_runner: Last 10 rows:
2025-08-12 09:02:06,568 [    INFO] backtest.backtest\_runner:
close  volume
2025-07-21 15:29:54+05:30  79.60     150
2025-07-21 15:29:55+05:30  80.00     150
2025-07-21 15:29:56+05:30  80.50      75
2025-07-21 15:29:56+05:30  79.90     150
2025-07-21 15:29:57+05:30  79.20      75
2025-07-21 15:29:58+05:30  79.55      75
2025-07-21 15:29:59+05:30  78.20     150
2025-07-21 15:29:59+05:30  78.80      75
2025-07-21 15:30:00+05:30  78.80      75
2025-07-21 15:30:01+05:30  78.80      75
2025-08-12 09:02:06,569 [    INFO] backtest.backtest\_runner: Loaded and normalized data. Shape: (36151, 6). Time range: 2025-07-21 09:18:04+05:30 to 2025-07-21 15:30:01+05:30
2025-08-12 09:02:06,569 [    INFO] backtest.backtest\_runner: Applying session
filtering to data based on user configuration
2025-08-12 09:02:06,679 [    INFO] backtest.backtest\_runner: Filtered data from 36151 to 36150 rows based on user session timing
2025-08-12 09:02:06,680 [    INFO] backtest.backtest\_runner: Optimizing memory usage for large tick dataset (36150 ticks)
2025-08-12 09:02:06,681 [    INFO] backtest.backtest\_runner: Processing 36150
rows in chunks of 2000
2025-08-12 09:02:06,681 [    INFO] backtest.backtest\_runner: Starting sequential chunk-based indicator processing...
2025-08-12 09:02:06,682 [    INFO] backtest.backtest\_runner: Large dataset (36150 rows), using memory-optimized processing
2025-08-12 09:02:06,685 [    INFO] core.indicators: Calculating indicators with: RSI=14, FastEMA=9, SlowEMA=21, VWAP=15, MACD=12/26/9, VolMult=1.0
2025-08-12 09:02:06,686 [   ERROR] backtest.backtest\_runner: Memory-optimized
processing failed: 'ConfigAccessor' object has no attribute 'is\_indicator\_enabled', falling back to chunked
2025-08-12 09:02:06,689 [    INFO] backtest.backtest\_runner: = CHUNK PROCESSING DIAGNOSTICS =
2025-08-12 09:02:06,690 [    INFO] backtest.backtest\_runner: Input dataset: 36150 rows
2025-08-12 09:02:06,692 [    INFO] backtest.backtest\_runner: Chunk size: 2000
2025-08-12 09:02:06,701 [    INFO] backtest.backtest\_runner: Number of chunks: 19
2025-08-12 09:02:06,704 [    INFO] backtest.backtest\_runner: Processing chunk
1: rows 0-2000
2025-08-12 09:02:06,705 [    INFO] core.indicators: Calculating indicators with: RSI=14, FastEMA=9, SlowEMA=21, VWAP=15, MACD=12/26/9, VolMult=1.0
2025-08-12 09:02:06,705 [   ERROR] backtest.backtest\_runner: Error processing
chunk 0-2000: 'ConfigAccessor' object has no attribute 'is\_indicator\_enabled'
2025-08-12 09:02:06,706 [    INFO] core.indicators: Calculating indicators with: RSI=14, FastEMA=9, SlowEMA=21, VWAP=15, MACD=12/26/9, VolMult=1.0
2025-08-12 09:02:06,710 [   ERROR] backtest.backtest\_runner: CRITICAL BACKTEST ERROR: 'ConfigAccessor' object has no attribute 'is\_indicator\_enabled'
2025-08-12 09:02:06,710 [   ERROR] backtest.backtest\_runner: Error type: AttributeError
2025-08-12 09:02:06,720 [   ERROR] backtest.backtest\_runner: Full traceback:
Traceback (most recent call last):
File "C:\\Users\\user\\projects\\Perplexity Combined\\my quant\\backtest\\backtest\_runner.py", line 653, in process\_indicators\_sequential
chunk\_with\_indicators = strategy.calculate\_indicators(chunk\_df)
File "C:\\Users\\user\\projects\\Perplexity Combined\\my quant\\core\\researchStrategy.py", line 160, in calculate\_indicators
return calculate\_all\_indicators(df, self.config)
File "C:\\Users\\user\\projects\\Perplexity Combined\\my quant\\core\\indicators.py", line 188, in calculate\_all\_indicators
if config\_accessor.is\_indicator\_enabled('rsi') and len(df) >= rsi\_period:
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AttributeError: 'ConfigAccessor' object has no attribute 'is\_indicator\_enabled'
During handling of the above exception, another exception occurred:
Traceback (most recent call last):
File "C:\\Users\\user\\projects\\Perplexity Combined\\my quant\\backtest\\backtest\_runner.py", line 90, in run\_backtest
return \_run\_backtest\_internal(config, data\_file, df\_normalized, skip\_indicator\_calculation)
File "C:\\Users\\user\\projects\\Perplexity Combined\\my quant\\backtest\\backtest\_runner.py", line 216, in \_run\_backtest\_internal
df\_with\_indicators = process\_indicators\_sequential(df\_normalized, strategy, chunk\_size)
File "C:\\Users\\user\\projects\\Perplexity Combined\\my quant\\backtest\\backtest\_runner.py", line 684, in process\_indicators\_sequential
fallback\_indicators = strategy.calculate\_indicators(chunk\_df)
File "C:\\Users\\user\\projects\\Perplexity Combined\\my quant\\core\\researchStrategy.py", line 160, in calculate\_indicators
return calculate\_all\_indicators(df, self.config)
File "C:\\Users\\user\\projects\\Perplexity Combined\\my quant\\core\\indicators.py", line 188, in calculate\_all\_indicators
if config\_accessor.is\_indicator\_enabled('rsi') and len(df) >= rsi\_period:
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AttributeError: 'ConfigAccessor' object has no attribute 'is\_indicator\_enabled'
2025-08-12 09:02:06,741 [   ERROR] **main**: Error in backtest execution: 'ConfigAccessor' object has no attribute 'is\_indicator\_enabled'

Looking at your error, the issue is clear: the `ConfigAccessor` class in `config_helper.py` is missing the `is_indicator_enabled` method that the indicators module is trying to call.

## **Root Cause**

The error occurs in `core/indicators.py` at line 188:

```python
if config_accessor.is_indicator_enabled('rsi') and len(df) >= rsi_period:
```

But the `ConfigAccessor` class in `utils/config_helper.py` doesn't have this method defined.

## **Solution**

Add the missing `is_indicator_enabled` method to your `ConfigAccessor` class. Here's what you need to add to `utils/config_helper.py`:

```python
def is_indicator_enabled(self, indicator_name: str) -> bool:
    """
    Check if a specific indicator is enabled in the strategy configuration.
    
    Args:
        indicator_name: Name of the indicator to check
        
    Returns:
        True if indicator is enabled, False otherwise
    """
    # Map indicator names to their config keys
    indicator_map = {
        'rsi': 'use_rsi_filter',
        'ema_crossover': 'use_ema_crossover', 
        'macd': 'use_macd',
        'vwap': 'use_vwap',
        'htf_trend': 'use_htf_trend',
        'bollinger_bands': 'use_bollinger_bands',
        'stochastic': 'use_stochastic',
        'atr': 'use_atr',
        'ma': 'use_ma',
        'volume_ma': 'use_volume_ma'
    }
    
    config_key = indicator_map.get(indicator_name)
    if config_key:
        return self.get_strategy_param(config_key, False)
    
    # Fallback: check if the indicator name itself exists as a config key
    return self.get_strategy_param(f'use_{indicator_name}', False)
```


## **Complete Fix**

Add this method to your `ConfigAccessor` class in `utils/config_helper.py`. The complete updated class should look like:

```python
class ConfigAccessor:
    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def get_strategy_param(self, key: str, default: Any = None) -> Any:
        return self.config.get('strategy', {}).get(key, default)

    def get_risk_param(self, key: str, default: Any = None) -> Any:
        return self.config.get('risk', {}).get(key, default)

    def get_capital_param(self, key: str, default: Any = None) -> Any:
        return self.config.get('capital', {}).get(key, default)

    def get_instrument_param(self, key: str, default: Any = None) -> Any:
        return self.config.get('instrument', {}).get(key, default)

    def get_session_param(self, key: str, default: Any = None) -> Any:
        return self.config.get('session', {}).get(key, default)

    def get_backtest_param(self, key: str, default: Any = None) -> Any:
        return self.config.get('backtest', {}).get(key, default)

    def is_indicator_enabled(self, indicator_name: str) -> bool:
        """
        Check if a specific indicator is enabled in the strategy configuration.
        
        Args:
            indicator_name: Name of the indicator to check
            
        Returns:
            True if indicator is enabled, False otherwise
        """
        # Map indicator names to their config keys
        indicator_map = {
            'rsi': 'use_rsi_filter',
            'ema_crossover': 'use_ema_crossover', 
            'macd': 'use_macd',
            'vwap': 'use_vwap',
            'htf_trend': 'use_htf_trend',
            'bollinger_bands': 'use_bollinger_bands',
            'stochastic': 'use_stochastic',
            'atr': 'use_atr',
            'ma': 'use_ma',
            'volume_ma': 'use_volume_ma'
        }
        
        config_key = indicator_map.get(indicator_name)
        if config_key:
            return self.get_strategy_param(config_key, False)
        
        # Fallback: check if the indicator name itself exists as a config key
        return self.get_strategy_param(f'use_{indicator_name}', False)

    def validate_required_params(self) -> Dict[str, Any]:
        # ... existing validation code ...
```


## **Why This Works**

1. **Maps indicator names** to their actual configuration keys (e.g., 'rsi' → 'use_rsi_filter')
2. **Uses existing methods** like `get_strategy_param` to check if indicators are enabled
3. **Provides fallback logic** for any indicators not in the mapping
4. **Returns boolean values** as expected by the indicators module

After adding this method, your backtest should run successfully. The error occurs because your indicators module expects this method to exist but it was missing from the `ConfigAccessor` implementation.

<div style="text-align: center">⁂</div>

[^1]: unified_gui.py

[^2]: backtest_runner.py

[^3]: strategy_config.yaml

[^4]: indicators.py

[^5]: liveStrategy.py

[^6]: position_manager.py

[^7]: researchStrategy.py

[^8]: unified_gui.py

[^9]: cache_manager.py

[^10]: config_helper.py

[^11]: config_loader.py

[^12]: logging_utils.py

[^13]: simple_loader.py

[^14]: time_utils.py

