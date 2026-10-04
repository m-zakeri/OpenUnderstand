# Architecture

## The pipeline

```
openunderstand.py          CLI and config
    ↓
oudb.api.create_db         create the SQLite file and its five tables
    ↓
oudb.fill.fill             seed 237 entity kinds and 106 reference kinds
    ↓
symbol_table.build         index every declaration in the project
    ↓
ounderstand.runner         workers parse and collect, the parent writes
    ↓
parsing_process.process_file
    ↓
  parse once  →  build 24 listeners  →  one shared walk  →  write, in order
    ↓
models.finalise_analysis   six project-wide passes (once, after all files)
```

`symbol_table.build()` runs first because a pass resolving a name declared in
another file cannot wait until that file is parsed -- see
[Resolving names across files](#resolving-names-across-files).

A file is parsed once and every pass walks that one tree. With the C++
accelerator parsing is about 3% of a build; the write layer is roughly half,
the passes' own handlers most of the rest. On the pure-Python runtime parsing
is around a third, so any profile has to say which engine it was taken on.

### Build and write are separate phases

Each pass runs twice. The first pass over the list *builds* a listener, all of
them share a single walk of the tree, and then the list runs again to *write*.
`ListenersAndParsers.phase` selects which half; `BOTH` is the pre-split
behaviour and the default.

The ordering rules are about the **writes**, not the walks. `modify_listener`
writes last because it resolves a variable the declaring passes must already
have written; moving every walk ahead of every write changed two rows in the
whole JSON benchmark.

**The write layer must never touch the parse tree.** It used to: the class and
interface property lookups walked the tree once per name asked. That is what
made the split possible, and what makes a worker able to collect for a file the
writer never parsed.

### Analysing in parallel

`runner(path, jobs=N)` collects in worker processes and writes in the parent.
The database is byte-identical at any worker count, because a worker never
writes -- the pool initializer even rebinds the models to a throwaway in-memory
database so a stray write cannot reach the real one, and results are consumed
in order, since an entity's parent is set by whichever file supplies one first.

Scaling stops at about four workers: the write half is serial.

### Re-analysing one file

`oudb.api.update_files(paths, source_root=...)` deletes each named file's
previous contribution, re-analyses it, and runs the same six project-wide
passes. It expands the list to every file that depends on one of them -- a file
depends on another when it references a type declared there -- because editing
a base class changes what its subclasses inherit.

Re-analysis has to reproduce a rebuild of the same source. Two things it needs:
`symbol_table.build()` caches each file's contribution and reparses only what
changed, and `purge_file()` keeps a demoted row's declaration position, which is
what tells two overloads of one long name apart.

## The three layers

**`analysis_passes/`** -- one ANTLR listener per reference kind. A listener's
only job is to collect dictionaries while walking. It never touches the
database. This is what makes a pass easy to test: walk it over a tree and
inspect the list.

**`ounderstand/project.py`** -- the write layer. `Project.addXxxRefs(...)` turns
those dictionaries into `EntityModel` and `ReferenceModel` rows, resolving
entity identity and kinds along the way.

**`oudb/`** -- the schema (`models.py`), the Understand-compatible query API
(`api.py`), and kind seeding (`fill.py`).

`ounderstand/listeners_and_parsers.py` is the glue: each `*_listener` method
builds a listener, walks it, and hands the result to the matching `Project`
method. Every one is wrapped in try/except and **logs failures instead of
raising** -- so a broken pass silently produces no references. If references are
missing, read the log file first.

## Data model

Four tables:

- `KindModel` -- the vocabulary. `_inv` links a forward reference kind to its
  inverse.
- `EntityModel` -- `_kind`, `_parent` (self-referencing), `_name`, `_longname`,
  `_value`, `_type`, `_contents`.
- `ReferenceModel` -- `_kind`, `_file`, `_line`, `_column`, `_ent`, `_scope`.
- `ProjectModel` -- one row: name, language, root, database path.

Every reference is written twice, forward and inverse, with `_ent` and
`_scope` swapped and the same file, line and column.

### Entity identity

Two rows are the same entity when they share a long name *and* a kind family
(type, method, variable, package, file). `EntityModel.get_or_create` enforces
this -- peewee's default keys on every field passed in, so two passes describing
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
package, and **refuse an ambiguous name rather than guess** -- a wrong
resolution silently misattributes every reference built on it. `resolve_type()`
exists because `resolve()` would let a variable named `value` compete with a
class named `Value`; a pass that knows it is in a type position wants only the
types. `declaring_type()` follows `extends` so that a call to an inherited
method lands on the class that declares it, which is what Understand reports.

Working out *what* a name is often needs the declared type of something else --
`x.p = v` names a field of `x`'s type. `analysis_passes/declared_types.py`
reads those off the parse tree. It is not a type checker: it answers only what
a declaration states, so `a.b.c` resolves `b` on `a`'s type and stops.

**Placeholders** cover what the index cannot. A pass that still cannot place a
name creates a placeholder entity, and `merge_placeholder_entities()` folds
each into the real entity after every file has been parsed -- but only when
exactly one project-wide candidate shares the simple name. More than one means
guessing, and a wrong merge is worse than a duplicate.

Note the failure mode this creates when a pass records a *bare* name: the merge
will happily fold it into the single project method that happens to share it.
`entry.getValue()` on a `java.util.Map.Entry` became a call to
`org.json.CDL.getValue` that way. A pass should qualify what it can and emit
nothing for what it cannot.

A *qualified* name outside the project is not a placeholder at all. Anything
rooted under `EXTERNAL_ROOTS` -- `java.`, `javax.` -- is fully qualified by
construction, however unresolved its kind looks, and the merge skips it.
Without that, `java.lang.Object.equals` was folded into
`org.json.JSONObject.Null.equals`, the only `equals` the project declares, and
the reference pointed at itself from both ends.

Most references leave the project, so refusing to name an external target is
expensive: 1,197 of TheAlgorithms' 1,416 missing calls were to `java.io`,
`java.util` and `java.lang`. `oudb/jdk_index.txt.gz` answers for those -- 3,957
public `java.*` and `javax.*` types with their modifiers, supertypes, public
fields, their methods' arities and each method's reference return type, read
through `oudb/jdk_index.py`.

It is **generated, not listed**: `scripts/gen_jdk_index.py` builds it from a
local JDK's runtime image in about seven seconds. It replaced five hand-written
tables of 208 entries between them, each added the day a benchmark tripped over
it, and every gap in those was a wrong reference. If coverage is short, add to
the generator; do not re-grow a table.

`relabel_nondynamic_calls()` runs next and splits `Java Call` into
`Call`/`Call Nondynamic` now that the callee's modifiers are known. A JDK
callee carries no modifiers here -- it was named from the receiver's type, not
parsed -- so its class being final is what settles it: nothing can override
`java.lang.String.length`.

`drop_nonvariable_deref_refs()` deletes a `Deref Partial` whose target is not a
variable: `a.b` is a partial dereference only when `a` is one, and in
`org.evosuite.runtime.sandbox.Sandbox.goingToExecuteSUT()` the `org` is a
package qualifier.

`drop_shadowed_use_refs()` follows. Understand reports exactly one reference
kind per position: `x` in `x.next()` is a `Use Deref Partial`, an assignment
target is a `Set`, `i++` is a `Modify` -- and in none of those cases does it
also report a plain `Use`. The use pass cannot know this, because it runs
before set/dotref/modify have written anything, so the plain `Use` is deleted
here wherever a more specific kind sits on the same position.

`drop_external_inverse_refs()` then removes an inverse hung on an entity the
project does not declare. Understand writes `Java Call` for a call to
`java.lang.String.trim` and no `Java Callby`, because there is no analysed
entity to hang it on. `drop_orphan_placeholders()` finishes, deleting a
placeholder no reference points at.

### One emitter for the sequence

All six live in `models.finalise_analysis()`, and every entry point calls it --
the CLI, the MCP server, the comparison harness and `update_files()`. There
used to be three copies of the list kept in step by a comment, and a fourth
caller that ran two of the six, which left an updated database holding rows a
rebuilt one does not.

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
4. Add it to the `listeners` list in `parsing_process.py`. **Order matters** --
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
`#memberDeclaration3`, `#blockStatement1`, ...). Those labels generate the context
classes every pass references.

**It parses Java 9-25, added onto the Java 8 grammar rather than swapped for
upstream's**, so a Java 8 file parses to exactly the tree it always did: 4,164
of the 4,165 benchmark files compare identical node by node, rule index
included, and the JSON and calculator_app databases are byte-identical before
and after. The exception is jfreechart's `module-info.java`, which used to fail.
A record parses as a second alternative of `classDeclaration` and a type
pattern as a `localVariableDeclaration`, so the passes handle both largely
unchanged; `CLAUDE.md` lists what Understand does with each construct.

Four rules keep it that way, and each came from something that broke:

* **Add, never reshape.** New syntax goes in new rules or new labelled
  alternatives. A rule that gains a *second* reference to something
  (`IDENTIFIER`, `typeList`, ...) turns its accessor into a list, and every
  `ctx.IDENTIFIER().getText()` on it breaks.
* **Define every new rule at the end of the file.** A rule's index is its
  position, and `set_setby` and `setinit_setinitby` compare `getRuleIndex()`
  against integers. Inserting rules mid-file broke `test_set_pass`.
* **Contextual keywords stay IDENTIFIER tokens**, matched by text in a semantic
  predicate, so `int record;` still parses and no token id moves
  (`metrics/line_of_code.py` compares raw token ids 109/110). Predicates are
  Python; `java8speedy/build.py` rewrites them for C++ and refuses any it
  cannot. Wrap a compound one in parentheses: the Python target writes
  `if not <predicate>:`.
* **A bare method must stay unparseable.** `metrics/context.py` parses a
  method's own source and wraps it in a class only when that fails. Java 25
  compact source files would make it succeed, so they are not supported;
  `tests/test_grammar_java25.py` guards it.

Prove a grammar change with the tree comparison (old and new generated parser
over every benchmark file) *and* the fingerprint: the first catches a changed
tree, only the second caught the rule-index dependency.

Upstream's current grammar targets Java 24, but it has only 27 labels and
different ones, so adopting it means rewriting every listener. Extending this
one is the cheaper path.

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
and `peewee`. `.github/workflows/parity.yml` proves it on every push -- build
the wheel, check the seed files ship and nothing leaks to top level, install
into a clean venv, then analyse Java and query the result.

## The comparison

The comparison is the test suite. It builds a database with each
tool from the same source and diffs them at three levels:

- **(a) raw SQLite** -- what the passes actually wrote, `api.py` out of the picture
- **(b) through `api.py`** -- what a user sees
- **(c) real Understand** -- ground truth

(a) vs (c) isolates analysis bugs. (a) vs (b) isolates API bugs. A database
fingerprint guards refactors: a change that should not alter output must
reproduce the baseline digest byte for byte.

It needs a licensed Understand install and is kept outside this
repository.
