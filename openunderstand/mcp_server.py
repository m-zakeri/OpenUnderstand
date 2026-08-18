"""An MCP server exposing OpenUnderstand's analysis over stdio.

Lets an assistant analyse a Java project and then ask structural questions
about it -- what calls this, what does this class declare, how complex is this
method -- without shelling out or knowing the database schema.

Run it directly:

    openunderstand-mcp

or register it with a client, e.g. in Claude Code's settings:

    {"mcpServers": {"openunderstand": {"command": "openunderstand-mcp"}}}

Requires the `mcp` extra:  pip install "openunderstand[mcp]"
"""

from __future__ import annotations

import contextlib
import io
import json
import os
from typing import Any

#: The database the tools operate on, set by `analyze` or `open_database`.
_STATE: dict[str, Any] = {"db": None, "path": None}


def _require_db():
    if _STATE["db"] is None:
        raise ValueError(
            "No database open. Call analyze(source_dir=...) to build one, or "
            "open_database(path=...) if you already have a .udb."
        )
    return _STATE["db"]


def _quiet(fn, *args, **kwargs):
    """Run a call with its prints swallowed.

    The analysis layer prints progress and pass failures to stdout, and stdout
    is the MCP transport -- anything written there corrupts the protocol.
    """
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
        result = fn(*args, **kwargs)
    return result, buffer.getvalue()


def analyze(source_dir: str, database: str = "") -> str:
    """Analyse a Java project and open the resulting database.

    source_dir: directory of Java source to analyse.
    database:   where to write the .udb (default: alongside the source).
    """
    from openunderstand.oudb.api import create_db, open as ou_open
    from openunderstand.oudb.fill import fill
    from openunderstand.ounderstand.parsing_process import process_file, get_files
    from openunderstand.ounderstand import symbol_table
    from openunderstand.oudb.models import (merge_placeholder_entities,
                                            relabel_nondynamic_calls)

    source_dir = os.path.abspath(os.path.expanduser(source_dir))
    if not os.path.isdir(source_dir):
        raise ValueError(f"not a directory: {source_dir}")
    out_dir = os.path.abspath(os.path.expanduser(database or source_dir))
    os.makedirs(out_dir, exist_ok=True)
    name = os.path.basename(source_dir.rstrip("/")) + ".udb"

    def run():
        create_db(dbname=name, project_dir=source_dir, db_path=out_dir)
        fill(udb_path=out_dir)
        symbol_table.build(source_dir)
        # get_files, not a local os.walk: an entity's _parent is set by
        # whichever file created it first, so the walk order decides it and
        # os.walk order is neither sorted nor stable across machines.
        files = get_files(source_dir)
        for path in files:
            process_file(path)
        merge_placeholder_entities()
        relabel_nondynamic_calls()
        return len(files), ou_open(os.path.join(out_dir, name))

    (count, db), _ = _quiet(run)
    _STATE["db"], _STATE["path"] = db, os.path.join(out_dir, name)
    return json.dumps({
        "database": _STATE["path"],
        "files_analyzed": count,
        "entities": len(db.ents()),
    }, indent=2)


def open_database(path: str) -> str:
    """Open an existing .udb database."""
    from openunderstand.oudb.api import open as ou_open

    path = os.path.abspath(os.path.expanduser(path))
    (db, _) = _quiet(ou_open, path)
    _STATE["db"], _STATE["path"] = db, path
    return json.dumps({"database": path, "entities": len(db.ents())}, indent=2)


def list_entities(kind: str = "", limit: int = 100) -> str:
    """Entities in the database, optionally filtered.

    kind: an Understand kind filter -- tokens are ANDed, "~" excludes, ","
          ors. "Class", "Method ~Static" and "Class,Interface" all work.
    """
    db = _require_db()
    (ents, _) = _quiet(db.ents, kind or None)
    rows = [{"longname": e.longname(), "kind": e.kindname()} for e in ents[:limit]]
    return json.dumps({"total": len(ents), "shown": len(rows), "entities": rows},
                      indent=2)


def entity_references(longname: str, reference_kind: str = "", limit: int = 100) -> str:
    """References whose scope is this entity.

    reference_kind: e.g. "Call", "Define", "Use". Same filter grammar as kind.
    """
    db = _require_db()
    (ents, _) = _quiet(db.ents)
    match = next((e for e in ents if e.longname() == longname), None)
    if match is None:
        raise ValueError(f"no entity with longname {longname!r}")
    (refs, _) = _quiet(match.refs, reference_kind or None)
    rows = []
    by_id = {e._id: e for e in ents}
    for ref in refs[:limit]:
        target = by_id.get(ref._ent)
        rows.append({
            "kind": ref.kindname(),
            "entity": target.longname() if target else None,
            "line": ref.line(),
            "column": ref.column(),
        })
    return json.dumps({"entity": longname, "total": len(refs),
                       "references": rows}, indent=2)


def entity_metrics(longname: str, metrics: list[str] | None = None) -> str:
    """Metric values for an entity. Omit `metrics` for every available name."""
    db = _require_db()
    (ents, _) = _quiet(db.ents)
    match = next((e for e in ents if e.longname() == longname), None)
    if match is None:
        raise ValueError(f"no entity with longname {longname!r}")
    names = metrics or match.metrics()
    values = {}
    for name in names:
        try:
            (result, _) = _quiet(match.metric, [name])
            if result.get(name) is not None:
                values[name] = result[name]
        except NotImplementedError:
            continue
    return json.dumps({"entity": longname, "kind": match.kindname(),
                       "metrics": values}, indent=2)


def list_kinds(kind_filter: str = "", references: bool = False) -> str:
    """The entity or reference kind vocabulary, taken from Understand."""
    from openunderstand.oudb.api import kind_matches
    from openunderstand.oudb.models import KindModel

    _require_db()
    (rows, _) = _quiet(lambda: [
        k._name for k in KindModel.select().where(
            KindModel.is_ent_kind == (not references))
        if kind_matches(k._name, kind_filter)
    ])
    return json.dumps({"count": len(rows), "kinds": sorted(rows)}, indent=2)


TOOLS = (analyze, open_database, list_entities, entity_references,
         entity_metrics, list_kinds)


# --------------------------------------------------------------------- resources
#
# Reference data the model should be able to read without spending a tool call.
# The kind vocabulary is the important one: every filter argument in this server
# is a kind string, and a wrong filter returns an empty list rather than an
# error -- so an assistant that has to guess fails silently.

def _kind_names(is_entity: bool) -> str:
    from openunderstand.oudb.models import KindModel

    if _STATE["db"] is None:
        return ("No database open. The kind vocabulary is seeded per database; "
                "call analyze() or open_database() first.")
    (rows, _) = _quiet(lambda: sorted(
        k._name for k in KindModel.select().where(
            KindModel.is_ent_kind == is_entity)))
    return "\n".join(rows)


def entity_kinds() -> str:
    """Every Java entity kind, one per line.

    Taken verbatim from SciTools Understand, so a name here means what it means
    there. Filter arguments match whole tokens of these names.
    """
    return _kind_names(True)


def reference_kinds() -> str:
    """Every Java reference kind, one per line.

    Each forward kind has an inverse: `Java Call`/`Java Callby`. Both directions
    of a reference sit at the same file, line and column.
    """
    return _kind_names(False)


def current_database() -> str:
    """What is open right now, and how big it is."""
    if _STATE["db"] is None:
        return json.dumps({"open": False}, indent=2)
    (ents, _) = _quiet(_STATE["db"].ents)
    return json.dumps({"open": True, "path": _STATE["path"],
                       "entities": len(ents)}, indent=2)


def metric_names() -> str:
    """Metric names this database can answer, one per line.

    Names not listed here return None; names listed but unimplemented raise.
    """
    db = _STATE["db"]
    if db is None:
        return "No database open."
    (ents, _) = _quiet(db.ents)
    if not ents:
        return "Database is empty."
    (names, _) = _quiet(ents[0].metrics)
    return "\n".join(names)


RESOURCES = (
    ("openunderstand://kinds/entity", "entity-kinds", entity_kinds),
    ("openunderstand://kinds/reference", "reference-kinds", reference_kinds),
    ("openunderstand://database", "current-database", current_database),
    ("openunderstand://metrics", "metric-names", metric_names),
)

# Resources a client that wires up only tools would otherwise never see.
#
# `metric_names` is the one that costs something to miss: `entity_metrics` takes
# these names and answers None for a name it does not know, so a client guessing
# at them fails silently rather than being told.
#
# `entity_kinds` and `reference_kinds` are deliberately absent -- the `list_kinds`
# tool already runs the same query with a filter on top, and a second way to ask
# the same question is surface without reach.
ALSO_TOOLS = (current_database, metric_names)


# ----------------------------------------------------------------------- prompts
#
# Workflows a user starts deliberately, as opposed to actions the model decides
# to take. Each one names the tools it needs so the model does not have to
# rediscover the sequence.
#
# Registered as tools as well, because a client that wires up only tools -- and
# many do -- cannot see a prompt at all, so these were invisible to it. They
# return their instructions either way; nothing about them changes with the
# surface they are reached through.

def review_class(longname: str) -> str:
    """Review one class: size, complexity, what it declares and couples to."""
    return (
        f"Review the Java class `{longname}`.\n\n"
        "1. entity_metrics on it for CountLine, CountDeclMethod, "
        "SumCyclomatic, MaxCyclomatic, CountClassCoupled and "
        "PercentLackOfCohesion.\n"
        "2. entity_references with reference_kind=\"Define\" to see what it "
        "declares.\n"
        "3. entity_references with reference_kind=\"Couple\" for what it "
        "depends on.\n\n"
        "Then say whether it is doing too much, where the complexity is "
        "concentrated, and what you would split out first. Quote the numbers "
        "you are reasoning from. If the metrics look unremarkable, say so "
        "rather than inventing a concern."
    )


def complexity_hotspots(limit: int = 10) -> str:
    """Find the most complex methods in the project."""
    return (
        f"Find the {limit} most complex methods in the open database.\n\n"
        "Use list_entities with kind=\"Method ~Unknown\", then entity_metrics "
        "on each for Cyclomatic, MaxNesting and CountLine. Rank by Cyclomatic "
        "and show the numbers in a table.\n\n"
        "For the worst few, read what they call with entity_references "
        "reference_kind=\"Call\" and suggest what to extract. Complexity alone "
        "is not a defect -- say which ones actually look worth changing."
    )


def trace_callers(longname: str) -> str:
    """Who calls this method, and who calls them."""
    return (
        f"Trace the callers of `{longname}`.\n\n"
        "entity_references with reference_kind=\"Callby\" gives the direct "
        "callers; repeat on each to go up a level or two.\n\n"
        "Present it as a tree. Note that this analysis resolves roughly half "
        "of Understand's references, so treat an empty result as 'none found' "
        "rather than 'none exist'."
    )


PROMPTS = (review_class, complexity_hotspots, trace_callers)


def build_server():
    """The configured MCP server, or a clear error if the SDK is missing."""
    try:
        # SDK 2.x. Older releases exposed the same thing as
        # mcp.server.fastmcp.FastMCP.
        from mcp.server import MCPServer
    except ImportError:  # pragma: no cover - depends on the installed SDK
        try:
            from mcp.server.fastmcp import FastMCP as MCPServer
        except ImportError:
            raise SystemExit(
                'The MCP server needs the "mcp" package:\n'
                '    pip install "openunderstand[mcp]"'
            )

    server = MCPServer(
        "openunderstand",
        instructions=(
            "Analyse Java source and query its structure. Call analyze() with a "
            "source directory first, or open_database() for an existing .udb; "
            "every other tool operates on whatever is open."
        ),
    )
    for tool in TOOLS + PROMPTS + ALSO_TOOLS:
        server.add_tool(tool, name=tool.__name__, description=tool.__doc__)
    for uri, name, reader in RESOURCES:
        server.resource(uri, name=name, description=reader.__doc__,
                        mime_type="text/plain" if name.endswith("kinds")
                        or name == "metric-names" else "application/json")(reader)
    for prompt in PROMPTS:
        server.prompt(name=prompt.__name__, description=prompt.__doc__)(prompt)
    return server


def main() -> int:
    build_server().run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
