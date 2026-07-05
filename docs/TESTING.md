# Testing & Quality Engineering Guide

This document describes the test-engineering work added for Homework 3
(Industrial-Grade Unit Testing and CI/CD for OpenUnderstand) and how to run
every part locally.

- **Student ID:** 404131058
- **Branch:** `feature/testing-404131058`
- **Unit under test:** `openunderstand/oudb/api.py` — the public,
  Understand-compatible Python API (`Db`, `Ent`, `Kind`, `Ref`).
- **Kinds chosen (Part 3):** reference kinds `Java Call` / `Java Callby`
  (and `Define`/`Contain` families) plus the entity kinds needed to validate
  parent-child structure (`File → Class → Method → Parameter`).

## 1. Testing architecture

```
tests/
├── conftest.py            # isolation bootstrap + shared fixtures
├── test_kind.py           # entity & reference kinds, inverse references
├── test_ref.py            # reference objects (kind/ent/file/scope/line/col)
├── test_entity_and_db.py  # parent-child, unknown entities, db queries
├── _pynguin_support/
│   └── sitecustomize.py   # stubs the parser stack for Pynguin runs
└── generated/             # curated Pynguin output (Part 4)
```

### Isolation strategy (testing in isolation)
Importing `openunderstand.oudb.api` normally drags in the entire ANTLR/javalang
Java-parsing stack (`openunderstand.ounderstand.project` is imported by nearly
every metric module). That machinery is irrelevant to the database-backed
api/db layer and makes "unit" tests slow and brittle.

`tests/conftest.py` therefore registers lightweight stub modules in
`sys.modules` **before** importing the api, decoupling the unit under test from
its heavy collaborators. Every test then runs against a fresh **in-memory
SQLite** database (peewee `:memory:`), so tests are hermetic, fast, and order-
independent.

### Fixtures (in `conftest.py`)
| Fixture | Purpose |
|---|---|
| `db` | fresh in-memory SQLite bound to all models |
| `kinds` | entity + reference kinds, with inverse (`_inv`) wiring |
| `entities` | `File → Class → Method → Parameter` tree |
| `references` | a `Java Call` reference |
| `open_db` | an `api.Db` wired to the in-memory database |
| `make_kind` / `make_ent` / `make_ref` | wrap a model row as an api dataclass |

## 2. Environment setup (Part 1)

```bash
# main environment
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1          # Windows
# source .venv/bin/activate            # Linux/macOS
python -m pip install --upgrade pip
pip install -r requirements-dev.txt    # runtime + test tooling

# optional local hooks
pre-commit install
```

## 3. Running the suite & coverage (Parts 3 & 5)

```bash
# plain run
pytest tests -q

# with coverage + branch + reports (matches CI)
pytest tests \
  --cov=openunderstand.oudb.api \
  --cov=openunderstand.oudb.models \
  --cov-branch \
  --cov-report=term-missing \
  --cov-report=html \
  --cov-report=json
```
HTML report: `htmlcov/index.html`. Quality gates: **line ≥ 80%**,
**branch ≥ 70%** (enforced in CI from `coverage.json`).

## 4. Linting (Part 1 / Part 2 gate)

```bash
ruff check tests        # must report zero errors
ruff format tests       # auto-format
mypy tests              # optional static typing
```

## 5. CI/CD (Part 2)

`.github/workflows/ci.yml` runs on pushes to `feature/**`, `master`, `main`
and on PRs:

1. **lint** — `ruff check tests` (zero-error gate)
2. **test** — install deps, run pytest with branch coverage on Python
   3.10/3.11/3.12, then enforce the coverage gates from `coverage.json`
3. **reports/artifacts** — JUnit XML, Cobertura `coverage.xml`, `coverage.json`
   and the HTML report are uploaded as build artifacts; optional Codecov upload
4. **mutation** — opt-in job (manual `workflow_dispatch`) runs mutmut

Reproducibility: pinned `requirements-dev.txt`, pip caching, and
`PYTHONHASHSEED=0`.

## 6. Automated test generation — Pynguin (Part 4)

Pynguin lives in its **own** venv (it pins old dependencies):
```bash
py -3.12 -m venv .venv-pynguin
.\.venv-pynguin\Scripts\Activate.ps1
pip install "pynguin>=0.43.0"
pip install -r requirements.txt
.\scripts\run_pynguin.ps1     # or ./scripts/run_pynguin.sh
```
See `tests/generated/README.md` for the required curate→evaluate→refactor→
integrate workflow.

## 7. Mutation testing (Part 5)

```bash
.\scripts\run_mutation.ps1    # or ./scripts/run_mutation.sh
mutmut results
mutmut html                   # ./html/index.html
```
Mutation score = `killed / (killed + survived)`. If mutmut misbehaves on native
Windows, run it under WSL or use the Cosmic Ray config (`cosmic-ray.toml`).

## 8. Reproducible container (bonus)

```bash
docker build -t openunderstand-tests .
docker run --rm openunderstand-tests        # runs lint + tests + coverage gates
```

## 9. Fault reporting (Part 6)

See `docs/FAULTS.md` for ready-to-file GitHub issues. Two confirmed faults are
backed by `xfail` tests in the suite (`Kind.inv` TypeError; `Db.lookup` without
a kind filter).
