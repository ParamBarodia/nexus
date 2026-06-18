# start_nexus.ps1 — bring Nexus online (Ollama + brain) and open the dashboard.
# No admin required. Safe to run repeatedly (idempotent).
#   -NoBrowser : start services only (used by the logon Startup entry)
param([switch]$NoBrowser)

$ErrorActionPreference = "SilentlyContinue"
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

# 1. Ensure Ollama is serving (the local models live here).
if (-not (Get-NetTCPConnection -LocalPort 11434 -State Listen -ErrorAction SilentlyContinue)) {
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep 4
}

# 2. Ensure the brain (FastAPI :8765) is running — launched windowless via pythonw.
if (-not (Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue)) {
    Start-Process -FilePath "C:\jarvis\venv\Scripts\pythonw.exe" `
        -ArgumentList "-m uvicorn brain.server:app --host 127.0.0.1 --port 8765" `
        -WorkingDirectory "C:\jarvis" -WindowStyle Hidden
    for ($i = 0; $i -lt 40; $i++) {
        if (Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue) { break }
        Start-Sleep 1
    }
}

# 3. Open the dashboard (unless started headlessly at logon).
if (-not $NoBrowser) {
    Start-Process "http://localhost:8765/"
}
