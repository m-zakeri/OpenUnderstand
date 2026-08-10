"""A project-wide index of declarations, built before the per-file passes run.

`process_file` sees one file. A pass that meets `basic_operation.sum` while
walking `fibonacci.java` has no way to know what that name refers to, so it
invents a placeholder entity -- 51 of the 68 spurious entities on the
calculator_app fixture, and the reason reference recall sits below half.

`merge_placeholder_entities()` repairs some of this after the fact, but only
where exactly one project-wide candidate matches, and it cannot help a pass
that needed the answer *while* deciding what to write.

This module does the cheap half of the work up front: one pass over every file
recording what each declares, keyed by simple name. It is deliberately not a
type checker -- it answers "which declarations in this project are called
`sum`, and what are their long names", which is what the passes actually need.
"""

from __future__ import annotations

import os
from fnmatch import fnmatch

from antlr4 import FileStream

from openunderstand.utils import antler_parser


class _DeclarationIndex:
    """Simple name -> long names declaring it, project-wide."""

    def __init__(self):
        self.by_simple_name: dict[str, set[str]] = {}
        self.types: dict[str, str] = {}
        self.files = 0

    def add(self, simple_name: str, longname: str, is_type: bool = False):
        if not simple_name or not longname:
            return
        self.by_simple_name.setdefault(simple_name, set()).add(longname)
        if is_type:
            self.types.setdefault(simple_name, longname)

    def resolve(self, simple_name: str, scope_longname: str = "") -> str | None:
        """Long name for a simple name, or None when it is ambiguous.

        A declaration in the asking scope's own package wins over one
        elsewhere; otherwise a unique match wins and an ambiguous one is
        refused. Refusing beats guessing: a wrong resolution silently
        misattributes every reference built on it.
        """
        candidates = self.by_simple_name.get(simple_name)
        if not candidates:
            return None
        if len(candidates) == 1:
            return next(iter(candidates))
        package = scope_longname.rsplit(".", 1)[0] if scope_longname else ""
        if package:
            local = [c for c in candidates if c.startswith(package + ".")]
            if len(local) == 1:
                return local[0]
        return None

    def __len__(self):
        return sum(len(v) for v in self.by_simple_name.values())


#: Populated by build(); read by the passes through resolve().
INDEX = _DeclarationIndex()


def build(root: str) -> _DeclarationIndex:
    """Index every declaration under `root`. Safe to call more than once."""
    global INDEX
    index = _DeclarationIndex()

    # Imported here: the listener imports class_properties, which imports the
    # generated parser, and this module is imported by the CLI before sys.path
    # has been arranged in some entry points.
    from openunderstand.analysis_passes.define_definein import DefineListener
    from antlr4 import ParseTreeWalker

    for path in _java_files(root):
        try:
            tree = antler_parser.parse(
                FileStream(path, encoding="utf8"), "compilationUnit"
            )
            listener = DefineListener(path)
            ParseTreeWalker().walk(t=tree, listener=listener)
        except Exception:
            # A file that will not parse contributes nothing; the per-file
            # pass over it logs the failure in its own right.
            continue
        index.files += 1
        for declaration in listener.defines:
            index.add(
                declaration["ent"],
                declaration["ent_longname"],
                is_type=declaration.get("decl") in ("class", "interface", "enum",
                                                    "annotation"),
            )

    INDEX = index
    return index


def resolve(simple_name: str, scope_longname: str = "") -> str | None:
    return INDEX.resolve(simple_name, scope_longname)


def _java_files(root: str):
    for directory, _, names in os.walk(root):
        for name in names:
            if fnmatch(name, "*.java"):
                yield os.path.join(directory, name)
