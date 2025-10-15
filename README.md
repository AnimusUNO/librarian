# The Librarian

> **Sanctum Pillar Agent** — A stateful, OpenAI-compatible gateway powered by Letta agents

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Documentation License: CC BY-SA 4.0](https://img.shields.io/badge/Documentation%20License-CC%20BY--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-sa/4.0/)

## Overview

The Librarian is a stateful, OpenAI-compatible gateway that allows Sanctum systems and external clients to interface with a persistent Letta agent (with memory, tools, and reasoning) while still speaking the standard OpenAI API protocol.

This means any OpenAI-compatible client (LangChain, Autogen, Cursor, etc.) can route through Sanctum and transparently gain:

- **Persistent context** (Letta memory blocks)
- **Tool access** (SMCP / MCP toolchains)  
- **Self-tuning behavior** (archival memory patterning)
- **Provider abstraction** (OpenAI, Anthropic, Venice, Ollama, etc.)

The world thinks it's talking to OpenAI — but it's actually speaking to a Sanctum agent with a mind of its own.

## Architecture

```
External Client (OpenAI SDK / LangChain / UCW / Dream / SMCP)
    ↓  standard /v1/chat/completions
Librarian Gateway (middleware proxy)
    ↓  persistent Letta agent (The Librarian)
    ↓  memory, reasoning, tools, archival store
    ↓  downstream LLM (OpenAI / Anthropic / Venice / etc.)
```

## Feature Roadmap

### ✅ OpenAI Compatibility
- **Strict API compliance** - No schema changes or non-spec fields
- **Full endpoint support** - `/v1/chat/completions`, `/v1/models`, `/v1/completions`
- **Streaming support** - Real-time response streaming
- **Tool calling** - Dynamic tool synchronization

### 🧠 Advanced Capabilities
- **Dual-mode behavior** - Worker vs Persona mode switching
- **Persistent memory** - Context continuity across sessions
- **Identity management** - User-specific context and memory
- **System prompt overlays** - Unlimited length via memory blocks
- **MCP tool integration** - Model Context Protocol support

### 🏭 Production Ready
- **Load management** - Auto-duplication for high concurrency
- **Error handling** - Comprehensive fallback mechanisms
- **Health monitoring** - Built-in health checks
- **Debug capabilities** - Raw output logging and session debugging

## Quick Start

### Prerequisites
- Python 3.8+
- Letta server (local or cloud)
- Virtual environment

### Installation

```bash
# Clone the repository
git clone https://github.com/AnimusUNO/librarian.git
cd librarian

# Activate virtual environment
venv\Scripts\Activate.ps1  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Create a `.env` file:

```env
# Letta Server Configuration
LETTA_BASE_URL=https://your-letta-server.com:8283
LETTA_API_KEY=your_api_key

# Librarian Configuration
LIBRARIAN_HOST=0.0.0.0
LIBRARIAN_PORT=8000
LIBRARIAN_DEBUG=false

# Model Mappings
LIBRARIAN_WORKER_AGENT=librarian-worker
LIBRARIAN_PERSONA_AGENT=librarian-persona
```

### Running

```bash
# Start the server
python main.py

# Or with uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The server will be available at `http://localhost:8000`

## Usage

### OpenAI Client Integration

```python
import openai

# Configure OpenAI client to use The Librarian
client = openai.OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="any-value"  # Not validated by proxy
)

# Use standard OpenAI API calls
response = client.chat.completions.create(
    model="gpt-4",  # Maps to librarian-persona agent
    messages=[
        {"role": "user", "content": "Hello, Librarian!"}
    ],
    stream=True
)

for chunk in response:
    print(chunk.choices[0].delta.content, end="")
```

### Model Mapping

| OpenAI Model | Letta Agent | Mode | Description |
|--------------|-------------|------|-------------|
| `gpt-3.5-turbo` | `librarian-worker` | Worker | Procedural, technical tasks |
| `gpt-4` | `librarian-persona` | Persona | Expressive, interpretive responses |
| `gpt-4-turbo` | `librarian-persona-turbo` | Persona | High-performance persona mode |

## Development

### Project Structure

```
librarian/
├── docs/                    # Documentation (CC-BY-SA 4.0)
│   ├── sanctum-pillar-agent-plan.md
│   ├── letta-api-reference.md
│   ├── openai-letta-mapping.md
│   └── proxy-comparison-analysis.md
├── src/                     # Source code (AGPLv3)
├── tests/                   # Test suite
├── venv/                    # Virtual environment (gitignored)
├── tmp/                     # Temporary files (gitignored)
├── .gitignore              # Git ignore rules
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Licensing & Attribution

### Code License
This project is licensed under the **GNU Affero General Public License v3.0** (AGPLv3) - see the [LICENSE](LICENSE) file for details.

### Documentation License
All documentation is licensed under **Creative Commons Attribution-ShareAlike 4.0 International** (CC-BY-SA 4.0) - see the [LICENSE-DOCS](LICENSE-DOCS) file for details.

### Base Implementation
- **Soft fork of**: [wsargent/letta-openai-proxy](https://github.com/wsargent/letta-openai-proxy) (MIT License)
- **Architectural inspiration**: [ResonanceGroup/Letta-Proxy](https://github.com/ResonanceGroup/Letta-Proxy) (Apache 2.0)

### Why AGPLv3?
The Librarian is designed as a **Sanctum Pillar Agent** - core infrastructure that should remain open and accessible. AGPLv3 ensures that:
- The core implementation remains free and open
- Any modifications or improvements are shared back with the community
- Commercial users must contribute back to the ecosystem
- The Sanctum vision of open, collaborative AI infrastructure is preserved

## The Librarian Persona

### Identity
- **Codename**: The Librarian
- **Class**: Pillar Agent (core Sanctum daemon)
- **Domain**: Context continuity, documentation, cognitive routing
- **Archetype**: The Archivist of the Machine City — keeps the record of all things done, said, and built.

### Voice
- Speaks with composure, clarity, and reverence for knowledge
- Prefers complete sentences, structured thoughts, and elegant phrasing
- In reflective moments, may wax poetic about structure and memory

### Dual-Mode Behavior
- **Worker Mode**: Procedural, technical tasks with minimal narrative
- **Persona Mode**: Expressive, interpretive responses with Librarian's voice
- **Mode Selection**: Autonomous decision via reasoning block (never surfaced to clients)

## Roadmap

- [ ] **Phase 1**: Core implementation (basic OpenAI compatibility)
- [ ] **Phase 2**: Advanced features (streaming, tools, memory overlays)
- [ ] **Phase 3**: Production features (identity management, load balancing)
- [ ] **Phase 4**: Additional endpoints (embeddings, completions)
- [ ] **Phase 5**: SMCP integration and intelligent documentation

## Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/AnimusUNO/librarian/issues)
- **Discussions**: [GitHub Discussions](https://github.com/AnimusUNO/librarian/discussions)

## Acknowledgments

- **Letta Team** - For the amazing agent platform
- **wsargent** - For the MIT-licensed base implementation
- **ResonanceGroup** - For architectural inspiration and advanced features
- **Sanctum Community** - For the vision of open, collaborative AI infrastructure

---

*The Librarian — Keeping the record of all things done, said, and built.*