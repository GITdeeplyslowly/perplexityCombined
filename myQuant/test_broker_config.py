#!/usr/bin/env python3
"""
Test broker_adapter configuration handling with dynamic instrument_token
"""

def test_broker_adapter_config():
    """Test that broker_adapter properly handles dynamic instrument_token"""
    
    try:
        from utils.config_helper import create_config_from_defaults, freeze_config
        
        # Create base config
        config = create_config_from_defaults()
        
        # Set required API credentials (these should always be set)
        config['live']['api_key'] = "TEST_API_KEY"
        config['live']['client_code'] = "TEST_CLIENT_CODE"
        
        print("✅ Test 1: Base configuration created successfully")
        print(f"  - Symbol: {config['instrument']['symbol']}")
        print(f"  - Exchange: {config['instrument']['exchange']}")
        print(f"  - Product Type: {config['instrument']['product_type']}")
        
        # Test with empty instrument_token (should be OK for initialization)
        frozen_config = freeze_config(config)
        
        try:
            from live.broker_adapter import BrokerAdapter
            print("✅ Test 2: BrokerAdapter can be imported (no initialization yet)")
        except Exception as e:
            print(f"❌ Test 2 Failed: {e}")
            return
        
        # Test initialization without instrument_token (should work for init)
        print("\n🔧 Test 3: Testing BrokerAdapter initialization without instrument_token...")
        try:
            # This should work since we're not starting streaming yet
            adapter = BrokerAdapter(frozen_config)
            print("✅ Test 3: BrokerAdapter initialized successfully")
            print(f"  - Lot Size: {adapter.lot_size}")
            print(f"  - Tick Size: {adapter.tick_size}")
            print(f"  - Exchange: {adapter.exchange}")
            print(f"  - Product Type: {adapter.product_type}")
        except Exception as e:
            print(f"❌ Test 3 Failed: {e}")
            return
            
        # Test that streaming fails without instrument_token (expected behavior)
        print("\n🔧 Test 4: Testing streaming without instrument_token (should fail safely)...")
        try:
            adapter._start_websocket_stream()
            print("❌ Test 4 Failed: Should have raised error for missing instrument_token")
        except ValueError as e:
            if "instrument_token not set" in str(e):
                print("✅ Test 4: Correctly failed with clear error for missing instrument_token")
                print(f"  Error: {e}")
            else:
                print(f"❌ Test 4 Failed: Wrong error type: {e}")
        except Exception as e:
            print(f"❌ Test 4 Failed: Unexpected error: {e}")
            
        # Test with valid instrument_token
        print("\n🔧 Test 5: Testing with valid instrument_token...")
        config['instrument']['instrument_token'] = "12345_NIFTY2410118000CE"
        frozen_config_with_token = freeze_config(config)
        
        try:
            adapter_with_token = BrokerAdapter(frozen_config_with_token)
            print("✅ Test 5: BrokerAdapter initialized with instrument_token")
            print(f"  - Token ready for streaming: Yes")
        except Exception as e:
            print(f"❌ Test 5 Failed: {e}")
            
        print("\n🎉 Configuration handling test completed!")
        
    except Exception as e:
        print(f"❌ Test setup failed: {e}")

if __name__ == "__main__":
    test_broker_adapter_config()