# OpenUnderstand

An open-source implementation of the [SciTools Understand](https://scitools.com)
Python API for Java source code.

Understand analyses a codebase and lets you ask questions about it: which
methods call this one, what does this class contain, how complex is this
function. Its API is excellent and its analysis is closed — the database
format is proprietary and the API source is not published. OpenUnderstand
reimplements that API on top of an ANTLR4 Java parser and a SQLite database,
so the same scripts run without a licence.

The goal is that a script written against Understand runs unchanged here. Every
class name, method signature and kind name is Understand's, and every change is
measured against the real tool — see [Parity](parity.md) for how close it
currently is.

## Install

```bash
pip install openunderstand
```

Python 3.9 or newer. Extras: `[speedy]` for the C++ parser accelerator,
`[mcp]` for the MCP server, `[dev]` for the test and build tooling.

## Build a database

Point it at a directory of Java source. It walks the tree, parses every
`.java` file, and writes a `.udb` — a SQLite file, despite the name.

```bash
python openunderstand/ounderstand/openunderstand.py \
    -r /path/to/java/project \
    -dba /path/for/database \
    -dbn myproject.udb \
    -l /path/for/app.log
```

Or from Python, which is how [CodART](https://github.com/m-zakeri/CodART)
uses it:

```python
from openunderstand.ounderstand.openunderstand import start_parsing

start_parsing(
    repo_address="/path/to/java/project",
    db_address="/path/for/database",
    db_name="myproject.udb",
    engine_core="C++",          # or "Python"
    log_address="/path/for/app.log",
)
```

## Query it

```python
import openunderstand.ounderstand as und

db = und.open("/path/for/database/myproject.udb")

for cls in db.ents("Class"):
    print(cls.longname())
    for ref in cls.refs("Define", "Method"):
        print("   ", ref.ent().name(), "at line", ref.line())
```

The full surface is in the [API reference](api.md); the vocabulary of kind
names is in [Kinds](kinds.md).

## Check it against Understand

If you have Understand installed and licensed, the comparison harness builds
both databases from the same source and reports every difference:

```bash
bash scripts/fetch_benchmarks.sh JSON
bash scripts/compare/run_all.sh --fixture JSON
```

It writes a ranked defect report to `scripts/compare/out/JSON/report.md`. This
is the project's test suite: there are no unit tests, because the only
specification that matters is the real tool's output.

## Where to go next

| | |
| --- | --- |
| [API reference](api.md) | Every class and method, and what is not implemented |
| [Kinds](kinds.md) | The 237 entity and 106 reference kinds |
| [Architecture](architecture.md) | How a file becomes rows, and how to add a pass |
| [Parity](parity.md) | Current measured agreement with Understand |
| [MCP server](mcp.md) | Query your code from an assistant |
