# Enterprise AI SRE Platform v3.2.1 — local demo starter
# Forces ENABLE_MCP=true for this process tree so a system-level
# ENABLE_MCP=false cannot hide the .env value.

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$env:ENABLE_MCP = "true"

$mcpCwd = ""
$envFile = Join-Path $Root ".env"
if (Test-Path $envFile) {
    Get-Content -Path $envFile -Encoding UTF8 | ForEach-Object {
        if ($_ -match '^\s*MCP_SERVER_CWD\s*=\s*(.*)$') {
            $mcpCwd = $Matches[1].Trim().Trim('"').Trim("'")
        }
    }
}

Write-Host "================================"
Write-Host "Enterprise AI SRE Platform v3.2.1"
Write-Host "MCP Enabled: true"
Write-Host "================================"

if (-not $mcpCwd) {
    Write-Host "[WARN] MCP_SERVER_CWD is empty in .env. Backend will start; MCP tools may be unavailable." -ForegroundColor Yellow
} elseif (-not (Test-Path -LiteralPath $mcpCwd)) {
    Write-Host "[WARN] MCP Server path does not exist: $mcpCwd" -ForegroundColor Yellow
    Write-Host "[WARN] Backend will still start. Set MCP_SERVER_CWD to Project 2 root." -ForegroundColor Yellow
} else {
    Write-Host "[OK] MCP Server path exists."
}

python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
