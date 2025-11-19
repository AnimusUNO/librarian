# The Librarian - Development Guide

**License**: [CC-BY-SA-4.0](../LICENSE-DOCS)

## Development Setup

### Prerequisites

- Python 3.10 or higher
- Git
- Access to a Letta server (for testing)
- Virtual environment tool (venv, virtualenv, etc.)

### Initial Setup

```bash
# Clone the repository
git clone <repository-url>
cd librarian

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-test.txt  # For development

# Copy configuration
cp config.example config

# Edit config with your Letta server details
# Set LETTA_BASE_URL and LETTA_API_KEY
```

### Development Configuration

Set these in your `config` file for development:

```bash
LIBRARIAN_DEBUG=true
LIBRARIAN_ENABLE_DOCS=true
LIBRARIAN_LOG_LEVEL=DEBUG
LIBRARIAN_DEV_MODE=true
LIBRARIAN_DEV_RELOAD=true
```

## Project Structure

```
librarian/
├── main.py                 # FastAPI application entry point
├── src/
│   └── librarian/         # Core library components
│       ├── __init__.py
│       ├── model_registry.py
│       ├── message_translator.py
│       ├── response_formatter.py
│       ├── token_counter.py
│       ├── tool_synchronizer.py
│       └── load_manager.py
├── bootstrap/             # Agent bootstrap scripts
│   └── bootstrap_librarian.py
├── tests/                 # Test suites
│   ├── test_librarian_integration.py
│   ├── test_token_counting.py
│   ├── test_compatibility.py
│   └── validate_config.py
├── docs/                  # Documentation
├── config.example         # Configuration template
└── requirements.txt       # Dependencies
```

## Running in Development

### Start Development Server

```bash
# With auto-reload
python main.py

# Or with uvicorn directly
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

### Access API Documentation

When `LIBRARIAN_DEBUG=true` or `LIBRARIAN_ENABLE_DOCS=true`:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Testing

### Run All Tests

```bash
python tests/test_librarian_integration.py
```

### Run Specific Test Suites

```bash
# Token counting tests
python tests/test_token_counting.py

# Compatibility tests
python tests/test_compatibility.py

# Configuration validation
python tests/validate_config.py
```

### Test with pytest

```bash
# Install pytest if not already installed
pip install pytest pytest-asyncio

# Run tests
pytest tests/
```

## Code Style

### Python Style Guide

Follow PEP 8 with these guidelines:

- **Line length**: 100 characters (soft limit)
- **Indentation**: 4 spaces
- **Imports**: Grouped (stdlib, third-party, local)
- **Type hints**: Use type hints for function signatures
- **Docstrings**: Use Google-style docstrings

### Example Code Style

```python
"""
Module docstring here.
"""

from typing import List, Optional, Dict
import logging

logger = logging.getLogger(__name__)


def example_function(
    param1: str,
    param2: Optional[int] = None
) -> Dict[str, Any]:
    """
    Function docstring.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        Description of return value
    """
    # Implementation
    pass
```

### Linting

```bash
# Install linting tools
pip install flake8 black isort mypy

# Run linters
flake8 src/ main.py
black --check src/ main.py
isort --check src/ main.py
mypy src/ main.py
```

### Auto-formatting

```bash
# Format code
black src/ main.py
isort src/ main.py
```

## Adding New Features

### 1. Create Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Implement Feature

- Follow code style guidelines
- Add type hints
- Write docstrings
- Add tests

### 3. Test Your Changes

```bash
# Run tests
python tests/test_librarian_integration.py

# Test manually
python main.py
# Test endpoints with curl or Postman
```

### 4. Update Documentation

- Update relevant documentation in `docs/`
- Update README if needed
- Add examples if applicable

### 5. Commit Changes

```bash
git add .
git commit -m "feat: description of your feature"
```

### Commit Message Format

Follow conventional commits:

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes
- `refactor:` Code refactoring
- `test:` Test changes
- `chore:` Maintenance tasks

## Adding New Components

### Example: Adding a New Component

1. **Create component file** in `src/librarian/`:

```python
"""
New Component for The Librarian

Copyright (c) 2025 AnimusUNO
Licensed under AGPLv3
"""

from typing import Optional
import logging

logger = logging.getLogger(__name__)


class NewComponent:
    """Description of the component."""
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize component."""
        self.config = config or {}
    
    def do_something(self, param: str) -> str:
        """Do something."""
        # Implementation
        pass
```

2. **Export in `src/librarian/__init__.py`**:

```python
from .new_component import NewComponent

__all__ = [
    # ... existing exports
    "NewComponent",
]
```

3. **Use in `main.py`**:

```python
from src.librarian import NewComponent

new_component = NewComponent()
```

4. **Add tests** in `tests/test_new_component.py`

## Debugging

### Enable Debug Logging

```bash
LIBRARIAN_LOG_LEVEL=DEBUG
LIBRARIAN_DEBUG=true
```

### Debug with Print Statements

```python
import logging
logger = logging.getLogger(__name__)

logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
```

### Debug with Python Debugger

```python
import pdb; pdb.set_trace()  # Breakpoint
```

### Debug with IDE

- VS Code: Use Python debugger
- PyCharm: Use built-in debugger
- Set breakpoints in code

## Common Development Tasks

### Adding a New Model

1. Update `ModelRegistry` in `src/librarian/model_registry.py`
2. Add to `TokenCounter` in `src/librarian/token_counter.py`
3. Test with the new model

### Adding a New Endpoint

1. Add route in `main.py`
2. Implement handler function
3. Add tests
4. Update API documentation

### Modifying Message Translation

1. Update `MessageTranslator` in `src/librarian/message_translator.py`
2. Test with various message formats
3. Update tests

## Performance Testing

### Load Testing

```bash
# Install load testing tools
pip install locust

# Run load tests
locust -f tests/load_test.py
```

### Profiling

```bash
# Install profiling tools
pip install py-spy

# Profile application
py-spy record -o profile.svg -- python main.py
```

## Contributing

### Pull Request Process

1. Fork the repository
2. Create feature branch
3. Make changes
4. Add tests
5. Update documentation
6. Submit pull request

### Pull Request Checklist

- [ ] Code follows style guidelines
- [ ] Tests pass
- [ ] Documentation updated
- [ ] Commit messages follow convention
- [ ] No breaking changes (or documented)

## Troubleshooting Development Issues

### Import Errors

**Problem**: Cannot import modules

**Solutions**:
- Ensure virtual environment is activated
- Check PYTHONPATH
- Verify package structure

### Test Failures

**Problem**: Tests failing

**Solutions**:
- Check Letta server connection
- Verify agent IDs are correct
- Check configuration
- Review test logs

### Debug Mode Not Working

**Problem**: Auto-reload not working

**Solutions**:
- Verify `LIBRARIAN_DEBUG=true`
- Check uvicorn is using `--reload`
- Restart server

## Next Steps

- See [Architecture](architecture.md) for system architecture
- See [API Reference](api-reference.md) for API documentation
- See [Deployment Guide](deployment.md) for production deployment

