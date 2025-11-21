"""
Tests for ErrorHandler

Copyright (C) 2025 AnimusUNO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import pytest
from fastapi import HTTPException
from letta_client.core.api_error import ApiError
from src.librarian.error_handler import ErrorHandler, ErrorType, ErrorHandlingResult


class TestErrorHandler:
    """Test ErrorHandler class"""
    
    def test_init(self):
        """Test ErrorHandler initialization"""
        handler = ErrorHandler()
        assert handler is not None
    
    def test_is_context_window_full_error_true(self):
        """Test context window full error detection - positive cases"""
        handler = ErrorHandler()
        
        # Test various context window full error messages
        error1 = Exception("context window full")
        error2 = Exception("context_window exceeded")
        error3 = Exception("token limit exceeded")
        error4 = Exception("maximum context length")
        
        assert handler.is_context_window_full_error(error1) is True
        assert handler.is_context_window_full_error(error2) is True
        assert handler.is_context_window_full_error(error3) is True
        assert handler.is_context_window_full_error(error4) is True
    
    def test_is_context_window_full_error_false(self):
        """Test context window full error detection - negative cases"""
        handler = ErrorHandler()
        
        # Test non-context window errors
        error1 = Exception("network error")
        error2 = Exception("authentication failed")
        error3 = Exception("invalid request")
        
        assert handler.is_context_window_full_error(error1) is False
        assert handler.is_context_window_full_error(error2) is False
        assert handler.is_context_window_full_error(error3) is False
    
    def test_classify_error_http_exception(self):
        """Test error classification - HTTPException"""
        handler = ErrorHandler()
        error = HTTPException(status_code=400, detail="Bad request")
        assert handler.classify_error(error) == ErrorType.VALIDATION_ERROR
    
    def test_classify_error_api_error(self):
        """Test error classification - ApiError"""
        handler = ErrorHandler()
        # ApiError is typically raised by the letta_client library
        # Create a mock ApiError for testing with required attributes
        class MockApiError(ApiError):
            def __init__(self):
                # ApiError requires headers, status_code, and body
                self.headers = {}
                self.status_code = 500
                self.body = {"error": "API error"}
        
        error = MockApiError()
        error_type = handler.classify_error(error)
        # ApiError should be classified as API_ERROR (unless it's context window full)
        assert error_type in [ErrorType.API_ERROR, ErrorType.CONTEXT_WINDOW_FULL]
    
    def test_classify_error_context_window_full(self):
        """Test error classification - context window full"""
        handler = ErrorHandler()
        error = Exception("context window full")
        assert handler.classify_error(error) == ErrorType.CONTEXT_WINDOW_FULL
    
    def test_classify_error_generic(self):
        """Test error classification - generic error"""
        handler = ErrorHandler()
        error = Exception("generic error")
        assert handler.classify_error(error) == ErrorType.SERVER_ERROR
    
    def test_is_retryable_error_context_window_full(self):
        """Test retryable error check - context window full"""
        handler = ErrorHandler()
        error = Exception("context window full")
        
        # Should be retryable if retry_on_context_full is True and attempt < max_retries
        assert handler.is_retryable_error(error, attempt=0, max_retries=2, retry_on_context_full=True) is True
        assert handler.is_retryable_error(error, attempt=1, max_retries=2, retry_on_context_full=True) is False  # Last attempt
        assert handler.is_retryable_error(error, attempt=0, max_retries=2, retry_on_context_full=False) is False  # Retry disabled
    
    def test_is_retryable_error_http_exception(self):
        """Test retryable error check - HTTPException (not retryable)"""
        handler = ErrorHandler()
        error = HTTPException(status_code=400, detail="Bad request")
        
        assert handler.is_retryable_error(error, attempt=0, max_retries=2, retry_on_context_full=True) is False
    
    def test_is_retryable_error_generic(self):
        """Test retryable error check - generic error (not retryable)"""
        handler = ErrorHandler()
        error = Exception("generic error")
        
        assert handler.is_retryable_error(error, attempt=0, max_retries=2, retry_on_context_full=True) is False
    
    @pytest.mark.asyncio
    async def test_handle_error_non_retryable(self):
        """Test error handling - non-retryable error"""
        handler = ErrorHandler()
        error = Exception("generic error")
        
        result = await handler.handle_error(
            error,
            agent_id="test-agent",
            attempt=0,
            max_retries=2,
            retry_on_context_full=True,
            is_streaming=False
        )
        
        assert result.should_retry is False
        assert result.error_response is not None
        assert isinstance(result.error_response, HTTPException)
    
    @pytest.mark.asyncio
    async def test_handle_error_streaming(self):
        """Test error handling - streaming error"""
        handler = ErrorHandler()
        error = Exception("generic error")
        
        result = await handler.handle_error(
            error,
            agent_id="test-agent",
            attempt=0,
            max_retries=2,
            retry_on_context_full=True,
            is_streaming=True
        )
        
        assert result.should_retry is False
        assert result.error_response is not None
        assert isinstance(result.error_response, str)
        assert "data: " in result.error_response
        assert "[DONE]" in result.error_response
    
    def test_format_error_response_non_streaming(self):
        """Test error response formatting - non-streaming"""
        handler = ErrorHandler()
        error = Exception("test error")
        
        response = handler.format_error_response(error, ErrorType.SERVER_ERROR, is_streaming=False)
        
        assert isinstance(response, HTTPException)
        assert response.status_code == 500
        assert "test error" in str(response.detail)
    
    def test_format_error_response_streaming(self):
        """Test error response formatting - streaming"""
        handler = ErrorHandler()
        error = Exception("test error")
        
        response = handler.format_error_response(error, ErrorType.SERVER_ERROR, is_streaming=True)
        
        assert isinstance(response, str)
        assert "data: " in response
        assert "[DONE]" in response
        assert "test error" in response

