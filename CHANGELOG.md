# Changelog

## Unreleased

Reference and metric agreement with SciTools Understand 7.0.1217, measured on
the same source with the comparison harness. Precision and recall are for a
reference reproduced at the **exact** position — same kind, scope, entity, file,
line and column — with the dump's own normalisation applied to both sides.

| fixture | precision / recall, before | after |
| --- | ---: | ---: |
| org.json | 84% / 83% | **87% / 87%** |
| TheAlgorithms | 83% / 83% | **84% / 86%** |
| calculator_app | not measured this way | **89% / 92%** |

(The `report.md` headline is a different, looser measure — it ignores position
and so reads higher. Quote one or the other, never a mix.)

### New reference kinds

- **`Java Use Ptr` / `Java Useby Ptr`** — lambda expressions. Understand gives
  each lambda an entity of its own, kind `Java Method Lambda`, named
  `(lambda_expr_N)` and numbered within the enclosing method. 19 of 19 on
  TheAlgorithms, both directions.
- **`Java Importby` / `Java Importby Demand`** — static imports, recorded
  against the imported member with the importing file as the entity. Understand
  emits no `Java Import` for Java, so these are written one-directional via
  `"inverse_only": True`.
- **`Java Overrides` / `Java Overriddenby`** — 0 → 15 of 15 on org.json, 13 → 46
  of 47 on TheAlgorithms, at 100% precision on both.

### Corrected

- **A nested class was named for its package, not its outer class** —
  `ClassTypeData.get_long_name()` built `package + "." + IDENTIFIER`, so
  `Builder` inside `JSONPointer` was written as `org.json.Builder`, a second
  entity for a class already recorded as `org.json.JSONPointer.Builder`. Entity
  identity is (long name, kind family), so the two never merged. Each duplicate
  carried `ctx.getText()` as its contents — source with the whitespace removed —
  and any metric that reparsed one failed on input like
  `classBuilder{publicBuilder(){}`. 9 such entities on org.json, now 1; entity
  count 5196 → 5188 with references unchanged.
- **`Java Use Cast` was produced by two passes at once** — `use_variants` and
  `cast_cast_by` — so every cast got two rows and every `(int) x` got one
  Understand has no counterpart for. 74 rows against its 10, 6.8% precision.
  Now one emitter, primitives skipped, positioned on the type rather than the
  `(`, and casts to a type parameter resolved against the method or class that
  declares it. 100% / 100% on org.json.
- **Calls to the JDK are now resolved** — 1,197 of TheAlgorithms' 1,416 missing
  `Java Call` rows targeted `java.io`, `java.util` and `java.lang`. A receiver
  is a variable (`sb.append`), a type (`Arrays.sort`, a static call) or a field
  (`System.out.println`, which lands on the field's declared type); only the
  first was handled. Recall 37% → 64%, precision 59% → 91%.
- **`Java Call Nondynamic`** — a call on a final JDK class cannot dispatch
  virtually. Recall 35% → 81% on TheAlgorithms, 22% → 73% on org.json.
- **`Java Overrides` is signature-sensitive.** `MaxHeap.getElement(int)` does
  not override `Heap.getElement()`. Parameter *types* are compared, not counted:
  `SortAlgorithm` declares both `sort(T[])` and `sort(List<T>)`, and a
  signature map keyed by long name silently dropped the first.
- **`Java Use GenericArgument`** — a type argument now resolves as a type
  (`Comparable<Vertex>` had been resolving to the *constructor*
  `Others.Graph.Vertex.Vertex`), a type parameter's bound is scoped to the
  parameter itself, and the writer creates that entity rather than skipping the
  row because a later pass had not yet made it. Recall 53% → 97%.
- **`Java Create`** — anonymous class creation (`new ActionListener() { ... }`)
  is not a `Create`, and a type reached through one of several `import x.y.*`
  now resolves instead of falling back to a bare name. 99% / 99% on org.json.
- **Java's keyword literals are not entities.** `str.isidentifier()` is true for
  `true`, `false` and `null`, so `return true` pointed 114 references at an
  entity named `false`.
- **A JDK long name is no longer merged away.** `merge_placeholder_entities()`
  folds by simple name, so `java.lang.Object.equals` was absorbed into
  `org.json.JSONObject.Null.equals` — the only `equals` the project declares —
  and the reference then pointed at itself from both ends.
- **The contain pass no longer dies on default-package files.** It indexed
  `packageInfo[0]` unconditionally; the glue logs and swallows, so this looked
  like silence. 7 logged pass failures → 0.

### Metrics

- `CountCCViol`, `CountCCViolType`, `CCViolDensityCode` and `CCViolDensityLine`
  implemented — CodeCheck runs no rules here, so they report zero rather than
  raising.
- `CountDeclClass` counted `Java Define` for a package, which declares nothing;
  a package *contains*. It returned 0 for all 27 packages on TheAlgorithms.
  Also added to `_NOT_AGGREGATED`, without which `Ent.metric()` aggregates over
  the package's files before the metric's own branch can run.
- `PercentLackOfCohesion` reports 0 for a class with no instance state, as
  Understand does, rather than treating a static utility class as maximally
  incohesive.
- `CountOutput` 6% → 48% and `CountInput` 29% → 34%, both carried by the call
  resolution above.

### Resolution of external names

- **The JDK is now indexed rather than guessed at.**
  `scripts/gen_jdk_index.py` generates `oudb/jdk_index.txt.gz` (3,957 types,
  64 KB) from a local JDK; five hand-written tables of 208 entries are gone.
  Coverage went from 61 `java.lang` names to all of them, 114 simple-name
  mappings to 3,957, two known field types to 303 types' worth, seven
  overridable interfaces to 740, and 24 final classes to 663.
- **Type resolution follows javac's order** — explicit import, then scope and
  package, then `java.lang`, then on-demand imports. A uniquely-named project
  class in another package no longer shadows an imported JDK one.
- **A lone `import x.y.*` no longer types a lowercase name.** The variable
  `graph` was becoming `java.util.graph`, as a type parameter had become
  `java.util.E`.

### Also corrected

- `new X(...)` emits the constructor call Understand reports alongside the
  Create, and the constructor guard runs before the nondynamic modifiers test.
- `a.b` records two references: the receiver's `Use Deref Partial` and the
  member's `Java Use`, the latter previously absent — 1,513 references on
  TheAlgorithms, 490 of them `System.out`.
- `a[i]` is a `Use Deref Partial`, not a plain `Use`; this over-produced `Use`
  and under-produced `Deref Partial` by the same 700 rows.
- `Java Typed` keeps wildcard imports and handles for-each, catch clauses and
  type parameters; `Java Set` handles static and indexed assignment targets.
- Placeholder entities with no reference are dropped, as are Deref Partial
  references onto a package qualifier — `org` in `org.evosuite...`.
- `new int[n]` creates no entity, and only methods are split by declaration
  position, halving duplicate entity rows.
- `get_or_create` keeps a declared return type instead of discarding it, which
  is what `CountOutput`'s non-void clause reads.

### Known gaps

- `CountStmtExe` (56%), `CountLineCodeExe` (73%), `CountLineCodeDecl` (62%) —
  one family, one unsolved rule; the counts run in opposite directions.
- `Java Call` recall on org.json is 41%: a chained receiver (`f().g()`) or a
  project field chain is still refused rather than guessed at.
- Overrides of JDK *classes* (`java.awt.Window.paint` through `JFrame`) need a
  library class hierarchy this project does not have. `symbol_table`'s JDK
  tables cover the core language and collection contracts only, by design.

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
