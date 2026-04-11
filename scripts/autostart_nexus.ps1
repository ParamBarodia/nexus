# Auto-start Nexus brain on Windows login
# Registers a Windows Task Scheduler task that starts the brain server at logon.

$TaskName = "NexusBrainAutoStart"
$VenvPython = "C:\jarvis\venv\Scripts\python.exe"
$WorkDir = "C:\jarvis"

# Remove existing task if present
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

# Create the action: start uvicorn via venv python
$Action = New-ScheduledTaskAction `
    -Execute $VenvPython `
    -Argument "-m uvicorn brain.server:app --host 127.0.0.1 --port 8765 --log-level info" `
    -WorkingDirectory $WorkDir

# Trigger: at logon of current user
$Trigger = New-ScheduledTaskTrigger -AtLogOn

# Settings: restart on failure, don't stop on idle, run indefinitely
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Days 365)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "Nexus AI Brain Server - auto-starts at login" `
    -RunLevel Highest

Write-Host "Nexus auto-start registered: $TaskName" -ForegroundColor Green
Write-Host "Brain will start automatically at next login." -ForegroundColor Cyan
