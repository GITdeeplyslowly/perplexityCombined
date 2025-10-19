#!/usr/bin/env python3
"""
Debug script to check what's in the trades DataFrame
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

import pandas as pd
from datetime import datetime

# Mock the Trade class since we can't import the full modules
class MockTrade:
    def __init__(self):
        self.trade_id = "test123"
        self.position_id = "pos123"
        self.symbol = "NIFTY"
        self.entry_time = datetime(2025, 10, 12, 11, 16, 4)
        self.exit_time = datetime(2025, 10, 12, 11, 16, 6)
        self.entry_price = 23450.75
        self.exit_price = 23390.25
        self.quantity = 375
        self.gross_pnl = (23390.25 - 23450.75) * 375  # Should be -22687.5
        self.commission = 53.36
        self.net_pnl = self.gross_pnl - self.commission  # Should be -22740.86
        self.exit_reason = "Stop Loss"
        self.duration_minutes = 2.0

def debug_dataframe_creation():
    """Debug the DataFrame creation process"""
    
    # Create mock trades similar to what you're seeing
    trades = [MockTrade()]
    
    print("=== DEBUG: Trade Object Values ===")
    trade = trades[0]
    print(f"Entry Price: {trade.entry_price}")
    print(f"Exit Price: {trade.exit_price}")
    print(f"Gross P&L: {trade.gross_pnl}")
    print(f"Commission: {trade.commission}")
    print(f"Net P&L: {trade.net_pnl}")
    print(f"Duration: {trade.duration_minutes}")
    
    print("\n=== DEBUG: DataFrame Creation ===")
    
    # Replicate the _get_trades_dataframe logic
    rows = []
    for i, trade in enumerate(trades, 1):
        row_data = {
            '#': i,
            'Entry Time': trade.entry_time.strftime('%Y-%m-%d %H:%M:%S'),
            'Exit Time': trade.exit_time.strftime('%Y-%m-%d %H:%M:%S'),
            'Entry ₹': round(trade.entry_price, 2),
            'Exit ₹': round(trade.exit_price, 2),
            'Qty': trade.quantity,
            'Gross P&L': round(trade.gross_pnl, 2),
            'Commission': round(trade.commission, 2),
            'Net P&L': round(trade.net_pnl, 2),
            'Exit Reason': trade.exit_reason,
            'Duration (min)': round(trade.duration_minutes, 0)
        }
        
        print(f"Row {i} data:")
        for key, value in row_data.items():
            print(f"  {key}: {value} (type: {type(value).__name__})")
        
        rows.append(row_data)
    
    df = pd.DataFrame(rows)
    
    print(f"\n=== DEBUG: Final DataFrame ===")
    print(f"DataFrame shape: {df.shape}")
    print(f"DataFrame columns: {list(df.columns)}")
    print("\nDataFrame content:")
    print(df.to_string())
    
    print(f"\n=== DEBUG: Column-by-Column Check ===")
    for col in df.columns:
        values = df[col].tolist()
        print(f"{col}: {values} (all non-null: {df[col].notna().all()})")
    
    return df

if __name__ == "__main__":
    df = debug_dataframe_creation()
    
    # Also check if we can export this to a simple CSV to see what happens
    csv_file = "debug_trades.csv"
    df.to_csv(csv_file, index=False)
    print(f"\n✅ Debug DataFrame saved to {csv_file}")
    print("Check this file to see if all columns are present")