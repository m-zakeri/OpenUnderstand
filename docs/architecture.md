# Architecture

## The pipeline

```
openunderstand.py          CLI and config
    ↓
oudb.api.create_db         create the SQLite file and its four tables
    ↓
oudb.fill.fill             seed 237 entity kinds and 106 reference kinds
    ↓
ounderstand.runner         one worker per .java file
    ↓
parsing_process.process_file
    ↓
  parse once  →  run ~25 listeners over that one tree, in order
    ↓
merge_placeholder_entities + relabel_nondynamic_calls   (once, after all files)
```

A file is parsed once. Every analysis pass then walks that same tree, so
parsing is a small fraction of the total cost — most of the time goes into the
passes and the database writes.

## The three layers

**`analysis_passes/`** — one ANTLR listener per reference kind. A listener's
only job is to collect dictionaries while walking. It never touches the
database. This is what makes a pass easy to test: walk it over a tree and
inspect the list.

**`ounderstand/project.py`** — the write layer. `Project.addXxxRefs(...)` turns
those dictionaries into `EntityModel` and `ReferenceModel` rows, resolving
entity identity and kinds along the way.

**`oudb/`** — the schema (`models.py`), the Understand-compatible query API
(`api.py`), and kind seeding (`fill.py`).

`ounderstand/listeners_and_parsers.py` is the glue: each `*_listener` method
builds a listener, walks it, and hands the result to the matching `Project`
method. Every one is wrapped in try/except and **logs failures instead of
raising** — so a broken pass silently produces no references. If references are
missing, read the log file first.

## Data model

Four tables:

- `KindModel` — the vocabulary. `_inv` links a forward reference kind to its
  inverse.
- `EntityModel` — `_kind`, `_parent` (self-referencing), `_name`, `_longname`,
  `_value`, `_type`, `_contents`.
- `ReferenceModel` — `_kind`, `_file`, `_line`, `_column`, `_ent`, `_scope`.
- `ProjectModel` — one row: name, language, root, database path.

Every reference is written twice, forward and inverse, with `_ent` and
`_scope` swapped and the same file, line and column.

### Entity identity

Two rows are the same entity when they share a long name *and* a kind family
(type, method, variable, package, file). `EntityModel.get_or_create` enforces
this — peewee's default keys on every field passed in, so two passes describing
the same class with different `_contents` would each get a row.

Kinds containing `Unknown` or `Unresolved` are **placeholders**. They match any
family, never displace a real kind, and are upgraded in place when a
better-informed pass arrives. That is what makes the result independent of the
order the passes run in.

### Resolving names across files

`process_file` sees one file, so a pass cannot resolve a name declared
elsewhere. Instead of a project-wide symbol table built up front, unresolved
names become placeholder entities, and `merge_placeholder_entities()` folds
each into the real entity after every file has been parsed — but only when
exactly one project-wide candidate shares the simple name. More than one means
guessing, and a wrong merge is worse than a duplicate.

`relabel_nondynamic_calls()` runs next and splits `Java Call` into
`Call`/`Call Nondynamic` now that the callee's modifiers are known.

### Kind ids

Kind ids are assigned by `AutoField` in the order `fill.py` reads the seed
files, so they are positions, not identities. **Always resolve a kind by name:**

```python
from openunderstand.oudb.models import kind_id
ReferenceModel.get_or_create(_kind=kind_id("Java Call"), ...)
```

The codebase used to hard-code 89 of these integers, which meant inserting one
line in a `.txt` file silently repointed them all.

## Adding an analysis pass

1. Write a `JavaParserLabeledListener` subclass in `analysis_passes/`. Collect
   dictionaries; do not touch the database.
2. Add an `addXxxRefs(ref_dicts, file_ent)` method to `Project` that writes both
   directions of the reference, at the same position, resolving kinds by name.
3. Add a `*_listener` method to `ListenersAndParsers` wiring the two together.
4. Add it to the `listeners` list in `parsing_process.py`. **Order matters** —
   later passes rely on entities earlier ones created.
5. Run `bash scripts/compare/run_all.sh --fixture calculator_app` and check that
   the new kind's row count moved toward Understand's.

## Adding a metric

1. Write a module in `metrics/` exposing `metric_name(ent_model)`.
2. Import it in `api.py` and add an `elif` branch to `Ent.metric()`.
3. Add the name to `Ent.metrics()`.
4. `python scripts/compare/06_dump_ou_api.py --fixture calculator_app` classifies
   every metric name by what it actually does — the new one should come back
   `value`, not `raises`.

## The grammar

`grammars/JavaParserLabeled.g4` is a fork of `antlr/grammars-v4`'s Java grammar
carrying **114 custom labelled alternatives** (`#classBodyDeclaration0`,
`#memberDeclaration3`, `#blockStatement1`, …). Those labels generate the context
classes every pass references.

It is **Java 8**: no records, sealed types, `var`, text blocks or `yield`.
Upstream's current grammar handles Java 21 and is backward-compatible with
Java 8 source, but it has only 27 labels and different ones — adopting it means
rewriting every listener. Treat a grammar swap as a project.

Regenerate after editing a `.g4` (the runtime pin in `requirements.txt` must
match the tool version):

```bash
java -jar antlr-4.13.2-complete.jar -Dlanguage=Python3 -o OUT grammars/JavaLexer.g4
java -jar antlr-4.13.2-complete.jar -Dlanguage=Python3 -lib OUT -o OUT grammars/JavaParserLabeled.g4
cp OUT/*.py OUT/*.interp OUT/*.tokens openunderstand/gen/javaLabeled/
```

## Parser backends

`config.ini`'s `engine_core` selects the parser: anything starting with `c`
uses the speedy-antlr C++ accelerator, anything else the pure-Python ANTLR
runtime. The accelerator is roughly 8× faster at parsing and falls back to
Python with one warning if it was never built. Build it with
`python openunderstand/gen/java8speedy/build.py`.

## Two path landmines

1. **`openunderstand/` must be on `sys.path`.** The generated parsers are
   imported as top-level `gen.javaLabeled...`, not `openunderstand.gen...`, so
   any entry point needs:
   ```python
   sys.path.append(os.path.join(os.getcwd(), "openunderstand"))
   ```

2. **`config.ini` is read from two places.** `start_parsing` reads `./config.ini`
   relative to the working directory, while `utils/utilities.py:setup_config`
   resolves to one directory *above* the repository root. If logger setup fails
   with a `KeyError` on `["Logging"]`, that second file is missing.

## The comparison harness

`scripts/compare/` is the test suite. It builds both databases from the same
source and diffs them at three levels:

- **(a) raw SQLite** — what the passes actually wrote, `api.py` out of the picture
- **(b) through `api.py`** — what a user sees
- **(c) real Understand** — ground truth

(a) vs (c) isolates analysis bugs. (a) vs (b) isolates API bugs. A database
fingerprint guards refactors: a change that should not alter output must
reproduce the baseline digest byte for byte.

```bash
bash scripts/compare/run_all.sh --fixture calculator_app   # ~1 minute
bash scripts/compare/run_all.sh --fixture JSON             # acceptance
```
