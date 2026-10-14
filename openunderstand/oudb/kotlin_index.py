"""The Kotlin standard library, as much of it as resolving a type name needs.

Generated from the library's own source by ``scripts/gen_kotlin_index.py`` and
committed as ``kotlin_index.txt.gz``: one public type or typealias per line,
with a flag (C class or object, I interface, E enum class, A annotation class,
T typealias). It is what lets ``kotlin_project`` answer that ``Int`` in a
declaration is ``kotlin.Int`` and ``List`` is ``kotlin.collections.List``
without the project declaring either.

Like ``jdk_index`` this imports nothing outside the standard library and loads
on first use; a copy installed without the data file answers "unknown".
"""

from __future__ import annotations

import gzip
import os
from functools import lru_cache

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


@lru_cache(maxsize=1)
def _load() -> dict:
    types: dict[str, str] = {}
    if os.path.exists(_PATH):
        with gzip.open(_PATH, "rt", encoding="utf8") as handle:
            for line in handle:
                if line.startswith("#") or "\t" not in line:
                    continue
                name, flag = line.rstrip("\n").split("\t")
                types[name] = flag
    return types


def known(longname: str) -> bool:
    """Whether the standard library declares this type."""
    return longname in _load()


def flag(longname: str) -> str | None:
    return _load().get(longname)


def is_interface(longname: str) -> bool:
    return _load().get(longname) == "I"


def resolve_simple(name: str, packages=DEFAULT_PACKAGES) -> str | None:
    """The type a simple (or nested, dotted) name means through these packages."""
    types = _load()
    for package in packages:
        candidate = f"{package}.{name}"
        if candidate in types:
            return candidate
    return None
