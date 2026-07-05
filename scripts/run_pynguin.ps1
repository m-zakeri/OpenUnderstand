# Run Pynguin automated test generation against the api/db layer (Part 4).
#
# Prerequisites (one-time):
#   py -3.12 -m venv .venv-pynguin
#   .\.venv-pynguin\Scripts\Activate.ps1
#   pip install "pynguin>=0.43.0"
#   pip install -r requirements.txt        # so the target module's imports resolve
#
# Then, with .venv-pynguin activated, run this script from the repo root.

$ErrorActionPreference = "Stop"
$Repo = (Resolve-Path "$PSScriptRoot\..").Path

# Pynguin executes the module under test; acknowledge that explicitly.
$env:PYNGUIN_DANGER_AWARE = "1"

# Put the repo root + the isolation shim on PYTHONPATH so sitecustomize.py
# stubs the ANTLR parser stack before Pynguin imports the target module.
$env:PYTHONPATH = "$Repo;$Repo\tests\_pynguin_support"

New-Item -ItemType Directory -Force -Path "$Repo\tests\generated" | Out-Null

pynguin `
  --project-path "$Repo" `
  --module-name openunderstand.oudb.api `
  --output-path "$Repo\tests\generated" `
  --maximum-search-time 120 `
  --seed 42 `
  -v

# Optional flags worth exploring (verify names with `pynguin --help`):
#   --assertion-generation MUTATION_ANALYSIS   # stronger assertions
#   --create-coverage-report true              # per-run coverage html
