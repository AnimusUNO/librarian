# OpenAI ChatCompletion API vs Letta API Mapping

## OpenAI ChatCompletion Endpoints Analysis

### Core Endpoint
- **URL**: `POST /v1/chat/completions`
- **Purpose**: Generate chat completions using language models

### Request Parameters

#### Required Parameters
- **`model`** (string): Model identifier (e.g., "gpt-3.5-turbo", "gpt-4")
- **`messages`** (array): Conversation history
  - **`role`** (string): "system", "user", "assistant", "tool"
  - **`content`** (string|array): Message content
  - **`tool_calls`** (array): Tool calls made by assistant
  - **`tool_call_id`** (string): ID for tool call results

#### Optional Parameters
- **`temperature`** (float): Randomness control (0.0-2.0, default: 1.0)
- **`top_p`** (float): Nucleus sampling (0.0-1.0, default: 1.0)
- **`max_tokens`** (integer): Maximum tokens to generate
- **`stream`** (boolean): Enable streaming responses
- **`stop`** (string|array): Stop sequences
- **`presence_penalty`** (float): Presence penalty (-2.0 to 2.0)
- **`frequency_penalty`** (float): Frequency penalty (-2.0 to 2.0)
- **`logit_bias`** (object): Token bias adjustments
- **`user`** (string): User identifier for abuse monitoring
- **`n`** (integer): Number of completions to generate
- **`tools`** (array): Available tools for function calling
- **`tool_choice`** (string|object): Tool selection strategy

### Response Structure
```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1677858242,
  "model": "gpt-3.5-turbo",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Response content",
        "tool_calls": [
          {
            "id": "call_abc123",
            "type": "function",
            "function": {
              "name": "get_weather",
              "arguments": "{\"location\": \"San Francisco\"}"
            }
          }
        ]
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 56,
    "completion_tokens": 17,
    "total_tokens": 73
  }
}
```

### Streaming Response
- **Content-Type**: `text/event-stream`
- **Format**: Server-Sent Events (SSE)
- **Structure**: Multiple chunks with `data:` prefix
- **Final chunk**: `data: [DONE]`

## Letta API Capabilities Mapping

### Direct Mappings ✅

#### 1. **Core Chat Functionality**
- **OpenAI**: `POST /v1/chat/completions`
- **Letta**: `POST /agents/{id}/messages/create`
- **Mapping**: Direct 1:1 mapping possible

#### 2. **Message Structure**
- **OpenAI**: `messages` array with `role` and `content`
- **Letta**: `MessageCreate` objects with `role` and `content`
- **Mapping**: Direct compatibility

#### 3. **Streaming Support**
- **OpenAI**: `stream: true` parameter
- **Letta**: `create_stream()` method
- **Mapping**: Both support streaming responses

#### 4. **Tool/Function Calling**
- **OpenAI**: `tools` parameter with function definitions
- **Letta**: Tool management via `/tools` endpoints
- **Mapping**: Can be mapped through tool synchronization

### Partial Mappings ⚠️

#### 1. **Model Selection**
- **OpenAI**: `model` parameter (string)
- **Letta**: Agent-based (each agent is a "model")
- **Mapping**: Map OpenAI model names to Letta agent IDs

#### 2. **System Messages**
- **OpenAI**: `role: "system"` in messages
- **Letta**: System prompts via memory blocks/overlay
- **Mapping**: Convert system messages to Letta memory blocks

#### 3. **Temperature/Parameters**
- **OpenAI**: `temperature`, `top_p`, `max_tokens`
- **Letta**: Provider-level configuration
- **Mapping**: Pass through to underlying LLM provider

### Advanced Mappings 🔄

#### 1. **Identity Management**
- **OpenAI**: `user` parameter (basic)
- **Letta**: Full identity system with persistent memory
- **Enhancement**: Use Letta identities for advanced context

#### 2. **Memory Persistence**
- **OpenAI**: Stateless (conversation in messages)
- **Letta**: Persistent memory blocks and archival memory
- **Enhancement**: Maintain conversation history in Letta memory

#### 3. **Tool Management**
- **OpenAI**: Static tool definitions per request
- **Letta**: Dynamic tool discovery and MCP integration
- **Enhancement**: Real-time tool synchronization

## Implementation Strategy for The Librarian

### 1. **Core Proxy Layer**
```python
@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    # Map OpenAI model to Letta agent
    agent_id = map_model_to_agent(request.model)
    
    # Convert OpenAI messages to Letta format
    letta_messages = convert_messages(request.messages)
    
    # Handle system prompts via memory blocks
    if has_system_messages(request.messages):
        await apply_system_overlay(agent_id, request.messages)
    
    # Send to Letta agent
    if request.stream:
        return stream_response(agent_id, letta_messages)
    else:
        return await get_completion(agent_id, letta_messages)
```

### 2. **Model Mapping**
```python
def map_model_to_agent(model_name: str) -> str:
    """Map OpenAI model names to Letta agent IDs"""
    model_mapping = {
        "gpt-3.5-turbo": "librarian-worker",
        "gpt-4": "librarian-persona",
        "gpt-4-turbo": "librarian-persona-turbo"
    }
    return model_mapping.get(model_name, "librarian-default")
```

### 3. **Message Conversion**
```python
def convert_messages(openai_messages: List[dict]) -> List[MessageCreate]:
    """Convert OpenAI messages to Letta MessageCreate format"""
    letta_messages = []
    for msg in openai_messages:
        if msg["role"] == "system":
            # Handle via memory blocks instead
            continue
        elif msg["role"] == "user":
            letta_messages.append(MessageCreate(
                role="user",
                content=[TextContent(text=msg["content"])]
            ))
        elif msg["role"] == "assistant":
            letta_messages.append(MessageCreate(
                role="assistant", 
                content=[TextContent(text=msg["content"])]
            ))
        elif msg["role"] == "tool":
            letta_messages.append(MessageCreate(
                role="tool",
                content=[TextContent(text=msg["content"])],
                tool_call_id=msg.get("tool_call_id")
            ))
    return letta_messages
```

### 4. **Tool Synchronization**
```python
async def sync_tools(agent_id: str, openai_tools: List[dict]):
    """Sync OpenAI tool definitions with Letta agent"""
    for tool in openai_tools:
        if tool["type"] == "function":
            # Create or update tool in Letta
            await letta_client.tools.upsert(
                name=tool["function"]["name"],
                description=tool["function"]["description"],
                parameters=tool["function"]["parameters"]
            )
            # Attach to agent
            await letta_client.agents.tools.attach(agent_id, tool["function"]["name"])
```

### 5. **Response Formatting**
```python
def format_openai_response(letta_response: LettaResponse, model_name: str) -> dict:
    """Convert Letta response to OpenAI format"""
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model_name,
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": letta_response.content
            },
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": letta_response.usage.prompt_tokens,
            "completion_tokens": letta_response.usage.completion_tokens,
            "total_tokens": letta_response.usage.total_tokens
        }
    }
```

## Supported vs Unsupported Features

### ✅ **Fully Supported**
- Basic chat completions
- Streaming responses
- Message history
- Tool/function calling
- Multiple completion choices
- Token usage statistics
- Stop sequences
- User identification

### ⚠️ **Partially Supported**
- System messages (via memory blocks)
- Temperature/top_p (passed to provider)
- Max tokens (provider-dependent)
- Tool choice (Letta agent decides)

### ❌ **Not Supported**
- Logit bias (provider-specific)
- Presence/frequency penalties (provider-specific)
- Multiple completions (n > 1) - Letta is deterministic
- Custom stop sequences (provider-dependent)

## Benefits of Letta Integration

### 1. **Enhanced Capabilities**
- **Persistent Memory**: Conversations persist across sessions
- **Identity Management**: User-specific context and memory
- **Advanced Tool Integration**: MCP protocol support
- **Archival Memory**: Pattern learning and self-improvement

### 2. **The Librarian Advantages**
- **Dual-Mode Behavior**: Worker vs Persona mode switching
- **System Prompt Management**: Unlimited length via memory blocks
- **Tool Documentation**: Automatic SMCP tool documentation
- **Context Continuity**: Maintains conversation context

### 3. **Production Features**
- **Load Management**: Auto-duplication for high concurrency
- **Error Handling**: Comprehensive fallback mechanisms
- **Health Monitoring**: Built-in health checks
- **Debug Capabilities**: Raw output logging and session debugging

## Conclusion

The Letta API can be fully conformed to OpenAI ChatCompletion endpoints with significant enhancements. The mapping is straightforward for core functionality, while Letta's advanced features (memory, identity, tools) provide substantial value-adds for The Librarian implementation.

The key is maintaining OpenAI compatibility while leveraging Letta's stateful, memory-enabled architecture for superior user experiences.
