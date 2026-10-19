$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
New-Item -ItemType File -Force storage/local.stop | Out-Null
if (Test-Path storage/local.pid) {
    $runtimeId = [int](Get-Content storage/local.pid)
    for ($attempt = 0; $attempt -lt 40; $attempt++) {
        if (-not (Get-Process -Id $runtimeId -ErrorAction SilentlyContinue)) { break }
        Start-Sleep -Milliseconds 500
    }
}
Write-Host 'Parada solicitada para API, SMTP y proceso de informes. PostgreSQL conserva los datos y sigue disponible.'
