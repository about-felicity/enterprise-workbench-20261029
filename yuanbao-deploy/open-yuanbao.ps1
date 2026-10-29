$ErrorActionPreference = 'Stop'
$yuanbaoWorkspace = Split-Path -Parent $PSScriptRoot
$yuanbaoTools = Join-Path $yuanbaoWorkspace 'redroid-deploy'
$yuanbaoArtifacts = Join-Path $PSScriptRoot 'artifacts'
$yuanbaoAdb = Join-Path $yuanbaoTools 'artifacts\platform-tools\adb.exe'
$yuanbaoScrcpy = Get-ChildItem -LiteralPath (Join-Path $yuanbaoTools 'artifacts\scrcpy') -Recurse -Filter scrcpy.exe | Select-Object -First 1
$yuanbaoSerial = '127.0.0.1:15559'
if (-not (Test-Path -LiteralPath $yuanbaoAdb) -or -not $yuanbaoScrcpy) { throw 'ADB or scrcpy missing.' }
New-Item -ItemType Directory -Path $yuanbaoArtifacts -Force | Out-Null
$yuanbaoProbe = [System.Net.Sockets.TcpClient]::new()
try { $yuanbaoProbe.Connect('127.0.0.1',15559); $yuanbaoConnected=$true }
catch { $yuanbaoConnected=$false }
finally { $yuanbaoProbe.Dispose() }
if (-not $yuanbaoConnected) {
    $yuanbaoTunnel=Join-Path $yuanbaoTools 'tunnel.py'
    Start-Process -FilePath (Get-Command python.exe).Source -ArgumentList @('-B','-u',('"'+$yuanbaoTunnel+'"'),'--local-port','15559','--remote-port','5559') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $yuanbaoArtifacts 'tunnel.log') -RedirectStandardError (Join-Path $yuanbaoArtifacts 'tunnel-error.log')
    Start-Sleep -Seconds 2
}
& $yuanbaoAdb connect $yuanbaoSerial
if ($LASTEXITCODE -ne 0) { throw 'Yuanbao ADB connection failed.' }
$yuanbaoReady = $false
for ($yuanbaoAttempt=0; $yuanbaoAttempt -lt 15; $yuanbaoAttempt++) {
    $yuanbaoBoot = & $yuanbaoAdb -s $yuanbaoSerial shell getprop sys.boot_completed 2>$null
    if ($LASTEXITCODE -eq 0 -and "$yuanbaoBoot".Trim() -eq '1') { $yuanbaoReady=$true; break }
    & $yuanbaoAdb disconnect $yuanbaoSerial | Out-Null
    & $yuanbaoAdb connect $yuanbaoSerial | Out-Null
    Start-Sleep -Seconds 2
}
if (-not $yuanbaoReady) { throw 'Yuanbao Android has not finished booting. Existing devices were not changed.' }
$yuanbaoActivity = & $yuanbaoAdb -s $yuanbaoSerial shell cmd package resolve-activity --brief com.tencent.hunyuan.app.chat | Select-Object -Last 1
if (-not $yuanbaoActivity) { throw 'Yuanbao launcher did not resolve.' }
$yuanbaoActivity = $yuanbaoActivity.Trim()
if (-not $yuanbaoActivity.StartsWith('com.tencent.hunyuan.app.chat/')) { throw 'Yuanbao launcher missing.' }
& $yuanbaoAdb -s $yuanbaoSerial shell am start -W -n $yuanbaoActivity
if ($LASTEXITCODE -ne 0) { throw 'Yuanbao launch failed.' }
# Visible projection explicitly requested for the user's login.
$yuanbaoProjection = Start-Process -FilePath $yuanbaoScrcpy.FullName -WorkingDirectory $yuanbaoScrcpy.DirectoryName -ArgumentList @('-s',$yuanbaoSerial,'--window-title','"Yuanbao - Login"','--no-audio','--max-fps=15','--max-size=1024','--video-bit-rate=2M') -RedirectStandardOutput (Join-Path $yuanbaoArtifacts 'scrcpy.log') -RedirectStandardError (Join-Path $yuanbaoArtifacts 'scrcpy-error.log') -PassThru
$yuanbaoProjection.Id | Set-Content -LiteralPath (Join-Path $yuanbaoArtifacts 'scrcpy.pid')
