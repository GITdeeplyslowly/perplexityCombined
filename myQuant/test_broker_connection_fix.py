#!/usr/bin/env python3
"""
Quick test to verify broker adapter connection object after fix
"""

def test_broker_connection():
    """Test that broker adapter connection is SmartConnect object, not dict"""
    print("=" * 60)
    print("BROKER ADAPTER CONNECTION OBJECT TEST")
    print("=" * 60)
    
    try:
        from config.defaults import load_live_trading_credentials
        from types import MappingProxyType
        
        # Load real credentials
        creds = load_live_trading_credentials()
        print(f"✅ Credentials loaded: {list(creds.keys())}")
        
        # Create test config with real credentials
        test_config = MappingProxyType({
            "live": {
                "paper_trading": True,
                **creds  # Include real credentials
            },
            "instrument": {
                "symbol": "NIFTY14OCT2525200PE",
                "exchange": "NFO",
                "product_type": "MIS",
                "token": "42690"
            },
            "data_simulation": {
                "enabled": False
            }
        })
        
        # Mock the ConfigAccessor to avoid instrument mapping errors
        class MockConfigAccessor:
            def __init__(self, config):
                self.config = config
                
            def get_current_instrument_param(self, param):
                defaults = {
                    'lot_size': 75,
                    'tick_size': 0.05
                }
                return defaults.get(param, 0)
        
        # Temporarily patch the import
        import utils.config_helper
        original_accessor = utils.config_helper.ConfigAccessor
        utils.config_helper.ConfigAccessor = MockConfigAccessor
        
        try:
            from live.broker_adapter import BrokerAdapter
            broker = BrokerAdapter(test_config)
            print("✅ BrokerAdapter created successfully")
            
            # Test that SmartConnect is available
            print(f"SmartConnect available: {broker.SmartConnect is not None}")
            
            # Test connection (should authenticate)
            print("\n🔌 Testing connection...")
            try:
                broker.connect()
                print("✅ Connection successful!")
                print(f"Connection object type: {type(broker.connection)}")
                print(f"Has getLTP method: {hasattr(broker.connection, 'getLTP')}")
                
                # Test a simple getLTP call
                print("\n📊 Testing getLTP call...")
                try:
                    ltp_response = broker.connection.getLTP({
                        "exchange": "NFO",
                        "tradingsymbol": "NIFTY14OCT2525200PE",
                        "symboltoken": "42690"
                    })
                    print(f"✅ getLTP call successful: {type(ltp_response)}")
                    if isinstance(ltp_response, dict) and 'data' in ltp_response:
                        print(f"✅ Response format correct: {list(ltp_response.keys())}")
                    else:
                        print(f"❓ Unexpected response format: {ltp_response}")
                except Exception as e:
                    print(f"❌ getLTP call failed: {e}")
                
            except Exception as e:
                print(f"❌ Connection failed: {e}")
                
        finally:
            # Restore original
            utils.config_helper.ConfigAccessor = original_accessor
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_broker_connection()