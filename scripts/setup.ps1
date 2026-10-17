$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$pythonCommand = Get-Command python -ErrorAction Stop
$pythonVersionText = & $pythonCommand.Source -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
$pythonVersion = [version]$pythonVersionText
if ($pythonVersion -lt [version]'3.11') {
    throw "SQBF requires Python 3.11 or later; found $pythonVersionText."
}

$venvPython = Join-Path $repoRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $venvPython)) {
    & $pythonCommand.Source -m venv (Join-Path $repoRoot '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Creating .venv failed.' }
}

& $venvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw 'Updating pip in .venv failed.' }

& $venvPython -m pip install -e $repoRoot
if ($LASTEXITCODE -ne 0) { throw 'Installing SQBF dependencies failed.' }

& $venvPython -m playwright install chromium
if ($LASTEXITCODE -ne 0) { throw 'Installing Playwright Chromium failed.' }

Write-Host "SQBF environment ready. Activate it with: .\.venv\Scripts\Activate.ps1"
