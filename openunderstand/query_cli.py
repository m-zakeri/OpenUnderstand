"""Query an OpenUnderstand database from the shell, one line per fact.

    openunderstand-query refs  org.json.JSONPointer.queryFrom Callby
    openunderstand-query metrics JSONWriter.append Cyclomatic
    openunderstand-query ents "Class ~Unknown"
    openunderstand-query update src/main/java/org/json/JSONWriter.java

The same lookups as the MCP server, for an agent that already has a shell:
it composes with grep in one command and needs no tool schema loaded. The
database is found as the server finds it (--db, $OPENUNDERSTAND_DB, or the
one .udb in the working directory or its .openunderstand/ folder).
"""

import argparse
import json
import os
import sys

from openunderstand import mcp_server as server


def _rel(path):
    try:
        rel = os.path.relpath(path)
        return path if rel.startswith("..") else rel
    except ValueError:
        return path


def _kind(name):
    return name[5:] if name.startswith("Java ") else name


def refs(args):
    got = json.loads(server.entity_references(args.name, args.kind, args.limit))
    print(f"{got['entity']}: {got['total']} refs"
          + (f", {got['overloads']} overloads" if got["overloads"] > 1 else ""))
    for r in got["references"]:
        at = f"  (overload at line {r['declared_at']})" if "declared_at" in r else ""
        print(f"{_kind(r['kind'])}\t{r['entity']}\t{_rel(r['file'])}:{r['line']}{at}")


def metrics(args):
    got = json.loads(server.entity_metrics(args.name, args.metric or None))
    for entry in got.get("overloads") or [got]:
        line = f"  (overload at line {entry['declared_at']})" if "declared_at" in entry else ""
        values = " ".join(f"{k}={v}" for k, v in entry["metrics"].items())
        print(f"{got['entity']}{line}: {values}")


def ents(args):
    got = json.loads(server.list_entities(args.kind, args.limit))
    print(f"{got['total']} entities, {got['shown']} shown")
    for e in got["entities"]:
        where = f"\t{_rel(e['file'])}:{e['line']}" if e.get("file") else ""
        print(f"{_kind(e['kind'])}\t{e['longname']}{where}")


def update(args):
    got = json.loads(server.update(args.files))
    print(f"reanalysed {got['reanalysed']} file(s) for {got['requested']} requested")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="openunderstand-query", description=__doc__.split("\n\n")[0])
    ap.add_argument("--db", help="the .udb to query (default: discovered)")
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("refs", help="references whose scope is NAME (Callby = callers, Call = callees)")
    p.add_argument("name")
    p.add_argument("kind", nargs="?", default="")
    p.add_argument("--limit", type=int, default=200)
    p.set_defaults(run=refs)
    p = sub.add_parser("metrics", help="metric values for NAME (all if none named)")
    p.add_argument("name")
    p.add_argument("metric", nargs="*")
    p.set_defaults(run=metrics)
    p = sub.add_parser("ents", help="entities of a kind (Understand filter grammar)")
    p.add_argument("kind", nargs="?", default="")
    p.add_argument("--limit", type=int, default=200)
    p.set_defaults(run=ents)
    p = sub.add_parser("update", help="re-analyse changed source files")
    p.add_argument("files", nargs="+")
    p.set_defaults(run=update)
    args = ap.parse_args(argv)
    try:
        if args.db:
            server.open_database(args.db)
        args.run(args)
    except ValueError as err:
        print(f"error: {err}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
