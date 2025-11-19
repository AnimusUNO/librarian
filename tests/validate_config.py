#!/usr/bin/env python3
"""
Configuration validation script for The Librarian
Validates environment configuration and provides helpful feedback

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

import os
import json
import sys
from dotenv import load_dotenv

def validate_config():
    """Validate The Librarian configuration"""
    print("Validating The Librarian Configuration...")
    
    # Load environment variables
    load_dotenv()
    
    errors = []
    warnings = []
    
    # Required configuration
    required_configs = [
        ("LETTA_BASE_URL", "Letta server base URL"),
        ("LETTA_API_KEY", "Letta API key"),
    ]
    
    for config_key, description in required_configs:
        value = os.getenv(config_key)
        if not value:
            errors.append(f"Missing required configuration: {config_key} ({description})")
        elif config_key == "LETTA_BASE_URL" and not value.startswith(("http://", "https://")):
            warnings.append(f"LETTA_BASE_URL should start with http:// or https://")
    
    # Optional but important configuration
    optional_configs = [
        ("LIBRARIAN_WORKER_AGENT", "Worker agent ID"),
        ("LIBRARIAN_PERSONA_AGENT", "Persona agent ID"),
        ("LIBRARIAN_PERSONA_TURBO_AGENT", "Persona turbo agent ID"),
    ]
    
    for config_key, description in optional_configs:
        value = os.getenv(config_key)
        if not value:
            warnings.append(f"Missing optional configuration: {config_key} ({description})")
    
    # Validate JSON configurations
    json_configs = [
        ("LIBRARIAN_CUSTOM_MODELS", "Custom model configurations"),
        ("LIBRARIAN_ADDITIONAL_MODELS", "Additional model configurations"),
    ]
    
    for config_key, description in json_configs:
        value = os.getenv(config_key)
        if value:
            try:
                json.loads(value)
            except json.JSONDecodeError as e:
                errors.append(f"Invalid JSON in {config_key}: {e}")
    
    # Validate numeric configurations
    numeric_configs = [
        ("LIBRARIAN_PORT", "Server port", 1, 65535),
        ("LIBRARIAN_MAX_CONCURRENT", "Max concurrent requests", 1, 1000),
        ("LIBRARIAN_DUPLICATION_THRESHOLD", "Duplication threshold", 1, 100),
        ("LETTA_TIMEOUT", "Letta timeout", 1, 300),
    ]
    
    for config_key, description, min_val, max_val in numeric_configs:
        value = os.getenv(config_key)
        if value:
            try:
                num_value = int(value)
                if not (min_val <= num_value <= max_val):
                    warnings.append(f"{config_key} should be between {min_val} and {max_val}")
            except ValueError:
                errors.append(f"Invalid numeric value for {config_key}: {value}")
    
    # Validate boolean configurations
    boolean_configs = [
        ("LIBRARIAN_DEBUG", "Debug mode"),
        ("LIBRARIAN_ENABLE_IP_FILTERING", "IP filtering"),
        ("LIBRARIAN_RATE_LIMIT_ENABLED", "Rate limiting"),
        ("LIBRARIAN_ENABLE_AUTO_DUPLICATION", "Auto duplication"),
    ]
    
    for config_key, description in boolean_configs:
        value = os.getenv(config_key)
        if value and value.lower() not in ("true", "false"):
            warnings.append(f"{config_key} should be 'true' or 'false'")
    
    # Print results
    if errors:
        print("\nConfiguration Errors:")
        for error in errors:
            print(f"  • {error}")
    
    if warnings:
        print("\nConfiguration Warnings:")
        for warning in warnings:
            print(f"  • {warning}")
    
    if not errors and not warnings:
        print("\nConfiguration is valid!")
    
    # Print current configuration summary
    print("\nCurrent Configuration Summary:")
    print(f"  Server: {os.getenv('LIBRARIAN_HOST', '127.0.0.1')}:{os.getenv('LIBRARIAN_PORT', '8000')}")
    print(f"  Debug Mode: {os.getenv('LIBRARIAN_DEBUG', 'false')}")
    print(f"  Letta URL: {os.getenv('LETTA_BASE_URL', 'Not set')}")
    print(f"  Letta API Key: {'Set' if os.getenv('LETTA_API_KEY') else 'Not set'}")
    print(f"  Worker Agent: {os.getenv('LIBRARIAN_WORKER_AGENT', 'Not set')}")
    print(f"  Persona Agent: {os.getenv('LIBRARIAN_PERSONA_AGENT', 'Not set')}")
    print(f"  Max Concurrent: {os.getenv('LIBRARIAN_MAX_CONCURRENT', '10')}")
    print(f"  Auto Duplication: {os.getenv('LIBRARIAN_ENABLE_AUTO_DUPLICATION', 'true')}")
    
    return len(errors) == 0

def main():
    """Main function"""
    print("The Librarian Configuration Validator")
    print("=" * 50)
    
    valid = validate_config()
    
    if valid:
        print("\nConfiguration validation passed!")
        print("You can now start The Librarian with: python main.py")
        sys.exit(0)
    else:
        print("\nConfiguration validation failed!")
        print("Please fix the errors above before starting The Librarian.")
        sys.exit(1)

if __name__ == "__main__":
    main()
