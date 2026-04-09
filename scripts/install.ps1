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
$dirs = @("brain", "client", "data", "logs", "scripts")
foreach ($d in $dirs) {
    $path = Join-Path $jarvisRoot $d
    if (-not (Test-Path $path)) {
        New-Item -ItemType Directory -Path $path -Force | Out-Null
    }
}
Write-Host "  Directories OK." -ForegroundColor Green

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

# 4. Verify data files
Write-Host "[4/8] Verifying data files..." -ForegroundColor Yellow
$userJson = Join-Path $jarvisRoot "data\user.json"
$memoryJson = Join-Path $jarvisRoot "data\memory.json"
if (-not (Test-Path $userJson)) {
    Write-Host "  ERROR: user.json not found!" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $memoryJson)) {
    "[]" | Out-File -FilePath $memoryJson -Encoding utf8
}
Write-Host "  Data files OK." -ForegroundColor Green

# 5. Register jarvis command on PATH
Write-Host "[5/8] Registering 'jarvis' command..." -ForegroundColor Yellow
$clientDir = Join-Path $jarvisRoot "client"
$currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($currentPath -notlike "*$clientDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$currentPath;$clientDir", "User")
    Write-Host "  Added $clientDir to user PATH." -ForegroundColor Green
} else {
    Write-Host "  Already on PATH." -ForegroundColor Green
}
# Also update current session PATH
if ($env:Path -notlike "*$clientDir*") {
    $env:Path = "$env:Path;$clientDir"
}

# 6. Register Task Scheduler auto-start
Write-Host "[6/8] Setting up auto-start on login..." -ForegroundColor Yellow
$taskName = "JarvisBrain"
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

$action = New-ScheduledTaskAction `
    -Execute $venvPython `
    -Argument "-m uvicorn brain.server:app --host 127.0.0.1 --port 8765 --log-level info" `
    -WorkingDirectory $jarvisRoot

$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Days 365)

# Hide the window by running it hidden
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "Jarvis AI Brain - auto-start on login" | Out-Null

Write-Host "  Task '$taskName' registered." -ForegroundColor Green

# 7. Start the brain now
Write-Host "[7/8] Starting Jarvis brain..." -ForegroundColor Yellow
# Kill any existing brain process
$existing = Get-Process -Name python, pythonw -ErrorAction SilentlyContinue |
    Where-Object {
        try {
            $cmdLine = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
            $cmdLine -match "brain\.server" -or $cmdLine -match "uvicorn.*brain"
        } catch { $false }
    }
if ($existing) {
    $existing | Stop-Process -Force
    Start-Sleep -Seconds 2
}

# Start brain in background
Start-Process -FilePath $venvPython `
    -ArgumentList "-m uvicorn brain.server:app --host 127.0.0.1 --port 8765 --log-level info" `
    -WorkingDirectory $jarvisRoot `
    -WindowStyle Hidden

# Wait for brain to come online
Write-Host "  Waiting for brain to come online..." -ForegroundColor Yellow
$maxWait = 30
$waited = 0
$online = $false
while ($waited -lt $maxWait) {
    Start-Sleep -Seconds 1
    $waited++
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8765/status" -TimeoutSec 2
        if ($response.ok -eq $true) {
            $online = $true
            break
        }
    } catch {
        # Not ready yet
    }
}

if ($online) {
    Write-Host "  Brain is ONLINE." -ForegroundColor Green
} else {
    Write-Host "  WARNING: Brain did not respond within ${maxWait}s. Check logs at C:\jarvis\logs\jarvis.log" -ForegroundColor Red
}

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
