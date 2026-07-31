#!/usr/bin/env bash
# Mutation testing with mutmut (Part 5).  Run from the repo root with the main
# (.venv) environment activated.
set -uo pipefail

echo ">> Running mutmut on openunderstand/oudb/api.py ..."
mutmut run || true   # mutmut exits non-zero when mutants survive; that's expected

echo ">> Results summary:"
mutmut results || true

# mutmut 3.x removed the `html` and `junitxml` subcommands that 2.x provided.
# `export-cicd-stats` is the machine-readable replacement; `browse` is the
# interactive report.  requirements-dev.txt pins mutmut>=3.0,<4.0, and
# setup.cfg uses the 3.x configuration keys.
echo ">> Machine-readable summary:"
mutmut export-cicd-stats || true

echo
echo "Mutation score = killed / (killed + survived)."
echo "Inspect a surviving mutant with:  mutmut show <id>"
echo "Browse all results interactively with:  mutmut browse"
