
# Letta API Reference

## Overview

The Letta platform provides multiple ways to interact with your stateful agents through a comprehensive REST API and native SDKs in Python and TypeScript. All interfaces use the same underlying API to interact with your agents.

## Python SDK

<Note>
The legacy Letta Python `LocalClient`/`RestClient` SDK is available under `pip install letta` (which also contains the server).
This client is deprecated and will be replaced in a future release with the new `letta-client`.
Please migrate any Python code using the old `RESTClient` or `LocalClient` to use `letta-client` to avoid breaking changes in the future.
</Note>

The Letta [Python SDK](https://github.com/letta-ai/letta-python) can be downloaded with:
```bash
pip install letta-client
```

Once installed, you can instantiate the client in your Python code with:
```python
from letta_client import Letta

# connect to a local server
client = Letta(base_url="http://localhost:8283")

# connect to Letta Cloud
client = Letta(token="LETTA_API_KEY", project="default-project")
```

## TypeScript SDK

The Letta TypeScript (Node) SDK can be downloaded with:
```bash
npm install @letta-ai/letta-client
```

Once installed, you can instantiate the client in your TypeScript code with:
```typescript
import { LettaClient } from '@letta-ai/letta-client'

// connect to a local server
const client = new LettaClient({
  baseUrl: "http://localhost:8283",
})

// connect to Letta Cloud
const client = new LettaClient({
  token: "LETTA_API_KEY",
  project: "default-project",
})
```

## API Endpoints Overview

The Letta API provides comprehensive endpoints for managing agents, identities, blocks, tools, and more. Here's a complete reference:

### Core Endpoints

- **Health Check**: `GET /health` - Check server health status
- **Chat Completions**: `POST /chat/completions` - Create chat completions
- **Voice Chat**: `POST /voice/chat/completions` - Create voice chat completions

### Agents
- `GET /agents` - List agents
- `GET /agents/{id}` - Retrieve agent
- `POST /agents` - Create agent
- `PATCH /agents/{id}` - Modify agent
- `DELETE /agents/{id}` - Delete agent
- `GET /agents/count` - Count agents
- `POST /agents/import` - Import agent
- `GET /agents/export` - Export agent
- `POST /agents/search` - Search agents

### Agent Context & Memory
- `GET /agents/{id}/context` - Retrieve agent context
- `GET /agents/{id}/tools` - List agent tools
- `GET /agents/{id}/sources` - List agent sources
- `GET /agents/{id}/folders` - List agent folders
- `GET /agents/{id}/files` - List agent files
- `GET /agents/{id}/core-memory` - Get core memory
- `GET /agents/{id}/blocks` - List agent blocks
- `GET /agents/{id}/passages` - List agent passages
- `GET /agents/{id}/messages` - List agent messages
- `GET /agents/{id}/groups` - List agent groups
- `GET /agents/{id}/memory-variables` - List memory variables

### Identities
- `GET /identities` - List identities
- `GET /identities/{id}` - Retrieve identity
- `POST /identities` - Create identity
- `PUT /identities` - Upsert identity
- `PATCH /identities/{id}` - Modify identity
- `DELETE /identities/{id}` - Delete identity
- `GET /identities/count` - Count identities

### Blocks
- `GET /blocks` - List blocks
- `GET /blocks/{id}` - Retrieve block
- `POST /blocks` - Create block
- `PATCH /blocks/{id}` - Modify block
- `DELETE /blocks/{id}` - Delete block
- `GET /blocks/count` - Count blocks

### Tools
- `GET /tools` - List tools
- `GET /tools/{id}` - Retrieve tool
- `POST /tools` - Create tool
- `PUT /tools` - Upsert tool
- `PATCH /tools/{id}` - Modify tool
- `DELETE /tools/{id}` - Delete tool
- `GET /tools/count` - Count tools
- `POST /tools/upsert-base` - Upsert base tools
- `POST /tools/run-from-source` - Run tool from source

### MCP (Model Context Protocol) Tools
- `GET /tools/mcp-servers` - List MCP servers
- `PUT /tools/mcp-servers` - Add MCP server to config
- `GET /tools/mcp-tools-by-server` - List MCP tools by server
- `POST /tools/mcp-tools` - Add MCP tool
- `DELETE /tools/mcp-servers` - Delete MCP server from config
- `PATCH /tools/mcp-servers` - Update MCP server
- `POST /tools/mcp-servers/test` - Test MCP server
- `STREAM /tools/mcp-servers/connect` - Connect MCP server

### Folders & Files
- `GET /folders` - List folders
- `GET /folders/{id}` - Retrieve folder
- `POST /folders` - Create folder
- `PATCH /folders/{id}` - Modify folder
- `DELETE /folders/{id}` - Delete folder
- `GET /folders/count` - Count folders
- `GET /folders/by-name` - Get folder by name
- `GET /folders/{id}/metadata` - Retrieve metadata

### Sources
- `GET /sources` - List sources
- `GET /sources/{id}` - Retrieve source
- `POST /sources` - Create source
- `PATCH /sources/{id}` - Modify source
- `DELETE /sources/{id}` - Delete source
- `GET /sources/count` - Count sources
- `GET /sources/by-name` - Get source ID by name
- `GET /sources/metadata` - Get sources metadata
- `POST /sources/{id}/upload` - Upload file to source
- `GET /sources/{id}/files` - List source files
- `DELETE /sources/{id}/files` - Delete file from source
- `GET /sources/{id}/passages` - List source passages

### Models & Providers
- `GET /models/llm` - List LLM models
- `GET /models/embeddings` - List embedding models
- `GET /providers` - List providers
- `GET /providers/{id}` - Retrieve provider
- `POST /providers` - Create provider
- `PATCH /providers/{id}` - Modify provider
- `DELETE /providers/{id}` - Delete provider
- `POST /providers/check` - Check provider
- `POST /providers/check-existing` - Check existing provider

### Jobs & Runs
- `GET /jobs` - List jobs
- `GET /jobs/active` - List active jobs
- `GET /jobs/{id}` - Retrieve job
- `DELETE /jobs/{id}` - Delete job
- `PATCH /jobs/{id}/cancel` - Cancel job
- `GET /runs` - List runs
- `GET /runs/active` - List active runs
- `GET /runs/{id}` - Retrieve run
- `DELETE /runs/{id}` - Delete run
- `GET /runs/{id}/metrics` - Retrieve metrics for run
- `STREAM /runs/{id}/stream` - Retrieve stream

### Groups & Messages
- `GET /groups` - List groups
- `GET /groups/{id}` - Retrieve group
- `POST /groups` - Create group
- `PATCH /groups/{id}` - Modify group
- `DELETE /groups/{id}` - Delete group
- `GET /groups/count` - Count groups

### Archives & Batches
- `GET /archives` - List archives
- `POST /archives` - Create archive
- `PATCH /archives/{id}` - Modify archive
- `GET /batches` - List batches
- `GET /batches/{id}` - Retrieve batch
- `POST /batches` - Create batch
- `PATCH /batches/{id}/cancel` - Cancel batch

### Cloud-Only Endpoints
- `GET /projects` - List projects
- `POST /templates` - Create agents from template
- `GET /templates` - List templates
- `POST /templates/save-version` - Save template version
- `DELETE /templates/{id}` - Delete template
- `GET /templates/{id}/snapshot` - Get template snapshot
- `PUT /templates/{id}/current` - Set current template from snapshot
- `POST /templates/{id}/fork` - Fork template
- `POST /templates/create` - Create template
- `PATCH /templates/{id}/rename` - Rename template
- `PATCH /templates/{id}/description` - Update template description
- `GET /templates/{id}/versions` - List template versions
- `POST /templates/{id}/migrate` - Migrate deployment to template version
- `PUT /templates/{id}/update` - Update current template from agent file
- `GET /tokens` - List client-side access tokens
- `POST /tokens` - Create token
- `DELETE /tokens/{id}` - Delete token

### Telemetry
- `GET /telemetry/provider-trace` - Retrieve provider trace

### Tags
- `GET /tags` - List tags

## SDK Examples

### Health Check
```python
from letta_client import Letta

client = Letta(token="YOUR_TOKEN")
client.health.check()
```

### Agents
```python
# List agents
agents = client.agents.list()

# Retrieve agent
agent = client.agents.retrieve(agent_id="agent_id")

# Create agent
agent = client.agents.create(
    name="My Agent",
    instructions="You are a helpful assistant"
)

# Modify agent
client.agents.modify(
    agent_id="agent_id",
    instructions="Updated instructions"
)

# Delete agent
client.agents.delete(agent_id="agent_id")
```

### Messages
```python
from letta_client import Letta, MessageCreate

client = Letta(token="YOUR_TOKEN")

# Send message
response = client.agents.messages.create(
    agent_id="agent_id",
    messages=[
        MessageCreate(
            role="user",
            content="Hello, how are you?"
        )
    ]
)

# Send message with identity
response = client.agents.messages.create(
    agent_id="agent_id",
    messages=[
        MessageCreate(
            role="user",
            content="Hello, how are you?"
        )
    ],
    identity_id="user_123"
)

# Send streaming message
response = client.agents.messages.create_stream(
    agent_id="agent_id",
    messages=[
        MessageCreate(
            role="user",
            content="Tell me a story"
        )
    ]
)
for chunk in response:
    print(chunk)

# Send async message
response = await client.agents.messages.create_async(
    agent_id="agent_id",
    messages=[
        MessageCreate(
            role="user",
            content="Hello"
        )
    ]
)

# List messages
messages = client.agents.messages.list(agent_id="agent_id")

# Modify message
client.agents.messages.modify(
    agent_id="agent_id",
    message_id="message_id"
)
```

### Blocks
```python
# Create block
block = client.blocks.create(
    label="My Block",
    value={"content": "This is my block content"}
)

# Retrieve block
block = client.blocks.retrieve(block_id="block_id")

# Modify block
client.blocks.modify(
    block_id="block_id",
    value={"content": "Updated content"}
)

# Delete block
client.blocks.delete(block_id="block_id")

# List blocks
blocks = client.blocks.list()

# Attach block to agent
client.agents.blocks.attach(
    agent_id="agent_id",
    block_id="block_id"
)

# Detach block from agent
client.agents.blocks.detach(
    agent_id="agent_id",
    block_id="block_id"
)
```

### Identities
```python
# Create identity
identity = client.identities.create(
    identifier_key="user_123",
    name="John Doe",
    identity_type="user"
)

# Retrieve identity
identity = client.identities.retrieve(identity_id="identity_id")

# Upsert identity
identity = client.identities.upsert(
    identifier_key="user_123",
    name="John Doe",
    identity_type="user"
)

# Modify identity
client.identities.modify(
    identity_id="identity_id",
    name="Updated Name"
)

# Delete identity
client.identities.delete(identity_id="identity_id")

# List identities
identities = client.identities.list()
```

### Tools
```python
# List tools
tools = client.tools.list()

# Retrieve tool
tool = client.tools.retrieve(tool_id="tool_id")

# Create tool
tool = client.tools.create(
    name="my_tool",
    description="A useful tool",
    parameters={"type": "object", "properties": {}}
)

# Upsert tool
tool = client.tools.upsert(
    name="my_tool",
    description="A useful tool",
    parameters={"type": "object", "properties": {}}
)

# Modify tool
client.tools.modify(
    tool_id="tool_id",
    description="Updated description"
)

# Delete tool
client.tools.delete(tool_id="tool_id")
```

### Sources
```python
# List sources
sources = client.sources.list()

# Create source
source = client.sources.create(
    name="My Source",
    description="A data source"
)

# Upload file to source
client.sources.upload_file(
    source_id="source_id",
    file_path="/path/to/file.txt"
)

# List source files
files = client.sources.list_files(source_id="source_id")

# Delete file from source
client.sources.delete_file(
    source_id="source_id",
    file_id="file_id"
)
```

### Providers
```python
# List providers
providers = client.providers.list()

# Create provider
provider = client.providers.create(
    name="OpenAI",
    provider_type="openai",
    api_key="your-api-key"
)

# Check provider
client.providers.check(provider_id="provider_id")

# Modify provider
client.providers.modify(
    provider_id="provider_id",
    api_key="new-api-key"
)
```

## Development Notes

#### Identity Management
- Identities must be explicitly specified as "user" type when creating them
- User context is not automatically maintained between messages - each message must include the identity_id
- Core memory blocks should be attached to user identities to maintain context
- When sending messages, always include the identity_id parameter to maintain conversation context

Example identity creation:
```python
# Create a user identity
identity = {
    "identifier_key": "user_123",
    "name": "John Doe",
    "identity_type": "user"  # Important: must specify as "user"
}
```

Example message with identity:
```python
client.agents.messages.create(
    agent_id="agent_id",
    messages=[MessageCreate(role="user", content="Hello")],
    identity_id="user_123"  # Include identity_id to maintain context
)
```

#### Core Block Management
- Each user identity should have an associated core memory block named `Persona_<username>`
- The core block should be created when the identity is created
- The core block should be attached to the identity as a variable
- Message flow:
  1. Create the block using `client.blocks.create()`
  2. Attach the user's `Persona_<username>` core block to the agent
  3. Send the message with the user's identity_id
  4. Detach the user's core block from the agent
- This ensures the agent has access to the user's persona information during the conversation
- Core blocks should contain relevant user information, preferences, and conversation history

#### CRITICAL: Block ID Management
- The `client.blocks.list()` operation is currently unreliable and may not show all blocks
- This is a known issue being investigated by the core team
- **DESIGN REQUIREMENT**: All block IDs must be cached locally
- Block IDs should be stored in the database alongside user records
- Never rely on `client.blocks.list()` for block discovery or management

Implementation Details:
```python
# Create a new block
block = client.blocks.create(
    label=f"Persona_{username}",
    value={
        "name": username,
        "preferences": {},
        "conversation_history": []
    }
)

# Store block ID in database
user_record.block_id = block.id
user_record.save()

# Core block operations (using cached block ID)
client.blocks.retrieve(block_id=user_record.block_id)
client.blocks.modify(block_id=user_record.block_id, value=new_content)
client.agents.blocks.attach(agent_id=agent_id, block_id=user_record.block_id)
client.agents.blocks.detach(agent_id=agent_id, block_id=user_record.block_id)

# NEVER use list() for block discovery
# client.blocks.list()  # DO NOT USE - unreliable
```

Example Usage:
```python
# Create and manage a user's persona block
block_label = f"Persona_{username}"
block_content = {
    "name": username,
    "preferences": {},
    "conversation_history": []
}

# Create the block first
block = client.blocks.create(
    label=block_label,
    value=block_content
)

# Store block ID in database
user_record.block_id = block.id
user_record.save()

# Attach block before sending message
client.agents.blocks.attach(agent_id=agent_id, block_id=user_record.block_id)
try:
    # Send message with identity
    response = client.agents.messages.create(
        agent_id=agent_id,
        messages=[MessageCreate(role="user", content=message)],
        identity_id=identity_id
    )
finally:
    # Always detach block after message
    client.agents.blocks.detach(agent_id=agent_id, block_id=user_record.block_id)
```

## REST API Examples

### Health Check
```bash
curl http://localhost:8283/health \
     -H "Authorization: Bearer <token>"
```

### Identities (REST)
```bash
# List identities
curl http://localhost:8283/v1/identities/ \
     -H "Authorization: Bearer <token>"

# Create identity
curl -X POST http://localhost:8283/v1/identities/ \
     -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json" \
     -d '{
  "identifier_key": "user_123",
  "name": "John Doe",
  "identity_type": "user"
}'

# Upsert identity
curl -X PUT http://localhost:8283/v1/identities/ \
     -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json" \
     -d '{
  "identifier_key": "user_123",
  "name": "John Doe",
  "identity_type": "user"
}'

# Retrieve identity
curl http://localhost:8283/v1/identities/identity_id \
     -H "Authorization: Bearer <token>"

# Modify identity
curl -X PATCH http://localhost:8283/v1/identities/identity_id \
     -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json" \
     -d '{"name": "Updated Name"}'

# Delete identity
curl -X DELETE http://localhost:8283/v1/identities/identity_id \
     -H "Authorization: Bearer <token>"
```

## Important Notes

### Block ID Management
- The `client.blocks.list()` operation is currently unreliable and may not show all blocks
- This is a known issue being investigated by the core team
- **DESIGN REQUIREMENT**: All block IDs must be cached locally
- Block IDs should be stored in the database alongside user records
- Never rely on `client.blocks.list()` for block discovery or management

### Identity Management Best Practices
- Identities must be explicitly specified as "user" type when creating them
- User context is not automatically maintained between messages - each message must include the identity_id
- Core memory blocks should be attached to user identities to maintain context
- When sending messages, always include the identity_id parameter to maintain conversation context

### Server Configuration
- Our server is not localhost - we'll be connecting to a VPS server
- Server URL: `https://your-letta-server.com:8283`
- Password: `YOUR_PASSWORD` (configure this in your environment)
- We'll want to configure this in the admin dashboard settings