"""Write a Kotlin project's declarations to the database.

The first Kotlin entity pass: ``analysis_passes.kotlin_declarations`` collects
facts, this module writes them through the same layer the Java passes use
(``Project.addDefineRefs``, ``addDeclareRefs``), so a Kotlin entity is an
ordinary row with a Java kind (see the collector's docstring for why) and the
API, metrics that read entities, and ``purge_file`` treat it like any other.

Written, per file: the file entity; the package chain with ``Declare`` and
``Declarein``, and ``Contain`` for each top-level type; every declaration with
``Define``/``Definein`` and ``Begin``/``End``; and ``Typed``/``Typedby`` from a
declaration to the project class its declared type names.

**Two phases across the project.** Every file's declarations are written before
any ``Typed``, so a type declared in a file read later still resolves.
Resolution is against the *database*, so it also finds the project's Java
classes, and a re-analysed file needs no facts from the others. A type is
resolved the way Kotlin does it -- enclosing scopes, explicit imports and
aliases, the package, ``*`` imports, the default imports, then the name as
written -- to a class the project declares or a library type from the Kotlin
stdlib index (``oudb/kotlin_index``) or the JDK index. A library target is a
placeholder entity, as the Java passes make for the JDK. A name that resolves to
neither gets **no reference**: a wrong target is worse than a missing one.

Not written: calls, uses, sets, overrides, extends/implements, type arguments,
and anything inside a lambda. A file that does not parse is skipped and reported.
"""

from __future__ import annotations

import logging
import os

from openunderstand.analysis_passes import kotlin_declarations
from openunderstand.oudb.models import (
    EntityModel,
    ReferenceModel,
    col_1based,
    entity_rows,
    flush_reference_writes,
    _kind_name,
    kind_family,
    kind_id,
)
from openunderstand.oudb import jdk_index, kotlin_index
from openunderstand.utils import kotlin_parser

logger = logging.getLogger(__name__)


def _database_bound() -> bool:
    return ReferenceModel._meta.database is not None


def _file_entity(path: str):
    with open(path, encoding="utf-8", errors="replace") as handle:
        text = handle.read()
    return EntityModel.get_or_create(
        _kind=kind_id("Java File"),
        _name=os.path.basename(path),
        _longname=path,
        _contents=text,
    )[0]


def _row_at(longname: str, line: int, col: int):
    """The entity declared with this long name at this position."""
    rows = entity_rows(longname)
    for row in rows:
        if row._line == line and row._column == col_1based(col):
            return row
    return rows[0] if len(rows) == 1 else None


def _write_package(p, kfile, file_ent):
    if kfile.package_pos:
        refs, prefix, previous = [], "", None
        for name, line, col in kfile.package_pos:
            longname = f"{prefix}.{name}" if prefix else name
            refs.append(
                {
                    "scope": previous,
                    "ent": name,
                    "scope_longname": prefix,
                    "ent_longname": longname,
                    "line": line,
                    "col": col,
                }
            )
            prefix, previous = longname, name
    else:
        refs = [{"scope": None, "ent": None, "line": 1, "col": 0}]
    p.addDeclareRefs(refs, file_ent)
    # a package belongs to the package above it
    above = None
    for ref in refs:
        if ref["ent"] is None:
            continue
        row = EntityModel.get_or_none(EntityModel._longname == ref["ent_longname"])
        if row is not None and above is not None and row._parent_id != above._id:
            row._parent = above
            row.save()
        above = row
    if kfile.package_pos:
        return EntityModel.get_or_none(EntityModel._longname == kfile.package)
    return p.getUnnamedPackageEntity(file_ent)


def _write_declarations(p, kfile):
    from openunderstand.ounderstand import project as project_module

    file_ent = _file_entity(kfile.path)
    project_module.CURRENT_FILE["ent"] = file_ent
    package = _write_package(p, kfile, file_ent)
    p.addDefineRefs(kfile.defines, file_ent)
    for name, longname, line, col in kfile.top_types:
        ent = _row_at(longname, line, col)
        if ent is None or package is None:
            continue
        for kind, scope, target in (
            ("Java Contain", package, ent),
            ("Java Containin", ent, package),
        ):
            ReferenceModel.get_or_create(
                _kind=kind_id(kind),
                _file=file_ent,
                _line=line,
                _column=col_1based(col),
                _scope=scope,
                _ent=target,
            )
    return file_ent


def _library_entity(longname: str):
    """The (placeholder) entity for a library type the project does not declare.

    The Java passes name a JDK type the same way: an ``Unknown`` kind that
    ``EntityModel.get_or_create`` upgrades if a declaration ever turns up, and
    whose inverse reference ``drop_external_inverse_refs`` removes, as it does
    for every external target.
    """
    return EntityModel.get_or_create(
        _kind=kind_id("Java Unknown Class Type Member"),
        _name=longname.rsplit(".", 1)[-1],
        _parent=None,
        _longname=longname,
        _value=None,
        _type=None,
        _contents="",
    )[0]


def _project_type(longname: str):
    for row in entity_rows(longname):
        # a class, or a type parameter in scope (its family is "other")
        if kind_family(row._kind_id) == "type" or "GenericParameter" in _kind_name(row._kind_id):
            return row
    return None


def _is_library_type(longname: str) -> bool:
    return kotlin_index.known(longname) or jdk_index.known(longname)


def resolve_type(name: str, kfile, enclosing) -> EntityModel | None:
    """What ``name`` means in ``kfile``: a project class, or a library type.

    Kotlin's order: the enclosing scopes (nested types, type parameters), explicit
    imports and aliases, the file's package, ``*`` imports, then the default
    imports (``kotlin.*``, ``kotlin.collections.*``, ..., ``java.lang.*``), and
    last the name as written. A project declaration beats a library type of the
    same name at the same step. ``None`` when nothing matches -- no reference is
    written for a name nothing explains.
    """
    first = name.split(".", 1)[0]
    rest = name[len(first):]
    package_depth = len(kfile.package.split(".")) if kfile.package else 0
    scopes = []
    for depth in range(len(enclosing), package_depth, -1):
        scopes.append(".".join(enclosing[:depth]))
    steps = [[f"{scope}.{name}" for scope in scopes]]
    steps.append([fq + rest for fq, alias, star in kfile.imports if not star and (alias or fq.rsplit(".", 1)[-1]) == first])
    steps.append([f"{kfile.package}.{name}" if kfile.package else name])
    steps.append([f"{fq}.{name}" for fq, alias, star in kfile.imports if star])
    steps.append([f"{package}.{name}" for package in (*kotlin_index.DEFAULT_PACKAGES, "java.lang")])
    steps.append([name])
    for candidates in steps:
        for candidate in candidates:
            row = _project_type(candidate)
            if row is not None:
                return row
            if _is_library_type(candidate):
                return _library_entity(candidate)
    return None


def _write_typed(kfile, file_ent):
    for t in kfile.types:
        owner = _row_at(*t["owner"])
        target = resolve_type(t["name"], kfile, t["enclosing"])
        if owner is None or target is None:
            continue
        for kind, scope, ent in (("Java Typed", owner, target), ("Java Typedby", target, owner)):
            ReferenceModel.get_or_create(
                _kind=kind_id(kind),
                _file=file_ent,
                _line=t["line"],
                _column=col_1based(t["col"]),
                _ent=ent,
                _scope=scope,
            )


def analyse(paths) -> kotlin_parser.Summary:
    """Parse and write these Kotlin files; with no database bound, only parse.

    Returns the parse summary, with ``analysed`` counting the files written.
    """
    paths = list(paths)
    if not _database_bound():
        return kotlin_parser.parse_paths(paths)
    from openunderstand.ounderstand.project import Project

    summary = kotlin_parser.Summary()
    facts = []
    for path in paths:
        summary.files += 1
        try:
            result = kotlin_parser.parse_file(path)
        except (OSError, UnicodeDecodeError) as exc:
            summary.failed[path] = f"{type(exc).__name__}: {exc}"
            continue
        if not result.ok:
            summary.failed[path] = result.errors[0] if result.errors else "no tree"
            continue
        facts.append(kotlin_declarations.collect(result.tree, path))
    p = Project()
    written = []
    with ReferenceModel._meta.database.atomic():
        for kfile in facts:
            written.append((kfile, _write_declarations(p, kfile)))
        for kfile, file_ent in written:
            _write_typed(kfile, file_ent)
        flush_reference_writes()
    summary.analysed = len(written)
    for path, error in summary.failed.items():
        logger.warning("kotlin: cannot parse %s: %s", path, error[:200])
    if summary.files:
        logger.info(
            "kotlin: %d file(s), %d analysed, %d failed",
            summary.files, summary.analysed, len(summary.failed),
        )
    return summary


def analyse_project(root: str) -> kotlin_parser.Summary:
    return analyse(kotlin_parser.find_files(root))
