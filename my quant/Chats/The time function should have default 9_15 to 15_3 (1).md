<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# The time function should have default 9:15 to 15:30 session with a 20 min buffer at the end and 5 min beginning. With the user being able to make changes as required.

The data should only be able to mark the maximum session length, but not the smaller lengths, that should be user driven. So if the data is from 10:15 to 15:15, then the system can inform the max and min time but if the user wishes to use session between 11.00 and 13.00, he should have the flexibity to do it. The system should only process data only between the session timing set by the user.

Based on your requirements and the timing issues identified in your trading bot, here's a comprehensive solution for **user-controlled session timing with data-driven maximum bounds**:

## **Complete Session Timing Solution**

### **1. Data Session Analysis \& User Feedback**

**File**: `utils/session_analyzer.py` (New)

```python
"""
Session analyzer to determine data bounds and provide user feedback
"""
import pandas as pd
from datetime import time, datetime, timedelta
from typing import Tuple, Dict, Any
import logging

logger = logging.getLogger(__name__)

def analyze_data_session_bounds(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Analyze data to find maximum available session bounds
    
    Returns:
        Dict with session analysis including max bounds and recommendations
    """
    if df.empty:
        return {"error": "No data provided"}
    
    # Get earliest and latest timestamps
    earliest_time = df.index.min()
    latest_time = df.index.max()
    
    # Extract time components
    earliest_time_only = earliest_time.time()
    latest_time_only = latest_time.time()
    
    # Calculate session duration
    earliest_minutes = earliest_time_only.hour * 60 + earliest_time_only.minute
    latest_minutes = latest_time_only.hour * 60 + latest_time_only.minute
    duration_minutes = latest_minutes - earliest_minutes
    
    # NSE standard session for reference
    nse_start = time(9, 15)
    nse_end = time(15, 30)
    nse_duration = (15 * 60 + 30) - (9 * 60 + 15)  # 375 minutes
    
    return {
        "data_start_time": earliest_time_only,
        "data_end_time": latest_time_only,
        "data_duration_minutes": duration_minutes,
        "data_start_timestamp": earliest_time,
        "data_end_timestamp": latest_time,
        "total_ticks": len(df),
        "nse_standard_start": nse_start,
        "nse_standard_end": nse_end,
        "nse_standard_duration": nse_duration,
        "is_full_session": duration_minutes >= (nse_duration - 30),  # Allow 30min tolerance
        "recommendations": _generate_session_recommendations(
            earliest_time_only, latest_time_only, duration_minutes
        )
    }

def _generate_session_recommendations(start_time: time, end_time: time, 
                                     duration: int) -> Dict[str, Any]:
    """Generate session timing recommendations based on data"""
    
    recommendations = {
        "can_use_full_nse": False,
        "suggested_buffers": {},
        "warnings": [],
        "optimal_session": {}
    }
    
    # Check if data covers full NSE session
    nse_start_minutes = 9 * 60 + 15  # 9:15 AM
    nse_end_minutes = 15 * 60 + 30   # 3:30 PM
    
    data_start_minutes = start_time.hour * 60 + start_time.minute
    data_end_minutes = end_time.hour * 60 + end_time.minute
    
    if data_start_minutes <= nse_start_minutes and data_end_minutes >= nse_end_minutes:
        recommendations["can_use_full_nse"] = True
        recommendations["suggested_buffers"] = {
            "start_buffer": 5,  # 5 minutes after market open
            "end_buffer": 20    # 20 minutes before market close
        }
    else:
        # Suggest conservative buffers for partial data
        available_duration = data_end_minutes - data_start_minutes
        start_buffer = min(5, available_duration // 10)  # Max 5 min or 10% of session
        end_buffer = min(20, available_duration // 5)     # Max 20 min or 20% of session
        
        recommendations["suggested_buffers"] = {
            "start_buffer": start_buffer,
            "end_buffer": end_buffer
        }
        
        recommendations["warnings"].append(
            f"Data only covers {data_start_minutes//60:02d}:{data_start_minutes%60:02d} to "
            f"{data_end_minutes//60:02d}:{data_end_minutes%60:02d} - partial session"
        )
    
    # Calculate optimal session (data bounds minus suggested buffers)
    optimal_start_minutes = data_start_minutes + recommendations["suggested_buffers"]["start_buffer"]
    optimal_end_minutes = data_end_minutes - recommendations["suggested_buffers"]["end_buffer"]
    
    recommendations["optimal_session"] = {
        "start_time": time(optimal_start_minutes // 60, optimal_start_minutes % 60),
        "end_time": time(optimal_end_minutes // 60, optimal_end_minutes % 60),
        "duration_minutes": optimal_end_minutes - optimal_start_minutes
    }
    
    return recommendations

def validate_user_session(user_start: time, user_end: time, data_bounds: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate user-defined session against data bounds
    
    Returns:
        Validation result with status and messages
    """
    validation = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "adjusted_session": None
    }
    
    data_start = data_bounds["data_start_time"]
    data_end = data_bounds["data_end_time"]
    
    user_start_minutes = user_start.hour * 60 + user_start.minute
    user_end_minutes = user_end.hour * 60 + user_end.minute
    data_start_minutes = data_start.hour * 60 + data_start.minute
    data_end_minutes = data_end.hour * 60 + data_end.minute
    
    # Check if user session is within data bounds
    if user_start_minutes < data_start_minutes:
        validation["errors"].append(
            f"Session start {user_start} is before data start {data_start}. "
            f"Please choose start time at or after {data_start}."
        )
        validation["valid"] = False
    
    if user_end_minutes > data_end_minutes:
        validation["errors"].append(
            f"Session end {user_end} is after data end {data_end}. "
            f"Please choose end time at or before {data_end}."
        )
        validation["valid"] = False
    
    if user_start_minutes >= user_end_minutes:
        validation["errors"].append("Session start must be before session end")
        validation["valid"] = False
    
    # Check session duration
    if validation["valid"]:
        session_duration = user_end_minutes - user_start_minutes
        if session_duration < 30:  # Less than 30 minutes
            validation["warnings"].append(
                f"Very short session duration: {session_duration} minutes. "
                "Consider longer session for meaningful backtesting."
            )
        elif session_duration < 60:  # Less than 1 hour
            validation["warnings"].append(
                f"Short session duration: {session_duration} minutes. "
                "May limit trading opportunities."
            )
    
    return validation
```


### **2. Enhanced GUI with Data-Driven Session Controls**

**File**: `gui/unified_gui.py` (Enhanced session timing section)

```python
def _build_enhanced_session_timing_panel(self, frame, row):
    """Build data-driven session timing panel with user controls"""
    
    # Session Timing Header
    ttk.Label(frame, text="📅 Session Timing Configuration", font=('Arial', 11, 'bold')).grid(
        row=row, column=0, columnspan=3, sticky="w", padx=5, pady=(15,5)
    )
    row += 1
    
    # Create main session frame
    session_frame = ttk.LabelFrame(frame, text="User-Defined Session", padding=10)
    session_frame.grid(row=row, column=0, columnspan=3, sticky="ew", padx=5, pady=5)
    
    # Data Analysis Section
    analysis_frame = ttk.Frame(session_frame)
    analysis_frame.grid(row=0, column=0, columnspan=4, sticky="ew", pady=(0,10))
    
    ttk.Label(analysis_frame, text="📊 Data Analysis:", font=('Arial', 9, 'bold')).grid(
        row=0, column=0, sticky="w"
    )
    
    self.data_session_info = tk.StringVar(value="Load data to see available session range")
    ttk.Label(analysis_frame, textvariable=self.data_session_info, foreground="blue").grid(
        row=0, column=1, sticky="w", padx=(10,0)
    )
    
    ttk.Button(analysis_frame, text="Analyze Data", 
               command=self._analyze_data_session).grid(row=0, column=2, padx=(10,0))
    
    # User Session Configuration
    config_frame = ttk.Frame(session_frame)
    config_frame.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(10,0))
    
    # Session Start Time
    ttk.Label(config_frame, text="Session Start:").grid(row=0, column=0, sticky="e", padx=(0,5))
    self.user_session_start_hour = tk.StringVar(value="9")
    self.user_session_start_min = tk.StringVar(value="15")
    
    start_frame = ttk.Frame(config_frame)
    start_frame.grid(row=0, column=1, sticky="w")
    ttk.Entry(start_frame, textvariable=self.user_session_start_hour, width=4).pack(side=tk.LEFT)
    ttk.Label(start_frame, text=":").pack(side=tk.LEFT, padx=2)
    ttk.Entry(start_frame, textvariable=self.user_session_start_min, width=4).pack(side=tk.LEFT)
    
    # Session End Time
    ttk.Label(config_frame, text="Session End:").grid(row=0, column=2, sticky="e", padx=(20,5))
    self.user_session_end_hour = tk.StringVar(value="15")
    self.user_session_end_min = tk.StringVar(value="30")
    
    end_frame = ttk.Frame(config_frame)
    end_frame.grid(row=0, column=3, sticky="w")
    ttk.Entry(end_frame, textvariable=self.user_session_end_hour, width=4).pack(side=tk.LEFT)
    ttk.Label(end_frame, text=":").pack(side=tk.LEFT, padx=2)
    ttk.Entry(end_frame, textvariable=self.user_session_end_min, width=4).pack(side=tk.LEFT)
    
    # Buffer Configuration
    buffer_frame = ttk.Frame(session_frame)
    buffer_frame.grid(row=2, column=0, columnspan=4, sticky="ew", pady=(10,0))
    
    ttk.Label(buffer_frame, text="Start Buffer (min):").grid(row=0, column=0, sticky="e", padx=(0,5))
    self.user_start_buffer = tk.StringVar(value="5")
    ttk.Entry(buffer_frame, textvariable=self.user_start_buffer, width=6).grid(row=0, column=1, sticky="w")
    
    ttk.Label(buffer_frame, text="End Buffer (min):").grid(row=0, column=2, sticky="e", padx=(20,5))
    self.user_end_buffer = tk.StringVar(value="20")
    ttk.Entry(buffer_frame, textvariable=self.user_end_buffer, width=6).grid(row=0, column=3, sticky="w")
    
    # Validation and Apply
    action_frame = ttk.Frame(session_frame)
    action_frame.grid(row=3, column=0, columnspan=4, pady=(15,0))
    
    ttk.Button(action_frame, text="Validate Session", 
               command=self._validate_user_session).pack(side=tk.LEFT, padx=(0,10))
    
    ttk.Button(action_frame, text="Use Optimal", 
               command=self._apply_optimal_session).pack(side=tk.LEFT)
    
    # Status Display
    self.session_validation_status = tk.StringVar(value="Configure session timing above")
    status_label = ttk.Label(session_frame, textvariable=self.session_validation_status, 
                            foreground="orange", wraplength=400)
    status_label.grid(row=4, column=0, columnspan=4, pady=(10,0))
    
    # Store reference for color changes
    self.session_status_label = status_label
    
    return row + 1

def _analyze_data_session(self):
    """Analyze loaded data to determine session bounds"""
    if not hasattr(self, 'data_file') or not self.bt_data_file.get():
        messagebox.showwarning("No Data", "Please select a data file first")
        return
    
    try:
        # Load data for analysis
        from utils.simple_loader import load_data_simple
        from utils.session_analyzer import analyze_data_session_bounds
        
        df = load_data_simple(self.bt_data_file.get())
        analysis = analyze_data_session_bounds(df)
        
        if "error" in analysis:
            self.data_session_info.set(f"❌ Error: {analysis['error']}")
            return
        
        # Update data session info
        data_start = analysis["data_start_time"]
        data_end = analysis["data_end_time"]
        duration = analysis["data_duration_minutes"]
        
        self.data_session_info.set(
            f"📊 Data Range: {data_start.strftime('%H:%M')} - {data_end.strftime('%H:%M')} "
            f"({duration} min, {analysis['total_ticks']} ticks)"
        )
        
        # Store analysis for validation
        self.session_analysis = analysis
        
        # Show recommendations
        recommendations = analysis["recommendations"]
        if recommendations["warnings"]:
            warning_msg = "\n".join(recommendations["warnings"])
            messagebox.showinfo("Data Analysis", 
                               f"Session Analysis Complete!\n\n"
                               f"Warnings:\n{warning_msg}\n\n"
                               f"Suggested buffers: {recommendations['suggested_buffers']['start_buffer']} min start, "
                               f"{recommendations['suggested_buffers']['end_buffer']} min end")
        else:
            messagebox.showinfo("Data Analysis", 
                               f"✅ Data covers full trading session!\n"
                               f"Suggested buffers: {recommendations['suggested_buffers']['start_buffer']} min start, "
                               f"{recommendations['suggested_buffers']['end_buffer']} min end")
        
    except Exception as e:
        self.data_session_info.set(f"❌ Analysis failed: {str(e)}")
        logger.error(f"Session analysis error: {e}")

def _validate_user_session(self):
    """Validate user-defined session against data bounds"""
    if not hasattr(self, 'session_analysis'):
        messagebox.showwarning("No Analysis", "Please analyze data first")
        return
    
    try:
        from utils.session_analyzer import validate_user_session
        from datetime import time
        
        # Get user input
        user_start = time(
            int(self.user_session_start_hour.get()),
            int(self.user_session_start_min.get())
        )
        user_end = time(
            int(self.user_session_end_hour.get()),
            int(self.user_session_end_min.get())
        )
        
        # Validate against data bounds
        validation = validate_user_session(user_start, user_end, self.session_analysis)
        
        if validation["valid"]:
            # Calculate effective trading window
            start_buffer = int(self.user_start_buffer.get())
            end_buffer = int(self.user_end_buffer.get())
            
            user_start_minutes = user_start.hour * 60 + user_start.minute
            user_end_minutes = user_end.hour * 60 + user_end.minute
            effective_window = (user_end_minutes - user_start_minutes) - (start_buffer + end_buffer)
            
            self.session_validation_status.set(
                f"✅ Valid session: {user_start.strftime('%H:%M')} - {user_end.strftime('%H:%M')} "
                f"(Effective trading: {effective_window} minutes)"
            )
            self.session_status_label.config(foreground="green")
            
            if validation["warnings"]:
                warning_msg = "\n".join(validation["warnings"])
                messagebox.showinfo("Session Validated", f"✅ Session is valid!\n\nWarnings:\n{warning_msg}")
            
        else:
            error_msg = "\n".join(validation["errors"])
            self.session_validation_status.set("❌ Invalid session - see errors")
            self.session_status_label.config(foreground="red")
            messagebox.showerror("Session Validation Failed", f"Please fix these issues:\n\n{error_msg}")
            
    except ValueError as e:
        self.session_validation_status.set("❌ Invalid time format")
        self.session_status_label.config(foreground="red")
        messagebox.showerror("Invalid Input", "Please enter valid time values (HH:MM format)")

def _apply_optimal_session(self):
    """Apply the optimal session timing based on data analysis"""
    if not hasattr(self, 'session_analysis'):
        messagebox.showwarning("No Analysis", "Please analyze data first")
        return
    
    optimal = self.session_analysis["recommendations"]["optimal_session"]
    buffers = self.session_analysis["recommendations"]["suggested_buffers"]
    
    # Apply optimal session times
    self.user_session_start_hour.set(str(optimal["start_time"].hour))
    self.user_session_start_min.set(str(optimal["start_time"].minute))
    self.user_session_end_hour.set(str(optimal["end_time"].hour))
    self.user_session_end_min.set(str(optimal["end_time"].minute))
    
    # Apply suggested buffers
    self.user_start_buffer.set(str(buffers["start_buffer"]))
    self.user_end_buffer.set(str(buffers["end_buffer"]))
    
    # Auto-validate
    self._validate_user_session()
    
    messagebox.showinfo("Optimal Session Applied", 
                       f"Applied optimal session timing:\n"
                       f"Session: {optimal['start_time'].strftime('%H:%M')} - {optimal['end_time'].strftime('%H:%M')}\n"
                       f"Buffers: {buffers['start_buffer']} min start, {buffers['end_buffer']} min end")
```


### **3. Data Filtering Based on User Session**

**File**: `utils/session_filter.py` (New)

```python
"""
Filter data based on user-defined session timing
"""
import pandas as pd
from datetime import time, datetime
from typing import Tuple
import logging

logger = logging.getLogger(__name__)

def filter_data_by_session(df: pd.DataFrame, session_start: time, session_end: time,
                          start_buffer: int = 0, end_buffer: int = 0) -> pd.DataFrame:
    """
    Filter DataFrame to only include data within user-defined session
    
    Args:
        df: Input DataFrame with datetime index
        session_start: Session start time
        session_end: Session end time  
        start_buffer: Minutes to skip after session start
        end_buffer: Minutes to skip before session end
        
    Returns:
        Filtered DataFrame containing only session data
    """
    if df.empty:
        return df
    
    # Calculate effective session boundaries
    session_start_minutes = session_start.hour * 60 + session_start.minute
    session_end_minutes = session_end.hour * 60 + session_end.minute
    
    effective_start_minutes = session_start_minutes + start_buffer
    effective_end_minutes = session_end_minutes - end_buffer
    
    effective_start_time = time(effective_start_minutes // 60, effective_start_minutes % 60)
    effective_end_time = time(effective_end_minutes // 60, effective_end_minutes % 60)
    
    logger.info(f"Filtering data to session: {effective_start_time} - {effective_end_time}")
    
    # Filter by time of day
    mask = df.index.to_series().dt.time.between(effective_start_time, effective_end_time)
    filtered_df = df[mask].copy()
    
    original_count = len(df)
    filtered_count = len(filtered_df)
    
    logger.info(f"Session filtering: {original_count} → {filtered_count} rows "
               f"({filtered_count/original_count*100:.1f}% retained)")
    
    return filtered_df

def validate_session_coverage(df: pd.DataFrame, session_start: time, session_end: time) -> Dict[str, Any]:
    """
    Validate that data adequately covers the requested session
    
    Returns:
        Dict with coverage analysis
    """
    if df.empty:
        return {"error": "No data provided"}
    
    # Get data time bounds
    data_start_time = df.index.min().time()
    data_end_time = df.index.max().time()
    
    # Convert to minutes for comparison
    data_start_minutes = data_start_time.hour * 60 + data_start_time.minute
    data_end_minutes = data_end_time.hour * 60 + data_end_time.minute
    session_start_minutes = session_start.hour * 60 + session_start.minute
    session_end_minutes = session_end.hour * 60 + session_end.minute
    
    coverage = {
        "full_coverage": data_start_minutes <= session_start_minutes and data_end_minutes >= session_end_minutes,
        "partial_coverage": not (data_end_minutes < session_start_minutes or data_start_minutes > session_end_minutes),
        "data_start_time": data_start_time,
        "data_end_time": data_end_time,
        "requested_start": session_start,
        "requested_end": session_end,
        "coverage_percentage": 0
    }
    
    if coverage["partial_coverage"]:
        # Calculate actual overlap
        overlap_start = max(data_start_minutes, session_start_minutes)
        overlap_end = min(data_end_minutes, session_end_minutes)
        overlap_duration = max(0, overlap_end - overlap_start)
        requested_duration = session_end_minutes - session_start_minutes
        
        coverage["coverage_percentage"] = (overlap_duration / requested_duration) * 100 if requested_duration > 0 else 0
    
    return coverage
```


### **4. Integration with Backtest Runner**

**File**: `backtest/backtest_runner.py` (Enhanced data loading)

```python
def _run_backtest_internal_with_session_filter(config: Dict[str, Any], data_file: str,
                                             df_normalized=None, skip_indicator_calculation=False):
    """Enhanced backtest runner with user-defined session filtering"""
    
    # ... existing initialization code ...
    
    # Extract user session configuration
    session_config = config.get('session', {})
    user_session_start = time(
        session_config.get('user_session_start_hour', 9),
        session_config.get('user_session_start_min', 15)
    )
    user_session_end = time(
        session_config.get('user_session_end_hour', 15), 
        session_config.get('user_session_end_min', 30)
    )
    start_buffer = session_config.get('user_start_buffer', 5)
    end_buffer = session_config.get('user_end_buffer', 20)
    
    # Load and analyze data
    if df_normalized is None:
        from utils.simple_loader import load_data_simple
        from utils.session_analyzer import analyze_data_session_bounds, validate_user_session
        from utils.session_filter import filter_data_by_session, validate_session_coverage
        
        logger.info("Loading and analyzing data...")
        df_raw = load_data_simple(data_file, process_as_ticks=True)
        
        # Analyze data session bounds
        session_analysis = analyze_data_session_bounds(df_raw)
        logger.info(f"Data session analysis: {session_analysis['data_start_time']} to {session_analysis['data_end_time']}")
        
        # Validate user session against data
        validation = validate_user_session(user_session_start, user_session_end, session_analysis)
        if not validation["valid"]:
            error_msg = "User session validation failed: " + "; ".join(validation["errors"])
            logger.error(error_msg)
            return pd.DataFrame(), {"error": error_msg}
        
        if validation["warnings"]:
            for warning in validation["warnings"]:
                logger.warning(f"Session warning: {warning}")
        
        # Validate session coverage
        coverage = validate_session_coverage(df_raw, user_session_start, user_session_end)
        if coverage["coverage_percentage"] < 50:
            logger.warning(f"Low session coverage: {coverage['coverage_percentage']:.1f}%")
        
        # Filter data to user-defined session
        df_normalized = filter_data_by_session(df_raw, user_session_start, user_session_end, 
                                              start_buffer, end_buffer)
        
        if df_normalized.empty:
            error_msg = f"No data remaining after session filtering {user_session_start} - {user_session_end}"
            logger.error(error_msg)
            return pd.DataFrame(), {"error": error_msg}
        
        logger.info(f"Session filtering complete: {len(df_raw)} → {len(df_normalized)} rows "
                   f"({len(df_normalized)/len(df_raw)*100:.1f}% retained)")
    
    # ... continue with existing backtest logic using df_normalized ...
```


### **5. Updated Configuration Structure**

**File**: `strategy_config.yaml` (Enhanced session section)

```yaml
session:
  # === USER-DEFINED SESSION TIMING ===
  # Default NSE session with buffers
  user_session_start_hour: 9      # User configurable
  user_session_start_min: 15      # User configurable  
  user_session_end_hour: 15       # User configurable
  user_session_end_min: 30        # User configurable
  
  # === USER-DEFINED BUFFERS ===
  user_start_buffer: 5            # Minutes after session start (default 5)
  user_end_buffer: 20             # Minutes before session end (default 20)
  
  # === SYSTEM SETTINGS ===
  timezone: "Asia/Kolkata"
  enforce_session_bounds: true    # Strictly filter data to user session
  min_session_duration: 30       # Minimum session duration in minutes
  
  # === DATA VALIDATION ===
  require_full_coverage: false   # If true, require 100% data coverage of user session
  min_coverage_percentage: 50    # Minimum data coverage required (%)
  
  # === BACKWARD COMPATIBILITY ===
  intraday_start_hour: 9          # Used if user session not defined
  intraday_start_min: 15
  intraday_end_hour: 15  
  intraday_end_min: 30
  exit_before_close: 20
```


## **Key Benefits of This Solution**

### **✅ Complete User Control**

- **Data-driven bounds**: System analyzes data to show maximum available session range[^1][^2]
- **User flexibility**: Users can define any session within data bounds[^2][^3]
- **No system overrides**: Exact user configuration is respected


### **✅ Intelligent Feedback**

- **Real-time validation**: Immediate feedback on session feasibility[^3][^4]
- **Coverage analysis**: Shows percentage of requested session covered by data
- **Optimal suggestions**: System recommends optimal session based on data analysis


### **✅ Default Behavior as Requested**

- **Default session**: 9:15 AM - 3:30 PM NSE standard[^5][^6]
- **Default buffers**: 5 minutes start, 20 minutes end[^6]
- **User flexibility**: Full ability to modify all timing parameters


### **✅ Data Processing Efficiency**

- **Pre-filtering**: Only processes data within user-defined session[^7][^4]
- **Memory optimization**: Reduced data volume for large tick datasets
- **Performance improvement**: Faster backtesting with session-filtered data

This solution directly addresses your zero-signals issue by ensuring the session timing logic is completely user-controlled and transparently validated against actual data bounds.[^2][^3]

<div style="text-align: center">⁂</div>

[^1]: https://docs.defined.fi/trading/getting-started/trade-settings

[^2]: https://www.tradingview.com/script/vcVMyr4h-Session-Filter-Trendoscope/

[^3]: https://gocharting.com/docs/general-settings/Session-settings

[^4]: https://forum.ninjatrader.com/forum/ninjatrader-8/strategy-development/1265601-restrict-trading-to-specific-times-of-day

[^5]: https://www.nseindia.com/products-services/equity-market-pre-open

[^6]: https://www.elearnmarkets.com/school/units/intraday-trading

[^7]: https://www.tradingcode.net/tradingview/limit-day-trades/

[^8]: cache_manager.py

[^9]: config_helper.py

[^10]: config_loader.py

[^11]: logging_utils.py

[^12]: simple_loader.py

[^13]: time_utils.py

[^14]: unified_gui.py

[^15]: indicators.py

[^16]: liveStrategy.py

[^17]: position_manager.py

[^18]: researchStrategy.py

[^19]: strategy_config.yaml

[^20]: backtest_runner.py

[^21]: 1.md

[^22]: 2.md

