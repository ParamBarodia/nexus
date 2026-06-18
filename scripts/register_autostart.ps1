# register_autostart.ps1
# Registers Nexus to start at logon, plus a Signal Monitor that runs 30 min after boot.
# Safe to re-run (idempotent). Does not require the venv to exist yet.
#
# NOTE: Registering AtLogOn scheduled tasks requires an ELEVATED terminal.
# Run this from "Windows Terminal (Admin)" / "PowerShell (Admin)". If not elevated,
# the script completes without crashing and tells you what to do.

$ErrorActionPreference = "Stop"
$WorkDir = "C:\jarvis"

function Register-NexusTask($name, $action, $trigger, $settings, $desc) {
    try {
        Unregister-ScheduledTask -TaskName $name -Confirm:$false -ErrorAction SilentlyContinue
        Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger `
            -Settings $settings -Description $desc -ErrorAction Stop | Out-Null
        Write-Host "[OK] Registered '$name'." -ForegroundColor Green
        return $true
    } catch {
        if ("$_" -match "denied|0x80070005") {
            Write-Host "[SKIP] '$name' needs an elevated terminal. Re-run this script as Administrator." -ForegroundColor Yellow
        } else {
            Write-Host "[WARN] '$name': $_" -ForegroundColor Yellow
        }
        return $false
    }
}

# Resolve a Python interpreter: prefer the project venv, else fall back to system python.
$VenvPython = Join-Path $WorkDir "venv\Scripts\python.exe"
if (Test-Path $VenvPython) {
    $Python = $VenvPython
} else {
    $sys = Get-Command python -ErrorAction SilentlyContinue
    $Python = if ($sys) { $sys.Source } else { $VenvPython }  # best-guess; registration still succeeds
}
Write-Host "Using Python: $Python" -ForegroundColor DarkGray

$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Days 365)

# --- Task 1: NexusBrain — start the brain server at logon -------------------
$brainAction = New-ScheduledTaskAction -Execute $Python `
    -Argument "-m uvicorn brain.server:app --host 127.0.0.1 --port 8765 --log-level info" `
    -WorkingDirectory $WorkDir
$brainTrigger = New-ScheduledTaskTrigger -AtLogOn
$okBrain = Register-NexusTask "NexusBrain" $brainAction $brainTrigger $Settings `
    "Nexus brain server (FastAPI :8765) - auto-start at logon"

# --- Task 2: NexusSignalMonitor — fires 30 min after logon ------------------
# Pings the brain's proactive briefing so Nexus surfaces signals once the
# session has settled. Runs via PowerShell so it's self-contained.
$sigCommand = "try { Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8765/proactive/domains_check' -TimeoutSec 30 } catch {}; try { Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8765/proactive/briefing' -TimeoutSec 30 } catch {}"
$sigAction = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -WindowStyle Hidden -Command `"$sigCommand`""
$sigTrigger = New-ScheduledTaskTrigger -AtLogOn
$sigTrigger.Delay = "PT30M"   # 30 minutes after boot/logon
$okSig = Register-NexusTask "NexusSignalMonitor" $sigAction $sigTrigger $Settings `
    "Nexus Signal Monitor - runs 30 min after boot"

if ($okBrain -and $okSig) {
    Write-Host "`nNexus autostart configured. Tasks: NexusBrain, NexusSignalMonitor" -ForegroundColor Cyan
} else {
    Write-Host "`nScript completed. Re-run as Administrator to finish registering the task(s) above." -ForegroundColor Cyan
}
