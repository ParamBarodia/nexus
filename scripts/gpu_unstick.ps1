# gpu_unstick.ps1 — recover a wedged GPU on the 6GB box.
#
# Symptom this fixes: chats (and even raw Ollama calls) hang/time out while the GPU
# sits at ~100% util and ~5.7/6.1 GB used, yet `ollama ps` shows NO model loaded.
# Cause: orphaned `llama-server.exe` model-runners left behind by killed or abandoned
# requests keep squatting VRAM, so Ollama can't load a model. Killing them frees the GPU;
# Ollama re-spawns a fresh runner on the next request.
#
# Safe to run anytime: at worst it evicts a currently-loaded model, which simply reloads
# on the next call.

$ErrorActionPreference = "SilentlyContinue"

Write-Host "== Before =="
& nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu --format=csv,noheader
$runners = Get-Process llama-server -ErrorAction SilentlyContinue
Write-Host ("llama-server runners: " + ($runners | Measure-Object).Count)

if ($runners) {
    $runners | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep 2
    Write-Host "Killed orphaned runners."
}

Write-Host "== After =="
& nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu --format=csv,noheader

# Ensure the Ollama server itself is up (the runners are children; the server persists).
if (-not (Get-NetTCPConnection -LocalPort 11434 -State Listen -ErrorAction SilentlyContinue)) {
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
    Write-Host "Restarted ollama serve."
}

Write-Host "Done. Next request will spawn a fresh runner."
