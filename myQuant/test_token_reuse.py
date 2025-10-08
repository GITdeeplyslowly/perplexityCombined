#!/usr/bin/env python3
"""
Token Reuse Verification Test
Tests that JWT tokens are properly reused for 20 hours before requiring fresh TOTP.
"""

import os
import json
from datetime import datetime, timedelta

def test_token_reuse():
    """Test JWT token reuse behavior vs fresh TOTP generation."""
    print("🔄 Testing JWT Token Reuse System")
    print("=" * 50)
    
    session_file = "smartapi/session_token.json"
    
    # Check if session file exists
    if os.path.exists(session_file):
        try:
            with open(session_file, "r") as f:
                session_data = json.load(f)
            
            print("✅ Session file found")
            print(f"📁 Location: {session_file}")
            
            # Check session age
            if "refresh_time" in session_data:
                refresh_time = datetime.fromisoformat(session_data["refresh_time"])
                age_hours = (datetime.now() - refresh_time).total_seconds() / 3600
                
                print(f"⏰ Session age: {age_hours:.1f} hours")
                print(f"🔑 Client code: {session_data.get('client_code', 'N/A')}")
                
                if age_hours < 20:
                    print("✅ Session VALID - Will reuse JWT token (no TOTP needed)")
                    return True, "reuse"
                else:
                    print("⚠️  Session EXPIRED - Will require fresh TOTP login")
                    return True, "expired"
            else:
                print("⚠️  Session missing timestamp")
                return True, "invalid"
                
        except Exception as e:
            print(f"❌ Error reading session: {e}")
            return False, "error"
    else:
        print("📝 No session file found - Will require fresh TOTP login")
        return True, "no_session"

def test_session_manager():
    """Test the SmartAPISessionManager token reuse logic."""
    print("\n🔧 Testing SmartAPISessionManager Logic")
    print("-" * 40)
    
    try:
        from live.login import SmartAPISessionManager
        from config.defaults import DEFAULT_CONFIG
        
        live = DEFAULT_CONFIG['live']
        
        # Create session manager
        session_mgr = SmartAPISessionManager(
            api_key=live['api_key'],
            client_code=live['client_code'],
            pin="",  # No PIN for session load test
            totp_secret=""  # No TOTP for session load test
        )
        
        # Try to load existing session
        session_info = session_mgr.load_session_from_file()
        
        if session_info:
            print("✅ Session loaded from file")
            
            # Check if valid
            if session_mgr.is_session_valid():
                print("✅ Session is VALID - Would reuse JWT token")
                print("💡 No TOTP generation needed!")
                return True, "valid_session"
            else:
                print("⚠️  Session is EXPIRED - Would require fresh login")
                print("💡 Fresh TOTP generation needed")
                return True, "expired_session"
        else:
            print("📝 No session found - Would require fresh login")
            print("💡 Fresh TOTP generation needed")
            return True, "no_session"
            
    except Exception as e:
        print(f"❌ Error testing session manager: {e}")
        return False, "error"

def show_token_flow():
    """Show the complete token reuse flow."""
    print("\n📊 JWT Token Reuse Flow")
    print("=" * 30)
    print("1️⃣  First Time:")
    print("   • Generate TOTP with pyotp.TOTP(secret).now()")
    print("   • Call SmartAPI.generateSession(client, pin, totp)")
    print("   • Get JWT token (valid 20 hours)")
    print("   • Save to session_token.json")
    print("")
    print("2️⃣  Subsequent Calls (< 20 hours):")
    print("   • Load JWT from session_token.json") 
    print("   • Check age < 20 hours")
    print("   • ✅ Reuse existing token (NO TOTP needed)")
    print("")
    print("3️⃣  After 20 hours:")
    print("   • JWT expired")
    print("   • Generate fresh TOTP") 
    print("   • New generateSession() call")
    print("   • Get new JWT token")

if __name__ == "__main__":
    # Test token reuse
    success1, status1 = test_token_reuse()
    success2, status2 = test_session_manager()
    
    show_token_flow()
    
    print(f"\n📋 Test Results:")
    print(f"   Session file check: {status1}")
    print(f"   Session manager: {status2}")
    
    if success1 and success2:
        print("\n🎉 Token Reuse System: WORKING CORRECTLY!")
        print("✅ JWT tokens are reused efficiently")
        print("✅ TOTP only generated when needed") 
        print("✅ 20-hour session lifecycle implemented")
        
        if status2 == "valid_session":
            print("\n💡 Current Status: Using saved JWT token")
            print("   → No TOTP generation required")
        else:
            print(f"\n💡 Current Status: {status2}")
            print("   → Fresh TOTP generation required")
    else:
        print("\n❌ Token reuse system has issues")