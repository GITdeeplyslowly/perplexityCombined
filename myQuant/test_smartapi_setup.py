#!/usr/bin/env python3
"""
Quick test to check SmartAPI availability and broker adapter configuration
"""

def test_smartapi_availability():
    """Test if SmartAPI is available"""
    print("Testing SmartAPI availability...")
    
    try:
        from SmartApi import SmartConnect
        print("✅ SmartAPI package is available")
        print(f"   SmartConnect class: {SmartConnect}")
        return True
    except ImportError as e:
        print(f"❌ SmartAPI package not available: {e}")
        print("💡 Install with: pip install smartapi-python")
        return False

def test_broker_adapter_config():
    """Test broker adapter configuration"""
    print("\nTesting broker adapter configuration...")
    
    try:
        # Create a minimal test config
        from types import MappingProxyType
        
        test_config = MappingProxyType({
            "live": {
                "paper_trading": True,  # Forward test mode
                "api_key": "test_key",
                "client_code": "test_client"
            },
            "instrument": {
                "symbol": "NIFTY14OCT2525200PE",
                "exchange": "NFO",
                "product_type": "MIS",
                "lot_size": 75,
                "tick_size": 0.05,
                "token": "42690"
            },
            "data_simulation": {
                "enabled": False  # Live webstream mode
            }
        })
        
        print("Test config created:")
        print(f"  Paper Trading: {test_config['live']['paper_trading']}")
        print(f"  Data Simulation: {test_config['data_simulation']['enabled']}")
        print(f"  Symbol: {test_config['instrument']['symbol']}")
        
        # Try to create broker adapter
        from live.broker_adapter import BrokerAdapter
        broker = BrokerAdapter(test_config)
        
        print("✅ BrokerAdapter created successfully")
        print(f"   Paper Trading Mode: {broker.paper_trading}")
        print(f"   Has File Simulator: {broker.file_simulator is not None}")
        print(f"   Has SmartConnect: {broker.SmartConnect is not None}")
        
        return True
        
    except Exception as e:
        print(f"❌ BrokerAdapter creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("SMARTAPI AND BROKER ADAPTER TEST")
    print("=" * 60)
    
    smartapi_ok = test_smartapi_availability()
    broker_ok = test_broker_adapter_config()
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"SmartAPI Available: {'✅ YES' if smartapi_ok else '❌ NO'}")
    print(f"BrokerAdapter OK: {'✅ YES' if broker_ok else '❌ NO'}")
    
    if not smartapi_ok:
        print("\n🔧 SOLUTION:")
        print("   Install SmartAPI: pip install smartapi-python")
        print("   Then restart the application")
    
    if smartapi_ok and broker_ok:
        print("\n✅ All components ready for live webstream forward testing!")
    else:
        print("\n❌ Issues detected - forward testing will fail")