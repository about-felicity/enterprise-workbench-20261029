# Python's official per-user installer; no administrator privileges or PATH changes.
function Test-CollectorPython([string]$Candidate) {
    try {
        if (-not $Candidate -or $Candidate -like '*WindowsApps*' -or -not (Test-Path -LiteralPath $Candidate -PathType Leaf -ErrorAction Stop)) { return $false }
        $Result = & $Candidate -I -S -c "import sys,ssl,json,http.server,urllib.request; print('collector-python-ok' if (3,10)<=sys.version_info[:2]<(4,0) else 'unsupported')" 2>$null
        return ($LASTEXITCODE -eq 0 -and $Result -eq 'collector-python-ok')
    } catch { return $false }
}

function Find-CollectorPython([string]$Target) {
    $Candidates = @((Join-Path $Target 'python.exe'))
    foreach ($Name in @('python', 'python3')) {
        try {
            $Command = Get-Command $Name -ErrorAction Stop
            if ($Command) { $Candidates += $Command.Source }
        } catch { continue }
    }
    foreach ($Candidate in ($Candidates | Select-Object -Unique)) {
        if (Test-CollectorPython $Candidate) { return $Candidate }
    }
    foreach ($Hive in @('HKCU:\Software\Python\PythonCore', 'HKLM:\Software\Python\PythonCore', 'HKLM:\Software\WOW6432Node\Python\PythonCore')) {
        try { $Keys = @(Get-ChildItem -LiteralPath $Hive -ErrorAction Stop) } catch { continue }
        foreach ($Key in $Keys) {
            try {
                $Install = Get-Item -LiteralPath ($Key.PSPath+'\InstallPath') -ErrorAction Stop
                if (-not $Install) { continue }
                $Executable = [string]$Install.GetValue('ExecutablePath')
                if (-not $Executable -and $Install.GetValue('')) { $Executable = Join-Path ([string]$Install.GetValue('')) 'python.exe' }
                if ($Executable -and (Test-CollectorPython $Executable)) { return $Executable }
            } catch { continue }
        }
    }
    return $null
}

function Get-CollectorPython {
    $global:DS_START_STAGE = 'Python environment discovery'
    Write-Host '[2/4] Checking Python environment...'
    $Target = Join-Path $env:LOCALAPPDATA 'DeepSeekCollector\Python313'
    $Existing = Find-CollectorPython $Target
    if ($Existing) { return $Existing }
    Write-Host '未检测到可用的 Python，正在下载并安装官方 Python（首次需要联网）……'
    $Version = '3.13.16'
    $Arch = if ($env:PROCESSOR_ARCHITEW6432) { $env:PROCESSOR_ARCHITEW6432 } else { $env:PROCESSOR_ARCHITECTURE }
    $Suffix = switch ($Arch.ToUpperInvariant()) { 'AMD64' {'-amd64'} 'ARM64' {'-arm64'} 'X86' {''} default {throw '不支持的 Windows 处理器架构。'} }
    $Cache = Join-Path $env:LOCALAPPDATA 'DeepSeekCollector\installers'
    $global:DS_START_STAGE = 'Python installer download'
    $global:DS_START_TARGET = $Cache
    New-Item -ItemType Directory -Path $Cache -Force | Out-Null
    $Installer = Join-Path $Cache ('python-'+$Version+$Suffix+'.exe')
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -UseBasicParsing -Uri ('https://www.python.org/ftp/python/'+$Version+'/python-'+$Version+$Suffix+'.exe') -OutFile $Installer -TimeoutSec 180
    $Signature = Get-AuthenticodeSignature -LiteralPath $Installer
    if ($Signature.Status -ne 'Valid' -or $Signature.SignerCertificate.Subject -notmatch '(^|,\s*)CN=Python Software Foundation(,|$)') {
        throw 'Python 安装包的官方数字签名验证失败，已停止安装。请检查网络或电脑时间后重试。'
    }
    $Arguments = @('/quiet', 'InstallAllUsers=0', ('TargetDir="'+$Target+'"'), 'PrependPath=0', 'Include_test=0', 'Include_pip=0', 'Include_launcher=0', 'AssociateFiles=0', 'Shortcuts=0', '/log', ('"'+(Join-Path $Cache 'python-install.log')+'"'))
    $global:DS_START_STAGE = 'Official Python installer execution'
    $global:DS_START_TARGET = $Installer
    $Process = Start-Process -FilePath $Installer -ArgumentList $Arguments -WindowStyle Hidden -Wait -PassThru
    if ($Process.ExitCode -notin @(0,3010)) { throw ('Python 安装失败，错误码 '+$Process.ExitCode+'。日志：'+(Join-Path $Cache 'python-install.log')) }
    $Python = Join-Path $Target 'python.exe'
    if (-not (Test-CollectorPython $Python)) { throw 'Python 安装后验证失败，请查看安装日志。' }
    return $Python
}
