"""
Response Builder for The Librarian

Builds OpenAI-compatible responses for both streaming and non-streaming modes.

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

import json
import time
import uuid
from typing import Dict, Optional


class ResponseBuilder:
    """Builds OpenAI-compatible responses"""
    
    def __init__(self):
        """Initialize response builder"""
        pass
    
    def generate_response_id(self) -> str:
        """Generate a unique response ID"""
        return f"chatcmpl-{uuid.uuid4().hex}"
    
    def build_completion_response(
        self,
        content: str,
        model_name: str,
        usage: Dict[str, int],
        response_id: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Build non-streaming completion response data.
        
        Args:
            content: Response content
            model_name: Model name
            usage: Token usage information
            response_id: Optional response ID (generated if not provided)
            
        Returns:
            Dict with response data (can be used to construct ChatCompletionResponse)
        """
        if response_id is None:
            response_id = self.generate_response_id()
        
        return {
            "id": response_id,
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model_name,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content
                },
                "finish_reason": "stop"
            }],
            "usage": usage
        }
    
    def build_stream_chunk(
        self,
        content: str,
        model_name: str,
        response_id: str,
        finish_reason: Optional[str] = None,
        usage: Optional[Dict[str, int]] = None
    ) -> str:
        """
        Build streaming chunk.
        
        Args:
            content: Chunk content
            model_name: Model name
            response_id: Response ID
            finish_reason: Optional finish reason
            usage: Optional usage information
            
        Returns:
            Formatted chunk string
        """
        chunk_data = {
            "id": response_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model_name,
            "choices": [{
                "index": 0,
                "delta": {
                    "content": content
                } if content else {},
                "finish_reason": finish_reason
            }]
        }
        
        if usage:
            chunk_data["usage"] = usage
        
        return f"data: {json.dumps(chunk_data)}\n\n"
    
    def build_final_stream_chunk(
        self,
        model_name: str,
        response_id: str,
        usage: Dict[str, int]
    ) -> str:
        """
        Build final streaming chunk with usage.
        
        Args:
            model_name: Model name
            response_id: Response ID
            usage: Token usage information
            
        Returns:
            Formatted final chunk string
        """
        return self.build_stream_chunk("", model_name, response_id, "stop", usage)
    
    def build_done_chunk(self) -> str:
        """Build [DONE] chunk"""
        return "data: [DONE]\n\n"

