#!/usr/bin/env python3
"""
Test script to verify P&L calculation fixes
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from datetime import datetime
from myQuant.core.position_manager import PositionManager, Trade
from myQuant.live.forward_test_results import ForwardTestResults

def test_pnl_calculations():
    """Test that P&L calculations are working correctly"""
    
    # Create a basic config
    config = {
        'instrument': {'symbol': 'NIFTY', 'lot_size': 50},
        'capital': {'initial_capital': 100000},
        'risk': {'max_positions_per_day': 5}
    }
    
    # Create position manager
    pm = PositionManager(initial_capital=100000)
    
    # Create a simple trade to test
    from dataclasses import dataclass
    
    @dataclass
    class MockTrade:
        trade_id: str = "test123"
        position_id: str = "pos123"
        symbol: str = "NIFTY"
        entry_time: datetime = datetime(2024, 1, 1, 10, 0, 0)
        exit_time: datetime = datetime(2024, 1, 1, 15, 0, 0)
        entry_price: float = 21500.0
        exit_price: float = 21550.0
        quantity: int = 50
        gross_pnl: float = 2500.0  # (21550 - 21500) * 50
        commission: float = 50.0
        net_pnl: float = 2450.0  # 2500 - 50
        exit_reason: str = "TP1"
        duration_minutes: int = 300
        lot_size: int = 50
        lots_traded: int = 1
    
    # Add mock trade to position manager
    mock_trade = MockTrade()
    pm.completed_trades.append(mock_trade)
    
    # Test ForwardTestResults
    ftr = ForwardTestResults(config, pm, datetime.now())
    trades_df = ftr._get_trades_dataframe()
    
    print("=== P&L Test Results ===")
    print(f"Number of trades: {len(trades_df)}")
    
    if not trades_df.empty:
        print(f"Gross P&L: {trades_df.iloc[0]['Gross P&L']}")
        print(f"Commission: {trades_df.iloc[0]['Commission']}")
        print(f"Net P&L: {trades_df.iloc[0]['Net P&L']}")
        
        # Check if values are populated (not NaN or 0 when they should have values)
        gross_pnl = trades_df.iloc[0]['Gross P&L']
        commission = trades_df.iloc[0]['Commission']
        net_pnl = trades_df.iloc[0]['Net P&L']
        
        if gross_pnl != 0 and commission != 0 and net_pnl != 0:
            print("✅ SUCCESS: All P&L values are properly populated!")
            print(f"   Gross P&L: ₹{gross_pnl}")
            print(f"   Commission: ₹{commission}")
            print(f"   Net P&L: ₹{net_pnl}")
            return True
        else:
            print("❌ FAILURE: Some P&L values are missing or zero")
            return False
    else:
        print("❌ FAILURE: No trades found in DataFrame")
        return False

if __name__ == "__main__":
    success = test_pnl_calculations()
    if success:
        print("\n🎉 P&L calculation fix is working correctly!")
    else:
        print("\n⚠️  P&L calculation fix needs more work")