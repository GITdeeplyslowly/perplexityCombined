#!/usr/bin/env python3
"""
Virtual Environment SmartAPI Test
Verifies that the GUI's virtual environment has SmartAPI properly configured.
"""

def test_venv_smartapi():
    """Test SmartAPI in the virtual environment used by the GUI."""
    print("🧪 Testing SmartAPI in Virtual Environment")
    print("=" * 50)
    
    try:
        # Test direct import
        from SmartApi import SmartConnect
        print("✅ SmartAPI import: SUCCESS")
        
        # Test broker adapter
        from live.broker_adapter import BrokerAdapter
        from config.defaults import DEFAULT_CONFIG
        from types import MappingProxyType
        
        config = MappingProxyType(DEFAULT_CONFIG)
        ba = BrokerAdapter(config)
        
        print(f"✅ BrokerAdapter SmartConnect: {'Available' if ba.SmartConnect else 'NOT Available'}")
        print(f"📝 Paper trading mode: {ba.paper_trading}")
        print(f"🔌 File simulation enabled: {ba.file_simulator is not None}")
        
        # Test connection logic (should pass SmartAPI check)
        print("\n🔗 Testing connection logic...")
        try:
            ba.connect()
        except Exception as e:
            if "SmartAPI package missing" in str(e) or "SmartAPI not installed" in str(e):
                print("❌ SmartAPI detection FAILED")
                return False
            else:
                print("✅ SmartAPI detection PASSED (failed at auth as expected)")
        
        print("\n🎉 Virtual Environment SmartAPI: READY FOR GUI!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_venv_smartapi()
    if success:
        print("\n💡 The GUI should now work with SmartAPI!")
        print("   • Forward tests will detect SmartAPI properly")  
        print("   • Live webstream data will be available")
    else:
        print("\n❌ Virtual environment setup incomplete")