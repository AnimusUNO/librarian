"""
Tests for TokenLimitService

Copyright (C) 2025 AnimusUNO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.librarian.token_limit_service import TokenLimitService


class TestTokenLimitService:
    """Test TokenLimitService class"""
    
    @pytest.fixture
    def mock_letta_client(self):
        """Create mock Letta client"""
        return AsyncMock()
    
    @pytest.fixture
    def token_limit_service(self, mock_letta_client):
        """Create TokenLimitService instance"""
        return TokenLimitService(mock_letta_client, cache_ttl=300)
    
    @pytest.mark.asyncio
    async def test_get_agent_token_limits(self, token_limit_service, mock_letta_client):
        """Test getting agent token limits"""
        # Mock context response
        mock_context = MagicMock()
        mock_context.model_dump.return_value = {
            'context_window_size_current': 1000,
            'context_window_size_max': 128000
        }
        mock_letta_client.agents.context.retrieve = AsyncMock(return_value=mock_context)
        
        limits = await token_limit_service.get_agent_token_limits("agent-123")
        
        assert limits['max_context_window'] == 128000
        assert limits['current_tokens'] == 1000
        assert limits['available_tokens'] == 127000
        mock_letta_client.agents.context.retrieve.assert_called_once_with(agent_id="agent-123")
    
    @pytest.mark.asyncio
    async def test_get_agent_token_limits_caching(self, token_limit_service, mock_letta_client):
        """Test that max_context_window is cached"""
        # Mock context response
        mock_context = MagicMock()
        mock_context.model_dump.return_value = {
            'context_window_size_current': 1000,
            'context_window_size_max': 128000
        }
        mock_letta_client.agents.context.retrieve = AsyncMock(return_value=mock_context)
        
        # First call
        limits1 = await token_limit_service.get_agent_token_limits("agent-123")
        assert limits1['max_context_window'] == 128000
        
        # Second call - should still call API (for current_tokens), but cache max_context_window
        limits2 = await token_limit_service.get_agent_token_limits("agent-123")
        assert limits2['max_context_window'] == 128000
        
        # Should be called twice (once per get_agent_token_limits call)
        assert mock_letta_client.agents.context.retrieve.call_count == 2
    
    @pytest.mark.asyncio
    async def test_get_agent_token_limits_api_error(self, token_limit_service, mock_letta_client):
        """Test handling when API fails"""
        mock_letta_client.agents.context.retrieve = AsyncMock(side_effect=Exception("API Error"))
        
        # Should return defaults when API fails
        limits = await token_limit_service.get_agent_token_limits("agent-123")
        
        assert limits['max_context_window'] == 0
        assert limits['current_tokens'] == 0
        assert limits['available_tokens'] == 0
    
    @pytest.mark.asyncio
    async def test_calculate_optimal_max_tokens(self, token_limit_service, mock_letta_client):
        """Test calculating optimal max_tokens"""
        # Mock context response
        mock_context = MagicMock()
        mock_context.model_dump.return_value = {
            'context_window_size_current': 1000,
            'context_window_size_max': 128000
        }
        mock_letta_client.agents.context.retrieve = AsyncMock(return_value=mock_context)
        
        # available = 128000 - 1000 = 127000
        # optimal = 127000 - 500 (request) - 100 (safety) = 126400
        optimal = await token_limit_service.calculate_optimal_max_tokens(
            agent_id="agent-123",
            request_tokens=500,
            safety_margin=100
        )
        
        assert optimal == 126400
        assert optimal <= 128000  # Never exceeds max
    
    @pytest.mark.asyncio
    async def test_calculate_optimal_max_tokens_minimum_threshold(self, token_limit_service, mock_letta_client):
        """Test minimum threshold for calculated max_tokens"""
        # Mock context response - nearly full
        mock_context = MagicMock()
        mock_context.model_dump.return_value = {
            'context_window_size_current': 127900,
            'context_window_size_max': 128000
        }
        mock_letta_client.agents.context.retrieve = AsyncMock(return_value=mock_context)
        
        # available = 100, request = 50, safety = 100
        # optimal = 100 - 50 - 100 = -50 -> 0, but minimum is 50
        # Since available (100) >= minimum (50), use minimum
        optimal = await token_limit_service.calculate_optimal_max_tokens(
            agent_id="agent-123",
            request_tokens=50,
            safety_margin=100,
            minimum_max_tokens=50
        )
        
        assert optimal == 50  # Minimum threshold applied
    
    @pytest.mark.asyncio
    async def test_calculate_optimal_max_tokens_insufficient_capacity(self, token_limit_service, mock_letta_client):
        """Test when there's insufficient capacity even for minimum"""
        # Mock context response - very little available
        mock_context = MagicMock()
        mock_context.model_dump.return_value = {
            'context_window_size_current': 127950,
            'context_window_size_max': 128000
        }
        mock_letta_client.agents.context.retrieve = AsyncMock(return_value=mock_context)
        
        # available = 50, request = 10, safety = 100
        # optimal = 50 - 10 - 100 = -60 -> 0
        # Not enough for minimum (50), so use what we have: 50 - 10 = 40
        optimal = await token_limit_service.calculate_optimal_max_tokens(
            agent_id="agent-123",
            request_tokens=10,
            safety_margin=100,
            minimum_max_tokens=50
        )
        
        assert optimal == 40  # What's available minus request
    
    @pytest.mark.asyncio
    async def test_calculate_optimal_max_tokens_exceeds_available(self, token_limit_service, mock_letta_client):
        """Test when request_tokens exceeds available"""
        # Mock context response
        mock_context = MagicMock()
        mock_context.model_dump.return_value = {
            'context_window_size_current': 1000,
            'context_window_size_max': 128000
        }
        mock_letta_client.agents.context.retrieve = AsyncMock(return_value=mock_context)
        
        # available = 127000, request = 200000 (exceeds available)
        # optimal = max(0, 127000 - 200000 - 100) = 0
        optimal = await token_limit_service.calculate_optimal_max_tokens(
            agent_id="agent-123",
            request_tokens=200000,
            safety_margin=100
        )
        
        assert optimal == 0  # Can't be negative
    
    def test_invalidate_cache(self, token_limit_service):
        """Test cache invalidation"""
        # Set up cache
        token_limit_service._cache = {
            'agent-123': {'max_context_window': 128000, 'cached_at': 1000},
            'agent-456': {'max_context_window': 8192, 'cached_at': 1000}
        }
        
        # Invalidate specific agent
        token_limit_service.invalidate_cache('agent-123')
        
        assert 'agent-123' not in token_limit_service._cache
        assert 'agent-456' in token_limit_service._cache
        
        # Invalidate all
        token_limit_service.invalidate_cache()
        assert len(token_limit_service._cache) == 0


