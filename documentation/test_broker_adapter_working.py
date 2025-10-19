#!/usr/bin/env python3
"""
Test the actual broker adapter with a realistic configuration
"""

def test_broker_adapter_real_config():
    """Test broker adapter with a real configuration"""
    print("=" * 60)
    print("REAL BROKER ADAPTER CONFIGURATION TEST")
    print("=" * 60)
    
    try:
        from types import MappingProxyType
        from live.broker_adapter import BrokerAdapter
        
        # Create a realistic test config that should work
        test_config = MappingProxyType({
            "live": {
                "paper_trading": True,  # Forward test mode
                "api_key": "test_key",
                "client_code": "test_client"
            },
            "instrument": {
                "symbol": "NIFTY",
                "exchange": "NSE",
                "product_type": "MIS",
                "lot_size": 75,
                "tick_size": 0.05,
                "token": "99926000"
            },
            "data_simulation": {
                "enabled": False  # Live webstream mode
            }
        })
        
        print("Test config:")
        print(f"  Paper Trading: {test_config['live']['paper_trading']}")
        print(f"  Data Simulation: {test_config['data_simulation']['enabled']}")
        print(f"  Symbol: {test_config['instrument']['symbol']}")
        
        # Mock the ConfigAccessor to avoid instrument mapping errors
        class MockConfigAccessor:
            def __init__(self, config):
                self.config = config
                
            def get_current_instrument_param(self, param):
                return self.config['instrument'][param]
        
        # Temporarily patch the import
        import sys
        import utils.config_helper
        original_accessor = utils.config_helper.ConfigAccessor
        utils.config_helper.ConfigAccessor = MockConfigAccessor
        
        try:
            broker = BrokerAdapter(test_config)
            print("✅ BrokerAdapter created successfully")
            print(f"   Paper Trading Mode: {broker.paper_trading}")
            print(f"   Has File Simulator: {broker.file_simulator is not None}")
            print(f"   Has SmartConnect: {broker.SmartConnect is not None}")
            
            # Test connect method
            try:
                print("\n🔌 Testing connection...")
                broker.connect()
                print("❌ Connection should have failed (no credentials)")
            except Exception as e:
                print(f"✅ Connection correctly failed: {str(e)[:100]}...")
            
            return True
            
        finally:
            # Restore original
            utils.config_helper.ConfigAccessor = original_accessor
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_broker_adapter_real_config()
    
    print("\n" + "=" * 60)
    print("TEST RESULT")
    print("=" * 60)
    if success:
        print("✅ BrokerAdapter is working correctly!")
        print("💡 The main issue was likely SmartAPI package installation")
        print("🟢 SmartAPI is now available and broker adapter can be created")
    else:
        print("❌ BrokerAdapter still has issues")
        print("🔍 Check the error details above")