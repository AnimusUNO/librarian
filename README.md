# The Librarian

**An OpenAI-Compatible Letta Proxy - Stateful Gateway for Persistent AI Agents**

[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-blue.svg)](LICENSE)
[![License: CC-BY-SA-4.0](https://img.shields.io/badge/Docs%20License-CC--BY--SA--4.0-green.svg)](LICENSE-DOCS)

The Librarian is a stateful, OpenAI-compatible gateway that allows clients to interface with persistent Letta agents while speaking the standard OpenAI API protocol. This means any OpenAI-compatible client (LangChain, Autogen, Cursor, etc.) can route through The Librarian and transparently gain persistent context, tool access, and self-tuning behavior.

## 🎯 Core Purpose

The Librarian serves as a middleware proxy that:

- **Maintains Persistent Context**: Uses Letta memory blocks to preserve conversation history across sessions
- **Provides Tool Access**: Enables SMCP/MCP toolchains through the agent interface
- **Supports Self-Tuning Behavior**: Leverages archival memory for pattern-aware responses
- **Offers Provider Abstraction**: Works with OpenAI, Anthropic, Venice, Ollama, and other LLM providers via Letta
- **Maintains Full OpenAI Compatibility**: Drop-in replacement for OpenAI API endpoints

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- A self-hosted Letta server (cloud support may come in a future version)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd librarian

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy configuration template
cp config.example config

# Edit config with your self-hosted Letta server details
# Set LETTA_BASE_URL (and LETTA_API_KEY if your Letta server requires authentication)
```

### Bootstrap Agents

Before running The Librarian, you need to create the agents in your Letta server:

```bash
# Bootstrap agents in Letta server
cd bootstrap
python bootstrap_librarian.py --config bootstrap.env
```

This creates a single agent:
- `librarian` - The Librarian agent that handles all model names and dynamically switches between Worker Mode (procedural tasks) and Persona Mode (expressive responses) based on the request context

### Run The Librarian

```bash
# Start the server
python main.py

# Or with uvicorn directly
uvicorn main:app --host 127.0.0.1 --port 8000
```

The server will be available at `http://127.0.0.1:8000`

### Test the Installation

```bash
# Run integration tests
python tests/test_librarian_integration.py

# Test configuration
python tests/validate_config.py
```

## 📚 Documentation

### Getting Started
- **[Usage Guide](docs/usage-guide.md)** - How to use The Librarian with OpenAI clients
- **[Configuration Guide](docs/configuration.md)** - Complete configuration reference
- **[API Reference](docs/api-reference.md)** - OpenAI-compatible API endpoints

### Technical Documentation
- **[Architecture](docs/architecture.md)** - System architecture and design decisions
- **[Development Guide](docs/development.md)** - Contributing and development setup
- **[Deployment Guide](docs/deployment.md)** - Production deployment instructions

### Additional Resources
- **[Letta API Reference](docs/letta-api-reference.md)** - Letta API integration details
- **[OpenAI-Letta Mapping](docs/openai-letta-mapping.md)** - How OpenAI requests map to Letta
- **[Security Configuration](docs/librarian-security-configuration.md)** - Security settings and best practices

## 🔧 Features

### Core Capabilities

- **OpenAI API Compatibility**: Full compatibility with `/v1/models`, `/v1/chat/completions`, and `/v1/completions` endpoints
- **Streaming Support**: Real-time streaming responses via Server-Sent Events (SSE)
- **Dual-Mode Operation**: Automatic switching between Worker Mode (procedural) and Persona Mode (expressive)
- **Persistent Memory**: Conversation history maintained across sessions via Letta memory blocks
- **Tool Synchronization**: Dynamic tool attachment and management
- **Load Management**: Automatic request queuing and agent duplication for high concurrency
- **Token Management**: Accurate token counting and context window management
- **Error Handling**: Comprehensive error handling with automatic retry and summarization

### Advanced Features

- **Context Window Management**: Automatic context window adjustment and conversation summarization
- **Per-Request Configuration**: Dynamic temperature and max_tokens configuration per request
- **Request Queuing**: Buffered request queues with semaphore-based concurrency control
- **Auto-Duplication**: Automatic agent cloning for high-load scenarios
- **API Call Indicators**: All requests marked with `[API]` indicator for agent awareness

## 🏗️ Architecture

```
External Client (OpenAI SDK / LangChain / Cursor)
    ↓  standard /v1/chat/completions
The Librarian Gateway (FastAPI middleware)
    ↓  persistent Letta agent (The Librarian)
    ↓  memory, reasoning, tools, archival store
    ↓  downstream LLM (OpenAI / Anthropic / Venice / etc.)
```

The Librarian acts as a transparent proxy, translating OpenAI API requests into Letta agent interactions while maintaining full compatibility with existing OpenAI clients.

## 📋 API Endpoints

### Models
- `GET /v1/models` - List available models
- `GET /v1/models/{model_id}` - Get model information

### Chat Completions
- `POST /v1/chat/completions` - Create chat completion (streaming and non-streaming)

### Legacy Completions
- `POST /v1/completions` - Legacy completion endpoint

### Health & Status
- `GET /health` - Health check endpoint
- `GET /` - Root endpoint with service information

All endpoints maintain full OpenAI API compatibility. See [API Reference](docs/api-reference.md) for detailed documentation.

## ⚙️ Configuration

The Librarian is configured via environment variables. See `config.example` for all available options.

Key configuration areas:
- **Server Configuration**: Host, port, debug mode
- **Letta Server**: Base URL of your self-hosted Letta server (API key if authentication is required)
- **Agent Configuration**: Agent IDs and model mappings

**Note**: The Librarian currently requires a self-hosted Letta server. Cloud/hosted Letta support may be added in a future version.
- **Security**: IP filtering, API key authentication
- **Performance**: Concurrency limits, queue settings
- **Logging**: Log levels and formats

See [Configuration Guide](docs/configuration.md) for complete details.

## 🔒 Security

The Librarian supports multiple security features:

- **IP Filtering**: Allow/block specific IP addresses or ranges
- **API Key Authentication**: Optional API key requirement
- **Rate Limiting**: Configurable rate limits
- **Request Validation**: Input validation and sanitization
- **Security Logging**: Audit logging for security events

See [Security Configuration](docs/librarian-security-configuration.md) for setup instructions.

## 🧪 Testing

```bash
# Run all unit tests (excludes integration/E2E to avoid burning tokens)
pytest -k "not integration and not e2e" tests/ -v

# Run all tests including integration/E2E (requires running server)
pytest tests/ -v

# Run only integration/E2E tests (requires running server)
pytest -m integration tests/ -v

# Run with coverage report
pytest --cov=src --cov-report=term-missing -k "not integration and not e2e" tests/

# Validate configuration
python tests/validate_config.py
```

**Test Coverage**: 93.97% unit test coverage. See [Test Coverage Report](docs/test-coverage-report.md) for details.

## 📦 Project Structure

```
librarian/
├── main.py                 # FastAPI application entry point
├── src/librarian/          # Core library components
│   ├── model_registry.py   # Model-to-agent mapping
│   ├── message_translator.py  # OpenAI-to-Letta message conversion
│   ├── response_formatter.py  # Letta-to-OpenAI response formatting
│   ├── token_counter.py    # Token counting and usage calculation
│   ├── tool_synchronizer.py  # Tool attachment and management
│   └── load_manager.py     # Request queuing and load management
├── bootstrap/              # Agent bootstrap scripts
│   └── bootstrap_librarian.py  # Agent creation script
├── tests/                  # Test suites
├── docs/                   # Documentation
└── config.example          # Configuration template
```

## 🤝 Contributing

Contributions are welcome! Please see [Development Guide](docs/development.md) for:

- Development setup
- Code style guidelines
- Testing requirements
- Pull request process

## 📄 License

- **Code**: Licensed under [AGPL-3.0](LICENSE)
- **Documentation**: Licensed under [CC-BY-SA-4.0](LICENSE-DOCS)

See the LICENSE files for full terms.

## 🙏 Acknowledgments

The Librarian is part of the **Sanctum** and **Animus** ecosystem, providing persistent intelligence and context continuity for AI applications. This project is built on and integrates with the **Letta** ecosystem.

## 📞 Support

For issues, questions, or contributions:
- Check the [documentation](docs/) first
- Review [existing issues](https://github.com/your-repo/issues)
- Open a new issue with detailed information

---

**The Librarian** - *Preserving context, maintaining continuity, enabling persistent intelligence.*
