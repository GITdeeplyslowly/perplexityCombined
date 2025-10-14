#!/usr/bin/env python3
"""
Configuration Fallback Audit & Fix Script
=========================================

This script identifies and helps fix all .get() calls with fallbacks 
that violate the "NO FALLBACKS IN TRADING SYSTEMS" principle.

Usage:
    python fix_config_fallbacks.py --scan    # Find all violations
    python fix_config_fallbacks.py --fix     # Generate fixes
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple, Dict

class ConfigFallbackAuditor:
    """Audits and fixes configuration fallback violations."""
    
    def __init__(self, workspace_root: str):
        self.workspace_root = Path(workspace_root)
        self.violations = []
        
    def scan_for_violations(self) -> List[Dict[str, any]]:
        """Scan all Python files for .get() calls with fallbacks."""
        
        # Patterns that violate NO FALLBACKS principle
        violation_patterns = [
            r'\.get\([^,)]+,\s*[^)]+\)',  # .get(key, default)
            r'\.get\([^,)]+,\s*None\)',   # .get(key, None) 
            r'\.get\([^,)]+,\s*\{\}\)',   # .get(key, {})
            r'\.get\([^,)]+,\s*\[\]\)',   # .get(key, [])
            r'\.get\([^,)]+,\s*"[^"]*"\)', # .get(key, "default")
            r'\.get\([^,)]+,\s*\'[^\']*\'\)', # .get(key, 'default')
            r'\.get\([^,)]+,\s*\d+\)',    # .get(key, 123)
        ]
        
        # Files to scan (exclude test files for now)
        python_files = []
        for root, dirs, files in os.walk(self.workspace_root):
            # Skip __pycache__ and test directories
            dirs[:] = [d for d in dirs if d not in ['__pycache__', 'tests', '.git']]
            
            for file in files:
                if file.endswith('.py'):
                    python_files.append(Path(root) / file)
        
        print(f"🔍 Scanning {len(python_files)} Python files for configuration fallbacks...")
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    for line_num, line in enumerate(lines, 1):
                        for pattern in violation_patterns:
                            matches = re.finditer(pattern, line)
                            for match in matches:
                                violation = {
                                    'file': str(file_path.relative_to(self.workspace_root)),
                                    'line_num': line_num,
                                    'line_content': line.strip(),
                                    'match': match.group(),
                                    'severity': self._assess_severity(file_path, line)
                                }
                                self.violations.append(violation)
                                
            except Exception as e:
                print(f"⚠️  Error reading {file_path}: {e}")
                
        return self.violations
    
    def _assess_severity(self, file_path: Path, line: str) -> str:
        """Assess the severity of a configuration fallback violation."""
        
        # Critical: Trading components
        if any(component in str(file_path) for component in [
            'broker_adapter', 'trader', 'live', 'researchStrategy', 'liveStrategy'
        ]):
            return 'CRITICAL'
            
        # High: Core components  
        if any(component in str(file_path) for component in [
            'position_manager', 'indicators', 'backtest_runner'
        ]):
            return 'HIGH'
            
        # Medium: GUI and utils
        if any(component in str(file_path) for component in [
            'gui', 'utils', 'config'
        ]):
            return 'MEDIUM'
            
        return 'LOW'
    
    def generate_report(self) -> str:
        """Generate a detailed violation report."""
        
        if not self.violations:
            return "✅ No configuration fallback violations found!"
        
        report = []
        report.append("🚨 CONFIGURATION FALLBACK VIOLATIONS REPORT")
        report.append("=" * 50)
        report.append("")
        
        # Summary by severity
        severity_counts = {}
        for violation in self.violations:
            severity = violation['severity']
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        report.append("📊 SUMMARY:")
        for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
            count = severity_counts.get(severity, 0)
            if count > 0:
                report.append(f"   {severity}: {count} violations")
        report.append(f"   TOTAL: {len(self.violations)} violations")
        report.append("")
        
        # Group by file
        violations_by_file = {}
        for violation in self.violations:
            file = violation['file']
            if file not in violations_by_file:
                violations_by_file[file] = []
            violations_by_file[file].append(violation)
        
        # Detail report
        report.append("🔍 DETAILED VIOLATIONS:")
        report.append("")
        
        for file, file_violations in sorted(violations_by_file.items()):
            # Sort by severity priority
            severity_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
            file_violations.sort(key=lambda v: severity_order.get(v['severity'], 4))
            
            report.append(f"📁 {file}")
            for violation in file_violations:
                severity_emoji = {
                    'CRITICAL': '🔴',
                    'HIGH': '🟠', 
                    'MEDIUM': '🟡',
                    'LOW': '🔵'
                }.get(violation['severity'], '⚪')
                
                report.append(f"   Line {violation['line_num']:3d}: {severity_emoji} {violation['severity']}")
                report.append(f"              {violation['line_content']}")
                report.append(f"              Match: {violation['match']}")
                report.append("")
        
        return "\n".join(report)
    
    def generate_fixes(self) -> str:
        """Generate suggested fixes for violations."""
        
        fixes = []
        fixes.append("🔧 SUGGESTED FIXES FOR CONFIGURATION FALLBACKS")
        fixes.append("=" * 50)
        fixes.append("")
        
        # Critical violations first
        critical_violations = [v for v in self.violations if v['severity'] == 'CRITICAL']
        
        if critical_violations:
            fixes.append("🚨 CRITICAL FIXES (Immediate Action Required):")
            fixes.append("")
            
            for violation in critical_violations:
                fixes.append(f"File: {violation['file']} (Line {violation['line_num']})")
                fixes.append(f"Current: {violation['line_content']}")
                
                # Generate suggested fix
                suggested_fix = self._generate_fix_suggestion(violation)
                fixes.append(f"Fix:     {suggested_fix}")
                fixes.append("")
        
        # General fix patterns
        fixes.append("🛠️  GENERAL FIX PATTERNS:")
        fixes.append("")
        fixes.append("1. Replace .get() with direct access:")
        fixes.append("   ❌ value = config.get('key', 'default')")
        fixes.append("   ✅ value = config['key']  # Will raise KeyError if missing")
        fixes.append("")
        fixes.append("2. Add missing parameters to defaults.py:")
        fixes.append("   ✅ Ensure ALL required parameters exist in SSOT")
        fixes.append("")
        fixes.append("3. Use ConfigAccessor for instrument parameters:")
        fixes.append("   ❌ lot_size = instrument.get('lot_size', 1)")
        fixes.append("   ✅ lot_size = self.config_accessor.get_current_instrument_param('lot_size')")
        fixes.append("")
        fixes.append("4. Validate configuration before use:")
        fixes.append("   ✅ Add comprehensive validation in defaults.py")
        fixes.append("   ✅ Use validate_config() before freezing")
        fixes.append("")
        
        return "\n".join(fixes)
    
    def _generate_fix_suggestion(self, violation: Dict[str, any]) -> str:
        """Generate a specific fix suggestion for a violation."""
        
        line = violation['line_content']
        match = violation['match']
        
        # Extract the key from .get(key, default)
        get_match = re.search(r'\.get\(["\']?([^,"\']+)["\']?\s*,', match)
        if get_match:
            key = get_match.group(1)
            
            # Generate contextual fix based on file
            if 'broker_adapter' in violation['file']:
                return f"self.{key} = self.instrument['{key}']"
            elif 'Strategy' in violation['file']:
                return f"{key} = self.config_accessor.get_current_instrument_param('{key}')"
            else:
                return line.replace(match, match.split(',')[0] + ']').replace('.get(', '[')
        
        return "# TODO: Replace with direct access pattern"

def main():
    """Main execution function."""
    
    if len(sys.argv) < 2:
        print("Usage: python fix_config_fallbacks.py --scan|--fix")
        return
    
    workspace_root = r"c:\Users\user\projects\Perplexity Combined\myQuant"
    auditor = ConfigFallbackAuditor(workspace_root)
    
    if sys.argv[1] == '--scan':
        print("🔍 Scanning for configuration fallback violations...")
        violations = auditor.scan_for_violations()
        report = auditor.generate_report()
        print(report)
        
        # Save report to file
        with open('config_fallback_violations.txt', 'w') as f:
            f.write(report)
        print(f"\n📄 Report saved to: config_fallback_violations.txt")
        
    elif sys.argv[1] == '--fix':
        print("🔧 Generating fix suggestions...")
        violations = auditor.scan_for_violations()
        fixes = auditor.generate_fixes()
        print(fixes)
        
        # Save fixes to file
        with open('config_fallback_fixes.txt', 'w') as f:
            f.write(fixes)
        print(f"\n📄 Fixes saved to: config_fallback_fixes.txt")
        
    else:
        print("Invalid option. Use --scan or --fix")

if __name__ == "__main__":
    main()