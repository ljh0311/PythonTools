# Normalize android shell scripts to LF (required for Termux/bash).
$ErrorActionPreference = "Stop"
$android = Split-Path -Parent $MyInvocation.MyCommand.Path
$files = @("install.sh", "carrs", "verify_install.sh", "package.sh", "go.sh")
$utf8 = New-Object System.Text.UTF8Encoding $false
foreach ($name in $files) {
    $path = Join-Path $android $name
    $text = [System.IO.File]::ReadAllText($path) -replace "`r`n", "`n" -replace "`r", "`n"
    [System.IO.File]::WriteAllText($path, $text, $utf8)
    Write-Host "Normalized LF: $name"
}
