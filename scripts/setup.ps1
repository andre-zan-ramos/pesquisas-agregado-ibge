param([switch]$WithTests)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    & python -m venv (Join-Path $projectRoot '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao criar ambiente Python.' }
}
$requirementsPath = if ($WithTests) { 'backend\requirements-dev.txt' } else { 'backend\requirements.txt' }
& $pythonPath -m pip install -r (Join-Path $projectRoot $requirementsPath)
if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar dependencias Python.' }
Push-Location (Join-Path $projectRoot 'web')
try {
    & npm.cmd ci
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar dependencias Node.' }
} finally { Pop-Location }
& $pythonPath (Join-Path $PSScriptRoot 'init_env.py')
if ($LASTEXITCODE -ne 0) { throw 'Falha ao configurar ambientes.' }
Write-Host 'Preparado. Execute .\servers.bat para iniciar.'
