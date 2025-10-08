#!/usr/bin/env python3
"""
Credential Migration Script: Wind → myQuant

This script helps migrate credentials from the Wind system to myQuant's .env file.
It attempts to load credentials from the Wind/angelalgo environment and 
update the myQuant .env file.
"""

import os
import sys
from pathlib import Path

def load_wind_credentials():
    """Try to load credentials from Wind/angelalgo environment"""
    try:
        # Try to load from angelalgo .env.trading (Wind's expected location)
        angelalgo_path = Path(r"C:\Users\user\projects\angelalgo")
        env_trading = angelalgo_path / ".env.trading"
        
        if env_trading.exists():
            print(f"✅ Found Wind credentials file: {env_trading}")
            
            # Parse the .env file manually
            credentials = {}
            with open(env_trading, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        credentials[key.strip()] = value.strip().strip('"').strip("'")
            
            return credentials
        else:
            print(f"❌ Wind credentials file not found: {env_trading}")
            return None
            
    except Exception as e:
        print(f"❌ Error loading Wind credentials: {e}")
        return None

def update_myquant_env(credentials):
    """Update myQuant .env file with Wind credentials"""
    if not credentials:
        print("❌ No credentials to update")
        return False
        
    # Map Wind credential names to myQuant names
    credential_mapping = {
        'API_KEY': 'SMARTAPI_API_KEY',
        'CLIENT_ID': 'SMARTAPI_CLIENT_CODE', 
        'PASSWORD': 'SMARTAPI_PIN',
        'SMARTAPI_TOTP_SECRET': 'SMARTAPI_TOTP_TOKEN'
    }
    
    myquant_env = Path(__file__).parent / ".env"
    
    # Read existing .env content
    env_lines = []
    if myquant_env.exists():
        with open(myquant_env, 'r') as f:
            env_lines = f.readlines()
    
    # Update credentials
    updated_credentials = {}
    for wind_key, myquant_key in credential_mapping.items():
        if wind_key in credentials and credentials[wind_key]:
            updated_credentials[myquant_key] = credentials[wind_key]
            print(f"✅ Mapped {wind_key} → {myquant_key}")
        else:
            print(f"⚠️  Missing credential: {wind_key}")
    
    if not updated_credentials:
        print("❌ No valid credentials found to migrate")
        return False
    
    # Update .env file
    new_env_lines = []
    updated_keys = set()
    
    for line in env_lines:
        line_stripped = line.strip()
        if line_stripped and not line_stripped.startswith('#') and '=' in line_stripped:
            key = line_stripped.split('=', 1)[0].strip()
            if key in updated_credentials:
                new_env_lines.append(f"{key}={updated_credentials[key]}\n")
                updated_keys.add(key)
            else:
                new_env_lines.append(line)
        else:
            new_env_lines.append(line)
    
    # Add any missing credentials
    for key, value in updated_credentials.items():
        if key not in updated_keys:
            new_env_lines.append(f"{key}={value}\n")
    
    # Write updated .env file
    with open(myquant_env, 'w') as f:
        f.writelines(new_env_lines)
    
    print(f"✅ Updated myQuant .env file: {myquant_env}")
    return True

def main():
    print("🔄 Migrating credentials from Wind to myQuant...")
    print("=" * 50)
    
    # Load Wind credentials
    credentials = load_wind_credentials()
    if not credentials:
        print("\n❌ Could not load Wind credentials")
        print("💡 Manual setup required:")
        print("   1. Get your SmartAPI credentials from Angel Broking")
        print("   2. Edit .env file manually with your credentials")
        return False
    
    print(f"\n✅ Loaded {len(credentials)} credentials from Wind")
    
    # Show what we found (masked)
    print("\nFound credentials:")
    for key, value in credentials.items():
        if value:
            masked_value = value[:4] + "*" * (len(value) - 4) if len(value) > 4 else "****"
            print(f"  {key}: {masked_value}")
        else:
            print(f"  {key}: (empty)")
    
    # Update myQuant .env
    if update_myquant_env(credentials):
        print("\n🎉 SUCCESS: Credentials migrated successfully!")
        print("💡 You can now run forward tests with live WebStream data")
        return True
    else:
        print("\n❌ FAILED: Could not update myQuant .env file")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)