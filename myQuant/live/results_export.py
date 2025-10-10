"""
Forward Test Results Export - Single CSV format matching backtest
Consolidates configur    # Capital change info
    if hasattr(trader.position_manager, 'initial_capital') and hasattr(trader.position_manager, 'current_capital'):
        initial = trader.position_manager.initial_capital
        current = trader.position_manager.current_capital
        change = current - initial
        change_pct = (change / initial) * 100 if initial > 0 else 0
        rows.append({"Key": "Capital Change", "Value": f"₹{change:,.2f} ({change_pct:+.2f}%)"});nd trade data into one CSV file, same as backtest module.
"""
import csv
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

def export_forward_test_results(config_summary: str, trader, output_dir: str = "results") -> Dict[str, str]:
    """
    Export forward test results to single CSV file matching backtest format.
    
    Args:
        config_summary: Already generated config text from dialog
        trader: Trader instance with position_manager containing all data
        output_dir: Directory to save results
    
    Returns:
        Dict with file_path created (single CSV file)
    """
    
    # Create results directory
    Path(output_dir).mkdir(exist_ok=True)
    
    # Generate timestamp for filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    try:
        # Create single CSV file like backtest module
        csv_file = f"{output_dir}/forward_test_results_{timestamp}.csv"
        
        # 1. Create configuration info table (similar to backtest additional_info_table)
        config_info = _create_config_info_table(config_summary, trader)
        
        # 2. Create trades data (same format as backtest CSV)
        trades_data = _create_trades_data(trader)
        
        # 3. Write both tables to same CSV file (like backtest does)
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            # Write config info table first
            config_info.to_csv(f, index=False)
            f.write('\n')  # Empty line separator
            # Write trades data
            trades_data.to_csv(f, index=False)
        
        logger.info(f"Forward test results exported to: {csv_file}")
        return {"file_path": csv_file}
        
    except Exception as e:
        logger.error(f"Failed to export forward test results: {e}")
        return {"error": str(e)}


def _create_config_info_table(config_summary: str, trader) -> pd.DataFrame:
    """Create configuration info table similar to backtest format."""
    
    # Get performance data
    perf_data = trader.position_manager.get_performance_summary()
    
    # Extract key info from config summary
    rows = []
    
    # Parse basic info from config summary
    lines = config_summary.split('\n')
    symbol = "N/A"
    strategy = "Forward Test Strategy"
    capital = "N/A"
    
    for line in lines:
        if "Symbol:" in line:
            symbol = line.split("Symbol:")[-1].strip()
        elif "Strategy:" in line:
            strategy = line.split("Strategy:")[-1].strip()
        elif "Capital:" in line:
            capital = line.split("Capital:")[-1].strip()
    
    # Add configuration rows
    rows.append({"Key": "Test Type", "Value": "Forward Test"})
    rows.append({"Key": "Symbol", "Value": symbol})
    rows.append({"Key": "Strategy", "Value": strategy})
    rows.append({"Key": "Initial Capital", "Value": capital})
    
    # Add performance summary
    rows.append({"Key": "Total Trades", "Value": str(perf_data.get('total_trades', 0))})
    rows.append({"Key": "Win Rate (%)", "Value": f"{perf_data.get('win_rate', 0):.1f}"})
    rows.append({"Key": "Total P&L", "Value": f"₹{perf_data.get('total_pnl', 0):,.2f}"})
    rows.append({"Key": "Profit Factor", "Value": f"{perf_data.get('profit_factor', 0):.2f}"})
    
    # Capital change info
    if hasattr(trader.position_manager, 'initial_capital') and hasattr(trader.position_manager, 'available_capital'):
        initial = trader.position_manager.initial_capital
        current = trader.position_manager.available_capital
        change = current - initial
        change_pct = (change / initial) * 100 if initial > 0 else 0
        rows.append({"Key": "Capital Change", "Value": f"₹{change:,.2f} ({change_pct:+.2f}%)"})
    
    # Export timestamp
    rows.append({"Key": "Export Time", "Value": datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
    
    return pd.DataFrame(rows)


def _create_trades_data(trader) -> pd.DataFrame:
    """Create trades data in same format as backtest CSV."""
    
    if not trader.position_manager.completed_trades:
        # Return empty DataFrame with correct headers if no trades
        return pd.DataFrame(columns=[
            'trade_id', 'position_id', 'symbol', 'entry_time', 'exit_time',
            'entry_price', 'exit_price', 'quantity', 'gross_pnl', 'commission',
            'net_pnl', 'exit_reason', 'duration_minutes', 'return_percent'
        ])
    
    trades_list = []
    
    for trade in trader.position_manager.completed_trades:
        # Calculate duration in minutes
        try:
            if hasattr(trade, 'entry_time') and hasattr(trade, 'exit_time'):
                entry_dt = pd.to_datetime(trade.entry_time)
                exit_dt = pd.to_datetime(trade.exit_time)
                duration = (exit_dt - entry_dt).total_seconds() / 60
            else:
                duration = 0
        except:
            duration = 0
        
        # Calculate return percentage
        try:
            return_pct = (trade.net_pnl / (trade.entry_price * trade.quantity)) * 100
        except:
            return_pct = 0
        
        # Create trade row (same format as backtest)
        trade_row = {
            'trade_id': getattr(trade, 'trade_id', 'N/A'),
            'position_id': getattr(trade, 'position_id', getattr(trade, 'trade_id', 'N/A')),
            'symbol': getattr(trade, 'symbol', 'N/A'),
            'entry_time': getattr(trade, 'entry_time', ''),
            'exit_time': getattr(trade, 'exit_time', ''),
            'entry_price': getattr(trade, 'entry_price', 0),
            'exit_price': getattr(trade, 'exit_price', 0),
            'quantity': getattr(trade, 'quantity', 0),
            'gross_pnl': getattr(trade, 'gross_pnl', getattr(trade, 'net_pnl', 0)),
            'commission': getattr(trade, 'commission', 0),
            'net_pnl': getattr(trade, 'net_pnl', 0),
            'exit_reason': getattr(trade, 'exit_reason', 'Unknown'),
            'duration_minutes': int(duration),
            'return_percent': return_pct
        }
        
        trades_list.append(trade_row)
    
    return pd.DataFrame(trades_list)