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
from typing import Dict, Any, Optional, AsyncGenerator
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv
from letta_client import Letta, MessageCreate

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

# Initialize components
model_registry = ModelRegistry()
message_translator = MessageTranslator()
response_formatter = ResponseFormatter()
token_counter = TokenCounter()

# Initialize Letta client with configuration
letta_client = Letta(
    base_url=letta_base_url,
    token=letta_api_key,
    timeout=letta_timeout
)

# Initialize advanced components
tool_synchronizer = ToolSynchronizer(letta_client)
load_manager = LoadManager()

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
        # Create message with Letta client
        response = letta_client.agents.messages.create(
            agent_id=agent_id,
            messages=message_objects
        )
        
        # Extract response content
        response_content = response_formatter._extract_content(response)
        
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
        
    except Exception as e:
        logger.error(f"Error in non-streaming response: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": {"message": "Failed to generate response", "type": "server_error"}}
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
            stream = letta_client.agents.messages.create_stream(
                agent_id=agent_id,
                messages=message_objects
            )
            
            response_id = f"chatcmpl-{uuid.uuid4().hex}"
            full_content = ""
            
            # Stream chunks
            for chunk in stream:
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
                    
                    yield f"data: {chunk_data}\n\n"
            
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
            
            yield f"data: {final_chunk}\n\n"
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            logger.error(f"Error in streaming response: {str(e)}")
            error_chunk = {
                "error": {
                    "message": "Streaming error occurred",
                    "type": "server_error"
                }
            }
            yield f"data: {error_chunk}\n\n"
    
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
        
        # Convert to MessageCreate objects
        message_objects = []
        for msg in letta_messages:
            message_objects.append(MessageCreate(
                role=msg["role"],
                content=msg["content"]
            ))
        
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
