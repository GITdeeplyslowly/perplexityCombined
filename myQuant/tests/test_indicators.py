import pytest
from core.indicators import calculate_all_indicators
from core.config_accessor import ConfigAccessor

def test_rsi_indicator():
    config = ConfigAccessor()
    config.set_indicator_enabled('rsi', True)
    data = {'close': [1, 2, 3, 4, 5], 'volume': [1, 1, 1, 1, 1]}
    df = pd.DataFrame(data)
    result = calculate_all_indicators(df, config)
    assert 'rsi' in result.columns

def test_ema_indicator():
    config = ConfigAccessor()
    config.set_indicator_enabled('ema', True)
    data = {'close': [1, 2, 3, 4, 5], 'volume': [1, 1, 1, 1, 1]}
    df = pd.DataFrame(data)
    result = calculate_all_indicators(df, config)
    assert 'ema' in result.columns

def test_macd_indicator():
    config = ConfigAccessor()
    config.set_indicator_enabled('macd', True)
    data = {'close': [1, 2, 3, 4, 5], 'volume': [1, 1, 1, 1, 1]}
    df = pd.DataFrame(data)
    result = calculate_all_indicators(df, config)
    assert 'macd' in result.columns

def test_indicator_disabled():
    config = ConfigAccessor()
    config.set_indicator_enabled('rsi', False)
    data = {'close': [1, 2, 3, 4, 5], 'volume': [1, 1, 1, 1, 1]}
    df = pd.DataFrame(data)
    result = calculate_all_indicators(df, config)
    assert 'rsi' not in result.columns

def test_config_accessor_has_is_indicator_enabled():
    config = ConfigAccessor()
    assert hasattr(config, 'is_indicator_enabled')
