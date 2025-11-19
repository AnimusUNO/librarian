#!/usr/bin/env python3
"""
Dependency management script for The Librarian

Copyright (C) 2025 AnimusUNO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import subprocess
import sys
import os

def run_command(cmd):
    """Run a command and return success status"""
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {cmd}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {cmd}")
        print(f"Error: {e.stderr}")
        return False

def install_production():
    """Install production dependencies"""
    print("Installing production dependencies...")
    return run_command("pip install -r requirements.txt")

def install_test():
    """Install test dependencies"""
    print("Installing test dependencies...")
    return run_command("pip install -r requirements-test.txt")

def install_all():
    """Install all dependencies"""
    print("Installing all dependencies...")
    success1 = install_production()
    success2 = install_test()
    return success1 and success2

def run_tests():
    """Run the test suite"""
    print("Running tests...")
    return run_command("pytest tests/ -v")

def format_code():
    """Format code with black and isort"""
    print("Formatting code...")
    success1 = run_command("black src/ main.py")
    success2 = run_command("isort src/ main.py")
    return success1 and success2

def lint_code():
    """Lint code with flake8 and mypy"""
    print("Linting code...")
    success1 = run_command("flake8 src/ main.py")
    success2 = run_command("mypy src/ main.py")
    return success1 and success2

def main():
    """Main CLI interface"""
    if len(sys.argv) < 2:
        print("Usage: python manage_deps.py <command>")
        print("Commands:")
        print("  install-prod    - Install production dependencies")
        print("  install-test    - Install test dependencies")
        print("  install-all     - Install all dependencies")
        print("  test            - Run tests")
        print("  format          - Format code")
        print("  lint            - Lint code")
        print("  all             - Install all, format, lint, and test")
        return

    command = sys.argv[1].lower()
    
    if command == "install-prod":
        install_production()
    elif command == "install-test":
        install_test()
    elif command == "install-all":
        install_all()
    elif command == "test":
        run_tests()
    elif command == "format":
        format_code()
    elif command == "lint":
        lint_code()
    elif command == "all":
        print("Running full development setup...")
        if install_all():
            format_code()
            lint_code()
            run_tests()
    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main()
