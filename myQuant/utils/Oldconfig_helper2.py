"""
config_helper.py - Simplified Configuration Access Helper
"""
from typing import Dict, Any, Optional, List
from copy import deepcopy
import logging

logger = logging.getLogger(__name__)

class ConfigAccessor:
    """
    Helper class for accessing configuration parameters in a nested dictionary.
    Simplifies access and provides consistent defaults.
    """
    def __init__(self, config: Dict[str, Any]):
        self.config = config if config else {}
        
    def get(self, path: str, default: Any = None) -> Any:
        """Get value from nested config using dot notation"""
        parts = path.split('.')
        current = self.config
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default
                
        return current
    
    def get_strategy_param(self, param_name: str, default: Any = None) -> Any:
        """
        Get a strategy parameter with fallback to default.
        
        Args:
            param_name: Parameter name
            default: Default value if parameter is missing
        
        Returns:
            Parameter value
        """
        if 'strategy' not in self.config:
            return default
            
        return self.config['strategy'].get(param_name, default)
    
    def get_risk_param(self, param_name: str, default: Any = None) -> Any:
        """
        Get a risk parameter with fallback to default.
        
        Args:
            param_name: Parameter name
            default: Default value if parameter is missing
        
        Returns:
            Parameter value
        """
        if 'risk' not in self.config:
            return default
            
        return self.config['risk'].get(param_name, default)
    
    def get_capital_param(self, param_name: str, default: Any = None) -> Any:
        """
        Get a capital parameter from the nested config['capital'] section.
        Warn if section is missing.
        """
        if 'capital' not in self.config:
            logger.warning(f"Config missing 'capital' section. Please update your config to use nested structure: config['capital']['{param_name}']")
            return default
        return self.config['capital'].get(param_name, default)
        
    def validate_required_params(self) -> Dict[str, Any]:
        """
        Validate that required parameters exist in config.
        
        Returns:
            Dict with validation status
        """
        missing = []
        required_paths = [
            'strategy.strategy_version',
            'session.start_hour',
            'session.end_hour'
        ]
        
        for path in required_paths:
            if self.get(path) is None:
                missing.append(path)
                
        return {"valid": len(missing) == 0, "errors": missing}

    def is_indicator_enabled(self, indicator_name: str) -> bool:
        """
        Check if an indicator is enabled in the strategy config.
        Example: is_indicator_enabled('rsi') checks 'use_rsi_filter'
        """
        # Map indicator names to config keys
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
        key = indicator_map.get(indicator_name, indicator_name)
        return bool(self.config.get('strategy', {}).get(key, False))

def create_config_from_defaults():
    """
    Create a new configuration object from defaults.
    
    Returns:
        Fresh config dictionary
    """
    from config.defaults import DEFAULT_CONFIG
    return deepcopy(DEFAULT_CONFIG)

def create_nested_config_from_flat(flat: dict) -> dict:
    """
    Convert a flat config dict with keys like 'strategy_fast_ema' to a nested dict:
    {'strategy': {'fast_ema': ...}, ...}
    """
    nested = {}
    for key, value in flat.items():
        if '_' in key:
            section, param = key.split('_', 1)
            if section not in nested:
                nested[section] = {}
            nested[section][param] = value
        else:
            nested[key] = value
    return nested