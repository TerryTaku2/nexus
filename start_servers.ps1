# NeXus Project — Local Server Startup Script
# Starts all backend APIs in separate terminal windows.
#
# API Port Map:
#   Login / Auth API        → http://localhost:8000
#   Community / Networking  → http://localhost:8001  (WebSocket: ws://localhost:8001)
#   Government API          → http://localhost:8002
#   Toolkit API             → http://localhost:8005
#
# Usage: Right-click start_servers.ps1 → "Run with PowerShell"
#        OR from a PowerShell terminal: .\start_servers.ps1

$root = $PSScriptRoot

# ── Step 1: Ensure the database exists ─────────────────────────────────────
Write-Host "Checking database..." -ForegroundColor Cyan
$dbPath = Join-Path $root "Database\Nexus.db"
if (-not (Test-Path $dbPath)) {
    Write-Host "Creating database..." -ForegroundColor Yellow
    python "$root\Database\Nexus Database.py"
} else {
    Write-Host "Database found: $dbPath" -ForegroundColor Green
}

# ── Step 2: Start APIs ──────────────────────────────────────────────────────

function Start-API {
    param(
        [string]$Title,
        [string]$WorkingDir,
        [string]$Module,
        [int]$Port,
        [string]$Color = "Cyan"
    )
    Write-Host "Starting $Title on port $Port..." -ForegroundColor $Color
    Start-Process powershell -ArgumentList `
        "-NoExit", "-Command",
        "Set-Location '$WorkingDir'; Write-Host '$Title' -ForegroundColor $Color; python -m uvicorn ${Module} --reload --port $Port"
}

# File server (serves all HTML pages) — port 3000
Write-Host "Starting File Server (Frontend) on port 3000..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList `
    "-NoExit", "-Command",
    "Set-Location '$root'; Write-Host 'File Server - port 3000' -ForegroundColor Cyan; python -m http.server 3000"

Start-Sleep -Milliseconds 500

# Login API — port 8000
Start-API -Title "Login API" `
          -WorkingDir "$root\login" `
          -Module "login_api:app" `
          -Port 8000 `
          -Color "Green"

Start-Sleep -Milliseconds 500

# Community / Networking API — port 8001
Start-API -Title "Community API" `
          -WorkingDir "$root\Pillar 1- Networking" `
          -Module "Community:app" `
          -Port 8001 `
          -Color "Magenta"

Start-Sleep -Milliseconds 500

# Government API — port 8002
Start-API -Title "Government API" `
          -WorkingDir "$root\Pillar 2- Government" `
          -Module "government_api:app" `
          -Port 8002 `
          -Color "Blue"

Start-Sleep -Milliseconds 500

# Toolkit API — port 8005
Start-API -Title "Toolkit API" `
          -WorkingDir "$root\Toolkit" `
          -Module "Toolkit_API:app" `
          -Port 8005 `
          -Color "Yellow"

Write-Host ""
Write-Host "============================================" -ForegroundColor White
Write-Host " All servers starting. Open in your browser:" -ForegroundColor White
Write-Host "   Login page  →  login\login.html" -ForegroundColor Green
Write-Host "   Dashboard   →  dashboard\dashboard.html" -ForegroundColor Cyan
Write-Host "   Toolkit     →  Toolkit\toolkit.html" -ForegroundColor Yellow
Write-Host "   Government  →  Pillar 2- Government\government.html" -ForegroundColor Blue
Write-Host "   Networking  →  Pillar 1- Networking\network_hub.html" -ForegroundColor Magenta
Write-Host "============================================" -ForegroundColor White
Write-Host ""
Write-Host "API Docs (Swagger UI):" -ForegroundColor Gray
Write-Host "   http://localhost:8000/docs  (Login)" -ForegroundColor Gray
Write-Host "   http://localhost:8001/docs  (Community)" -ForegroundColor Gray
Write-Host "   http://localhost:8002/docs  (Government)" -ForegroundColor Gray
Write-Host "   http://localhost:8005/docs  (Toolkit)" -ForegroundColor Gray
