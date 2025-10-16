#!/usr/bin/env python3
"""
Test runner for The Librarian

Runs all tests and provides comprehensive test reporting.
"""

import subprocess
import sys
import os
from pathlib import Path

def run_tests():
    """Run all tests"""
    print("🧪 Running The Librarian Test Suite")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path("main.py").exists():
        print("❌ Error: main.py not found. Please run from the project root.")
        return 1
    
    # Run configuration validation
    print("\n🔍 Running configuration validation...")
    try:
        result = subprocess.run([sys.executable, "tests/validate_config.py"], 
                              capture_output=True, text=True, check=True)
        print("✅ Configuration validation passed")
        if result.stdout:
            print(result.stdout)
    except subprocess.CalledProcessError as e:
        print("❌ Configuration validation failed:")
        print(e.stdout)
        print(e.stderr)
        return 1
    
    # Run integration tests
    print("\n🔍 Running integration tests...")
    try:
        result = subprocess.run([sys.executable, "tests/test_librarian_integration.py"], 
                              capture_output=True, text=True, check=True)
        print("✅ Integration tests passed")
        if result.stdout:
            print(result.stdout)
    except subprocess.CalledProcessError as e:
        print("❌ Integration tests failed:")
        print(e.stdout)
        print(e.stderr)
        return 1
    
    print("\n🎉 All tests passed!")
    return 0

def main():
    """Main function"""
    return run_tests()

if __name__ == "__main__":
    sys.exit(main())
