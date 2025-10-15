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
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv

# Import Librarian components
from src.librarian import ModelRegistry, MessageTranslator, ResponseFormatter, TokenCounter

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="The Librarian",
    description="OpenAI-Compatible Letta Proxy",
    version="0.1.0",
    docs_url="/docs" if os.getenv("LIBRARIAN_DEBUG", "false").lower() == "true" else None,
    redoc_url="/redoc" if os.getenv("LIBRARIAN_DEBUG", "false").lower() == "true" else None,
)

# Initialize components
model_registry = ModelRegistry()
message_translator = MessageTranslator()
response_formatter = ResponseFormatter()
token_counter = TokenCounter()

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
    
    # Validate model
    if not model_registry.is_valid_model(request.model):
        raise HTTPException(
            status_code=400,
            detail={"error": {"message": f"Unknown model: {request.model}", "type": "invalid_request_error"}}
        )
    
    # Get agent configuration
    agent_config = model_registry.get_agent_config(request.model)
    logger.info(f"Processing request for model {request.model} -> agent {agent_config['agent_id']}")
    
    # Convert messages to Letta format
    openai_messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
    letta_messages, system_content = message_translator.translate_messages(openai_messages)
    
    # Generate placeholder response content
    response_content = f"Hello! I'm The Librarian in {agent_config['mode']} mode. This is a placeholder response while we implement the Letta integration."
    
    # Calculate accurate token usage
    usage = token_counter.calculate_usage(openai_messages, response_content, request.model)
    
    # TODO: Implement actual Letta integration
    # For now, return a placeholder response with accurate token counting
    response = ChatCompletionResponse(
        id="chatcmpl-placeholder",
        created=1700000000,
        model=request.model,
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
    
    if request.stream:
        # TODO: Implement streaming response
        return StreamingResponse(
            iter([f"data: {response.model_dump_json()}\n\n", "data: [DONE]\n\n"]),
            media_type="text/event-stream"
        )
    else:
        return response

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
    # Configuration
    host = os.getenv("LIBRARIAN_HOST", "127.0.0.1")
    port = int(os.getenv("LIBRARIAN_PORT", "8000"))
    debug = os.getenv("LIBRARIAN_DEBUG", "false").lower() == "true"
    
    logger.info(f"Starting The Librarian on {host}:{port}")
    logger.info(f"Debug mode: {debug}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="debug" if debug else "info"
    )
