<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# Final Implementation Recommendations for Control Base Stop Loss

**Key Recommendation:** Implement the configurable post–base-stop-loss green–tick increase with reset on any profitable exit, single-step increase only, GUI spin–box controls, and clear logging of threshold changes.

***

## 1. Configuration (defaults.py)

```python
"strategy": {
    "entry_green_ticks": 4,                # Normal consecutive green ticks for entry
    "control_base_sl_enabled": True,       # Enable dynamic entry control after base SL
    "control_base_sl_green_ticks": 7,      # Required green ticks after base SL
}
```

- **Spin–box defaults** for GUI:
    - `entry_green_ticks`: min=1, max=20
    - `control_base_sl_green_ticks`: min=1, max=50

***

## 2. Strategy Logic (liveStrategy.py)

```diff
 class ModularIntradayStrategy:
     def __init__(self, config: MappingProxyType, indicators_module):
         # Existing initialization...
+        self.control_base_sl_enabled = self.config_accessor.get_strategy_param('control_base_sl_enabled')
+        self.normal_green_ticks = self.config_accessor.get_strategy_param('entry_green_ticks')
+        self.base_sl_green_ticks = self.config_accessor.get_strategy_param('control_base_sl_green_ticks')
+        self.last_exit_was_base_sl = False
+        self.current_green_tick_threshold = self.normal_green_ticks

     def on_tick(self, tick: Dict) -> Optional[Dict]:
+        # Update threshold dynamically
+        self.current_green_tick_threshold = (
+            self.base_sl_green_ticks if (self.control_base_sl_enabled and self.last_exit_was_base_sl)
+            else self.normal_green_ticks
+        )
         # Existing tick processing and entry evaluation using self.current_green_tick_threshold

     def _evaluate_entry_conditions(self, tick: Dict) -> Optional[Dict]:
         # Existing checks...
         if self.consecutive_green_ticks >= self.current_green_tick_threshold:
             signal = self._generate_entry_signal(tick)
+            if signal and self.control_base_sl_enabled:
+                self.last_exit_was_base_sl = False
+                logger.info(
+                    f"Entry taken; threshold reset to {self.normal_green_ticks} green ticks."
+                )
             return signal
         return None

     def on_position_exit(self, exit_info: Dict):
         exit_reason = exit_info.get('exit_reason', '').lower()
+        if not self.control_base_sl_enabled:
+            return

         if 'base_sl' in exit_reason:
             self.last_exit_was_base_sl = True
             logger.info(
                 f"Base SL exit detected—next entry requires {self.base_sl_green_ticks} green ticks."
             )
-        else:
+        # Reset threshold on any profitable exit (TP or trailing stop)
+        elif exit_reason in ('target_profit', 'trailing_stop'):
             self.last_exit_was_base_sl = False
             logger.info(
                 f"Profitable exit detected—threshold reset to {self.normal_green_ticks} green ticks."
             )
```

- **Reset Conditions:**
    - **On profitable exits** (`target_profit` or `trailing_stop`), threshold resets immediately.
    - **Single-step increase:** Multiple consecutive base SL exits will maintain the same elevated threshold (no further increments).

***

## 3. Position Manager Callback (core/position_manager.py)

```diff
 class PositionManager:
     def __init__(self, config: MappingProxyType, strategy_callback=None):
         # Existing initialization...
         self.strategy_callback = strategy_callback

     def check_exit_conditions(self, current_price: float, tick: Dict) -> Optional[Dict]:
         # Existing logic...
         if exit_info:
             self._execute_exit(exit_info)
+            if self.strategy_callback:
+                self.strategy_callback(exit_info)
         return exit_info
```

- **Standardized `exit_reason`** values: `'base_sl'`, `'target_profit'`, `'trailing_stop'`, etc.

***

## 4. GUI Integration (gui/noCamel1.py)

```diff
 def build_spinbox_controls(self):
     # Existing spin boxes...
+    self.add_spinbox(
+        label="Entry Green Ticks:",
+        config_path=('strategy', 'entry_green_ticks'),
+        min=1, max=20
+    )
+    self.add_spinbox(
+        label="Green Ticks After Base SL:",
+        config_path=('strategy', 'control_base_sl_green_ticks'),
+        min=1, max=50
+    )
+    self.add_checkbox(
+        label="Enable Control Base SL",
+        config_path=('strategy', 'control_base_sl_enabled')
+    )
```

- **User Experience:**
    - Spin boxes for normal and post–SL thresholds.
    - Checkbox to toggle the feature.

***

## 5. Logging

- **Always log**:
    - Detection of base SL exit and new threshold.
    - Reset after profitable exit.
    - Entry and threshold reset on order placement.

***

## 6. Next Steps

- **Implement code diffs** above in respective modules.
- **Forward testing**: Evaluate different `control_base_sl_green_ticks` values.
- **Research prototype**: Consider volatility-based dynamic thresholds in `researchStrategy.py` for future iteration.

