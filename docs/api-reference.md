# The Librarian - API Reference

**License**: [CC-BY-SA-4.0](../LICENSE-DOCS)

## Overview

The Librarian provides full OpenAI API compatibility. All endpoints follow the OpenAI API specification, making it a drop-in replacement for OpenAI API calls.

## Base URL

```
http://localhost:8000
```

Or your configured `LIBRARIAN_HOST` and `LIBRARIAN_PORT`.

## Authentication

If `LIBRARIAN_API_KEY_REQUIRED=true`, include the API key in the `Authorization` header:

```
Authorization: Bearer YOUR_API_KEY
```

## Endpoints

### List Models

List all available models.

**Endpoint**: `GET /v1/models`

**Response**:
```json
{
  "object": "list",
  "data": [
    {
      "id": "gpt-4.1",
      "object": "model",
      "created": 1677610602,
      "owned_by": "openai"
    },
    {
      "id": "gpt-4",
      "object": "model",
      "created": 1677610602,
      "owned_by": "openai"
    }
  ]
}
```

### Get Model

Get information about a specific model.

**Endpoint**: `GET /v1/models/{model_id}`

**Parameters**:
- `model_id` (path): The model identifier

**Response**:
```json
{
  "id": "gpt-4.1",
  "object": "model",
  "created": 1677610602,
  "owned_by": "openai"
}
```

### Create Chat Completion

Create a chat completion.

**Endpoint**: `POST /v1/chat/completions`

**Request Body**:
```json
{
  "model": "gpt-4.1",
  "messages": [
    {
      "role": "system",
      "content": "You are a helpful assistant."
    },
    {
      "role": "user",
      "content": "Hello, how are you?"
    }
  ],
  "temperature": 0.7,
  "max_tokens": 1000,
  "stream": false
}
```

**Parameters**:
- `model` (string, required): The model to use
- `messages` (array, required): Array of message objects
  - `role` (string, required): "system", "user", "assistant", or "tool"
  - `content` (string, required): Message content
  - `name` (string, optional): Name for the message
  - `tool_calls` (array, optional): Tool calls (for assistant messages)
  - `tool_call_id` (string, optional): Tool call ID (for tool messages)
- `temperature` (number, optional): Sampling temperature (0-2)
- `max_tokens` (integer, optional): Maximum tokens to generate
- `stream` (boolean, optional): Whether to stream the response
- `tools` (array, optional): Tools available to the model
- `user` (string, optional): User identifier for conversation tracking

**Non-Streaming Response**:
```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1677652288,
  "model": "gpt-4.1",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello! I'm doing well, thank you for asking."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 25,
    "completion_tokens": 12,
    "total_tokens": 37
  }
}
```

**Streaming Response** (Server-Sent Events):

When `stream=true`, the response is sent as Server-Sent Events (SSE):

```
data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1677652288,"model":"gpt-4.1","choices":[{"index":0,"delta":{"content":"Hello"},"finish_reason":null}]}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1677652288,"model":"gpt-4.1","choices":[{"index":0,"delta":{"content":"!"},"finish_reason":null}]}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1677652288,"model":"gpt-4.1","choices":[{"index":0,"delta":{},"finish_reason":"stop"}],"usage":{"prompt_tokens":25,"completion_tokens":12,"total_tokens":37}}

data: [DONE]
```

### Create Completion (Legacy)

Legacy completion endpoint.

**Endpoint**: `POST /v1/completions`

**Request Body**:
```json
{
  "model": "gpt-4.1",
  "prompt": "Hello, how are you?",
  "temperature": 0.7,
  "max_tokens": 1000
}
```

**Response**:
```json
{
  "id": "cmpl-123",
  "object": "text_completion",
  "created": 1677652288,
  "model": "gpt-4.1",
  "choices": [
    {
      "text": "Hello! I'm doing well, thank you for asking.",
      "index": 0,
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 8,
    "completion_tokens": 12,
    "total_tokens": 20
  }
}
```

### Health Check

Check service health.

**Endpoint**: `GET /health`

**Response**:
```json
{
  "status": "healthy",
  "service": "The Librarian",
  "version": "0.1.0"
}
```

### Root Endpoint

Get service information.

**Endpoint**: `GET /`

**Response**:
```json
{
  "service": "The Librarian",
  "description": "OpenAI-Compatible Letta Proxy",
  "version": "0.1.0",
  "endpoints": {
    "models": "/v1/models",
    "chat_completions": "/v1/chat/completions",
    "completions": "/v1/completions",
    "health": "/health"
  }
}
```

## Error Responses

All errors follow OpenAI API error format:

```json
{
  "error": {
    "message": "Error description",
    "type": "invalid_request_error",
    "code": "context_length_exceeded"
  }
}
```

**Error Types**:
- `invalid_request_error`: Invalid request parameters
- `server_error`: Server-side error
- `rate_limit_error`: Rate limit exceeded

**Error Codes**:
- `context_length_exceeded`: Request exceeds model's context window
- `model_not_found`: Model not available
- `invalid_api_key`: Invalid API key

## Rate Limiting

If rate limiting is enabled, responses include rate limit headers:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 99
X-RateLimit-Reset: 1677652288
```

## Examples

### Python (OpenAI SDK)

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="not-needed"  # Or your API key if required
)

response = client.chat.completions.create(
    model="gpt-4.1",
    messages=[
        {"role": "user", "content": "Hello!"}
    ]
)

print(response.choices[0].message.content)
```

### Python (Streaming)

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="not-needed"
)

stream = client.chat.completions.create(
    model="gpt-4.1",
    messages=[
        {"role": "user", "content": "Tell me a story"}
    ],
    stream=True
)

for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

### cURL

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4.1",
    "messages": [
      {"role": "user", "content": "Hello!"}
    ]
  }'
```

### JavaScript (Fetch)

```javascript
const response = await fetch('http://localhost:8000/v1/chat/completions', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    model: 'gpt-4.1',
    messages: [
      { role: 'user', content: 'Hello!' }
    ]
  })
});

const data = await response.json();
console.log(data.choices[0].message.content);
```

## Differences from OpenAI API

The Librarian maintains full compatibility with the OpenAI API, with these enhancements:

1. **Persistent Context**: Conversations persist across sessions via Letta memory
2. **Tool Access**: SMCP/MCP tools available through the agent
3. **Dual-Mode Operation**: Automatic Worker/Persona mode switching
4. **Context Management**: Automatic context window adjustment and summarization
5. **Per-Request Configuration**: Dynamic temperature and max_tokens per request

All standard OpenAI API features are supported, making The Librarian a drop-in replacement.

