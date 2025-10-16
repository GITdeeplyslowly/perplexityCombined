<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# Combined VS Code Copilot Diffs

Implement raw tick logging per live session as a CSV in a dynamic project path, with minimal performance impact.

***

## 1. Define Dynamic Tick Log Directory

**File:** `websocket_stream.py` (or equivalent live-stream module)

```diff
@@
-import os
+import os
 from datetime import datetime
+from pathlib import Path

+# Derive project root dynamically and set tick log directory
+PROJECT_ROOT = Path(__file__).resolve().parent.parent
+TICK_LOG_DIR = PROJECT_ROOT / "LiveTickPrice"
+TICK_LOG_DIR.mkdir(parents=True, exist_ok=True)
+
```


***

## 2. Initialize Session-Specific CSV Logger

**File:** `websocket_stream.py`

```diff
@@ class LiveStreamer:
-    def __init__(self, config):
+    def __init__(self, config):
         # … existing initialization …
-        # Prepare tick log file
-        base = r"C:\Users\user\projects\Perplexity CombinedTest\LiveTickPrice"
-        os.makedirs(base, exist_ok=True)
-        eh = config['session']['end_hour']
-        em = config['session']['end_min']
-        date = now_ist().strftime("%Y%m%d")
-        fname = f"livePrice_{date}_{eh:02d}{em:02d}.csv"
-        path = os.path.join(base, fname)
-        self.tick_file = open(path, mode="w", newline="", encoding="utf-8")
-        self.tick_writer = csv.writer(self.tick_file)
-        self.tick_writer.writerow(["timestamp","price","volume"])
+        # Initialize tick CSV log for this session
+        from csv import writer
+        date = datetime.now().strftime("%Y%m%d")
+        eh, em = config['session']['end_hour'], config['session']['end_min']
+        fname = f"livePrice_{date}_{eh:02d}{em:02d}.csv"
+        self.tick_file = (TICK_LOG_DIR / fname).open("w", newline="", encoding="utf-8")
+        self.tick_writer = writer(self.tick_file)
+        self.tick_writer.writerow(["timestamp", "price", "volume"])
```


***

## 3. Log Each Tick Efficiently

```diff
@@ class LiveStreamer:
     def on_tick(self, tick):
         # … existing processing …
-        self.logger.debug(f"Tick: {tick}")
+        # Append raw tick to CSV (buffered)
+        self.tick_writer.writerow([tick.timestamp, tick.price, tick.volume])
```


***

## 4. Close File on Session End

```diff
@@ class LiveStreamer:
     def end_session(self):
         # … existing cleanup …
-        self.logger.info("Session ended")
+        self.tick_file.close()
+        self.logger.info("Tick log saved and session ended")
```


***

### Performance and Path Notes

1. **Latency Impact:** Negligible, as CSV writes are buffered and non-blocking if executed in a background thread or via buffered I/O.
2. **Dynamic Path:** Uses `Path(__file__).parent.parent` to derive project root, so renaming the project folder requires no code changes.
3. **Folder Exists:** `TICK_LOG_DIR.mkdir(exist_ok=True)` is idempotent and safe even if `LiveTickPrice` already exists.
