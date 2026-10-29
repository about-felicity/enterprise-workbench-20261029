param([Parameter(Mandatory=$true)][string]$InputDocx,[Parameter(Mandatory=$true)][string]$OutputPdf)
$ErrorActionPreference = 'Stop'
$resolvedInput = (Resolve-Path -LiteralPath $InputDocx).Path
$resolvedOutput = [System.IO.Path]::GetFullPath($OutputPdf)
[System.IO.Directory]::CreateDirectory([System.IO.Path]::GetDirectoryName($resolvedOutput)) | Out-Null
$wordApplication = $null
$openedDocument = $null
try {
    $wordApplication = New-Object -ComObject Word.Application
    if ($wordApplication.Documents.Count -ne 0) { throw 'Existing user documents detected; refusing to use that Word instance.' }
    $wordApplication.Visible = $false
    $wordApplication.DisplayAlerts = 0
    $wordApplication.AutomationSecurity = 3
    $openedDocument = $wordApplication.Documents.Open($resolvedInput, $false, $true, $false)
    $openedDocument.ExportAsFixedFormat($resolvedOutput, 17)
    Write-Output $resolvedOutput
} finally {
    if ($null -ne $openedDocument) { $openedDocument.Close(0); [System.Runtime.InteropServices.Marshal]::ReleaseComObject($openedDocument) | Out-Null }
    if ($null -ne $wordApplication -and $wordApplication.Documents.Count -eq 0) { $wordApplication.Quit(); [System.Runtime.InteropServices.Marshal]::ReleaseComObject($wordApplication) | Out-Null }
}
