# Copy .env.example if needed, start compose, wait for health, import demo docs.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "docker is required"
}
docker compose version | Out-Null

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example"
}

Write-Host "Starting services..."
docker compose up -d

Write-Host "Waiting for backend health..."
$ok = $false
for ($i = 1; $i -le 60; $i++) {
    try {
        Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 3 | Out-Null
        $ok = $true
        Write-Host "Backend is healthy"
        break
    } catch {
        try {
            Invoke-WebRequest -Uri "http://localhost:8000/api/health" -UseBasicParsing -TimeoutSec 3 | Out-Null
            $ok = $true
            Write-Host "Backend is healthy"
            break
        } catch {
            Start-Sleep -Seconds 2
        }
    }
}
if (-not $ok) {
    Write-Error "Timeout waiting for backend health"
}

python demo/import_demo_data.py
Write-Host "Demo ready: http://localhost  (demo_admin / Demo@2026!)"
Write-Host "Do not commit .env, kubeconfig, or SSH keys."
