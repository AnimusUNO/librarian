"""
Response Formatter for The Librarian

Converts Letta responses to OpenAI format.
Handles reasoning block filtering and middleware processing.

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
    
    def _extract_content(self, response: Any) -> str:
        """
        Extract content from Letta response, filtering out reasoning blocks
        
        Args:
            response: Letta response object (dict or object)
            
        Returns:
            Cleaned content string
        """
        # Handle both dict and object responses
        response_dict = response
        if not isinstance(response, dict):
            # Convert object to dict if possible
            if hasattr(response, 'model_dump'):
                response_dict = response.model_dump()
            elif hasattr(response, '__dict__'):
                response_dict = response.__dict__
            else:
                # Try to access as attributes
                response_dict = {}
                for attr in ['content', 'message', 'text', 'message_type', 'stop_reason', 'error']:
                    if hasattr(response, attr):
                        try:
                            value = getattr(response, attr)
                            if value is not None:  # Only add non-None values
                                response_dict[attr] = value
                        except:
                            pass
        
        # Skip error and stop_reason events
        if isinstance(response_dict, dict):
            if response_dict.get("message_type") in ["error", "stop_reason"]:
                return ""
            
            # Filter out reasoning blocks - middleware removes reasoning output
            if "reasoning" in response_dict:
                logger.debug("Filtering out reasoning block from response")
                # Remove reasoning block but keep other content
                pass
            
            if "content" in response_dict:
                content = response_dict["content"]
                if isinstance(content, list) and content:
                    # Handle list of content items (TextContent objects or dicts)
                    text_parts = []
                    for item in content:
                        if isinstance(item, dict):
                            text_parts.append(item.get("text", ""))
                        elif hasattr(item, 'text'):
                            # TextContent object
                            text_parts.append(item.text)
                        else:
                            text_parts.append(str(item))
                    return "".join(text_parts)
                elif isinstance(content, str):
                    return content
            elif "message" in response_dict and "content" in response_dict["message"]:
                return response_dict["message"]["content"]
            elif "text" in response_dict:
                return response_dict["text"]
        
        # If it's a string or has string representation, return that
        if isinstance(response, str):
            return response
        
        return ""
    
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
