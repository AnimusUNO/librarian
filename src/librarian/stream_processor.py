"""
Stream Processor for The Librarian

Shared logic for processing Letta streams in both streaming and non-streaming modes.

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
from typing import AsyncGenerator, Optional, Callable, Any, Dict
from letta_client import AsyncLetta
from letta_client.types import MessageCreate

from src.librarian.response_formatter import ResponseFormatter

logger = logging.getLogger(__name__)


class StreamProcessor:
    """Shared stream processing logic for streaming and non-streaming handlers"""
    
    def __init__(self, letta_client: AsyncLetta, response_formatter: ResponseFormatter):
        """
        Initialize stream processor.
        
        Args:
            letta_client: Letta client instance
            response_formatter: Response formatter instance
        """
        self.letta_client = letta_client
        self.response_formatter = response_formatter
    
    async def create_stream(
        self,
        agent_id: str,
        message_objects: list
    ) -> AsyncGenerator:
        """
        Create stream from Letta.
        
        Args:
            agent_id: Agent ID
            message_objects: List of message objects
            
        Returns:
            AsyncGenerator of chunks
        """
        return self.letta_client.agents.messages.create_stream(
            agent_id=agent_id,
            messages=message_objects,
            stream_tokens=True
        )
    
    def detect_event_type(self, chunk: Any) -> Optional[str]:
        """
        Detect event type from chunk.
        
        Args:
            chunk: Chunk from Letta stream
            
        Returns:
            Event type string or None
        """
        # Check message_type attribute
        if hasattr(chunk, 'message_type') and isinstance(chunk.message_type, str):
            return chunk.message_type
        
        # Check for tool_call
        if hasattr(chunk, 'tool_call'):
            return 'tool_call_message'
        
        # Check for content
        if hasattr(chunk, 'content'):
            return 'assistant_message'
        
        return None
    
    def extract_chunk_content(self, chunk: Any) -> str:
        """
        Extract content from chunk.
        
        Args:
            chunk: Chunk from Letta stream
            
        Returns:
            Extracted content string
        """
        return self.response_formatter._extract_content(chunk)
    
    def extract_chunk_content_detailed(self, chunk: Any) -> str:
        """
        Extract content from chunk with detailed handling for assistant_message type.
        
        Args:
            chunk: Chunk from Letta stream
            
        Returns:
            Extracted content string
        """
        event_type = self.detect_event_type(chunk)
        
        if event_type == 'assistant_message':
            content = getattr(chunk, 'content', '') or ""
            if isinstance(content, list):
                return "".join(item.text for item in content if hasattr(item, 'text'))
            elif isinstance(content, str):
                return content
        
        # Fall back to standard extraction
        return self.extract_chunk_content(chunk)
    
    async def process_chunks(
        self,
        stream: AsyncGenerator,
        on_chunk: Callable[[str, str], None],
        on_error: Callable[[Exception], bool],
        on_stop: Callable[[], None]
    ) -> Dict[str, Any]:
        """
        Process stream chunks with callbacks.
        
        Args:
            stream: Stream to process
            on_chunk: Callback for each content chunk (content, event_type)
            on_error: Callback for errors (returns True if should retry)
            on_stop: Callback for normal stop
            
        Returns:
            Dict with 'content' and 'chunk_count'
        """
        full_content = ""
        chunk_count = 0
        
        async for chunk in stream:
            chunk_count += 1
            logger.debug(f"Stream chunk {chunk_count}: type={type(chunk).__name__}")
            
            event_type = self.detect_event_type(chunk)
            logger.debug(f"  Final event_type: {event_type}")
            
            # Handle different event types
            if event_type == 'error':
                error_msg = getattr(chunk, 'error', 'Unknown error')
                error_exception = Exception(error_msg)
                if on_error(error_exception):
                    # Should retry, break out of loop
                    break
                # Error handled, continue
                continue
            
            elif event_type == 'stop_reason':
                stop_reason = getattr(chunk, 'stop_reason', None)
                if stop_reason == 'error':
                    error_msg = getattr(chunk, 'error', 'Unknown error')
                    error_exception = Exception(error_msg)
                    if on_error(error_exception):
                        # Should retry, break out of loop
                        break
                    # Error handled, continue
                    continue
                else:
                    # Normal stop
                    on_stop()
                    break
            
            elif event_type == 'assistant_message':
                content = self.extract_chunk_content_detailed(chunk)
                if content:
                    full_content += content
                    on_chunk(content, event_type)
            
            elif event_type == 'reasoning_message':
                # Skip reasoning messages
                continue
            
            else:
                # Fallback: try to extract content
                content = self.extract_chunk_content(chunk)
                if content:
                    full_content += content
                    on_chunk(content, event_type)
        
        return {
            'content': full_content,
            'chunk_count': chunk_count
        }

