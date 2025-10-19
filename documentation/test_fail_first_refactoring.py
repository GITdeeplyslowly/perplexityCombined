"""
Test: Verify Fail-First Behavior in ForwardTestResults

This test ensures the refactoring correctly enforces SSOT and fail-first principles.
"""

import sys
sys.path.insert(0, 'myQuant')

from datetime import datetime
from types import MappingProxyType
from live.forward_test_results import ForwardTestResults
from core.position_manager import PositionManager


def test_forward_test_results_fails_without_dialog_text():
    """
    CRITICAL TEST: Verify that ForwardTestResults raises ValueError 
    when dialog_text is not provided (fail-first principle).
    """
    # Create minimal test config
    test_config = {
        'instrument': {'symbol': 'TEST', 'exchange': 'NSE'},
        'capital': {'initial_capital': 100000},
        'data_simulation': {'enabled': False}
    }
    
    # Create ForwardTestResults WITHOUT dialog_text (use None for pm - we won't call methods that need it)
    results = ForwardTestResults(
        config=test_config,
        position_manager=None,  # Not needed for this test
        start_time=datetime.now()
        # dialog_text intentionally NOT provided!
    )
    
    # Should raise ValueError when trying to get dialog text
    try:
        results._get_dialog_box_text()
        # If we get here, test FAILED (should have raised ValueError)
        raise AssertionError("Expected ValueError but method succeeded!")
    except ValueError as e:
        # Good! Should raise ValueError
        error_msg = str(e).lower()
        assert "dialog_text not provided" in error_msg or "configuration error" in error_msg, f"Wrong error message: {e}"
        assert "programming error" in error_msg, f"Missing 'programming error' in: {e}"
        assert "ssot" in error_msg, f"Missing 'SSOT' in: {e}"
        print("✅ PASS: Fail-first behavior verified - crashes without dialog_text")


def test_forward_test_results_succeeds_with_dialog_text():
    """
    Verify that ForwardTestResults works correctly when dialog_text IS provided.
    """
    # Create minimal test config
    test_config = {
        'instrument': {'symbol': 'TEST', 'exchange': 'NSE'},
        'capital': {'initial_capital': 100000},
        'data_simulation': {'enabled': False}
    }
    
    # Create minimal position manager
    frozen_config = MappingProxyType(test_config)
    pm = PositionManager(frozen_config)
    
    # Test dialog text (what would be shown to user)
    test_dialog = """
FORWARD TEST CONFIGURATION REVIEW
================================================================================

INSTRUMENT & SESSION
----------------------------------------
Symbol:              TEST
Exchange:            NSE
Initial Capital:     100,000

STRATEGY & INDICATORS
----------------------------------------
Strategy Version:    1
Green Bars Required: 3

Enabled Indicators:
  EMA Crossover:     Fast=18, Slow=42
  MACD:              Fast=12, Slow=26, Signal=9

================================================================================
Review the configuration above. Click 'Start Forward Test' to proceed.
"""
    
    # Create ForwardTestResults WITH dialog_text
    results = ForwardTestResults(
        config=test_config,
        position_manager=pm,
        start_time=datetime.now(),
        dialog_text=test_dialog  # ← Provided!
    )
    
    # Should return the exact dialog text
    returned_text = results._get_dialog_box_text()
    assert returned_text == test_dialog
    
    print("✅ PASS: Dialog text correctly stored and retrieved")


def test_no_hardcoded_defaults_in_code():
    """
    Verify that the refactored code doesn't contain hardcoded defaults.
    This is a regression test to ensure we don't re-introduce the problem.
    """
    import inspect
    from live.forward_test_results import ForwardTestResults
    
    # Get source code of _get_dialog_box_text method
    source = inspect.getsource(ForwardTestResults._get_dialog_box_text)
    
    # Should NOT contain any hardcoded indicator values
    assert "12" not in source or "macd" not in source.lower()  # No MACD defaults
    assert "26" not in source or "macd" not in source.lower()
    assert "14" not in source or "rsi" not in source.lower()   # No RSI defaults
    assert "20" not in source or "vwap" not in source.lower()  # No VWAP defaults
    assert "0.01" not in source or "noise" not in source.lower()  # No noise defaults
    
    # Should NOT contain .get() calls with defaults
    assert ".get('macd_fast_period', 12)" not in source
    assert ".get('rsi_period', 14)" not in source
    
    print("✅ PASS: No hardcoded defaults found in refactored code")


if __name__ == "__main__":
    print("Running Fail-First Refactoring Tests...")
    print("=" * 60)
    
    try:
        test_forward_test_results_fails_without_dialog_text()
        test_forward_test_results_succeeds_with_dialog_text()
        test_no_hardcoded_defaults_in_code()
        
        print("=" * 60)
        print("✅ ALL TESTS PASSED - Fail-First Refactoring Verified!")
        
    except AssertionError as e:
        print(f"❌ TEST FAILED: {e}")
        raise
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {e}")
        raise
