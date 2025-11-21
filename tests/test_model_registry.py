#!/usr/bin/env python3
"""
Test suite for ModelRegistry

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
import json
from src.librarian.model_registry import ModelRegistry


class TestModelRegistry:
    """Test ModelRegistry class"""
    
    def setup_method(self):
        """Clear environment variables before each test"""
        self.original_env = os.environ.copy()
        for key in list(os.environ.keys()):
            if key.startswith("LIBRARIAN_CUSTOM_MODELS") or key.startswith("LIBRARIAN_ADDITIONAL_MODELS"):
                os.environ.pop(key)
    
    def teardown_method(self):
        """Restore environment variables after each test"""
        os.environ.clear()
        os.environ.update(self.original_env)
    
    def test_init_default(self):
        """Test ModelRegistry initialization with default agent"""
        registry = ModelRegistry()
        assert registry.librarian_agent == "librarian"
        assert len(registry.models) > 0
    
    def test_init_custom_agent(self):
        """Test ModelRegistry initialization with custom agent"""
        registry = ModelRegistry(librarian_agent="custom-agent")
        assert registry.librarian_agent == "custom-agent"
    
    def test_get_agent_config_existing(self):
        """Test getting agent config for existing model"""
        registry = ModelRegistry()
        config = registry.get_agent_config("gpt-4")
        assert config is not None
        assert "agent_id" in config
        assert "mode" in config
    
    def test_get_agent_config_nonexistent(self):
        """Test getting agent config for nonexistent model"""
        registry = ModelRegistry()
        config = registry.get_agent_config("nonexistent-model")
        assert config is None
    
    def test_list_models(self):
        """Test listing all models"""
        registry = ModelRegistry()
        models = registry.list_models()
        assert isinstance(models, dict)
        assert len(models) > 0
        assert "gpt-4" in models
    
    def test_is_valid_model(self):
        """Test checking if model is valid"""
        registry = ModelRegistry()
        assert registry.is_valid_model("gpt-4") is True
        assert registry.is_valid_model("nonexistent") is False
    
    def test_get_agent_id(self):
        """Test getting agent ID for model"""
        registry = ModelRegistry()
        agent_id = registry.get_agent_id("gpt-4")
        assert agent_id == "librarian"
    
    def test_get_agent_id_nonexistent(self):
        """Test getting agent ID for nonexistent model"""
        registry = ModelRegistry()
        agent_id = registry.get_agent_id("nonexistent")
        assert agent_id is None
    
    def test_get_mode(self):
        """Test getting mode for model"""
        registry = ModelRegistry()
        mode = registry.get_mode("gpt-4")
        assert mode == "auto"
    
    def test_get_mode_nonexistent(self):
        """Test getting mode for nonexistent model"""
        registry = ModelRegistry()
        mode = registry.get_mode("nonexistent")
        assert mode is None
    
    def test_add_model(self):
        """Test adding a new model"""
        registry = ModelRegistry()
        registry.add_model("test-model", "test-agent", "worker", "Test model")
        assert registry.is_valid_model("test-model") is True
        config = registry.get_agent_config("test-model")
        assert config["agent_id"] == "test-agent"
        assert config["mode"] == "worker"
    
    def test_remove_model(self):
        """Test removing a model"""
        registry = ModelRegistry()
        # Add a model first
        registry.add_model("test-model", "test-agent", "worker")
        assert registry.is_valid_model("test-model") is True
        
        # Remove it
        result = registry.remove_model("test-model")
        assert result is True
        assert registry.is_valid_model("test-model") is False
    
    def test_remove_model_nonexistent(self):
        """Test removing a nonexistent model"""
        registry = ModelRegistry()
        result = registry.remove_model("nonexistent")
        assert result is False
    
    def test_load_custom_models(self):
        """Test loading custom models from environment"""
        custom_models = {
            "custom-model": {
                "agent_id": "custom-agent",
                "mode": "worker",
                "description": "Custom model"
            }
        }
        os.environ["LIBRARIAN_CUSTOM_MODELS"] = json.dumps(custom_models)
        
        registry = ModelRegistry()
        assert registry.is_valid_model("custom-model") is True
        config = registry.get_agent_config("custom-model")
        assert config["agent_id"] == "custom-agent"
    
    def test_load_custom_models_invalid_json(self):
        """Test handling invalid JSON in custom models"""
        os.environ["LIBRARIAN_CUSTOM_MODELS"] = "invalid json"
        
        # Should not raise, just log error
        registry = ModelRegistry()
        assert len(registry.models) > 0  # Should still have defaults
    
    def test_load_additional_models(self):
        """Test loading additional models from environment"""
        additional_models = {
            "additional-model": {
                "agent_id": "additional-agent",
                "mode": "persona",
                "description": "Additional model"
            }
        }
        os.environ["LIBRARIAN_ADDITIONAL_MODELS"] = json.dumps(additional_models)
        
        registry = ModelRegistry()
        assert registry.is_valid_model("additional-model") is True
    
    def test_load_additional_models_invalid_json(self):
        """Test handling invalid JSON in additional models"""
        os.environ["LIBRARIAN_ADDITIONAL_MODELS"] = "invalid json"
        
        # Should not raise, just log error
        registry = ModelRegistry()
        assert len(registry.models) > 0  # Should still have defaults


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
