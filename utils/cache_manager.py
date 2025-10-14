"""
utils/cache_manager.py

Simple symbol/token cache manager replicating angelalgo windsurf approach
- Simple symbol:token mapping for fast lookup
- Direct fetch from Angel One API
- Compatible with GUI autocomplete
"""

import os
import json
import requests
from datetime import datetime

# Default cache file path - exactly like angelalgo windsurf
DEFAULT_CACHE_PATH = os.path.join("smartapi", "symbol_cache.json")
DEFAULT_MASTER_URL = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"

def load_symbol_cache(path: str = DEFAULT_CACHE_PATH) -> dict:
    """
    Load symbol-token mapping from cache exactly like angelalgo windsurf.
    
    Returns:
        symbol_token_map (dict): { 'NIFTY': '99926000', 'BANKNIFTY': '99926009', ... }
    """
    if not os.path.exists(path):
        # Try to fetch from online if cache doesn't exist
        print(f"Cache file not found at {path}, fetching from API...")
        return fetch_and_cache_symbols(path)
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            cache_data = json.load(f)
        
        # Expect angelalgo windsurf format: {"timestamp": "...", "symbols": {"symbol": "token", ...}}
        if "symbols" in cache_data:
            symbols = cache_data["symbols"]
            # Return the simple symbol:token mapping
            return symbols if isinstance(symbols, dict) else {}
        else:
            # If old format, return empty and force refresh
            print("Old cache format detected, forcing refresh...")
            return fetch_and_cache_symbols(path)
            
    except Exception as e:
        print(f"Error loading cache: {e}")
        return fetch_and_cache_symbols(path)

def fetch_and_cache_symbols(path: str = DEFAULT_CACHE_PATH, url: str = DEFAULT_MASTER_URL) -> dict:
    """
    Fetch symbols from Angel One API and cache them using exact angelalgo windsurf format.
    
    Returns:
        symbol_token_map (dict): { 'NIFTY': '99926000', ... }
    """
    try:
        print("Fetching symbols from Angel One API...")
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        data = response.json()
        
        # Create simple symbol:token mapping exactly like angelalgo windsurf
        symbol_token_map = {}
        for entry in data:
            symbol = entry.get("symbol")
            token = entry.get("token")
            if symbol and token:
                symbol_token_map[symbol] = str(token)  # Ensure token is string
        
        # Save to cache in angelalgo windsurf format
        save_cache(symbol_token_map, path)
        
        print(f"âœ… Cached {len(symbol_token_map)} symbols to {path}")
        return symbol_token_map
        
    except Exception as e:
        print(f"âŒ Error fetching symbols: {e}")
        return {}

def save_cache(symbol_token_map: dict, path: str = DEFAULT_CACHE_PATH):
    """Save symbol-token mapping to cache file in exact angelalgo windsurf format."""
    try:
        # Ensure directory exists
        cache_dir = os.path.dirname(path)
        if cache_dir:
            os.makedirs(cache_dir, exist_ok=True)
        
        # Use exact format from angelalgo windsurf
        cache_data = {
            "timestamp": datetime.now().isoformat(),
            "symbols": symbol_token_map
        }
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, indent=2)
            
        print(f"âœ… Symbol cache saved to {path}")
        
    except Exception as e:
        print(f"âŒ Error saving cache: {e}")

def refresh_symbol_cache(path: str = DEFAULT_CACHE_PATH) -> int:
    """
    Manually refresh the symbol cache.
    
    Returns:
        count (int): number of symbols cached
    """
    symbol_token_map = fetch_and_cache_symbols(path)
    return len(symbol_token_map)

def get_token_for_symbol(symbol: str, path: str = DEFAULT_CACHE_PATH) -> str:
    """Get token for a specific symbol."""
    try:
        symbols = load_symbol_cache(path)
        return symbols.get(symbol, "")
    except:
        return ""

def get_symbols_list(path: str = DEFAULT_CACHE_PATH) -> list:
    """Get sorted list of all symbols."""
    try:
        symbols = load_symbol_cache(path)
        return sorted(symbols.keys())
    except:
        return []

def cache_last_refresh(path: str = DEFAULT_CACHE_PATH) -> str:
    """Return the timestamp of the last cache refresh."""
    if not os.path.exists(path):
        return "Never"
    try:
        with open(path, "r", encoding="utf-8") as f:
            cache_data = json.load(f)
        return cache_data.get("timestamp", "Unknown")
    except:
        return "Error reading cache"

# Test/CLI usage
if __name__ == "__main__":
    print("Testing cache manager (angelalgo windsurf style)...")
    symbols = load_symbol_cache()
    print(f"Loaded {len(symbols)} symbols")
    
    if symbols:
        # Show first 5 symbols
        for i, (symbol, token) in enumerate(symbols.items()):
            if i >= 5:
                break
            print(f"  {symbol}: {token}")
        
        print(f"Last refresh: {cache_last_refresh()}")
    else:
        print("No symbols loaded. Refreshing the cache...")
        count = refresh_symbol_cache()
        print(f"Refreshed cache with {count} symbols.")

def get_symbol_details(symbol: str, path: str = DEFAULT_CACHE_PATH) -> dict:
    """
    Retrieve a single symbol's details from cache (angelalgo windsurf style).
    Returns simple format: {"token": "99926000", "symbol": "NIFTY"}
    """
    symbols = load_symbol_cache(path)
    token = symbols.get(symbol, "")
    
    if token:
        return {"token": token, "symbol": symbol}
    else:
        return {}

def is_simple_format(path: str = DEFAULT_CACHE_PATH) -> bool:
    """
    Check if the cache uses simple format (symbol -> token) - angelalgo windsurf style.
    """
    try:
        symbols = load_symbol_cache(path)
        if symbols:
            first_value = next(iter(symbols.values()))
            return isinstance(first_value, str)
        return True  # Default to simple format
    except:
        return True

# Example CLI usage for manual refresh
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "refresh":
        print("Refreshing Angel One SmartAPI symbol cache...")
        count = refresh_symbol_cache()
        print(f"âœ… Loaded {count} symbols into cache.")
        print(f"Last refresh: {cache_last_refresh()}")
    else:
        print("Testing cache manager (angelalgo windsurf style)...")
        symbols = load_symbol_cache()
        print(f"Loaded {len(symbols)} symbols")
        
        if symbols:
            # Show first 5 symbols
            for i, (symbol, token) in enumerate(symbols.items()):
                if i >= 5:
                    break
                print(f"  {symbol}: {token}")
            
            print(f"Last refresh: {cache_last_refresh()}")
        else:
            print("No symbols loaded. Refreshing the cache...")
            count = refresh_symbol_cache()
            print(f"✅ Refreshed cache with {count} symbols.")
