$ErrorActionPreference = 'Stop'
$deepseekWorkspace = Split-Path -Parent $PSScriptRoot
$deepseekTools = Join-Path $deepseekWorkspace 'redroid-deploy'
$deepseekArtifacts = Join-Path $PSScriptRoot 'artifacts'
$deepseekAdb = Join-Path $deepseekTools 'artifacts\platform-tools\adb.exe'
$deepseekScrcpy = Get-ChildItem -LiteralPath (Join-Path $deepseekTools 'artifacts\scrcpy') -Recurse -Filter scrcpy.exe | Select-Object -First 1
$deepseekSerial = '127.0.0.1:15560'
if (-not (Test-Path -LiteralPath $deepseekAdb) -or -not $deepseekScrcpy) { throw 'ADB or scrcpy missing.' }
New-Item -ItemType Directory -Path $deepseekArtifacts -Force | Out-Null
$deepseekProbe = [System.Net.Sockets.TcpClient]::new()
try { $deepseekProbe.Connect('127.0.0.1',15560); $deepseekConnected=$true }
catch { $deepseekConnected=$false }
finally { $deepseekProbe.Dispose() }
if (-not $deepseekConnected) {
    $deepseekTunnel=Join-Path $deepseekTools 'tunnel.py'
    Start-Process -FilePath (Get-Command python.exe).Source -ArgumentList @('-B','-u',('"'+$deepseekTunnel+'"'),'--local-port','15560','--remote-port','5560') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $deepseekArtifacts 'tunnel.log') -RedirectStandardError (Join-Path $deepseekArtifacts 'tunnel-error.log')
    Start-Sleep -Seconds 2
}
& $deepseekAdb connect $deepseekSerial
if ($LASTEXITCODE -ne 0) { throw 'DeepSeek ADB connection failed.' }
$deepseekReady = $false
for ($deepseekAttempt=0; $deepseekAttempt -lt 15; $deepseekAttempt++) {
    $deepseekBoot = & $deepseekAdb -s $deepseekSerial shell getprop sys.boot_completed 2>$null
    if ($LASTEXITCODE -eq 0 -and "$deepseekBoot".Trim() -eq '1') { $deepseekReady=$true; break }
    & $deepseekAdb disconnect $deepseekSerial | Out-Null
    & $deepseekAdb connect $deepseekSerial | Out-Null
    Start-Sleep -Seconds 2
}
if (-not $deepseekReady) { throw 'DeepSeek Android has not finished booting. Existing devices were not changed.' }
$deepseekActivity = & $deepseekAdb -s $deepseekSerial shell cmd package resolve-activity --brief com.deepseek.chat | Select-Object -Last 1
if (-not $deepseekActivity) { throw 'DeepSeek launcher did not resolve.' }
$deepseekActivity = $deepseekActivity.Trim()
if (-not $deepseekActivity.StartsWith('com.deepseek.chat/')) { throw 'DeepSeek launcher missing.' }
& $deepseekAdb -s $deepseekSerial shell cmd locale set-app-locales com.deepseek.chat --user 0 --locales zh-CN
& $deepseekAdb -s $deepseekSerial shell am start -W -n $deepseekActivity
if ($LASTEXITCODE -ne 0) { throw 'DeepSeek launch failed.' }
# Visible projection explicitly requested for the user's login.
$deepseekProjection = Start-Process -FilePath $deepseekScrcpy.FullName -WorkingDirectory $deepseekScrcpy.DirectoryName -ArgumentList @('-s',$deepseekSerial,'--window-title','"DeepSeek - Login"','--no-audio','--max-fps=15','--max-size=1024','--video-bit-rate=2M') -RedirectStandardOutput (Join-Path $deepseekArtifacts 'scrcpy.log') -RedirectStandardError (Join-Path $deepseekArtifacts 'scrcpy-error.log') -PassThru
$deepseekProjection.Id | Set-Content -LiteralPath (Join-Path $deepseekArtifacts 'scrcpy.pid')
