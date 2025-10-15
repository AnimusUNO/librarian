"""
Model Registry for The Librarian

Maps OpenAI model names to Letta agent configurations.
"""

from typing import Dict, Optional
import os


class ModelRegistry:
    """Maps OpenAI model names to Letta agent configurations"""
    
    def __init__(self):
        self.models = {
            "gpt-3.5-turbo": {
                "agent_id": os.getenv("LIBRARIAN_WORKER_AGENT", "librarian-worker"),
                "mode": "worker",
                "description": "The Librarian in Worker Mode"
            },
            "gpt-4": {
                "agent_id": os.getenv("LIBRARIAN_PERSONA_AGENT", "librarian-persona"), 
                "mode": "persona",
                "description": "The Librarian in Persona Mode"
            },
            "gpt-4-turbo": {
                "agent_id": os.getenv("LIBRARIAN_PERSONA_TURBO_AGENT", "librarian-persona-turbo"),
                "mode": "persona", 
                "description": "The Librarian in Persona Mode (Turbo)"
            }
        }
    
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
