# Start WhatsApp Node.js Bridge
$ErrorActionPreference = "Stop"
$whatsappDir = "C:\jarvis\brain\whatsapp"

Write-Host "[Nexus] Starting WhatsApp Bridge..." -ForegroundColor Cyan

# Check Node.js
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Node.js not found. Install from https://nodejs.org" -ForegroundColor Red
    exit 1
}

# Install npm deps if needed
if (-not (Test-Path (Join-Path $whatsappDir "node_modules"))) {
    Write-Host "Installing npm dependencies..." -ForegroundColor Yellow
    Push-Location $whatsappDir
    npm install --quiet
    Pop-Location
}

# Load .env for allowed numbers
$env:WHATSAPP_ALLOWED_NUMBERS = (Get-Content "C:\jarvis\.env" | Select-String "WHATSAPP_ALLOWED_NUMBERS" | ForEach-Object { $_.Line.Split("=", 2)[1] })

# Start bridge
Write-Host "Starting Node bridge on port 8766..." -ForegroundColor Yellow
Start-Process -FilePath "node" `
    -ArgumentList "bridge.js" `
    -WorkingDirectory $whatsappDir `
    -WindowStyle Normal

Write-Host ""
Write-Host "WhatsApp bridge started. Scan QR code if this is the first time." -ForegroundColor Green
Write-Host "Check status: curl http://localhost:8766/status" -ForegroundColor Gray
