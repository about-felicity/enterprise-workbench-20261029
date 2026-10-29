$ErrorActionPreference = 'Stop'
$workspace = (Resolve-Path -LiteralPath '.').Path
$allowed = @('geo-monitor-deploy/creation','geo-monitor-deploy/tests','geo-monitor-deploy/server-source','redroid-deploy/tests','yuanbao-deploy','geo-source-card-collectors/geo_source_cards','geo-source-card-collectors/web_collectors','geo-source-card-collectors/wenxin_monitor','geo-source-card-collectors/monitor_core','geo-source-card-collectors/tests')
$deleted = @()
foreach ($relative in $allowed) {
    $scope = (Resolve-Path -LiteralPath (Join-Path $workspace $relative)).Path
    if (-not $scope.StartsWith($workspace + '\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Out-of-workspace scope' }
    $files = Get-ChildItem -LiteralPath $scope -Recurse -File -Filter '*.pyc' | Where-Object { $_.Directory.Name -eq '__pycache__' -and $_.FullName -notmatch '\\(maintenance|artifacts|diagnostics|profile|profiles|\.git|venv)\\' }
    foreach ($file in $files) {
        $resolved = (Resolve-Path -LiteralPath $file.FullName).Path
        if (-not $resolved.StartsWith($scope + '\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Invalid cache target' }
        if (($file.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Refusing reparse target' }
        $deleted += [pscustomobject]@{path=$resolved;bytes=$file.Length;sha256=(Get-FileHash -LiteralPath $resolved -Algorithm SHA256).Hash}
    }
}
$manifest = Join-Path $workspace 'geo-monitor-deploy/maintenance/20261015-unified/local-generated-cleanup.json'
if (Test-Path -LiteralPath $manifest) { throw 'Manifest already exists; inspect before repeating' }
@{at=(Get-Date).ToString('o');files=$deleted;bytes=($deleted | Measure-Object bytes -Sum).Sum;scope='Reproducible Python bytecode in explicitly named source directories only'} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifest -Encoding utf8
foreach ($entry in $deleted) {
    if ((Get-FileHash -LiteralPath $entry.path -Algorithm SHA256).Hash -ne $entry.sha256) { throw 'Cache changed before deletion' }
    Remove-Item -LiteralPath $entry.path
}
$deleted | ForEach-Object { Split-Path -LiteralPath $_.path } | Sort-Object -Unique | ForEach-Object {
    if ((Get-ChildItem -LiteralPath $_ -Force | Measure-Object).Count -eq 0) { Remove-Item -LiteralPath $_ }
}
Write-Output ('Removed {0} bytecode files, {1} bytes' -f $deleted.Count,($deleted | Measure-Object bytes -Sum).Sum)
