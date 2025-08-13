"""
config_loader.py - Compatibility layer for the new defaults-based configuration

This module provides backward compatibility for code that still uses config_loader.
It redirects to the defaults.py-based configuration system.
"""

from typing import Dict, Any, Optional
from pathlib import Path
import logging
from copy import deepcopy
import os
import json

# Import defaults and helper
from config.defaults import DEFAULT_CONFIG
from utils.config_helper import create_config_from_defaults

logger = logging.getLogger(__name__)

def load_config(config_path: str = None) -> Dict[str, Any]:
    """
    Load configuration - now simply returns a copy of the defaults
    with optional user preferences applied.
    
    Args:
        config_path: Path to config file (ignored, kept for compatibility)
        
    Returns:
        Complete configuration dictionary
    """
    logger.info("Using defaults.py-based configuration (YAML no longer used)")
    
    # Start with defaults
    config = create_config_from_defaults()
    
    # Optionally apply user preferences if they exist
    prefs_file = "user_preferences.json"
    if os.path.exists(prefs_file):
        try:
            with open(prefs_file, 'r') as f:
                user_prefs = json.load(f)
                
            # Apply preferences to config
            for key_path, value in user_prefs.items():
                # Handle dot notation paths
                parts = key_path.split('.')
                if len(parts) == 2:
                    section, param = parts
                    if section in config and param in config[section]:
                        config[section][param] = value
                        
            logger.info(f"Applied user preferences from {prefs_file}")
        except Exception as e:
            logger.error(f"Failed to load user preferences: {e}")
    
    return config

def merge_configs(base_config: Dict[str, Any], override_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge configurations - kept for compatibility
    """
    result = deepcopy(base_config)
    
    for section, params in override_config.items():
        if section not in result:
            result[section] = {}
            
        if isinstance(params, dict):
            for param, value in params.items():
                result[section][param] = value
    
    return result

# Keep minimal versions of other functions for compatibility
def _validate_and_apply_defaults(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply defaults - now just a wrapper around create_config_from_defaults
    with merging of any provided values.
    """
    base_config = create_config_from_defaults()
    return merge_configs(base_config, config) if config else base_config
