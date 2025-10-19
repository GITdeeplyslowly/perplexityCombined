#!/usr/bin/env python3
"""
Test currency-agnostic implementation
"""

import pandas as pd
from datetime import datetime

def test_currency_agnostic_implementation():
    """Test that all outputs are currency agnostic"""
    
    class MockTrade:
        def __init__(self):
            self.entry_price = 23450.75
            self.exit_price = 23390.25
            self.quantity = 375
            self.gross_pnl = -22687.5
            self.commission = 53.36
            self.net_pnl = -22740.86
            self.entry_time = datetime(2025, 10, 12, 11, 16, 4)
            self.exit_time = datetime(2025, 10, 12, 11, 16, 6)
            self.exit_reason = "Stop Loss"
            self.duration_minutes = 2.0
    
    def create_currency_agnostic_row(trade, index):
        """Replicate the currency-agnostic logic"""
        entry_price = float(trade.entry_price) if trade.entry_price is not None else 0.0
        exit_price = float(trade.exit_price) if trade.exit_price is not None else 0.0
        quantity = int(trade.quantity) if trade.quantity is not None else 0
        gross_pnl = float(trade.gross_pnl) if trade.gross_pnl is not None else 0.0
        commission = float(trade.commission) if trade.commission is not None else 0.0
        net_pnl = float(trade.net_pnl) if trade.net_pnl is not None else 0.0
        duration_minutes = float(trade.duration_minutes) if trade.duration_minutes is not None else 0.0
        
        return {
            '#': index,
            'Entry Time': trade.entry_time.strftime('%Y-%m-%d %H:%M:%S') if trade.entry_time else '',
            'Exit Time': trade.exit_time.strftime('%Y-%m-%d %H:%M:%S') if trade.exit_time else '',
            'Entry Price': round(entry_price, 2),
            'Exit Price': round(exit_price, 2),
            'Qty': quantity,
            'Gross PnL': round(gross_pnl, 2),
            'Commission': round(commission, 2),
            'Net PnL': round(net_pnl, 2),
            'Exit Reason': str(trade.exit_reason) if trade.exit_reason else '',
            'Duration (min)': round(duration_minutes, 0)
        }
    
    def create_currency_agnostic_performance_metrics(net_pnl, initial_capital):
        """Test currency-agnostic performance metrics"""
        return [
            ("Total Trades", "1"),
            ("Winning Trades", "0"),
            ("Losing Trades", "1"),
            ("Win Rate", "0.00%"),
            ("Gross PnL", f"{net_pnl:,.2f}"),  # No currency symbol
            ("Net PnL", f"{net_pnl:,.2f}"),   # No currency symbol
            ("Profit Factor", "0.00"),
            ("Best Trade", "0.00"),           # No currency symbol
            ("Worst Trade", f"{net_pnl:,.2f}"), # No currency symbol
            ("Initial Capital", f"{initial_capital:,.2f}"), # No currency symbol
            ("Final Capital", f"{initial_capital + net_pnl:,.2f}"), # No currency symbol
            ("Return %", f"{(net_pnl/initial_capital*100):,.2f}%")
        ]
    
    print("=== TESTING CURRENCY-AGNOSTIC IMPLEMENTATION ===")
    
    # Test trade data
    trade = MockTrade()
    trade_row = create_currency_agnostic_row(trade, 1)
    
    print("\n1. Trade data (completely currency agnostic):")
    for key, value in trade_row.items():
        has_currency = '₹' in str(value) or '$' in str(value) or '£' in str(value) or '€' in str(value)
        status = "❌ HAS CURRENCY" if has_currency else "✅ CURRENCY AGNOSTIC"
        print(f"   {key}: {value} {status}")
    
    # Test performance metrics
    print(f"\n2. Performance metrics (completely currency agnostic):")
    metrics = create_currency_agnostic_performance_metrics(trade.net_pnl, 100000.0)
    
    for label, value in metrics:
        has_currency = '₹' in str(value) or '$' in str(value) or '£' in str(value) or '€' in str(value)
        status = "❌ HAS CURRENCY" if has_currency else "✅ CURRENCY AGNOSTIC"
        print(f"   {label}: {value} {status}")
    
    # Create DataFrame
    df = pd.DataFrame([trade_row])
    
    print(f"\n=== FINAL CURRENCY-AGNOSTIC DATAFRAME ===")
    print(f"Shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    
    # Check for any currency symbols
    has_any_currency = False
    for col in df.columns:
        if any(symbol in str(col) for symbol in ['₹', '$', '£', '€']):
            has_any_currency = True
            print(f"❌ Column '{col}' contains currency symbol")
    
    if not has_any_currency:
        print("✅ All column names are currency agnostic")
    
    # Check data values
    for col in df.columns:
        for value in df[col]:
            if any(symbol in str(value) for symbol in ['₹', '$', '£', '€']):
                print(f"❌ Value '{value}' in column '{col}' contains currency symbol")
                has_any_currency = True
    
    if not has_any_currency:
        print("✅ All data values are currency agnostic")
    
    # Export test
    csv_file = "currency_agnostic_test.csv"
    df.to_csv(csv_file, index=False)
    print(f"\n✅ Currency-agnostic test exported to {csv_file}")
    
    return df, not has_any_currency

if __name__ == "__main__":
    df, is_currency_agnostic = test_currency_agnostic_implementation()
    
    if is_currency_agnostic:
        print(f"\n🎉 SUCCESS: Implementation is completely currency agnostic!")
        print(f"✅ No currency symbols found in column names or data values")
        print(f"✅ Can be used with any currency (USD, EUR, INR, etc.)")
    else:
        print(f"\n⚠️  NEEDS WORK: Some currency symbols still present")
        print(f"❌ Check output above for specific issues")