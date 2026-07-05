#!/usr/bin/env bash
# Run Pynguin automated test generation against the api/db layer (Part 4).
#
# Prerequisites (one-time):
#   python3.12 -m venv .venv-pynguin
#   source .venv-pynguin/bin/activate
#   pip install "pynguin>=0.43.0"
#   pip install -r requirements.txt        # so the target module's imports resolve
#
# Then, with .venv-pynguin activated, run this script from the repo root.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Pynguin executes the module under test; acknowledge that explicitly.
export PYNGUIN_DANGER_AWARE=1

# Put the repo root + the isolation shim on PYTHONPATH so sitecustomize.py
# stubs the ANTLR parser stack before Pynguin imports the target module.
export PYTHONPATH="${REPO}:${REPO}/tests/_pynguin_support"

mkdir -p "${REPO}/tests/generated"

pynguin \
  --project-path "${REPO}" \
  --module-name openunderstand.oudb.api \
  --output-path "${REPO}/tests/generated" \
  --maximum-search-time 120 \
  --seed 42 \
  -v

# Optional flags worth exploring (verify names with `pynguin --help`):
#   --assertion-generation MUTATION_ANALYSIS   # stronger assertions
#   --create-coverage-report true              # per-run coverage html
