# start_hud.ps1 — launch the JARVIS HUD overlay (ensures Ollama + brain are up first).
$ErrorActionPreference = "SilentlyContinue"
& "C:\jarvis\scripts\start_nexus.ps1" -NoBrowser
Start-Process -FilePath "C:\jarvis\venv\Scripts\pythonw.exe" `
    -ArgumentList '"C:\jarvis\client\jarvis.py" --hud' `
    -WorkingDirectory "C:\jarvis" -WindowStyle Hidden
