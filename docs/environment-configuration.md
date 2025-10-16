# The Librarian - Environment Configuration Reference

This document provides a comprehensive reference for all environment configuration options available in The Librarian.

## Quick Start

1. Copy `config.example` to `config`
2. Update the values for your environment
3. Run `python start_librarian.py` or `python main.py`

## Configuration Categories

### 🖥️ Server Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `LIBRARIAN_HOST` | `127.0.0.1` | Server host address |
| `LIBRARIAN_PORT` | `8000` | Server port |
| `LIBRARIAN_DEBUG` | `false` | Enable debug mode (hot reload, detailed logging) |
| `LIBRARIAN_ENABLE_DOCS` | `false` | Enable API documentation in production |
| `LIBRARIAN_TITLE` | `The Librarian` | Application title |
| `LIBRARIAN_DESCRIPTION` | `OpenAI-Compatible Letta Proxy` | Application description |
| `LIBRARIAN_VERSION` | `0.1.0` | Application version |

### 🔗 Letta Server Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `LETTA_BASE_URL` | `http://localhost:8283` | Letta server base URL |
| `LETTA_API_KEY` | *required* | Letta API key |
| `LETTA_TIMEOUT` | `30` | Letta client timeout (seconds) |

### 🤖 Agent Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `LIBRARIAN_WORKER_AGENT` | `librarian-worker` | Worker mode agent ID |
| `LIBRARIAN_PERSONA_AGENT` | `librarian-persona` | Persona mode agent ID |
| `LIBRARIAN_PERSONA_TURBO_AGENT` | `librarian-persona-turbo` | Persona turbo agent ID |
| `LIBRARIAN_CUSTOM_MODELS` | *empty* | Custom model configurations (JSON) |
| `LIBRARIAN_ADDITIONAL_MODELS` | *empty* | Additional model configurations (JSON) |

### 🔒 Security Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `LIBRARIAN_ENABLE_IP_FILTERING` | `false` | Enable IP address filtering |
| `LIBRARIAN_ALLOWED_IPS` | *empty* | Comma-separated list of allowed IPs |
| `LIBRARIAN_BLOCKED_IPS` | *empty* | Comma-separated list of blocked IPs |
| `LIBRARIAN_API_KEY_REQUIRED` | `false` | Require API key authentication |
| `LIBRARIAN_API_KEY` | *empty* | API key for authentication |

### ⚡ Rate Limiting Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `LIBRARIAN_RATE_LIMIT_ENABLED` | `false` | Enable rate limiting |
| `LIBRARIAN_RATE_LIMIT_REQUESTS` | `100` | Max requests per window |
| `LIBRARIAN_RATE_LIMIT_WINDOW` | `60` | Rate limit window (seconds) |

### 🚀 Performance Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `LIBRARIAN_MAX_REQUEST_SIZE` | `10485760` | Max request size (bytes) |
| `LIBRARIAN_REQUEST_TIMEOUT` | `300` | Request timeout (seconds) |
| `LIBRARIAN_KEEP_ALIVE_TIMEOUT` | `5` | Keep-alive timeout (seconds) |

### 📊 Load Management Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `LIBRARIAN_MAX_CONCURRENT` | `10` | Max concurrent requests |
| `LIBRARIAN_DUPLICATION_THRESHOLD` | `8` | Threshold for auto-duplication |
| `LIBRARIAN_QUEUE_TIMEOUT` | `300` | Queue timeout (seconds) |
| `LIBRARIAN_CLEANUP_INTERVAL` | `60` | Cleanup interval (seconds) |
| `LIBRARIAN_ENABLE_AUTO_DUPLICATION` | `true` | Enable auto-duplication |
| `LIBRARIAN_MAX_CLONES_PER_AGENT` | `3` | Max clones per agent |

### 📝 Logging Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `LIBRARIAN_LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `LIBRARIAN_LOG_FORMAT` | `%(asctime)s - %(name)s - %(levelname)s - %(message)s` | Log format string |
| `LIBRARIAN_LOG_SECURITY_EVENTS` | `true` | Log security events |
| `LIBRARIAN_AUDIT_ENABLED` | `false` | Enable audit logging |

### 🧪 Testing Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `LIBRARIAN_TEST_TIMEOUT` | `30` | Test timeout (seconds) |
| `LIBRARIAN_TEST_MODELS` | `gpt-3.5-turbo,gpt-4` | Models to test (comma-separated) |
| `LIBRARIAN_ENABLE_STREAMING_TESTS` | `true` | Enable streaming tests |
| `LIBRARIAN_ENABLE_TOOL_TESTS` | `false` | Enable tool tests |
| `LIBRARIAN_TEST_VERBOSE` | `false` | Verbose test output |

### 🔧 Advanced Features
| Variable | Default | Description |
|----------|---------|-------------|
| `LIBRARIAN_ENABLE_TOOL_SYNC` | `true` | Enable tool synchronization |
| `LIBRARIAN_TOOL_SYNC_TIMEOUT` | `30` | Tool sync timeout (seconds) |
| `LIBRARIAN_ENABLE_MEMORY_MANAGEMENT` | `true` | Enable memory management |
| `LIBRARIAN_MEMORY_CLEANUP_INTERVAL` | `3600` | Memory cleanup interval (seconds) |
| `LIBRARIAN_STREAMING_ENABLED` | `true` | Enable streaming responses |
| `LIBRARIAN_STREAMING_CHUNK_SIZE` | `1024` | Streaming chunk size (bytes) |

### 📈 Monitoring Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `LIBRARIAN_HEALTH_CHECK_ENABLED` | `true` | Enable health checks |
| `LIBRARIAN_HEALTH_CHECK_INTERVAL` | `30` | Health check interval (seconds) |
| `LIBRARIAN_METRICS_ENABLED` | `false` | Enable metrics collection |
| `LIBRARIAN_METRICS_PORT` | `9090` | Metrics port |

### 🛠️ Development Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `LIBRARIAN_DEV_MODE` | `false` | Development mode |
| `LIBRARIAN_DEV_RELOAD` | `true` | Auto-reload in dev mode |
| `LIBRARIAN_DEV_LOG_REQUESTS` | `false` | Log all requests in dev mode |
| `LIBRARIAN_VALIDATE_CONFIG` | `true` | Validate config on startup |

## Configuration Examples

### Basic Production Setup
```bash
LIBRARIAN_HOST=0.0.0.0
LIBRARIAN_PORT=8000
LIBRARIAN_DEBUG=false
LETTA_BASE_URL=https://your-letta-server.com
LETTA_API_KEY=your_api_key_here
LIBRARIAN_WORKER_AGENT=your-worker-agent
LIBRARIAN_PERSONA_AGENT=your-persona-agent
```

### High-Performance Setup
```bash
LIBRARIAN_MAX_CONCURRENT=50
LIBRARIAN_DUPLICATION_THRESHOLD=40
LIBRARIAN_MAX_CLONES_PER_AGENT=5
LIBRARIAN_RATE_LIMIT_ENABLED=true
LIBRARIAN_RATE_LIMIT_REQUESTS=1000
LIBRARIAN_RATE_LIMIT_WINDOW=3600
```

### Development Setup
```bash
LIBRARIAN_DEBUG=true
LIBRARIAN_ENABLE_DOCS=true
LIBRARIAN_LOG_LEVEL=DEBUG
LIBRARIAN_DEV_MODE=true
LIBRARIAN_VALIDATE_CONFIG=true
```

### Custom Model Configuration
```bash
LIBRARIAN_CUSTOM_MODELS={"gpt-4-custom": {"agent_id": "custom-agent", "mode": "persona", "description": "Custom GPT-4 model"}}
LIBRARIAN_ADDITIONAL_MODELS={"claude-3": {"agent_id": "claude-agent", "mode": "worker", "description": "Claude 3 model"}}
```

## Validation

Use the configuration validator to check your setup:
```bash
python tests/validate_config.py
```

## Tools

- **Test Runner**: `tests/run_tests.py` - Runs all tests
- **Configuration Validator**: `tests/validate_config.py`
- **Integration Tests**: `tests/test_librarian_integration.py`

## Notes

- All configuration is loaded from environment variables
- The `config` file is loaded via `python-dotenv`
- Configuration is validated on startup (can be disabled)
- Default values are provided for all optional settings
- JSON configurations are validated for proper format
- Numeric configurations are validated for reasonable ranges
