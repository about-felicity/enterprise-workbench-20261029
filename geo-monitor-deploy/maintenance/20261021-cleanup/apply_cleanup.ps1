$ErrorActionPreference='Stop'
$workspaceRoot=(Resolve-Path -LiteralPath '.').ProviderPath.TrimEnd('\')
$reportRoot=Join-Path $workspaceRoot 'geo-monitor-deploy\maintenance\20261021-cleanup'
$manifest=Get-Content -LiteralPath (Join-Path $reportRoot 'plan.json') -Raw | ConvertFrom-Json
if(Test-Path -LiteralPath (Join-Path $reportRoot 'applied.json')){throw 'Cleanup was already applied'}
if($manifest.root -ne $workspaceRoot){throw 'Workspace mismatch'}
function Resolve-SafeTarget([string]$relative){
 $target=[IO.Path]::GetFullPath((Join-Path $workspaceRoot $relative))
 if(-not $target.StartsWith($workspaceRoot+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Target outside workspace'}
 $cursor=Get-Item -LiteralPath $target -Force
 while($cursor.FullName -ne $workspaceRoot){
  if(($cursor.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw ('Reparse target retained: '+$target)}
  $cursor=Get-Item -LiteralPath ([IO.Path]::GetDirectoryName($cursor.FullName)) -Force
 }
 return $target
}
$logPath=Resolve-SafeTarget $manifest.log.path
$archivePath=Resolve-SafeTarget $manifest.log.archive
$tailPath=Resolve-SafeTarget $manifest.log.replacement
if((Get-FileHash -LiteralPath $logPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $manifest.log.sha256){throw 'Log changed; retain it'}
if((Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $manifest.log.archive_sha256){throw 'Archive failed hash verification'}
if((Get-FileHash -LiteralPath $tailPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $manifest.log.tail_sha256){throw 'Tail failed hash verification'}
$tailBytes=[IO.File]::ReadAllBytes($tailPath)
$logStream=[IO.File]::Open($logPath,[IO.FileMode]::Open,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
try {if($logStream.Length -ne $manifest.log.bytes){throw 'Log size changed'};$logStream.SetLength(0);$logStream.Write($tailBytes,0,$tailBytes.Length);$logStream.Flush($true)}finally{$logStream.Dispose()}
$deleted=@();$failures=@();$removedBytes=0L
foreach($entry in $manifest.directories){
 try{
  if(-not(Test-Path -LiteralPath (Join-Path $workspaceRoot $entry.path))){continue}
  $target=Resolve-SafeTarget $entry.path
  $reparse=Get-ChildItem -LiteralPath $target -Recurse -Force | Where-Object {($_.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0} | Select-Object -First 1
  if($reparse){throw 'Nested reparse point retained'}
  Remove-Item -LiteralPath $target -Recurse -Force
  $deleted+=$entry.path;$removedBytes+=[long]$entry.bytes
 }catch{$failures+=[pscustomobject]@{path=$entry.path;error=$_.Exception.Message}}
}
$proof=[pscustomobject]@{at=(Get-Date).ToString('o');root=$workspaceRoot;deleted_directories=$deleted;failures=$failures;cache_bytes_removed=$removedBytes;log_bytes_before=[long]$manifest.log.bytes;log_bytes_after=(Get-Item -LiteralPath $logPath).Length;full_log_archive=$manifest.log.archive;archive_bytes=[long]$manifest.log.archive_bytes;net_bytes_reclaimed=($removedBytes+[long]$manifest.log.bytes-[long]$manifest.log.archive_bytes-[long]$manifest.log.tail_bytes);server_mutations=0;services_restarted=0;retained='Source, delivered files, datasets, sessions, queues, credentials, .git, runtime dependencies, reparse targets, rollback and unique failure evidence'}
$proof | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $reportRoot 'applied.json') -Encoding utf8
[pscustomobject]@{DeletedDirectories=$deleted.Count;Failures=$failures.Count;NetReclaimedMiB=[math]::Round($proof.net_bytes_reclaimed/1MB,2);LogTailBytes=$proof.log_bytes_after;ArchiveMiB=[math]::Round($proof.archive_bytes/1MB,2)} | ConvertTo-Json
