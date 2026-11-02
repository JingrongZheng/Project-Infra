param(
    [Parameter(Mandatory=$true)][string]$Destination,
    [string]$Python = 'python'
)
$ErrorActionPreference = 'Stop'
$target = [System.IO.Path]::GetFullPath($Destination)
if (Test-Path -LiteralPath $target) {
    throw "Destination already exists. Choose a new empty installation path: $target"
}
$wheels = @(Get-ChildItem -LiteralPath $PSScriptRoot -Filter 'project_infra-*.whl')
if ($wheels.Count -ne 1) { throw 'Keep exactly one project_infra wheel beside this installer.' }
& $Python -c "import sys; assert sys.version_info >= (3,11), 'Python 3.11+ required'"
if ($LASTEXITCODE -ne 0) { throw 'Python 3.11+ is required.' }
& $Python -m venv (Join-Path $target '.venv')
if ($LASTEXITCODE -ne 0) { throw 'Could not create isolated environment.' }
$installedPython = Join-Path $target '.venv/Scripts/python.exe'
& $installedPython -m pip install --no-index --no-deps $wheels[0].FullName
if ($LASTEXITCODE -ne 0) { throw 'Offline installation failed; see output above.' }
$wrapper = '@echo off' + "`r`n" + '@"%~dp0.venv\Scripts\project-infra.exe" %*' + "`r`n"
[System.IO.File]::WriteAllText((Join-Path $target 'project-infra.cmd'), $wrapper, [System.Text.Encoding]::ASCII)
& $installedPython -m project_infra --version
if ($LASTEXITCODE -ne 0) { throw 'Installed tool did not start.' }
Write-Host "Installed locally. Run from your project directory:"
Write-Host "  & '$target/project-infra.cmd' init"
Write-Host "  & '$target/project-infra.cmd' serve --port 8765"
