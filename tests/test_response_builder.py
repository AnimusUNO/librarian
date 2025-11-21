"""
Tests for ResponseBuilder

Copyright (C) 2025 AnimusUNO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import pytest
import json
from src.librarian.response_builder import ResponseBuilder


class TestResponseBuilder:
    """Test ResponseBuilder class"""
    
    def test_init(self):
        """Test ResponseBuilder initialization"""
        builder = ResponseBuilder()
        assert builder is not None
    
    def test_generate_response_id(self):
        """Test response ID generation"""
        builder = ResponseBuilder()
        id1 = builder.generate_response_id()
        id2 = builder.generate_response_id()
        
        assert id1.startswith("chatcmpl-")
        assert id2.startswith("chatcmpl-")
        assert id1 != id2  # Should be unique
    
    def test_build_completion_response(self):
        """Test building completion response"""
        builder = ResponseBuilder()
        
        response_data = builder.build_completion_response(
            content="Hello, world!",
            model_name="gpt-4",
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
        )
        
        assert response_data["id"].startswith("chatcmpl-")
        assert response_data["object"] == "chat.completion"
        assert response_data["model"] == "gpt-4"
        assert response_data["choices"][0]["message"]["content"] == "Hello, world!"
        assert response_data["usage"]["total_tokens"] == 15
    
    def test_build_completion_response_with_id(self):
        """Test building completion response with custom ID"""
        builder = ResponseBuilder()
        custom_id = "chatcmpl-custom123"
        
        response_data = builder.build_completion_response(
            content="Test",
            model_name="gpt-4",
            usage={"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7},
            response_id=custom_id
        )
        
        assert response_data["id"] == custom_id
    
    def test_build_stream_chunk(self):
        """Test building stream chunk"""
        builder = ResponseBuilder()
        response_id = builder.generate_response_id()
        
        chunk = builder.build_stream_chunk(
            content="Hello",
            model_name="gpt-4",
            response_id=response_id
        )
        
        assert chunk.startswith("data: ")
        chunk_data = json.loads(chunk.split("data: ")[1].strip())
        assert chunk_data["id"] == response_id
        assert chunk_data["model"] == "gpt-4"
        assert chunk_data["choices"][0]["delta"]["content"] == "Hello"
        assert chunk_data["choices"][0]["finish_reason"] is None
    
    def test_build_stream_chunk_with_finish_reason(self):
        """Test building stream chunk with finish reason"""
        builder = ResponseBuilder()
        response_id = builder.generate_response_id()
        
        chunk = builder.build_stream_chunk(
            content="",
            model_name="gpt-4",
            response_id=response_id,
            finish_reason="stop"
        )
        
        chunk_data = json.loads(chunk.split("data: ")[1].strip())
        assert chunk_data["choices"][0]["finish_reason"] == "stop"
    
    def test_build_stream_chunk_with_usage(self):
        """Test building stream chunk with usage"""
        builder = ResponseBuilder()
        response_id = builder.generate_response_id()
        
        chunk = builder.build_stream_chunk(
            content="",
            model_name="gpt-4",
            response_id=response_id,
            finish_reason="stop",
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
        )
        
        chunk_data = json.loads(chunk.split("data: ")[1].strip())
        assert "usage" in chunk_data
        assert chunk_data["usage"]["total_tokens"] == 15
    
    def test_build_final_stream_chunk(self):
        """Test building final stream chunk"""
        builder = ResponseBuilder()
        response_id = builder.generate_response_id()
        
        chunk = builder.build_final_stream_chunk(
            model_name="gpt-4",
            response_id=response_id,
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
        )
        
        chunk_data = json.loads(chunk.split("data: ")[1].strip())
        assert chunk_data["choices"][0]["finish_reason"] == "stop"
        assert "usage" in chunk_data
        assert chunk_data["usage"]["total_tokens"] == 15
    
    def test_build_done_chunk(self):
        """Test building [DONE] chunk"""
        builder = ResponseBuilder()
        chunk = builder.build_done_chunk()
        
        assert chunk == "data: [DONE]\n\n"

