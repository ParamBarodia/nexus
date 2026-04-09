# Start the Jarvis brain server
$ErrorActionPreference = "Stop"

Write-Host "Starting Jarvis brain..." -ForegroundColor Cyan

$venvPython = "C:\jarvis\venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "ERROR: Virtual environment not found at C:\jarvis\venv" -ForegroundColor Red
    Write-Host "Run install.ps1 first." -ForegroundColor Yellow
    exit 1
}

# Start the brain server
Set-Location "C:\jarvis"
& $venvPython -m uvicorn brain.server:app --host 127.0.0.1 --port 8765 --log-level info
