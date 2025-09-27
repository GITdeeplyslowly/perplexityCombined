# Consecutive Green Bars Implementation

This document summarizes the changes made to replace the time gap condition with a consecutive green bars requirement for re-entry.

## Overview

The system has been modified to track consecutive green bars (where close > open) and require a user-defined number of such bars before allowing re-entry into a position. The default value is set to 3 consecutive green bars.

## Files Modified

### 1. defaults.py
**Changes:**
- Added `'consecutive_green_bars': 3` to the strategy section
- This sets the default requirement to 3 consecutive green bars

**New Parameter:**
```python
'strategy': {
    # ... existing parameters ...
    'consecutive_green_bars': 3  # Number of consecutive green bars required before re-entry
}
```

### 2. researchStrategy.py (Backtest Strategy)
**Major Changes:**

#### Initialization
- Removed: `self.min_signal_gap = config.get('min_signal_gap_minutes', 5)`
- Added: `self.consecutive_green_bars_required = self.config_accessor.get_strategy_param('consecutive_green_bars', 3)`
- Added tracking variables:
  ```python
  self.green_bars_count = 0
  self.last_bar_data = None
  ```

#### Re-entry Logic
- Removed time gap check:
  ```python
  # OLD CODE (REMOVED)
  if self.last_signal_time:
      time_gap = (current_time - self.last_signal_time).total_seconds() / 60
      if time_gap < self.min_signal_gap:
          return False
  ```
- Replaced with consecutive green bars check:
  ```python
  # NEW CODE
  if self.last_signal_time and not self._check_consecutive_green_bars():
      return False
  ```

#### New Helper Methods
1. **`_check_consecutive_green_bars()`**
   - Checks if enough consecutive green bars have occurred
   - Returns True if `green_bars_count >= consecutive_green_bars_required`
   - Includes logging for debugging

2. **`_update_green_bars_count(row)`**
   - Updates the count based on current bar data
   - A green bar is defined as `close > open`
   - For tick data without open price, compares current close with previous close
   - Resets count to 0 on any non-green bar
   - Stores bar data for next comparison

#### Integration Points
- Green bars count is updated in both `can_open_long()` and `generate_entry_signal()` methods
- Ensures consistent tracking across all entry evaluation points

### 3. liveStrategy.py (Live Trading Strategy)
**Similar Changes to researchStrategy.py:**

#### Initialization
- Removed: `self.min_signal_gap = config.get('min_signal_gap_minutes', 5)`
- Added: `self.consecutive_green_bars_required = config.get('consecutive_green_bars', 3)`
- Added tracking variables for green bars count and last bar data

#### Helper Methods
- Added the same `_check_consecutive_green_bars()` and `_update_green_bars_count()` methods
- Simplified error handling for live trading environment

#### Integration
- Updates green bars count in the `can_open_long()` method
- Replaces time gap logic with consecutive green bars requirement

### 4. unified_gui.py (User Interface)
**GUI Enhancements:**

#### New GUI Controls
- Added input field for "Green Bars Req:" in both backtest and forward test tabs
- Placed next to HTF Period parameter for logical grouping
- Default value set to 3

#### Variable Management
- Added `self.bt_consecutive_green_bars` for backtest tab
- Added `self.ft_consecutive_green_bars` for forward test tab
- Integrated with preference loading/saving system

#### Configuration Building
- Added parameter to `build_config_from_gui()` method
- Ensures the user-specified value is passed to the strategy

#### User Preferences
- Added support for loading/saving the consecutive green bars setting
- Maintains user's preferred value across GUI sessions

## How It Works

### Green Bar Definition
A "green bar" is defined as a price bar where:
- `close_price > open_price`

For tick data where open price might not be available:
- Current close is compared with previous close
- `current_close > previous_close` constitutes a green tick

### Counting Logic
1. **Increment:** When a green bar is detected, increment `green_bars_count`
2. **Reset:** When a non-green bar is detected, reset `green_bars_count` to 0
3. **Requirement:** Only allow re-entry when `green_bars_count >= consecutive_green_bars_required`

### Re-entry Condition
Before allowing a new position:
1. Check if this is a re-entry (i.e., `last_signal_time` exists)
2. If it's a re-entry, verify that enough consecutive green bars have occurred
3. Only proceed with entry signal evaluation if requirement is met

## Configuration Examples

### Default Configuration (3 consecutive green bars)
```python
config = {
    'strategy': {
        'consecutive_green_bars': 3,
        # ... other parameters
    }
}
```

### Conservative Configuration (5 consecutive green bars)
```python
config = {
    'strategy': {
        'consecutive_green_bars': 5,
        # ... other parameters
    }
}
```

### Aggressive Configuration (1 green bar - minimal filtering)
```python
config = {
    'strategy': {
        'consecutive_green_bars': 1,
        # ... other parameters
    }
}
```

## Benefits of This Approach

1. **Market Momentum:** Ensures re-entry only occurs during positive price momentum
2. **User Control:** Fully configurable parameter allows strategy tuning
3. **Objective Criteria:** Removes subjective time-based delays
4. **Market-Responsive:** Adapts to market conditions rather than fixed time intervals
5. **Trend Alignment:** Helps ensure entries align with short-term upward price movement

## Debugging and Monitoring

The implementation includes logging to help monitor the consecutive green bars logic:
- Debug messages show when green bars are detected
- Info messages confirm when requirements are met
- Count resets are logged for troubleshooting

## Backward Compatibility

- Existing configurations without the `consecutive_green_bars` parameter will use the default value of 3
- All other strategy logic remains unchanged
- The time gap mechanism has been completely removed

## Testing Recommendations

1. **Backtest Comparison:** Run backtests with different consecutive green bars settings (1, 3, 5, 7)
2. **Market Conditions:** Test in trending vs. sideways markets
3. **Timeframe Impact:** Verify behavior with different data frequencies (1min, 5min, tick)
4. **Edge Cases:** Test with very volatile data to ensure proper count resets