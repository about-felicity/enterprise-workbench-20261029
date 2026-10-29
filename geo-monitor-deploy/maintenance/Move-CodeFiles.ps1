$ErrorActionPreference='Stop'
$workspace=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$planPath=Join-Path $PSScriptRoot '20261015-reorganize\organization-plan.json'
$plan=Get-Content -LiteralPath $planPath -Raw | ConvertFrom-Json
if ($plan.root -ne $workspace) { throw 'Wrong workspace' }
function Checked([string]$relative) {
    $p=[IO.Path]::GetFullPath((Join-Path $workspace $relative))
    if (-not $p.StartsWith($workspace+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) { throw 'Outside workspace' }
    $part=$p
    while ($part -and $part -ne $workspace) {
        if ((Test-Path -LiteralPath $part) -and ((Get-Item -LiteralPath $part -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'Reparse point rejected' }
        $part=Split-Path -Parent $part
    }
    return $p
}
foreach ($row in $plan.moves) {
    $src=Checked $row.source;$dst=Checked $row.target
    if (Test-Path -LiteralPath $dst) { throw "Destination exists: $dst" }
    if ((Get-FileHash -LiteralPath $src -Algorithm SHA256).Hash.ToLowerInvariant() -ne $row.sha256) { throw "Changed file: $src" }
}
foreach ($row in $plan.moves) {
    $src=Checked $row.source;$dst=Checked $row.target
    $parent=Split-Path -Parent $dst
    if (-not (Test-Path -LiteralPath $parent)) { $null=New-Item -ItemType Directory -Path $parent -Force }
    Move-Item -LiteralPath $src -Destination $dst
}
[pscustomobject]@{ Moved=$plan.moves.Count } | ConvertTo-Json
