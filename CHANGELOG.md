# Changelog

## 0.2.0

First release that can be installed from PyPI. **Databases built by earlier
versions are not readable by this one** — the kind vocabulary and the entity
schema both changed. Rebuild rather than upgrade in place.

### Correctness

Every change below was measured against SciTools Understand 7.0.1217 on the
same source. Agreement, before → after:

| | before | after |
| --- | ---: | ---: |
| Metric values matching Understand (calculator_app) | 34% | 80% |
| Metric values matching Understand (org.json) | — | 72% |
| References reproduced at the exact position (calculator_app) | 0.32 | 0.62 |
| References reproduced at the exact position (org.json) | 0.12 | 0.50 |
| Metrics raising `NotImplementedError` | 22 | 2 |

- **Kind vocabulary is now Understand's, verbatim** — 237 entity kinds and 106
  reference kinds generated from `Kind.list_entity/list_reference("Java")`,
  with forward/inverse pairs taken from `Kind.inv()`. Kinds resolve by name;
  the 89 hard-coded kind integers are gone, so the seed files are editable
  again.
- **Entity kinds are read from the declaration** — its modifiers, not a guess.
  Parameters, constructors and annotations were previously never created at
  all; 964 of 2626 entities on org.json claimed to be packages.
- **Overloads are distinct entities**, separated by declaration position, as
  Understand does it. `EntityModel` gained `_line` and `_column`.
- **New reference kinds**: Begin/End, project-wide Call/Callby, Use Deref
  Partial, Use Cast, Use Return, Use Annotation, Typed GenericArgument.
- **Reference positions corrected** — a reference and its inverse now sit at
  the same file, line and column, and `_file` is the file the reference occurs
  in. Columns are 1-based, as Understand reports them.
- **Metric definitions taken from the shipped `metrics.pdf`** rather than
  inferred. Six were wrong: `CountClassBase` counted transitively instead of
  immediately, `CountClassCoupled` counted base classes the manual excludes,
  `CountInput`/`CountOutput` ignored parameter and global access entirely.
- **`AvgLine*` renamed to `AvgCountLine*`** — the old names are not
  Understand's, so scripts asking for `AvgCountLine` got nothing.
- Entity source text is the real declaration, including its Javadoc, rather
  than whitespace-stripped token text. Every metric that reparsed contents was
  returning 0.

### API

- `Db.ents()` returns a list, not a set, and implements the full filter
  grammar (`~` excludes, `,` ors, tokens ANDed) — verified against the
  manual's own examples.
- `Db.lookup(name)` works without a kind string; it always returned `[]`.
- `Ent.refs()` and `Ent.ref()` work with no arguments; `Ent.ref()` returns a
  `Ref` rather than a list; `unique` keeps one reference per entity rather
  than truncating to one.
- `Kind.inv()` works. `Ent.metrics()` is deduplicated.
- `Ent.metric()` returns `None` for an unknown name, as documented.

### Incremental analysis

- `update_files(paths, source_root)` re-analyses only what changed, together
  with the files that depend on it — 1 file of 228 typically re-analyses 1.
  A file's previous contribution is deleted first, so renames and deletions no
  longer leave stale rows behind. A declaration that disappears but is still
  referenced elsewhere is demoted to an `Unknown` kind, matching Understand.
- `update_db(repo_path, branch)` resolves git paths correctly and uses it.

### Packaging

- **The package could not previously be installed and used**: it installed
  `oudb`, `gen`, `metrics` and `utils` at top level while every import said
  `openunderstand.oudb…`. Fixed, with `scripts/test_install.sh` to keep it
  fixed.
- Runtime dependencies are `antlr4-python3-runtime` and `peewee`. `pandas` and
  `GitPython` were imported at module scope for functions almost nobody calls;
  `pkg_resources` was imported and never used.
- Optional extras: `[speedy]`, `[metrics]`, `[mcp]`, `[dev]`.
- `setup_config()` no longer raises on a missing `config.ini`, and
  `setup_logger()` is memoized instead of adding a handler per call.

### MCP server

`openunderstand-mcp` (extra `[mcp]`) — six tools, four resources exposing the
kind vocabulary and metric names, three prompts.

### Tooling

- `scripts/compare/` builds a database with both tools from the same source
  and diffs entities, references and metric values, with a fingerprint guard
  for changes that should not alter output.
- `scripts/fetch_benchmarks.sh` for the three fixture tiers.
- `benchmark/` is no longer tracked (was 143 MB, 7522 files).

## 0.1.0

Never released to PyPI. Source-checkout use only.
