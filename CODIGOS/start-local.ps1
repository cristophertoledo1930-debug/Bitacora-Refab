param([switch]$NoBrowser, [int]$Port = 8071)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
New-Item -ItemType Directory -Force storage/logs | Out-Null
while ($Port -le 8090) {
    $listener = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue
    if (-not $listener) { break }
    try {
        $live = Invoke-RestMethod "http://127.0.0.1:$Port/health/live" -TimeoutSec 2
        if ($live.service -eq 'qr-lab-hub') { break }
    } catch {}
    Write-Host "Puerto $Port ocupado por otra aplicacion; probando el siguiente."
    $Port++
}
if ($Port -gt 8090) { throw 'No hay puerto libre entre el solicitado y 8090.' }
$baseUrl = "http://127.0.0.1:$Port"
$env:APP_BASE_URL = "http://localhost:$Port"
$Port | Set-Content storage/local.port
& $python -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Revise las dependencias de .venv.' }
& ./.tools/pgsql/bin/pg_ctl.exe -D pgdata status | Out-Null
if ($LASTEXITCODE -ne 0) {
    & ./.tools/pgsql/bin/pg_ctl.exe -D pgdata -l storage/logs/postgres.log -o '-h 127.0.0.1' -w start
    if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL no pudo iniciar.' }
}
& $python -m alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw 'Fallaron las migraciones.' }
& $python -c 'from lab_hub.db.session import SessionLocal; from lab_hub.services.seeds import seed_catalogs; db=SessionLocal(); seed_catalogs(db); db.close()'
if ($LASTEXITCODE -ne 0) { throw 'Fallaron los catálogos.' }
try { $ready = Invoke-RestMethod "$baseUrl/health/ready" -TimeoutSec 2 } catch { $ready = $null }
if (-not $ready -or $ready.status -ne 'ready') {
    $process = Start-Process -FilePath $python -ArgumentList "-m lab_hub.local_runtime --port $Port" -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -RedirectStandardOutput storage/logs/app.log -RedirectStandardError storage/logs/app-error.log -PassThru
    $ready = $null
    for ($attempt = 0; $attempt -lt 40; $attempt++) {
        Start-Sleep -Milliseconds 500
        try { $ready = Invoke-RestMethod "$baseUrl/health/ready" -TimeoutSec 2; break } catch {}
        if ($process.HasExited) { throw 'El proceso terminó. Revise storage/logs/app-error.log.' }
    }
    if (-not $ready -or $ready.status -ne 'ready') { throw 'El servidor no respondió a tiempo.' }
    $process.Id | Set-Content storage/local.pid
}
Write-Host "QR Lab Hub: http://localhost:$Port/dashboard/"
if (-not $NoBrowser) { Start-Process "http://localhost:$Port/dashboard/" }
