$ErrorActionPreference = 'Stop'
$redroidArtifacts = Join-Path $PSScriptRoot 'artifacts'
$redroidAdb = Join-Path $redroidArtifacts 'platform-tools\adb.exe'
$redroidScrcpy = Get-ChildItem -LiteralPath (Join-Path $redroidArtifacts 'scrcpy') -Recurse -Filter scrcpy.exe | Select-Object -First 1
$redroidSerial = '127.0.0.1:15563'
$redroidProbe = [System.Net.Sockets.TcpClient]::new()
try { $redroidProbe.Connect('127.0.0.1',15563); $redroidConnected=$true }
catch { $redroidConnected=$false }
finally { $redroidProbe.Dispose() }
if (-not $redroidConnected) {
    $redroidTunnel=Join-Path $PSScriptRoot 'tunnel-runtime.py'
    Start-Process -FilePath 'C:/Users/Administrator/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -ArgumentList @('-u',('"'+$redroidTunnel+'"'),'--local-port','15563','--remote-port','5563') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $redroidArtifacts 'tunnel-15563.log') -RedirectStandardError (Join-Path $redroidArtifacts 'tunnel-15563-error.log')
    Start-Sleep -Seconds 5
}
& $redroidAdb connect $redroidSerial
if ($LASTEXITCODE -ne 0) { throw 'Account 3 ADB connection failed' }
& $redroidAdb -s $redroidSerial shell am start -n com.larus.nova/com.larus.home.impl.alias.AliasActivity1
if ($LASTEXITCODE -ne 0) { throw 'Launching Doubao account 2 failed' }
Start-Process -FilePath $redroidScrcpy.FullName -WorkingDirectory $redroidScrcpy.DirectoryName -ArgumentList @('-s',$redroidSerial,'--window-title','"Doubao - Account 3 Login"','--no-audio','--max-fps=15','--max-size=1024','--video-bit-rate=2M') -RedirectStandardOutput (Join-Path $redroidArtifacts 'scrcpy-account3.log') -RedirectStandardError (Join-Path $redroidArtifacts 'scrcpy-account3-error.log')
