class TestConfigAccessor:
    def test_is_indicator_enabled(self):
        config_accessor = ConfigAccessor()
        assert hasattr(config_accessor, 'is_indicator_enabled')
        
        # Assuming default behavior is to return False for disabled indicators
        assert config_accessor.is_indicator_enabled('rsi') is False
        assert config_accessor.is_indicator_enabled('ema') is False
        
        # Mock enabling the RSI indicator
        config_accessor.enable_indicator('rsi')
        assert config_accessor.is_indicator_enabled('rsi') is True
        
        # Mock disabling the RSI indicator
        config_accessor.disable_indicator('rsi')
        assert config_accessor.is_indicator_enabled('rsi') is False
