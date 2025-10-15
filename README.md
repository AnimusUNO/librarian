# Librarian Project

## Python Virtual Environment Setup

This project uses a Python virtual environment located in the `python/` folder.

### Quick Start

1. **Activate the virtual environment:**
   ```powershell
   # Windows PowerShell
   .\activate_venv.ps1
   
   # Or manually:
   python\venv\Scripts\Activate.ps1
   ```

2. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

3. **Deactivate when done:**
   ```powershell
   deactivate
   ```

### Project Structure

```
librarian/
├── .gitignore          # Git ignore rules for Python projects
├── requirements.txt    # Python dependencies
├── activate_venv.ps1   # Virtual environment activation script
└── python/
    └── venv/           # Virtual environment (ignored by git)
```

### Development

- The virtual environment is already set up in `python/venv/`
- Add your project dependencies to `requirements.txt`
- The `.gitignore` file includes comprehensive Python ignore patterns
- Use the provided PowerShell script to easily activate the environment

### Notes

- The virtual environment is excluded from version control
- All Python cache files and temporary files are ignored
- IDE-specific files (VS Code, PyCharm, etc.) are ignored
- OS-specific files (Windows, macOS, Linux) are ignored
