"""
Test script to verify WebSocket import fix.
This validates that exchange_mapper.py is now accessible and WebSocket streaming is available.
"""

import sys
import os

# Add myQuant to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'myQuant'))

print("=" * 60)
print("TESTING WEBSOCKET IMPORT FIX")
print("=" * 60)

# Test 1: exchange_mapper.py import
print("\n1. Testing exchange_mapper.py import...")
try:
    from exchange_mapper import map_to_angel_exchange_type
    print("   ✅ exchange_mapper imported successfully")
    
    # Test the mapping function
    nfo_type = map_to_angel_exchange_type("NFO")
    nse_type = map_to_angel_exchange_type("NSE")
    print(f"   ✅ NFO maps to: {nfo_type}")
    print(f"   ✅ NSE maps to: {nse_type}")
except Exception as e:
    print(f"   ❌ FAILED: {e}")

# Test 2: websocket_stream.py import
print("\n2. Testing websocket_stream.py import...")
try:
    from live.websocket_stream import WebSocketTickStreamer
    print("   ✅ WebSocketTickStreamer imported successfully")
except Exception as e:
    print(f"   ❌ FAILED: {e}")

# Test 3: broker_adapter.py WebSocket detection
print("\n3. Testing broker_adapter.py WebSocket detection...")
try:
    from live.broker_adapter import BrokerAdapter
    print("   ✅ BrokerAdapter imported successfully")
    
    # Check if WebSocketTickStreamer is available in BrokerAdapter
    from types import MappingProxyType
    test_config = MappingProxyType({
        'credentials': {
            'api_key': 'test',
            'client_code': 'test',
            'totp_secret': 'test'
        },
        'trading': {
            'paper_trading': True
        },
        'file_simulation': {
            'enabled': False
        },
        'data_source': {
            'mode': 'callback',
            'polling_interval': 1
        }
    })
    
    adapter = BrokerAdapter(test_config)
    
    if adapter.WebSocketTickStreamer is not None:
        print("   ✅ WebSocket streaming AVAILABLE in BrokerAdapter")
    else:
        print("   ❌ WebSocket streaming NOT available in BrokerAdapter")
        
except Exception as e:
    print(f"   ❌ FAILED: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("FIX SUMMARY:")
print("=" * 60)
print("✅ Copied exchange_mapper.py to myQuant/ directory")
print("✅ Fixed imports in websocket_stream.py (removed myQuant. prefix)")
print("✅ WebSocket streaming should now be available for live trading")
print("\nNext steps:")
print("- Restart live forward test")
print("- Verify log shows WebSocket available (not 'will use polling mode')")
print("- Confirm heartbeat displays actual prices instead of 'N/A'")
print("=" * 60)
