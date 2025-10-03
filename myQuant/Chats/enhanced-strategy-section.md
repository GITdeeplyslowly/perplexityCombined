# Updated GUI Implementation: Enhanced Strategy Section with Requirements

Based on your requirements, here's the updated implementation focusing on the strategic section improvements:

## Key Changes Required

### 1. Parameters Near Respective Indicators
### 2. Grey Out Unchecked Indicators and Parameters  
### 3. Config Validation Dialog Before Freezing
### 4. Consecutive Green Tick as Indicator with Checkbox
### 5. Noise Filter as Parameter for Consecutive Green Tick
### 6. Enhanced Font Sizes and Styles
### 7. Better UI Layout with More Columns/Rows

## Updated Strategy Section Implementation

```python
def _build_strategy_section(self, parent):
    """Enhanced strategy configuration with grouped indicators and parameters"""
    section = CollapsibleFrame(parent, "Strategy Configuration", collapsed=False)
    content = section.get_content_frame()
    
    # Configure main grid layout
    content.columnconfigure(1, weight=1)
    
    # Create styles for different UI elements
    self._create_strategy_styles()
    
    # Build indicator groups with their parameters
    self._build_trend_indicators_group(content)
    self._build_momentum_indicators_group(content) 
    self._build_volume_indicators_group(content)
    self._build_pattern_indicators_group(content)
    
    section.pack(fill='x', pady=(0,10))

def _create_strategy_styles(self):
    """Create custom styles for strategy section"""
    style = ttk.Style()
    
    # Group headers - large, bold font
    style.configure('GroupHeader.TLabel', 
                   font=('Arial', 12, 'bold'), 
                   foreground='navy')
    
    # Indicator labels - medium font
    style.configure('Indicator.TLabel', 
                   font=('Arial', 10, 'bold'), 
                   foreground='darkgreen')
    
    # Parameter labels - normal font
    style.configure('Parameter.TLabel', 
                   font=('Arial', 9), 
                   foreground='black')
    
    # Disabled style for greyed out elements
    style.configure('Disabled.TLabel', 
                   font=('Arial', 9), 
                   foreground='grey')
    
    style.configure('Disabled.TEntry', 
                   fieldbackground='lightgrey')

def _build_trend_indicators_group(self, parent):
    """Trend indicators with their parameters grouped together"""
    row_start = 0
    
    # Group header
    ttk.Label(parent, text="📈 TREND INDICATORS", 
             style='GroupHeader.TLabel').grid(row=row_start, column=0, columnspan=6, 
                                            sticky='w', pady=(10,5))
    
    # EMA Crossover with parameters
    row = row_start + 1
    ema_frame = ttk.LabelFrame(parent, text="EMA Crossover", padding=10)
    ema_frame.grid(row=row, column=0, columnspan=6, sticky='ew', padx=5, pady=5)
    ema_frame.columnconfigure((1,3), weight=1)
    
    # EMA Checkbox
    self.ema_cb = ttk.Checkbutton(ema_frame, text="Enable EMA Crossover", 
                                 variable=self.bt_use_ema_crossover,
                                 style='Indicator.TLabel',
                                 command=lambda: self._toggle_indicator_group('ema'))
    self.ema_cb.grid(row=0, column=0, columnspan=4, sticky='w', pady=(0,5))
    
    # EMA Parameters in same row
    ttk.Label(ema_frame, text="Fast Period:", style='Parameter.TLabel').grid(row=1, column=0, sticky='e', padx=(0,5))
    self.ema_fast_entry = ttk.Entry(ema_frame, textvariable=self.bt_fast_ema, width=8, font=('Arial', 10))
    self.ema_fast_entry.grid(row=1, column=1, sticky='w', padx=(0,15))
    
    ttk.Label(ema_frame, text="Slow Period:", style='Parameter.TLabel').grid(row=1, column=2, sticky='e', padx=(0,5))
    self.ema_slow_entry = ttk.Entry(ema_frame, textvariable=self.bt_slow_ema, width=8, font=('Arial', 10))
    self.ema_slow_entry.grid(row=1, column=3, sticky='w')
    
    # Store widgets for enable/disable functionality
    self.ema_widgets = [self.ema_fast_entry, self.ema_slow_entry]
    self.ema_labels = ema_frame.grid_slaves()
    
    # MACD with parameters
    row += 1
    macd_frame = ttk.LabelFrame(parent, text="MACD", padding=10)
    macd_frame.grid(row=row, column=0, columnspan=6, sticky='ew', padx=5, pady=5)
    macd_frame.columnconfigure((1,3,5), weight=1)
    
    # MACD Checkbox
    self.macd_cb = ttk.Checkbutton(macd_frame, text="Enable MACD", 
                                  variable=self.bt_use_macd,
                                  style='Indicator.TLabel',
                                  command=lambda: self._toggle_indicator_group('macd'))
    self.macd_cb.grid(row=0, column=0, columnspan=6, sticky='w', pady=(0,5))
    
    # MACD Parameters in same row
    ttk.Label(macd_frame, text="Fast:", style='Parameter.TLabel').grid(row=1, column=0, sticky='e', padx=(0,5))
    self.macd_fast_entry = ttk.Entry(macd_frame, textvariable=self.bt_macd_fast, width=6, font=('Arial', 10))
    self.macd_fast_entry.grid(row=1, column=1, sticky='w', padx=(0,10))
    
    ttk.Label(macd_frame, text="Slow:", style='Parameter.TLabel').grid(row=1, column=2, sticky='e', padx=(0,5))
    self.macd_slow_entry = ttk.Entry(macd_frame, textvariable=self.bt_macd_slow, width=6, font=('Arial', 10))
    self.macd_slow_entry.grid(row=1, column=3, sticky='w', padx=(0,10))
    
    ttk.Label(macd_frame, text="Signal:", style='Parameter.TLabel').grid(row=1, column=4, sticky='e', padx=(0,5))
    self.macd_signal_entry = ttk.Entry(macd_frame, textvariable=self.bt_macd_signal, width=6, font=('Arial', 10))
    self.macd_signal_entry.grid(row=1, column=5, sticky='w')
    
    self.macd_widgets = [self.macd_fast_entry, self.macd_slow_entry, self.macd_signal_entry]

def _build_momentum_indicators_group(self, parent):
    """Momentum indicators with their parameters"""
    # Find next available row
    used_rows = [int(child.grid_info()['row']) for child in parent.grid_slaves() if child.grid_info()]
    row_start = max(used_rows) + 1 if used_rows else 0
    
    # Group header
    ttk.Label(parent, text="⚡ MOMENTUM INDICATORS", 
             style='GroupHeader.TLabel').grid(row=row_start, column=0, columnspan=6, 
                                            sticky='w', pady=(10,5))
    
    # RSI Filter with parameters
    row = row_start + 1
    rsi_frame = ttk.LabelFrame(parent, text="RSI Filter", padding=10)
    rsi_frame.grid(row=row, column=0, columnspan=6, sticky='ew', padx=5, pady=5)
    rsi_frame.columnconfigure((1,3,5), weight=1)
    
    # RSI Checkbox
    self.rsi_cb = ttk.Checkbutton(rsi_frame, text="Enable RSI Filter", 
                                 variable=self.bt_use_rsi_filter,
                                 style='Indicator.TLabel',
                                 command=lambda: self._toggle_indicator_group('rsi'))
    self.rsi_cb.grid(row=0, column=0, columnspan=6, sticky='w', pady=(0,5))
    
    # RSI Parameters
    ttk.Label(rsi_frame, text="Period:", style='Parameter.TLabel').grid(row=1, column=0, sticky='e', padx=(0,5))
    self.rsi_length_entry = ttk.Entry(rsi_frame, textvariable=self.bt_rsi_length, width=6, font=('Arial', 10))
    self.rsi_length_entry.grid(row=1, column=1, sticky='w', padx=(0,10))
    
    ttk.Label(rsi_frame, text="Oversold:", style='Parameter.TLabel').grid(row=1, column=2, sticky='e', padx=(0,5))
    self.rsi_oversold_entry = ttk.Entry(rsi_frame, textvariable=self.bt_rsi_oversold, width=6, font=('Arial', 10))
    self.rsi_oversold_entry.grid(row=1, column=3, sticky='w', padx=(0,10))
    
    ttk.Label(rsi_frame, text="Overbought:", style='Parameter.TLabel').grid(row=1, column=4, sticky='e', padx=(0,5))
    self.rsi_overbought_entry = ttk.Entry(rsi_frame, textvariable=self.bt_rsi_overbought, width=6, font=('Arial', 10))
    self.rsi_overbought_entry.grid(row=1, column=5, sticky='w')
    
    self.rsi_widgets = [self.rsi_length_entry, self.rsi_oversold_entry, self.rsi_overbought_entry]

def _build_volume_indicators_group(self, parent):
    """Volume-based indicators"""
    used_rows = [int(child.grid_info()['row']) for child in parent.grid_slaves() if child.grid_info()]
    row_start = max(used_rows) + 1 if used_rows else 0
    
    # Group header  
    ttk.Label(parent, text="📊 VOLUME INDICATORS", 
             style='GroupHeader.TLabel').grid(row=row_start, column=0, columnspan=6, 
                                            sticky='w', pady=(10,5))
    
    # VWAP (no parameters needed)
    row = row_start + 1
    vwap_frame = ttk.LabelFrame(parent, text="Volume Weighted Average Price", padding=10)
    vwap_frame.grid(row=row, column=0, columnspan=6, sticky='ew', padx=5, pady=5)
    
    ttk.Checkbutton(vwap_frame, text="Enable VWAP", 
                   variable=self.bt_use_vwap,
                   style='Indicator.TLabel',
                   command=lambda: self._toggle_indicator_group('vwap')).grid(row=0, column=0, sticky='w')
    
    ttk.Label(vwap_frame, text="No parameters required for VWAP", 
             style='Parameter.TLabel', foreground='grey').grid(row=1, column=0, sticky='w', pady=5)

def _build_pattern_indicators_group(self, parent):
    """Pattern recognition indicators"""
    used_rows = [int(child.grid_info()['row']) for child in parent.grid_slaves() if child.grid_info()]
    row_start = max(used_rows) + 1 if used_rows else 0
    
    # Group header
    ttk.Label(parent, text="🔄 PATTERN INDICATORS", 
             style='GroupHeader.TLabel').grid(row=row_start, column=0, columnspan=6, 
                                            sticky='w', pady=(10,5))
    
    # Consecutive Green Tick Indicator (NEW - as requested)
    row = row_start + 1
    green_frame = ttk.LabelFrame(parent, text="Consecutive Green Tick Pattern", padding=10)
    green_frame.grid(row=row, column=0, columnspan=6, sticky='ew', padx=5, pady=5)
    green_frame.columnconfigure((1,3), weight=1)
    
    # Add new variable for consecutive green tick indicator
    if not hasattr(self, 'bt_use_consecutive_green'):
        self.bt_use_consecutive_green = tk.BooleanVar(value=True)  # Default enabled
    
    # Consecutive Green Checkbox
    self.green_cb = ttk.Checkbutton(green_frame, text="Enable Consecutive Green Tick Detection", 
                                   variable=self.bt_use_consecutive_green,
                                   style='Indicator.TLabel',
                                   command=lambda: self._toggle_indicator_group('consecutive_green'))
    self.green_cb.grid(row=0, column=0, columnspan=4, sticky='w', pady=(0,5))
    
    # Parameters for consecutive green (existing + noise filter)
    ttk.Label(green_frame, text="Required Green Bars:", style='Parameter.TLabel').grid(row=1, column=0, sticky='e', padx=(0,5))
    self.green_bars_entry = ttk.Entry(green_frame, textvariable=self.bt_consecutive_green_bars, width=6, font=('Arial', 10))
    self.green_bars_entry.grid(row=1, column=1, sticky='w', padx=(0,15))
    
    # Noise Filter Parameters (as requested - specifically for consecutive green tick)
    ttk.Label(green_frame, text="Noise Filter (%):", style='Parameter.TLabel').grid(row=1, column=2, sticky='e', padx=(0,5))
    self.noise_filter_entry = ttk.Entry(green_frame, textvariable=self.bt_noise_filter_percentage, width=8, font=('Arial', 10))
    self.noise_filter_entry.grid(row=1, column=3, sticky='w')
    
    # Second row for additional noise filter parameters
    ttk.Label(green_frame, text="Min Ticks:", style='Parameter.TLabel').grid(row=2, column=0, sticky='e', padx=(0,5))
    self.noise_ticks_entry = ttk.Entry(green_frame, textvariable=self.bt_noise_filter_min_ticks, width=6, font=('Arial', 10))
    self.noise_ticks_entry.grid(row=2, column=1, sticky='w', padx=(0,15))
    
    ttk.Checkbutton(green_frame, text="Enable Noise Filter", 
                   variable=self.bt_noise_filter_enabled,
                   style='Parameter.TLabel').grid(row=2, column=2, columnspan=2, sticky='w')
    
    self.consecutive_green_widgets = [self.green_bars_entry, self.noise_filter_entry, self.noise_ticks_entry]
    
    # HTF Trend
    row += 1
    htf_frame = ttk.LabelFrame(parent, text="Higher Time Frame Trend", padding=10)
    htf_frame.grid(row=row, column=0, columnspan=6, sticky='ew', padx=5, pady=5)
    
    self.htf_cb = ttk.Checkbutton(htf_frame, text="Enable HTF Trend Filter", 
                                 variable=self.bt_use_htf_trend,
                                 style='Indicator.TLabel',
                                 command=lambda: self._toggle_indicator_group('htf'))
    self.htf_cb.grid(row=0, column=0, columnspan=2, sticky='w', pady=(0,5))
    
    ttk.Label(htf_frame, text="HTF Period:", style='Parameter.TLabel').grid(row=1, column=0, sticky='e', padx=(0,5))
    self.htf_period_entry = ttk.Entry(htf_frame, textvariable=self.bt_htf_period, width=8, font=('Arial', 10))
    self.htf_period_entry.grid(row=1, column=1, sticky='w')
    
    self.htf_widgets = [self.htf_period_entry]

def _toggle_indicator_group(self, group_name):
    """Enable/disable indicator group and grey out parameters"""
    indicator_states = {
        'ema': (self.bt_use_ema_crossover.get(), getattr(self, 'ema_widgets', [])),
        'macd': (self.bt_use_macd.get(), getattr(self, 'macd_widgets', [])),
        'rsi': (self.bt_use_rsi_filter.get(), getattr(self, 'rsi_widgets', [])),
        'vwap': (self.bt_use_vwap.get(), []),  # No parameters for VWAP
        'consecutive_green': (self.bt_use_consecutive_green.get(), getattr(self, 'consecutive_green_widgets', [])),
        'htf': (self.bt_use_htf_trend.get(), getattr(self, 'htf_widgets', []))
    }
    
    if group_name in indicator_states:
        is_enabled, widgets = indicator_states[group_name]
        
        for widget in widgets:
            if is_enabled:
                widget.configure(state='normal')
                if hasattr(widget, 'configure') and 'style' in widget.configure():
                    widget.configure(style='TEntry')
            else:
                widget.configure(state='disabled')
                if hasattr(widget, 'configure') and 'style' in widget.configure():
                    widget.configure(style='Disabled.TEntry')

def _create_config_validation_dialog(self, config):
    """Show configuration validation dialog before freezing"""
    dialog = tk.Toplevel(self)
    dialog.title("Configuration Validation")
    dialog.geometry("600x500")
    dialog.transient(self)
    dialog.grab_set()
    
    # Center the dialog
    dialog.geometry("+%d+%d" % (self.winfo_rootx() + 50, self.winfo_rooty() + 50))
    
    # Main frame
    main_frame = ttk.Frame(dialog, padding=20)
    main_frame.pack(fill='both', expand=True)
    
    # Title
    ttk.Label(main_frame, text="Configuration Review", 
             font=('Arial', 14, 'bold')).pack(pady=(0,10))
    
    # Scrollable text area for config display
    text_frame = ttk.Frame(main_frame)
    text_frame.pack(fill='both', expand=True, pady=(0,10))
    
    text_widget = tk.Text(text_frame, wrap='word', font=('Courier', 9))
    scrollbar = ttk.Scrollbar(text_frame, orient='vertical', command=text_widget.yview)
    text_widget.configure(yscrollcommand=scrollbar.set)
    
    text_widget.pack(side='left', fill='both', expand=True)
    scrollbar.pack(side='right', fill='y')
    
    # Format and display config
    config_text = self._format_config_for_display(config)
    text_widget.insert('1.0', config_text)
    text_widget.configure(state='disabled')
    
    # Validation status
    validation_frame = ttk.Frame(main_frame)
    validation_frame.pack(fill='x', pady=(0,10))
    
    try:
        validation = validate_config(config)
        if validation['valid']:
            ttk.Label(validation_frame, text="✓ Configuration is valid", 
                     foreground='green', font=('Arial', 10, 'bold')).pack()
        else:
            ttk.Label(validation_frame, text="✗ Configuration has errors:", 
                     foreground='red', font=('Arial', 10, 'bold')).pack()
            for error in validation['errors']:
                ttk.Label(validation_frame, text=f"  • {error}", 
                         foreground='red', font=('Arial', 9)).pack(anchor='w')
    except Exception as e:
        ttk.Label(validation_frame, text=f"✗ Validation failed: {e}", 
                 foreground='red', font=('Arial', 10, 'bold')).pack()
    
    # Buttons
    button_frame = ttk.Frame(main_frame)
    button_frame.pack(fill='x')
    
    result = {'approved': False}
    
    def approve():
        result['approved'] = True
        dialog.destroy()
    
    def cancel():
        result['approved'] = False
        dialog.destroy()
    
    ttk.Button(button_frame, text="Approve & Run Backtest", 
              command=approve).pack(side='right', padx=(5,0))
    ttk.Button(button_frame, text="Cancel", 
              command=cancel).pack(side='right')
    
    # Wait for dialog to close
    dialog.wait_window()
    return result['approved']

def _format_config_for_display(self, config):
    """Format configuration for readable display"""
    lines = []
    lines.append("BACKTEST CONFIGURATION")
    lines.append("=" * 50)
    lines.append("")
    
    for section, params in config.items():
        if isinstance(params, dict):
            lines.append(f"[{section.upper()}]")
            for key, value in params.items():
                if isinstance(value, list):
                    value_str = f"[{', '.join(str(v) for v in value)}]"
                else:
                    value_str = str(value)
                lines.append(f"  {key}: {value_str}")
            lines.append("")
    
    return "\\n".join(lines)

# Updated build_config_from_gui method with validation dialog
def build_config_from_gui(self):
    """Build complete configuration from current GUI state with validation dialog"""
    config = create_config_from_defaults()
    
    # Update with current GUI values (existing code...)
    
    # Strategy settings - include new consecutive green indicator
    config['strategy']['use_ema_crossover'] = self.bt_use_ema_crossover.get()
    config['strategy']['use_macd'] = self.bt_use_macd.get()
    config['strategy']['use_vwap'] = self.bt_use_vwap.get()
    config['strategy']['use_rsi_filter'] = self.bt_use_rsi_filter.get()
    config['strategy']['use_htf_trend'] = self.bt_use_htf_trend.get()
    config['strategy']['use_bollinger_bands'] = self.bt_use_bollinger_bands.get()
    config['strategy']['use_stochastic'] = self.bt_use_stochastic.get()
    config['strategy']['use_atr'] = self.bt_use_atr.get()
    
    # NEW: Add consecutive green tick indicator
    if hasattr(self, 'bt_use_consecutive_green'):
        config['strategy']['use_consecutive_green'] = self.bt_use_consecutive_green.get()
    
    # Convert string inputs to appropriate types
    config['strategy']['fast_ema'] = int(self.bt_fast_ema.get())
    config['strategy']['slow_ema'] = int(self.bt_slow_ema.get())
    config['strategy']['macd_fast'] = int(self.bt_macd_fast.get())
    config['strategy']['macd_slow'] = int(self.bt_macd_slow.get())
    config['strategy']['macd_signal'] = int(self.bt_macd_signal.get())
    config['strategy']['consecutive_green_bars'] = int(self.bt_consecutive_green_bars.get())
    
    # Add noise filter settings (specific to consecutive green tick as requested)
    config['strategy']['noise_filter_enabled'] = self.bt_noise_filter_enabled.get()
    config['strategy']['noise_filter_percentage'] = float(self.bt_noise_filter_percentage.get()) / 100.0
    config['strategy']['noise_filter_min_ticks'] = float(self.bt_noise_filter_min_ticks.get())
    
    config['strategy']['strategy_version'] = DEFAULT_CONFIG['strategy']['strategy_version']
    
    # ... rest of existing configuration code ...
    
    # SHOW VALIDATION DIALOG BEFORE FREEZING
    approved = self._create_config_validation_dialog(config)
    if not approved:
        return None  # User cancelled
    
    # Final validation and freeze (existing code...)
    try:
        validation = validate_config(config)
    except Exception as e:
        logger.exception("validate_config raised unexpected exception: %s", e)
        messagebox.showerror("Validation Error", f"Unexpected error during validation: {e}")
        return None

    if not validation.get('valid', False):
        errs = validation.get('errors', []) or ["Unknown validation failure"]
        messagebox.showerror("Configuration Validation Failed",
                           "Please fix configuration issues:\\n\\n" + "\\n".join(errs))
        return None

    # Freeze config to make it immutable for the run
    try:
        frozen = freeze_config(config)
    except Exception as e:
        logger.exception("freeze_config failed: %s", e)
        messagebox.showerror("Configuration Error", "Failed to freeze configuration. Aborting run.")
        return None

    if not isinstance(frozen, MappingProxyType):
        logger.error("freeze_config did not return MappingProxyType; aborting run")
        messagebox.showerror("Configuration Error", "Configuration could not be frozen. Aborting run.")
        return None

    return frozen
```

## Key Features Implemented

✅ **Parameters near indicators**: Each indicator group contains its parameters in the same frame  
✅ **Grey out unchecked**: `_toggle_indicator_group()` disables widgets when indicators are unchecked  
✅ **Config validation dialog**: Shows full config review before freezing with approve/cancel options  
✅ **Consecutive green as indicator**: New checkbox with dedicated parameters section  
✅ **Noise filter for consecutive green**: Integrated as parameters specific to the pattern  
✅ **Enhanced fonts**: Different font sizes and weights for hierarchy (12pt headers, 10pt indicators, 9pt parameters)  
✅ **Better layout**: Organized into logical groups with LabelFrames, more columns for parameters  

This implementation maintains your SSOT architecture while providing the enhanced user experience you requested.