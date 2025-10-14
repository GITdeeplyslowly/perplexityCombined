```python
// filepath: c:\Users\user\projects\Perplexity Combined\tests\test_position_manager.py
# Standalone unit test for PositionManager using GUI SSOT config flow

import pandas as pd
import pytest
from utils.config_helper import create_config_from_defaults, validate_config
from core.position_manager import PositionManager, now_ist


def test_open_position_and_take_profit_triggers():
    # Build canonical run config from defaults (GUI SSOT)
    cfg = create_config_from_defaults()
    # Use a known initial capital for deterministic sizing
    cfg['capital']['initial_capital'] = 500_000.0

    # Validate config as GUI would (test should fail early if config is invalid)
    validation = validate_config(cfg)
    assert validation.get('valid', False), f"Config invalid: {validation.get('errors')}"

    # Instantiate PositionManager with validated config
    pm = PositionManager(cfg)

    symbol = cfg['instrument']['symbol']
    price = 22_000.0
    lot = int(cfg['instrument']['lot_size'])
    tick = float(cfg['instrument'].get('tick_size', 0.05))

    pos_id = pm.open_position(symbol, price, now_ist(), lot, tick)
    assert pos_id is not None, "Failed to open position"

    # Simulate price move enough to hit first TP(s)
    tp_price = price + 35.0  # default tp_points include 10 and 25
    pm.process_positions(pd.Series({'close': tp_price}), now_ist())

    # After processing, at least one trade should be completed (some TP executed)
    assert len(pm.completed_trades) > 0, "No trades completed after TP price move"

    summary = pm.get_performance_summary()
    assert summary['total_trades'] > 0
    assert 'total_pnl' in summary
