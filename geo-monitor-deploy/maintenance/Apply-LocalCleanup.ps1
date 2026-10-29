param([switch]$Apply)
$ErrorActionPreference = 'Stop'
$workspace = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$auditDir = Join-Path $PSScriptRoot '20261015'
$plan = Get-Content -LiteralPath (Join-Path $auditDir 'local-cleanup-plan.json') -Raw | ConvertFrom-Json
if ($plan.root -ne $workspace) { throw 'Workspace mismatch' }
function Get-CheckedPath([string]$relative) {
    $target = [IO.Path]::GetFullPath((Join-Path $workspace $relative))
    if (-not $target.StartsWith($workspace + [IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) {
        throw 'Target outside intended workspace'
    }
    $part = $target
    while ($part -and $part -ne $workspace) {
        if (Test-Path -LiteralPath $part) {
            $item = Get-Item -LiteralPath $part -Force
            if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Reparse point rejected' }
        }
        $part = Split-Path -Parent $part
    }
    return $target
}
function Assert-Hash([string]$path,[string]$expected) {
    if ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) {
        throw "File changed since inventory: $path"
    }
}
# Validate every target and retained archive before the first mutation.
Assert-Hash (Get-CheckedPath ('geo-monitor-deploy\maintenance\20261015\' + $plan.archive)) $plan.archive_sha256
foreach ($row in $plan.files) {
    $path = Get-CheckedPath $row.path
    Assert-Hash $path $row.sha256
    if ($row.action -eq 'replace_with_tail') {
        Assert-Hash (Get-CheckedPath $row.archive) $row.archive_sha256
        Assert-Hash (Get-CheckedPath $row.replacement) $row.replacement_sha256
    }
}
foreach ($relative in $plan.directories) { $null=Get-CheckedPath $relative }
if (-not $Apply) {
    [pscustomobject]@{ Validated=$true; Files=$plan.files.Count; ExpectedNetBytes=$plan.net_expected_bytes } | ConvertTo-Json
    exit
}
$actions = @()
foreach ($row in $plan.files) {
    $path = Get-CheckedPath $row.path
    if ($row.action -eq 'replace_with_tail') {
        Move-Item -LiteralPath (Get-CheckedPath $row.replacement) -Destination $path -Force
    } else {
        Remove-Item -LiteralPath $path -Force
    }
    $actions += [pscustomobject]@{ Path=$row.path; Action=$row.action; OriginalBytes=$row.bytes; OriginalSha256=$row.sha256 }
}
# Remove only empty directory trees. New or unplanned files are never removed.
foreach ($relative in ($plan.directories | Sort-Object Length -Descending)) {
    $path=Get-CheckedPath $relative
    if (-not (Test-Path -LiteralPath $path)) { continue }
    Get-ChildItem -LiteralPath $path -Directory -Recurse -Force | Sort-Object FullName -Descending | ForEach-Object {
        $checked=Get-CheckedPath ([IO.Path]::GetRelativePath($workspace,$_.FullName))
        if (-not (Get-ChildItem -LiteralPath $checked -Force | Select-Object -First 1)) { Remove-Item -LiteralPath $checked -Force }
    }
    if (-not (Get-ChildItem -LiteralPath $path -Force | Select-Object -First 1)) { Remove-Item -LiteralPath $path -Force }
}
[pscustomobject]@{ AppliedAt=(Get-Date).ToString('o'); Root=$workspace; Actions=$actions; ExpectedNetBytes=$plan.net_expected_bytes } |
    ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $auditDir 'local-cleanup-applied.json') -Encoding utf8
[pscustomobject]@{ Applied=$true; Files=$actions.Count; ExpectedNetBytes=$plan.net_expected_bytes } | ConvertTo-Json
