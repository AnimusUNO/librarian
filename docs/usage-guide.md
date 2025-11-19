# The Librarian - Usage Guide

**License**: [CC-BY-SA-4.0](../LICENSE-DOCS)

## Quick Start

### 1. Installation

See [README.md](../README.md) for installation instructions.

### 2. Bootstrap Agents

Before using The Librarian, bootstrap the agents in your Letta server:

```bash
cd bootstrap
python bootstrap_librarian.py --config bootstrap.env
```

### 3. Start The Librarian

```bash
python main.py
```

The server will start at `http://127.0.0.1:8000` (or your configured host/port).

## Using with OpenAI SDK

The Librarian is a drop-in replacement for the OpenAI API. Simply change the `base_url`:

```python
from openai import OpenAI

# Instead of OpenAI's default API
# client = OpenAI()

# Use The Librarian
client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="not-needed"  # Or your API key if LIBRARIAN_API_KEY_REQUIRED=true
)

# Use exactly like OpenAI API
response = client.chat.completions.create(
    model="gpt-4.1",
    messages=[
        {"role": "user", "content": "Hello!"}
    ]
)

print(response.choices[0].message.content)
```

## Basic Usage Examples

### Simple Chat

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1")

response = client.chat.completions.create(
    model="gpt-4.1",
    messages=[
        {"role": "user", "content": "What is the capital of France?"}
    ]
)

print(response.choices[0].message.content)
```

### Conversation with Context

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1")

messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "My name is Alice."},
    {"role": "assistant", "content": "Hello Alice! How can I help you?"},
    {"role": "user", "content": "What's my name?"}
]

response = client.chat.completions.create(
    model="gpt-4.1",
    messages=messages
)

print(response.choices[0].message.content)  # Should remember "Alice"
```

### Streaming Responses

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1")

stream = client.chat.completions.create(
    model="gpt-4.1",
    messages=[
        {"role": "user", "content": "Tell me a short story"}
    ],
    stream=True
)

for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
```

### Custom Temperature and Max Tokens

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1")

response = client.chat.completions.create(
    model="gpt-4.1",
    messages=[
        {"role": "user", "content": "Write a creative story"}
    ],
    temperature=0.9,  # More creative
    max_tokens=2000   # Longer response
)

print(response.choices[0].message.content)
```

## Advanced Usage

### Function Calling / Tools

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1")

response = client.chat.completions.create(
    model="gpt-4.1",
    messages=[
        {"role": "user", "content": "What's the weather in San Francisco?"}
    ],
    tools=[
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get the current weather in a location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The city and state"
                        }
                    },
                    "required": ["location"]
                }
            }
        }
    ]
)

# Handle tool calls
message = response.choices[0].message
if message.tool_calls:
    for tool_call in message.tool_calls:
        print(f"Tool: {tool_call.function.name}")
        print(f"Arguments: {tool_call.function.arguments}")
```

### User Identity for Conversation Tracking

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1")

# Use the same user ID to maintain conversation context
response = client.chat.completions.create(
    model="gpt-4.1",
    messages=[
        {"role": "user", "content": "Hello, my name is Bob"}
    ],
    user="user-123"  # User identifier
)

# Later, same user ID maintains context
response2 = client.chat.completions.create(
    model="gpt-4.1",
    messages=[
        {"role": "user", "content": "What's my name?"}
    ],
    user="user-123"  # Same user ID
)
```

## Using with LangChain

```python
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage

# Configure LangChain to use The Librarian
llm = ChatOpenAI(
    base_url="http://localhost:8000/v1",
    api_key="not-needed",
    model="gpt-4.1"
)

messages = [HumanMessage(content="Hello!")]
response = llm.invoke(messages)
print(response.content)
```

## Using with cURL

### Simple Request

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

### Streaming Request

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4.1",
    "messages": [
      {"role": "user", "content": "Tell me a story"}
    ],
    "stream": true
  }'
```

## Using with JavaScript/TypeScript

### Fetch API

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

### Streaming with Fetch

```javascript
const response = await fetch('http://localhost:8000/v1/chat/completions', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    model: 'gpt-4.1',
    messages: [
      { role: 'user', content: 'Tell me a story' }
    ],
    stream: true
  })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  
  const chunk = decoder.decode(value);
  const lines = chunk.split('\n');
  
  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const data = line.slice(6);
      if (data === '[DONE]') break;
      
      const json = JSON.parse(data);
      if (json.choices[0].delta.content) {
        process.stdout.write(json.choices[0].delta.content);
      }
    }
  }
}
```

## Best Practices

### 1. Use User IDs for Conversation Tracking

Always provide a `user` parameter to maintain conversation context:

```python
response = client.chat.completions.create(
    model="gpt-4.1",
    messages=[...],
    user="unique-user-id"  # Important for context
)
```

### 2. Handle Large Token Requests

For large token requests, The Librarian automatically:
- Adjusts context window if needed
- Summarizes conversation if context is full
- Retries the request after summarization

### 3. Set Appropriate Temperature

- `temperature=0.0-0.3`: Factual, deterministic responses
- `temperature=0.7`: Balanced creativity
- `temperature=1.0-2.0`: Highly creative responses

### 4. Monitor Token Usage

Check the `usage` field in responses:

```python
response = client.chat.completions.create(...)
print(f"Prompt tokens: {response.usage.prompt_tokens}")
print(f"Completion tokens: {response.usage.completion_tokens}")
print(f"Total tokens: {response.usage.total_tokens}")
```

### 5. Handle Errors Gracefully

```python
from openai import OpenAI, APIError

client = OpenAI(base_url="http://localhost:8000/v1")

try:
    response = client.chat.completions.create(...)
except APIError as e:
    print(f"API Error: {e.message}")
    print(f"Error type: {e.type}")
    print(f"Error code: {e.code}")
```

## Troubleshooting

### Connection Errors

**Problem**: Cannot connect to The Librarian

**Solutions**:
- Check that The Librarian is running: `curl http://localhost:8000/health`
- Verify `LIBRARIAN_HOST` and `LIBRARIAN_PORT` configuration
- Check firewall settings

### Model Not Found

**Problem**: `model_not_found` error

**Solutions**:
- Check available models: `curl http://localhost:8000/v1/models`
- Verify model name matches exactly
- Check `ModelRegistry` configuration

### Context Length Exceeded

**Problem**: `context_length_exceeded` error

**Solutions**:
- Reduce `max_tokens` in request
- The Librarian will automatically summarize if possible
- Consider breaking long conversations into smaller parts

### Slow Responses

**Problem**: Responses are slow

**Solutions**:
- Check Letta server performance
- Monitor queue status
- Adjust `LIBRARIAN_MAX_CONCURRENT` if needed
- Consider using streaming for better perceived performance

## Next Steps

- See [API Reference](api-reference.md) for detailed API documentation
- See [Configuration Guide](configuration.md) for configuration options
- See [Architecture](architecture.md) for system architecture details

