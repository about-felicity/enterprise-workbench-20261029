"""Build a transparent ZIP with a visible extension and no PS1/encoded payload."""
from pathlib import Path
import hashlib,json,shutil,zipfile
ROOT=Path(__file__).resolve().parents[2];SRC=Path(__file__).resolve().parent
DEST=ROOT/'outputs/DeepSeekCollector_v3';DEST.mkdir(exist_ok=True)
# This is passed as readable inline PowerShell, not a generated script or encoded command.
code=r'''
$ErrorActionPreference='Stop';$stage='Python discovery';$target='';
function Good($p){try{if(-not $p -or $p -like '*WindowsApps*' -or -not(Test-Path -LiteralPath $p -PathType Leaf -ErrorAction Stop)){return $false};& $p -I -S -c 'import sys,ssl,json,http.server,urllib.request;assert (3,10)<=sys.version_info[:2]<(4,0)' *> $null;return ($LASTEXITCODE -eq 0)}catch{return $false}};
try {
$target=Join-Path $env:LOCALAPPDATA 'DeepSeekCollector\Python313';$py=Join-Path $target 'python.exe';
if(-not(Good $py)){$py=$null;foreach($n in @('python','python3')){try{$p=(Get-Command $n -ErrorAction Stop).Source;if(Good $p){$py=$p;break}}catch{}}};
if(-not $py){foreach($h in @('HKCU:\Software\Python\PythonCore','HKLM:\Software\Python\PythonCore','HKLM:\Software\WOW6432Node\Python\PythonCore')){try{$keys=@(Get-ChildItem -LiteralPath $h -ErrorAction Stop)}catch{continue};foreach($k in $keys){try{$i=Get-Item -LiteralPath ($k.PSPath+'\InstallPath') -ErrorAction Stop;$p=[string]$i.GetValue('ExecutablePath');if(-not $p){$p=Join-Path ([string]$i.GetValue('')) 'python.exe'};if(Good $p){$py=$p;break}}catch{}};if($py){break}}};
if(-not $py){
Write-Host '[2/4] Installing official Python for current user...';$stage='Official Python download';
$v='3.13.16';$a=if($env:PROCESSOR_ARCHITEW6432){$env:PROCESSOR_ARCHITEW6432}else{$env:PROCESSOR_ARCHITECTURE};if(-not $a){try{$a=[System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString()}catch{$a=if([Environment]::Is64BitOperatingSystem){'AMD64'}else{'X86'}}};$suffix=switch($a.ToUpperInvariant()){'AMD64'{'-amd64'} 'X64'{'-amd64'} 'ARM64'{'-arm64'} 'X86'{''} default{throw 'Unsupported Windows architecture'}};
$cache=Join-Path $env:LOCALAPPDATA 'DeepSeekCollector\installers';New-Item -ItemType Directory -Path $cache -Force|Out-Null;$exe=Join-Path $cache ('python-'+$v+$suffix+'.exe');
[Net.ServicePointManager]::SecurityProtocol=[Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12;
Invoke-WebRequest -UseBasicParsing -Uri ('https://www.python.org/ftp/python/'+$v+'/python-'+$v+$suffix+'.exe') -OutFile $exe -TimeoutSec 180;
$sig=Get-AuthenticodeSignature -LiteralPath $exe;if($sig.Status -ne 'Valid' -or $sig.SignerCertificate.Subject -notmatch '(^|,\s*)CN=Python Software Foundation(,|$)'){throw 'Official installer signature check failed'};
$stage='Official Python install';$q=[char]34;$r=Start-Process -FilePath $exe -WindowStyle Hidden -Wait -PassThru -ArgumentList @('/quiet','InstallAllUsers=0',('TargetDir='+$q+$target+$q),'PrependPath=0','Include_launcher=0','Include_test=0','Include_pip=0','AssociateFiles=0','Shortcuts=0','/log',($q+(Join-Path $cache 'python-install.log')+$q));if($r.ExitCode -notin @(0,3010)){throw ('Installer exit code: '+$r.ExitCode)};$py=Join-Path $target 'python.exe';if(-not(Good $py)){throw 'Installed Python could not run'};
};
$stage='Python bootstrap';$entry=Join-Path $env:DS_PACKAGE_ROOT 'app\bootstrap.py';$check=@();if($env:DS_CHECK -eq '1'){$check=@('--check')};& $py -X utf8 -B $entry @check;exit $LASTEXITCODE;
}catch{Write-Host ('Stage: '+$stage);Write-Host ('Target: '+$target);Write-Host ('Error: '+$_.Exception.Message);exit 1}
'''
line=' '.join(s.strip() for s in code.splitlines() if s.strip()).replace(chr(92)*2,chr(92))
assert '"' not in line and len(line)<7000
cmd='\r\n'.join(['@echo off','setlocal','chcp 65001 >nul','set "DS_PACKAGE_ROOT=%~dp0"','set "DS_CHECK="','if /I "%~1"=="--check" set "DS_CHECK=1"',r'if not exist "%~dp0app\bootstrap.py" goto missing','if not exist "%~dp0manifest.json" goto missing','powershell.exe -NoProfile -Command "'+line+'"','set "RESULT=%ERRORLEVEL%"','if /I not "%~1"=="--check" if /I not "%~1"=="--no-pause" pause','exit /b %RESULT%',':missing','echo Package is incomplete. Extract the entire ZIP; keep START.cmd, app, config and extension together.','if /I not "%~1"=="--check" pause','exit /b 2',''])
(DEST/'START.cmd').write_bytes(cmd.encode('ascii'))
for folder in ['app','config','extension']:(DEST/folder).mkdir(exist_ok=True)
shutil.copy2(SRC/'windows_bootstrap.py',DEST/'app/bootstrap.py')
for name in ['enrollment.py','local_receiver.py','remote_sync.py']:shutil.copy2(SRC/name,DEST/'app'/name)
shutil.copy2(ROOT/'outputs/DeepSeek同事公网版/config/public_upload.json',DEST/'config/public_upload.json')
for p in (SRC/'extension').iterdir():
 if p.is_file():shutil.copy2(p,DEST/'extension'/p.name)
(DEST/'使用说明.txt').write_text('Windows 10/11 多电脑版 v3\n\n1. 完整解压整个ZIP，保持 START.cmd、app、config、extension 在同一层。\n2. 双击 START.cmd。自动检查或安装官方Python，随后检查并启动接收器。\n3. Chrome 打开 chrome://extensions，开启开发者模式，加载本包 extension 文件夹。\n4. 登录DeepSeek，在插件里点击开始。\n\n本包没有PS1脚本、没有编码的PowerShell命令、没有嵌入在CMD里的压缩包。不需要手动提权或关闭安全防护。第一次安装Python需要联网。已有Python、设备配置和结果继续保留。重复启动不会新增接收器；端口被别的程序占用会明确提示且不停止对方。\n\n失败时请提供窗口完整Stage、Error与Diagnostic log信息。公司策略明确阻止Python或PowerShell时，需要管理员按公司流程允许运行，本包不会绕过策略。\n\n包内有采集设备登记凭据，只发给授权同事，不要公开发布。\n',encoding='utf-8-sig')
manifest={p.relative_to(DEST).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in DEST.rglob('*') if p.is_file() and p!=DEST/'manifest.json'}
(DEST/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
output=ROOT/'outputs/DeepSeek_标准安装包_v3.zip'
with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as z:
 for rel in [*manifest,'manifest.json']:z.write(DEST/rel,Path('DeepSeekCollector')/rel)
print('Built standard Windows package: no PS1 files or encoded PowerShell.')
