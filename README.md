# The Librarian Bootstrap

This directory contains tools for bootstrapping The Librarian agents in Letta server.

## Files

- `bootstrap_librarian.py` - Main bootstrap script
- `bootstrap.env` - Bootstrap configuration
- `persona_block.md` - Core Librarian persona content
- `worker_system_instructions.md` - Worker mode system instructions
- `persona_system_instructions.md` - Persona mode system instructions

## Usage

### Basic Bootstrap
```bash
python bootstrap_librarian.py --config bootstrap.env
```

### With Custom Letta Server
```bash
python bootstrap_librarian.py --letta-url http://your-letta-server:8283 --api-key your_api_key
```

### Force Recreation
```bash
python bootstrap_librarian.py --config bootstrap.env --force
```

### Verify Only
```bash
python bootstrap_librarian.py --config bootstrap.env --verify-only
```

## What It Creates

The bootstrap script creates three agents in your Letta server:

1. **librarian-worker** - Worker Mode (procedural tasks)
2. **librarian-persona** - Persona Mode (expressive responses)
3. **librarian-persona-turbo** - High-performance Persona Mode

Each agent includes:
- Proper system instructions for dual-mode behavior
- Librarian persona block with core identity
- Appropriate mode-specific configuration

## Configuration

Update `bootstrap.env` with your Letta server details:
- `LETTA_BASE_URL` - Your Letta server URL
- `LETTA_API_KEY` - Your Letta API key

## Integration

Once bootstrap is complete, The Librarian proxy will be able to:
- Connect to the created agents
- Route requests to appropriate modes
- Maintain context and memory
- Provide OpenAI-compatible API

## Next Steps

After successful bootstrap:
1. Update your main `.env` file with actual Letta server details
2. Test the integration: `python tests/test_librarian_integration.py`
3. Start The Librarian: `python main.py`