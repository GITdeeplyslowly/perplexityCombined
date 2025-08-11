<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# Create the diff for the improvements belo. Can you make the session timing to be user input with the current values as hard code.

'session': {
'is_intraday': True,
'intraday_start_hour': 9,
'intraday_start_min': 15,
'intraday_end_hour': 15,
'intraday_end_min': 30,
'no_trade_start_minutes': 5,  \# Default buffers
'no_trade_end_minutes': 20,
'timezone': 'Asia/Kolkata'
},

Based on your request to make session timing user-configurable while keeping the current values as defaults, here's the complete diff to implement this improvement:

## **Complete Session Timing User Input Implementation**

### **1. Add Session Timing GUI Elements**

```diff
--- a/gui/unified_gui.py
+++ b/gui/unified_gui.py
@@ -285,6 +285,28 @@
         row += 1
         
+        # Session Timing Configuration
+        ttk.Label(frame, text="Session Timing:", font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky="w", padx=5, pady=(10,2))
+        row += 1
+        
+        session_frame = ttk.Frame(frame)
+        session_frame.grid(row=row, column=0, columnspan=3, sticky="w", padx=5, pady=2)
+        
+        # Session Start Time
+        ttk.Label(session_frame, text="Start Time:").grid(row=0, column=0, sticky="e", padx=2)
+        self.session_start_hour = tk.StringVar(value="9")
+        ttk.Entry(session_frame, textvariable=self.session_start_hour, width=4).grid(row=0, column=1, padx=2)
+        ttk.Label(session_frame, text=":").grid(row=0, column=2)
+        self.session_start_min = tk.StringVar(value="15")
+        ttk.Entry(session_frame, textvariable=self.session_start_min, width=4).grid(row=0, column=3, padx=2)
+        
+        # Session End Time
+        ttk.Label(session_frame, text="End Time:").grid(row=0, column=4, sticky="e", padx=(10,2))
+        self.session_end_hour = tk.StringVar(value="15")
+        ttk.Entry(session_frame, textvariable=self.session_end_hour, width=4).grid(row=0, column=5, padx=2)
+        ttk.Label(session_frame, text=":").grid(row=0, column=6)
+        self.session_end_min = tk.StringVar(value="30")
+        ttk.Entry(session_frame, textvariable=self.session_end_min, width=4).grid(row=0, column=7, padx=2)
+        
+        # Trading Buffers
+        ttk.Label(session_frame, text="Start Buffer (min):").grid(row=1, column=0, sticky="e", padx=2)
+        self.no_trade_start_buffer = tk.StringVar(value="5")
+        ttk.Entry(session_frame, textvariable=self.no_trade_start_buffer, width=6).grid(row=1, column=1, padx=2)
+        
+        ttk.Label(session_frame, text="End Buffer (min):").grid(row=1, column=2, sticky="e", padx=(10,2))
+        self.no_trade_end_buffer = tk.StringVar(value="20")
+        ttk.Entry(session_frame, textvariable=self.no_trade_end_buffer, width=6).grid(row=1, column=3, padx=2)
+        
+        # Timezone
+        ttk.Label(session_frame, text="Timezone:").grid(row=1, column=4, sticky="e", padx=(10,2))
+        self.session_timezone = tk.StringVar(value="Asia/Kolkata")
+        ttk.Entry(session_frame, textvariable=self.session_timezone, width=15).grid(row=1, column=5, columnspan=3, padx=2)
+        
+        row += 1
+        
         # Add instrument panel before capital management
         row = self._build_instrument_panel(frame, row)
```


### **2. Update Backtest Configuration to Use User Inputs**

```diff
--- a/gui/unified_gui.py
+++ b/gui/unified_gui.py
@@ -593,12 +615,14 @@
             # === SESSION SECTION ===
             'session': {
                 'is_intraday': True,
-                'intraday_start_hour': 9,
-                'intraday_start_min': 15,
-                'intraday_end_hour': 15,
-                'intraday_end_min': 30,
-                'timezone': 'Asia/Kolkata'
+                'intraday_start_hour': int(self.session_start_hour.get()),
+                'intraday_start_min': int(self.session_start_min.get()),
+                'intraday_end_hour': int(self.session_end_hour.get()),
+                'intraday_end_min': int(self.session_end_min.get()),
+                'no_trade_start_minutes': int(self.no_trade_start_buffer.get()),
+                'no_trade_end_minutes': int(self.no_trade_end_buffer.get()),
+                'timezone': self.session_timezone.get()
             },
```


### **3. Update Forward Test Configuration to Use User Inputs**

```diff
--- a/gui/unified_gui.py
+++ b/gui/unified_gui.py
@@ -788,12 +810,14 @@
             # === SESSION SECTION ===
             'session': {
                 'is_intraday': True,
-                'intraday_start_hour': 9,
-                'intraday_start_min': 15,
-                'intraday_end_hour': 15,
-                'intraday_end_min': 30,
-                'timezone': 'Asia/Kolkata'
+                'intraday_start_hour': int(self.session_start_hour.get()),
+                'intraday_start_min': int(self.session_start_min.get()),
+                'intraday_end_hour': int(self.session_end_hour.get()),
+                'intraday_end_min': int(self.session_end_min.get()),
+                'no_trade_start_minutes': int(self.no_trade_start_buffer.get()),
+                'no_trade_end_minutes': int(self.no_trade_end_buffer.get()),
+                'timezone': self.session_timezone.get()
             },
```


### **4. Add Session Validation Method**

```diff
--- a/gui/unified_gui.py
+++ b/gui/unified_gui.py
@@ -665,6 +687,35 @@
         logger.info(f"✅ Configuration validation passed - all required sections present")
         return True
 
+    def _validate_session_timing(self):
+        """Validate user-entered session timing parameters"""
+        try:
+            start_hour = int(self.session_start_hour.get())
+            start_min = int(self.session_start_min.get())
+            end_hour = int(self.session_end_hour.get())
+            end_min = int(self.session_end_min.get())
+            start_buffer = int(self.no_trade_start_buffer.get())
+            end_buffer = int(self.no_trade_end_buffer.get())
+            
+            # Basic validation
+            if not (0 <= start_hour <= 23) or not (0 <= start_min <= 59):
+                raise ValueError("Invalid session start time")
+            if not (0 <= end_hour <= 23) or not (0 <= end_min <= 59):
+                raise ValueError("Invalid session end time")
+            if start_buffer < 0 or end_buffer < 0:
+                raise ValueError("Buffers cannot be negative")
+                
+            # Session sequence validation
+            start_minutes = start_hour * 60 + start_min
+            end_minutes = end_hour * 60 + end_min
+            
+            if start_minutes >= end_minutes:
+                raise ValueError("Session end must be after session start")
+                
+            return True
+            
+        except ValueError as e:
+            messagebox.showerror("Session Timing Error", f"Invalid session configuration: {str(e)}")
+            return False
+
     # --- Forward Test Tab ---
```


### **5. Add Validation Call Before Backtest Execution**

```diff
--- a/gui/unified_gui.py
+++ b/gui/unified_gui.py
@@ -625,6 +647,11 @@
             # Validate configuration structure before running
             self._validate_nested_config(gui_config)
+            
+            # Validate session timing
+            if not self._validate_session_timing():
+                return
+                
             logger.info("🔧 Using nested configuration structure for backtest")
```


## **Key Features of This Implementation**

### **✅ User-Configurable Session Parameters**

- **Session Start Time**: Hour and minute inputs (default: 9:15)
- **Session End Time**: Hour and minute inputs (default: 15:30)
- **Trading Buffers**: Start and end buffer minutes (default: 5 and 20)
- **Timezone**: Configurable timezone string (default: Asia/Kolkata)


### **✅ Enhanced User Experience**

- **Organized Layout**: Clean, intuitive session timing panel
- **Real-time Configuration**: Changes immediately apply to next backtest/forward test
- **Validation**: Prevents invalid session configurations
- **Default Values**: Current hardcoded values become user-modifiable defaults


### **✅ Consistent Implementation**

- **Both Modes**: Backtest and forward test use same session inputs
- **Configuration Integration**: Seamlessly integrates with existing nested config structure
- **Backward Compatibility**: Maintains all existing functionality


### **✅ Expected Results After Implementation**

1. **User Control**: Complete control over session timing without code changes
2. **Flexible Trading**: Can test different market sessions (pre-market, main session, etc.)
3. **Custom Buffers**: Adjust no-trade periods based on strategy requirements
4. **Timezone Support**: Support for different market timezones if needed

This implementation directly addresses your requirement to make session timing user-driven while maintaining the current NSE session timing (9:15-15:30) and standard buffers (5 min start, 20 min end) as defaults.

<div style="text-align: center">⁂</div>

[^1]: unified_gui.py

