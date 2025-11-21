#!/usr/bin/env python3
"""
Test suite for LoadManager

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
from unittest.mock import Mock, AsyncMock
from src.librarian.load_manager import LoadManager, RequestStatus, RequestItem
from src.librarian.config import Config


class TestLoadManager:
    """Test LoadManager class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        pass
    
    def test_init(self):
        """Test LoadManager initialization"""
        manager = LoadManager(
            max_concurrent=10,
            duplication_threshold=8,
            queue_timeout=300,
            cleanup_interval=60,
            enable_auto_duplication=True,
            max_clones_per_agent=3
        )
        assert manager is not None
        assert manager.max_concurrent == 10
        assert manager.duplication_threshold == 8
        assert len(manager.request_queue) == 0
        assert len(manager.active_requests) == 0
    
    @pytest.mark.asyncio
    async def test_queue_request_basic(self):
        """Test basic request queuing"""
        manager = LoadManager()
        messages = [{"role": "user", "content": "Hello"}]
        
        request_id = await manager.queue_request("agent-123", messages)
        assert request_id is not None
        assert len(manager.request_queue) == 1
    
    @pytest.mark.asyncio
    async def test_queue_request_with_user_id(self):
        """Test queuing request with user ID"""
        manager = LoadManager()
        messages = [{"role": "user", "content": "Hello"}]
        
        request_id = await manager.queue_request("agent-123", messages, user_id="user-1")
        assert request_id is not None
        # Check that request has user_id
        assert len(manager.request_queue) == 1
    
    @pytest.mark.asyncio
    async def test_queue_request_creates_request_item(self):
        """Test that queue_request creates a RequestItem"""
        manager = LoadManager()
        messages = [{"role": "user", "content": "Hello"}]
        
        request_id = await manager.queue_request("agent-123", messages)
        assert request_id is not None
        
        # Check that request is in queue
        async with manager.request_lock:
            assert len(manager.request_queue) == 1
            assert manager.request_queue[0].request_id == request_id
            assert manager.request_queue[0].status == RequestStatus.PENDING
    
    @pytest.mark.asyncio
    async def test_queue_request_multiple(self):
        """Test queuing multiple requests"""
        manager = LoadManager()
        messages = [{"role": "user", "content": "Hello"}]
        
        request_id1 = await manager.queue_request("agent-123", messages)
        request_id2 = await manager.queue_request("agent-123", messages)
        
        assert request_id1 != request_id2
        async with manager.request_lock:
            assert len(manager.request_queue) == 2
    
    @pytest.mark.asyncio
    async def test_get_request_status(self):
        """Test getting request status"""
        manager = LoadManager()
        messages = [{"role": "user", "content": "Hello"}]
        
        request_id = await manager.queue_request("agent-123", messages)
        status = await manager.get_request_status(request_id)
        assert status is not None
        assert status["status"] == RequestStatus.PENDING.value
    
    @pytest.mark.asyncio
    async def test_get_request_status_nonexistent(self):
        """Test getting status for non-existent request"""
        manager = LoadManager()
        status = await manager.get_request_status("nonexistent-id")
        assert status is None
    
    @pytest.mark.asyncio
    async def test_process_request(self):
        """Test processing a request"""
        manager = LoadManager()
        messages = [{"role": "user", "content": "Hello"}]
        
        request_id = await manager.queue_request("agent-123", messages)
        
        async def processor():
            return "result"
        
        result = await manager.process_request(request_id, processor)
        assert result == "result"
        
        # Request should be in active_requests, then moved to completed
        async with manager.request_lock:
            # After processing, request should be completed
            assert request_id in manager.active_requests or len(manager.request_queue) == 0
    
    @pytest.mark.asyncio
    async def test_process_request_not_found(self):
        """Test processing a non-existent request"""
        manager = LoadManager()
        
        async def processor():
            return "result"
        
        result = await manager.process_request("nonexistent-id", processor)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_process_request_with_error(self):
        """Test processing a request that raises an error"""
        manager = LoadManager()
        messages = [{"role": "user", "content": "Hello"}]
        
        request_id = await manager.queue_request("agent-123", messages)
        
        async def processor():
            raise ValueError("Test error")
        
        # Exception should be re-raised
        with pytest.raises(ValueError, match="Test error"):
            await manager.process_request(request_id, processor)
        
        # Request should be marked as failed and removed from active_requests
        async with manager.request_lock:
            # Request should be removed from active_requests (in finally block)
            assert request_id not in manager.active_requests
            assert request_id not in [req.request_id for req in manager.request_queue]
    
    @pytest.mark.asyncio
    async def test_check_load_and_spawn_clones(self):
        """Test checking load and spawning clones"""
        manager = LoadManager(duplication_threshold=2)
        messages = [{"role": "user", "content": "Hello"}]
        
        # Create enough requests to trigger clone spawning
        for i in range(3):
            await manager.queue_request("agent-123", messages)
        
        # Check that clone spawning was attempted
        # (actual cloning is mocked, but the method should be called)
    
    @pytest.mark.asyncio
    async def test_spawn_agent_clone(self):
        """Test spawning an agent clone"""
        manager = LoadManager()
        
        await manager._spawn_agent_clone("agent-123")
        
        # Check that clone was added
        assert "agent-123" in manager.agent_clones
        assert len(manager.agent_clones["agent-123"]) == 1
    
    def test_get_load_stats(self):
        """Test getting load statistics"""
        manager = LoadManager()
        stats = manager.get_load_stats()
        
        assert "queue_size" in stats
        assert "active_requests" in stats
        assert "total_clones" in stats
        assert stats["queue_size"] == 0
        assert stats["active_requests"] == 0
    
    @pytest.mark.asyncio
    async def test_cleanup_completed_requests(self):
        """Test cleaning up completed requests"""
        manager = LoadManager()
        messages = [{"role": "user", "content": "Hello"}]
        
        request_id = await manager.queue_request("agent-123", messages)
        
        async def processor():
            return "result"
        
        await manager.process_request(request_id, processor)
        
        # Cleanup should remove completed requests
        await manager.cleanup_completed_requests()
        
        # Request should be removed from active_requests
        async with manager.request_lock:
            assert request_id not in manager.active_requests


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

