"""Produce a self-extracting CMD. The private enrollment capability stays in delivery only."""
from pathlib import Path
import base64,hashlib,io,zipfile,textwrap

ROOT=Path(__file__).resolve().parents[2]
SOURCE=Path(__file__).resolve().parent
CONFIG=ROOT/'outputs/DeepSeek同事公网版/config/public_upload.json'
OUTPUT=ROOT/'outputs/DeepSeek_一键安装启动.cmd'
files=['ensure_python.ps1','start_monitor.ps1','restart_receiver.ps1','enrollment.py','local_receiver.py','remote_sync.py','questions.txt','使用说明.txt']
buffer=io.BytesIO()
with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as archive:
    for name in files:archive.write(SOURCE/name,name)
    for path in (SOURCE/'extension').iterdir():
        if path.is_file():archive.write(path,'extension/'+path.name)
    archive.write(CONFIG,'config/public_upload.json')
payload=buffer.getvalue()
digest=hashlib.sha256(payload).hexdigest().upper()
script=r'''
$ErrorActionPreference='Stop'
$global:DS_START_STAGE='Payload extraction'
$global:DS_START_TARGET=''
try {
 $s=[IO.File]::ReadAllText($env:DS_INSTALLER_SELF)
 $p=($s -split '(?m)^:__DS_PAYLOAD__\r?$',2)[1]
 $b=[Convert]::FromBase64String(($p -replace '\s',''))
 $h=[Security.Cryptography.SHA256]::Create()
 if ([BitConverter]::ToString($h.ComputeHash($b)).Replace('-','') -ne 'DIGEST') {throw 'Installer is incomplete. Download the single CMD file again.'}
 $h.Dispose()
 Add-Type -AssemblyName System.IO.Compression
 $m=[IO.MemoryStream]::new($b,$false)
 $z=[IO.Compression.ZipArchive]::new($m,[IO.Compression.ZipArchiveMode]::Read)
 $root=[IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA 'DeepSeekCollector\App'))
 foreach($e in $z.Entries) {
  $target=[IO.Path]::GetFullPath((Join-Path $root $e.FullName))
  $global:DS_START_TARGET=$target
  if (-not $target.StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase)) {throw 'Invalid package path'}
  [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($target)) | Out-Null
  $from=$e.Open();$to=[IO.File]::Create($target)
  try {$from.CopyTo($to)} finally {$to.Dispose();$from.Dispose()}
 }
 $z.Dispose();$m.Dispose()
 Write-Host ('Files ready: '+$root)
 $global:DS_START_STAGE='Loading startup script'
 $global:DS_START_TARGET=Join-Path $root 'start_monitor.ps1'
 if ($env:DS_BOOTSTRAP_CHECK -eq '1') {& (Join-Path $root 'start_monitor.ps1') -CheckPackage}
 else {& (Join-Path $root 'start_monitor.ps1')}
} catch {
 $detail='Stage: '+$global:DS_START_STAGE+"`r`nTarget: "+$global:DS_START_TARGET+"`r`nError: "+$_.Exception.Message+"`r`nType: "+$_.Exception.GetType().FullName+"`r`nCode: "+$_.FullyQualifiedErrorId+"`r`nLocation: "+$_.InvocationInfo.ScriptName+':'+$_.InvocationInfo.ScriptLineNumber+"`r`nStack: "+$_.ScriptStackTrace
 Write-Host $detail -ForegroundColor Red
 foreach($log in @((Join-Path $env:LOCALAPPDATA 'DeepSeekCollector\startup-error.txt'),(Join-Path $env:TEMP 'DeepSeekCollector-startup-error.txt'))) {
  try {[IO.File]::WriteAllText($log,$detail);Write-Host ('Diagnostic log: '+$log);break} catch {}
 }
 exit 1
}
'''.replace('DIGEST',digest)
encoded=base64.b64encode(script.encode('utf-16le')).decode('ascii')
command='powershell.exe -NoProfile -ExecutionPolicy Bypass -EncodedCommand '+encoded
assert len(command)<8000,'CMD command line limit'
header='\r\n'.join([
 '@echo off','setlocal','chcp 65001 >nul','set "DS_INSTALLER_SELF=%~f0"','set "DS_BOOTSTRAP_CHECK="',
 'if /I "%~1"=="--check" set "DS_BOOTSTRAP_CHECK=1"',command,
 'set "DS_RESULT=%ERRORLEVEL%"','if /I not "%~1"=="--check" if /I not "%~1"=="--no-pause" pause','exit /b %DS_RESULT%',':__DS_PAYLOAD__',''])
OUTPUT.write_bytes((header+'\r\n'.join(textwrap.wrap(base64.b64encode(payload).decode('ascii'),100))+'\r\n').encode('ascii'))
print('Built single-file launcher; payload files included, no external PS1 needed.')
