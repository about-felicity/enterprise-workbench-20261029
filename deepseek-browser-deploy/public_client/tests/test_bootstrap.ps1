$ErrorActionPreference = 'Stop'
$SourceRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
foreach ($Name in @('ensure_python.ps1','start_monitor.ps1','restart_receiver.ps1')) {
    $ErrorsFound = $null
    [System.Management.Automation.Language.Parser]::ParseFile((Join-Path $SourceRoot $Name), [ref]$null, [ref]$ErrorsFound) | Out-Null
    if ($ErrorsFound) { throw $ErrorsFound }
}
. (Join-Path $SourceRoot 'ensure_python.ps1')
$Existing = Find-CollectorPython (Join-Path $env:LOCALAPPDATA 'DeepSeekCollector\Python313')
if (-not $Existing -or -not (Test-CollectorPython $Existing)) { throw 'This QA host needs an existing Python; no real installation is performed by this test.' }
Write-Output 'Existing installed Python discovery: PASS'

# Stub network and installer boundaries; never install or launch a downloaded program in QA.
$OriginalLocal = $env:LOCALAPPDATA
$OriginalArch = $env:PROCESSOR_ARCHITECTURE
$OriginalArch64 = $env:PROCESSOR_ARCHITEW6432
$TestRoot = Join-Path $env:TEMP ('deepseek-bootstrap-qa-'+[guid]::NewGuid().ToString('N'))
$env:LOCALAPPDATA = $TestRoot
$env:PROCESSOR_ARCHITECTURE = 'AMD64'
$env:PROCESSOR_ARCHITEW6432 = ''
$script:SignatureValid = $false
$script:InstallerCalled = $false
$script:Installed = $false
function Find-CollectorPython { return $null }
function Test-CollectorPython { return $script:Installed }
function Invoke-WebRequest {
    param([switch]$UseBasicParsing,[string]$Uri,[string]$OutFile,[int]$TimeoutSec)
    if ($Uri -ne 'https://www.python.org/ftp/python/3.13.16/python-3.13.16-amd64.exe') { throw 'Unexpected installer source' }
    [IO.File]::WriteAllText($OutFile, 'non executable QA placeholder')
}
function Get-AuthenticodeSignature {
    param([string]$LiteralPath)
    return [pscustomobject]@{Status=$(if($script:SignatureValid){'Valid'}else{'HashMismatch'});SignerCertificate=[pscustomobject]@{Subject='CN=Python Software Foundation, O=Python Software Foundation'}}
}
function Start-Process {
    param([string]$FilePath,[string[]]$ArgumentList,[string]$WindowStyle,[switch]$Wait,[switch]$PassThru)
    if ('InstallAllUsers=0' -notin $ArgumentList -or 'PrependPath=0' -notin $ArgumentList -or 'Include_launcher=0' -notin $ArgumentList) { throw 'Installer scope changed' }
    if ($WindowStyle -ne 'Hidden' -or -not $Wait -or -not $PassThru) { throw 'Installer lifecycle changed' }
    $script:InstallerCalled = $true
    $script:Installed = $true
    return [pscustomobject]@{ExitCode=0}
}
try {
    $Rejected = $false
    try { Get-CollectorPython | Out-Null } catch { $Rejected = $true }
    if (-not $Rejected -or $script:InstallerCalled) { throw 'Invalid signature was not blocked before execution' }
    Write-Output 'Invalid installer signature blocks execution: PASS'
    $script:SignatureValid = $true
    $Result = Get-CollectorPython
    if (-not $script:InstallerCalled -or $Result -ne (Join-Path $TestRoot 'DeepSeekCollector\Python313\python.exe')) { throw 'First-run install did not return its exact interpreter' }
    Write-Output 'Missing Python -> per-user install -> exact interpreter: PASS (mocked installer)'
} finally {
    $env:LOCALAPPDATA = $OriginalLocal
    $env:PROCESSOR_ARCHITECTURE = $OriginalArch
    $env:PROCESSOR_ARCHITEW6432 = $OriginalArch64
    # Only this test's newly created, fully resolved directory may be removed.
    $Resolved = [IO.Path]::GetFullPath($TestRoot)
    $TempBase = [IO.Path]::GetFullPath($env:TEMP).TrimEnd('\')+'\'
    if ($Resolved.StartsWith($TempBase,[StringComparison]::OrdinalIgnoreCase) -and [IO.Path]::GetFileName($Resolved).StartsWith('deepseek-bootstrap-qa-')) {
        Remove-Item -LiteralPath $Resolved -Recurse -Force -ErrorAction SilentlyContinue
    }
}
