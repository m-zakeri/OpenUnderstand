# OpenUnderstand

![OpenUnderstand Logo](https://raw.githubusercontent.com/m-zakeri/OpenUnderstand/master/docs/figs/OpenUnderstand_Logo.png)

An open-source implementation of the [SciTools Understand](https://scitools.com)
Python API, for Java.

Understand reads a codebase and lets you ask questions about it -- which methods
call this one, what does this class contain, how complex is this function. The
API is good. The analysis is closed: the database format is proprietary, the API
source is not published, and it needs a licence.

OpenUnderstand reimplements that API on top of an ANTLR4 Java parser and a
SQLite database, so the same scripts run without one.

```python
import openunderstand.ounderstand as und

db = und.open("myproject.udb")

for cls in db.ents("Class"):
    print(cls.longname())
    for ref in cls.refs("Define", "Method"):
        print("   ", ref.ent().name(), "at line", ref.line())
```

That is Understand's API, unchanged. Same class names, same method signatures,
same kind names.

## Install

```bash
pip install openunderstand
```

Python 3.9 to 3.14. On Linux x86_64, macOS arm64 and Windows x64 that wheel carries
the C++ parse accelerator, which is 7.8x faster at parsing and takes about a
third off a full analysis. Everywhere else the pure-Python ANTLR runtime is used
instead and everything works the same, just slower -- both engines produce
byte-identical databases.

Optional extras:

| Extra | For |
| --- | --- |
| `openunderstand[speedy]` | tools to build the C++ parser accelerator from source |
| `openunderstand[mcp]` | the MCP server, so an assistant can query your code |

From a checkout instead:

```bash
git clone https://github.com/m-zakeri/OpenUnderstand
cd OpenUnderstand
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
```

## Build a database

Point it at a directory of Java source:

```bash
python openunderstand/ounderstand/openunderstand.py \
    -r /path/to/java/project \
    -dba /path/for/database \
    -dbn myproject.udb \
    -l /path/for/app.log
```

| Flag | Meaning |
| --- | --- |
| `-r` | source directory to analyse |
| `-dba` | directory to write the database into |
| `-dbn` | database filename |
| `-e` | `C++` (fast) or `Python` parser backend |
| `-l` | log file |

Or from Python:

```python
from openunderstand.ounderstand.openunderstand import start_parsing

start_parsing(
    repo_address="/path/to/java/project",
    db_address="/path/for/database",
    db_name="myproject.udb",
    engine_core="C++",
    log_address="/path/for/app.log",
)
```

The result is a `.udb` file. Despite the name it is plain SQLite -- open it with
any SQLite tool if you want to poke at the rows directly.

## How correct is it?

Honestly measured, not claimed. Every release is compared against a licensed
SciTools Understand install on the same source, entity by entity, reference by
reference, metric by metric.

Current agreement, over thirteen Java systems: 2,370,698 of Understand's
references and 178,077 of its entities.

| | precision | recall | F1 |
| --- | ---: | ---: | ---: |
| References, pooled | 0.989 | 0.990 | 0.990 |
| References, lowest subject | 0.979 | 0.977 | 0.981 |
| Entities, pooled | 1.000 | 1.000 | 1.000 |

Every subject, every one of 77 reference kinds and every one of 120 entity
kinds scores at least 0.9 on precision, recall and F1, pooled and one subject
at a time. Entities match on kind and long name: 178,075 of Understand's
178,077 are found, with 8 extra.

Metrics are compared the same way: an entity's metric is a hit when it equals
Understand's value. All 62 metrics both tools compute score F1 0.9 or better
on every subject. Per subject, macro F1 runs 0.986 (jenetics) to 1.000
(calculator_app); org.json is 0.991. The lowest single metric is class coupling
(`CountClassCoupled`), at 0.900 on jenetics and 0.907 on ganttproject and
jhotdraw.

Three of the subjects, for comparison with earlier releases:

| | calculator_app | org.json | TheAlgorithms |
| --- | ---: | ---: | ---: |
| Understand references | 586 | 70,518 | 53,793 |
| Reference precision / recall | 1.000 / 1.000 | 0.997 / 0.998 | 0.979 / 0.986 |
| Metric macro F1 | 1.000 | 0.991 | 0.992 |

Understand's own rows are kept, including its references into the JDK: a call
to `java.lang.String.trim` is part of the answer. Both sides are scoped the
same way. Entities nothing in the project declares (JDK and library types,
placeholders) are set aside on our side unless Understand's dump names them
too. Seven files Understand 7.0 misparses (`case null, default ->`, a type
annotation after type parameters, `import module`) are set aside on both
sides.

[docs/parity.md](https://m-zakeri.github.io/OpenUnderstand/parity/) has the per-kind breakdown.

The comparison is the specification: what the real tool outputs is what decides
whether a reference is right. Understand must be installed and licensed, so it
is not part of this repository -- ask if you want to run it.

`tests/` holds unit tests for the pass rules that comparison established. They
need no database and run in about a second each:

```bash
for t in tests/test_*.py; do .venv/bin/python -W ignore "$t"; done
```

## Re-analysing after an edit

A full build is not the only way in. `update_files()` re-analyses the files you
name and every file that depends on them, deleting each one's previous
contribution first:

```python
from openunderstand.oudb import api

db = api.open("myproject.udb")
api.update_files(["/path/to/java/project/src/Foo.java"],
                 source_root="/path/to/java/project")
```

It reproduces what a rebuild of the same source would write, which is the point
-- an update that only ever adds leaves a renamed method in the database under
both names.

## How fast is it?

On the 85-file `org.json` benchmark, on one ordinary Linux machine:

| | OpenUnderstand | Understand |
| --- | ---: | ---: |
| Full analysis | 14.1s | 7.6s |
| Full analysis, 4 workers | 10.2s | -- |
| Re-analyse one changed file | 1.2s | 3.1s |

Understand is C++ over a purpose-built store, so a full build being within
about 1.4x of it is the interesting part -- and re-analysing after an edit,
which is what an editor integration actually does, is faster here, because it
does less work rather than doing the same work quickly.

Pass `jobs=` to `openunderstand.ounderstand.runner.runner()` for the parallel
build, or set `OU_JOBS`. Workers only parse and collect and one process writes,
so the database is byte-identical whatever the worker count -- which is also
why more than about four workers buys nothing.

## Use it from an assistant

An MCP server ships with the package:

```bash
pip install "openunderstand[mcp]"
```

```json
{"mcpServers": {"openunderstand": {"command": "openunderstand-mcp"}}}
```

Seven tools (`analyze`, `open_database`, `update`, `list_entities`,
`entity_references`, `entity_metrics`, `list_kinds`), four resources exposing the kind vocabulary
and metric names, and three prompts (`review_class`, `complexity_hotspots`,
`trace_callers`) -- so an assistant can analyse a Java project and ask what
calls what, without knowing the schema. See [docs/mcp.md](https://m-zakeri.github.io/OpenUnderstand/mcp/).

## Use it from IntelliJ IDEA

`idea-plugin/` builds a **Java Metrics** tool window: analyse the open project,
sort by any metric, browse the symbol table and any entity's references,
double-click to jump to the declaration, export CSV. It runs the analysis in a
Python subprocess, in a private virtualenv it builds and installs itself.

```bash
cd idea-plugin && gradle buildPlugin    # then install the zip from disk
```

See [docs/idea-plugin.md](https://m-zakeri.github.io/OpenUnderstand/idea-plugin/).

## What it does not do

- **Kotlin is analysed but not measured.** `.kt` and `.kts` files go into the same database under Java
  kinds (declarations, lambdas, calls, uses, supertypes, overrides, casts, and text metrics), but
  Understand itself has no Kotlin, so there is nothing to compare it with. It was checked by reading samples
  on kotlinx.coroutines and detekt. See [docs/kotlin.md](docs/kotlin.md) for what is and is not covered.

- **Java 9-25 is analysed, measured against Understand.** Records, sealed
  types and `permits`, pattern variables and record patterns, `var` (including
  lambda parameters), switch expressions, local enums and interfaces, and
  `module-info.java` are modelled the way Understand models them, checked on
  jenetics' incubator module and a hand-written probe. Java 25 compact source
  files (top-level methods) do not parse; `import module` parses but cannot be
  checked, because Understand 7.0 itself does not parse it.
- **No external analysis.** The JDK and third-party jars are not parsed. JDK
  types and members appear only where the project uses them, resolved from a
  generated index of the JDK's public signatures (GraalVM 21.0.2, the JDK
  Understand analyses against). A third-party class is a name and nothing
  more.
- **Close, not identical.** 97.7 to 100% of Understand's references are
  reproduced at the exact position, at 97.9 to 100% precision, depending on the
  subject. Class coupling is the weakest metric, at 0.900 to 1.000. Understand
  infers the types of implicit lambda parameters (`(a, b) -> ...`) and this
  project does not, which accounts for most of what is left. 46 of the 49
  public API methods are implemented.
- **Silence, not refusal, on what is missing.** The three unimplemented methods
  -- `Db.close`, `Db.lookup_uniquename`, `Violation.add_fixit_hint` -- return
  `None`. Querying a reference kind no pass emits returns an empty list, which
  reads exactly like an entity that has none. `NotImplementedError` is *not*
  raised anywhere in the query API, whatever this file used to say.

## Documentation

| | |
| --- | --- |
| [Getting started](https://m-zakeri.github.io/OpenUnderstand/) | install, build, query |
| [API reference](https://m-zakeri.github.io/OpenUnderstand/api/) | every class and method, and what is missing |
| [Kinds](https://m-zakeri.github.io/OpenUnderstand/kinds/) | the 237 entity and 106 reference kinds |
| [Architecture](https://m-zakeri.github.io/OpenUnderstand/architecture/) | how a file becomes rows; how to add a pass |
| [Parity](https://m-zakeri.github.io/OpenUnderstand/parity/) | measured agreement with Understand |
| [MCP server](https://m-zakeri.github.io/OpenUnderstand/mcp/) | query your code from an assistant |
| [IntelliJ IDEA plugin](https://m-zakeri.github.io/OpenUnderstand/idea-plugin/) | metrics in a tool window |

Published at
[m-zakeri.github.io/OpenUnderstand](https://m-zakeri.github.io/OpenUnderstand/).

## Contributing

Read [docs/architecture.md](https://m-zakeri.github.io/OpenUnderstand/architecture/) first -- particularly the rule
that kind ids are positions and must always be resolved by name.

Changes to the analysis are judged against Understand, not against opinion.
If you can run the comparison, report recall **and** precision before and
after -- a change that raises recall by tanking precision is not an
improvement. If you cannot, say what you expect to change and it will be
measured for you.

Pull requests target the `dev` branch.

## Credits

Started at the IUST Reverse Engineering Research Laboratory. Uses
[ANTLR4](https://www.antlr.org/), [peewee](http://docs.peewee-orm.com/), and a
labelled fork of the [grammars-v4](https://github.com/antlr/grammars-v4) Java
grammar.
