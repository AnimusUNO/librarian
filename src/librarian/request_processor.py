"""
Request Processor for The Librarian

Processes chat completion requests, handling all business logic
separate from HTTP concerns.

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
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from letta_client import AsyncLetta, MessageCreate
from letta_client.types import TextContent

logger = logging.getLogger(__name__)


@dataclass
class ProcessedRequest:
    """Processed chat completion request data"""
    agent_id: str
    agent_config: Dict[str, Any]
    model_name: str
    letta_messages: List[Dict[str, Any]]
    message_objects: List[MessageCreate]
    openai_messages: List[Dict[str, str]]
    system_content: str
    user_id: Optional[str]
    max_tokens: Optional[int]
    temperature: Optional[float]


class RequestProcessor:
    """Processes chat completion requests, handling all business logic"""
    
    def __init__(
        self,
        model_registry,
        message_translator,
        token_counter,
        tool_synchronizer,
        letta_client: AsyncLetta,
        check_token_capacity_func
    ):
        """
        Initialize request processor.
        
        Args:
            model_registry: ModelRegistry instance
            message_translator: MessageTranslator instance
            token_counter: TokenCounter instance
            tool_synchronizer: ToolSynchronizer instance
            letta_client: AsyncLetta client instance
            check_token_capacity_func: Function to check token capacity
        """
        self.model_registry = model_registry
        self.message_translator = message_translator
        self.token_counter = token_counter
        self.tool_synchronizer = tool_synchronizer
        self.letta_client = letta_client
        self.check_token_capacity = check_token_capacity_func
    
    async def process_request(
        self,
        request: Any,  # ChatCompletionRequest
        user_id: Optional[str] = None
    ) -> ProcessedRequest:
        """
        Process a chat completion request.
        
        Args:
            request: ChatCompletionRequest object
            user_id: Optional user ID from request
            
        Returns:
            ProcessedRequest with all processed data ready for handlers
            
        Raises:
            ValueError: If request is invalid (token capacity exceeded, etc.)
        """
        # Get agent configuration
        agent_config = self.model_registry.get_agent_config(request.model)
        agent_id = agent_config['agent_id']
        logger.info(f"Processing request for model {request.model} -> agent {agent_id}")
        
        # Prepare messages (translation, system content injection, token counting)
        letta_messages, system_content, estimated_tokens = await self.prepare_messages(
            request.messages,
            agent_config,
            request.model
        )
        
        # Validate token capacity
        is_valid, error_message = await self.validate_token_capacity(
            agent_id,
            estimated_tokens,
            request.max_tokens
        )
        if not is_valid:
            raise ValueError(error_message or "Request exceeds model's maximum token capacity")
        
        # Sync tools if provided
        if request.tools:
            await self.tool_synchronizer.sync_tools(agent_id, request.tools)
        
        # Convert to MessageCreate objects
        message_objects = self._build_message_objects(letta_messages)
        
        # Convert OpenAI messages to dict format
        openai_messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        
        return ProcessedRequest(
            agent_id=agent_id,
            agent_config=agent_config,
            model_name=request.model,
            letta_messages=letta_messages,
            message_objects=message_objects,
            openai_messages=openai_messages,
            system_content=system_content,
            user_id=user_id or request.user,
            max_tokens=request.max_tokens,
            temperature=request.temperature
        )
    
    async def prepare_messages(
        self,
        messages: List[Any],  # List of ChatMessage
        agent_config: Dict[str, Any],
        model_name: str
    ) -> Tuple[List[Dict[str, Any]], str, int]:
        """
        Prepare messages for Letta API.
        
        Args:
            messages: List of ChatMessage objects
            agent_config: Agent configuration dict
            model_name: Model name for token counting
            
        Returns:
            (letta_messages, system_content, estimated_tokens)
        """
        # Convert to OpenAI format
        openai_messages = [{"role": msg.role, "content": msg.content} for msg in messages]
        
        # Convert messages to Letta format
        letta_messages, system_content = self.message_translator.translate_messages(openai_messages)
        
        # Add API call indicator - all requests via /v1/chat/completions are API calls
        api_indicator = "[API]"
        
        # Add mode selection instruction to system content
        mode_instruction = self.message_translator.create_mode_selection_instruction(agent_config['mode'])
        if system_content:
            system_content = f"{api_indicator}\n\n{system_content}\n\n{mode_instruction}"
        else:
            system_content = f"{api_indicator}\n\n{mode_instruction}"
        
        # Estimate request tokens including [API] indicator and mode instruction
        # Create a complete message list that includes the system content for accurate token counting
        messages_for_counting = []
        if system_content:
            # Add system content as a system message for token counting
            messages_for_counting.append({"role": "system", "content": system_content})
        # Add all non-system messages
        for msg in openai_messages:
            if msg["role"] != "system":  # System messages are already in system_content
                messages_for_counting.append(msg)
        
        estimated_prompt_tokens = self.token_counter.count_messages_tokens(messages_for_counting, model_name)
        
        return letta_messages, system_content, estimated_prompt_tokens
    
    async def validate_token_capacity(
        self,
        agent_id: str,
        estimated_tokens: int,
        requested_max_tokens: Optional[int]
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate token capacity.
        
        Args:
            agent_id: Letta agent ID
            estimated_tokens: Estimated tokens for the prompt
            requested_max_tokens: Requested max_tokens value
            
        Returns:
            (is_valid, error_message)
        """
        is_valid, error_message, _ = await self.check_token_capacity(
            agent_id,
            estimated_tokens,
            requested_max_tokens=requested_max_tokens
        )
        return is_valid, error_message
    
    def _build_message_objects(self, letta_messages: List[Dict[str, Any]]) -> List[MessageCreate]:
        """
        Convert Letta messages to MessageCreate objects.
        
        Args:
            letta_messages: List of Letta message dicts
            
        Returns:
            List of MessageCreate objects
        """
        message_objects = []
        for msg in letta_messages:
            # message_translator returns content as list of dicts: [{"type": "text", "text": "..."}]
            # Convert to TextContent objects like reference implementation
            content = msg["content"]
            if isinstance(content, list):
                # Convert list of dicts to TextContent objects
                text_content = [TextContent(text=item["text"]) for item in content if isinstance(item, dict) and item.get("type") == "text"]
            else:
                # Fallback: wrap string in TextContent
                text_content = [TextContent(text=str(content))]
            
            # Only include tool_call_id if it exists (don't pass None)
            msg_kwargs = {
                "role": msg["role"],
                "content": text_content
            }
            if msg.get("tool_call_id"):
                msg_kwargs["tool_call_id"] = msg["tool_call_id"]
            
            message_objects.append(MessageCreate(**msg_kwargs))
        
        return message_objects

