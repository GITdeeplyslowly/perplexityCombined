#!/usr/bin/env python3
"""
Capital and P&L Consistency Diagnostic Tool

Analyzes the discrepancy between reported Total P&L and Capital calculations
to identify the source of the inconsistency in performance summaries.
"""

def analyze_capital_pnl_discrepancy():
    """Analyze the reported discrepancy"""
    
    print("🔍 CAPITAL AND P&L DISCREPANCY ANALYSIS")
    print("=" * 80)
    
    # Reported values from user
    reported_values = {
        'total_pnl': 34679.00,
        'initial_capital': 100000.00,
        'current_capital': 46584.14,
        'capital_change': -53415.86,
        'total_trades': 86,
        'winning_trades': 55,
        'losing_trades': 31,
        'total_commission': 3694.75
    }
    
    print("📊 REPORTED VALUES:")
    print("-" * 40)
    for key, value in reported_values.items():
        if 'capital' in key or 'pnl' in key or 'commission' in key:
            print(f"{key:20s}: ₹{value:,.2f}")
        else:
            print(f"{key:20s}: {value}")
    
    print(f"\n🧮 MATHEMATICAL ANALYSIS:")
    print("-" * 40)
    
    # Expected capital calculation
    expected_current_capital = reported_values['initial_capital'] + reported_values['total_pnl']
    actual_current_capital = reported_values['current_capital']
    
    print(f"Expected Current Capital: ₹100,000 + ₹34,679 = ₹{expected_current_capital:,.2f}")
    print(f"Actual Current Capital:   ₹{actual_current_capital:,.2f}")
    print(f"Discrepancy:             ₹{expected_current_capital - actual_current_capital:,.2f}")
    
    # Check if it's double-counting commission
    if abs(expected_current_capital - actual_current_capital - reported_values['total_commission']) < 100:
        print(f"\n💡 POSSIBLE CAUSE: Double-counting commission")
        print(f"   Discrepancy ≈ Total Commission: ₹{reported_values['total_commission']:,.2f}")
    
    # Check capital change calculation
    reported_capital_change = reported_values['capital_change']
    calculated_capital_change = actual_current_capital - reported_values['initial_capital']
    
    print(f"\n📈 CAPITAL CHANGE ANALYSIS:")
    print(f"Reported Capital Change:   ₹{reported_capital_change:,.2f}")
    print(f"Calculated Capital Change: ₹{calculated_capital_change:,.2f}")
    print(f"Match: {'✅' if abs(reported_capital_change - calculated_capital_change) < 1 else '❌'}")

def identify_root_cause():
    """Identify the likely root cause of the discrepancy"""
    
    print(f"\n🎯 ROOT CAUSE ANALYSIS:")
    print("=" * 80)
    
    print("""
🔍 LIKELY ISSUE: Capital Reservation System vs P&L Calculation

The Position Manager uses a "capital reservation" approach:

📉 PROBLEM FLOW:
1. Position Open: Deducts full position value from current_capital
   - Example: ₹100,000 - ₹50,000 = ₹50,000 remaining
   
2. Position Close: Adds sale proceeds (not net P&L) back to current_capital  
   - Example: Sold for ₹52,000 → ₹50,000 + ₹52,000 = ₹102,000
   - But commission ₹500 already deducted from proceeds
   
3. P&L Calculation: Separately tracks net profit/loss from trades
   - Example: ₹52,000 - ₹50,000 - ₹500 = ₹1,500 profit

❌ INCONSISTENCY:
- P&L shows cumulative trade profits: +₹34,679
- Capital shows reservation accounting: ₹46,584 (₹100,000 - ₹53,416)
- These use different accounting methods!

✅ CORRECT APPROACH:
Current Capital should be: Initial Capital + Total P&L
₹100,000 + ₹34,679 = ₹134,679

🔧 THE FIX:
Replace capital reservation system with simple P&L tracking:
current_capital = initial_capital + sum(all_trade_net_pnl)
""")

def recommend_fixes():
    """Recommend specific fixes for the code"""
    
    print(f"\n🔧 RECOMMENDED FIXES:")
    print("=" * 80)
    
    print("""
📝 FIX 1: Update Position Manager Capital Calculation

In position_manager.py, change current_capital calculation:

```python
# WRONG (current approach):
def open_position(...):
    self.current_capital -= required_capital  # ❌ Capital reservation
    
def close_position(...):
    self.current_capital += proceeds  # ❌ Adds proceeds, not net P&L

# CORRECT (recommended approach):  
@property
def current_capital(self) -> float:
    total_pnl = sum(trade.net_pnl for trade in self.completed_trades)
    return self.initial_capital + total_pnl
```

📝 FIX 2: Alternative - Separate Available vs Total Capital

Keep reservation system but clarify terminology:

```python
@property  
def available_capital(self) -> float:
    # Money available for new positions (reservation system)
    return self._available_capital
    
@property
def total_capital(self) -> float:
    # Actual portfolio value (P&L based)
    total_pnl = sum(trade.net_pnl for trade in self.completed_trades)
    return self.initial_capital + total_pnl
```

📝 FIX 3: GUI Performance Report Update

Update GUI to use consistent calculation:

```python
def _generate_performance_report(self, perf_data, position_manager):
    # Use P&L-based capital calculation
    initial_capital = position_manager.initial_capital
    total_pnl = perf_data['total_pnl']  # ₹34,679
    current_capital = initial_capital + total_pnl  # ₹134,679
    capital_change = total_pnl  # Same as total_pnl
```
""")

def main():
    """Run complete diagnostic analysis"""
    
    analyze_capital_pnl_discrepancy()
    identify_root_cause()
    recommend_fixes()
    
    print(f"\n" + "=" * 80)
    print("📋 SUMMARY")
    print("=" * 80)
    
    print("""
🎯 THE ISSUE:
Two different accounting systems are being mixed:
- P&L Calculation: Trade-based profit/loss (✅ Correct: +₹34,679)
- Capital Tracking: Reservation-based deduction/addition (❌ Wrong method)

🔧 THE SOLUTION:
Use consistent P&L-based capital calculation:
Current Capital = Initial Capital + Total P&L
₹134,679 = ₹100,000 + ₹34,679

This will make the performance summary consistent and mathematically correct.
""")

if __name__ == "__main__":
    main()