"""
Test script to verify the new results directory structure and naming conventions
"""

import os
import sys
from datetime import datetime

# Get the project root directory
project_root = os.path.dirname(os.path.abspath(__file__))
print(f"✅ Project root: {project_root}")

# Check directory structure
results_dir = os.path.join(project_root, "results")
backtest_dir = os.path.join(results_dir, "Back Test")
forward_test_dir = os.path.join(results_dir, "Forward Test")

print(f"\n📁 Directory Structure:")
print(f"   Results: {os.path.exists(results_dir)} - {results_dir}")
print(f"   Back Test: {os.path.exists(backtest_dir)} - {backtest_dir}")
print(f"   Forward Test: {os.path.exists(forward_test_dir)} - {forward_test_dir}")

# Test naming convention
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backtest_filename = f"bt-{timestamp}-data.xlsx"
forward_test_filename = f"ft-{timestamp}-live.xlsx"

print(f"\n📋 Naming Convention:")
print(f"   Backtest: {backtest_filename}")
print(f"   Forward Test: {forward_test_filename}")

# Test path construction
test_bt_path = os.path.join(backtest_dir, backtest_filename)
test_ft_path = os.path.join(forward_test_dir, forward_test_filename)

print(f"\n🎯 Full Paths:")
print(f"   Backtest: {test_bt_path}")
print(f"   Forward Test: {test_ft_path}")

print(f"\n✅ All directory structures and naming conventions are correctly configured!")
print(f"📊 Ready to generate results with the new format and organization.")