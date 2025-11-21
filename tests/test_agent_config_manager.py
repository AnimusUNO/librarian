#!/usr/bin/env python3
"""
Test suite for AgentConfigManager

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
import asyncio
from unittest.mock import AsyncMock, Mock, MagicMock
from letta_client import LlmConfig

from src.librarian.agent_config_manager import AgentConfigManager, AgentConfigContext


class TestAgentConfigManager:
    """Test AgentConfigManager class"""
    
    @pytest.fixture
    def mock_letta_client(self):
        """Create a mock Letta client"""
        client = AsyncMock()
        return client
    
    @pytest.fixture
    def manager(self, mock_letta_client):
        """Create AgentConfigManager instance"""
        return AgentConfigManager(mock_letta_client)
    
    @pytest.mark.asyncio
    async def test_context_manager_no_changes(self, manager):
        """Test context manager with no config changes"""
        agent_id = "test-agent"
        
        async with manager.temporary_config(agent_id):
            # Should not call any Letta methods
            pass
        
        # Verify no calls were made
        manager.letta_client.agents.retrieve.assert_not_called()
        manager.letta_client.agents.modify.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_context_manager_with_temperature(self, manager, mock_letta_client):
        """Test context manager with temperature change"""
        agent_id = "test-agent"
        # Create a minimal LlmConfig with required fields
        original_config = LlmConfig(
            model="gpt-4",
            model_endpoint_type="openai",
            context_window=8192,
            temperature=0.7,
            max_tokens=1000
        )
        
        # Mock agent state
        mock_agent_state = Mock()
        mock_agent_state.llm_config = original_config
        mock_letta_client.agents.retrieve.return_value = mock_agent_state
        mock_letta_client.agents.modify.return_value = None
        
        async with manager.temporary_config(agent_id, temperature=0.9):
            # Config should be changed
            pass
        
        # Verify config was changed and restored
        assert mock_letta_client.agents.retrieve.call_count == 1
        assert mock_letta_client.agents.modify.call_count == 2  # Change + restore
        
        # Check that modify was called with new config
        modify_calls = mock_letta_client.agents.modify.call_args_list
        assert modify_calls[0][1]['llm_config'].temperature == 0.9
        assert modify_calls[1][1]['llm_config'].temperature == 0.7
    
    @pytest.mark.asyncio
    async def test_context_manager_with_max_tokens(self, manager, mock_letta_client):
        """Test context manager with max_tokens change"""
        agent_id = "test-agent"
        original_config = LlmConfig(
            model="gpt-4",
            model_endpoint_type="openai",
            context_window=8192,
            temperature=0.7,
            max_tokens=1000
        )
        
        # Mock agent state
        mock_agent_state = Mock()
        mock_agent_state.llm_config = original_config
        mock_letta_client.agents.retrieve.return_value = mock_agent_state
        mock_letta_client.agents.modify.return_value = None
        
        async with manager.temporary_config(agent_id, max_tokens=2000):
            # Config should be changed
            pass
        
        # Verify config was changed and restored
        assert mock_letta_client.agents.modify.call_count == 2
        
        # Check that modify was called with new config
        modify_calls = mock_letta_client.agents.modify.call_args_list
        assert modify_calls[0][1]['llm_config'].max_tokens == 2000
        assert modify_calls[1][1]['llm_config'].max_tokens == 1000
    
    @pytest.mark.asyncio
    async def test_context_manager_restores_on_exception(self, manager, mock_letta_client):
        """Test that config is restored even when exception occurs"""
        agent_id = "test-agent"
        original_config = LlmConfig(
            model="gpt-4",
            model_endpoint_type="openai",
            context_window=8192,
            temperature=0.7,
            max_tokens=1000
        )
        
        # Mock agent state
        mock_agent_state = Mock()
        mock_agent_state.llm_config = original_config
        mock_letta_client.agents.retrieve.return_value = mock_agent_state
        mock_letta_client.agents.modify.return_value = None
        
        try:
            async with manager.temporary_config(agent_id, temperature=0.9):
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        # Verify config was restored despite exception
        assert mock_letta_client.agents.modify.call_count == 2
        modify_calls = mock_letta_client.agents.modify.call_args_list
        assert modify_calls[1][1]['llm_config'].temperature == 0.7
    
    @pytest.mark.asyncio
    async def test_context_manager_no_llm_config(self, manager, mock_letta_client):
        """Test context manager when agent has no llm_config"""
        agent_id = "test-agent"
        
        # Mock agent state with no llm_config
        mock_agent_state = Mock()
        mock_agent_state.llm_config = None
        mock_letta_client.agents.retrieve.return_value = mock_agent_state
        
        async with manager.temporary_config(agent_id, temperature=0.9):
            # Should not raise, just skip configuration
            pass
        
        # Verify retrieve was called but modify was not
        assert mock_letta_client.agents.retrieve.call_count == 1
        assert mock_letta_client.agents.modify.call_count == 0
    
    @pytest.mark.asyncio
    async def test_concurrent_requests_same_agent(self, manager, mock_letta_client):
        """Test that concurrent requests to same agent are handled safely"""
        agent_id = "test-agent"
        original_config = LlmConfig(
            model="gpt-4",
            model_endpoint_type="openai",
            context_window=8192,
            temperature=0.7,
            max_tokens=1000
        )
        
        # Mock agent state
        mock_agent_state = Mock()
        mock_agent_state.llm_config = original_config
        mock_letta_client.agents.retrieve.return_value = mock_agent_state
        mock_letta_client.agents.modify.return_value = None
        
        async def use_config(temp):
            async with manager.temporary_config(agent_id, temperature=temp):
                await asyncio.sleep(0.01)  # Simulate work
        
        # Run two concurrent requests
        await asyncio.gather(
            use_config(0.8),
            use_config(0.9)
        )
        
        # Verify both completed (no deadlock)
        # Each should have 2 modify calls (change + restore)
        assert mock_letta_client.agents.modify.call_count == 4
    
    @pytest.mark.asyncio
    async def test_restore_failure_handled_gracefully(self, manager, mock_letta_client):
        """Test that restore failure is handled gracefully"""
        agent_id = "test-agent"
        original_config = LlmConfig(
            model="gpt-4",
            model_endpoint_type="openai",
            context_window=8192,
            temperature=0.7,
            max_tokens=1000
        )
        
        # Mock agent state
        mock_agent_state = Mock()
        mock_agent_state.llm_config = original_config
        mock_letta_client.agents.retrieve.return_value = mock_agent_state
        
        # First modify succeeds, second (restore) fails
        call_count = 0
        def modify_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:  # Restore call
                raise Exception("Restore failed")
            return None
        
        mock_letta_client.agents.modify.side_effect = modify_side_effect
        
        # Should not raise exception
        async with manager.temporary_config(agent_id, temperature=0.9):
            pass
        
        # Verify both calls were attempted
        assert mock_letta_client.agents.modify.call_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

