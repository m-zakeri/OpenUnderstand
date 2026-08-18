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

Python 3.9+. On Linux x86_64 that wheel carries the C++ parse accelerator,
which is 7.8x faster at parsing and takes about 17% off a full analysis.
Everywhere else the pure-Python ANTLR runtime is used instead and everything
works the same, just slower -- both engines produce byte-identical databases.

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

Current agreement, over eleven Java systems and 174,260 Understand entities:

| | pooled | range across subjects |
| --- | ---: | :--- |
| Entities recovered -- recall | 0.935 | 0.49 -- 1.00 |
| -- precision | 0.943 | 0.84 -- 0.97 |
| References at the exact position -- recall | | 0.90 -- 0.98 |
| -- precision | | 0.62 -- 0.88 |

Three of the subjects, for comparison with earlier releases:

| | calculator_app | org.json | TheAlgorithms |
| --- | ---: | ---: | ---: |
| Java files | 8 | 85 | 228 |
| Reference recall / precision | 0.98 / 0.86 | 0.97 / 0.84 | 0.96 / 0.83 |

Both sides are scoped the same way: Understand indexes the whole Java library
whether or not a JDK is added to the project, and its dump keeps only entities
declared under the fixture root, so this project's placeholders for those same
names -- `java.lang.String`, `java.util.ArrayList` -- are excluded too.
Counting ours while its counterparts were dropped understated entity precision
by 5 to 14 points depending on the subject.

[docs/parity.md](https://m-zakeri.github.io/OpenUnderstand/parity/) has the per-kind breakdown.

The comparison is the specification: what the real tool outputs is what decides
whether a reference is right. Understand must be installed and licensed, so it
is not part of this repository -- ask if you want to run it.

`tests/` holds unit tests for the pass rules that comparison established. They
need no database and run in about a second each:

```bash
for t in tests/test_*.py; do .venv/bin/python -W ignore "$t"; done
```

## Use it from an assistant

An MCP server ships with the package:

```bash
pip install "openunderstand[mcp]"
```

```json
{"mcpServers": {"openunderstand": {"command": "openunderstand-mcp"}}}
```

Six tools (`analyze`, `open_database`, `list_entities`, `entity_references`,
`entity_metrics`, `list_kinds`), four resources exposing the kind vocabulary
and metric names, and three prompts (`review_class`, `complexity_hotspots`,
`trace_callers`) -- so an assistant can analyse a Java project and ask what
calls what, without knowing the schema. See [docs/mcp.md](https://m-zakeri.github.io/OpenUnderstand/mcp/).

## Use it from IntelliJ IDEA

`idea-plugin/` builds a **Java Metrics** tool window: analyse the open project,
sort by any metric, double-click to jump to the declaration, export CSV. It
runs the analysis in a Python subprocess and offers to install the package into
a private virtualenv when it cannot find one.

```bash
cd idea-plugin && gradle buildPlugin    # then install the zip from disk
```

See [docs/idea-plugin.md](https://m-zakeri.github.io/OpenUnderstand/idea-plugin/).

## What it does not do

- **Java 8 only.** The grammar predates records, sealed types, `var`, text
  blocks and `yield`.
- **No external resolution.** The JDK and third-party jars are not analysed, so
  `java.lang.String` exists but has no members.
- **Partial coverage.** 90 to 98% of Understand's references are reproduced at
  the exact position, at 62 to 88% precision. 46 of the 49 public API methods
  are implemented.
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
