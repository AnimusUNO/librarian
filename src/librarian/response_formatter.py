"""
Response Formatter for The Librarian

Converts Letta responses to OpenAI format.
Handles reasoning block filtering and middleware processing.
"""

import json
import time
import uuid
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class ResponseFormatter:
    """Converts Letta responses to OpenAI format"""
    
    def format_completion_response(self, letta_response: Dict[str, Any], model_name: str) -> Dict[str, Any]:
        """Format non-streaming response"""
        return {
            "id": f"chatcmpl-{uuid.uuid4().hex}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model_name,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": self._extract_content(letta_response)
                },
                "finish_reason": "stop"
            }],
            "usage": self._extract_usage(letta_response)
        }
    
    def format_streaming_chunk(self, chunk: Dict[str, Any], model_name: str, chunk_id: str) -> str:
        """Format streaming chunk"""
        chunk_data = {
            "id": chunk_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model_name,
            "choices": [{
                "index": 0,
                "delta": {
                    "content": self._extract_content(chunk)
                },
                "finish_reason": None
            }]
        }
        return f"data: {json.dumps(chunk_data)}\n\n"
    
    def format_error_response(self, error_message: str, error_type: str = "invalid_request_error") -> Dict[str, Any]:
        """Format error response in OpenAI format"""
        return {
            "error": {
                "message": error_message,
                "type": error_type,
                "param": None,
                "code": None
            }
        }
    
    def format_models_response(self, models: List[Dict[str, str]]) -> Dict[str, Any]:
        """Format models list response"""
        model_list = []
        for model_id, config in models.items():
            model_list.append({
                "id": model_id,
                "object": "model",
                "created": 1700000000,  # Placeholder timestamp
                "owned_by": "librarian"
            })
        
        return {
            "object": "list",
            "data": model_list
        }
    
    def _extract_content(self, response: Dict[str, Any]) -> str:
        """
        Extract content from Letta response, filtering out reasoning blocks
        
        Args:
            response: Letta response object
            
        Returns:
            Cleaned content string
        """
        if isinstance(response, dict):
            # Filter out reasoning blocks - middleware removes reasoning output
            if "reasoning" in response:
                logger.debug("Filtering out reasoning block from response")
                # Remove reasoning block but keep other content
                pass
            
            if "content" in response:
                if isinstance(response["content"], list) and response["content"]:
                    return response["content"][0].get("text", "")
                elif isinstance(response["content"], str):
                    return response["content"]
            elif "message" in response and "content" in response["message"]:
                return response["message"]["content"]
            elif "text" in response:
                return response["text"]
        
        return str(response)
    
    def _extract_usage(self, response: Dict[str, Any]) -> Dict[str, int]:
        """Extract usage information from Letta response"""
        if isinstance(response, dict) and "usage" in response:
            usage = response["usage"]
            return {
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0)
            }
        
        # Default usage if not provided
        return {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        }
