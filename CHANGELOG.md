# Changelog

## 0.3.1

### macOS arm64 and Windows x64 wheels

0.3.0 shipped the accelerator for Linux alone because the other two platforms
failed in CI and the cause was unknown. It was three separate faults stacked on
one another, each hidden by the one before it:

* cibuildwheel 2.21 pinned `packaging==24.1` through `PIP_CONSTRAINT`, and
  setuptools>=77 needs `packaging>=24.2` to canonicalise this project's SPDX
  `license` expression. The build died in `get_requires_for_build_wheel`,
  before `setup.py` ran at all. Fixed by naming the floor in
  `build-system.requires` and moving to cibuildwheel 2.23.
* ANTLR 4.13.2's `ProfilingATNSimulator.cpp` uses `std::chrono` without
  including `<chrono>`. It compiles wherever another header leaks it, which gcc
  and libc++ do and MSVC 19.51 does not. `build.py` now patches the extracted
  source.
* The ANTLR runtime defaults to `WITH_STATIC_CRT=On`, building `/MT`, while a
  CPython extension must be `/MD`. The compile succeeded and the link failed
  with 146 `LNK2038`s. Now configured `-DWITH_STATIC_CRT=OFF`.

Intel macOS is not coming back: GitHub has retired every Intel runner. Those
machines resolve to the sdist and the pure-Python parser.

## 0.3.0

### The C++ parse accelerator now ships compiled

`pip install openunderstand` gets it on Linux x86_64, for CPython 3.9 through
3.13. Until now it existed only for whoever ran
`openunderstand/gen/java8speedy/build.py` by hand with a JDK, cmake and a C++17
compiler on the machine, which in practice meant nobody: the published wheel
was `py3-none-any` and could not carry a compiled extension at all.

macOS and Windows wheels are not in this release. Both fail in CI inside
`python -m build` before reaching a compiler, and the cause is not yet known.
Those platforms install from the sdist and get the pure-Python parser, which is
what 0.2.4 gave them, so nothing regresses.

Measured on `benchmark/JSON`, 85 files, three runs back to back on an otherwise
idle machine:

| engine | total | fingerprint |
| --- | ---: | --- |
| C++ | 187.4s, 189.2s | `0a7d28a303441ba1` |
| Python | 225.8s | `0a7d28a303441ba1` |

37.5s, about 17%, with the two C++ runs agreeing within 1%. Parse-only over the
same files is 2.53s against 19.72s. The fingerprints are identical, which is
the whole point -- the accelerator changes how long the analysis takes and
nothing about what it produces.

`java8speedy/README.md` previously claimed "roughly 9%" and `CLAUDE.md` claimed
parsing was "only ~1% of runtime". Both are corrected. Measure this with
nothing else running: the same comparison taken under load reads 2.5%.

- **`engine_core` now defaults to `auto`** -- use the accelerator when the
  installed package has one, the pure-Python runtime when it does not. It
  defaulted to `Python`, which would have meant shipping compiled wheels that
  nobody ever used. An explicit `C++` or `Python` in `config.ini` still wins,
  and `C++` without a built extension still warns once and falls back.
- **`setup.py` is new** and does nothing but attach the extension. It probes
  for java, cmake and `speedy-antlr-tool` and declares no extension when any
  is missing, so installing the sdist on a machine with no toolchain still
  produces the working pure-Python package it always did.
  `OPENUNDERSTAND_BUILD_ACCELERATOR=1` turns a missing toolchain into a hard
  error instead, which is what CI sets so a silently pure wheel can never be
  published under a platform tag; `0` skips the extension even where it would
  build.
- **`build.py` builds through setuptools' compiler abstraction** rather than a
  hardcoded `g++` command line, which is what makes Windows a matrix entry
  rather than a port, and drives the ANTLR runtime with `cmake --build` rather
  than `make`. Two things that cost time and are now commented in place:
  the link needs `target_lang="c++"` or the extension compiles cleanly and
  imports with an undefined `__cxxabiv1` symbol, and the compile needs
  `ANTLR4CPP_STATIC` or the runtime headers declare `dllimport` on Windows.
- **`.github/workflows/wheels.yml` is new** and builds the matrix plus the
  sdist; `release.yml` calls it. Two guards on the publish set: no
  `py3-none-any` wheel may be present, because one on PyPI would shadow every
  binary wheel for the platforms it claims, and at least 15 wheels must have
  been produced.

There is no abi3 shortcut, which is why the matrix is that shape.
`speedy-antlr-tool` generates raw CPython C API code with no `Py_LIMITED_API`,
so a wheel is specific to one Python minor *and* one platform.

### The IDEA plugin upgrades itself to a compiled parser

The jar is one artifact for every platform and every Python, so it cannot
bundle a compiled wheel. It still bundles the `py3-none-any` one, which
guarantees a working first run with no network, and then best-effort runs
`pip install --only-binary=:all: openunderstand==<same version>` to swap in a
compiled wheel for whatever interpreter the venv ended up with. Every failure
path -- no network, no matching wheel, an unsupported Python -- leaves the
pure-Python parser in place, which is what happened before.

Gradle's `processResources` now takes `*-py3-none-any.whl` specifically. It
took `*.whl` and renamed the match to `openunderstand.whl`, which would have
collided the moment `dist/` held more than one wheel.

### Module names

Every module carrying a course-group suffix or a CamelCase filename was
renamed. The suffixes (`_g6`, `_g9`, `_g10_2`, `_g11`, `_G12`) recorded which
student group wrote a module and said nothing about what it does, and the
mixed casing meant `grep` for a pass needed two spellings. Nothing about the
analysis changed: the renames are import-only, and both fingerprints are
byte-identical to their baselines (calculator_app `30e18610cfd26ae7`, org.json
`0a7d28a303441ba1`), as is every metric value on both fixtures.

**This is a breaking change only for code importing these modules directly.**
The documented surface is untouched: `openunderstand.oudb.api`,
`start_parsing`, the `openunderstand` and `openunderstand-mcp` entry points,
and every metric and kind *name* keep their spelling. In particular the metric
strings `AvgCyclomatic`, `RatioCommentToCode` and `PercentLackOfCohesion` are
Understand's vocabulary, not module names, and did not move.

`analysis_passes/`:

| was | is |
| --- | --- |
| `DotRef_DorRefBy.py` | `dotref_dotrefby.py` |
| `Throws_ThrowsBy.py` | `throws_throwsby.py` |
| `callNonDynamic_callNonDynamicby.py` | `callnondynamic_callnondynamicby.py` |
| `cast_cast_by.py` | `cast_castby.py` |
| `contain_contain_by.py` | `contain_containby.py` |
| `couple_coupleby__G12.py` | `couple_coupleby.py` |
| `create_createby_g9.py` | `create_createby.py` |
| `entity_manager_g11.py` | `entity_manager.py` |
| `extend_listener_g6.py` | `extend_listener.py` |
| `g6_class_properties.py` | `class_properties_simple.py` |
| `import_demand_g9.py` | `import_demand.py` |
| `import_importby_g10_2.py` | `import_importby.py` |
| `package_entity_listener_g11.py` | `package_entity_listener.py` |
| `usemodule_usemoduleby_g11.py` | `usemodule_usemoduleby.py` |
| `variable_listener_g11.py` | `variable_listener.py` |

`metrics/`:

| was | is |
| --- | --- |
| `AvgCyclomatic.py` | `avg_cyclomatic.py` |
| `AvgCyclomaticModified.py` | `avg_cyclomatic_modified.py` |
| `AvgCyclomaticStrict.py` | `avg_cyclomatic_strict.py` |
| `AvgEssential.py` | `avg_essential.py` |
| `CyclomaticModified_G12.py` | `cyclomatic_modified.py` |
| `Cyclomatic_G12.py` | `cyclomatic_listener.py` |
| `CyclomaticStrict_G12.py` | `cyclomatic_strict_listener.py` |
| `Essential_G12.py` | `essential_listener.py` |
| `Lineofcode.py` | `line_of_code.py` |
| `MaxCalculator_G12.py` | `max_calculator.py` |
| `PercentLackOfCohesion.py` | `percent_lack_of_cohesion.py` |
| `PercentLackOfCohesionModified.py` | `percent_lack_of_cohesion_modified.py` |
| `RatioCommentToCode.py` | `ratio_comment_to_code.py` |
| `sumOfCyclomatics.py` | `sum_of_cyclomatics.py` |
| `utils_g10.py` | `utils.py` |

`ounderstand/override_overrideby__G12.py` became
`ounderstand/override_overrideby.py`.

Three of the metric modules could not take the obvious name because a
different, live module already holds it: `api.py` computes Cyclomatic,
CyclomaticStrict and Essential from `cyclomatic.py`, `cyclomatic_strict.py`
and `essential.py`, while `max_calculator.py` reaches for its own second
listener for each of the three. Those duplicates are what `_listener.py`
names. Making `max_calculator` use the live modules would delete three files
and free the names, but it changes what the Max* metrics answer, so it is not
part of a rename.

### Corrected

- **`start_parsing()` built a fraction of the database.** The documented
  programmatic entry point -- the one CodART uses -- ran `runner.py`'s `Pool`,
  and forked workers inherited the parent's already-open SQLite connection
  while each got its own copy of the process-local entity-identity cache.
  Writes were lost and duplicated with no exception raised, because
  `pool.map_async` without `.get()` discards whatever a worker raises.
  calculator_app committed **12 entities and 27 references against the correct
  90 and 578**, and was not even stable: the same files under `pool.map` gave
  43 and 208. JSON was worse: **1323 entities and 14920 references against
  5240 and 67794**, three quarters of the analysis discarded.
  `runner()` is sequential now, which is what
  `mcp_server.analyze()` and `scripts/compare` had always done for this
  reason, and `start_parsing()` reproduces the comparison harness's
  fingerprints byte for byte on both fixtures -- calculator_app
  `30e18610cfd26ae7` and org.json `0a7d28a303441ba1`, every digest and kind
  histogram equal.
- **The MCP server built a different database than the CLI.**
  `mcp_server.analyze()` ran only `merge_placeholder_entities()` and
  `relabel_nondynamic_calls()`, not the four `drop_*` passes that
  `start_parsing()` and `scripts/compare` also run, so the server -- and the
  IDEA plugin that reads it -- held rows the CLI deletes: plain `Java Use`
  references shadowed by a more specific variant, inverses hung on entities
  the project does not declare, and placeholders nothing resolved. On
  calculator_app that was **96 entities and 659 references against the correct
  90 and 578**, the surplus falling on `Java Use` (74 against 48), `Java
  Useby` (74 against 44), `Java Callby` (17 against 12), `Java Typedby`,
  `Java DotRefby` and `Java Useby Annotation`. All six passes run now, in the
  same order, and `analyze()` reproduces the harness fingerprint.
- **The file walk was unordered.** An entity's `_parent` is set by whichever
  file creates it first, so `get_files()`'s `os.listdir` order decided it and
  12 of calculator_app's 90 entities changed parent between walks.
  `get_files()` sorts now, and `mcp_server.analyze()` calls it instead of the
  third unsorted `os.walk` it carried.

### Removed

- **`metrics/G11_knots.py`** -- unreachable from the CLI, `oudb.api`, the MCP
  server, `scripts/` or `tests/`. `api.py` computes the knot metrics from
  `metrics/knots.py`.

## 0.2.3

Reference and metric agreement with SciTools Understand 7.0.1217, measured on
the same source with `scripts/compare`. Precision and recall are for a
reference reproduced at the **exact** position -- same kind, scope, entity, file,
line and column -- with the dump's own normalisation applied to both sides.

| fixture | precision / recall, before | after |
| --- | ---: | ---: |
| org.json | 84% / 83% | **87% / 87%** |
| TheAlgorithms | 83% / 83% | **84% / 86%** |
| calculator_app | not measured this way | **89% / 92%** |

(The `report.md` headline is a different, looser measure -- it ignores position
and so reads higher. Quote one or the other, never a mix.)

### New reference kinds

- **`Java Use Ptr` / `Java Useby Ptr`** -- lambda expressions. Understand gives
  each lambda an entity of its own, kind `Java Method Lambda`, named
  `(lambda_expr_N)` and numbered within the enclosing method. 19 of 19 on
  TheAlgorithms, both directions.
- **`Java Importby` / `Java Importby Demand`** -- static imports, recorded
  against the imported member with the importing file as the entity. Understand
  emits no `Java Import` for Java, so these are written one-directional via
  `"inverse_only": True`.
- **`Java Overrides` / `Java Overriddenby`** -- 0 → 15 of 15 on org.json, 13 → 46
  of 47 on TheAlgorithms, at 100% precision on both.

### Corrected

- **A nested class was named for its package, not its outer class** --
  `ClassTypeData.get_long_name()` built `package + "." + IDENTIFIER`, so
  `Builder` inside `JSONPointer` was written as `org.json.Builder`, a second
  entity for a class already recorded as `org.json.JSONPointer.Builder`. Entity
  identity is (long name, kind family), so the two never merged. Each duplicate
  carried `ctx.getText()` as its contents -- source with the whitespace removed --
  and any metric that reparsed one failed on input like
  `classBuilder{publicBuilder(){}`. 9 such entities on org.json, now 1; entity
  count 5196 → 5188 with references unchanged.
- **A `super.x()` call was scoped to its package, not its method** --
  `callNonDynamic_callNonDynamicby.dfs` names its parameters
  `(ctx, cls, context)` but is passed
  `(block, methodDeclaration, classDeclaration)`, so the scope's long name came
  from `findParents(classDeclaration)`, which excludes that context's own
  identifier and left the bare package. Each call site wrote a *class* entity
  named `org.json.junit.data` holding the method's whitespace-free `getText()`,
  and the 4 references scoped to it could not match Understand, which scopes a
  call to the calling method. Now `package.Class.method` with a Method kind, so
  entity identity binds it to the method `define_listener` already declared.
- **`Java Use Cast` was produced by two passes at once** -- `use_variants` and
  `cast_cast_by` -- so every cast got two rows and every `(int) x` got one
  Understand has no counterpart for. 74 rows against its 10, 6.8% precision.
  Now one emitter, primitives skipped, positioned on the type rather than the
  `(`, and casts to a type parameter resolved against the method or class that
  declares it. 100% / 100% on org.json.
- **Calls to the JDK are now resolved** -- 1,197 of TheAlgorithms' 1,416 missing
  `Java Call` rows targeted `java.io`, `java.util` and `java.lang`. A receiver
  is a variable (`sb.append`), a type (`Arrays.sort`, a static call) or a field
  (`System.out.println`, which lands on the field's declared type); only the
  first was handled. Recall 37% → 64%, precision 59% → 91%.
- **`Java Call Nondynamic`** -- a call on a final JDK class cannot dispatch
  virtually. Recall 35% → 81% on TheAlgorithms, 22% → 73% on org.json.
- **`Java Overrides` is signature-sensitive.** `MaxHeap.getElement(int)` does
  not override `Heap.getElement()`. Parameter *types* are compared, not counted:
  `SortAlgorithm` declares both `sort(T[])` and `sort(List<T>)`, and a
  signature map keyed by long name silently dropped the first.
- **`Java Use GenericArgument`** -- a type argument now resolves as a type
  (`Comparable<Vertex>` had been resolving to the *constructor*
  `Others.Graph.Vertex.Vertex`), a type parameter's bound is scoped to the
  parameter itself, and the writer creates that entity rather than skipping the
  row because a later pass had not yet made it. Recall 53% → 97%.
- **`Java Create`** -- anonymous class creation (`new ActionListener() { ... }`)
  is not a `Create`, and a type reached through one of several `import x.y.*`
  now resolves instead of falling back to a bare name. 99% / 99% on org.json.
- **Java's keyword literals are not entities.** `str.isidentifier()` is true for
  `true`, `false` and `null`, so `return true` pointed 114 references at an
  entity named `false`.
- **A JDK long name is no longer merged away.** `merge_placeholder_entities()`
  folds by simple name, so `java.lang.Object.equals` was absorbed into
  `org.json.JSONObject.Null.equals` -- the only `equals` the project declares --
  and the reference then pointed at itself from both ends.
- **The contain pass no longer dies on default-package files.** It indexed
  `packageInfo[0]` unconditionally; the glue logs and swallows, so this looked
  like silence. 7 logged pass failures → 0.

### Metrics

- `CountCCViol`, `CountCCViolType`, `CCViolDensityCode` and `CCViolDensityLine`
  implemented -- CodeCheck runs no rules here, so they report zero rather than
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

### Metrics measured against Understand's own definitions

`understand.Metric.description(name)` states each definition, and a candidate
formula can be scored over Understand's *own* database before it is written
here. That separates "we compute the wrong thing" from "our references are
incomplete", which the parity report alone cannot. Percentages below are exact
agreement on the JSON benchmark, excluding the 334 long names shared by
overloads -- our database merges those into one entity, so comparing them by
name is meaningless in either direction.

- **`CountDeclFile` 25% → 100%.** It queried `Java Define` scoped to the
  package. That pair puts the *file* on the ent side, so the query matched
  nothing and the metric returned 0 for every package. It is the package's own
  `Definein` refs, one per file carrying a `package p;`, which reproduces all 95
  of Understand's package values -- `org.json` 22, its parent `org` 0.
- **`CountInput` 58% → 75%.** It asked for `"Java Use"` alone, but
  `drop_shadowed_use_refs()` moves most reads onto `Use Deref Partial`, so
  nearly every parameter read was invisible. Understand's own `refs("Java Use")`
  is a prefix filter and hides the distinction; filtering by exact kind shows
  the plain kind scores 98.94% and the variants 99.23%. Also stopped counting
  `Java DotRef`, which is not a read, and recursive calls, which the definition
  excludes.
- **`PercentLackOfCohesionModified` 41% → 84%.** Never implemented: `api.py`
  routed it to the reparsing listener, and `graph_metrics` grew a `modified=`
  parameter that nothing passed and the body never read. The accessor allowance
  credits a method that reaches a field through a call to another method of the
  same class, closed to a fixed point -- 99% against Understand's own data,
  against 86% for direct use only.
- **`CountClassCoupled`**: the formula counted `Java Use` and `Java Typed`
  beside `Java Couple`. Couple alone matches 105 of Understand's 106 project
  classes; the wider query matches 23. The number here does not move, because
  a class's own scope carries almost no Use refs -- the remaining gap is
  `Java Couple` recall.
- **`CountDecl*` on packages.** The roll-up went package → *files*, and a file
  declares nothing, so `org.json` reported CountDeclMethod 0 against 505. These
  aggregate over the package's *classes*, walking Contain then Define to the end
  so anonymous classes count -- exact on all three JSON packages.
  `CountDeclClassVariable` 97% → 100%, `CountDeclMethodPrivate` 97% → 99%.
- **`CountLineCodeDecl` 34% → 99%, `CountLineCodeExe` 56% → 97%.** Every line of
  a declaration was declarative and only its first line executable, which is
  backwards for a string built by `+` over a hundred lines:
  `JSONMLTest.toJSONObjectToJSONArray` was 174 / 18 against Understand's 18 /
  175. The declarative half ends at the `=`; the initialiser's lines execute; an
  array initialiser is the exception, declarative throughout with only its
  element lines executing. Annotation lines are declarative and hang off the
  enclosing `classBodyDeclaration`. A statement owns every line it spans, and a
  compound statement owns its header plus the line each of `else`, `catch`,
  `finally`, a do-while's `while` and every `case` opens on -- never a line
  holding nothing but `}`. An anonymous class declares nothing for the method
  holding it, though its declarations still count as declarative *statements*.
- **`Knots` 74% → 89%, `CyclomaticModified` 68% → 97%, `CyclomaticStrict` 67% →
  96%, `Essential` 93%.** These reparsed with `context.parse` rather than
  `context.parse_entity`. A method is not a compilation unit, so the listener
  received an error-recovery tree: Knots counted 0 for every method, and
  `ClassDeclarationContext.IDENTIFIER()` was None, which made the two Cyclomatic
  metrics *raise* on 17 entities each. `Essential` also indexed an empty stack
  for a jump outside any `if`, where its five sibling handlers all guard.
- **A metric that throws reads as one that is missing.** Every caller wraps
  `Ent.metric()` in try/except, so the comparison skipped those entities silently
  and scored the rest; three metrics had been crashing for the whole life of the
  comparison without appearing as a finding. The same sweep found
  `cyclomatic_modified` returning `listener.method_count_Cyclomatic` *after*
  `exitMethodDeclaration` had filed the real count and reset it, so it answered
  1 for every method -- and scored 68%, exactly the share of methods whose
  answer is 1.
- Removed four stray `print` calls from the metric listeners. stdout is the MCP
  server's transport, and they were also polluting `scripts/idea_metrics.py`.
- `Ent.metrics()` reports 67 names; Understand values 62 of them on JSON.
  `CountPath` and `CountPathLog` still raise `NotImplementedError`, and
  `CountDeclFunction`, `CountDeclExecutableUnit` and the three
  `CountDeclInstanceVariable{Private,Protected,Public}` have no Understand value
  to compare against.

### Chained call receivers

- **`f(x).g()` resolves through the callee's return type.** `owner_longname`
  refused any receiver whose tail was not a plain identifier, so every chained
  call was dropped: Understand reports 13 calls in `JSONArrayTest.opt` the pass
  could not place, 11 of them this shape. `Double.valueOf(x).isNaN()` now lands
  on `java.lang.Double`, and the chain repeats -- `sb.append("a").append("b")`.
  A chain through a *project* method stays unresolved, because the index covers
  `java.`/`javax.` only and a wrong target is worse than a missing one.
  Measured on JSON: **+188 exact matches, none lost**.
- `scripts/gen_jdk_index.py` records each method's return type where it is a
  reference type -- a primitive, `void`, an array or a type variable cannot be
  a receiver and is not stored. 11,166 methods carry one; the file grows from
  126 KB to 155 KB.
- The generator's method pattern required `);` and so skipped every method
  declaring a `throws` clause. `Double.valueOf(String)` was indexed only because
  the `(double)` overload happens not to throw. 3,587 method names across the
  index were missing entirely.
- **P4 cannot see any of this.** `07_diff.py` drops Understand's `external`
  references -- 11,962 of JSON's 70,518 -- and every call into the JDK is one,
  so those rows can only land in `ou_only`. The same comparison without that
  filter is what the +188 above is measured on. Both numbers are recorded with the
  comparison scripts.

### Resolution of external names

- **The JDK is now indexed rather than guessed at.**
  `scripts/gen_jdk_index.py` generates `oudb/jdk_index.txt.gz` (3,957 types,
  64 KB) from a local JDK; five hand-written tables of 208 entries are gone.
  Coverage went from 61 `java.lang` names to all of them, 114 simple-name
  mappings to 3,957, two known field types to 303 types' worth, seven
  overridable interfaces to 740, and 24 final classes to 663.
- **Type resolution follows javac's order** -- explicit import, then scope and
  package, then `java.lang`, then on-demand imports. A uniquely-named project
  class in another package no longer shadows an imported JDK one.
- **A lone `import x.y.*` no longer types a lowercase name.** The variable
  `graph` was becoming `java.util.graph`, as a type parameter had become
  `java.util.E`.

### Also corrected

- `new X(...)` emits the constructor call Understand reports alongside the
  Create, and the constructor guard runs before the nondynamic modifiers test.
- `a.b` records two references: the receiver's `Use Deref Partial` and the
  member's `Java Use`, the latter previously absent -- 1,513 references on
  TheAlgorithms, 490 of them `System.out`.
- `a[i]` is a `Use Deref Partial`, not a plain `Use`; this over-produced `Use`
  and under-produced `Deref Partial` by the same 700 rows.
- `Java Typed` keeps wildcard imports and handles for-each, catch clauses and
  type parameters; `Java Set` handles static and indexed assignment targets.
- Placeholder entities with no reference are dropped, as are Deref Partial
  references onto a package qualifier -- `org` in `org.evosuite...`.
- `new int[n]` creates no entity, and only methods are split by declaration
  position, halving duplicate entity rows.
- `get_or_create` keeps a declared return type instead of discarding it, which
  is what `CountOutput`'s non-void clause reads.

### Performance

JSON builds in **58s rather than 127s**, with an identical fingerprint at every
step. Measured per phase on `JSONObject.java`, not under cProfile -- its
overhead roughly trebles the numbers and made the write layer look like 72% of
the run when it was 50%.

- **A reference is written without first asking whether it exists** --
  peewee's `get_or_create` issues a SELECT keyed on every field and then an
  INSERT, and that SELECT was 50% of `process_file` on JSONObject.java: 4.4s of
  8.8s across 8624 calls. One process writes the database, so the set of keys
  it has already written answers the question itself. A key that has been seen
  still falls through to the original path, so a genuine duplicate resolves to
  the existing row; the set is seeded from the database on first use and
  rebuilt when a different one is bound, which keeps both an incremental run
  and two analyses in one process correct.
- **`getClassProperties()` is memoized per file** -- it answers by walking the
  whole parse tree, and the create pass alone asked it 168 times for
  `JSONObject.java`, 13.5s of that file's 44s. The answer depends only on the
  long name and the tree, and the tree is fixed while a file is processed. JSON
  builds in 93s rather than 127s, with an identical fingerprint.
- **`runner.py`'s `Pool` is still not used**, and should not be. Entity
  identity is enforced in Python rather than by a database constraint, so
  concurrent workers each miss the same SELECT and both INSERT: 5606 entities
  against the sequential 5186, and 85113 references against 73363, to save 71
  seconds. Correct parallelism needs workers that only collect and a parent
  that writes.

### Known gaps

- `CountStmtExe` (56%), `CountLineCodeExe` (73%), `CountLineCodeDecl` (62%) --
  one family, one unsolved rule; the counts run in opposite directions.
- `Java Call` recall on org.json is 41%: a chained receiver (`f().g()`) or a
  project field chain is still refused rather than guessed at.
- Overrides of JDK *classes* (`java.awt.Window.paint` through `JFrame`) need a
  library class hierarchy this project does not have. `symbol_table`'s JDK
  tables cover the core language and collection contracts only, by design.

## 0.2.0

First release that can be installed from PyPI. **Databases built by earlier
versions are not readable by this one** -- the kind vocabulary and the entity
schema both changed. Rebuild rather than upgrade in place.

### Correctness

Every change below was measured against SciTools Understand 7.0.1217 on the
same source. Agreement, before → after:

| | before | after |
| --- | ---: | ---: |
| Metric values matching Understand (calculator_app) | 34% | 80% |
| Metric values matching Understand (org.json) | -- | 72% |
| References reproduced at the exact position (calculator_app) | 0.32 | 0.62 |
| References reproduced at the exact position (org.json) | 0.12 | 0.50 |
| Metrics raising `NotImplementedError` | 22 | 2 |

- **Kind vocabulary is now Understand's, verbatim** -- 237 entity kinds and 106
  reference kinds generated from `Kind.list_entity/list_reference("Java")`,
  with forward/inverse pairs taken from `Kind.inv()`. Kinds resolve by name;
  the 89 hard-coded kind integers are gone, so the seed files are editable
  again.
- **Entity kinds are read from the declaration** -- its modifiers, not a guess.
  Parameters, constructors and annotations were previously never created at
  all; 964 of 2626 entities on org.json claimed to be packages.
- **Overloads are distinct entities**, separated by declaration position, as
  Understand does it. `EntityModel` gained `_line` and `_column`.
- **New reference kinds**: Begin/End, project-wide Call/Callby, Use Deref
  Partial, Use Cast, Use Return, Use Annotation, Typed GenericArgument.
- **Reference positions corrected** -- a reference and its inverse now sit at
  the same file, line and column, and `_file` is the file the reference occurs
  in. Columns are 1-based, as Understand reports them.
- **Metric definitions taken from the shipped `metrics.pdf`** rather than
  inferred. Six were wrong: `CountClassBase` counted transitively instead of
  immediately, `CountClassCoupled` counted base classes the manual excludes,
  `CountInput`/`CountOutput` ignored parameter and global access entirely.
- **`AvgLine*` renamed to `AvgCountLine*`** -- the old names are not
  Understand's, so scripts asking for `AvgCountLine` got nothing.
- Entity source text is the real declaration, including its Javadoc, rather
  than whitespace-stripped token text. Every metric that reparsed contents was
  returning 0.

### API

- `Db.ents()` returns a list, not a set, and implements the full filter
  grammar (`~` excludes, `,` ors, tokens ANDed) -- verified against the
  manual's own examples.
- `Db.lookup(name)` works without a kind string; it always returned `[]`.
- `Ent.refs()` and `Ent.ref()` work with no arguments; `Ent.ref()` returns a
  `Ref` rather than a list; `unique` keeps one reference per entity rather
  than truncating to one.
- `Kind.inv()` works. `Ent.metrics()` is deduplicated.
- `Ent.metric()` returns `None` for an unknown name, as documented.

### Incremental analysis

- `update_files(paths, source_root)` re-analyses only what changed, together
  with the files that depend on it -- 1 file of 228 typically re-analyses 1.
  A file's previous contribution is deleted first, so renames and deletions no
  longer leave stale rows behind. A declaration that disappears but is still
  referenced elsewhere is demoted to an `Unknown` kind, matching Understand.
- `update_db(repo_path, branch)` resolves git paths correctly and uses it.

### Packaging

- **The package could not previously be installed and used**: it installed
  `oudb`, `gen`, `metrics` and `utils` at top level while every import said
  `openunderstand.oudb...`. Fixed, with `scripts/test_install.sh` to keep it
  fixed.
- Runtime dependencies are `antlr4-python3-runtime` and `peewee`. `pandas` and
  `GitPython` were imported at module scope for functions almost nobody calls;
  `pkg_resources` was imported and never used.
- Optional extras: `[speedy]`, `[metrics]`, `[mcp]`, `[dev]`.
- `setup_config()` no longer raises on a missing `config.ini`, and
  `setup_logger()` is memoized instead of adding a handler per call.

### MCP server

`openunderstand-mcp` (extra `[mcp]`) -- six tools, four resources exposing the
kind vocabulary and metric names, three prompts.

### Tooling

- `scripts/compare/` builds a database with both tools from the same source
  and diffs entities, references and metric values, with a fingerprint guard
  for changes that should not alter output.
- `scripts/fetch_benchmarks.sh` for the three fixture tiers.
- `benchmark/` is no longer tracked (was 143 MB, 7522 files).

## 0.1.0

Never released to PyPI. Source-checkout use only.
