param([string]$TaskName = 'ReFab-EnvioMensual')
$ErrorActionPreference = 'Stop'
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
Write-Host "Tarea eliminada: $TaskName"
