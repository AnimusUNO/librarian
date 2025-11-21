"""
Error Handler for The Librarian

Centralized error handling, classification, and response formatting.

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

import logging
from typing import Optional, Union, Dict, Any, Tuple
from fastapi import HTTPException
from letta_client.core.api_error import ApiError

logger = logging.getLogger(__name__)


class ErrorType:
    """Error type constants"""
    CONTEXT_WINDOW_FULL = "context_window_full"
    API_ERROR = "api_error"
    NETWORK_ERROR = "network_error"
    VALIDATION_ERROR = "validation_error"
    SERVER_ERROR = "server_error"
    UNKNOWN_ERROR = "unknown_error"


class ErrorHandlingResult:
    """Result of error handling"""
    def __init__(
        self,
        should_retry: bool,
        error_response: Optional[Union[HTTPException, str]] = None,
        error_type: Optional[str] = None
    ):
        self.should_retry = should_retry
        self.error_response = error_response
        self.error_type = error_type


class ErrorHandler:
    """Centralized error handling for The Librarian"""
    
    def __init__(self):
        """Initialize error handler"""
        pass
    
    def is_context_window_full_error(self, error: Exception) -> bool:
        """
        Check if error is a context window full error.
        
        Args:
            error: Exception to check
            
        Returns:
            True if error indicates context window is full
        """
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()
        
        # Check for context window full indicators
        context_full_indicators = [
            "context window",
            "context_window",
            "context is full",
            "token limit exceeded",
            "maximum context length",
            "context_length_exceeded",
            "context_length",
            "max_tokens",
            "token count"
        ]
        
        # Also check error message attributes
        if hasattr(error, 'message'):
            error_str += " " + str(error.message).lower()
        if hasattr(error, 'detail'):
            error_str += " " + str(error.detail).lower()
        if hasattr(error, 'body'):
            error_str += " " + str(error.body).lower()
        
        return any(indicator in error_str for indicator in context_full_indicators)
    
    def classify_error(self, error: Exception) -> str:
        """
        Classify error type.
        
        Args:
            error: Exception to classify
            
        Returns:
            Error type string
        """
        if isinstance(error, HTTPException):
            return ErrorType.VALIDATION_ERROR
        elif isinstance(error, ApiError):
            if self.is_context_window_full_error(error):
                return ErrorType.CONTEXT_WINDOW_FULL
            return ErrorType.API_ERROR
        elif self.is_context_window_full_error(error):
            return ErrorType.CONTEXT_WINDOW_FULL
        else:
            return ErrorType.SERVER_ERROR
    
    def is_retryable_error(
        self,
        error: Exception,
        attempt: int,
        max_retries: int,
        retry_on_context_full: bool
    ) -> bool:
        """
        Determine if error is retryable.
        
        Args:
            error: Exception to check
            attempt: Current attempt number (0-indexed)
            max_retries: Maximum number of retries
            retry_on_context_full: Whether to retry on context window full errors
            
        Returns:
            True if error should be retried
        """
        # Don't retry if we've exhausted retries
        if attempt >= max_retries - 1:
            return False
        
        # Don't retry HTTP exceptions (validation errors)
        if isinstance(error, HTTPException):
            return False
        
        # Check if it's a context window full error
        if self.is_context_window_full_error(error):
            return retry_on_context_full
        
        # Don't retry other errors by default
        return False
    
    async def handle_error(
        self,
        error: Exception,
        agent_id: str,
        attempt: int,
        max_retries: int,
        retry_on_context_full: bool,
        is_streaming: bool,
        summarize_func = None
    ) -> ErrorHandlingResult:
        """
        Handle an error and determine if we should retry.
        
        Args:
            error: Exception that occurred
            agent_id: Agent ID for summarization
            attempt: Current attempt number (0-indexed)
            max_retries: Maximum number of retries
            retry_on_context_full: Whether to retry on context window full errors
            is_streaming: Whether this is a streaming response
            summarize_func: Optional function to summarize conversation before retry
            
        Returns:
            ErrorHandlingResult with retry decision and error response
        """
        error_type = self.classify_error(error)
        should_retry = self.is_retryable_error(error, attempt, max_retries, retry_on_context_full)
        
        # If retryable and context window full, try summarization
        if should_retry and error_type == ErrorType.CONTEXT_WINDOW_FULL and summarize_func:
            logger.warning(
                f"Context window full error detected, attempting summarization and retry "
                f"(attempt {attempt + 1}/{max_retries})"
            )
            try:
                if await summarize_func(agent_id, max_message_length=10):
                    # Summarization succeeded, will retry
                    return ErrorHandlingResult(should_retry=True, error_type=error_type)
                else:
                    # Summarization failed, don't retry
                    logger.error(f"Summarization failed for agent {agent_id}, not retrying")
                    should_retry = False
            except Exception as summarize_error:
                logger.error(f"Error during summarization: {str(summarize_error)}", exc_info=True)
                should_retry = False
        
        # If not retrying, format error response
        if not should_retry:
            error_response = self.format_error_response(error, error_type, is_streaming)
            return ErrorHandlingResult(
                should_retry=False,
                error_response=error_response,
                error_type=error_type
            )
        
        # Should retry
        return ErrorHandlingResult(should_retry=True, error_type=error_type)
    
    def format_error_response(
        self,
        error: Exception,
        error_type: str,
        is_streaming: bool
    ) -> Union[HTTPException, str]:
        """
        Format error for HTTP response or streaming chunk.
        
        Args:
            error: Exception to format
            error_type: Classified error type
            is_streaming: Whether this is for streaming response
            
        Returns:
            HTTPException for non-streaming, error chunk string for streaming
        """
        error_message = str(error)
        
        # Determine error message based on type
        if error_type == ErrorType.CONTEXT_WINDOW_FULL:
            message = f"Context window full: {error_message}"
        elif error_type == ErrorType.API_ERROR:
            message = f"Letta API error: {error_message}"
        else:
            message = f"Server error: {error_message}"
        
        if is_streaming:
            # Format as streaming error chunk
            import json
            error_chunk = {
                "error": {
                    "message": message,
                    "type": "server_error"
                }
            }
            chunk_str = f"data: {json.dumps(error_chunk)}\n\n"
            chunk_str += "data: [DONE]\n\n"
            return chunk_str
        else:
            # Format as HTTPException
            return HTTPException(
                status_code=500,
                detail={"error": {"message": message, "type": "server_error"}}
            )

