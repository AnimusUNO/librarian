"""
Tests for RequestProcessor

Copyright (C) 2025 AnimusUNO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from letta_client import MessageCreate
from letta_client.types import TextContent
from src.librarian.request_processor import RequestProcessor, ProcessedRequest


class TestRequestProcessor:
    """Test RequestProcessor class"""
    
    @pytest.fixture
    def mock_components(self):
        """Create mock components for RequestProcessor"""
        model_registry = MagicMock()
        message_translator = MagicMock()
        token_counter = MagicMock()
        tool_synchronizer = MagicMock()
        letta_client = AsyncMock()
        check_token_capacity_func = AsyncMock()
        
        return {
            'model_registry': model_registry,
            'message_translator': message_translator,
            'token_counter': token_counter,
            'tool_synchronizer': tool_synchronizer,
            'letta_client': letta_client,
            'check_token_capacity_func': check_token_capacity_func
        }
    
    @pytest.fixture
    def request_processor(self, mock_components):
        """Create RequestProcessor instance with mocked components"""
        return RequestProcessor(**mock_components)
    
    @pytest.fixture
    def mock_request(self):
        """Create a mock ChatCompletionRequest"""
        request = MagicMock()
        request.model = "gpt-4.1"
        request.messages = [
            MagicMock(role="user", content="Hello")
        ]
        request.tools = None
        request.user = "test-user"
        request.max_tokens = None
        request.temperature = None
        return request
    
    def test_init(self, mock_components):
        """Test RequestProcessor initialization"""
        processor = RequestProcessor(**mock_components)
        assert processor.model_registry == mock_components['model_registry']
        assert processor.message_translator == mock_components['message_translator']
        assert processor.token_counter == mock_components['token_counter']
        assert processor.tool_synchronizer == mock_components['tool_synchronizer']
        assert processor.letta_client == mock_components['letta_client']
        assert processor.check_token_capacity == mock_components['check_token_capacity_func']
    
    @pytest.mark.asyncio
    async def test_process_request_basic(self, request_processor, mock_request, mock_components):
        """Test basic request processing"""
        # Setup mocks
        mock_components['model_registry'].get_agent_config.return_value = {
            'agent_id': 'agent-123',
            'mode': 'auto'
        }
        mock_components['message_translator'].translate_messages.return_value = (
            [{"role": "user", "content": [{"type": "text", "text": "Hello"}]}],
            None
        )
        mock_components['message_translator'].create_mode_selection_instruction.return_value = "Mode instruction"
        mock_components['token_counter'].count_messages_tokens.return_value = 10
        mock_components['check_token_capacity_func'].return_value = (True, None, None)
        
        # Process request
        processed = await request_processor.process_request(mock_request)
        
        # Verify
        assert isinstance(processed, ProcessedRequest)
        assert processed.agent_id == 'agent-123'
        assert processed.model_name == "gpt-4.1"
        assert processed.user_id == "test-user"
        assert "[API]" in processed.system_content
        assert "Mode instruction" in processed.system_content
        assert len(processed.message_objects) == 1
        assert isinstance(processed.message_objects[0], MessageCreate)
    
    @pytest.mark.asyncio
    async def test_process_request_with_tools(self, request_processor, mock_request, mock_components):
        """Test request processing with tools"""
        # Setup mocks
        mock_components['model_registry'].get_agent_config.return_value = {
            'agent_id': 'agent-123',
            'mode': 'auto'
        }
        mock_components['message_translator'].translate_messages.return_value = (
            [{"role": "user", "content": [{"type": "text", "text": "Hello"}]}],
            None
        )
        mock_components['message_translator'].create_mode_selection_instruction.return_value = "Mode instruction"
        mock_components['token_counter'].count_messages_tokens.return_value = 10
        mock_components['check_token_capacity_func'].return_value = (True, None, None)
        mock_components['tool_synchronizer'].sync_tools = AsyncMock()
        
        # Add tools to request
        mock_request.tools = [{"type": "function", "function": {"name": "test_tool"}}]
        
        # Process request
        processed = await request_processor.process_request(mock_request)
        
        # Verify tools were synced
        mock_components['tool_synchronizer'].sync_tools.assert_called_once_with('agent-123', mock_request.tools)
    
    @pytest.mark.asyncio
    async def test_process_request_token_capacity_exceeded(self, request_processor, mock_request, mock_components):
        """Test request processing when token capacity is exceeded"""
        # Setup mocks
        mock_components['model_registry'].get_agent_config.return_value = {
            'agent_id': 'agent-123',
            'mode': 'auto'
        }
        mock_components['message_translator'].translate_messages.return_value = (
            [{"role": "user", "content": [{"type": "text", "text": "Hello"}]}],
            None
        )
        mock_components['message_translator'].create_mode_selection_instruction.return_value = "Mode instruction"
        mock_components['token_counter'].count_messages_tokens.return_value = 10
        mock_components['check_token_capacity_func'].return_value = (
            False,
            "Request exceeds model's maximum token capacity",
            None
        )
        
        # Process request should raise ValueError
        with pytest.raises(ValueError, match="Request exceeds model's maximum token capacity"):
            await request_processor.process_request(mock_request)
    
    @pytest.mark.asyncio
    async def test_prepare_messages(self, request_processor, mock_components):
        """Test message preparation"""
        messages = [MagicMock(role="user", content="Hello")]
        agent_config = {'mode': 'auto'}
        model_name = "gpt-4.1"
        
        # Setup mocks
        mock_components['message_translator'].translate_messages.return_value = (
            [{"role": "user", "content": [{"type": "text", "text": "Hello"}]}],
            "System content"
        )
        mock_components['message_translator'].create_mode_selection_instruction.return_value = "Mode instruction"
        mock_components['token_counter'].count_messages_tokens.return_value = 15
        
        # Prepare messages
        letta_messages, system_content, estimated_tokens = await request_processor.prepare_messages(
            messages, agent_config, model_name
        )
        
        # Verify
        assert len(letta_messages) == 1
        assert "[API]" in system_content
        assert "System content" in system_content
        assert "Mode instruction" in system_content
        assert estimated_tokens == 15
    
    @pytest.mark.asyncio
    async def test_prepare_messages_no_system_content(self, request_processor, mock_components):
        """Test message preparation without existing system content"""
        messages = [MagicMock(role="user", content="Hello")]
        agent_config = {'mode': 'worker'}
        model_name = "gpt-4.1"
        
        # Setup mocks
        mock_components['message_translator'].translate_messages.return_value = (
            [{"role": "user", "content": [{"type": "text", "text": "Hello"}]}],
            None  # No system content
        )
        mock_components['message_translator'].create_mode_selection_instruction.return_value = "Mode instruction"
        mock_components['token_counter'].count_messages_tokens.return_value = 12
        
        # Prepare messages
        letta_messages, system_content, estimated_tokens = await request_processor.prepare_messages(
            messages, agent_config, model_name
        )
        
        # Verify
        assert "[API]" in system_content
        assert "Mode instruction" in system_content
    
    @pytest.mark.asyncio
    async def test_validate_token_capacity_valid(self, request_processor, mock_components):
        """Test token capacity validation - valid"""
        mock_components['check_token_capacity_func'].return_value = (True, None, None)
        
        is_valid, error_message = await request_processor.validate_token_capacity(
            "agent-123", 100, None
        )
        
        assert is_valid is True
        assert error_message is None
        mock_components['check_token_capacity_func'].assert_called_once_with(
            "agent-123", 100, requested_max_tokens=None
        )
    
    @pytest.mark.asyncio
    async def test_validate_token_capacity_invalid(self, request_processor, mock_components):
        """Test token capacity validation - invalid"""
        mock_components['check_token_capacity_func'].return_value = (
            False,
            "Request exceeds model's maximum token capacity",
            None
        )
        
        is_valid, error_message = await request_processor.validate_token_capacity(
            "agent-123", 100000, 50000
        )
        
        assert is_valid is False
        assert "exceeds" in error_message
        mock_components['check_token_capacity_func'].assert_called_once_with(
            "agent-123", 100000, requested_max_tokens=50000
        )
    
    def test_build_message_objects(self, request_processor):
        """Test building MessageCreate objects"""
        letta_messages = [
            {
                "role": "user",
                "content": [{"type": "text", "text": "Hello"}]
            },
            {
                "role": "assistant",
                "content": "Response"
            }
        ]
        
        message_objects = request_processor._build_message_objects(letta_messages)
        
        assert len(message_objects) == 2
        assert isinstance(message_objects[0], MessageCreate)
        assert isinstance(message_objects[1], MessageCreate)
        assert message_objects[0].role == "user"
        assert message_objects[1].role == "assistant"
    
    def test_build_message_objects_with_tool_call_id(self, request_processor):
        """Test building MessageCreate objects with tool_call_id"""
        letta_messages = [
            {
                "role": "tool",
                "content": [{"type": "text", "text": "Tool result"}],
                "tool_call_id": "call-123"
            }
        ]
        
        message_objects = request_processor._build_message_objects(letta_messages)
        
        assert len(message_objects) == 1
        assert message_objects[0].tool_call_id == "call-123"
    
    def test_build_message_objects_string_content(self, request_processor):
        """Test building MessageCreate objects with string content"""
        letta_messages = [
            {
                "role": "user",
                "content": "Simple string"
            }
        ]
        
        message_objects = request_processor._build_message_objects(letta_messages)
        
        assert len(message_objects) == 1
        assert len(message_objects[0].content) == 1
        assert isinstance(message_objects[0].content[0], TextContent)
        assert message_objects[0].content[0].text == "Simple string"

