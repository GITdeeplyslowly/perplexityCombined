"""
core/indicators.py
Unified, parameter-driven indicator library for both backtest and live trading bot.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Tuple, Any
from utils.config_helper import ConfigAccessor

logger = logging.getLogger(__name__)

def safe_divide(numerator, denominator, default=0.0):
    """Enhanced safe division with comprehensive error handling."""
    try:
        if pd.isna(numerator) or pd.isna(denominator) or denominator == 0:
            return default
        return numerator / denominator
    except Exception:
        return default

def calculate_ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()

def calculate_sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(window=period).mean()

def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    fast_ema = calculate_ema(series, fast)
    slow_ema = calculate_ema(series, slow)
    macd_line = fast_ema - slow_ema
    signal_line = calculate_ema(macd_line, signal)
    histogram = macd_line - signal_line
    return pd.DataFrame({'macd': macd_line, 'signal': signal_line, 'histogram': histogram})

def calculate_vwap(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
    typical_price = (high + low + close) / 3
    cum_vol = volume.cumsum()
    cum_tpv = (typical_price * volume).cumsum()
    return cum_tpv / cum_vol

def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    high_low = high - low
    high_close = np.abs(high - close.shift())
    low_close = np.abs(low - close.shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

def calculate_htf_trend(close: pd.Series, period: int) -> pd.Series:
    return calculate_ema(close, period)

def calculate_stochastic(high, low, close, k_period: int, d_period: int) -> Tuple[pd.Series, pd.Series]:
    lowest_low = low.rolling(window=k_period).min()
    highest_high = high.rolling(window=k_period).max()
    k = 100 * (close - lowest_low) / (highest_high - lowest_low)
    d = k.rolling(window=d_period).mean()
    return k, d

def calculate_bollinger_bands(series: pd.Series, period: int = 20, std: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
    ma = series.rolling(window=period).mean()
    sd = series.rolling(window=period).std()
    upper = ma + (sd * std)
    lower = ma - (sd * std)
    return upper, ma, lower

def calculate_ema_crossover_signals(fast_ema: pd.Series, slow_ema: pd.Series) -> pd.DataFrame:
    """Calculate EMA crossover signals.
    
    Returns:
        pd.DataFrame with 'ema_bullish' column only (continuous state where fast > slow)
    """
    crossover = (fast_ema > slow_ema).fillna(False)
    # Only return the continuous state signal
    return pd.DataFrame({
        'ema_bullish': crossover  # Continuous state (fast > slow)
    })

def calculate_macd_signals(macd_df: pd.DataFrame) -> pd.DataFrame:
    above = (macd_df['macd'] > macd_df['signal']).fillna(False)
    prev = above.shift().fillna(False)
    return pd.DataFrame({
        'macd_buy_signal': above & (~prev),
        'macd_sell_signal': (~above) & prev,
        'macd_bullish': above,
        'macd_histogram_positive': (macd_df['histogram'] > 0).fillna(False)
    })

def calculate_htf_signals(close: pd.Series, htf_ema: pd.Series) -> pd.DataFrame:
    bullish = (close > htf_ema).fillna(False)
    return pd.DataFrame({
        'htf_bullish': bullish,
        'htf_bearish': ~bullish
    })

def calculate_vwap_signals(close: pd.Series, vwap: pd.Series) -> pd.DataFrame:
    bullish = (close > vwap).fillna(False)
    return pd.DataFrame({
        'vwap_bullish': bullish,
        'vwap_bearish': ~bullish
    })

def calculate_rsi_signals(rsi: pd.Series, overbought: float = 70, oversold: float = 30) -> pd.DataFrame:
    return pd.DataFrame({
        'rsi_oversold': (rsi <= oversold).fillna(False),
        'rsi_overbought': (rsi >= overbought).fillna(False),
        'rsi_neutral': ((rsi > oversold) & (rsi < overbought)).fillna(False)
    })

def calculate_all_indicators(df: pd.DataFrame, params: Dict, chunk_size=1000):
    """
    Calculate all indicators based on the provided configuration.
    Handles both flat and nested parameter formats.
    """
    # Create a consistent ConfigAccessor regardless of input format
    from utils.config_helper import create_nested_config_from_flat
    
    # Determine if we have nested or flat config
    is_nested = 'strategy' in params or any(isinstance(params.get(k), dict) for k in params)
    
    # Create consistent nested structure
    if is_nested:
        nested_params = params
    else:
        nested_params = create_nested_config_from_flat(params)
        
    # Create a single config accessor for all parameter access
    config_accessor = ConfigAccessor(nested_params)

    # Clone the dataframe to avoid modifying the original
    df = df.copy()
    
    # Get indicator periods from configuration
    rsi_period = config_accessor.get_strategy_param('rsi_period', 14)
    fast_ema = config_accessor.get_strategy_param('fast_ema', 20)
    slow_ema = config_accessor.get_strategy_param('slow_ema', 50)
    vwap_period = config_accessor.get_strategy_param('vwap_period', 15)
    macd_fast = config_accessor.get_strategy_param('macd_fast', 12)
    macd_slow = config_accessor.get_strategy_param('macd_slow', 26)
    macd_signal = config_accessor.get_strategy_param('macd_signal', 9)

    # Additional parameters that might be directly accessed
    atr_period = config_accessor.get_strategy_param('atr_period', 14)
    bollinger_period = config_accessor.get_strategy_param('bollinger_period', 20)
    bollinger_std = config_accessor.get_strategy_param('bollinger_std', 2.0)

    # Any conditional logic using strategy_params
    if config_accessor.get_strategy_param('use_custom_indicators', False):
        # Custom indicator setup
        custom_period = config_accessor.get_strategy_param('custom_period', 10)
        # Custom indicator logic...

    # Any visualization settings
    show_signals = config_accessor.get_strategy_param('show_signals', True)
    signal_line_style = config_accessor.get_strategy_param('signal_line_style', '-')

    # Any direct dictionary access without defaults
    threshold = config_accessor.get_strategy_param('custom_threshold', None)
    if threshold is not None:
        # Custom threshold logic...
        pass  # Add actual logic or use pass as placeholder

    # Any nested parameter access
    # Handle nested parameters safely
    try:
        advanced_config = config_accessor.config.get('strategy', {}).get('advanced', {})
        filter_settings = advanced_config.get('filter_settings', {})
        filter_type = filter_settings.get('type', 'simple')
    except (AttributeError, KeyError):
        filter_type = 'simple'  # Default fallback
    
    # Set volume threshold scaling factor
    volume_multiplier = config_accessor.get_strategy_param('volume_multiplier', 1.0)

    # Log the parameters being used for transparency
    logger.info(f"Calculating indicators with: RSI={rsi_period}, FastEMA={fast_ema}, " +
               f"SlowEMA={slow_ema}, VWAP={vwap_period}, " +
               f"MACD={macd_fast}/{macd_slow}/{macd_signal}, VolMult={volume_multiplier}")
    
    # Calculate enabled indicators based on config
    if config_accessor.is_indicator_enabled('rsi') and len(df) >= rsi_period:
        df['rsi'] = calculate_rsi(df['close'], period=rsi_period)
        
    if config_accessor.is_indicator_enabled('ema_crossover'):
        df['fast_ema'] = calculate_ema(df['close'], fast_ema)
        df['slow_ema'] = calculate_ema(df['close'], slow_ema)
        crossover_signals = calculate_ema_crossover_signals(df['fast_ema'], df['slow_ema'])
        df['ema_bullish'] = crossover_signals['ema_bullish']
        
    if config_accessor.is_indicator_enabled('macd'):
        macd_df = calculate_macd(df['close'], macd_fast, macd_slow, macd_signal)
        df = df.join(macd_df)
        macd_signals = calculate_macd_signals(macd_df)
        df = df.join(macd_signals.add_prefix('macd_'))
        
    if config_accessor.is_indicator_enabled('vwap') and all(col in df.columns for col in ['high', 'low', 'close', 'volume']):
        df['vwap'] = calculate_vwap(df['high'], df['low'], df['close'], df['volume'])
        vwap_signals = calculate_vwap_signals(df['close'], df['vwap'])
        df = df.join(vwap_signals.add_prefix('vwap_'))
        
    if config_accessor.is_indicator_enabled('htf_trend'):
        df['htf_ema'] = calculate_htf_trend(df['close'], config_accessor.get_strategy_param("htf_period", 20))
        htf_signals = calculate_htf_signals(df['close'], df['htf_ema'])
        df = df.join(htf_signals.add_prefix('htf_'))
        
    if config_accessor.is_indicator_enabled('bollinger_bands'):
        upper, mid, lower = calculate_bollinger_bands(df['close'], config_accessor.get_strategy_param("bb_period", 20), config_accessor.get_strategy_param("bb_std", 2))
        df["bb_upper"], df["bb_middle"], df["bb_lower"] = upper, mid, lower
        
    if config_accessor.is_indicator_enabled('stochastic'):
        k, d = calculate_stochastic(df['high'], df['low'], df['close'], config_accessor.get_strategy_param("stoch_k", 14), config_accessor.get_strategy_param("stoch_d", 3))
        df["stoch_k"], df["stoch_d"] = k, d
        
    if config_accessor.is_indicator_enabled('atr'):
        df["atr"] = calculate_atr(df["high"], df["low"], df["close"], config_accessor.get_strategy_param("atr_len", 14))
        
    if config_accessor.is_indicator_enabled('ma'):
        df["ma_short"] = calculate_sma(df["close"], config_accessor.get_strategy_param("ma_short", 20))
        df["ma_long"] = calculate_sma(df["close"], config_accessor.get_strategy_param("ma_long", 50))
        
    if config_accessor.is_indicator_enabled('volume_ma') and "volume" in df.columns:
        df["volume_ma"] = calculate_sma(df["volume"], config_accessor.get_strategy_param("volume_ma_period", 20))
        df["volume_ratio"] = safe_divide(df["volume"], df["volume_ma"])
    
    # Log the total indicators calculated
    calculated_indicators = [col for col in df.columns if col not in ['open', 'high', 'low', 'close', 'volume', 'datetime']]
    logger.info(f"Calculated {len(calculated_indicators)} indicators: {calculated_indicators[:5]}...")

    return df

from typing import Tuple

# --- Incremental EMA ---
def update_ema(price: float, prev_ema: float, period: int) -> float:
    """
    Incremental EMA update formula.
    """
    alpha = 2 / (period + 1)
    return (price - prev_ema) * alpha + prev_ema

class IncrementalEMA:
    """
    Incremental EMA tracker holding its own state.
    """
    def __init__(self, period: int, first_price: float = None):
        self.period = period
        self.ema = first_price
    def update(self, price: float) -> float:
        if self.ema is None:
            self.ema = price
        else:
            self.ema = update_ema(price, self.ema, self.period)
        return self.ema

# --- Incremental MACD as previously integrated ---
class IncrementalMACD:
    """
    Incremental MACD, Signal line, Histogram.
    """
    def __init__(self, fast=12, slow=26, signal=9, first_price=None):
        self.fast = fast
        self.slow = slow
        self.signal = signal
        self.fast_ema = first_price
        self.slow_ema = first_price
        self.macd = 0.0
        self.signal_line = 0.0
    def update(self, price: float) -> Tuple[float, float, float]:
        if self.fast_ema is None or self.slow_ema is None:
            self.fast_ema = self.slow_ema = price
            self.macd = 0.0
            self.signal_line = 0.0
        else:
            self.fast_ema = update_ema(price, self.fast_ema, self.fast)
            self.slow_ema = update_ema(price, self.slow_ema, self.slow)
            self.macd = self.fast_ema - self.slow_ema
            self.signal_line = update_ema(self.macd, self.signal_line, self.signal)
        histogram = self.macd - self.signal_line
        return self.macd, self.signal_line, histogram

# --- Incremental VWAP (per session/day) ---
class IncrementalVWAP:
    """
    Incremental VWAP for intraday/session use with robust error handling.
    """
    def __init__(self):
        self.cum_tpv = 0.0
        self.cum_vol = 0.0
        self.last_vwap = None  # Store last valid VWAP for fallback
        
    def update(self, price, volume, high=None, low=None, close=None):
        try:
            # Validate inputs
            if pd.isna(price) or price <= 0:
                return self.last_vwap if self.last_vwap is not None else price
                
            # Handle invalid volume
            if pd.isna(volume) or volume < 0:
                volume = 0
                
            if high is not None and low is not None and close is not None:
                if not (pd.isna(high) or pd.isna(low) or pd.isna(close)):
                    typical_price = (high + low + close) / 3
                else:
                    typical_price = price
            else:
                typical_price = price
                
            self.cum_tpv += typical_price * volume
            self.cum_vol += volume
            
            # Safe calculation with fallback
            if self.cum_vol > 0:
                self.last_vwap = self.cum_tpv / self.cum_vol
            else:
                self.last_vwap = typical_price
                
            return self.last_vwap
        except Exception as e:
            logger.error(f"VWAP calculation error: {str(e)}")
            return self.last_vwap if self.last_vwap is not None else price
            
    def reset(self):
        self.cum_tpv = 0.0
        self.cum_vol = 0.0
        # Don't reset last_vwap to maintain a value during transitions

class IncrementalATR:
    """
    Incremental ATR, using Welles Wilder smoothing with robust error handling.
    """
    def __init__(self, period=14, first_close=None):
        self.period = period
        self.atr = None
        self.prev_close = first_close
        self.initialized = False
        self.tr_queue = []
        
    def update(self, high, low, close):
        try:
            # Validate inputs
            if pd.isna(high) or pd.isna(low) or pd.isna(close):
                return self.atr if self.atr is not None else 0.0
                
            # Ensure high >= low (data consistency)
            if high < low:
                high, low = low, high  # Swap if inverted
                
            if self.prev_close is None:
                tr = high - low
            else:
                tr = max(
                    high - low,
                    abs(high - self.prev_close),
                    abs(low - self.prev_close)
                )
                
            if not self.initialized:
                self.tr_queue.append(tr)
                if len(self.tr_queue) == self.period:
                    self.atr = sum(self.tr_queue) / self.period
                    self.initialized = True
            else:
                self.atr = (self.atr * (self.period - 1) + tr) / self.period
                
            self.prev_close = close
            return self.atr if self.atr is not None else tr
        except Exception as e:
            logger.error(f"ATR calculation error: {str(e)}")
            return self.atr if self.atr is not None else 0.0

class IncrementalEMA:
    """
    Incremental EMA tracker with robust error handling.
    """
    def __init__(self, period: int, first_price: float = None):
        self.period = period
        self.ema = first_price
        
    def update(self, price: float) -> float:
        try:
            # Validate input
            if pd.isna(price):
                return self.ema  # Return last value if available
                
            if self.ema is None:
                self.ema = price
            else:
                self.ema = update_ema(price, self.ema, self.period)
            return self.ema
        except Exception as e:
            logger.error(f"EMA calculation error: {str(e)}")
            return self.ema if self.ema is not None else price

class IncrementalMACD:
    """
    Incremental MACD with robust error handling.
    """
    def __init__(self, fast=12, slow=26, signal=9, first_price=None):
        self.fast = fast
        self.slow = slow
        self.signal = signal
        self.fast_ema = first_price
        self.slow_ema = first_price
        self.macd = 0.0
        self.signal_line = 0.0
        
    def update(self, price: float) -> Tuple[float, float, float]:
        try:
            # Validate input
            if pd.isna(price):
                return self.macd, self.signal_line, (self.macd - self.signal_line)
                
            if self.fast_ema is None or self.slow_ema is None:
                self.fast_ema = self.slow_ema = price
                self.macd = 0.0
                self.signal_line = 0.0
            else:
                self.fast_ema = update_ema(price, self.fast_ema, self.fast)
                self.slow_ema = update_ema(price, self.slow_ema, self.slow)
                self.macd = self.fast_ema - self.slow_ema
                self.signal_line = update_ema(self.macd, self.signal_line, self.signal)
                
            histogram = self.macd - self.signal_line
            return self.macd, self.signal_line, histogram
        except Exception as e:
            logger.error(f"MACD calculation error: {str(e)}")
            return self.macd, self.signal_line, (self.macd - self.signal_line)


"""
PARAMETER NAMING CONVENTION:
- Main function: calculate_all_indicators(df: pd.DataFrame, params: Dict)
- Parameter name 'params' is MANDATORY for interface compatibility
- All internal usage: params.get('parameter_name', default)

INTERFACE REQUIREMENT:
- The 'params' parameter name CANNOT be changed as it's used by:
  * researchStrategy.py: calculate_all_indicators(df, self.config)  
  * liveStrategy.py: calculate_all_indicators(df, self.config)
  * Multiple indicator calculation functions

CRITICAL: 
- Strategy modules pass their self.config as 'params' to this module
- This creates the interface boundary between 'config' (strategies) and 'params' (indicators)
- Do NOT change 'params' parameter name without updating ALL calling code
"""
