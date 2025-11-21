#!/usr/bin/env python3
"""
Test suite for ToolSynchronizer

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
from unittest.mock import AsyncMock, Mock
from src.librarian.tool_synchronizer import ToolSynchronizer


class TestToolSynchronizer:
    """Test ToolSynchronizer class"""
    
    @pytest.fixture
    def mock_letta_client(self):
        """Create a mock Letta client"""
        client = AsyncMock()
        return client
    
    @pytest.fixture
    def synchronizer(self, mock_letta_client):
        """Create ToolSynchronizer instance"""
        return ToolSynchronizer(mock_letta_client)
    
    @pytest.mark.asyncio
    async def test_init(self, synchronizer):
        """Test ToolSynchronizer initialization"""
        assert synchronizer is not None
        assert synchronizer.synced_tools == {}
    
    @pytest.mark.asyncio
    async def test_sync_tools_basic(self, synchronizer, mock_letta_client):
        """Test basic tool synchronization"""
        # Mock tool list (empty - tool doesn't exist)
        mock_letta_client.tools.list.return_value = []
        mock_letta_client.tools.create.return_value = None
        mock_letta_client.agents.tools.attach.return_value = None
        
        openai_tools = [
            {
                "type": "function",
                "function": {
                    "name": "test_tool",
                    "description": "Test tool",
                    "parameters": {"type": "object", "properties": {}}
                }
            }
        ]
        
        result = await synchronizer.sync_tools("test-agent", openai_tools)
        assert result is True
        mock_letta_client.tools.create.assert_called_once()
        mock_letta_client.agents.tools.attach.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_sync_tools_existing_tool(self, synchronizer, mock_letta_client):
        """Test syncing when tool already exists"""
        # Mock existing tool
        mock_tool = Mock()
        mock_tool.name = "test_tool"
        mock_letta_client.tools.list.return_value = [mock_tool]
        mock_letta_client.agents.tools.attach.return_value = None
        
        openai_tools = [
            {
                "type": "function",
                "function": {
                    "name": "test_tool",
                    "description": "Test tool"
                }
            }
        ]
        
        result = await synchronizer.sync_tools("test-agent", openai_tools)
        assert result is True
        # Should not create tool, just attach
        mock_letta_client.tools.create.assert_not_called()
        mock_letta_client.agents.tools.attach.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_sync_tools_multiple(self, synchronizer, mock_letta_client):
        """Test syncing multiple tools"""
        mock_letta_client.tools.list.return_value = []
        mock_letta_client.tools.create.return_value = None
        mock_letta_client.agents.tools.attach.return_value = None
        
        openai_tools = [
            {"type": "function", "function": {"name": "tool1", "description": "Tool 1"}},
            {"type": "function", "function": {"name": "tool2", "description": "Tool 2"}}
        ]
        
        result = await synchronizer.sync_tools("test-agent", openai_tools)
        assert result is True
        assert mock_letta_client.tools.create.call_count == 2
        assert mock_letta_client.agents.tools.attach.call_count == 2
    
    @pytest.mark.asyncio
    async def test_sync_tools_non_function(self, synchronizer, mock_letta_client):
        """Test syncing tools with non-function types"""
        openai_tools = [
            {"type": "code_interpreter", "name": "code_tool"}
        ]
        
        result = await synchronizer.sync_tools("test-agent", openai_tools)
        assert result is True
        # Should not sync non-function tools
        mock_letta_client.tools.create.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_sync_tools_error(self, synchronizer, mock_letta_client):
        """Test handling errors during sync"""
        mock_letta_client.tools.list.side_effect = Exception("Connection error")
        
        openai_tools = [
            {"type": "function", "function": {"name": "test_tool"}}
        ]
        
        result = await synchronizer.sync_tools("test-agent", openai_tools)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_detach_tools(self, synchronizer, mock_letta_client):
        """Test detaching tools"""
        mock_letta_client.agents.tools.detach.return_value = None
        
        await synchronizer.detach_tools("test-agent", ["tool1", "tool2"])
        
        assert mock_letta_client.agents.tools.detach.call_count == 2
    
    @pytest.mark.asyncio
    async def test_detach_tools_error(self, synchronizer, mock_letta_client):
        """Test handling errors during detach"""
        mock_letta_client.agents.tools.detach.side_effect = Exception("Error")
        
        # Should not raise, just log error
        await synchronizer.detach_tools("test-agent", ["tool1"])
    
    def test_get_synced_tools(self, synchronizer):
        """Test getting synced tools for an agent"""
        synchronizer.synced_tools = {
            "tool1": {"name": "tool1", "agent_id": "agent1"},
            "tool2": {"name": "tool2", "agent_id": "agent1"},
            "tool3": {"name": "tool3", "agent_id": "agent2"}
        }
        
        tools = synchronizer.get_synced_tools("agent1")
        assert len(tools) == 2
        assert all(tool["agent_id"] == "agent1" for tool in tools)
    
    def test_clear_cache(self, synchronizer):
        """Test clearing tool cache"""
        synchronizer.synced_tools = {"tool1": {}, "tool2": {}}
        synchronizer.clear_cache()
        assert synchronizer.synced_tools == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
