# Pynguin-generated tests (Part 4)

This folder holds tests produced by the [Pynguin](https://pynguin.readthedocs.io/)
automated test-generation framework. They **augment** the handcrafted suite in
`tests/`; they do not replace it.

## How these were generated

```bash
# Linux/macOS
./scripts/run_pynguin.sh
# Windows (PowerShell)
.\scripts\run_pynguin.ps1
```

Target module: `openunderstand.oudb.api`
Algorithm: DYNAMOSA (Pynguin default), fixed `--seed 42` for reproducibility.

The run scripts put `tests/_pynguin_support` on `PYTHONPATH`, whose
`sitecustomize.py` stubs the ANTLR/Java parser stack so Pynguin spends its search
budget on the api/db layer instead of the parser machinery.

## Required workflow for generated tests

Per the assignment, generated tests must be curated, not committed blindly:

1. **Evaluate usefulness** — keep tests that exercise real branches the manual
   suite missed (check the coverage delta before/after).
2. **Remove flaky / meaningless tests** — delete tests that depend on object
   identity, memory addresses, dict/set ordering, timestamps, or that assert on
   Pynguin's randomly generated junk values.
3. **Refactor for readability** — rename `test_case_0`/`var_0` to intention-
   revealing names, group related cases, and replace brittle assertions with
   meaningful ones.
4. **Integrate into CI** — once curated, these run automatically as part of
   `pytest tests` (this folder is under `tests/`), so the GitHub Actions
   pipeline picks them up with no extra configuration.

## Notes

- Generated tests that need a bound database will fail unless they use the
  shared fixtures in `tests/conftest.py`; prefer moving any kept test to rely on
  the `db` / `kinds` / `entities` fixtures.
- Keep this README; replace the rest of the folder with curated output.
