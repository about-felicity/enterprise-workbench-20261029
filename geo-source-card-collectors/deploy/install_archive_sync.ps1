param([string]$Python = 'pythonw.exe', [string]$Config = "$env:USERPROFILE/.geo-editorial/bridge.json")
$ErrorActionPreference = 'Stop'
$repository = Split-Path -Parent $PSScriptRoot
$pythonPath = (Get-Command $Python).Source
$arguments = '-B -m geo_source_cards.archive_sync --config "' + $Config + '" --interval 60'
$action = New-ScheduledTaskAction -Execute $pythonPath -Argument $arguments -WorkingDirectory $repository
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName GeoEditorialArchiveSync -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
Start-ScheduledTask -TaskName GeoEditorialArchiveSync
Write-Output 'GeoEditorialArchiveSync enabled: download only, no model dispatch.'
