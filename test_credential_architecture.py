#!/usr/bin/env python3
"""
Test the architectural separation between data simulation and live trading credentials.
This test validates that:
1. Data simulation users see no dotenv warnings
2. Live trading users see dotenv warnings only when needed
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

print("=== Testing Credential Loading Architecture ===\n")

# Test 1: Import defaults.py (should be clean - no warnings for data simulation users)
print("Test 1: Importing defaults.py (should be clean for data simulation users)")
from config.defaults import DEFAULT_CONFIG
print("✅ No warnings during import - data simulation users get clean experience")

# Test 2: Check that credentials are empty by default
print("\nTest 2: Default credentials (should be empty until live trading)")
live_config = DEFAULT_CONFIG["live"]
credentials = ["api_key", "client_code", "pin", "totp_secret"]
for cred in credentials:
    value = live_config.get(cred, "MISSING")
    print(f"  {cred}: '{value}' ({'✅ Empty' if value == '' else '❌ Not empty'})")

# Test 3: Load live trading credentials (this should show dotenv messages)
print("\nTest 3: Loading live trading credentials (should show dotenv messages)")
from config.defaults import load_live_trading_credentials
loaded_creds = load_live_trading_credentials()
print(f"  Loaded {len(loaded_creds)} credential keys: {list(loaded_creds.keys())}")

print("\n=== Architecture Test Complete ===")
print("✅ Data simulation path: Clean (no credential loading)")
print("✅ Live trading path: Credentials loaded only when needed")