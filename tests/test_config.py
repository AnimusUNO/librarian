#!/usr/bin/env python3
"""
Test suite for Config class

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

import pytest
import os
from src.librarian.config import Config


class TestConfig:
    """Test Config class"""
    
    def test_default_values(self):
        """Test that default values are used when env vars not set"""
        # Test with explicit defaults (bypassing .env file)
        config = Config(
            host="127.0.0.1",
            port=8000,
            debug=False,
            letta_base_url="http://localhost:8283",
            letta_timeout=30
        )
        assert config.host == "127.0.0.1"
        assert config.port == 8000
        assert config.debug is False
        assert config.letta_base_url == "http://localhost:8283"
        assert config.letta_timeout == 30
    
    def test_env_var_loading(self):
        """Test loading from environment variables"""
        os.environ["LIBRARIAN_HOST"] = "0.0.0.0"
        os.environ["LIBRARIAN_PORT"] = "9000"
        os.environ["LIBRARIAN_DEBUG"] = "true"
        
        try:
            config = Config.load()
            assert config.host == "0.0.0.0"
            assert config.port == 9000
            assert config.debug is True
        finally:
            # Clean up
            os.environ.pop("LIBRARIAN_HOST", None)
            os.environ.pop("LIBRARIAN_PORT", None)
            os.environ.pop("LIBRARIAN_DEBUG", None)
    
    def test_ip_list_parsing(self):
        """Test parsing of comma-separated IP lists"""
        os.environ["LIBRARIAN_ALLOWED_IPS"] = "192.168.1.1, 10.0.0.1, 172.16.0.1"
        os.environ["LIBRARIAN_BLOCKED_IPS"] = "192.168.1.2"
        
        try:
            config = Config.load()
            assert "192.168.1.1" in config.allowed_ips
            assert "10.0.0.1" in config.allowed_ips
            assert "172.16.0.1" in config.allowed_ips
            assert "192.168.1.2" in config.blocked_ips
            assert len(config.allowed_ips) == 3
        finally:
            os.environ.pop("LIBRARIAN_ALLOWED_IPS", None)
            os.environ.pop("LIBRARIAN_BLOCKED_IPS", None)
    
    def test_boolean_parsing(self):
        """Test boolean parsing from strings"""
        test_cases = [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("1", True),
            ("yes", True),
            ("false", False),
            ("False", False),
            ("0", False),
            ("no", False),
        ]
        
        for value, expected in test_cases:
            os.environ["LIBRARIAN_DEBUG"] = value
            try:
                config = Config.load()
                assert config.debug == expected, f"Failed for value: {value}"
            finally:
                os.environ.pop("LIBRARIAN_DEBUG", None)
    
    def test_int_parsing(self):
        """Test integer parsing"""
        os.environ["LIBRARIAN_PORT"] = "9000"
        os.environ["LIBRARIAN_RATE_LIMIT_REQUESTS"] = "200"
        
        try:
            config = Config.load()
            assert config.port == 9000
            assert config.rate_limit_requests == 200
        finally:
            os.environ.pop("LIBRARIAN_PORT", None)
            os.environ.pop("LIBRARIAN_RATE_LIMIT_REQUESTS", None)
    
    def test_port_validation(self):
        """Test port validation"""
        config = Config(port=8000)
        assert config.port == 8000
        
        # Invalid port should raise error
        with pytest.raises(ValueError):
            Config(port=70000)
        
        with pytest.raises(ValueError):
            Config(port=0)
    
    def test_log_level_validation(self):
        """Test log level validation"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        for level in valid_levels:
            config = Config(log_level=level)
            assert config.log_level == level
        
        # Invalid level should raise error
        with pytest.raises(ValueError):
            Config(log_level="INVALID")
    
    def test_timeout_validation(self):
        """Test timeout validation"""
        config = Config(letta_timeout=30)
        assert config.letta_timeout == 30
        
        # Invalid timeout should raise error
        with pytest.raises(ValueError):
            Config(letta_timeout=0)
    
    def test_config_validation(self):
        """Test config validation method"""
        config = Config.load()
        # Should not raise
        config.validate_config()
        
        # Test warning for missing API key when required
        config.api_key_required = True
        config.api_key = None
        # Should log warning but not raise
        config.validate_config()
    
    def test_load_manager_config(self):
        """Test load manager configuration values"""
        config = Config.load()
        assert config.max_concurrent > 0
        assert config.duplication_threshold > 0
        assert config.queue_timeout > 0
        assert config.cleanup_interval > 0
        assert isinstance(config.enable_auto_duplication, bool)
        assert config.max_clones_per_agent > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

