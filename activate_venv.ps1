# Python Virtual Environment Activation Script for Windows
# Run this script to activate the virtual environment

Write-Host "Activating Python virtual environment..." -ForegroundColor Green

# Check if virtual environment exists
if (Test-Path "python\venv\Scripts\Activate.ps1") {
    & "python\venv\Scripts\Activate.ps1"
    Write-Host "Virtual environment activated successfully!" -ForegroundColor Green
    Write-Host "You can now install packages with: pip install -r requirements.txt" -ForegroundColor Yellow
} else {
    Write-Host "Virtual environment not found. Please run: python -m venv python\venv" -ForegroundColor Red
}
