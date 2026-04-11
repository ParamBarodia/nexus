# Nexus / J.A.R.V.I.S. — Full Installation Script
$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  N E X U S  -  Installation            " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$jarvisRoot = "C:\jarvis"
$venvPath   = Join-Path $jarvisRoot "venv"
$venvPip    = Join-Path $venvPath "Scripts\pip.exe"
$venvPython = Join-Path $venvPath "Scripts\python.exe"

# [1/10] Directory structure
Write-Host "[1/10] Verifying directory structure..." -ForegroundColor Yellow
$dirs = @("brain", "client", "dashboard", "data", "logs", "scripts", "hud",
          "data/chroma", "data/mem0", "data/briefings", "data/reflections",
          "data/episodes", "data/audio", "data/backups", "data/exports",
          "brain/mcp_servers_india", "brain/connectors", "brain/capabilities", "brain/briefing")
foreach ($d in $dirs) {
    $path = Join-Path $jarvisRoot $d
    if (-not (Test-Path $path)) {
        New-Item -ItemType Directory -Path $path -Force | Out-Null
    }
}
Write-Host "  Directories OK." -ForegroundColor Green

# [2/10] .env setup
Write-Host "[2/10] Setting up environment variables..." -ForegroundColor Yellow
$envFile = Join-Path $jarvisRoot ".env"
if (-not (Test-Path $envFile)) {
    $token = [guid]::NewGuid().ToString().Replace("-", "")
    $envContent = @"
TIER1_MODEL=gemma2:2b
TIER2_MODEL=qwen2.5:7b
TIER3_LOCAL_MODEL=qwen2.5:14b
TIER3_CLOUD_ENABLED=false
ANTHROPIC_API_KEY=
TIER3_CLOUD_MODEL=claude-sonnet-4-5-20250929
TIER3_CLOUD_DAILY_LIMIT_USD=2.00
TIER3_MODE=ask_user
NTFY_TOPIC=nexus-param-$([guid]::NewGuid().ToString().Substring(0,8))
BRAIN_BEARER_TOKEN=$token

# Voice
STT_PRIMARY=faster-whisper
STT_MODEL=large-v3-turbo
STT_INDIC=true
STT_LANGUAGE=auto
WAKE_WORD=hey_jarvis
WAKE_WORD_THRESHOLD=0.5

# WhatsApp
WHATSAPP_ENABLED=false
WHATSAPP_NODE_BRIDGE_URL=http://localhost:8766
WHATSAPP_ALLOWED_NUMBERS=
WHATSAPP_OWNER_NUMBER=

# Location
HOME_LAT=23.0225
HOME_LON=72.5714

# Watchlists
REDDIT_SUBS=LocalLLaMA,neuroscience,india,IndianStreetBets
STOCK_WATCHLIST=RELIANCE.NS,INFY.NS,TCS.NS
CRYPTO_WATCHLIST=bitcoin,ethereum,solana

# TTS
TTS_BACKEND=edge
TTS_VOICE=en-GB-RyanNeural

# Search
TAVILY_API_KEY=
"@
    $envContent | Out-File -FilePath $envFile -Encoding utf8
    Write-Host "  .env created with bearer token: $token" -ForegroundColor Green
} else {
    Write-Host "  .env already exists." -ForegroundColor Green
}

# [3/10] Python venv
Write-Host "[3/10] Creating Python virtual environment..." -ForegroundColor Yellow
if (-not (Test-Path (Join-Path $venvPath "Scripts\python.exe"))) {
    python -m venv $venvPath
    Write-Host "  Virtual environment created." -ForegroundColor Green
} else {
    Write-Host "  Virtual environment already exists." -ForegroundColor Green
}

# [4/10] Pip dependencies
Write-Host "[4/10] Installing Python dependencies..." -ForegroundColor Yellow
& $venvPip install -r (Join-Path $jarvisRoot "requirements.txt") --quiet
Write-Host "  Dependencies installed." -ForegroundColor Green

# [5/10] Ollama models
Write-Host "[5/10] Pulling Ollama models (this may take a while)..." -ForegroundColor Yellow
$models = @("gemma2:2b", "qwen2.5:7b", "qwen2.5:14b", "nomic-embed-text")
foreach ($model in $models) {
    Write-Host "  Pulling $model..." -ForegroundColor Gray
    ollama pull $model
}
Write-Host "  All models pulled." -ForegroundColor Green

# [6/10] Data files
Write-Host "[6/10] Verifying data files..." -ForegroundColor Yellow
$userJson     = Join-Path $jarvisRoot "data\user.json"
$memoryJson   = Join-Path $jarvisRoot "data\memory.json"
$projectsJson = Join-Path $jarvisRoot "data\projects.json"
$hooksJson    = Join-Path $jarvisRoot "data\hooks.json"
$connState    = Join-Path $jarvisRoot "data\connectors_state.json"
$rssFeeds     = Join-Path $jarvisRoot "data\rss_feeds.json"

if (-not (Test-Path $userJson)) {
    Write-Host "  WARNING: user.json not found. Creating default." -ForegroundColor Yellow
    '{"name": "User", "age": "", "city": "", "role": "", "projects": [], "ambitions": [], "personality_notes": []}' | Out-File -FilePath $userJson -Encoding utf8
}
if (-not (Test-Path $memoryJson))   { "[]" | Out-File -FilePath $memoryJson -Encoding utf8 }
if (-not (Test-Path $projectsJson)) { '{"projects": [], "active_project_id": null}' | Out-File -FilePath $projectsJson -Encoding utf8 }
if (-not (Test-Path $hooksJson))    { "[]" | Out-File -FilePath $hooksJson -Encoding utf8 }
if (-not (Test-Path $connState))    { "{}" | Out-File -FilePath $connState -Encoding utf8 }
if (-not (Test-Path $rssFeeds))     { "[]" | Out-File -FilePath $rssFeeds -Encoding utf8 }
Write-Host "  Data files OK." -ForegroundColor Green

# [7/10] WhatsApp bridge (optional)
Write-Host "[7/10] Checking WhatsApp bridge..." -ForegroundColor Yellow
$waPackage = Join-Path $jarvisRoot "brain\whatsapp\package.json"
if (Test-Path $waPackage) {
    $waDir = Join-Path $jarvisRoot "brain\whatsapp"
    if (-not (Test-Path (Join-Path $waDir "node_modules"))) {
        Write-Host "  Installing WhatsApp bridge npm dependencies..." -ForegroundColor Gray
        Push-Location $waDir
        npm install --quiet 2>$null
        Pop-Location
        Write-Host "  WhatsApp bridge dependencies installed." -ForegroundColor Green
    } else {
        Write-Host "  WhatsApp bridge already set up." -ForegroundColor Green
    }
} else {
    Write-Host "  WhatsApp bridge not found (optional)." -ForegroundColor Gray
}

# [8/10] Add jarvis command to PATH
Write-Host "[8/10] Setting up global 'jarvis' command..." -ForegroundColor Yellow
$clientDir = Join-Path $jarvisRoot "client"
$currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($currentPath -notlike "*$clientDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$currentPath;$clientDir", "User")
    Write-Host "  Added $clientDir to user PATH." -ForegroundColor Green
    Write-Host "  Open a NEW terminal for 'jarvis' command to work." -ForegroundColor Yellow
} else {
    Write-Host "  Already in PATH." -ForegroundColor Green
}

# [9/10] Start brain server
Write-Host "[9/10] Starting brain server..." -ForegroundColor Yellow
Start-Process -FilePath $venvPython -ArgumentList "-m uvicorn brain.server:app --host 127.0.0.1 --port 8765 --log-level info" -WorkingDirectory $jarvisRoot -WindowStyle Hidden
Write-Host "  Brain server starting in background..." -ForegroundColor Green

# [10/10] Verify
Write-Host "[10/10] Verifying installation..." -ForegroundColor Yellow
Start-Sleep -Seconds 5
# Read bearer token from .env
$bearerToken = ""
foreach ($line in Get-Content $envFile) {
    if ($line -match "^BRAIN_BEARER_TOKEN=(.+)$") {
        $bearerToken = $matches[1].Trim()
    }
}
try {
    $headers = @{ "Authorization" = "Bearer $bearerToken" }
    $status = Invoke-RestMethod -Uri "http://localhost:8765/status" -Headers $headers -TimeoutSec 10
    Write-Host "  Brain:  ONLINE" -ForegroundColor Green
    Write-Host "  Model:  $($status.model)" -ForegroundColor Green
    Write-Host "  Memory: $($status.memory_facts) facts" -ForegroundColor Green
} catch {
    Write-Host "  Brain not responding yet. Check: C:\jarvis\logs\jarvis.log" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Nexus installation complete.          " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Commands (open a NEW terminal):" -ForegroundColor White
Write-Host "  jarvis                Interactive chat" -ForegroundColor Cyan
Write-Host "  jarvis --status       System health" -ForegroundColor Gray
Write-Host "  jarvis --connectors   List connectors" -ForegroundColor Gray
Write-Host "  jarvis --setup        Configure API keys" -ForegroundColor Gray
Write-Host "  jarvis --hud          Desktop overlay" -ForegroundColor Gray
Write-Host "  jarvis --greet        Voice greeting" -ForegroundColor Gray
Write-Host "  jarvis --briefing     Morning briefing" -ForegroundColor Gray
Write-Host "  jarvis --listen       Wake word mode" -ForegroundColor Gray
Write-Host ""
