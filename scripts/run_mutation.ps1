# Mutation testing with mutmut (Part 5). Run from the repo root with the main
# (.venv) environment activated.
#
# NOTE: mutmut can misbehave on native Windows. If you hit errors, run this
# under WSL, or switch to cosmic-ray using cosmic-ray.toml (see docs/TESTING.md).

Write-Host ">> Running mutmut on openunderstand/oudb/api.py ..."
mutmut run            # exits non-zero when mutants survive; that's expected

Write-Host ">> Results summary:"
mutmut results

Write-Host ">> Generating HTML report (.\html\index.html):"
mutmut html

Write-Host ""
Write-Host "Mutation score = killed / (killed + survived)."
Write-Host "Inspect a surviving mutant with:  mutmut show <id>"
