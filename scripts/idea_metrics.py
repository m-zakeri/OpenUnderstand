"""Dump what the IDEA plugin shows: metrics, the symbol table, or references.

    python -m scripts.idea_metrics <java-project-dir> [metric ...]
    python -m scripts.idea_metrics --symbols <java-project-dir>
    python -m scripts.idea_metrics --references <java-project-dir> <entity longname>

Metrics print as `path:line: text`, which IDEA's External Tools turns into
clickable links with the output filter `$FILE_PATH$:$LINE$:.*` -- no plugin
needed.

The symbol table and the references print as tab-separated rows under a header
row, because kind names hold spaces (`Java Static Method Public Member`). Every
view starts with the same three columns, Entity, File and Line, so the plugin
navigates and exports them all the same way.

`--references` reuses the database the last analysis of the project left, and
analyses only when there is none: asking about one symbol should not re-analyse
the whole project.
"""
import os
import sys
import tempfile

DATABASE_DIR = os.path.join(tempfile.gettempdir(), "idea-oudb")


def _analyse(source_dir):
    from openunderstand.mcp_server import analyze, _STATE

    analyze(source_dir, database=DATABASE_DIR)
    return _STATE["db"]


def _database(source_dir):
    """The project's existing database, or a fresh analysis when there is none."""
    path = os.path.join(
        DATABASE_DIR, os.path.basename(os.path.abspath(source_dir).rstrip("/")) + ".udb"
    )
    if os.path.exists(path):
        from openunderstand.oudb.api import open as ou_open

        return ou_open(path)
    return _analyse(source_dir)


def _declaration(ent):
    """The reference naming where `ent` is declared, or None."""
    defined = ent.refs("Definein") or ent.refs("Declarein")
    return defined[0] if defined else None


def _row(*cells):
    # A tab or newline inside a cell would break the row apart.
    return "\t".join(
        "" if c is None else str(c).replace("\t", " ").replace("\n", " ") for c in cells
    )


def dump(source_dir, metrics=None, kinds=("Class ~Unknown", "Method ~Unknown")):
    db = _analyse(source_dir)
    for kind in kinds:
        for ent in db.ents(kind):
            ref = _declaration(ent)
            if ref is None:
                continue
            values = {}
            # Every metric the entity defines -- ent.metrics() is Understand's
            # vocabulary, so there is no second list here to keep in step.
            for name in metrics or ent.metrics():
                try:
                    got = ent.metric([name]).get(name)
                except Exception:  # unimplemented metric, or one that raises
                    got = None
                if got is not None:
                    values[name] = got
            if not values:
                continue
            cells = " ".join(f"{k}={v}" for k, v in values.items())
            print(f"{ref.file().longname()}:{ref.line()}: {ent.longname()}  {cells}")


def symbols(source_dir):
    """Every entity the project declares: the symbol table."""
    db = _analyse(source_dir)
    print(_row("Entity", "File", "Line", "Name", "Kind", "Type", "Parent"))
    for ent in db.ents("~Unknown ~Unresolved"):
        ref = _declaration(ent)
        if ref is None:
            continue  # a file, or something only referenced, never declared
        parent = ent.parent()
        print(_row(
            ent.longname(), ref.file().longname(), ref.line(), ent.name(),
            ent.kindname(), ent.type(), parent.longname() if parent else None,
        ))


def references(source_dir, longname):
    """Every reference to or from one entity, in both directions."""
    db = _database(source_dir)
    print(_row("Entity", "File", "Line", "Column", "Reference", "Of"))
    for ent in db.ents():
        if ent.longname() != longname:
            continue
        for ref in ent.refs():
            print(_row(
                ref.ent().longname(), ref.file().longname(), ref.line(),
                ref.column(), ref.kindname(), longname,
            ))


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    if args[0] == "--symbols" and len(args) == 2:
        symbols(args[1])
    elif args[0] == "--references" and len(args) == 3:
        references(args[1], args[2])
    elif args[0].startswith("--"):
        sys.exit(__doc__)
    else:
        dump(args[0], tuple(args[1:]) or None)
