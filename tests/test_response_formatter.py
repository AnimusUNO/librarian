#!/usr/bin/env python3
"""
Test suite for ResponseFormatter

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
import uuid
import time
from src.librarian.response_formatter import ResponseFormatter


class TestResponseFormatter:
    """Test ResponseFormatter class"""
    
    def test_init(self):
        """Test ResponseFormatter initialization"""
        formatter = ResponseFormatter()
        assert formatter is not None
    
    def test_format_completion_response_basic(self):
        """Test basic completion response formatting"""
        formatter = ResponseFormatter()
        letta_response = {"content": "Hello, world!", "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}}
        response = formatter.format_completion_response(letta_response, "gpt-4")
        
        assert response is not None
        assert response["model"] == "gpt-4"
        assert "choices" in response
        assert len(response["choices"]) == 1
        assert response["choices"][0]["message"]["content"] == "Hello, world!"
        assert "usage" in response
    
    def test_format_completion_response_with_finish_reason(self):
        """Test completion response formatting with finish reason"""
        formatter = ResponseFormatter()
        letta_response = {"content": "Hello", "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}}
        response = formatter.format_completion_response(letta_response, "gpt-4")
        
        assert response["choices"][0]["finish_reason"] == "stop"
    
    def test_format_streaming_chunk_basic(self):
        """Test basic streaming chunk formatting"""
        formatter = ResponseFormatter()
        chunk_data = {"content": "Hello"}
        chunk_str = formatter.format_streaming_chunk(chunk_data, "gpt-4", "test-123")
        
        assert chunk_str is not None
        assert "data: " in chunk_str
        assert "test-123" in chunk_str
        assert "gpt-4" in chunk_str
        assert "Hello" in chunk_str
    
    def test_format_streaming_chunk_final(self):
        """Test final streaming chunk formatting"""
        formatter = ResponseFormatter()
        chunk_data = {"content": ""}
        chunk_str = formatter.format_streaming_chunk(chunk_data, "gpt-4", "test-123")
        
        assert chunk_str is not None
        # Finish reason is not currently in format_streaming_chunk signature
    
    def test_extract_content_from_dict(self):
        """Test extracting content from dict"""
        formatter = ResponseFormatter()
        response_dict = {"content": "Hello, world!"}
        content = formatter._extract_content(response_dict)
        assert content == "Hello, world!"
    
    def test_extract_content_from_string(self):
        """Test extracting content from string"""
        formatter = ResponseFormatter()
        content = formatter._extract_content("Hello, world!")
        assert content == "Hello, world!"
    
    def test_extract_content_from_list(self):
        """Test extracting content from list"""
        formatter = ResponseFormatter()
        response_dict = {
            "content": [
                {"text": "Hello, "},
                {"text": "world!"}
            ]
        }
        content = formatter._extract_content(response_dict)
        assert content == "Hello, world!"
    
    def test_extract_content_from_none(self):
        """Test extracting content from None"""
        formatter = ResponseFormatter()
        content = formatter._extract_content(None)
        assert content == ""
    
    def test_format_error_response(self):
        """Test formatting error response"""
        formatter = ResponseFormatter()
        error = formatter.format_error_response("Test error", "test_error")
        
        assert "error" in error
        assert error["error"]["message"] == "Test error"
        assert error["error"]["type"] == "test_error"
    
    def test_format_models_response(self):
        """Test formatting models response"""
        formatter = ResponseFormatter()
        models = {
            "gpt-4": {"description": "GPT-4"},
            "gpt-3.5-turbo": {"description": "GPT-3.5 Turbo"}
        }
        response = formatter.format_models_response(models)
        
        assert response["object"] == "list"
        assert len(response["data"]) == 2
        assert response["data"][0]["id"] in models
    
    def test_extract_usage(self):
        """Test extracting usage information"""
        formatter = ResponseFormatter()
        response = {
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15
            }
        }
        usage = formatter._extract_usage(response)
        assert usage["prompt_tokens"] == 10
        assert usage["completion_tokens"] == 5
        assert usage["total_tokens"] == 15
    
    def test_extract_usage_default(self):
        """Test extracting usage with defaults"""
        formatter = ResponseFormatter()
        response = {}
        usage = formatter._extract_usage(response)
        assert usage["prompt_tokens"] == 0
        assert usage["completion_tokens"] == 0
        assert usage["total_tokens"] == 0
    
    def test_extract_content_from_object_with_model_dump(self):
        """Test extracting content from object with model_dump"""
        from unittest.mock import Mock
        formatter = ResponseFormatter()
        mock_obj = Mock()
        mock_obj.model_dump.return_value = {"content": "Hello from model_dump"}
        content = formatter._extract_content(mock_obj)
        assert content == "Hello from model_dump"
    
    def test_extract_content_from_object_with_dict(self):
        """Test extracting content from object with __dict__"""
        from unittest.mock import Mock
        formatter = ResponseFormatter()
        mock_obj = Mock()
        # Create a class with __dict__
        class TestObj:
            def __init__(self):
                self.content = "Hello from __dict__"
        test_obj = TestObj()
        content = formatter._extract_content(test_obj)
        assert content == "Hello from __dict__"
    
    def test_extract_content_from_object_with_attributes(self):
        """Test extracting content from object with attributes"""
        from unittest.mock import Mock
        formatter = ResponseFormatter()
        # Create a simple object with content attribute
        class TestObj:
            def __init__(self):
                self.content = "Hello from attribute"
        test_obj = TestObj()
        content = formatter._extract_content(test_obj)
        assert content == "Hello from attribute"
    
    def test_extract_content_message_type_error(self):
        """Test extracting content from error message type"""
        formatter = ResponseFormatter()
        response_dict = {"message_type": "error", "content": "Error message"}
        content = formatter._extract_content(response_dict)
        assert content == ""  # Should return empty for error type
    
    def test_extract_content_message_type_stop_reason(self):
        """Test extracting content from stop_reason message type"""
        formatter = ResponseFormatter()
        response_dict = {"message_type": "stop_reason", "content": "Stop"}
        content = formatter._extract_content(response_dict)
        assert content == ""  # Should return empty for stop_reason type
    
    def test_extract_content_with_reasoning(self):
        """Test extracting content with reasoning block"""
        formatter = ResponseFormatter()
        response_dict = {
            "content": "Hello",
            "reasoning": "Some reasoning"
        }
        content = formatter._extract_content(response_dict)
        # Reasoning should be filtered but content should remain
        assert content == "Hello"
    
    def test_extract_content_from_message_nested(self):
        """Test extracting content from nested message structure"""
        formatter = ResponseFormatter()
        response_dict = {
            "message": {
                "content": "Hello from nested"
            }
        }
        content = formatter._extract_content(response_dict)
        assert content == "Hello from nested"
    
    def test_extract_content_from_text_field(self):
        """Test extracting content from text field"""
        formatter = ResponseFormatter()
        response_dict = {"text": "Hello from text"}
        content = formatter._extract_content(response_dict)
        assert content == "Hello from text"
    
    def test_extract_content_list_with_text_attr(self):
        """Test extracting content from list with text attribute"""
        formatter = ResponseFormatter()
        
        class TextObj:
            def __init__(self, text):
                self.text = text
        
        response_dict = {
            "content": [TextObj("Hello"), TextObj(" world")]
        }
        content = formatter._extract_content(response_dict)
        assert content == "Hello world"
    
    def test_extract_content_list_with_str(self):
        """Test extracting content from list with string items"""
        formatter = ResponseFormatter()
        response_dict = {
            "content": ["Hello", " world"]
        }
        content = formatter._extract_content(response_dict)
        assert content == "Hello world"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

