"""
Message Translator for The Librarian

Converts OpenAI messages to Letta MessageCreate format.
Handles system messages via memory overlays and dual-mode behavior.

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
                # System messages are NOT sent as normal messages
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
    
    def create_mode_selection_instruction(self, mode: str) -> str:
        """
        Create system instruction for dual-mode behavior
        
        Args:
            mode: Either 'worker' or 'persona'
            
        Returns:
            System instruction for mode selection
        """
        base_instruction = """Use your reasoning block to silently determine whether to act in Worker or Persona mode.
Do not reveal this process; only the final response should be returned.

Worker Mode: Follow instructions literally with minimal narrative. Use for procedural, technical, or mechanical tasks.
Persona Mode: Engage as The Librarian with expressive, interpretive responses. Use when judgment, authorship, or creative insight is requested."""
        
        if mode == "worker":
            return base_instruction + "\n\nCurrent context suggests Worker Mode is appropriate."
        elif mode == "persona":
            return base_instruction + "\n\nCurrent context suggests Persona Mode is appropriate."
        else:
            return base_instruction
    
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
