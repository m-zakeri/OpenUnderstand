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

**Calls and uses** come last, once every file's declarations are in the database.
``kotlin_symbols`` resolves each occurrence the expression walker found against
the facts of the whole project -- and against the Kotlin standard library
(``oudb/kotlin_index``), the project's Java classes and the JDK -- and this writes ``Call``/``Callby`` to a
function or constructor, ``Create``/``Createby`` to a constructed class,
``Use``/``Useby`` for a read, ``Set``/``Setby`` for a plain assignment and
``Modify``/``Modifyby`` for ``+=`` and ``++``, at the name, scoped to the
function, property or class whose code it is. A target in the standard
library or the JDK is a placeholder entity named by its long name (``kotlin.io.println``,
``java.lang.System.currentTimeMillis``), as the Java passes name the JDK's, and its
inverse is dropped like every external one; a Java project method is its real row.
Only a single fitting candidate is accepted (see ``kotlin_symbols``); the rest
writes nothing. ``relabel_nondynamic_calls`` later splits ``Call`` into
``Call Nondynamic`` from the callee's kind, as for Java.

The facts of every file are cached against its mtime and size, because resolving a
file needs the declarations of the others: an update re-reads only what changed.

Not written: overrides, extends/implements, type arguments, ``Set Init``, infix
and operator calls, and a Java getter read as a property. A file that does not parse is skipped and reported.
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
from openunderstand.ounderstand import kotlin_symbols
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


def _package_row(longname: str):
    for row in entity_rows(longname):
        if "Package" in _kind_name(row._kind_id):
            return row
    return None


def _project_type(longname: str):
    for row in entity_rows(longname):
        # a class, or a type parameter in scope (its family is "other")
        if kind_family(row._kind_id) == "type" or "GenericParameter" in _kind_name(row._kind_id):
            return row
    return None


def resolve_type(name: str, kfile, enclosing) -> EntityModel | None:
    """What ``name`` means in ``kfile``: a project class, or a library type.

    The lookup order is ``kotlin_symbols.lookup_type``'s; here "the project
    declares it" is answered by the database, so Java classes and type parameters
    in scope count too. ``None`` when nothing matches: no reference is written
    for a name nothing explains.
    """
    hit = kotlin_symbols.lookup_type(
        name, kfile, enclosing, lambda longname: _project_type(longname) is not None
    )
    if hit is None:
        return None
    return _project_type(hit[1]) if hit[0] == "project" else _library_entity(hit[1])


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
        if t.get("start") is not None:
            _write_type_qualifiers(kfile, file_ent, t, owner)


def _write_super_qualifiers(kfile, file_ent):
    for t in kfile.qualifiers:
        owner = _row_at(*t["owner"])
        if owner is not None:
            _write_type_qualifiers(kfile, file_ent, t, owner)


def _write_type_qualifiers(kfile, file_ent, t, owner):
    """``a.b.C x`` reads ``a.b`` and ``Outer.Inner x`` reads ``Outer``: a ``Java DotRef`` on each
    qualifier that names an entity, at the first segment, as Java's qualified types do. A project
    package or class has its inverse; a library one is external and loses it afterwards."""
    parts = t["name"].split(".")
    for i in range(len(parts) - 1, 0, -1):
        prefix = ".".join(parts[:i])
        package = _package_row(prefix)
        target = package or resolve_type(prefix, kfile, t["enclosing"])
        if target is None:
            continue
        for kind, scope, ent in (("Java DotRef", owner, target), ("Java DotRefby", target, owner)):
            ReferenceModel.get_or_create(
                _kind=kind_id(kind), _file=file_ent, _line=t["start"][0],
                _column=col_1based(t["start"][1]), _ent=ent, _scope=scope,
            )
        if package is not None:
            break


#: path -> ((mtime_ns, size), KFile). Facts are pure data, so they survive an update.
_FACTS: dict = {}


def _stat(path: str):
    info = os.stat(path)
    return (info.st_mtime_ns, info.st_size)


def _facts(path: str, fresh: bool):
    """The facts for a file, from the cache unless ``fresh`` or the file changed.

    Returns ``(KFile or None, error or None)``.
    """
    try:
        stat = _stat(path)
        cached = _FACTS.get(path)
        if cached is not None and cached[0] == stat and not fresh:
            return cached[1], None
        result = kotlin_parser.parse_file(path)
    except (OSError, UnicodeDecodeError) as exc:
        _FACTS.pop(path, None)
        return None, f"{type(exc).__name__}: {exc}"
    if not result.ok:
        _FACTS.pop(path, None)
        return None, result.errors[0] if result.errors else "no tree"
    kfile = kotlin_declarations.collect(result.tree, path)
    _FACTS[path] = (stat, kfile)
    return kfile, None


def forget(paths) -> None:
    for path in paths:
        _FACTS.pop(path, None)


_POSITIONAL = {
    "call": ("Java Call", "Java Callby"),
    "create": ("Java Create", "Java Createby"),
    "use": ("Java Use", "Java Useby"),
    "dotref": ("Java DotRef", "Java DotRefby"),
    "set": ("Java Set", "Java Setby"),
    "modify": ("Java Modify", "Java Modifyby"),
}


def _placeholder(kind: str, longname: str):
    """An external callable or variable named by its long name, as the Java passes name the JDK's."""
    return EntityModel.get_or_create(
        _kind=kind_id(kind),
        _name=longname.rsplit(".", 1)[-1],
        _parent=None,
        _longname=longname,
        _value=None,
        _type=None,
        _contents="",
    )[0]


def _java_method_row(owner: str, name: str, nargs: int):
    """The Java method row a call with ``nargs`` arguments names, or ``None`` when not unique."""
    from openunderstand.ounderstand import symbol_table

    longname = f"{owner}.{name}"
    rows = [r for r in entity_rows(longname) if kind_family(r._kind_id) == "method"]
    if len(rows) == 1:
        return rows[0]
    site = symbol_table.overload_site(longname, [None] * nargs)
    for row in rows:
        if site is not None and (row._line, row._column) == site:
            return row
    return None


def _java_variable_row(owner: str, name: str):
    rows = [r for r in entity_rows(f"{owner}.{name}") if kind_family(r._kind_id) == "variable"]
    return rows[0] if len(rows) == 1 else None


def _targets(outcome, index):
    """The (label, entity row) pairs an outcome from the resolver writes, mode aside."""
    kind = outcome[0]
    if kind in ("ref", "dotref"):          # a reference reads the declaration; it does not call it
        label = "use" if kind == "ref" else "dotref"
        return [(label, row) for _, row in _targets(outcome[1], index)]
    if kind == "package":
        return [("var", _package_row(outcome[1]))]
    if kind == "call":
        kf, rec = outcome[1]
        if getattr(kf, "library", False):
            return [("call", _placeholder("Java Unknown Method Member", rec["key"][0]))]
        return [("call", _row_at(*rec["key"]))]
    if kind == "var":
        kf, rec = outcome[1]
        if getattr(kf, "library", False):
            return [("var", _placeholder("Java Unknown Variable Member", rec["key"][0]))]
        return [("var", _row_at(*rec["key"]))]
    if kind == "create":
        kf, rec = index.classes[outcome[1]]
        if getattr(kf, "library", False):
            return [("create", _library_entity(outcome[1]))]
        return [("create", _row_at(*rec["key"]))]
    if kind == "jcall":
        return [("call", _java_method_row(outcome[1], outcome[2], outcome[3]))]
    if kind == "jcreate":
        return [("create", _project_type(outcome[1]))]
    if kind == "jvar":
        return [("var", _java_variable_row(outcome[1], outcome[2]))]
    if kind == "jdkcall":
        return [("call", _placeholder("Java Unknown Method Member", f"{outcome[1]}.{outcome[2]}"))]
    if kind == "jdkvar":
        return [("var", _placeholder("Java Unknown Variable Member", f"{outcome[1]}.{outcome[2]}"))]
    if kind == "libcreate":
        return [("create", _library_entity(outcome[1]))]
    return []


def _write_references(kfile, file_ent, resolver):
    index = resolver.ix
    for occ in kfile.occurrences:
        outcome = resolver.resolve(occ, kfile)
        if not outcome:
            continue
        scope = _row_at(*occ["o"])
        if scope is None:
            continue
        for item in outcome:
            for label, row in _targets(item, index):
                if row is None:
                    continue
                forward, inverse = _POSITIONAL[occ["m"] if label == "var" else label]
                for name, owner, ent in ((forward, scope, row), (inverse, row, scope)):
                    ReferenceModel.get_or_create(
                        _kind=kind_id(name),
                        _file=file_ent,
                        _line=occ["l"],
                        _column=col_1based(occ["c"]),
                        _ent=ent,
                        _scope=owner,
                    )


def _imported(fq: str, star: bool, ix) -> list:
    """The project entities an import names: a class, every overload of a function, a property,
    or (``*``) the package or class whose members it brings. Library targets name nothing here."""
    from openunderstand.ounderstand import symbol_table

    def own(entry):
        return entry is not None and not getattr(entry[0], "library", False)

    if star:
        if fq in ix.packages:
            return [_package_row(fq)]
        if own(ix.classes.get(fq)):
            return [_row_at(*ix.classes[fq][1]["key"])]
        return [_project_type(fq)] if symbol_table.is_project_type(fq) else []
    if own(ix.classes.get(fq)):
        return [_row_at(*ix.classes[fq][1]["key"])]
    if symbol_table.is_project_type(fq):
        return [_project_type(fq)]
    owner, _, name = fq.rpartition(".")
    found = [c for c in ix.top_funs.get((owner, name), []) + ix.top_vars.get((owner, name), [])]
    if own(ix.classes.get(owner)) and ix.classes[owner][1]["object"]:      # `import a.Obj.member`
        found += ix.members_funs.get(owner, {}).get(name, []) + ix.members_vars.get(owner, {}).get(name, [])
    return [_row_at(*rec["key"]) for kf, rec in found if not getattr(kf, "library", False)]


def _write_imports(kfile, file_ent, resolver):
    """``Java Importby`` (``Demand`` for ``*``) on what an import names, with the file as the entity.

    Inverse only, at the last identifier, as Java's: Understand has no ``Java Import`` on the
    importing file. A project class or function also gets a ``Java DotRefby`` on the package (and
    outer types) enclosing it, at the first identifier.
    """
    ix = resolver.ix
    for fq, star, line, col, head_line, head_col in kfile.import_sites:
        targets = [t for t in _imported(fq, star, ix) if t is not None]
        for target in targets:
            ReferenceModel.get_or_create(
                _kind=kind_id("Java Importby Demand" if star else "Java Importby"),
                _file=file_ent, _line=line, _column=col_1based(col), _ent=file_ent, _scope=target,
            )
        if not targets or star:
            continue
        parts = fq.split(".")
        for i in range(len(parts) - 1, 0, -1):
            prefix = ".".join(parts[:i])
            package = _package_row(prefix)
            row = package or (_row_at(*ix.classes[prefix][1]["key"]) if prefix in ix.classes else _project_type(prefix))
            if row is not None:
                ReferenceModel.get_or_create(
                    _kind=kind_id("Java DotRefby"),
                    _file=file_ent, _line=head_line, _column=col_1based(head_col), _ent=file_ent, _scope=row,
                )
                if package is not None:
                    break          # intermediate packages get nothing


def analyse(paths, root: str | None = None) -> kotlin_parser.Summary:
    """Parse and write these Kotlin files; with no database bound, only parse.

    ``root`` is the project, whose other Kotlin files supply the declarations a
    call or name may resolve to; without it only ``paths`` are known. Returns the
    parse summary, with ``analysed`` counting the files written.
    """
    paths = list(paths)
    if not _database_bound():
        return kotlin_parser.parse_paths(paths)
    from openunderstand.ounderstand.project import Project

    summary = kotlin_parser.Summary()
    facts = []
    for path in paths:
        summary.files += 1
        kfile, error = _facts(path, fresh=True)
        if kfile is None:
            summary.failed[path] = error
        else:
            facts.append(kfile)
    known = {k.path: k for k in facts}
    if root is not None:
        for path in kotlin_parser.find_files(root):
            if path not in known:
                kfile, _ = _facts(path, fresh=False)
                if kfile is not None:
                    known[path] = kfile
    resolver = kotlin_symbols.Resolver(kotlin_symbols.Index(list(known.values())))
    p = Project()
    written = []
    with ReferenceModel._meta.database.atomic():
        for kfile in facts:
            written.append((kfile, _write_declarations(p, kfile)))
        for kfile, file_ent in written:
            _write_typed(kfile, file_ent)
            _write_super_qualifiers(kfile, file_ent)
        for kfile, file_ent in written:
            _write_references(kfile, file_ent, resolver)
            _write_imports(kfile, file_ent, resolver)
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
    return analyse(kotlin_parser.find_files(root), root=root)


def dependents(file_ids) -> set:
    """Kotlin files, other than these, that refer to something these declare.

    A change to a declaration can change what a name or call elsewhere means, so
    those files are re-analysed with it. One level: a body edit never reaches
    past the files that name the entity.
    """
    flush_reference_writes()
    definein = kind_id("Java Definein")
    declared = {
        r._scope_id
        for r in ReferenceModel.select().where(
            (ReferenceModel._kind == definein) & (ReferenceModel._ent.in_(list(file_ids)))
        )
    }
    if not declared:
        return set()
    files = {
        r._file_id
        for r in ReferenceModel.select().where(
            ReferenceModel._ent.in_(list(declared)) | ReferenceModel._scope.in_(list(declared))
        )
        if r._file_id is not None
    }
    files -= set(file_ids)
    return {
        e._id
        for e in EntityModel.select().where(EntityModel._id.in_(list(files)))
        if kotlin_parser.is_kotlin(e._longname or "")
    }
