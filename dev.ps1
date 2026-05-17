<#
.SYNOPSIS
    Windows-friendly developer task runner for Outvox.

.DESCRIPTION
    Mirrors the targets in the repo-root Makefile so Windows contributors do
    not need GNU Make installed. Run from the repository root.

    Creates a single `.venv` at the repo root and installs both the backend
    and test requirements into it. Uses the most recent Python that the
    project's pinned dependencies support (3.11 - 3.13). Refuses to use
    Python 3.14 or newer because `pydantic_core` and `asyncpg` do not have
    3.14 wheels yet.

    Examples:

        .\dev.ps1 install          # everything (BE deps + FE deps in one go)
        .\dev.ps1 test             # backend tests via .venv
        .\dev.ps1 lint             # frontend ESLint
        .\dev.ps1 typecheck        # frontend tsc
        .\dev.ps1 build            # frontend Vite build
        .\dev.ps1 dev-be           # start db_service on :8000
        .\dev.ps1 dev-fe           # start Vite dev server on :3000
        .\dev.ps1 clean            # remove build/cache artifacts

.NOTES
    Uses the Python launcher (`py`) and `npm` from PATH.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet(
        "install", "install-be", "install-fe", "install-tests",
        "test", "test-be",
        "lint", "typecheck", "build",
        "dev-be", "dev-fe",
        "clean"
    )]
    [string]$Task
)

$ErrorActionPreference = "Stop"
$RepoRoot = $PSScriptRoot
$VenvPath = Join-Path $RepoRoot ".venv"
$VenvPython = Join-Path $VenvPath "Scripts\python.exe"

# Python versions whose pinned wheels exist for our deps. Update this list
# (and BE/requirements.txt) together when a new Python version ships.
$SupportedPythonVersions = @("3.12", "3.13", "3.11")
$MinPythonMajor = 3
$MinPythonMinor = 11
$MaxPythonMinor = 13   # inclusive; bump when pydantic/asyncpg ship newer wheels

function Invoke-InDirectory {
    param([string]$Path, [scriptblock]$Action)
    Push-Location $Path
    try { & $Action } finally { Pop-Location }
}

function Find-CompatiblePython {
    # Returns the version string (e.g. "3.12") of the best available Python,
    # or $null if none of $SupportedPythonVersions is installed.
    #
    # `py.exe` writes "No suitable Python runtime found" to stderr when a
    # requested version is missing, so we wrap each probe in try/catch
    # (PowerShell's strict ErrorActionPreference treats stderr writes from
    # native commands as terminating errors).
    foreach ($v in $SupportedPythonVersions) {
        try {
            & py "-$v" --version *> $null
            if ($LASTEXITCODE -eq 0) { return $v }
        } catch {
            # py.exe printed to stderr because this version isn't installed.
            # Move on to the next candidate.
        }
    }
    return $null
}

function Assert-VenvReady {
    if (-not (Test-Path $VenvPython)) {
        Write-Host ""
        Write-Host "ERROR: .venv is not initialized." -ForegroundColor Red
        Write-Host "       Run: .\dev.ps1 install" -ForegroundColor Yellow
        Write-Host ""
        exit 1
    }
}

function New-Venv {
    if (Test-Path $VenvPython) {
        Write-Host ".venv already exists; reusing it." -ForegroundColor DarkGray
        return
    }

    $version = Find-CompatiblePython
    if (-not $version) {
        Write-Host ""
        Write-Host "ERROR: No supported Python interpreter found." -ForegroundColor Red
        Write-Host ""
        Write-Host "Outvox pins dependencies (pydantic_core, asyncpg) that currently ship"
        Write-Host "wheels for Python $MinPythonMajor.$MinPythonMinor - $MinPythonMajor.$MaxPythonMinor only."
        Write-Host "Install one of those versions:"
        Write-Host ""
        Write-Host "    winget install -e --id Python.Python.3.12" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Then re-run .\dev.ps1 install"
        Write-Host ""
        exit 1
    }

    Write-Host "Creating .venv with Python $version ..." -ForegroundColor Cyan
    & py "-$version" -m venv $VenvPath
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    & $VenvPython -m pip install --upgrade pip --quiet
}

function Install-Backend {
    New-Venv
    Write-Host "Installing backend dependencies into .venv ..." -ForegroundColor Cyan
    & $VenvPython -m pip install -r (Join-Path $RepoRoot "BE\requirements.txt")
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

function Install-Tests {
    New-Venv
    Write-Host "Installing test dependencies into .venv ..." -ForegroundColor Cyan
    & $VenvPython -m pip install -r (Join-Path $RepoRoot "tests\requirements.txt")
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

function Install-Frontend {
    Invoke-InDirectory (Join-Path $RepoRoot "FE") { npm ci }
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

switch ($Task) {
    "install"       { Install-Backend; Install-Tests; Install-Frontend }
    "install-be"    { Install-Backend }
    "install-fe"    { Install-Frontend }
    "install-tests" { Install-Tests }

    "test"     { Assert-VenvReady; Invoke-InDirectory $RepoRoot { & $VenvPython -m pytest } }
    "test-be"  { Assert-VenvReady; Invoke-InDirectory $RepoRoot { & $VenvPython -m pytest } }

    "lint"      { Invoke-InDirectory (Join-Path $RepoRoot "FE") { npm run lint } }
    "typecheck" { Invoke-InDirectory (Join-Path $RepoRoot "FE") { npx tsc -b --noEmit } }
    "build"     { Invoke-InDirectory (Join-Path $RepoRoot "FE") { npm run build } }

    "dev-be" {
        Assert-VenvReady
        Invoke-InDirectory (Join-Path $RepoRoot "BE") { & $VenvPython db_service.py }
    }
    "dev-fe" {
        Invoke-InDirectory (Join-Path $RepoRoot "FE") { npm run dev }
    }

    "clean" {
        Invoke-InDirectory $RepoRoot {
            Remove-Item -Recurse -Force -ErrorAction Ignore `
                FE\dist, .pytest_cache, .venv-test, .venv
            Get-ChildItem -Recurse -Directory -Filter __pycache__ |
                Remove-Item -Recurse -Force -ErrorAction Ignore
        }
    }
}
