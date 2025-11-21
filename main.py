#!/usr/bin/env python3
"""
The Librarian - OpenAI-Compatible Letta Proxy

A stateful, OpenAI-compatible gateway that allows clients to interface with 
a persistent Letta agent while speaking the standard OpenAI API protocol.

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

import os
import logging
import time
import uuid
import json
from typing import Dict, Any, Optional, AsyncGenerator
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv
from letta_client import AsyncLetta, MessageCreate, AssistantMessage
from letta_client.types import TextContent
from letta_client.core.api_error import ApiError
from letta_client import LlmConfig

# Import Librarian components
from src.librarian import ModelRegistry, MessageTranslator, ResponseFormatter, TokenCounter
from src.librarian.tool_synchronizer import ToolSynchronizer
from src.librarian.load_manager import LoadManager, RequestStatus
from src.librarian.security import SecurityMiddleware

# Load environment variables
load_dotenv()

# Configure logging
log_level = os.getenv("LIBRARIAN_LOG_LEVEL", "INFO").upper()
log_format = os.getenv("LIBRARIAN_LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")

logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format=log_format
)
logger = logging.getLogger(__name__)

# Server configuration
debug_mode = os.getenv("LIBRARIAN_DEBUG", "false").lower() == "true"
host = os.getenv("LIBRARIAN_HOST", "127.0.0.1")
port = int(os.getenv("LIBRARIAN_PORT", "8000"))
docs_enabled = debug_mode or os.getenv("LIBRARIAN_ENABLE_DOCS", "false").lower() == "true"

# Letta client configuration
letta_base_url = os.getenv("LETTA_BASE_URL", "http://localhost:8283")
letta_api_key = os.getenv("LETTA_API_KEY")
letta_timeout = int(os.getenv("LETTA_TIMEOUT", "30"))

# Security configuration
enable_ip_filtering = os.getenv("LIBRARIAN_ENABLE_IP_FILTERING", "false").lower() == "true"
allowed_ips = os.getenv("LIBRARIAN_ALLOWED_IPS", "").split(",") if os.getenv("LIBRARIAN_ALLOWED_IPS") else []
blocked_ips = os.getenv("LIBRARIAN_BLOCKED_IPS", "").split(",") if os.getenv("LIBRARIAN_BLOCKED_IPS") else []
api_key_required = os.getenv("LIBRARIAN_API_KEY_REQUIRED", "false").lower() == "true"
api_key = os.getenv("LIBRARIAN_API_KEY")

# Rate limiting configuration
rate_limit_enabled = os.getenv("LIBRARIAN_RATE_LIMIT_ENABLED", "false").lower() == "true"
rate_limit_requests = int(os.getenv("LIBRARIAN_RATE_LIMIT_REQUESTS", "100"))
rate_limit_window = int(os.getenv("LIBRARIAN_RATE_LIMIT_WINDOW", "60"))

# Performance configuration
max_request_size = int(os.getenv("LIBRARIAN_MAX_REQUEST_SIZE", "10485760"))  # 10MB
request_timeout = int(os.getenv("LIBRARIAN_REQUEST_TIMEOUT", "300"))  # 5 minutes
keep_alive_timeout = int(os.getenv("LIBRARIAN_KEEP_ALIVE_TIMEOUT", "5"))

# Security event logging configuration
log_security_events = os.getenv("LIBRARIAN_LOG_SECURITY_EVENTS", "true").lower() == "true"

logger.info(f"Configuration loaded: host={host}, port={port}, debug={debug_mode}")
logger.info(f"Letta config: base_url={letta_base_url}, timeout={letta_timeout}")
logger.info(f"Security: ip_filtering={enable_ip_filtering}, api_key_required={api_key_required}")
logger.info(f"Rate limiting: enabled={rate_limit_enabled}, requests={rate_limit_requests}/window={rate_limit_window}")

# Initialize FastAPI app
app = FastAPI(
    title=os.getenv("LIBRARIAN_TITLE", "The Librarian"),
    description=os.getenv("LIBRARIAN_DESCRIPTION", "OpenAI-Compatible Letta Proxy"),
    version=os.getenv("LIBRARIAN_VERSION", "0.1.0"),
    docs_url="/docs" if docs_enabled else None,
    redoc_url="/redoc" if docs_enabled else None,
)

# Add security middleware (all features are configurable and opt-in)
app.add_middleware(
    SecurityMiddleware,
    enable_ip_filtering=enable_ip_filtering,
    allowed_ips=allowed_ips,
    blocked_ips=blocked_ips,
    api_key_required=api_key_required,
    api_key=api_key,
    rate_limit_enabled=rate_limit_enabled,
    rate_limit_requests=rate_limit_requests,
    rate_limit_window=rate_limit_window,
    log_security_events=log_security_events
)

# Initialize Letta client with configuration
letta_client = AsyncLetta(
    base_url=letta_base_url,
    token=letta_api_key,
    timeout=letta_timeout
)

# Initialize components
model_registry = ModelRegistry()

# Resolve agent name to agent ID at startup
async def resolve_agent_id(agent_name: str) -> Optional[str]:
    """Resolve agent name to agent ID by looking up in Letta"""
    try:
        agents = await letta_client.agents.list()
        for agent in agents:
            if agent.name == agent_name:
                logger.info(f"Resolved agent name '{agent_name}' to ID '{agent.id}'")
                return agent.id
        logger.error(f"Agent with name '{agent_name}' not found in Letta server")
        return None
    except Exception as e:
        logger.error(f"Failed to resolve agent ID for '{agent_name}': {e}")
        return None

# Resolve agent IDs in model registry (convert names to IDs) - run at startup
@app.on_event("startup")
async def resolve_agent_ids():
    """Resolve agent names to IDs at startup"""
    for model_name, config in model_registry.list_models().items():
        agent_name = config.get("agent_id")
        if agent_name and not agent_name.startswith("agent-"):
            # It's a name, not an ID - resolve it
            agent_id = await resolve_agent_id(agent_name)
            if agent_id:
                model_registry.add_model(model_name, agent_id, config.get("mode", "auto"), config.get("description", ""))
            else:
                logger.warning(f"Could not resolve agent name '{agent_name}' for model '{model_name}'")

message_translator = MessageTranslator()
response_formatter = ResponseFormatter()
token_counter = TokenCounter()

# Initialize advanced components
tool_synchronizer = ToolSynchronizer(letta_client)
load_manager = LoadManager()

# Thread pool for running synchronous Letta calls in async context
thread_pool = ThreadPoolExecutor(max_workers=10)

# OpenAI-compatible models
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    temperature: Optional[float] = 1.0
    max_tokens: Optional[int] = None
    stream: Optional[bool] = False
    user: Optional[str] = None
    tools: Optional[list[Dict[str, Any]]] = None

class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[Dict[str, Any]]
    usage: Optional[Dict[str, int]] = None

class ModelInfo(BaseModel):
    id: str
    object: str = "model"
    created: int
    owned_by: str = "librarian"

# Model registry is now handled by the ModelRegistry component

async def configure_agent_for_request(
    agent_id: str,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None
) -> Optional[LlmConfig]:
    """
    Configure agent's LLM settings for a request and return original config for restoration.
    
    Args:
        agent_id: Letta agent ID
        temperature: Temperature to set (None to leave unchanged)
        max_tokens: Max tokens to set (None to leave unchanged)
    
    Returns:
        Original LlmConfig if settings were changed, None otherwise
    """
    if temperature is None and max_tokens is None:
        return None  # No changes needed
    
    try:
        # Retrieve current agent state
        agent_state = await letta_client.agents.retrieve(agent_id=agent_id)
        current_llm_config = agent_state.llm_config
        
        if current_llm_config is None:
            logger.warning(f"Agent {agent_id} has no llm_config, cannot configure")
            return None
        
        # Store original config for restoration
        original_config = current_llm_config
        
        # Create new config with updated values
        config_dict = current_llm_config.model_dump()
        if temperature is not None:
            config_dict['temperature'] = temperature
            logger.info(f"Setting temperature to {temperature} for agent {agent_id}")
        if max_tokens is not None:
            config_dict['max_tokens'] = max_tokens
            logger.info(f"Setting max_tokens to {max_tokens} for agent {agent_id}")
        
        # Create new LlmConfig with updated values
        new_llm_config = LlmConfig(**config_dict)
        
        # Modify agent
        await letta_client.agents.modify(
            agent_id=agent_id,
            llm_config=new_llm_config
        )
        
        logger.info(f"Successfully configured agent {agent_id} for request")
        return original_config
        
    except Exception as e:
        logger.error(f"Failed to configure agent {agent_id}: {str(e)}")
        return None

async def restore_agent_config(agent_id: str, original_config: LlmConfig) -> bool:
    """
    Restore agent's original LLM configuration.
    
    Args:
        agent_id: Letta agent ID
        original_config: Original LlmConfig to restore
    
    Returns:
        True if restoration successful, False otherwise
    """
    try:
        await letta_client.agents.modify(
            agent_id=agent_id,
            llm_config=original_config
        )
        logger.info(f"Successfully restored original config for agent {agent_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to restore config for agent {agent_id}: {str(e)}")
        return False

async def handle_non_streaming_response(
    agent_id: str, 
    message_objects: list, 
    model_name: str,
    openai_messages: list,
    system_content: Optional[str],
    user_id: Optional[str],
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
    retry_on_context_full: bool = True
) -> ChatCompletionResponse:
    """Handle non-streaming chat completion with automatic retry on context window full"""
    max_retries = 2  # Try original request + 1 retry after summarization
    
    # Configure agent for this request (temperature, max_tokens)
    original_config = await configure_agent_for_request(agent_id, temperature, max_tokens)
    
    try:
        for attempt in range(max_retries):
            try:
                # Use create_stream() and collect chunks
                # Note: create() fails with this agent due to model_endpoint=None in agent config
                # Streaming works, so we use it for both streaming and non-streaming
                # Temperature and max_tokens are configured on the agent before the request
                stream = letta_client.agents.messages.create_stream(
                    agent_id=agent_id,
                    messages=message_objects,
                    stream_tokens=True
                )
                
                # Collect all chunks from stream
                response_content = ""
                async for chunk in stream:
                    # Skip error and stop_reason events
                    if hasattr(chunk, 'message_type'):
                        msg_type = chunk.message_type
                        if msg_type == 'error':
                            error_msg = getattr(chunk, 'error', 'Unknown error')
                            error_exception = Exception(error_msg)
                            
                            # Check if it's a context window full error
                            if is_context_window_full_error(error_exception) and retry_on_context_full and attempt < max_retries - 1:
                                logger.warning(f"Context window full error detected, summarizing and retrying (attempt {attempt + 1}/{max_retries})")
                                if await summarize_agent_conversation(agent_id, max_message_length=10):
                                    # Retry the request after summarization
                                    break  # Break out of chunk loop, will retry outer loop
                                else:
                                    # Summarization failed, raise error
                                    if original_config is not None:
                                        await restore_agent_config(agent_id, original_config)
                                    raise HTTPException(
                                        status_code=500,
                                        detail={"error": {"message": f"Letta agent error: {error_msg}", "type": "server_error"}}
                                    )
                            else:
                                # Not a context window error or no retries left
                                logger.error(f"Error in Letta stream: {error_msg}")
                                if original_config is not None:
                                    await restore_agent_config(agent_id, original_config)
                                raise HTTPException(
                                    status_code=500,
                                    detail={"error": {"message": f"Letta agent error: {error_msg}", "type": "server_error"}}
                                )
                        elif msg_type == 'stop_reason':
                            # Normal stop, break
                            break
                    
                    # Extract content from chunk
                    chunk_content = response_formatter._extract_content(chunk)
                    if chunk_content:
                        response_content += chunk_content
                
                # If we got here and have content, request succeeded
                if response_content or attempt == max_retries - 1:
                    # Calculate token usage (include system_content with [API] indicator)
                    usage = token_counter.calculate_usage(openai_messages, response_content, model_name, system_content=system_content)
                    
                    # Format response
                    response = ChatCompletionResponse(
                        id=f"chatcmpl-{uuid.uuid4().hex}",
                        created=int(time.time()),
                        model=model_name,
                        choices=[{
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": response_content
                            },
                            "finish_reason": "stop"
                        }],
                        usage=usage
                    )
                    # Restore original config before returning
                    if original_config is not None:
                        await restore_agent_config(agent_id, original_config)
                    return response
                
            except HTTPException:
                # Re-raise HTTP exceptions (don't retry)
                if original_config is not None:
                    await restore_agent_config(agent_id, original_config)
                raise
            except ApiError as api_error:
                # Check if it's a context window full error
                if is_context_window_full_error(api_error) and retry_on_context_full and attempt < max_retries - 1:
                    logger.warning(f"Context window full error from Letta API, summarizing and retrying (attempt {attempt + 1}/{max_retries})")
                    if await summarize_agent_conversation(agent_id, max_message_length=10):
                        # Retry the request after summarization
                        continue
                    else:
                        # Summarization failed, raise error
                        if original_config is not None:
                            await restore_agent_config(agent_id, original_config)
                        raise HTTPException(
                            status_code=500,
                            detail={"error": {"message": f"Letta API error: {str(api_error)}", "type": "server_error"}}
                        )
                else:
                    # Not a context window error or no retries left
                    logger.error(f"Letta API error: {str(api_error)}", exc_info=True)
                    if original_config is not None:
                        await restore_agent_config(agent_id, original_config)
                    raise HTTPException(
                        status_code=500,
                        detail={"error": {"message": f"Letta API error: {str(api_error)}", "type": "server_error"}}
                    )
            except Exception as e:
                # Check if it's a context window full error
                if is_context_window_full_error(e) and retry_on_context_full and attempt < max_retries - 1:
                    logger.warning(f"Context window full error detected, summarizing and retrying (attempt {attempt + 1}/{max_retries})")
                    if await summarize_agent_conversation(agent_id, max_message_length=10):
                        # Retry the request after summarization
                        continue
                    else:
                        # Summarization failed, raise error
                        if original_config is not None:
                            await restore_agent_config(agent_id, original_config)
                        logger.error(f"Error in non-streaming response: {str(e)}", exc_info=True)
                        raise HTTPException(
                            status_code=500,
                            detail={"error": {"message": f"Failed to generate response: {str(e)}", "type": "server_error"}}
                        )
                else:
                    # Not a context window error or no retries left
                    logger.error(f"Error in non-streaming response: {str(e)}", exc_info=True)
                    if original_config is not None:
                        await restore_agent_config(agent_id, original_config)
                    raise HTTPException(
                        status_code=500,
                        detail={"error": {"message": f"Failed to generate response: {str(e)}", "type": "server_error"}}
                    )
        
        # If we get here, all retries failed
        if original_config is not None:
            await restore_agent_config(agent_id, original_config)
        raise HTTPException(
            status_code=500,
            detail={"error": {"message": "Failed to generate response after retries", "type": "server_error"}}
        )
    except Exception as e:
        # Ensure config is restored even on unexpected errors
        if original_config is not None:
            await restore_agent_config(agent_id, original_config)
        raise

        # If we get here, all retries failed
        if original_config is not None:
            await restore_agent_config(agent_id, original_config)
        raise HTTPException(
            status_code=500,
            detail={"error": {"message": "Failed to generate response after retries", "type": "server_error"}}
        )
    except Exception as e:
        # Ensure config is restored even on unexpected errors
        if original_config is not None:
            await restore_agent_config(agent_id, original_config)
        raise

async def handle_streaming_response_with_queue(
    load_manager: LoadManager,
    agent_id: str,
    message_objects: list,
    model_name: str,
    openai_messages: list,
    system_content: Optional[str],
    user_id: Optional[str],
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None
) -> StreamingResponse:
    """Handle streaming chat completion with queueing"""
    
    # Queue the request
    request_id = await load_manager.queue_request(agent_id, openai_messages, user_id)
    
    async def generate_stream():
        # Acquire semaphore (waits if at max_concurrent)
        await load_manager.processing_semaphore.acquire()
        
        # Mark as processing
        async with load_manager.request_lock:
            # Find and move request to active
            request_item = None
            for req in load_manager.request_queue:
                if req.request_id == request_id:
                    request_item = req
                    break
            
            if request_item:
                request_item.status = RequestStatus.PROCESSING
                load_manager.active_requests[request_id] = request_item
                load_manager.request_queue.remove(request_item)
        
        try:
            # Yield from the actual stream
            async for chunk in _generate_stream_chunks(
                agent_id, message_objects, model_name, 
                openai_messages, system_content, max_tokens, temperature
            ):
                yield chunk
        finally:
            # Mark as completed and release semaphore
            async with load_manager.request_lock:
                if request_id in load_manager.active_requests:
                    req_item = load_manager.active_requests[request_id]
                    req_item.status = RequestStatus.COMPLETED
                    del load_manager.active_requests[request_id]
            load_manager.processing_semaphore.release()
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

async def _generate_stream_chunks(
    agent_id: str,
    message_objects: list,
    model_name: str,
    openai_messages: list,
    system_content: Optional[str] = None,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
    retry_on_context_full: bool = True
) -> AsyncGenerator[str, None]:
    """Generate stream chunks from Letta (internal helper) with retry on context window full"""
    max_retries = 2  # Try original request + 1 retry after summarization
    
    # Configure agent for this request (temperature, max_tokens)
    original_config = await configure_agent_for_request(agent_id, temperature, max_tokens)
    
    try:
        for attempt in range(max_retries):
            should_retry = False
            try:
                # Temperature and max_tokens are configured on the agent before the request
                stream = letta_client.agents.messages.create_stream(
                    agent_id=agent_id,
                    messages=message_objects,
                    stream_tokens=True
                )
                
                response_id = f"chatcmpl-{uuid.uuid4().hex}"
                full_content = ""
                chunk_count = 0
                
                try:
                    async for chunk in stream:
                        chunk_count += 1
                        logger.debug(f"Stream chunk {chunk_count}: type={type(chunk).__name__}")
                        
                        # Determine event type
                        event_type = None
                        if hasattr(chunk, 'message_type') and isinstance(chunk.message_type, str):
                            event_type = chunk.message_type
                        elif hasattr(chunk, 'tool_call'):
                            event_type = 'tool_call_message'
                        elif hasattr(chunk, 'content'):
                            event_type = 'assistant_message'
                        
                        logger.debug(f"  Final event_type: {event_type}")
                        
                        # Handle different event types
                        if event_type == 'error':
                            error_msg = getattr(chunk, 'error', 'Unknown error')
                            error_exception = Exception(error_msg)
                            
                            # Check if it's a context window full error
                            if is_context_window_full_error(error_exception) and retry_on_context_full and attempt < max_retries - 1:
                                logger.warning(f"Context window full error in stream, summarizing and retrying (attempt {attempt + 1}/{max_retries})")
                                if await summarize_agent_conversation(agent_id, max_message_length=10):
                                    # Will retry outer loop
                                    should_retry = True
                                    break
                                else:
                                    # Summarization failed, yield error
                                    error_chunk = {
                                        "error": {
                                            "message": f"Letta agent error: {error_msg}",
                                            "type": "server_error"
                                        }
                                    }
                                    yield f"data: {json.dumps(error_chunk)}\n\n"
                                    yield "data: [DONE]\n\n"
                                    if original_config is not None:
                                        await restore_agent_config(agent_id, original_config)
                                    return
                            else:
                                # Not a context window error or no retries left
                                logger.error(f"Error in Letta stream: {error_msg}")
                                error_chunk = {
                                    "error": {
                                        "message": f"Letta agent error: {error_msg}",
                                        "type": "server_error"
                                    }
                                }
                                yield f"data: {json.dumps(error_chunk)}\n\n"
                                yield "data: [DONE]\n\n"
                                if original_config is not None:
                                    await restore_agent_config(agent_id, original_config)
                                return
                        elif event_type == 'stop_reason':
                            stop_reason = getattr(chunk, 'stop_reason', None)
                            if stop_reason == 'error':
                                error_msg = getattr(chunk, 'error', 'Unknown error')
                                error_exception = Exception(error_msg)
                                
                                # Check if it's a context window full error
                                if is_context_window_full_error(error_exception) and retry_on_context_full and attempt < max_retries - 1:
                                    logger.warning(f"Context window full error in stream stop_reason, summarizing and retrying (attempt {attempt + 1}/{max_retries})")
                                    if await summarize_agent_conversation(agent_id, max_message_length=10):
                                        # Will retry outer loop
                                        should_retry = True
                                        break
                                    else:
                                        # Summarization failed, yield error
                                        error_chunk = {
                                            "error": {
                                                "message": f"Letta agent error: {error_msg}",
                                                "type": "server_error"
                                            }
                                        }
                                        yield f"data: {json.dumps(error_chunk)}\n\n"
                                        yield "data: [DONE]\n\n"
                                        if original_config is not None:
                                            await restore_agent_config(agent_id, original_config)
                                        return
                                else:
                                    # Not a context window error or no retries left
                                    logger.error(f"Stop reason error: {error_msg}")
                                    error_chunk = {
                                        "error": {
                                            "message": f"Letta agent error: {error_msg}",
                                            "type": "server_error"
                                        }
                                    }
                                    yield f"data: {json.dumps(error_chunk)}\n\n"
                                    yield "data: [DONE]\n\n"
                                    if original_config is not None:
                                        await restore_agent_config(agent_id, original_config)
                                    return
                            break
                        elif event_type == 'assistant_message':
                            content = getattr(chunk, 'content', '') or ""
                            chunk_content = ""
                            if isinstance(content, list):
                                chunk_content = "".join(item.text for item in content if hasattr(item, 'text'))
                            elif isinstance(content, str):
                                chunk_content = content
                            
                            if chunk_content:
                                full_content += chunk_content
                                
                                chunk_data = {
                                    "id": response_id,
                                    "object": "chat.completion.chunk",
                                    "created": int(time.time()),
                                    "model": model_name,
                                    "choices": [{
                                        "index": 0,
                                        "delta": {
                                            "content": chunk_content
                                        },
                                        "finish_reason": None
                                    }]
                                }
                                
                                yield f"data: {json.dumps(chunk_data)}\n\n"
                        elif event_type == 'reasoning_message':
                            continue
                    else:
                        chunk_content = response_formatter._extract_content(chunk)
                        if chunk_content:
                            full_content += chunk_content
                            
                            chunk_data = {
                                "id": response_id,
                                "object": "chat.completion.chunk",
                                "created": int(time.time()),
                                "model": model_name,
                                "choices": [{
                                    "index": 0,
                                    "delta": {
                                        "content": chunk_content
                                    },
                                    "finish_reason": None
                                }]
                            }
                            
                            yield f"data: {json.dumps(chunk_data)}\n\n"
                
                    # If we should retry, break and continue outer loop
                    if should_retry:
                        break
                    
                    # Stream completed successfully
                    logger.debug(f"Stream completed: {chunk_count} chunks processed, {len(full_content)} chars of content")
                    
                    # Send final chunk with usage (include system_content with [API] indicator)
                    usage = token_counter.calculate_usage(openai_messages, full_content, model_name, system_content=system_content)
                    final_chunk = {
                        "id": response_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": model_name,
                        "choices": [{
                            "index": 0,
                            "delta": {},
                            "finish_reason": "stop"
                        }],
                        "usage": usage
                    }
                    
                    yield f"data: {json.dumps(final_chunk)}\n\n"
                    yield "data: [DONE]\n\n"
                    # Restore original config before returning
                    if original_config is not None:
                        await restore_agent_config(agent_id, original_config)
                    return  # Success, exit function
                    
                except Exception as stream_error:
                    # Check if it's a context window full error
                    if is_context_window_full_error(stream_error) and retry_on_context_full and attempt < max_retries - 1:
                        logger.warning(f"Context window full error in stream iteration, summarizing and retrying (attempt {attempt + 1}/{max_retries})")
                        if await summarize_agent_conversation(agent_id, max_message_length=10):
                            # Will retry outer loop
                            continue
                        else:
                            # Summarization failed, yield error
                            logger.error(f"Error iterating stream: {type(stream_error).__name__}: {str(stream_error)}", exc_info=True)
                            error_chunk = {
                                "error": {
                                    "message": f"Stream iteration error: {str(stream_error)}",
                                    "type": "server_error"
                                }
                            }
                            yield f"data: {json.dumps(error_chunk)}\n\n"
                            yield "data: [DONE]\n\n"
                            if original_config is not None:
                                await restore_agent_config(agent_id, original_config)
                            return
                    else:
                        # Not a context window error or no retries left
                        logger.error(f"Error iterating stream: {type(stream_error).__name__}: {str(stream_error)}", exc_info=True)
                        error_chunk = {
                            "error": {
                                "message": f"Stream iteration error: {str(stream_error)}",
                                "type": "server_error"
                            }
                        }
                        yield f"data: {json.dumps(error_chunk)}\n\n"
                        yield "data: [DONE]\n\n"
                        if original_config is not None:
                            await restore_agent_config(agent_id, original_config)
                        return
                
            except ApiError as api_error:
                # Check if it's a context window full error
                if is_context_window_full_error(api_error) and retry_on_context_full and attempt < max_retries - 1:
                    logger.warning(f"Context window full error from Letta API in stream, summarizing and retrying (attempt {attempt + 1}/{max_retries})")
                    if await summarize_agent_conversation(agent_id, max_message_length=10):
                        # Will retry outer loop
                        continue
                    else:
                        # Summarization failed, yield error
                        error_chunk = {
                            "error": {
                                "message": f"Letta API error: {str(api_error)}",
                                "type": "server_error"
                            }
                        }
                        yield f"data: {json.dumps(error_chunk)}\n\n"
                        yield "data: [DONE]\n\n"
                        if original_config is not None:
                            await restore_agent_config(agent_id, original_config)
                        return
                else:
                    # Not a context window error or no retries left
                    logger.error(f"Letta API error in stream: {str(api_error)}", exc_info=True)
                    error_chunk = {
                        "error": {
                            "message": f"Letta API error: {str(api_error)}",
                            "type": "server_error"
                        }
                    }
                    yield f"data: {json.dumps(error_chunk)}\n\n"
                    yield "data: [DONE]\n\n"
                    if original_config is not None:
                        await restore_agent_config(agent_id, original_config)
                    return
            except Exception as e:
                # Check if it's a context window full error
                if is_context_window_full_error(e) and retry_on_context_full and attempt < max_retries - 1:
                    logger.warning(f"Context window full error in stream, summarizing and retrying (attempt {attempt + 1}/{max_retries})")
                    if await summarize_agent_conversation(agent_id, max_message_length=10):
                        # Will retry outer loop
                        continue
                    else:
                        # Summarization failed, yield error
                        logger.error(f"Error in streaming response: {str(e)}", exc_info=True)
                        error_chunk = {
                            "error": {
                                "message": f"Streaming error: {str(e)}",
                                "type": "server_error"
                            }
                        }
                        yield f"data: {json.dumps(error_chunk)}\n\n"
                        yield "data: [DONE]\n\n"
                        if original_config is not None:
                            await restore_agent_config(agent_id, original_config)
                        return
                else:
                    # Not a context window error or no retries left
                    logger.error(f"Error in streaming response: {str(e)}", exc_info=True)
                    error_chunk = {
                        "error": {
                            "message": f"Streaming error: {str(e)}",
                            "type": "server_error"
                        }
                    }
                    yield f"data: {json.dumps(error_chunk)}\n\n"
                    yield "data: [DONE]\n\n"
                    if original_config is not None:
                        await restore_agent_config(agent_id, original_config)
                    return
    
        # If we get here, all retries failed
        if original_config is not None:
            await restore_agent_config(agent_id, original_config)
        error_chunk = {
            "error": {
                "message": "Failed to generate stream after retries",
                "type": "server_error"
            }
        }
        yield f"data: {json.dumps(error_chunk)}\n\n"
        yield "data: [DONE]\n\n"
    except Exception as e:
        # Ensure config is restored even on unexpected errors
        if original_config is not None:
            await restore_agent_config(agent_id, original_config)
        error_chunk = {
            "error": {
                "message": f"Unexpected error: {str(e)}",
                "type": "server_error"
            }
        }
        yield f"data: {json.dumps(error_chunk)}\n\n"
        yield "data: [DONE]\n\n"

async def handle_streaming_response(
    agent_id: str,
    message_objects: list,
    model_name: str,
    openai_messages: list,
    system_content: Optional[str],
    user_id: Optional[str],
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None
) -> StreamingResponse:
    """Handle streaming chat completion (legacy, now uses queueing)"""
    
    async def generate_stream():
        try:
            # Create streaming message with Letta client
            # create_stream() returns an async generator, don't await it
            stream_kwargs = {
                "agent_id": agent_id,
                "messages": message_objects,
                "stream_tokens": True  # Enable token-level streaming
            }
            # Pass through max_tokens and temperature if provided
            if max_tokens is not None:
                stream_kwargs["max_tokens"] = max_tokens
            if temperature is not None:
                stream_kwargs["temperature"] = temperature
            
            stream = letta_client.agents.messages.create_stream(**stream_kwargs)
            
            response_id = f"chatcmpl-{uuid.uuid4().hex}"
            full_content = ""
            
            # Stream chunks (create_stream returns an async iterator)
            # Extract content like reference implementation
            chunk_count = 0
            try:
                async for chunk in stream:
                    chunk_count += 1
                    logger.debug(f"Stream chunk {chunk_count}: type={type(chunk).__name__}")
                    
                    # Determine event type (same as reference)
                    event_type = None
                    if hasattr(chunk, 'message_type') and isinstance(chunk.message_type, str):
                        event_type = chunk.message_type
                        logger.debug(f"  Event type from message_type: {event_type}")
                    elif hasattr(chunk, 'tool_call'):
                        event_type = 'tool_call_message'
                    elif hasattr(chunk, 'content'):
                        event_type = 'assistant_message'
                        logger.debug(f"  Event type from content: {event_type}, content type={type(getattr(chunk, 'content', None))}")
                    elif hasattr(chunk, 'reasoning'):
                        event_type = 'reasoning_message'
                    
                    logger.debug(f"  Final event_type: {event_type}")
                    
                    # Handle different event types
                    if event_type == 'error':
                        error_msg = getattr(chunk, 'error', 'Unknown error')
                        logger.error(f"Error in Letta stream: {error_msg}")
                        error_chunk = {
                            "error": {
                                "message": f"Letta agent error: {error_msg}",
                                "type": "server_error"
                            }
                        }
                        yield f"data: {json.dumps(error_chunk)}\n\n"
                        yield "data: [DONE]\n\n"
                        return
                    elif event_type == 'stop_reason':
                        stop_reason = getattr(chunk, 'stop_reason', None)
                        if stop_reason == 'error':
                            error_msg = getattr(chunk, 'error', 'Unknown error')
                            logger.error(f"Stop reason error: {error_msg}")
                            error_chunk = {
                                "error": {
                                    "message": f"Letta agent error: {error_msg}",
                                    "type": "server_error"
                                }
                            }
                            yield f"data: {json.dumps(error_chunk)}\n\n"
                            yield "data: [DONE]\n\n"
                            return
                        # Normal stop, break
                        break
                    elif event_type == 'assistant_message':
                        # Extract content from assistant message (same as reference)
                        content = getattr(chunk, 'content', '') or ""
                        chunk_content = ""
                        if isinstance(content, list):
                            # Extract text from TextContent objects
                            chunk_content = "".join(item.text for item in content if hasattr(item, 'text'))
                        elif isinstance(content, str):
                            chunk_content = content
                        
                        if chunk_content:
                            full_content += chunk_content
                            
                            chunk_data = {
                                "id": response_id,
                                "object": "chat.completion.chunk",
                                "created": int(time.time()),
                                "model": model_name,
                                "choices": [{
                                    "index": 0,
                                    "delta": {
                                        "content": chunk_content
                                    },
                                    "finish_reason": None
                                }]
                            }
                            
                            yield f"data: {json.dumps(chunk_data)}\n\n"
                    elif event_type == 'reasoning_message':
                        # Skip reasoning messages (filtered out)
                        continue
                    else:
                        # Unknown event type, try to extract content anyway
                        chunk_content = response_formatter._extract_content(chunk)
                        if chunk_content:
                            full_content += chunk_content
                            
                            chunk_data = {
                                "id": response_id,
                                "object": "chat.completion.chunk",
                                "created": int(time.time()),
                                "model": model_name,
                                "choices": [{
                                    "index": 0,
                                    "delta": {
                                        "content": chunk_content
                                    },
                                    "finish_reason": None
                                }]
                            }
                            
                            yield f"data: {json.dumps(chunk_data)}\n\n"
                
                logger.debug(f"Stream completed: {chunk_count} chunks processed, {len(full_content)} chars of content")
            except Exception as stream_error:
                logger.error(f"Error iterating stream: {type(stream_error).__name__}: {str(stream_error)}", exc_info=True)
                error_chunk = {
                    "error": {
                        "message": f"Stream iteration error: {str(stream_error)}",
                        "type": "server_error"
                    }
                }
                yield f"data: {json.dumps(error_chunk)}\n\n"
                yield "data: [DONE]\n\n"
                return
            
            # Send final chunk with usage (include system_content with [API] indicator)
            usage = token_counter.calculate_usage(openai_messages, full_content, model_name, system_content=system_content)
            final_chunk = {
                "id": response_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": model_name,
                "choices": [{
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop"
                }],
                "usage": usage
            }
            
            yield f"data: {json.dumps(final_chunk)}\n\n"
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            logger.error(f"Error in streaming response: {str(e)}", exc_info=True)
            error_chunk = {
                "error": {
                    "message": f"Streaming error: {str(e)}",
                    "type": "server_error"
                }
            }
            yield f"data: {json.dumps(error_chunk)}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "librarian"}

@app.get("/v1/models")
async def list_models():
    """List available models (OpenAI compatible)"""
    models = []
    for model_id, config in model_registry.list_models().items():
        models.append(ModelInfo(
            id=model_id,
            created=1700000000,  # Placeholder timestamp
            owned_by="librarian"
        ))
    return {"object": "list", "data": models}

@app.get("/v1/models/{model_id}")
async def get_model(model_id: str):
    """Get model information (OpenAI compatible)"""
    if not model_registry.is_valid_model(model_id):
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
    
    return ModelInfo(
        id=model_id,
        created=1700000000,  # Placeholder timestamp
        owned_by="librarian"
    )

async def summarize_agent_conversation(agent_id: str, max_message_length: int = 10) -> bool:
    """
    Summarize agent's conversation history to free up context window.
    
    Args:
        agent_id: Letta agent ID
        max_message_length: Maximum number of messages to retain after summarization
    
    Returns:
        True if summarization successful, False otherwise
    """
    try:
        logger.info(f"Summarizing conversation for agent {agent_id}, keeping last {max_message_length} messages")
        await letta_client.agents.summarize(
            agent_id=agent_id,
            max_message_length=max_message_length
        )
        logger.info(f"Successfully summarized conversation for agent {agent_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to summarize conversation for agent {agent_id}: {str(e)}")
        return False

def is_context_window_full_error(error: Exception) -> bool:
    """
    Check if an error indicates context window is full.
    
    Args:
        error: Exception to check
    
    Returns:
        True if error indicates context window full
    """
    error_str = str(error).lower()
    error_msg = error_str
    
    # Check for common context window full indicators
    context_full_indicators = [
        "context window full",
        "context window exceeded",
        "context length exceeded",
        "context overflow",
        "token limit exceeded",
        "context_window",
        "context is full"
    ]
    
    return any(indicator in error_msg for indicator in context_full_indicators)

async def check_token_capacity(
    agent_id: str, 
    request_tokens: int, 
    requested_max_tokens: Optional[int] = None
) -> tuple[bool, Optional[str], Optional[Dict[str, int]]]:
    """
    Check if request is valid based on current token usage and model limits.
    Only errors if requested_max_tokens exceeds the model's absolute maximum capability.
    For small requests, allows them even if they exceed current capacity (summarization will handle it).
    
    Args:
        agent_id: Letta agent ID
        request_tokens: Estimated tokens for the prompt
        requested_max_tokens: max_tokens value requested by user (None if not specified)
    
    Returns:
        (is_valid, error_message, capacity_info) where:
        - is_valid: True if request is valid (or will be handled by summarization)
        - error_message: Error message if invalid, None if valid
        - capacity_info: Dict with max_tokens, current_tokens, available_tokens, request_tokens
    """
    try:
        # Get current context from Letta
        context = await letta_client.agents.context.retrieve(agent_id=agent_id)
        context_dict = context.model_dump()
        
        # Get current usage and max window size (model's absolute maximum)
        current_tokens = context_dict.get('context_window_size_current', 0)
        max_context_window = context_dict.get('context_window_size_max', 0)  # Model's absolute max
        
        capacity_info = {
            'max_tokens': max_context_window,
            'current_tokens': current_tokens,
            'available_tokens': max_context_window - current_tokens,
            'request_tokens': request_tokens
        }
        
        # Only error if requested_max_tokens exceeds the model's absolute maximum capability
        if requested_max_tokens is not None:
            if requested_max_tokens > max_context_window:
                error_msg = (
                    f"Requested max_tokens ({requested_max_tokens:,}) exceeds model's maximum capability "
                    f"({max_context_window:,} tokens)."
                )
                return False, error_msg, capacity_info
        
        # For small requests, calculate total needed but don't error - let summarization handle it
        # Total needed = current usage + request tokens + completion tokens
        estimated_completion_tokens = requested_max_tokens if requested_max_tokens is not None else 100
        total_needed = current_tokens + request_tokens + estimated_completion_tokens
        
        # Log if we're over capacity (but don't error - summarization will handle it)
        if total_needed > max_context_window:
            logger.info(
                f"Request will exceed current capacity (needed: {total_needed:,}, max: {max_context_window:,}, "
                f"current: {current_tokens:,}). Will attempt summarization if context window full error occurs."
            )
        
        # Request is valid (either fits, or will be handled by summarization on error)
        return True, None, capacity_info
        
    except Exception as e:
        logger.warning(f"Failed to check token capacity for agent {agent_id}: {e}")
        # If we can't check, allow the request (fail open)
        return True, None, None

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """Main OpenAI-compatible chat completions endpoint"""
    
    try:
        # Validate model
        if not model_registry.is_valid_model(request.model):
            raise HTTPException(
                status_code=400,
                detail={"error": {"message": f"Unknown model: {request.model}", "type": "invalid_request_error"}}
            )
        
        # Get agent configuration
        agent_config = model_registry.get_agent_config(request.model)
        agent_id = agent_config['agent_id']
        logger.info(f"Processing request for model {request.model} -> agent {agent_id}")
        
        # Convert messages to Letta format first to extract system content
        openai_messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        letta_messages, system_content = message_translator.translate_messages(openai_messages)
        
        # Add API call indicator - all requests via /v1/chat/completions are API calls
        api_indicator = "[API]"
        
        # Add mode selection instruction to system content
        mode_instruction = message_translator.create_mode_selection_instruction(agent_config['mode'])
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
        
        estimated_prompt_tokens = token_counter.count_messages_tokens(messages_for_counting, request.model)
        
        # Check token capacity (only errors if max_tokens exceeds model's absolute maximum)
        is_valid, error_message, capacity_info = await check_token_capacity(
            agent_id, 
            estimated_prompt_tokens,
            requested_max_tokens=request.max_tokens
        )
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "message": error_message or "Request exceeds model's maximum token capacity",
                        "type": "invalid_request_error",
                        "code": "context_length_exceeded"
                    }
                }
            )
        
        # Sync tools if provided
        if request.tools:
            await tool_synchronizer.sync_tools(agent_id, request.tools)
        
        # Convert to MessageCreate objects with TextContent (same format as reference)
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
        
        # Handle streaming vs non-streaming with queueing
        if request.stream:
            # For streaming, we need to yield from generator, so handle queueing inline
            return await handle_streaming_response_with_queue(
                load_manager,
                agent_id, message_objects, request.model, 
                openai_messages, system_content, request.user,
                max_tokens=request.max_tokens,
                temperature=request.temperature
            )
        else:
            # For non-streaming, use queue processing
            async def processor():
                return await handle_non_streaming_response(
                    agent_id, message_objects, request.model,
                    openai_messages, system_content, request.user,
                    max_tokens=request.max_tokens,
                    temperature=request.temperature
                )
            
            return await load_manager.process_with_queue(
                agent_id,
                openai_messages,
                processor,
                user_id=request.user
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing chat completion: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": {"message": "Internal server error", "type": "server_error"}}
        )

@app.post("/v1/completions")
async def completions(request: Dict[str, Any]):
    """Legacy completions endpoint (alias for chat/completions)"""
    # Convert legacy format to chat format
    if "prompt" in request:
        chat_request = ChatCompletionRequest(
            model=request.get("model", "gpt-4.1"),
            messages=[ChatMessage(role="user", content=request["prompt"])],
            temperature=request.get("temperature", 1.0),
            max_tokens=request.get("max_tokens"),
            stream=request.get("stream", False)
        )
        return await chat_completions(chat_request)
    
    raise HTTPException(status_code=400, detail="Legacy completions format not supported")

if __name__ == "__main__":
    logger.info(f"Starting The Librarian on {host}:{port}")
    logger.info(f"Debug mode: {debug_mode}")
    logger.info(f"Documentation: {'enabled' if docs_enabled else 'disabled'}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=debug_mode,
        log_level="debug" if debug_mode else "info",
        timeout_keep_alive=keep_alive_timeout,
        limit_max_requests=max_request_size,
        access_log=debug_mode
    )
