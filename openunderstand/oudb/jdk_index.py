"""The JDK, as much of it as resolving external names needs.

Understand indexes the whole Java library. This project cannot, and for a long
time it compensated with five hand-written tables -- 208 entries spread over
symbol_table.py and models.py, each one added the day a benchmark tripped over
it: `java.lang` names, simple-name-to-package for wildcard imports, the type of
`System.out`, the members of the handful of interfaces a class might implement,
and which JDK classes are final. They were honest about being incomplete, and
every gap showed up as a wrong or missing reference: `new HashMap<>()` binding
to a project class, `String.length` reported as a virtual call, a class
implementing `Comparator` with no `Overrides` row.

`scripts/gen_jdk_index.py` generates the real thing from a JDK's own runtime
image -- 3,957 public java./javax. types with their modifiers, supertypes,
public fields and, for interfaces, their members. The result is committed as
`jdk_index.txt.gz` (64 KB), so neither a JDK nor an Understand licence is
needed to use it.

Loaded once, on first access. The parse is a few milliseconds and this module
imports nothing outside the standard library, so it stays safe to reach from
anywhere -- including models.py, which sits below everything else.
"""

from __future__ import annotations

import gzip
import os
from functools import lru_cache

_PATH = os.path.join(os.path.dirname(__file__), "jdk_index.txt.gz")


@lru_cache(maxsize=1)
def _load() -> dict:
    types: dict[str, dict] = {}
    by_simple: dict[str, list[str]] = {}
    if not os.path.exists(_PATH):
        # An installed copy without the data file still works; every lookup
        # simply answers "unknown", which is the same answer the hand-written
        # tables gave for anything they did not list.
        return {"types": types, "by_simple": by_simple}
    with gzip.open(_PATH, "rt", encoding="utf8") as handle:
        for line in handle:
            if line.startswith("#"):
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) != 5:
                continue
            longname, final, supers, fields, methods = parts
            types[longname] = {
                "final": final == "F",
                "supers": supers.split(",") if supers else [],
                "fields": dict(
                    pair.split("=", 1) for pair in fields.split(",") if "=" in pair),
                "methods": {
                    name: int(arity) for name, arity in
                    (m.split("/", 1) for m in methods.split(",") if "/" in m)},
            }
            by_simple.setdefault(longname.rsplit(".", 1)[-1], []).append(longname)
    return {"types": types, "by_simple": by_simple}


def resolve_simple(name: str, packages=()) -> str | None:
    """Long name for a JDK type's simple name, or None when it cannot be placed.

    A simple name is only accepted when it is unambiguous across the whole
    index, or when exactly one of the packages offered -- the file's wildcard
    imports -- declares it. 66 of the 3,957 names are ambiguous (`java.util.List`
    and `java.awt.List`), and guessing between them is what the packages are
    for.
    """
    candidates = _load()["by_simple"].get(name, ())
    if not candidates:
        return None
    if packages:
        offered = [c for c in candidates if c.rsplit(".", 1)[0] in packages]
        if len(offered) == 1:
            return offered[0]
        if offered:
            return None                 # the imports do not settle it either
    return candidates[0] if len(candidates) == 1 else None


def package_of(name: str) -> str | None:
    """Package declaring a JDK simple name, when exactly one does."""
    longname = resolve_simple(name)
    return longname.rsplit(".", 1)[0] if longname else None


def is_final(longname: str) -> bool:
    """Whether a JDK type is declared final, so a call on it never dispatches."""
    entry = _load()["types"].get(longname)
    return bool(entry and entry["final"])


def field_type(owner: str, field: str) -> str | None:
    """Declared type of a JDK type's public field -- `System.out` is a PrintStream."""
    entry = _load()["types"].get(owner)
    return entry["fields"].get(field) if entry else None


def members(longname: str) -> dict:
    """Member name -> parameter count, for an interface or java.lang.Object."""
    entry = _load()["types"].get(longname)
    return entry["methods"] if entry else {}


def declares(longname: str, member: str, arity: int) -> bool:
    """Whether a JDK type declares `member` taking `arity` parameters."""
    return members(longname).get(member) == arity


def known(longname: str) -> bool:
    return longname in _load()["types"]
