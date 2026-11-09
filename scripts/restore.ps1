param(
    [Parameter(Mandatory = $true)][string]$InputFile,
    [switch]$ConfirmRestore,
    [string]$PgBin = "",
    [string]$Drive = "W:"
)
$ErrorActionPreference = "Stop"
if (-not $ConfirmRestore) {
    throw 'Restore is an explicit operation. Select an EMPTY local target in DATABASE_URL, then pass -ConfirmRestore.'
}
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
$helperPath = Join-Path $PSScriptRoot 'db_maintenance.py'
$arguments = @($helperPath, 'restore', '--file', $InputFile, '--confirm-restore', '--drive', $Drive)
if ($PgBin) { $arguments += @('--pg-bin', $PgBin) }
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'Run uv sync first to create the project virtual environment.'
}
& $pythonPath @arguments
if ($LASTEXITCODE -ne 0) { throw "Restore failed with exit code $LASTEXITCODE." }
