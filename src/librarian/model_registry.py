"""
Model Registry for The Librarian

Maps OpenAI model names to Letta agent configurations.
Fully configurable via environment variables.
"""

from typing import Dict, Optional
import os
import json
import logging

logger = logging.getLogger(__name__)


class ModelRegistry:
    """Maps OpenAI model names to Letta agent configurations"""
    
    def __init__(self):
        self.models = self._load_model_config()
    
    def _load_model_config(self) -> Dict[str, Dict[str, str]]:
        """Load model configuration from environment variables"""
        # Default model mappings - all map to the same agent
        # The agent decides which model to use internally via model selector
        librarian_agent_id = os.getenv("LIBRARIAN_AGENT", "librarian")
        default_models = {
            "gpt-4.1": {
                "agent_id": librarian_agent_id,
                "mode": "auto",  # Agent decides Worker/Persona mode internally
                "description": "The Librarian"
            },
            "gpt-3.5-turbo": {
                "agent_id": librarian_agent_id,
                "mode": "auto",  # Agent decides Worker/Persona mode internally
                "description": "The Librarian"
            },
            "gpt-4": {
                "agent_id": librarian_agent_id,
                "mode": "auto",  # Agent decides Worker/Persona mode internally
                "description": "The Librarian"
            },
            "gpt-4-turbo": {
                "agent_id": librarian_agent_id,
                "mode": "auto",  # Agent decides Worker/Persona mode internally
                "description": "The Librarian"
            }
        }
        
        # Check for custom model configuration
        custom_models_json = os.getenv("LIBRARIAN_CUSTOM_MODELS")
        if custom_models_json:
            try:
                custom_models = json.loads(custom_models_json)
                default_models.update(custom_models)
                logger.info(f"Loaded {len(custom_models)} custom model configurations")
            except json.JSONDecodeError as e:
                logger.error(f"Invalid LIBRARIAN_CUSTOM_MODELS JSON: {e}")
        
        # Check for additional models from environment
        additional_models = os.getenv("LIBRARIAN_ADDITIONAL_MODELS")
        if additional_models:
            try:
                additional = json.loads(additional_models)
                default_models.update(additional)
                logger.info(f"Loaded {len(additional)} additional model configurations")
            except json.JSONDecodeError as e:
                logger.error(f"Invalid LIBRARIAN_ADDITIONAL_MODELS JSON: {e}")
        
        logger.info(f"Loaded {len(default_models)} total model configurations")
        return default_models
    
    def get_agent_config(self, model_name: str) -> Optional[Dict[str, str]]:
        """Get Letta agent configuration for OpenAI model"""
        return self.models.get(model_name)
    
    def list_models(self) -> Dict[str, Dict[str, str]]:
        """List all available models"""
        return self.models.copy()
    
    def is_valid_model(self, model_name: str) -> bool:
        """Check if model name is valid"""
        return model_name in self.models
    
    def get_agent_id(self, model_name: str) -> Optional[str]:
        """Get agent ID for model"""
        config = self.get_agent_config(model_name)
        return config.get("agent_id") if config else None
    
    def get_mode(self, model_name: str) -> Optional[str]:
        """Get mode for model"""
        config = self.get_agent_config(model_name)
        return config.get("mode") if config else None
    
    def add_model(self, model_name: str, agent_id: str, mode: str, description: str = "") -> None:
        """Add a new model configuration"""
        self.models[model_name] = {
            "agent_id": agent_id,
            "mode": mode,
            "description": description
        }
        logger.info(f"Added model configuration: {model_name} -> {agent_id}")
    
    def remove_model(self, model_name: str) -> bool:
        """Remove a model configuration"""
        if model_name in self.models:
            del self.models[model_name]
            logger.info(f"Removed model configuration: {model_name}")
            return True
        return False
