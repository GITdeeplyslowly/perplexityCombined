#!/usr/bin/env python3
"""
Test SmartAPI methods and WebSocket initialization
"""

def test_smartapi_methods():
    """Test SmartConnect methods available"""
    print("=" * 60)
    print("SMARTAPI METHODS TEST")
    print("=" * 60)
    
    try:
        from SmartApi import SmartConnect
        
        # Create a dummy instance to check methods
        smart = SmartConnect(api_key="dummy")
        
        # Check available methods
        methods = [method for method in dir(smart) if not method.startswith('_')]
        print("Available SmartConnect methods:")
        
        # Look for LTP-related methods
        ltp_methods = [m for m in methods if 'ltp' in m.lower() or 'data' in m.lower()]
        print("\nLTP/Data related methods:")
        for method in ltp_methods:
            print(f"  - {method}")
        
        # Check specific methods we need
        needed_methods = ['ltpData', 'getLTP', 'getfeedToken', 'generateSession']
        print("\nChecking needed methods:")
        for method in needed_methods:
            exists = hasattr(smart, method)
            print(f"  {method}: {'✅' if exists else '❌'}")
            
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_websocket_import():
    """Test WebSocket imports"""
    print("\n" + "=" * 60)
    print("WEBSOCKET IMPORT TEST")
    print("=" * 60)
    
    try:
        from SmartApi.smartWebSocketV2 import SmartWebSocketV2
        print("✅ SmartWebSocketV2 import successful")
        
        # Check constructor signature
        import inspect
        sig = inspect.signature(SmartWebSocketV2.__init__)
        print(f"Constructor signature: {sig}")
        
        return True
        
    except Exception as e:
        print(f"❌ SmartWebSocketV2 import failed: {e}")
        
        # Try alternative imports
        try:
            from SmartApi.smartApiWebsocket import SmartWebSocket
            print("✅ SmartWebSocket (v1) import successful")
            return True
        except Exception as e2:
            print(f"❌ SmartWebSocket (v1) also failed: {e2}")
            return False

if __name__ == "__main__":
    print("SMARTAPI COMPATIBILITY TEST")
    print("=" * 60)
    
    methods_ok = test_smartapi_methods()
    websocket_ok = test_websocket_import()
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"SmartConnect Methods: {'✅ OK' if methods_ok else '❌ ISSUES'}")
    print(f"WebSocket Import: {'✅ OK' if websocket_ok else '❌ ISSUES'}")
    
    if methods_ok and websocket_ok:
        print("\n✅ SmartAPI is ready for use!")
    else:
        print("\n❌ SmartAPI compatibility issues detected")