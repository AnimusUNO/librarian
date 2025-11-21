"""
Load Manager for The Librarian

Handles buffered request queue and auto-duplication for high concurrency.
Fully configurable via environment variables.

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

import asyncio
import logging
import time
import os
from typing import Dict, List, Optional, Any, Callable, Awaitable
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class RequestStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class RequestItem:
    """Represents a request in the queue"""
    request_id: str
    agent_id: str
    messages: List[Dict[str, Any]]
    user_id: Optional[str]
    timestamp: float
    status: RequestStatus = RequestStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None


class LoadManager:
    """Manages request load and auto-duplication"""
    
    def __init__(
        self,
        max_concurrent: int = 10,
        duplication_threshold: int = 8,
        queue_timeout: int = 300,
        cleanup_interval: int = 60,
        enable_auto_duplication: bool = True,
        max_clones_per_agent: int = 3
    ):
        """
        Initialize load manager.
        
        Args:
            max_concurrent: Maximum concurrent requests
            duplication_threshold: Queue threshold for auto-duplication
            queue_timeout: Queue timeout in seconds
            cleanup_interval: Cleanup interval in seconds
            enable_auto_duplication: Enable auto-duplication
            max_clones_per_agent: Maximum clones per agent
        """
        self.max_concurrent = max_concurrent
        self.duplication_threshold = duplication_threshold
        self.queue_timeout = queue_timeout
        self.cleanup_interval = cleanup_interval
        self.enable_auto_duplication = enable_auto_duplication
        self.max_clones_per_agent = max_clones_per_agent
        
        # Initialize state
        self.request_queue: List[RequestItem] = []
        self.active_requests: Dict[str, RequestItem] = {}
        self.agent_clones: Dict[str, List[str]] = {}  # agent_id -> list of clone_ids
        self.request_lock = asyncio.Lock()
        
        # Semaphore for concurrency control
        self.processing_semaphore = asyncio.Semaphore(self.max_concurrent)
        
        logger.info(f"LoadManager initialized: max_concurrent={self.max_concurrent}, "
                   f"duplication_threshold={self.duplication_threshold}, "
                   f"auto_duplication={self.enable_auto_duplication}")
        
    async def queue_request(
        self, 
        agent_id: str, 
        messages: List[Dict[str, Any]], 
        user_id: Optional[str] = None
    ) -> str:
        """
        Queue a request for processing
        
        Args:
            agent_id: Target agent ID
            messages: Message list
            user_id: Optional user ID
            
        Returns:
            Request ID
        """
        request_id = f"req_{int(time.time() * 1000)}_{len(self.request_queue)}"
        
        request_item = RequestItem(
            request_id=request_id,
            agent_id=agent_id,
            messages=messages,
            user_id=user_id,
            timestamp=time.time()
        )
        
        async with self.request_lock:
            self.request_queue.append(request_item)
            
        logger.info(f"Queued request {request_id} for agent {agent_id}")
        
        # Check if we need to spawn clones
        await self._check_load_and_spawn_clones()
        
        return request_id
    
    async def _check_load_and_spawn_clones(self) -> None:
        """Check load and spawn agent clones if needed"""
        active_count = len(self.active_requests)
        queue_count = len(self.request_queue)
        
        if active_count >= self.duplication_threshold:
            # Find the most loaded agent
            agent_loads = {}
            for request in self.active_requests.values():
                agent_loads[request.agent_id] = agent_loads.get(request.agent_id, 0) + 1
            
            # Spawn clones for overloaded agents
            for agent_id, load in agent_loads.items():
                if load >= self.duplication_threshold // 2:  # Half the threshold per agent
                    await self._spawn_agent_clone(agent_id)
    
    async def _spawn_agent_clone(self, agent_id: str) -> None:
        """Spawn a temporary agent clone"""
        try:
            # This would integrate with Letta's agent duplication API
            # For now, we'll simulate it
            clone_id = f"{agent_id}_clone_{int(time.time())}"
            
            if agent_id not in self.agent_clones:
                self.agent_clones[agent_id] = []
            
            self.agent_clones[agent_id].append(clone_id)
            
            logger.info(f"Spawned clone {clone_id} for agent {agent_id}")
            
            # TODO: Implement actual agent cloning via Letta API
            # await letta_client.agents.clone(agent_id, clone_id)
            
        except Exception as e:
            logger.error(f"Error spawning agent clone: {str(e)}")
    
    async def process_request(
        self, 
        request_id: str, 
        processor: Callable[[], Awaitable[Any]]
    ) -> Optional[Any]:
        """
        Process a queued request with concurrency control
        
        Args:
            request_id: Request ID to process
            processor: Async callable that performs the actual processing
            
        Returns:
            Request result or None if not found/failed
        """
        # Acquire semaphore (waits if at max_concurrent)
        await self.processing_semaphore.acquire()
        
        async with self.request_lock:
            # Find the request
            request_item = None
            for req in self.request_queue:
                if req.request_id == request_id:
                    request_item = req
                    break
            
            if not request_item:
                logger.error(f"Request {request_id} not found in queue")
                self.processing_semaphore.release()
                return None
            
            # Move to active processing
            request_item.status = RequestStatus.PROCESSING
            self.active_requests[request_id] = request_item
            self.request_queue.remove(request_item)
        
        try:
            logger.info(f"Processing request {request_id} (active: {len(self.active_requests)})")
            
            # Call the actual processor function
            result = await processor()
            
            # Mark as completed
            request_item.status = RequestStatus.COMPLETED
            request_item.result = result
            
            logger.info(f"Completed processing request {request_id}")
            
            return result
            
        except Exception as e:
            # Mark as failed
            request_item.status = RequestStatus.FAILED
            request_item.error = str(e)
            
            logger.error(f"Error processing request {request_id}: {str(e)}")
            raise  # Re-raise to let caller handle
            
        finally:
            # Remove from active requests and release semaphore
            async with self.request_lock:
                if request_id in self.active_requests:
                    del self.active_requests[request_id]
            self.processing_semaphore.release()
    
    async def process_with_queue(
        self,
        agent_id: str,
        messages: List[Dict[str, Any]],
        processor: Callable[[], Awaitable[Any]],
        user_id: Optional[str] = None
    ) -> Any:
        """
        Queue a request and process it with concurrency control.
        This is the main entry point for request processing.
        
        Args:
            agent_id: Target agent ID
            messages: Message list
            processor: Async callable that performs the actual processing
            user_id: Optional user ID
            
        Returns:
            Result from processor
        """
        # Queue the request
        request_id = await self.queue_request(agent_id, messages, user_id)
        
        # Process it (will wait for semaphore if needed)
        return await self.process_request(request_id, processor)
    
    async def get_request_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a request"""
        async with self.request_lock:
            # Check active requests
            if request_id in self.active_requests:
                req = self.active_requests[request_id]
                return {
                    "request_id": req.request_id,
                    "status": req.status.value,
                    "timestamp": req.timestamp,
                    "result": req.result,
                    "error": req.error
                }
            
            # Check queue
            for req in self.request_queue:
                if req.request_id == request_id:
                    return {
                        "request_id": req.request_id,
                        "status": req.status.value,
                        "timestamp": req.timestamp,
                        "queue_position": self.request_queue.index(req)
                    }
        
        return None
    
    async def cleanup_completed_requests(self) -> None:
        """Clean up completed requests"""
        async with self.request_lock:
            completed_requests = [
                req_id for req_id, req in self.active_requests.items()
                if req.status in [RequestStatus.COMPLETED, RequestStatus.FAILED]
            ]
            
            for req_id in completed_requests:
                del self.active_requests[req_id]
            
            if completed_requests:
                logger.info(f"Cleaned up {len(completed_requests)} completed requests")
    
    def get_load_stats(self) -> Dict[str, int]:
        """Get current load statistics"""
        return {
            "queue_size": len(self.request_queue),
            "active_requests": len(self.active_requests),
            "total_clones": sum(len(clones) for clones in self.agent_clones.values()),
            "max_concurrent": self.max_concurrent
        }
