# Stop the Jarvis brain server
$ErrorActionPreference = "SilentlyContinue"

Write-Host "Stopping Jarvis brain..." -ForegroundColor Cyan

$procs = Get-Process -Name python, pythonw -ErrorAction SilentlyContinue |
    Where-Object {
        try {
            $cmdLine = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
            $cmdLine -match "brain\.server" -or $cmdLine -match "uvicorn.*brain"
        } catch { $false }
    }

if ($procs) {
    $procs | Stop-Process -Force
    Write-Host "Jarvis brain stopped." -ForegroundColor Green
} else {
    Write-Host "Jarvis brain is not running." -ForegroundColor Yellow
}
