#!/usr/bin/env bash
# Run Pynguin automated test generation against the api/db layer (Part 4).
#
# Prerequisites (one-time) — needs Python 3.10-3.12:
#   python3 -m venv .venv-pynguin
#   source .venv-pynguin/bin/activate
#   pip install "pynguin>=0.43.0" -r requirements.txt
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

# 30 s is what the committed results in docs/REPORT.md section 4 were produced
# with; raise it if you want a longer search (the coverage delta plateaus early
# on this module -- nearly every branch sits behind a live peewee query).
pynguin \
  --project-path "${REPO}" \
  --module-name openunderstand.oudb.api \
  --output-path "${REPO}/tests/generated" \
  --maximum-search-time 30 \
  --seed 42 \
  --assertion-generation MUTATION_ANALYSIS \
  -v

# Optional flags worth exploring (verify names with `pynguin --help`):
#   --assertion-generation MUTATION_ANALYSIS   # stronger assertions
#   --create-coverage-report true              # per-run coverage html
