param()
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Falta .venv. Instale las dependencias primero.' }
New-Item -ItemType Directory -Force storage/logs | Out-Null
# Only the local PostgreSQL installation managed by this project may be started.
$databaseInfo = & $python -c 'from sqlalchemy.engine import make_url; from lab_hub.config import get_settings; u=make_url(get_settings().DATABASE_URL); print(u.host or "localhost"); print(u.port or 5432)'
if ($LASTEXITCODE -ne 0) { throw 'Configuracion de base de datos invalida.' }
if ($databaseInfo[0] -in @('localhost', '127.0.0.1', '::1')) {
    $pgBin = Join-Path $projectRoot '.tools\pgsql\bin'
    if (-not (Test-Path (Join-Path $pgBin 'pg_ctl.exe'))) {
        $pgBin = Join-Path $env:ProgramFiles 'PostgreSQL\16\bin'
    }
    $pgCtl = Join-Path $pgBin 'pg_ctl.exe'
    if (-not (Test-Path -LiteralPath $pgCtl)) { throw 'No se encuentra PostgreSQL 16 local.' }
    & $pgCtl -D pgdata status | Out-Null
    if ($LASTEXITCODE -ne 0) {
        & $pgCtl -D pgdata -l storage/logs/postgres-monthly.log -o "-h 127.0.0.1 -p $($databaseInfo[1])" -w start
        if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL no pudo iniciar.' }
    }
}
$job = Start-Process -FilePath $python -ArgumentList '-m lab_hub.jobs.monthly_report' -WorkingDirectory $projectRoot -WindowStyle Hidden -Wait -PassThru -RedirectStandardOutput storage/logs/monthly.log -RedirectStandardError storage/logs/monthly-error.log
exit $job.ExitCode
