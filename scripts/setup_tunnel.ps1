# Setup Cloudflare Tunnel for Nexus Brain
$ErrorActionPreference = "Stop"

Write-Host "Setting up Cloudflare Tunnel..." -ForegroundColor Cyan

# 1. Install cloudflared if missing
if (-not (Get-Command cloudflared -ErrorAction SilentlyContinue)) {
    Write-Host "Installing cloudflared via winget..." -ForegroundColor Yellow
    winget install Cloudflare.cloudflared
}

# 2. Instructions
Write-Host ""
Write-Host "To expose your Nexus brain to the web:" -ForegroundColor White
Write-Host "1. Run: cloudflared tunnel login" -ForegroundColor Gray
Write-Host "2. Run: cloudflared tunnel create nexus" -ForegroundColor Gray
Write-Host "3. Run: cloudflared tunnel route dns nexus <your-domain>" -ForegroundColor Gray
Write-Host "4. Start: cloudflared tunnel run nexus" -ForegroundColor Gray
Write-Host ""
Write-Host "On your remote device, set JARVIS_BRAIN_URL=<your-domain>" -ForegroundColor Cyan
Write-Host "And ensure BRAIN_BEARER_TOKEN matches your .env file." -ForegroundColor Cyan
