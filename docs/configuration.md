# The Librarian - Configuration Guide

**License**: [CC-BY-SA-4.0](../LICENSE-DOCS)

## Overview

The Librarian is configured entirely via environment variables. Copy `config.example` to `config` (or use `.env`) and set the values for your environment.

## Configuration File

Create a `config` file (or `.env` file) in the project root:

```bash
cp config.example config
# Edit config with your settings
```

## Configuration Sections

### Server Configuration

```bash
# Server host and port
LIBRARIAN_HOST=127.0.0.1
LIBRARIAN_PORT=8000

# Debug mode (enables hot reload, detailed logging, and API docs)
LIBRARIAN_DEBUG=false

# Enable API documentation (Swagger/ReDoc) even in production
LIBRARIAN_ENABLE_DOCS=false

# Application metadata
LIBRARIAN_TITLE=The Librarian
LIBRARIAN_DESCRIPTION=OpenAI-Compatible Letta Proxy
LIBRARIAN_VERSION=0.1.0
```

### Letta Server Configuration

```bash
# Letta server connection
LETTA_BASE_URL=https://sanctum.zero1.network:8283
LETTA_API_KEY=your_api_key_here

# Letta client timeout (seconds)
LETTA_TIMEOUT=30
```

**Required**: `LETTA_BASE_URL` and `LETTA_API_KEY` must be set.

### Agent Configuration

```bash
# Default agent IDs for different models
LIBRARIAN_WORKER_AGENT=librarian-worker
LIBRARIAN_PERSONA_AGENT=librarian-persona
LIBRARIAN_PERSONA_TURBO_AGENT=librarian-persona-turbo

# Custom model configurations (JSON format)
LIBRARIAN_CUSTOM_MODELS={"custom-model": {"agent_id": "custom-agent", "mode": "worker", "description": "Custom model"}}

# Additional model configurations (JSON format)
LIBRARIAN_ADDITIONAL_MODELS={"claude-3": {"agent_id": "claude-agent", "mode": "persona", "description": "Claude 3 model"}}
```

**Model Configuration Format**:
```json
{
  "model-name": {
    "agent_id": "letta-agent-id",
    "mode": "worker" | "persona",
    "description": "Model description"
  }
}
```

### Security Configuration

```bash
# IP filtering
LIBRARIAN_ENABLE_IP_FILTERING=false
LIBRARIAN_ALLOWED_IPS=192.168.1.0/24,10.0.0.0/8
LIBRARIAN_BLOCKED_IPS=192.168.1.100,10.0.0.50

# API key authentication
LIBRARIAN_API_KEY_REQUIRED=false
LIBRARIAN_API_KEY=your_secret_api_key
```

**IP Filtering**:
- `LIBRARIAN_ALLOWED_IPS`: Comma-separated list of IPs/CIDR ranges to allow
- `LIBRARIAN_BLOCKED_IPS`: Comma-separated list of IPs to block
- If `LIBRARIAN_ENABLE_IP_FILTERING=true`, only allowed IPs can access (unless blocked)

**API Key Authentication**:
- If `LIBRARIAN_API_KEY_REQUIRED=true`, all requests must include `Authorization: Bearer YOUR_API_KEY`
- Set `LIBRARIAN_API_KEY` to your secret key

### Rate Limiting Configuration

```bash
# Rate limiting settings
LIBRARIAN_RATE_LIMIT_ENABLED=false
LIBRARIAN_RATE_LIMIT_REQUESTS=100
LIBRARIAN_RATE_LIMIT_WINDOW=60
```

**Rate Limiting**:
- `LIBRARIAN_RATE_LIMIT_REQUESTS`: Maximum requests per window
- `LIBRARIAN_RATE_LIMIT_WINDOW`: Time window in seconds
- Example: `100` requests per `60` seconds = 100 requests/minute

### Performance Configuration

```bash
# Request limits
LIBRARIAN_MAX_REQUEST_SIZE=10485760  # 10MB
LIBRARIAN_REQUEST_TIMEOUT=300         # 5 minutes
LIBRARIAN_KEEP_ALIVE_TIMEOUT=5       # 5 seconds

# Load management
LIBRARIAN_MAX_CONCURRENT=10
LIBRARIAN_DUPLICATION_THRESHOLD=8
LIBRARIAN_QUEUE_TIMEOUT=300
LIBRARIAN_CLEANUP_INTERVAL=60
LIBRARIAN_ENABLE_AUTO_DUPLICATION=true
LIBRARIAN_MAX_CLONES_PER_AGENT=3
```

**Load Management**:
- `LIBRARIAN_MAX_CONCURRENT`: Maximum concurrent requests per agent
- `LIBRARIAN_DUPLICATION_THRESHOLD`: Queue size threshold for auto-duplication
- `LIBRARIAN_MAX_CLONES_PER_AGENT`: Maximum agent clones per agent
- `LIBRARIAN_QUEUE_TIMEOUT`: Maximum time a request can wait in queue (seconds)

### Logging Configuration

```bash
# Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LIBRARIAN_LOG_LEVEL=INFO

# Log format (Python logging format string)
LIBRARIAN_LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s

# Security event logging
LIBRARIAN_LOG_SECURITY_EVENTS=true

# Audit logging
LIBRARIAN_AUDIT_ENABLED=false
```

**Log Levels**:
- `DEBUG`: Detailed debugging information
- `INFO`: General informational messages
- `WARNING`: Warning messages
- `ERROR`: Error messages
- `CRITICAL`: Critical errors

### Advanced Features

```bash
# Tool synchronization
LIBRARIAN_ENABLE_TOOL_SYNC=true
LIBRARIAN_TOOL_SYNC_TIMEOUT=30

# Memory management
LIBRARIAN_ENABLE_MEMORY_MANAGEMENT=true
LIBRARIAN_MEMORY_CLEANUP_INTERVAL=3600

# Streaming configuration
LIBRARIAN_STREAMING_ENABLED=true
LIBRARIAN_STREAMING_CHUNK_SIZE=1024
```

### Monitoring & Health Checks

```bash
# Health check configuration
LIBRARIAN_HEALTH_CHECK_ENABLED=true
LIBRARIAN_HEALTH_CHECK_INTERVAL=30

# Metrics collection
LIBRARIAN_METRICS_ENABLED=false
LIBRARIAN_METRICS_PORT=9090
```

### Development Configuration

```bash
# Development mode settings
LIBRARIAN_DEV_MODE=false
LIBRARIAN_DEV_RELOAD=true
LIBRARIAN_DEV_LOG_REQUESTS=false

# Testing configuration
LIBRARIAN_TEST_MODE=false
LIBRARIAN_TEST_TIMEOUT=10
```

## Configuration Examples

### Development Setup

```bash
LIBRARIAN_HOST=127.0.0.1
LIBRARIAN_PORT=8000
LIBRARIAN_DEBUG=true
LIBRARIAN_ENABLE_DOCS=true
LIBRARIAN_LOG_LEVEL=DEBUG
LETTA_BASE_URL=http://localhost:8283
LETTA_API_KEY=dev_api_key
```

### Production Setup

```bash
LIBRARIAN_HOST=0.0.0.0
LIBRARIAN_PORT=8000
LIBRARIAN_DEBUG=false
LIBRARIAN_ENABLE_DOCS=false
LIBRARIAN_LOG_LEVEL=INFO
LIBRARIAN_API_KEY_REQUIRED=true
LIBRARIAN_API_KEY=secure_random_key
LIBRARIAN_RATE_LIMIT_ENABLED=true
LIBRARIAN_RATE_LIMIT_REQUESTS=1000
LIBRARIAN_RATE_LIMIT_WINDOW=3600
LETTA_BASE_URL=https://sanctum.zero1.network:8283
LETTA_API_KEY=production_api_key
```

### High-Performance Setup

```bash
LIBRARIAN_MAX_CONCURRENT=50
LIBRARIAN_DUPLICATION_THRESHOLD=40
LIBRARIAN_MAX_CLONES_PER_AGENT=5
LIBRARIAN_QUEUE_TIMEOUT=600
LIBRARIAN_ENABLE_AUTO_DUPLICATION=true
```

### Secure Setup

```bash
LIBRARIAN_ENABLE_IP_FILTERING=true
LIBRARIAN_ALLOWED_IPS=192.168.1.0/24,10.0.0.0/8
LIBRARIAN_API_KEY_REQUIRED=true
LIBRARIAN_API_KEY=very_secure_random_key
LIBRARIAN_RATE_LIMIT_ENABLED=true
LIBRARIAN_LOG_SECURITY_EVENTS=true
LIBRARIAN_AUDIT_ENABLED=true
```

## Environment Variable Priority

1. Environment variables (highest priority)
2. `.env` file
3. `config` file
4. Default values (lowest priority)

## Validation

Validate your configuration:

```bash
python tests/validate_config.py
```

This will check:
- Required variables are set
- Format validation
- Connection to Letta server
- Agent availability

## Configuration Best Practices

### 1. Use Environment Variables for Secrets

Never commit secrets to version control. Use environment variables:

```bash
# In production, set via environment
export LIBRARIAN_API_KEY=secret_key
export LETTA_API_KEY=secret_key
```

### 2. Separate Development and Production Configs

- Development: Use `.env` file (gitignored)
- Production: Use environment variables or secure config management

### 3. Monitor Performance Settings

Adjust these based on your workload:
- `LIBRARIAN_MAX_CONCURRENT`: Start with 10, increase if needed
- `LIBRARIAN_DUPLICATION_THRESHOLD`: Set to ~80% of max_concurrent
- `LIBRARIAN_QUEUE_TIMEOUT`: Based on your SLA requirements

### 4. Enable Security in Production

Always enable in production:
- `LIBRARIAN_API_KEY_REQUIRED=true`
- `LIBRARIAN_RATE_LIMIT_ENABLED=true`
- `LIBRARIAN_LOG_SECURITY_EVENTS=true`

### 5. Tune Logging

- Development: `DEBUG` level
- Production: `INFO` or `WARNING` level
- Use structured logging for production (modify `LIBRARIAN_LOG_FORMAT`)

## Troubleshooting Configuration

### Configuration Not Loading

**Problem**: Changes to config file not taking effect

**Solutions**:
- Restart The Librarian after config changes
- Check environment variables aren't overriding config
- Verify config file format (no syntax errors)

### Connection to Letta Fails

**Problem**: Cannot connect to Letta server

**Solutions**:
- Verify `LETTA_BASE_URL` is correct
- Check `LETTA_API_KEY` is valid
- Test connection: `curl $LETTA_BASE_URL/health`
- Check network/firewall settings

### Agents Not Found

**Problem**: Agent IDs not found in Letta

**Solutions**:
- Verify agent IDs in `LIBRARIAN_*_AGENT` variables
- Run bootstrap script to create agents
- Check Letta server has the agents

## Next Steps

- See [Usage Guide](usage-guide.md) for how to use The Librarian
- See [Architecture](architecture.md) for system architecture
- See [Deployment Guide](deployment.md) for production deployment

