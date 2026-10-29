$ErrorActionPreference='Stop'
. (Join-Path (Split-Path -Parent $PSScriptRoot) 'ensure_python.ps1')
function Test-Path { param($LiteralPath,$PathType,$ErrorAction);throw [UnauthorizedAccessException]::new('Access to the path is denied.') }
if (Test-CollectorPython 'C:\restricted\python.exe') { throw 'Denied candidate accepted' }
Remove-Item Function:\Test-Path
Write-Output 'Denied executable path is skipped: PASS'

function Get-Command { param($Name,$ErrorAction);throw [UnauthorizedAccessException]::new('Application alias access denied') }
function Get-ChildItem { param($LiteralPath,$ErrorAction);throw [UnauthorizedAccessException]::new('Registry enumeration denied') }
if (Find-CollectorPython 'C:\nonexistent-collector-python') {throw 'Unexpected candidate'}
Remove-Item Function:\Get-ChildItem
Write-Output 'Denied command lookup and registry hive are skipped: PASS'

function Get-ChildItem { param($LiteralPath,$ErrorAction);return [pscustomobject]@{PSPath='HKCU:\blocked'} }
function Get-Item {
 param($LiteralPath,$ErrorAction)
 $Value=[pscustomobject]@{}
 $Value | Add-Member -MemberType ScriptMethod -Name GetValue -Value {throw [UnauthorizedAccessException]::new('Registry value access denied')}
 return $Value
}
if (Find-CollectorPython 'C:\nonexistent-collector-python') {throw 'Unexpected candidate'}
Write-Output 'Denied registry installation value is skipped: PASS'
