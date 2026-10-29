$ErrorActionPreference = 'Stop'
$redroidArtifacts = Join-Path $PSScriptRoot 'artifacts'
$redroidAdb = Join-Path $redroidArtifacts 'platform-tools\adb.exe'
$redroidScrcpy = Get-ChildItem -LiteralPath (Join-Path $redroidArtifacts 'scrcpy') -Recurse -Filter scrcpy.exe | Select-Object -First 1
$redroidSerial = '127.0.0.1:15558'
$redroidProbe = [System.Net.Sockets.TcpClient]::new()
try { $redroidProbe.Connect('127.0.0.1',15558); $redroidConnected=$true }
catch { $redroidConnected=$false }
finally { $redroidProbe.Dispose() }
if (-not $redroidConnected) {
    $redroidTunnel=Join-Path $PSScriptRoot 'tunnel.py'
    Start-Process -FilePath (Get-Command python.exe).Source -ArgumentList @('-u',('"'+$redroidTunnel+'"'),'--local-port','15558','--remote-port','5558') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $redroidArtifacts 'tunnel-15558.log') -RedirectStandardError (Join-Path $redroidArtifacts 'tunnel-15558-error.log')
    Start-Sleep -Seconds 2
}
& $redroidAdb connect $redroidSerial
if ($LASTEXITCODE -ne 0) { throw 'Account 2 ADB connection failed' }
& $redroidAdb -s $redroidSerial shell am start -n com.larus.nova/com.larus.home.impl.alias.AliasActivity1
if ($LASTEXITCODE -ne 0) { throw 'Launching Doubao account 2 failed' }
Start-Process -FilePath $redroidScrcpy.FullName -WorkingDirectory $redroidScrcpy.DirectoryName -ArgumentList @('-s',$redroidSerial,'--window-title','"Doubao - Account 2 Login"','--no-audio','--max-fps=15','--max-size=1024','--video-bit-rate=2M') -RedirectStandardOutput (Join-Path $redroidArtifacts 'scrcpy-account2.log') -RedirectStandardError (Join-Path $redroidArtifacts 'scrcpy-account2-error.log')
