"""
Agent Configuration Manager for The Librarian

Manages agent configuration lifecycle with automatic restoration via context managers.

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
from typing import Dict, Optional
from contextlib import asynccontextmanager

from letta_client import AsyncLetta, LlmConfig

logger = logging.getLogger(__name__)


class AgentConfigContext:
    """Async context manager for temporary agent configuration"""
    
    def __init__(
        self,
        manager: "AgentConfigManager",
        agent_id: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ):
        """
        Initialize context manager.
        
        Args:
            manager: AgentConfigManager instance
            agent_id: Letta agent ID
            temperature: Temperature to set (None to leave unchanged)
            max_tokens: Max tokens to set (None to leave unchanged)
        """
        self.manager = manager
        self.agent_id = agent_id
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.original_config: Optional[LlmConfig] = None
        self._lock_acquired = False
    
    async def __aenter__(self) -> "AgentConfigContext":
        """Enter context - configure agent"""
        if self.temperature is None and self.max_tokens is None:
            # No changes needed, skip configuration
            return self
        
        # Get or create lock for this agent
        async with self.manager.lock:
            if self.agent_id not in self.manager.agent_locks:
                self.manager.agent_locks[self.agent_id] = asyncio.Lock()
            agent_lock = self.manager.agent_locks[self.agent_id]
        
        # Acquire agent-specific lock (prevents concurrent modifications)
        await agent_lock.acquire()
        self._lock_acquired = True
        
        try:
            # Retrieve current agent state
            agent_state = await self.manager.letta_client.agents.retrieve(agent_id=self.agent_id)
            current_llm_config = agent_state.llm_config
            
            if current_llm_config is None:
                logger.warning(f"Agent {self.agent_id} has no llm_config, cannot configure")
                agent_lock.release()
                self._lock_acquired = False
                return self
            
            # Store original config for restoration
            self.original_config = current_llm_config
            
            # Create new config with updated values
            config_dict = current_llm_config.model_dump()
            if self.temperature is not None:
                config_dict['temperature'] = self.temperature
                logger.info(f"Setting temperature to {self.temperature} for agent {self.agent_id}")
            if self.max_tokens is not None:
                config_dict['max_tokens'] = self.max_tokens
                logger.info(f"Setting max_tokens to {self.max_tokens} for agent {self.agent_id}")
            
            # Create new LlmConfig with updated values
            new_llm_config = LlmConfig(**config_dict)
            
            # Modify agent
            await self.manager.letta_client.agents.modify(
                agent_id=self.agent_id,
                llm_config=new_llm_config
            )
            
            logger.info(f"Successfully configured agent {self.agent_id} for request")
            return self
            
        except Exception as e:
            # If configuration fails, release lock and return
            logger.error(f"Failed to configure agent {self.agent_id}: {str(e)}")
            if self._lock_acquired:
                agent_lock.release()
                self._lock_acquired = False
            self.original_config = None
            return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit context - restore agent config"""
        if self.original_config is None:
            return False  # No config was changed, nothing to restore
        
        # Get the lock for this agent
        async with self.manager.lock:
            if self.agent_id not in self.manager.agent_locks:
                # Lock was released or never created, can't restore safely
                logger.warning(f"Agent lock not found for {self.agent_id}, skipping restoration")
                return False
            agent_lock = self.manager.agent_locks[self.agent_id]
        
        # Lock should already be held, but verify
        if not agent_lock.locked():
            logger.warning(f"Agent lock not held for {self.agent_id}, skipping restoration")
            return False
        
        try:
            # Restore original configuration
            await self.manager.letta_client.agents.modify(
                agent_id=self.agent_id,
                llm_config=self.original_config
            )
            logger.info(f"Successfully restored original config for agent {self.agent_id}")
        except Exception as e:
            logger.error(f"Failed to restore config for agent {self.agent_id}: {str(e)}")
        finally:
            # Always release the lock
            if agent_lock.locked():
                agent_lock.release()
            self._lock_acquired = False
        
        return False  # Don't suppress exceptions


class AgentConfigManager:
    """Manages agent configuration lifecycle with thread-safe operations"""
    
    def __init__(self, letta_client: AsyncLetta):
        """
        Initialize agent configuration manager.
        
        Args:
            letta_client: AsyncLetta client instance
        """
        self.letta_client = letta_client
        self.agent_locks: Dict[str, asyncio.Lock] = {}
        self.lock = asyncio.Lock()  # For managing agent_locks dict
        
        logger.info("AgentConfigManager initialized")
    
    @asynccontextmanager
    async def temporary_config(
        self,
        agent_id: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ):
        """
        Context manager for temporary agent configuration.
        
        Automatically restores original configuration when exiting the context,
        even if an exception occurs.
        
        Args:
            agent_id: Letta agent ID
            temperature: Temperature to set (None to leave unchanged)
            max_tokens: Max tokens to set (None to leave unchanged)
        
        Yields:
            AgentConfigContext instance
        
        Example:
            async with agent_config_manager.temporary_config(agent_id, temperature=0.7):
                # Agent has temperature=0.7
                await make_request()
            # Agent config automatically restored
        """
        context = AgentConfigContext(self, agent_id, temperature, max_tokens)
        async with context:
            yield context

