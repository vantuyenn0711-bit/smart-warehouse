param([int]$Port = 8010)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$projectPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
if ($Port -lt 1024 -or $Port -gt 65535) { throw 'Choose a port from 1024 to 65535.' }
if (-not (Test-Path -LiteralPath $projectPython)) { throw 'Create .venv first using uv sync --python 3.13; see README.md.' }
if (-not (Test-Path -LiteralPath (Join-Path $projectRoot '.env'))) { throw 'Run scripts/init_env.py first; see README.md.' }
$portProbe = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $Port)
$portProbe.Server.ExclusiveAddressUse = $true
try { $portProbe.Start() } catch { throw "Port $Port is already in use. Stop your Warehouse server first or choose -Port with a free port." } finally { $portProbe.Stop() }
Push-Location -LiteralPath $projectRoot
try {
    if (Test-Path -LiteralPath '.runtime\pgsql\bin\pg_ctl.exe') {
        & $projectPython scripts/local_postgres.py start
        if ($LASTEXITCODE -ne 0) { throw 'Local PostgreSQL could not start. See .runtime/postgres.log.' }
    }
    & $projectPython manage.py check
    if ($LASTEXITCODE -ne 0) { throw 'Django checks failed; review the messages above.' }
    Write-Host "Smart Warehouse local: http://127.0.0.1:$Port/ (Ctrl+C to stop)"
    & $projectPython manage.py runserver "127.0.0.1:$Port" --noreload
    if ($LASTEXITCODE -ne 0) { throw 'The development server could not start.' }
} finally {
    Pop-Location
}
