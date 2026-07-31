# Run Pynguin automated test generation against the api/db layer (Part 4).
#
# Prerequisites (one-time) — needs Python 3.10-3.12:
#   python -m venv .venv-pynguin
#   .\.venv-pynguin\Scripts\Activate.ps1
#   pip install "pynguin>=0.43.0" -r requirements.txt
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

# 30 s is what the committed results in docs/REPORT.md section 4 were produced
# with; raise it if you want a longer search (the coverage delta plateaus early
# on this module -- nearly every branch sits behind a live peewee query).
pynguin `
  --project-path "$Repo" `
  --module-name openunderstand.oudb.api `
  --output-path "$Repo\tests\generated" `
  --maximum-search-time 30 `
  --seed 42 `
  --assertion-generation MUTATION_ANALYSIS `
  -v

# Optional flags worth exploring (verify names with `pynguin --help`):
#   --assertion-generation MUTATION_ANALYSIS   # stronger assertions
#   --create-coverage-report true              # per-run coverage html
