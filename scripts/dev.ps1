param(
    [ValidateRange(1,65535)][int]$BackendPort = 8817,
    [ValidateRange(1,65535)][int]$WebPort = 5187
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
$vitePath = Join-Path $projectRoot 'web\node_modules\vite\bin\vite.js'
foreach ($required in @($pythonPath, $vitePath, (Join-Path $projectRoot 'backend\.env'))) {
    if (-not (Test-Path -LiteralPath $required)) { throw "Arquivo ausente: $required. Execute scripts\setup.ps1." }
}
if ($BackendPort -eq $WebPort) { throw 'As portas do backend e frontend devem ser diferentes.' }
foreach ($port in @($BackendPort, $WebPort)) {
    $listener = Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue
    if ($listener) { throw "Porta $port em uso. Ajuste -BackendPort/-WebPort; nenhum processo sera encerrado." }
}
$logDirectory = Join-Path $projectRoot 'var\dev'
New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
$runId = Get-Date -Format 'yyyyMMdd-HHmmss-ffff'
$oldProxy = $env:VITE_BACKEND_PROXY_TARGET
$oldWebPort = $env:VITE_WEB_PORT
$env:VITE_BACKEND_PROXY_TARGET = "http://127.0.0.1:$BackendPort"
$env:VITE_WEB_PORT = "$WebPort"
$children = @()
try {
    $backend = Start-Process -FilePath $pythonPath -ArgumentList @('manage.py', 'runserver', "127.0.0.1:$BackendPort", '--noreload') -WorkingDirectory (Join-Path $projectRoot 'backend') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logDirectory "$runId-backend.out.log") -RedirectStandardError (Join-Path $logDirectory "$runId-backend.err.log")
    $children += $backend
    # Caminho relativo evita problemas de aspas em diretorios com espacos.
    $frontend = Start-Process -FilePath (Get-Command node.exe).Source -ArgumentList @('node_modules/vite/bin/vite.js') -WorkingDirectory (Join-Path $projectRoot 'web') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logDirectory "$runId-web.out.log") -RedirectStandardError (Join-Path $logDirectory "$runId-web.err.log")
    $children += $frontend
    @{ backend_pid = $backend.Id; web_pid = $frontend.Id; backend_port = $BackendPort; web_port = $WebPort; started_at = (Get-Date).ToString('o') } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $logDirectory "$runId-processes.json") -Encoding UTF8
    Write-Host "Agregados IBGE: backend PID $($backend.Id), frontend PID $($frontend.Id)"
    Write-Host "Abra http://127.0.0.1:$WebPort"
    Write-Host "Logs: $logDirectory ($runId). Ctrl+C encerra os servidores desta execucao."
    while ($true) {
        foreach ($child in $children) {
            $child.Refresh()
            if ($child.HasExited) { throw "Servidor PID $($child.Id) encerrou com codigo $($child.ExitCode). Consulte os logs $runId." }
        }
        Start-Sleep -Milliseconds 500
    }
} finally {
    foreach ($child in $children) {
        $child.Refresh()
        # Processos obtidos diretamente por Start-Process; nao busca por nome/porta.
        if (-not $child.HasExited) { $child.Kill(); $child.WaitForExit() }
        $child.Dispose()
    }
    $env:VITE_BACKEND_PROXY_TARGET = $oldProxy
    $env:VITE_WEB_PORT = $oldWebPort
}
