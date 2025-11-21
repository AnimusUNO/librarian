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
from src.librarian.config import Config
from src.librarian.agent_config_manager import AgentConfigManager
from src.librarian.error_handler import ErrorHandler, ErrorHandlingResult, ErrorType
from src.librarian.stream_processor import StreamProcessor
from src.librarian.response_builder import ResponseBuilder
from src.librarian.request_processor import RequestProcessor, ProcessedRequest

# Load and validate configuration
config = Config.load()
config.validate_config()

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.log_level, logging.INFO),
    format=config.log_format
)
logger = logging.getLogger(__name__)

# Log configuration summary
config.log_summary()

# Initialize FastAPI app
app = FastAPI(
    title=os.getenv("LIBRARIAN_TITLE", "The Librarian"),
    description=os.getenv("LIBRARIAN_DESCRIPTION", "OpenAI-Compatible Letta Proxy"),
    version=os.getenv("LIBRARIAN_VERSION", "0.1.0"),
    docs_url="/docs" if (config.debug or config.enable_docs) else None,
    redoc_url="/redoc" if (config.debug or config.enable_docs) else None,
)

# Add security middleware (all features are configurable and opt-in)
app.add_middleware(
    SecurityMiddleware,
    enable_ip_filtering=config.enable_ip_filtering,
    allowed_ips=config.allowed_ips,
    blocked_ips=config.blocked_ips,
    api_key_required=config.api_key_required,
    api_key=config.api_key,
    rate_limit_enabled=config.rate_limit_enabled,
    rate_limit_requests=config.rate_limit_requests,
    rate_limit_window=config.rate_limit_window,
    log_security_events=config.log_security_events
)

# Initialize Letta client with configuration
letta_client = AsyncLetta(
    base_url=config.letta_base_url,
    token=config.letta_api_key,
    timeout=config.letta_timeout
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
load_manager = LoadManager(
    max_concurrent=config.max_concurrent,
    duplication_threshold=config.duplication_threshold,
    queue_timeout=config.queue_timeout,
    cleanup_interval=config.cleanup_interval,
    enable_auto_duplication=config.enable_auto_duplication,
    max_clones_per_agent=config.max_clones_per_agent
)
agent_config_manager = AgentConfigManager(letta_client)
error_handler = ErrorHandler()
stream_processor = StreamProcessor(letta_client, response_formatter)
response_builder = ResponseBuilder()

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
    
    # Use context manager for agent configuration (automatically restores on exit)
    async with agent_config_manager.temporary_config(agent_id, temperature=temperature, max_tokens=max_tokens):
        for attempt in range(max_retries):
            should_retry = False
            response_content = ""
            
            try:
                # Create stream using StreamProcessor
                stream = await stream_processor.create_stream(agent_id, message_objects)
                
                # Process chunks with callbacks
                chunk_error = None
                
                def on_chunk(content: str, event_type: str):
                    nonlocal response_content
                    response_content += content
                
                def on_error(error: Exception) -> bool:
                    nonlocal chunk_error, should_retry
                    # Store error for async handling after chunk processing
                    chunk_error = error
                    # Check if it's a context window full error that we can retry
                    if error_handler.is_context_window_full_error(error) and retry_on_context_full and attempt < max_retries - 1:
                        should_retry = True
                        return True  # Signal to break chunk loop
                    return False  # Don't retry, will raise error
                
                def on_stop():
                    pass  # Normal stop, nothing to do
                
                # Process stream chunks
                result = await stream_processor.process_chunks(stream, on_chunk, on_error, on_stop)
                response_content = result['content']
                
                # Handle any errors encountered during chunk processing
                if chunk_error:
                    error_result = await error_handler.handle_error(
                        chunk_error,
                        agent_id,
                        attempt,
                        max_retries,
                        retry_on_context_full,
                        is_streaming=False,
                        summarize_func=summarize_agent_conversation
                    )
                    if error_result.should_retry:
                        continue  # Retry outer loop
                    else:
                        # Not retryable, raise error
                        if isinstance(error_result.error_response, HTTPException):
                            raise error_result.error_response
                        # Fallback
                        logger.error(f"Error in Letta stream: {str(chunk_error)}")
                        raise HTTPException(
                            status_code=500,
                            detail={"error": {"message": f"Letta agent error: {str(chunk_error)}", "type": "server_error"}}
                        )
                
                # If we got here and have content, request succeeded
                if response_content or attempt == max_retries - 1:
                    # Calculate token usage (include system_content with [API] indicator)
                    usage = token_counter.calculate_usage(openai_messages, response_content, model_name, system_content=system_content)
                    
                    # Build response using ResponseBuilder
                    response_data = response_builder.build_completion_response(
                        response_content,
                        model_name,
                        usage
                    )
                    
                    # Convert to ChatCompletionResponse
                    response = ChatCompletionResponse(**response_data)
                    return response
                
            except HTTPException:
                # Re-raise HTTP exceptions (don't retry)
                raise
            except Exception as e:
                # Handle error using ErrorHandler
                error_result = await error_handler.handle_error(
                    e,
                    agent_id,
                    attempt,
                    max_retries,
                    retry_on_context_full,
                    is_streaming=False,
                    summarize_func=summarize_agent_conversation
                )
                
                if error_result.should_retry:
                    continue  # Retry outer loop
                else:
                    # Not retryable, raise error
                    if isinstance(error_result.error_response, HTTPException):
                        raise error_result.error_response
                    # Fallback error
                    logger.error(f"Error in non-streaming response: {str(e)}", exc_info=True)
                    raise HTTPException(
                        status_code=500,
                        detail={"error": {"message": f"Failed to generate response: {str(e)}", "type": "server_error"}}
                    )
        
        # If we get here, all retries failed
        raise HTTPException(
            status_code=500,
            detail={"error": {"message": "Failed to generate response after retries", "type": "server_error"}}
        )

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
    
    # Use context manager for agent configuration (automatically restores on exit)
    async with agent_config_manager.temporary_config(agent_id, temperature=temperature, max_tokens=max_tokens):
        for attempt in range(max_retries):
            should_retry = False
            try:
                # Create stream using StreamProcessor
                stream = await stream_processor.create_stream(agent_id, message_objects)
                
                response_id = response_builder.generate_response_id()
                full_content = ""
                chunk_count = 0
                
                try:
                    async for chunk in stream:
                        chunk_count += 1
                        logger.debug(f"Stream chunk {chunk_count}: type={type(chunk).__name__}")
                        
                        # Detect event type using StreamProcessor
                        event_type = stream_processor.detect_event_type(chunk)
                        logger.debug(f"  Final event_type: {event_type}")
                        
                        # Handle different event types
                        if event_type == 'error':
                            error_msg = getattr(chunk, 'error', 'Unknown error')
                            error_exception = Exception(error_msg)
                            
                            # Handle error using ErrorHandler
                            error_result = await error_handler.handle_error(
                                error_exception,
                                agent_id,
                                attempt,
                                max_retries,
                                retry_on_context_full,
                                is_streaming=True,
                                summarize_func=summarize_agent_conversation
                            )
                            
                            if error_result.should_retry:
                                should_retry = True
                                break
                            else:
                                # Not retryable, yield error and return
                                if isinstance(error_result.error_response, str):
                                    yield error_result.error_response
                                else:
                                    # Fallback error chunk
                                    error_chunk_str = error_handler.format_error_response(
                                        error_exception,
                                        error_result.error_type or ErrorType.SERVER_ERROR,
                                        is_streaming=True
                                    )
                                    yield error_chunk_str
                                return
                        
                        elif event_type == 'stop_reason':
                            stop_reason = getattr(chunk, 'stop_reason', None)
                            if stop_reason == 'error':
                                error_msg = getattr(chunk, 'error', 'Unknown error')
                                error_exception = Exception(error_msg)
                                
                                # Handle error using ErrorHandler
                                error_result = await error_handler.handle_error(
                                    error_exception,
                                    agent_id,
                                    attempt,
                                    max_retries,
                                    retry_on_context_full,
                                    is_streaming=True,
                                    summarize_func=summarize_agent_conversation
                                )
                                
                                if error_result.should_retry:
                                    should_retry = True
                                    break
                                else:
                                    # Not retryable, yield error and return
                                    if isinstance(error_result.error_response, str):
                                        yield error_result.error_response
                                    else:
                                        # Fallback error chunk
                                        error_chunk_str = error_handler.format_error_response(
                                            error_exception,
                                            error_result.error_type or ErrorType.SERVER_ERROR,
                                            is_streaming=True
                                        )
                                        yield error_chunk_str
                                    return
                            else:
                                # Normal stop, break
                                break
                        
                        elif event_type == 'assistant_message':
                            # Extract content using StreamProcessor
                            chunk_content = stream_processor.extract_chunk_content_detailed(chunk)
                            
                            if chunk_content:
                                full_content += chunk_content
                                
                                # Build chunk using ResponseBuilder
                                chunk_str = response_builder.build_stream_chunk(
                                    chunk_content,
                                    model_name,
                                    response_id
                                )
                                yield chunk_str
                        
                        elif event_type == 'reasoning_message':
                            # Skip reasoning messages
                            continue
                        
                        else:
                            # Fallback: try to extract content
                            chunk_content = stream_processor.extract_chunk_content(chunk)
                            if chunk_content:
                                full_content += chunk_content
                                
                                # Build chunk using ResponseBuilder
                                chunk_str = response_builder.build_stream_chunk(
                                    chunk_content,
                                    model_name,
                                    response_id
                                )
                                yield chunk_str
                    
                    # If we should retry, break and continue outer loop
                    if should_retry:
                        break
                    
                    # Stream completed successfully
                    logger.debug(f"Stream completed: {chunk_count} chunks processed, {len(full_content)} chars of content")
                    
                    # Send final chunk with usage (include system_content with [API] indicator)
                    usage = token_counter.calculate_usage(openai_messages, full_content, model_name, system_content=system_content)
                    
                    # Build final chunk using ResponseBuilder
                    final_chunk_str = response_builder.build_final_stream_chunk(
                        model_name,
                        response_id,
                        usage
                    )
                    yield final_chunk_str
                    yield response_builder.build_done_chunk()
                    return  # Success, exit function
                    
                except Exception as stream_error:
                    # Handle error using ErrorHandler
                    error_result = await error_handler.handle_error(
                        stream_error,
                        agent_id,
                        attempt,
                        max_retries,
                        retry_on_context_full,
                        is_streaming=True,
                        summarize_func=summarize_agent_conversation
                    )
                    
                    if error_result.should_retry:
                        continue  # Retry outer loop
                    else:
                        # Not retryable, yield error and return
                        if isinstance(error_result.error_response, str):
                            yield error_result.error_response
                        else:
                            # Fallback error chunk
                            logger.error(f"Error iterating stream: {type(stream_error).__name__}: {str(stream_error)}", exc_info=True)
                            error_chunk_str = error_handler.format_error_response(
                                stream_error,
                                error_result.error_type or ErrorType.SERVER_ERROR,
                                is_streaming=True
                            )
                            yield error_chunk_str
                        return
                
            except Exception as e:
                # Handle error using ErrorHandler
                error_result = await error_handler.handle_error(
                    e,
                    agent_id,
                    attempt,
                    max_retries,
                    retry_on_context_full,
                    is_streaming=True,
                    summarize_func=summarize_agent_conversation
                )
                
                if error_result.should_retry:
                    continue  # Retry outer loop
                else:
                    # Not retryable, yield error and return
                    if isinstance(error_result.error_response, str):
                        yield error_result.error_response
                    else:
                        # Fallback error chunk
                        logger.error(f"Error in streaming response: {str(e)}", exc_info=True)
                        error_chunk_str = error_handler.format_error_response(
                            e,
                            error_result.error_type or ErrorType.SERVER_ERROR,
                            is_streaming=True
                        )
                        yield error_chunk_str
                    return
        
        # If we get here, all retries failed
        error_chunk_str = error_handler.format_error_response(
            Exception("Failed to generate stream after retries"),
            ErrorType.SERVER_ERROR,
            is_streaming=True
        )
        yield error_chunk_str

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

# is_context_window_full_error is now in ErrorHandler class

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

# Initialize request_processor after check_token_capacity is defined
request_processor = RequestProcessor(
    model_registry,
    message_translator,
    token_counter,
    tool_synchronizer,
    letta_client,
    check_token_capacity
)

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """Main OpenAI-compatible chat completions endpoint"""
    
    try:
        # HTTP validation: model check
        if not model_registry.is_valid_model(request.model):
            raise HTTPException(
                status_code=400,
                detail={"error": {"message": f"Unknown model: {request.model}", "type": "invalid_request_error"}}
            )
        
        # Delegate business logic to RequestProcessor
        try:
            processed = await request_processor.process_request(request, user_id=request.user)
        except ValueError as e:
            # Business logic validation error - convert to HTTP error
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "message": str(e),
                        "type": "invalid_request_error",
                        "code": "context_length_exceeded"
                    }
                }
            )
        
        # Route to appropriate handler (HTTP concern)
        if request.stream:
            # For streaming, we need to yield from generator, so handle queueing inline
            return await handle_streaming_response_with_queue(
                load_manager,
                processed.agent_id,
                processed.message_objects,
                processed.model_name,
                processed.openai_messages,
                processed.system_content,
                processed.user_id,
                max_tokens=processed.max_tokens,
                temperature=processed.temperature
            )
        else:
            # For non-streaming, use queue processing
            async def processor():
                return await handle_non_streaming_response(
                    processed.agent_id,
                    processed.message_objects,
                    processed.model_name,
                    processed.openai_messages,
                    processed.system_content,
                    processed.user_id,
                    max_tokens=processed.max_tokens,
                    temperature=processed.temperature
                )
            
            return await load_manager.process_with_queue(
                processed.agent_id,
                processed.openai_messages,
                processor,
                user_id=processed.user_id
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing chat completion: {str(e)}", exc_info=True)
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
    logger.info(f"Starting The Librarian on {config.host}:{config.port}")
    logger.info(f"Debug mode: {config.debug}")
    logger.info(f"Documentation: {'enabled' if (config.debug or config.enable_docs) else 'disabled'}")
    
    uvicorn.run(
        "main:app",
        host=config.host,
        port=config.port,
        reload=config.debug,
        log_level="debug" if config.debug else "info",
        timeout_keep_alive=config.keep_alive_timeout,
        limit_max_requests=config.max_request_size,
        access_log=config.debug
    )
