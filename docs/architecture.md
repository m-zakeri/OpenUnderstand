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
  parse once  →  run ~28 listeners over that one tree, in order
    ↓
merge_placeholder_entities + relabel_nondynamic_calls
+ drop_shadowed_use_refs                                (once, after all files)
```

Before any of that, `symbol_table.build()` indexes every declaration in the
project — see [Resolving names across files](#resolving-names-across-files).

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
elsewhere. Two mechanisms cover this, and they work from opposite ends.

**`ounderstand/symbol_table.py`** indexes every declaration in the project
*before* the passes run, so a pass can ask what a name means while it is still
deciding what to write:

```python
symbol_table.resolve(name, scope_longname)       # any declaration
symbol_table.resolve_type(name, scope_longname)  # classes/interfaces/enums only
symbol_table.declaring_type(type_longname, member)  # walks the extends chain
```

All three search the innermost scope outward, then the asking scope's own
package, and **refuse an ambiguous name rather than guess** — a wrong
resolution silently misattributes every reference built on it. `resolve_type()`
exists because `resolve()` would let a variable named `value` compete with a
class named `Value`; a pass that knows it is in a type position wants only the
types. `declaring_type()` follows `extends` so that a call to an inherited
method lands on the class that declares it, which is what Understand reports.

Working out *what* a name is often needs the declared type of something else —
`x.p = v` names a field of `x`'s type. `analysis_passes/declared_types.py`
reads those off the parse tree. It is not a type checker: it answers only what
a declaration states, so `a.b.c` resolves `b` on `a`'s type and stops.

**Placeholders** cover what the index cannot. A pass that still cannot place a
name creates a placeholder entity, and `merge_placeholder_entities()` folds
each into the real entity after every file has been parsed — but only when
exactly one project-wide candidate shares the simple name. More than one means
guessing, and a wrong merge is worse than a duplicate.

Note the failure mode this creates when a pass records a *bare* name: the merge
will happily fold it into the single project method that happens to share it.
`entry.getValue()` on a `java.util.Map.Entry` became a call to
`org.json.CDL.getValue` that way. A pass should qualify what it can and emit
nothing for what it cannot.

A *qualified* name outside the project is not a placeholder at all. Anything
rooted under `EXTERNAL_ROOTS` — `java.`, `javax.` — is fully qualified by
construction, however unresolved its kind looks, and the merge skips it.
Without that, `java.lang.Object.equals` was folded into
`org.json.JSONObject.Null.equals`, the only `equals` the project declares, and
the reference pointed at itself from both ends.

Most references leave the project, so refusing to name an external target is
expensive: 1,197 of TheAlgorithms' 1,416 missing calls were to `java.io`,
`java.util` and `java.lang`. `symbol_table` carries small hand-written tables
for this — `JAVA_LANG_TYPES`, `JDK_TYPE_PACKAGES`, `JDK_FIELD_TYPES`,
`JDK_OVERRIDABLE` and `models.JDK_FINAL_TYPES`. They are lookup tables covering
what the benchmarks use, not a model of the JDK, and each says so where it is
defined.

`relabel_nondynamic_calls()` runs next and splits `Java Call` into
`Call`/`Call Nondynamic` now that the callee's modifiers are known. A JDK
callee carries no modifiers here — it was named from the receiver's type, not
parsed — so its class being final is what settles it: nothing can override
`java.lang.String.length`.

`drop_shadowed_use_refs()` runs last. Understand reports exactly one reference
kind per position: `x` in `x.next()` is a `Use Deref Partial`, an assignment
target is a `Set`, `i++` is a `Modify` — and in none of those cases does it
also report a plain `Use`. The use pass cannot know this, because it runs
before set/dotref/modify have written anything, so the plain `Use` is deleted
here wherever a more specific kind sits on the same position.

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
5. Have the change measured against Understand: the new kind's row count
   should move toward Understand's without hurting precision.

## Adding a metric

1. Write a module in `metrics/` exposing `metric_name(ent_model)`.
2. Import it in `api.py` and add an `elif` branch to `Ent.metric()`.
3. Add the name to `Ent.metrics()`.
4. Check the metric against Understand's own value for the same entity, and
   read its definition in Understand's `metrics.pdf` first. Six metrics here
   were written from guesswork and every one of them was wrong.

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

## Packaging

The installed package is `openunderstand`; everything imports fully qualified
(`openunderstand.gen.javaLabeled...`). Two long-standing landmines are gone:

- Imports used to be top-level `gen.javaLabeled...`, so `openunderstand/` had
  to be on `sys.path` and the package could not be installed and used.
- `setup_config()` used to resolve `config.ini` one directory *above* the
  repository root and `KeyError` on a missing `[Logging]` section. It now
  falls back to defaults, so the library works with no configuration.

An installed wheel is expected to do the whole job with only `antlr4-runtime`
and `peewee`. `.github/workflows/parity.yml` proves it on every push — build
the wheel, check the seed files ship and nothing leaks to top level, install
into a clean venv, then analyse Java and query the result.

## The comparison harness

The comparison harness is the test suite. It builds a database with each
tool from the same source and diffs them at three levels:

- **(a) raw SQLite** — what the passes actually wrote, `api.py` out of the picture
- **(b) through `api.py`** — what a user sees
- **(c) real Understand** — ground truth

(a) vs (c) isolates analysis bugs. (a) vs (b) isolates API bugs. A database
fingerprint guards refactors: a change that should not alter output must
reproduce the baseline digest byte for byte.

The harness needs a licensed Understand install and is kept outside this
repository.
