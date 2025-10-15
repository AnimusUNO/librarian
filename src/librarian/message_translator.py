"""
Message Translator for The Librarian

Converts OpenAI messages to Letta MessageCreate format.
"""

from typing import List, Dict, Tuple, Optional
from pydantic import BaseModel


class TextContent(BaseModel):
    """Text content for Letta messages"""
    type: str = "text"
    text: str


class MessageTranslator:
    """Converts OpenAI messages to Letta MessageCreate format"""
    
    def translate_messages(self, openai_messages: List[Dict[str, str]]) -> Tuple[List[Dict[str, any]], Optional[str]]:
        """
        Convert OpenAI messages to Letta MessageCreate format
        
        Args:
            openai_messages: List of OpenAI message objects
            
        Returns:
            Tuple of (letta_messages, system_content)
        """
        letta_messages = []
        system_content = None
        
        for msg in openai_messages:
            if msg["role"] == "system":
                # Extract system content for memory overlay
                system_content = msg["content"]
            elif msg["role"] == "user":
                letta_messages.append({
                    "role": "user",
                    "content": [{"type": "text", "text": msg["content"]}]
                })
            elif msg["role"] == "assistant":
                letta_messages.append({
                    "role": "assistant",
                    "content": [{"type": "text", "text": msg["content"]}]
                })
            elif msg["role"] == "tool":
                letta_messages.append({
                    "role": "tool",
                    "content": [{"type": "text", "text": msg["content"]}],
                    "tool_call_id": msg.get("tool_call_id")
                })
        
        return letta_messages, system_content
    
    def extract_system_messages(self, openai_messages: List[Dict[str, str]]) -> List[str]:
        """Extract all system messages from OpenAI messages"""
        system_messages = []
        for msg in openai_messages:
            if msg["role"] == "system":
                system_messages.append(msg["content"])
        return system_messages
    
    def has_system_messages(self, openai_messages: List[Dict[str, str]]) -> bool:
        """Check if messages contain system messages"""
        return any(msg["role"] == "system" for msg in openai_messages)
    
    def validate_messages(self, openai_messages: List[Dict[str, str]]) -> bool:
        """Validate OpenAI message format"""
        if not openai_messages:
            return False
        
        for msg in openai_messages:
            if not isinstance(msg, dict):
                return False
            if "role" not in msg or "content" not in msg:
                return False
            if msg["role"] not in ["system", "user", "assistant", "tool"]:
                return False
        
        return True
