#!/usr/bin/env python3
"""
The Librarian - OpenAI-Compatible Letta Proxy

A stateful, OpenAI-compatible gateway that allows clients to interface with 
a persistent Letta agent while speaking the standard OpenAI API protocol.

Copyright (c) 2025 AnimusUNO
Licensed under AGPLv3
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

# Import Librarian components
from src.librarian import ModelRegistry, MessageTranslator, ResponseFormatter, TokenCounter
from src.librarian.tool_synchronizer import ToolSynchronizer
from src.librarian.load_manager import LoadManager

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

async def handle_non_streaming_response(
    agent_id: str, 
    message_objects: list, 
    model_name: str,
    openai_messages: list,
    system_content: Optional[str],
    user_id: Optional[str]
) -> ChatCompletionResponse:
    """Handle non-streaming chat completion"""
    try:
        # Use create_stream() and collect chunks
        # Note: create() fails with this agent due to model_endpoint=None in agent config
        # Streaming works, so we use it for both streaming and non-streaming
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
                    logger.error(f"Error in Letta stream: {error_msg}")
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
        
        # Calculate token usage
        usage = token_counter.calculate_usage(openai_messages, response_content, model_name)
        
        # Format response
        return ChatCompletionResponse(
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
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error in non-streaming response: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": {"message": f"Failed to generate response: {str(e)}", "type": "server_error"}}
        )

async def handle_streaming_response(
    agent_id: str,
    message_objects: list,
    model_name: str,
    openai_messages: list,
    system_content: Optional[str],
    user_id: Optional[str]
) -> StreamingResponse:
    """Handle streaming chat completion"""
    
    async def generate_stream():
        try:
            # Create streaming message with Letta client
            # create_stream() returns an async generator, don't await it
            stream = letta_client.agents.messages.create_stream(
                agent_id=agent_id,
                messages=message_objects,
                stream_tokens=True  # Enable token-level streaming
            )
            
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
            
            # Send final chunk with usage
            usage = token_counter.calculate_usage(openai_messages, full_content, model_name)
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
        
        # Convert messages to Letta format
        openai_messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        letta_messages, system_content = message_translator.translate_messages(openai_messages)
        
        # Add mode selection instruction to system content
        mode_instruction = message_translator.create_mode_selection_instruction(agent_config['mode'])
        if system_content:
            system_content = f"{system_content}\n\n{mode_instruction}"
        else:
            system_content = mode_instruction
        
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
        
        # Handle streaming vs non-streaming
        if request.stream:
            return await handle_streaming_response(
                agent_id, message_objects, request.model, 
                openai_messages, system_content, request.user
            )
        else:
            return await handle_non_streaming_response(
                agent_id, message_objects, request.model,
                openai_messages, system_content, request.user
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
            model=request.get("model", "gpt-3.5-turbo"),
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
