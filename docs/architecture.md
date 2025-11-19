# The Librarian - Architecture Documentation

**License**: [CC-BY-SA-4.0](../LICENSE-DOCS)

## Overview

The Librarian is a stateful, OpenAI-compatible gateway that translates OpenAI API requests into Letta agent interactions. It maintains full compatibility with the OpenAI API while providing persistent context, tool access, and self-tuning behavior through Letta agents.

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    External Clients                          │
│  (OpenAI SDK, LangChain, Cursor, Autogen, etc.)            │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ HTTP/HTTPS
                       │ OpenAI API Protocol
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              The Librarian Gateway (FastAPI)                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Request Handler Layer                               │  │
│  │  - /v1/models                                        │  │
│  │  - /v1/chat/completions                              │  │
│  │  - /v1/completions                                   │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Core Components                                     │  │
│  │  - ModelRegistry: Model-to-agent mapping            │  │
│  │  - MessageTranslator: OpenAI ↔ Letta conversion     │  │
│  │  - ResponseFormatter: Letta → OpenAI formatting     │  │
│  │  - TokenCounter: Token counting & usage              │  │
│  │  - ToolSynchronizer: Tool attachment                │  │
│  │  - LoadManager: Request queuing & load balancing   │  │
│  └──────────────────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ Letta API
                       │ (HTTP/HTTPS)
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    Letta Server                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  The Librarian Agent (Persistent)                      │  │
│  │  - Core Memory: Identity & heuristics                 │  │
│  │  - Recall Memory: Conversation history                 │  │
│  │  - Archival Memory: Long-term knowledge                │  │
│  │  - Tools: SMCP/MCP toolchains                         │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  LLM Provider (OpenAI, Anthropic, Venice, etc.)     │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. ModelRegistry

**Purpose**: Maps OpenAI model names to Letta agent configurations.

**Key Features**:
- Model-to-agent ID mapping
- Mode selection (worker/persona)
- Custom model support via environment variables
- Default model fallback

**Location**: `src/librarian/model_registry.py`

**Configuration**:
- Default models: `gpt-3.5-turbo`, `gpt-4`, `gpt-4.1`, `gpt-4-turbo`
- Custom models via `LIBRARIAN_CUSTOM_MODELS` environment variable
- Additional models via `LIBRARIAN_ADDITIONAL_MODELS` environment variable

### 2. MessageTranslator

**Purpose**: Converts OpenAI message format to Letta MessageCreate format.

**Key Features**:
- System message extraction and handling
- Role mapping (user, assistant, system, tool)
- Content format conversion
- Mode selection instruction injection
- API call indicator (`[API]`) injection

**Location**: `src/librarian/message_translator.py`

**Translation Flow**:
1. Extract system messages → system_content
2. Convert user/assistant messages → Letta format
3. Add `[API]` indicator to system_content
4. Add mode selection instructions
5. Return Letta messages + system_content

### 3. ResponseFormatter

**Purpose**: Formats Letta agent responses into OpenAI-compatible format.

**Key Features**:
- Content extraction from Letta chunks
- Reasoning block filtering
- Streaming response formatting
- Error message formatting
- Usage statistics formatting

**Location**: `src/librarian/response_formatter.py`

**Formatting**:
- Extracts text content from Letta message chunks
- Filters out reasoning blocks (private deliberation)
- Formats as OpenAI chat completion response
- Includes usage statistics (prompt_tokens, completion_tokens, total_tokens)

### 4. TokenCounter

**Purpose**: Accurate token counting and usage calculation.

**Key Features**:
- Model-specific token encoding (tiktoken)
- Message token counting
- Response token counting
- Usage statistics calculation
- Cost estimation
- System content token inclusion

**Location**: `src/librarian/token_counter.py`

**Supported Models**:
- `gpt-3.5-turbo`: cl100k_base encoding
- `gpt-4`, `gpt-4.1`, `gpt-4-turbo`: cl100k_base encoding
- `gpt-4o`, `gpt-4o-mini`: o200k_base encoding

**Token Counting**:
- Includes `[API]` indicator in token counts
- Includes mode selection instructions
- Includes system content
- Accurate prompt and completion token calculation

### 5. ToolSynchronizer

**Purpose**: Synchronizes OpenAI function calling tools with Letta agent tools.

**Key Features**:
- Dynamic tool attachment
- Tool format conversion
- Tool call handling
- Tool response formatting

**Location**: `src/librarian/tool_synchronizer.py`

**Synchronization Flow**:
1. Receive OpenAI tools from request
2. Convert to Letta tool format
3. Attach to agent via Letta API
4. Handle tool calls during conversation
5. Format tool responses back to OpenAI format

### 6. LoadManager

**Purpose**: Manages request load, queuing, and auto-duplication.

**Key Features**:
- Request queuing with buffered queues
- Semaphore-based concurrency control
- Auto-duplication for high load
- Request status tracking
- Queue timeout handling

**Location**: `src/librarian/load_manager.py`

**Load Management**:
- `max_concurrent`: Maximum concurrent requests per agent
- `duplication_threshold`: Queue size threshold for auto-duplication
- `max_clones_per_agent`: Maximum agent clones
- Request status: QUEUED → PROCESSING → COMPLETED

## Request Flow

### Non-Streaming Request

```
1. Client sends POST /v1/chat/completions
   ↓
2. Request validation (model, messages, parameters)
   ↓
3. ModelRegistry: Get agent_id for model
   ↓
4. TokenCounter: Estimate prompt tokens
   ↓
5. check_token_capacity: Validate token limits
   ↓
6. MessageTranslator: Convert messages to Letta format
   ↓
7. Add [API] indicator and mode instructions
   ↓
8. LoadManager: Queue request (if needed)
   ↓
9. configure_agent_for_request: Set temperature/max_tokens
   ↓
10. Letta API: Create stream (collect all chunks)
    ↓
11. ResponseFormatter: Extract content from chunks
    ↓
12. TokenCounter: Calculate usage (with system_content)
    ↓
13. restore_agent_config: Restore original config
    ↓
14. Return OpenAI-formatted response
```

### Streaming Request

```
1. Client sends POST /v1/chat/completions (stream=true)
   ↓
2. Request validation
   ↓
3. ModelRegistry: Get agent_id
   ↓
4. MessageTranslator: Convert messages
   ↓
5. LoadManager: Queue request
   ↓
6. configure_agent_for_request: Set config
   ↓
7. Letta API: Create stream
   ↓
8. For each chunk:
   - Extract content
   - Format as SSE chunk
   - Yield to client
   ↓
9. Final chunk: Include usage statistics
   ↓
10. restore_agent_config: Restore config
    ↓
11. Stream complete
```

## Error Handling

### Context Window Full

When a request exceeds the agent's context window:

1. Detect "context window full" error
2. Call `summarize_agent_conversation()` via Letta API
3. Retry the original request
4. If retry fails, return error to client

### Token Capacity

- **Pre-request validation**: Check if `max_tokens` exceeds model's absolute maximum
- **Dynamic adjustment**: Automatically adjust agent's context window if needed
- **Summarization**: Automatically summarize conversation if context is full

### Agent Configuration

- **Per-request config**: Set `temperature` and `max_tokens` for each request
- **Config restoration**: Always restore original config after request
- **Error handling**: Ensure config is restored even on errors

## Memory Architecture

### Letta Memory Blocks

The Librarian agent uses three types of Letta memory:

1. **Core Memory**: Immutable identity and operational heuristics
2. **Recall Memory**: Conversation history and short-term awareness
3. **Archival Memory**: Long-term knowledge and patterns

### Memory Management

- **No self-pruning**: The agent does not prune its own memory
- **Summarization**: Automatic summarization when context window is full
- **Archival insertion**: Long-term insights stored in archival memory
- **Context retrieval**: Semantic search across archival memory

## Security Architecture

### Request Validation

- Input validation for all request parameters
- Message format validation
- Model name validation
- Token limit validation

### Authentication

- Optional API key authentication
- IP filtering (allow/block lists)
- Rate limiting (configurable)

### Security Logging

- Security event logging
- Audit trail for authentication attempts
- Request logging (optional)

## Performance Architecture

### Concurrency Control

- **Semaphore-based**: Limits concurrent requests per agent
- **Queue-based**: Buffers requests when at capacity
- **Auto-duplication**: Creates agent clones for high load

### Request Queuing

- **Buffered queues**: Per-agent request queues
- **Status tracking**: QUEUED → PROCESSING → COMPLETED
- **Timeout handling**: Queue timeout configuration

### Load Balancing

- **Agent duplication**: Automatic cloning at threshold
- **Load distribution**: Requests distributed across clones
- **Clone management**: Automatic cleanup of completed clones

## Configuration Architecture

### Environment Variables

All configuration via environment variables:
- Server configuration
- Letta server connection
- Agent configuration
- Security settings
- Performance tuning
- Logging configuration

### Configuration Loading

1. Load from `.env` file (if present)
2. Override with environment variables
3. Validate required settings
4. Apply defaults for optional settings

## Extension Points

### Custom Models

Add custom models via:
- `LIBRARIAN_CUSTOM_MODELS` environment variable
- `LIBRARIAN_ADDITIONAL_MODELS` environment variable

### Custom Tools

Tools synchronized via:
- `ToolSynchronizer` component
- OpenAI function calling format
- Letta tool attachment API

### Custom Handlers

Extend request handling via:
- FastAPI route handlers
- Custom middleware
- Request/response interceptors

## Design Decisions

### Why FastAPI?

- High performance async framework
- Automatic API documentation
- Type validation with Pydantic
- Easy to extend

### Why Streaming for Non-Streaming?

- Letta's `create()` API has limitations
- Streaming works reliably
- Content collection is transparent to client

### Why Per-Request Config?

- Letta agents have persistent config
- Need to support per-request parameters
- Must restore original config after request

### Why [API] Indicator?

- Agent needs to know request source
- Distinguishes API calls from direct chat
- Enables different behavior if needed

## Future Architecture Considerations

### Caching

- Response caching for identical requests
- Token counting cache
- Model registry cache

### Metrics

- Prometheus metrics endpoint
- Request/response metrics
- Performance metrics

### Multi-Tenancy

- User identity management
- Per-user conversation history
- Resource isolation

### Distributed Deployment

- Horizontal scaling
- Shared state management
- Load balancing across instances

