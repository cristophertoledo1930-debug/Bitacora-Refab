# Contract test: mock every Windows task mutation; never register a real task.
$ErrorActionPreference = 'Stop'
$global:monthlyTaskTestState = @{ Registered = $false; Unregistered = $false }
function New-ScheduledTaskAction {
    param($Execute, $Argument, $WorkingDirectory)
    if ($Execute -ne 'powershell.exe' -or $Argument -notmatch 'ejecutar_envio_mensual.ps1' -or $Argument -notmatch 'Hidden') { throw 'Invalid action' }
    return @{ Execute = $Execute; Argument = $Argument }
}
function New-ScheduledTaskTrigger {
    param([switch]$Daily, $At)
    if (-not $Daily -or -not $At) { throw 'Daily trigger required' }
    return @{ Daily = $true }
}
function New-ScheduledTaskSettingsSet {
    param([switch]$StartWhenAvailable, $MultipleInstances, [switch]$AllowStartIfOnBatteries, [switch]$DontStopIfGoingOnBatteries)
    if (-not $StartWhenAvailable -or $MultipleInstances -ne 'IgnoreNew') { throw 'Recovery and exclusion required' }
    return @{ StartWhenAvailable = $true }
}
function New-ScheduledTaskPrincipal {
    param($UserId, $LogonType, $RunLevel)
    if ($LogonType -ne 'S4U' -or $RunLevel -ne 'Limited') { throw 'Invalid principal' }
    return @{ UserId = $UserId }
}
function Register-ScheduledTask {
    param($TaskName, $Action, $Trigger, $Settings, $Principal, $Description)
    if ($TaskName -ne 'Synthetic-Monthly-Test' -or -not $Settings.StartWhenAvailable) { throw 'Invalid task' }
    $global:monthlyTaskTestState.Registered = $true
}
function Unregister-ScheduledTask {
    param($TaskName, $Confirm)
    if ($TaskName -ne 'Synthetic-Monthly-Test') { throw 'Invalid removal' }
    $global:monthlyTaskTestState.Unregistered = $true
}
& (Join-Path $PSScriptRoot '../scripts/instalar_tarea_mensual.ps1') -TaskName 'Synthetic-Monthly-Test'
& (Join-Path $PSScriptRoot '../scripts/desinstalar_tarea_mensual.ps1') -TaskName 'Synthetic-Monthly-Test'
if (-not $global:monthlyTaskTestState.Registered -or -not $global:monthlyTaskTestState.Unregistered) { throw 'Mocks were not called' }
Remove-Variable -Name monthlyTaskTestState -Scope Global
Write-Output 'M7: contrato de instalacion/desinstalacion correcto; solo dobles, cero tareas reales.'
