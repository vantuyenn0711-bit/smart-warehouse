param(
    [Parameter(Mandatory = $true)][string]$OutputFile,
    [string]$PgBin = "",
    [string]$Drive = "W:"
)
$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
$helperPath = Join-Path $PSScriptRoot 'db_maintenance.py'
$arguments = @($helperPath, 'backup', '--file', $OutputFile, '--drive', $Drive)
if ($PgBin) { $arguments += @('--pg-bin', $PgBin) }
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'Run uv sync first to create the project virtual environment.'
}
& $pythonPath @arguments
if ($LASTEXITCODE -ne 0) { throw "Backup failed with exit code $LASTEXITCODE." }
