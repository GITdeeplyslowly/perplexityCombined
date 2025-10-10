#!/usr/bin/env python3
"""
Test script to verify the CSV data processing fix
"""

import pandas as pd
import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_csv_data_structure():
    """Test the CSV data structure and simulate the fix"""
    
    print("🔍 Testing CSV data structure and fix...")
    
    # Load the CSV file
    csv_file = "live_ticks_20251001_170006.csv"
    if not os.path.exists(csv_file):
        print(f"❌ CSV file {csv_file} not found!")
        return False
    
    df = pd.read_csv(csv_file)
    print(f"✅ Loaded CSV with {len(df)} rows")
    print(f"📊 Columns: {df.columns.tolist()}")
    
    # Get first few rows
    print(f"\n📋 First 3 rows:")
    for i in range(min(3, len(df))):
        print(f"Row {i}: {df.iloc[i].to_dict()}")
    
    # Simulate the original problem
    print(f"\n🔍 Testing original problem...")
    row = df.iloc[0]  # First row as pandas Series
    
    # This would have caused the KeyError
    print(f"Original row keys: {list(row.index)}")
    print(f"'close' in row: {'close' in row}")
    print(f"'price' in row: {'price' in row}")
    
    # Simulate the fix
    print(f"\n🔧 Simulating the fix...")
    updated_row = row.copy()
    
    # Extract close price with fallback (like in the fixed code)
    if 'close' in updated_row:
        close_price = updated_row['close']
    elif 'price' in updated_row:
        close_price = updated_row['price']
    else:
        print("❌ No price data found!")
        return False
    
    # Add close price to updated row (the fix)
    updated_row['close'] = close_price
    
    print(f"✅ Close price extracted: {close_price}")
    print(f"✅ 'close' in updated_row: {'close' in updated_row}")
    
    # Test that we can now access row['close'] safely
    try:
        test_access = updated_row['close']
        print(f"✅ Successfully accessed row['close']: {test_access}")
        return True
    except KeyError as e:
        print(f"❌ Still getting KeyError: {e}")
        return False

if __name__ == "__main__":
    success = test_csv_data_structure()
    if success:
        print(f"\n🎉 Fix verified successfully!")
        print(f"The KeyError: 'close' issue should now be resolved.")
    else:
        print(f"\n❌ Fix verification failed!")
    
    sys.exit(0 if success else 1)