param([string]$TaskName = 'ReFab-EnvioMensual')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
$hour = & $python -c 'from lab_hub.config import get_settings; print(get_settings().REPORT_SEND_HOUR)'
if ($LASTEXITCODE -ne 0) { throw 'Configuracion invalida.' }
$runner = Join-Path $PSScriptRoot 'ejecutar_envio_mensual.ps1'
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -NonInteractive -WindowStyle Hidden -File `"$runner`"" -WorkingDirectory $projectRoot
$trigger = New-ScheduledTaskTrigger -Daily -At ([datetime]::Today.AddHours([int]$hour))
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$principal = New-ScheduledTaskPrincipal -UserId $identity -LogonType S4U -RunLevel Limited
# S4U uses local resources without storing a Windows password. SMTP uses configured credentials.
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description 'Archivo y envio mensual ReFab, con recuperacion al encender.' | Out-Null
Write-Host "Tarea instalada: $TaskName"
