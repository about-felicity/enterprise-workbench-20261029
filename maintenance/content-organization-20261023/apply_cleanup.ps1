$ErrorActionPreference = 'Stop'
$workspace = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$planPath = Join-Path $PSScriptRoot 'cleanup-plan.json'
$cleanupPlan = Get-Content -LiteralPath $planPath -Raw -Encoding utf8 | ConvertFrom-Json
if ($cleanupPlan.workspace -ne $workspace) { throw 'Workspace identity changed' }
$outputRoot = [System.IO.Path]::GetFullPath((Join-Path $workspace 'outputs')) + [System.IO.Path]::DirectorySeparatorChar
$cacheRoot = [System.IO.Path]::GetFullPath((Join-Path $workspace 'geo-source-card-collectors/geo_source_cards/__pycache__')) + [System.IO.Path]::DirectorySeparatorChar
$allowedReasons = @('regenerable_word_page_png','regenerable_word_contact_sheet','regenerable_pdf_page_png','regenerable_python_bytecode','byte_identical_duplicate_archive','byte_identical_generated_build_source')
$checkedPaths = @()
foreach ($entry in $cleanupPlan.actions) {
    $targetPath = (Resolve-Path -LiteralPath $entry.path).Path
    if (-not ($targetPath.StartsWith($outputRoot,[System.StringComparison]::OrdinalIgnoreCase) -or $targetPath.StartsWith($cacheRoot,[System.StringComparison]::OrdinalIgnoreCase))) { throw "Out of scope: $targetPath" }
    if ($allowedReasons -notcontains $entry.reason) { throw 'Unknown removal reason' }
    $targetItem = Get-Item -LiteralPath $targetPath -Force
    if ($targetItem.PSIsContainer -or ($targetItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint)) { throw 'Non-regular file refused' }
    if ((Get-FileHash -LiteralPath $targetPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.sha256) { throw "Target changed: $targetPath" }
    if ($entry.preserved_source) {
        $sourcePath = (Resolve-Path -LiteralPath $entry.preserved_source).Path
        if (-not $sourcePath.StartsWith($workspace + [System.IO.Path]::DirectorySeparatorChar,[System.StringComparison]::OrdinalIgnoreCase)) { throw 'Preserved source out of scope' }
        if ((Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.source_sha256) { throw "Preserved source changed: $sourcePath" }
    }
    $checkedPaths += $targetPath
}
$removedEntries = [System.Collections.Generic.List[object]]::new()
$removedDirectories = [System.Collections.Generic.List[string]]::new()
try {
    foreach ($entry in $cleanupPlan.actions) {
        Remove-Item -LiteralPath $entry.path -Force
        $removedEntries.Add($entry)
    }
    $parents = @($checkedPaths | ForEach-Object { [System.IO.Path]::GetDirectoryName($_) } | Sort-Object -Unique | Sort-Object Length -Descending)
    foreach ($parentPath in $parents) {
        if (-not (Test-Path -LiteralPath $parentPath -PathType Container)) { continue }
        if (-not ($parentPath.StartsWith($outputRoot,[System.StringComparison]::OrdinalIgnoreCase) -or ($parentPath + [System.IO.Path]::DirectorySeparatorChar) -eq $cacheRoot)) { throw 'Empty-directory scope changed' }
        if (@(Get-ChildItem -LiteralPath $parentPath -Force).Count -eq 0) {
            Remove-Item -LiteralPath $parentPath -Force
            $removedDirectories.Add($parentPath)
        }
    }
} finally {
    $bytesRemoved = ($removedEntries | Measure-Object -Property bytes -Sum).Sum
    $result = [ordered]@{workspace=$workspace;removed_file_count=$removedEntries.Count;removed_bytes=$bytesRemoved;all_planned_removed=($removedEntries.Count -eq $cleanupPlan.file_count);removed_empty_directories=@($removedDirectories);removed=@($removedEntries);business_code_removed=$false;production_mutated=$false;api_calls=0}
    $result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'cleanup-result.json') -Encoding utf8
}
Write-Output "Removed $($removedEntries.Count) files, $bytesRemoved bytes; production untouched."
