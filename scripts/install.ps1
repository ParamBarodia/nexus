# Jarvis Phase 0 - Installation Script
$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  J.A.R.V.I.S. - Phase 0 Installation   " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$jarvisRoot = "C:\jarvis"

# 1. Ensure directory structure exists
Write-Host "[1/8] Verifying directory structure..." -ForegroundColor Yellow
$dirs = @("brain", "client", "data", "logs", "scripts", "data/chroma", "data/mem0", "brain/mcp_servers_india")
foreach ($d in $dirs) {
    $path = Join-Path $jarvisRoot $d
    if (-not (Test-Path $path)) {
        New-Item -ItemType Directory -Path $path -Force | Out-Null
    }
}
Write-Host "  Directories OK." -ForegroundColor Green

# 1.5 Setup .env file
Write-Host "[1.5/8] Setting up environment variables..." -ForegroundColor Yellow
$envFile = Join-Path $jarvisRoot ".env"
if (-not (Test-Path $envFile)) {
    $token = [Convert]::ToBase64String([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
    $envContent = @"
TIER2_MODEL=qwen2.5:7b
TIER3_LOCAL_MODEL=qwen2.5:14b
TIER3_CLOUD_ENABLED=false
ANTHROPIC_API_KEY=
TIER3_MODE=ask_user
NTFY_TOPIC=nexus-param-$([guid]::NewGuid().ToString().Substring(0,8))
BRAIN_BEARER_TOKEN=$token
"@
    $envContent | Out-File -FilePath $envFile -Encoding utf8
    Write-Host "  .env file created with new bearer token." -ForegroundColor Green
} else {
    Write-Host "  .env file already exists." -ForegroundColor Green
}

# 2. Create Python virtual environment
Write-Host "[2/8] Creating Python virtual environment..." -ForegroundColor Yellow
$venvPath = Join-Path $jarvisRoot "venv"
if (-not (Test-Path (Join-Path $venvPath "Scripts\python.exe"))) {
    python -m venv $venvPath
    Write-Host "  Virtual environment created." -ForegroundColor Green
} else {
    Write-Host "  Virtual environment already exists." -ForegroundColor Green
}

# 3. Install dependencies
Write-Host "[3/8] Installing dependencies..." -ForegroundColor Yellow
$venvPip = Join-Path $venvPath "Scripts\pip.exe"
$venvPython = Join-Path $venvPath "Scripts\python.exe"
& $venvPip install -r (Join-Path $jarvisRoot "requirements.txt") --quiet
Write-Host "  Dependencies installed." -ForegroundColor Green

# 3.5 Pull Ollama models
Write-Host "[3.5/8] Pulling Ollama models (this may take a while)..." -ForegroundColor Yellow
ollama pull gemma2:2b
ollama pull qwen2.5:7b
ollama pull qwen2.5:14b
ollama pull nomic-embed-text
Write-Host "  Models pulled." -ForegroundColor Green

# 4. Verify data files
Write-Host "[4/8] Verifying data files..." -ForegroundColor Yellow
$userJson = Join-Path $jarvisRoot "data\user.json"
$memoryJson = Join-Path $jarvisRoot "data\memory.json"
$projectsJson = Join-Path $jarvisRoot "data\projects.json"
if (-not (Test-Path $userJson)) {
    Write-Host "  ERROR: user.json not found!" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $memoryJson)) {
    "[]" | Out-File -FilePath $memoryJson -Encoding utf8
}
if (-not (Test-Path $projectsJson)) {
    '{"projects": [], "active_project_id": null}' | Out-File -FilePath $projectsJson -Encoding utf8
}
Write-Host "  Data files OK." -ForegroundColor Green

# 8. Verify
Write-Host "[8/8] Verification..." -ForegroundColor Yellow
try {
    $status = Invoke-RestMethod -Uri "http://localhost:8765/status" -TimeoutSec 5
    Write-Host "  Status: OK" -ForegroundColor Green
    Write-Host "  Model:  $($status.model)" -ForegroundColor Green
    Write-Host "  Memory: $($status.memory_turns) turns" -ForegroundColor Green
} catch {
    Write-Host "  Could not verify. Check logs." -ForegroundColor Red
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Installation complete.                " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Open a NEW PowerShell window and type:" -ForegroundColor White
Write-Host "  jarvis" -ForegroundColor Cyan
Write-Host ""
Write-Host "Other commands:" -ForegroundColor White
Write-Host "  jarvis --status    Check brain health" -ForegroundColor Gray
Write-Host "  jarvis --reset     Clear conversation memory" -ForegroundColor Gray
Write-Host ""
