#!/usr/bin/env bash
# Mutation testing with mutmut (Part 5).  Run from the repo root with the main
# (.venv) environment activated.
set -uo pipefail

echo ">> Running mutmut on openunderstand/oudb/api.py ..."
mutmut run || true   # mutmut exits non-zero when mutants survive; that's expected

echo ">> Results summary:"
mutmut results || true

echo ">> Generating HTML report (./html/index.html):"
mutmut html || true

echo
echo "Mutation score = killed / (killed + survived)."
echo "Inspect a surviving mutant with:  mutmut show <id>"
