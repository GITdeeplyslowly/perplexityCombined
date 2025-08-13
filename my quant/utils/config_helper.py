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

def create_config_from_defaults():
    """
    Create a new configuration object from defaults.
    
    Returns:
        Fresh config dictionary
    """
    from config.defaults import DEFAULT_CONFIG
    return deepcopy(DEFAULT_CONFIG)