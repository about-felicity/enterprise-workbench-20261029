param([switch]$CheckPackage)
$ErrorActionPreference = "Stop"
$TaskRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
foreach ($Required in @('ensure_python.ps1','enrollment.py','local_receiver.py','remote_sync.py','extension\manifest.json','config\public_upload.json')) {
    if (-not (Test-Path -LiteralPath (Join-Path $TaskRoot $Required) -PathType Leaf)) { throw ('安装包缺少文件：'+$Required+'。请先完整解压整个ZIP，不要只复制启动文件。') }
}
if ($CheckPackage) { Write-Output 'Package files OK; PowerShell entry found under current path.'; exit 0 }
$DefaultSync = Join-Path $TaskRoot "config\deepseek_sync.json"
$env:DEEPSEEK_REMOTE_SYNC_CONFIG = $DefaultSync
$env:DEEPSEEK_REMOTE_DEVICE = "deepseek-browser-extension"
$env:DEEPSEEK_MONITOR_DATA_DIR = Join-Path $TaskRoot "data"
$global:DS_START_STAGE = 'Loading Python setup script'
$global:DS_START_TARGET = Join-Path $TaskRoot 'ensure_python.ps1'
. $global:DS_START_TARGET
$PythonPath = Get-CollectorPython
Write-Host 'Python 环境已就绪，正在启动采集接收器……'
$global:DS_START_STAGE = 'Device configuration initialization'
$global:DS_START_TARGET = $PythonPath
Write-Host '[3/4] Preparing device configuration...'
& $PythonPath -B (Join-Path $TaskRoot "enrollment.py")
if ($LASTEXITCODE -ne 0) { throw '设备配置初始化失败，请检查 config 文件夹后重试。' }
$ReceiverUrl = "http://127.0.0.1:8767/api/health"
$ReceiverReady = $false
try {
    $Health = Invoke-RestMethod -Uri $ReceiverUrl -TimeoutSec 2
    $ReceiverReady = [bool]$Health.ok
} catch {}

if (-not $ReceiverReady) {
    $global:DS_START_STAGE = 'Local receiver process launch'
    $global:DS_START_TARGET = $PythonPath
    Write-Host '[4/4] Starting local receiver...'
    $LogDir = Join-Path $TaskRoot "data"
    New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
    $EmptyInput = Join-Path $LogDir 'receiver_input.txt'
    [IO.File]::WriteAllText($EmptyInput, '')
    Start-Process -FilePath $PythonPath -ArgumentList @("-X", "utf8", ('"'+(Join-Path $TaskRoot "local_receiver.py")+'"')) -WorkingDirectory $TaskRoot -WindowStyle Hidden -RedirectStandardInput $EmptyInput -RedirectStandardOutput (Join-Path $LogDir "receiver.log") -RedirectStandardError (Join-Path $LogDir "receiver_error.log")
    $Deadline = (Get-Date).AddSeconds(12)
    do {
        Start-Sleep -Milliseconds 400
        try {
            $Health = Invoke-RestMethod -Uri $ReceiverUrl -TimeoutSec 2
            $ReceiverReady = [bool]$Health.ok
        } catch {}
    } while (-not $ReceiverReady -and (Get-Date) -lt $Deadline)
    if (-not $ReceiverReady) { throw "Local receiver failed to start. Check data\receiver_error.log." }
}

Write-Output "DeepSeek local receiver is ready at http://127.0.0.1:8767"
Write-Host '准备完成！在 Chrome 打开 chrome://extensions，开启开发者模式，加载下面的 extension 文件夹：'
Write-Host (Join-Path $TaskRoot 'extension')
Write-Host '装好插件后，打开并登录 chat.deepseek.com，在插件中点击开始。以后运行本脚本即可，无需重复安装。'
