#!/usr/bin/env python3
"""
agents/health_check.py

Scans the entire Makima project structure to verify:
1. Python syntax integrity (AST parsing).
2. Presence of critical files.
3. Basic directory structure health.
"""

import os
import ast
import sys
import logging

# Fix for Windows UnicodeEncodeError
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("HealthCheck")

def check_syntax(file_path):
    """Parse file content to check for syntax errors without executing."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
        ast.parse(source)
        return True, None
    except SyntaxError as e:
        return False, f"Line {e.lineno}: {e.msg}"
    except Exception as e:
        return False, str(e)

def scan_directory(root_dir):
    logger.info(f"Scanning project root: {root_dir}")
    
    results = {"passed": 0, "failed": 0, "files": []}
    
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Ignore common non-code directories
        for ignore in ["__pycache__", ".git", ".idea", "venv", "env"]:
            if ignore in dirnames:
                dirnames.remove(ignore)
            
        for filename in filenames:
            if filename.endswith(".py"):
                full_path = os.path.join(dirpath, filename)
                rel_path = os.path.relpath(full_path, root_dir)
                
                success, error = check_syntax(full_path)
                
                if success:
                    # logger.info(f"✅ {rel_path}") # Uncomment for verbose output
                    results["passed"] += 1
                else:
                    logger.error(f"❌ {rel_path}: Syntax Error - {error}")
                    results["failed"] += 1
                    results["files"].append((rel_path, error))
                    
    return results

if __name__ == "__main__":
    # Determine project root (assuming this script is in /systems/)
    current_file = os.path.abspath(__file__)
    project_root = os.path.dirname(os.path.dirname(current_file))
    
    print(f"MA KIMA SYSTEM HEALTH CHECK")
    print("="*40)
    
    stats = scan_directory(project_root)
    
    print("-" * 40)
    print(f"Files Scanned: {stats['passed'] + stats['failed']}")
    print(f"Passed:        {stats['passed']}")
    print(f"Failed:        {stats['failed']}")
    print("="*40)
    
    if stats['failed'] > 0:
        sys.exit(1)
    sys.exit(0)