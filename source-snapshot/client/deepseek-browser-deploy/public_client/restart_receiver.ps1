$ErrorActionPreference = "Stop"
$TaskRoot = [IO.Path]::GetFullPath((Split-Path -Parent $MyInvocation.MyCommand.Path))
$ReceiverScript = [IO.Path]::GetFullPath((Join-Path $TaskRoot "local_receiver.py"))
$DefaultSync = Join-Path $TaskRoot "config\deepseek_sync.json"
if (-not $env:DEEPSEEK_REMOTE_SYNC_CONFIG -and (Test-Path -LiteralPath $DefaultSync)) {
    $env:DEEPSEEK_REMOTE_SYNC_CONFIG = $DefaultSync
}
$Connection = Get-NetTCPConnection -LocalPort 8767 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($Connection) {
    $ProcessInfo = Get-CimInstance Win32_Process -Filter "ProcessId=$($Connection.OwningProcess)"
    $CommandLine = [string]$ProcessInfo.CommandLine
    if ($ProcessInfo.Name -notmatch "^python" -or $CommandLine.IndexOf($ReceiverScript, [StringComparison]::OrdinalIgnoreCase) -lt 0) {
        throw "Port 8767 is occupied by another process; refusing to stop it."
    }
    Stop-Process -Id $Connection.OwningProcess -Force
    Start-Sleep -Milliseconds 500
}
& (Join-Path $TaskRoot 'start_monitor.ps1')
