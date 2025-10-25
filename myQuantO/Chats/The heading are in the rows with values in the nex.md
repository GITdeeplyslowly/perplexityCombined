<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# The heading are in the rows with values in the next columns, but since the headings are in column B, which is a narrow column, the text overshoots the column. Move the headings to column C and the corresponding values to column D, Other heading may be brought column H from column I and the corresponding values from column L to columns I. This has to be for all results and hence may changes in the forward_test_results.py

To fix the performance summary placement and appearance for **all results** in your Excel export (via `forward_test_results.py`):

### Problem

- Currently, summary headings are in **column B** (narrow; text overflows).
- Values are in **column E** and **column L**.
- You want headings in **column C**, values in **column D**.
- For the right side: headings should move from **column I** to **column H**, and values from **column L** to **column I**.

***

### Solution: Modify Excel Writing Logic

You need to update the code that writes the performance summary table so that:

- For each heading, write it to the correct column (C for left, H for right).
- For each value, write to the correct adjacent column (D for left, I for right).

**Here’s a diff-style pseudocode for what you should change:**

```diff
@@ -1234,12 +1234,41 @@
-    # Originally, maybe:
-    for i, (label, value, side) in enumerate(metrics):
-        ws.cell(row=start_row+i, column=2 if side=="Left" else 9, value=label)   # B or I
-        ws.cell(row=start_row+i, column=5 if side=="Left" else 12, value=value) # E or L
+    # New placement logic:
+    for i, (label, value, side) in enumerate(metrics):
+        if side == "Left":
+            ws.cell(row=start_row+i, column=3, value=label)  # C
+            ws.cell(row=start_row+i, column=4, value=value)  # D
+        else:
+            ws.cell(row=start_row+i, column=8, value=label)  # H
+            ws.cell(row=start_row+i, column=9, value=value)  # I
```

- `column=3` is **C**
- `column=4` is **D**
- `column=8` is **H**
- `column=9` is **I**

> **This change ensures your headings and values are always correctly placed for every results file output.**

### Summary

- **Move headings:** Left-side to C, right-side to H.
- **Move values:** Left-side to D, right-side to I.
- Update all export logic in `forward_test_results.py` that writes these fields.

***

**This fix is structural:**
If you apply it to all relevant export/writing locations (dashboard, summary, etc.), the output in Excel will always have correctly-placed headings/values, solving the text overflow and misaligned data problem for all results.

If you need the exact code location for the loop, I can extract it—just let me know!
<span style="display:none">[^1]</span>

<div align="center">⁂</div>

[^1]: forward_test_results.py

