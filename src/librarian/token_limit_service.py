"""
Token Limit Service for The Librarian

Manages token limits using Letta API as source of truth.
Eliminates static hardcoded token limits.

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

import time
import logging
from typing import Dict, Optional
from letta_client import AsyncLetta

logger = logging.getLogger(__name__)


class TokenLimitService:
    """Manages token limits using Letta API as source of truth"""
    
    def __init__(self, letta_client: AsyncLetta, cache_ttl: int = 300):
        """
        Initialize token limit service.
        
        Args:
            letta_client: AsyncLetta client instance
            cache_ttl: Cache TTL in seconds for max_context_window (default: 300 = 5 minutes)
        """
        self.letta_client = letta_client
        self.cache_ttl = cache_ttl
        # Cache structure: {agent_id: {'max_context_window': int, 'cached_at': float}}
        self._cache: Dict[str, Dict] = {}
    
    async def get_agent_token_limits(self, agent_id: str) -> Dict[str, int]:
        """
        Get token limits for an agent from Letta API.
        
        Caches max_context_window per agent (TTL: 5 minutes).
        Always fetches current_tokens fresh (changes frequently).
        
        Args:
            agent_id: Letta agent ID
            
        Returns:
            {
                'max_context_window': int,  # Model's absolute maximum
                'current_tokens': int,       # Current usage
                'available_tokens': int,     # Available capacity
            }
        """
        try:
            # Get current context from Letta
            context = await self.letta_client.agents.context.retrieve(agent_id=agent_id)
            context_dict = context.model_dump()
            
            # Get current usage (always fresh)
            current_tokens = context_dict.get('context_window_size_current', 0)
            
            # Get max window size (use cache if available and not expired)
            max_context_window = self._get_max_context_window(agent_id, context_dict)
            
            available_tokens = max_context_window - current_tokens
            
            return {
                'max_context_window': max_context_window,
                'current_tokens': current_tokens,
                'available_tokens': available_tokens
            }
        except Exception as e:
            logger.warning(f"Failed to get token limits for agent {agent_id}: {e}")
            # If we have cached max_context_window, use it with current_tokens=0
            # This allows the system to continue operating even if API is temporarily unavailable
            cached_max = self._get_cached_max_context_window(agent_id)
            if cached_max:
                logger.info(f"Using cached max_context_window ({cached_max:,}) for agent {agent_id}")
                return {
                    'max_context_window': cached_max,
                    'current_tokens': 0,  # Unknown, assume 0
                    'available_tokens': cached_max  # Conservative estimate
                }
            # No cache available, return defaults
            return {
                'max_context_window': 0,
                'current_tokens': 0,
                'available_tokens': 0
            }
    
    def _get_max_context_window(self, agent_id: str, context_dict: Dict) -> int:
        """
        Get max_context_window, using cache if available and not expired.
        
        Args:
            agent_id: Letta agent ID
            context_dict: Context dict from Letta API
            
        Returns:
            max_context_window value
        """
        max_context_window = context_dict.get('context_window_size_max', 0)
        
        # Check if we have a valid cached value
        cached = self._get_cached_max_context_window(agent_id)
        if cached and cached == max_context_window:
            # Cache is still valid and matches current value
            return cached
        
        # Update cache with new value
        if max_context_window > 0:
            self._cache[agent_id] = {
                'max_context_window': max_context_window,
                'cached_at': time.time()
            }
            logger.debug(f"Cached max_context_window for agent {agent_id}: {max_context_window:,}")
        
        return max_context_window
    
    def _get_cached_max_context_window(self, agent_id: str) -> Optional[int]:
        """
        Get cached max_context_window if available and not expired.
        
        Args:
            agent_id: Letta agent ID
            
        Returns:
            Cached max_context_window or None if not available/expired
        """
        if agent_id not in self._cache:
            return None
        
        cached_data = self._cache[agent_id]
        cached_at = cached_data.get('cached_at', 0)
        
        # Check if cache is expired
        if time.time() - cached_at > self.cache_ttl:
            # Cache expired, remove it
            del self._cache[agent_id]
            return None
        
        return cached_data.get('max_context_window')
    
    async def calculate_optimal_max_tokens(
        self,
        agent_id: str,
        request_tokens: int,
        safety_margin: int = 100,
        minimum_max_tokens: int = 50
    ) -> int:
        """
        Calculate optimal max_tokens when user doesn't specify.
        
        Formula:
            available = max_context_window - current_tokens
            optimal = available - request_tokens - safety_margin
        
        Note: request_tokens is estimated BEFORE the request is sent,
        so it's NOT yet in current_tokens. Therefore we subtract it.
        
        Args:
            agent_id: Letta agent ID
            request_tokens: Estimated tokens for the prompt (NOT yet in current_tokens)
            safety_margin: Safety buffer (default: 100 tokens)
            minimum_max_tokens: Minimum threshold for calculated max_tokens (default: 50)
        
        Returns:
            Optimal max_tokens value (never exceeds max_context_window, minimum 50)
        """
        limits = await self.get_agent_token_limits(agent_id)
        available = limits['available_tokens']
        max_context_window = limits['max_context_window']
        
        # Calculate optimal: available - request - safety margin
        # Note: request_tokens is NOT yet in current_tokens, so we subtract it
        optimal = max(0, available - request_tokens - safety_margin)
        
        # Never exceed model's absolute maximum
        optimal = min(optimal, max_context_window)
        
        # Apply minimum threshold only if we have enough capacity
        if optimal < minimum_max_tokens:
            # Check if we have enough available capacity for minimum
            # Need: request_tokens + minimum_max_tokens + safety_margin
            total_needed_for_minimum = request_tokens + minimum_max_tokens + safety_margin
            if available >= total_needed_for_minimum:
                # We have space for minimum, use it
                optimal = minimum_max_tokens
                logger.warning(
                    f"Calculated optimal max_tokens was below minimum ({minimum_max_tokens}), "
                    f"using minimum for agent {agent_id}"
                )
            else:
                # Not enough space even for minimum, use what we can (available - request)
                optimal = max(0, available - request_tokens)
                logger.warning(
                    f"Insufficient capacity for minimum max_tokens ({minimum_max_tokens}) "
                    f"for agent {agent_id}, using {optimal:,}"
                )
        
        return optimal
    
    def invalidate_cache(self, agent_id: Optional[str] = None):
        """
        Invalidate cache for an agent or all agents.
        
        Args:
            agent_id: Agent ID to invalidate (None = invalidate all)
        """
        if agent_id is None:
            self._cache.clear()
            logger.debug("Invalidated all token limit caches")
        elif agent_id in self._cache:
            del self._cache[agent_id]
            logger.debug(f"Invalidated token limit cache for agent {agent_id}")

