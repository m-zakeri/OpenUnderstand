# Pynguin-generated tests (Part 4)

This folder holds **curated** tests produced by the
[Pynguin](https://pynguin.readthedocs.io/) automated test-generation framework.
They **augment** the handcrafted suite in `tests/unit/`; they do not replace it.

| | |
|---|---|
| Curated tests (collected by CI) | `test_api_pynguin_curated.py` — 5 tests |
| Raw, unedited Pynguin output | `../../pynguin-report/generated-raw-output.py.txt` — 14 cases |
| Tool configuration actually used | `../../pynguin-report/pynguin-cli-params.txt` |
| Full write-up | `docs/REPORT.md` §4 |

The raw output is kept **outside** `tests/` on purpose so pytest does not
collect it — it is evidence of the run, not a deliverable.

## How these were generated

```bash
# Linux/macOS
./scripts/run_pynguin.sh
# Windows (PowerShell)
.\scripts\run_pynguin.ps1
```

Target module: `openunderstand.oudb.api`
Pynguin 0.45.0, DYNAMOSA, `--seed 42` (reproducibility),
`--assertion-generation MUTATION_ANALYSIS`.

The run scripts put `tests/_pynguin_support` on `PYTHONPATH`, whose
`sitecustomize.py` stubs the ANTLR/Java parser stack **and GitPython** so
Pynguin spends its search budget on the api/db layer. Stubbing `git` is not
cosmetic — without it `dill` fails to reconstruct GitPython's deprecated
`Iterable` metaclass and the worker dies with
`NameError: name 'IterableClassWatcher' is not defined`. See `docs/REPORT.md`
§4.1.

## Curation workflow (what was actually done)

Generated tests are raw material, not deliverables. Per the assignment:

1. **Evaluate usefulness.** Measured the coverage delta:

   | Suite | Line | Branch |
   |---|---|---|
   | Manual only | 97.39 % | 95.45 % |
   | Generated only | 57.44 % | 9.09 % |
   | Combined | 97.39 % | 95.45 % |

   Zero delta — the generated tests reach nothing the manual suite missed.

2. **Remove flaky / meaningless tests.** Deleted: the 17 module-constant
   assertions Pynguin appends to every test; five tests that called a method
   with no assertion at all; four duplicates of existing `tests/unit/` cases;
   and one test that called `create_db()` and **wrote a SQLite file to the
   working directory**.

3. **Refactor for readability.** Renamed `test_case_N` to intention-revealing
   names, gave `var_0`/`str_0`/`int_0` meaning, and added the assertions
   Pynguin could not infer.

4. **Integrate into CI.** This folder is under `tests/`, so
   `pytest tests` picks the curated file up with no extra configuration.

## Notes

- Generated tests that need a bound database will fail unless they use the
  shared fixtures in `tests/conftest.py`; prefer moving any kept test to rely on
  the `db` / `kinds` / `entities` fixtures.
- Re-running the generator overwrites `test_openunderstand_oudb_api.py` in this
  folder. Move it to `pynguin-report/` and re-curate rather than committing raw
  output.
