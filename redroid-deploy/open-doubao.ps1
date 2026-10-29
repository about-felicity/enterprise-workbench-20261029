param([switch]$Legacy)
$ErrorActionPreference = 'Stop'
$redroidLocalPort = if ($Legacy) { 15555 } else { 15557 }
$redroidRemotePort = if ($Legacy) { 5555 } else { 5557 }
$redroidSerial = "127.0.0.1:$redroidLocalPort"
$redroidArtifacts = Join-Path $PSScriptRoot 'artifacts'
$redroidAdb = Join-Path $redroidArtifacts 'platform-tools\adb.exe'
$redroidScrcpy = Get-ChildItem -LiteralPath (Join-Path $redroidArtifacts 'scrcpy') -Recurse -Filter scrcpy.exe | Select-Object -First 1
if (-not (Test-Path -LiteralPath $redroidAdb) -or -not $redroidScrcpy) {
    throw 'ADB or scrcpy is missing from artifacts.'
}
$redroidProbe = [System.Net.Sockets.TcpClient]::new()
try {
    $redroidProbe.Connect('127.0.0.1', $redroidLocalPort)
    $redroidTunnelExists = $true
} catch {
    $redroidTunnelExists = $false
} finally {
    $redroidProbe.Dispose()
}
if (-not $redroidTunnelExists) {
    $redroidPython = (Get-Command python.exe).Source
    $redroidTunnel = Join-Path $PSScriptRoot 'tunnel.py'
    $redroidProcess = Start-Process -FilePath $redroidPython -ArgumentList @('-u', ('"' + $redroidTunnel + '"'), '--local-port', $redroidLocalPort, '--remote-port', $redroidRemotePort) -WindowStyle Hidden -RedirectStandardOutput (Join-Path $redroidArtifacts "tunnel-$redroidLocalPort.log") -RedirectStandardError (Join-Path $redroidArtifacts "tunnel-$redroidLocalPort-error.log") -PassThru
    $redroidProcess.Id | Set-Content -LiteralPath (Join-Path $redroidArtifacts 'tunnel.pid')
    Start-Sleep -Seconds 2
}
& $redroidAdb connect $redroidSerial
if ($LASTEXITCODE -ne 0) { throw 'ADB connection failed.' }
& $redroidAdb -s $redroidSerial shell am start -n com.larus.nova/com.larus.home.impl.alias.AliasActivity1
if ($LASTEXITCODE -ne 0) { throw 'Launching Doubao failed.' }
# This window is visible because the script is explicitly used to view and log in to Doubao.
Start-Process -FilePath $redroidScrcpy.FullName -WorkingDirectory $redroidScrcpy.DirectoryName -ArgumentList @('-s', $redroidSerial, '--window-title', '"Doubao - Redroid"', '--no-audio', '--max-fps=15', '--max-size=1024', '--video-bit-rate=2M') -RedirectStandardOutput (Join-Path $redroidArtifacts 'scrcpy.log') -RedirectStandardError (Join-Path $redroidArtifacts 'scrcpy-error.log')
