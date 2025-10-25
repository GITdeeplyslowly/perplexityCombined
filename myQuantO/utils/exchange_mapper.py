# exchange_mapper.py - Angel One Exchange Type Mapping Utility
"""
Map internal exchange codes to Angel One SmartAPI exchange_type integers.
Based on proven Wind implementation working for months.
"""

def map_to_angel_exchange_type(exchange_code):
    """
    Convert internal exchange codes to Angel One SmartAPI exchange_type integers.
    
    Based on Wind's proven implementation:
    - exchange_type=1: NSE_FO (Futures & Options) 
    - exchange_type=2: NSE_CM (Cash Market)
    - exchange_type=3: BSE (Bombay Stock Exchange)
    
    Args:
        exchange_code (str): Internal exchange code ("NFO", "NSE", "BFO", or full Angel One codes)
        
    Returns:
        int: Angel One exchange_type integer
        
    Raises:
        ValueError: If exchange_code is not supported
    """
    mapping = {
        # Our internal codes (CORRECTED based on Wind's proven implementation)
        "NFO": 2,  # NSE Futures & Options (NSE_FO = 2 in Wind)
        "NSE": 1,  # NSE Cash Market (NSE_CM = 1 in Wind)
        "BFO": 4,  # BSE Futures & Options (BSE_FO = 4 in Wind)
        
        # Angel One full format codes (Wind's exact mapping)
        "NSE_FO": 2,  # NSE Futures & Options
        "NSE_CM": 1,  # NSE Cash Market
        "BSE_FO": 4,  # BSE Futures & Options
        "BSE_CM": 3,  # BSE Cash Market
        "MCX_FO": 5,  # MCX Futures & Options
        "NCDEX_FO": 7,  # NCDEX Futures & Options
    }
    
    if exchange_code not in mapping:
        raise ValueError(f"Unsupported exchange code: {exchange_code}. Supported: {list(mapping.keys())}")
    
    return mapping[exchange_code]

def map_from_angel_exchange_type(exchange_type):
    """
    Convert Angel One exchange_type integers back to internal exchange codes.
    
    Args:
        exchange_type (int): Angel One exchange_type integer
        
    Returns:
        str: Internal exchange code
        
    Raises:
        ValueError: If exchange_type is not supported
    """
    reverse_mapping = {
        1: "NSE",  # NSE Cash Market (NSE_CM)
        2: "NFO",  # NSE Futures & Options (NSE_FO)
        3: "BSE_CM",  # BSE Cash Market
        4: "BFO",  # BSE Futures & Options (BSE_FO)
        5: "MCX_FO",  # MCX Futures & Options
        7: "NCDEX_FO",  # NCDEX Futures & Options
    }
    
    if exchange_type not in reverse_mapping:
        raise ValueError(f"Unsupported exchange_type: {exchange_type}. Supported: {list(reverse_mapping.keys())}")
    
    return reverse_mapping[exchange_type]

# Validation helper
def validate_exchange_compatibility(exchange_code, symbol=None):
    """
    Validate that exchange code is compatible with Angel One API.
    
    Args:
        exchange_code (str): Exchange code to validate
        symbol (str, optional): Symbol for error context
        
    Returns:
        bool: True if compatible
        
    Raises:
        ValueError: If not compatible with detailed message
    """
    try:
        angel_type = map_to_angel_exchange_type(exchange_code)
        # Removed verbose per-symbol logging - only log errors
        return True
    except ValueError as e:
        context = f" for symbol {symbol}" if symbol else ""
        raise ValueError(f"Exchange validation failed{context}: {e}")
