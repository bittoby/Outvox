<#
.SYNOPSIS
    Windows-friendly developer task runner for Outvox.

.DESCRIPTION
    Mirrors the targets in the repo-root Makefile so Windows contributors do
    not need GNU Make installed. Run from the repository root.

    Examples:

        # Install everything (BE + FE + tests)
        .\dev.ps1 install

        # Run backend tests
        .\dev.ps1 test

        # Frontend lint / type-check / build
        .\dev.ps1 lint
        .\dev.ps1 typecheck
        .\dev.ps1 build

        # Local dev servers
        .\dev.ps1 dev-be
        .\dev.ps1 dev-fe

.NOTES
    Uses the `py` launcher and `npm` from PATH.
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

function Invoke-InDirectory {
    param(
        [string]$Path,
        [scriptblock]$Action
    )
    Push-Location $Path
    try { & $Action } finally { Pop-Location }
}

switch ($Task) {
    "install"       { & $PSCommandPath install-be; & $PSCommandPath install-fe; & $PSCommandPath install-tests }
    "install-be"    { Invoke-InDirectory $RepoRoot { py -m pip install -r BE/requirements.txt } }
    "install-fe"    { Invoke-InDirectory (Join-Path $RepoRoot "FE") { npm ci } }
    "install-tests" { Invoke-InDirectory $RepoRoot { py -m pip install -r tests/requirements.txt python-dotenv } }

    "test"     { & $PSCommandPath test-be }
    "test-be"  { Invoke-InDirectory $RepoRoot { py -m pytest } }

    "lint"      { Invoke-InDirectory (Join-Path $RepoRoot "FE") { npm run lint } }
    "typecheck" { Invoke-InDirectory (Join-Path $RepoRoot "FE") { npx tsc -b --noEmit } }
    "build"     { Invoke-InDirectory (Join-Path $RepoRoot "FE") { npm run build } }

    "dev-be" { Invoke-InDirectory (Join-Path $RepoRoot "BE") { py db_service.py } }
    "dev-fe" { Invoke-InDirectory (Join-Path $RepoRoot "FE") { npm run dev } }

    "clean" {
        Invoke-InDirectory $RepoRoot {
            Remove-Item -Recurse -Force -ErrorAction Ignore FE\dist, .pytest_cache, .venv-test
            Get-ChildItem -Recurse -Directory -Filter __pycache__ |
                Remove-Item -Recurse -Force -ErrorAction Ignore
        }
    }
}
