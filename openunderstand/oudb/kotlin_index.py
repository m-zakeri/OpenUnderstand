"""The Kotlin standard library, as much of it as resolving a name needs.

Generated from the library's own source by ``scripts/gen_kotlin_index.py`` and
committed as ``kotlin_index.txt.gz``: its public types and typealiases (with
supertypes), top-level and member functions and constructors (arity, extension
receiver, return type, and which parameters are function types with a receiver)
and properties. It is what lets ``kotlin_project`` answer that ``Int`` is
``kotlin.Int``, that ``println`` is ``kotlin.io.println`` and that ``list.map { }``
is an extension on ``Iterable``, without the project declaring any of them.

Like ``jdk_index`` this imports nothing outside the standard library and loads
on first use; a copy installed without the data file answers "unknown".

``library_files()`` returns the declarations as pseudo-files shaped like the
facts ``kotlin_declarations`` collects from a project file, one per package, so
the resolver looks a stdlib function up exactly as it looks up a project one. Their
``library`` attribute is true: the writer gives such a target a placeholder entity.
"""

from __future__ import annotations

import gzip
import json
import os
from functools import lru_cache
from types import SimpleNamespace

_PATH = os.path.join(os.path.dirname(__file__), "kotlin_index.txt.gz")

#: What every Kotlin/JVM file sees without importing, lowest precedence of all
#: (after the file's own scope, its package, and its explicit and `*` imports).
DEFAULT_PACKAGES = (
    "kotlin",
    "kotlin.annotation",
    "kotlin.collections",
    "kotlin.comparisons",
    "kotlin.io",
    "kotlin.ranges",
    "kotlin.sequences",
    "kotlin.text",
    "kotlin.jvm",
)

_DECL = {"C": "class", "O": "class", "I": "interface", "E": "enum", "A": "annotation"}


def _tuple(x):
    """A JSON type expression (lists) as the tuples the collector produces."""
    if isinstance(x, list):
        return tuple(_tuple(i) for i in x)
    return x


def _expr(text):
    return _tuple(json.loads(text)) if text else None


@lru_cache(maxsize=1)
def _load() -> dict:
    data = {"types": {}, "supers": {}, "aliases": {}, "functions": [], "properties": [], "data": {},
            "tparams": {}, "super_exprs": {}, "alias_exprs": {}}
    if not os.path.exists(_PATH):
        return data
    with gzip.open(_PATH, "rt", encoding="utf8") as handle:
        for line in handle:
            if line.startswith("#"):
                continue
            parts = line.rstrip("\n").split("\t")
            if parts[0] == "@A" and len(parts) >= 3:
                data["aliases"][parts[1]] = parts[2]
                if len(parts) >= 5:
                    data["alias_exprs"][parts[1]] = (tuple(p for p in parts[3].split(",") if p), _expr(parts[4]))
            elif parts[0] == "@D" and len(parts) >= 3:
                data["data"][parts[1]] = parts[2].split(",")
            elif parts[0] == "@F" and len(parts) >= 7:
                row = tuple(parts[1:7]) + ((parts[7] if len(parts) > 7 else ""),)
                data["functions"].append(row + tuple(parts[8:11]) + ("",) * max(0, 11 - len(parts)))
            elif parts[0] == "@V" and len(parts) >= 5:
                data["properties"].append(tuple(parts[1:5]) + tuple(parts[5:7]) + ("",) * max(0, 7 - len(parts)))
            elif len(parts) >= 2 and not parts[0].startswith("@"):
                data["types"][parts[0]] = parts[1]
                if len(parts) > 2 and parts[2]:
                    data["supers"][parts[0]] = parts[2].split(",")
                if len(parts) > 3:
                    data["tparams"][parts[0]] = tuple(p for p in parts[3].split(",") if p)
                if len(parts) > 4 and parts[4]:
                    data["super_exprs"][parts[0]] = _tuple(json.loads(parts[4]))
    return data


def known(longname: str) -> bool:
    """Whether the standard library declares this type."""
    return longname in _load()["types"]


def flag(longname: str) -> str | None:
    return _load()["types"].get(longname)


def is_interface(longname: str) -> bool:
    return _load()["types"].get(longname) == "I"


def alias_expression(longname: str):
    """A stdlib typealias's type parameters and the type expression it stands for, or ``None``."""
    return _load()["alias_exprs"].get(longname)


def alias_target(longname: str) -> str | None:
    """What a stdlib typealias stands for: ``kotlin.collections.ArrayList`` is ``java.util.ArrayList``."""
    return _load()["aliases"].get(longname)


def resolve_simple(name: str, packages=DEFAULT_PACKAGES) -> str | None:
    """The type a simple (or nested, dotted) name means through these packages."""
    types = _load()["types"]
    for package in packages:
        candidate = f"{package}.{name}"
        if candidate in types:
            return candidate
    return None


@lru_cache(maxsize=1)
def library_files() -> tuple:
    """The index as pseudo-files (one per package) in the shape of collected facts."""
    data = _load()
    files: dict = {}

    def file_of(package):
        if package not in files:
            files[package] = SimpleNamespace(
                path=f"<kotlin stdlib {package}>", package=package, imports=[], classes={},
                callables=[], variables=[], occurrences=[], aliases=[], library=True,
            )
        return files[package]

    for fq, kind in data["types"].items():
        if kind == "T":
            continue
        package = fq.rpartition(".")[0]
        # a nested type lives in its top-level type's package
        while package and package in data["types"]:
            package = package.rpartition(".")[0]
        record = {
            "name": fq.rpartition(".")[2], "decl": _DECL.get(kind, "class"), "object": kind == "O",
            "companion": None, "supers": list(data["supers"].get(fq, [])), "scope": (),
            "key": (fq, 0, 0), "vis": ["public"], "data": list(data["data"].get(fq, [])),
            "tparams": data["tparams"].get(fq, ()), "super_exprs": data["super_exprs"].get(fq, ()),
        }
        file_of(package).classes[fq] = record
    serial = 0
    for kind, where, name, receiver, params, ret, ptypes, rexpr, retexpr, ptexprs in data["functions"]:
        serial += 1
        package, owner = (where[1:], None) if where.startswith("=") else ("", where)
        if owner:
            package = owner
            while package and package in data["types"]:
                package = package.rpartition(".")[0]
        longname = f"{where[1:]}.{name}" if where.startswith("=") else f"{owner}.{name}"
        file_of(package).callables.append(
            {
                "key": (longname, 0, serial), "name": name, "owner": owner, "ctor": kind == "c",
                "params": [(c in "dD", c in "vV", c in "RDV") for c in params],
                "receiver": receiver or None, "ret": ret or None, "ret_init": None, "local": False,
                "scope": (), "vis": ["public"], "tparams": (),
                "ptypes": tuple((t or None) for t in ptypes.split(",")) if params else (),
                "receiver_expr": _expr(rexpr), "ret_expr": _expr(retexpr),
                "ptexprs": tuple(_expr(t) for t in ptexprs.split("|")) if params else (),
            }
        )
    for where, name, receiver, declared, declared_expr, receiver_expr in data["properties"]:
        serial += 1
        package, owner = (where[1:], None) if where.startswith("=") else ("", where)
        if owner:
            package = owner
            while package and package in data["types"]:
                package = package.rpartition(".")[0]
        longname = f"{where[1:]}.{name}" if where.startswith("=") else f"{owner}.{name}"
        file_of(package).variables.append(
            {
                "key": (longname, 0, serial), "name": name, "owner": owner, "kind": "property",
                "declared": declared or None, "init": None, "scope": (), "vis": ["public"],
                "receiver": receiver or None,
                "declared_expr": _expr(declared_expr), "receiver_expr": _expr(receiver_expr),
            }
        )
    return tuple(files.values())
