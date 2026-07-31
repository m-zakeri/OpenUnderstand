# Mutation testing with Cosmic Ray (Part 5). Run from the repo root with the
# main (.venv) environment activated; Cosmic Ray is installed by
# requirements-dev.txt, so there is nothing else to set up.
#
# Why Cosmic Ray on Windows: mutmut has no native Windows support
# (https://github.com/boxed/mutmut/issues/397). Cosmic Ray is cross-platform and
# is configured in cosmic-ray.toml to mutate openunderstand/oudb/api.py and run
# the unit suite against each mutant. On Linux/macOS/WSL you may use mutmut
# instead via scripts/run_mutation.sh.

$ErrorActionPreference = "Stop"

$session = "cr-session.sqlite"

# `cosmic-ray init` appends to an existing session; start from a clean slate so
# the reported score always reflects this run only.
if (Test-Path $session) {
    Write-Host ">> Removing previous session ($session) ..."
    Remove-Item $session -Force
}

Write-Host ">> Initialising mutation session ($session) ..."
cosmic-ray init cosmic-ray.toml $session

Write-Host ">> Executing mutants (runs the test suite per mutant; this is slow) ..."
cosmic-ray exec cosmic-ray.toml $session

Write-Host ">> Results:"
cr-report $session

Write-Host ""
Write-Host "Mutation score = killed / total (see docs/REPORT.md section 5.2)."
Write-Host "For an HTML report:  cr-html $session > cr-report.html"
