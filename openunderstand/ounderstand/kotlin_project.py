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

Also written, after the declarations: supertypes, overrides, casts, ``@Throws``, ``Set Init``, type-parameter
bounds, implicit supertypes and ``Java Couple`` (see ``_write_supers`` onward). A file that does not parse is
skipped and reported.
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
    forget_entity_rows,
    is_placeholder_kind,
    _kind_name,
    kind_family,
    kind_id,
)
from openunderstand.oudb import jdk_index, kotlin_index
from openunderstand.ounderstand import kotlin_symbols
from openunderstand.utils import kind_names as K
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


def _owner_row(key, file_ent):
    """The entity a piece of code belongs to: the file itself for a `@file:` annotation."""
    return file_ent if key[0] == "<file>" else _row_at(*key)


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


def _forwarding_methods(kfile, resolver) -> list:
    """The methods ``class A(b: I) : I by b`` generates: one per member of a project interface ``I`` that
    ``A`` does not declare, as ``Define Implicit`` (the way a data class's ``componentN`` is). A library
    interface is left alone: its members come from an index, not from the code being analysed."""
    ix = resolver.ix
    out = []
    for sup in kfile.supers:
        if not sup.get("delegated"):
            continue
        target = resolver.type_name(sup["name"], kfile, sup["enclosing"])
        if target is None or target[0] != "class" or target[1] not in ix.classes:
            continue
        if target[1].startswith("kotlin."):
            continue
        owner = sup["owner"][0]
        own = {(name, len(r["params"])) for name, lst in ix.members_funs.get(owner, {}).items() for _, r in lst}
        seen = set()
        for level in resolver.hierarchy(target):
            if level[0] != "class" or level[1].startswith("kotlin."):
                continue
            for name, lst in ix.members_funs.get(level[1], {}).items():
                for _, r in lst:
                    key = (name, len(r["params"]))
                    if key in own or key in seen or "private" in (r.get("vis") or ()):
                        continue
                    seen.add(key)
                    out.append({
                        "contents": "", "type": None, "decl": K.METHOD, "modifiers": ["public"], "span": None,
                        "parent": kfile.package,
                        "scope": owner.rsplit(".", 1)[-1],
                        "ent": name, "scope_longname": owner, "ent_longname": f"{owner}.{name}",
                        "line": sup["line"], "col": sup["col"], "implicit": True,
                    })
    return out


def _write_declarations(p, kfile, resolver=None):
    from openunderstand.ounderstand import project as project_module

    file_ent = _file_entity(kfile.path)
    project_module.CURRENT_FILE["ent"] = file_ent
    package = _write_package(p, kfile, file_ent)
    forwarded = _forwarding_methods(kfile, resolver) if resolver is not None else []
    p.addDefineRefs([*kfile.defines, *forwarded], file_ent)
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
        # a single-type import names its class exactly, even from a library nothing indexes
        head = name.split(".", 1)[0]
        for fq, alias, star in kfile.imports:
            if not star and (alias or fq.rsplit(".", 1)[-1]) == head:
                return _library_entity(fq + name[len(head):])
        return None
    return _project_type(hit[1]) if hit[0] == "project" else _library_entity(hit[1])


def _write_typed(kfile, file_ent):
    for t in kfile.types:
        owner = _row_at(*t["owner"])
        target = resolve_type(t["name"], kfile, t["enclosing"])
        if owner is None or target is None:
            continue
        pair = ("Java Typed Implicit", "Java Typedby Implicit") if t.get("implicit") else ("Java Typed", "Java Typedby")
        for kind, scope, ent in ((pair[0], owner, target), (pair[1], target, owner)):
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


def _write_receivers(kfile, file_ent):
    """An extension reads the class it extends: a ``Java Use`` at the receiver type's last segment."""
    for t in kfile.receivers:
        owner = _row_at(*t["owner"])
        target = resolve_type(t["name"], kfile, t["enclosing"])
        if owner is None or target is None:
            continue
        for kind, scope, ent in (("Java Use", owner, target), ("Java Useby", target, owner)):
            ReferenceModel.get_or_create(
                _kind=kind_id(kind), _file=file_ent, _line=t["line"],
                _column=col_1based(t["col"]), _ent=ent, _scope=scope,
            )


def _write_type_args(kfile, file_ent):
    """A class named as a type argument of a declaration: ``Typed GenericArgument`` (``Use`` when
    variance-projected), at the argument's first segment, as Java's declared generic arguments."""
    for t in kfile.type_args:
        owner = _row_at(*t["owner"])
        target = resolve_type(t["name"], kfile, t["enclosing"])
        if owner is None or target is None:
            continue
        if t.get("constructed"):                # `ArrayList<Point>()`: Java's `new HashMap<K, V>()` rule
            pair = ("Java Use GenericArgument", "Java Useby GenericArgument")
        elif t["plain"]:
            pair = ("Java Use", "Java Useby")
        else:
            pair = ("Java Typed GenericArgument", "Java Typedby GenericArgument")
        for kind, scope, ent in ((pair[0], owner, target), (pair[1], target, owner)):
            ReferenceModel.get_or_create(
                _kind=kind_id(kind), _file=file_ent, _line=t["start"][0],
                _column=col_1based(t["start"][1]), _ent=ent, _scope=scope,
            )


def _write_annotations(kfile, file_ent):
    """``@Mark`` on a declaration is a ``Java Use Annotation`` of the annotation class, scoped to it."""
    for t in kfile.annotations:
        owner = _owner_row(t["owner"], file_ent)
        target = resolve_type(t["name"], kfile, t["enclosing"])
        if owner is None or target is None:
            continue
        for kind, scope, ent in (("Java Use Annotation", owner, target), ("Java Useby Annotation", target, owner)):
            ReferenceModel.get_or_create(
                _kind=kind_id(kind), _file=file_ent, _line=t["line"],
                _column=col_1based(t["col"]), _ent=ent, _scope=scope,
            )


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


def _pair(forward, inverse, file_ent, line, col, scope, ent):
    for kind, owner, target in ((forward, scope, ent), (inverse, ent, scope)):
        ReferenceModel.get_or_create(
            _kind=kind_id(kind), _file=file_ent, _line=line, _column=col_1based(col), _ent=target, _scope=owner,
        )


def _write_supers(kfile, file_ent, resolver):
    """``class A : B()`` extends, ``class A : I`` implements, ``interface J : I`` extends: at the supertype's
    last segment, as Java's. A plain supertype whose kind nothing tells is refused, not guessed."""
    ix = resolver.ix
    for t in kfile.supers:
        owner = _row_at(*t["owner"])
        target = resolve_type(t["name"], kfile, t["enclosing"])
        if owner is None or target is None or target._id == owner._id:
            continue
        fq = target._longname
        external = fq not in ix.classes and "Unknown" in _kind_name(target._kind_id)
        known = fq in ix.classes or kotlin_index.known(fq) or jdk_index.known(fq) or not external
        interface = False if t["ctor"] else resolver.is_interface_type(fq)
        if not t["ctor"] and not known:
            continue
        mine = kfile.classes.get(t["owner"][0]) or {}
        if interface and mine.get("decl") != "interface":
            pair = ("Java Implement Couple", "Java Implementby Coupleby")
        else:
            suffix = " External" if external else ""
            pair = (f"Java Extend Couple{suffix}", f"Java Extendby Coupleby{suffix}")
        _pair(*pair, file_ent, t["line"], t["col"], owner, target)


def _write_implicit_supers(kfile, file_ent):
    """What nothing writes but the language implies: an enum extends ``kotlin.Enum``, a class with no
    superclass ``kotlin.Any``, and an unbounded type parameter ``kotlin.Any`` too. Java's rule, at the
    declaration's line and no column; the target is external, so it has no inverse."""
    explicit = {t["owner"][0] for t in kfile.supers if t["ctor"]}
    owners = []
    for longname, rec in kfile.classes.items():
        if rec["decl"] in ("interface", "annotation") or longname in explicit:
            continue
        enum = "enum" in (rec.get("kind_mods") or ()) or rec.get("enum")
        owners.append((rec["key"], "kotlin.Enum" if enum else "kotlin.Any"))
    owners += [(key, "kotlin.Any") for key in kfile.unbounded]
    for key, base in owners:
        scope = _row_at(*key)
        if scope is None:
            continue
        target = _library_entity(base)
        ReferenceModel.get_or_create(
            _kind=kind_id("Java Extend Couple Implicit External"), _file=file_ent, _line=key[1], _column=0,
            _ent=target, _scope=scope,
        )


def _write_overrides(kfile, file_ent, resolver):
    """A declaration marked ``override`` is a ``Java Overrides`` of the member it overrides, at its name."""
    for rec, variable in [(r, False) for r in kfile.callables] + [(r, True) for r in kfile.variables]:
        if not rec.get("override"):
            continue
        outcome = resolver.overridden(rec, variable)
        mine = _row_at(*rec["key"])
        if outcome is None or mine is None:
            continue
        for _, row in _targets(outcome, resolver.ix):
            if row is not None and row._id != mine._id:
                _pair("Java Overrides", "Java Overriddenby", file_ent, rec["key"][1], rec["key"][2], mine, row)


def _write_owned_types(kfile, file_ent, records, forward, inverse):
    """A class named by a cast or ``@Throws``, scoped to the declaration holding it, at its first segment."""
    for t in records:
        owner = _owner_row(t["owner"], file_ent)
        target = resolve_type(t["name"], kfile, t["enclosing"])
        if owner is not None and target is not None:
            _pair(forward, inverse, file_ent, t["line"], t["col"], owner, target)


def _write_set_inits(kfile, file_ent):
    """``val x = e`` sets ``x`` at its name, from the function or class that holds it."""
    for rec in kfile.variables:
        if not rec.get("set_init"):
            continue
        row = _row_at(*rec["key"])
        scope = row._parent if row is not None else None
        if scope is not None:
            _pair("Java Set Init", "Java Setby Init", file_ent, rec["key"][1], rec["key"][2], scope, row)


#: The references through which one class uses a type, data or member of another.
_COUPLE_KINDS = (
    "Java Typed", "Java Create", "Java Use Cast", "Java Extend Couple", "Java Extend Couple External",
    "Java Implement Couple", "Java Call", "Java Call Nondynamic", "Java Use", "Java Use Return", "Java Set",
    "Java Modify", "Java Use Annotation", "Java Throw", "Java Typed GenericArgument", "Java Use GenericArgument",
    "Java Use Deref Partial",
)


def _write_couples(written):
    """``Java Couple`` between classes: A couples to B when code inside A names B, or a member B declares.

    Read back from the references already written (a member's class is its parent; an external member's
    is the type its long name starts with), and put at the coupled class's own declaration.
    """
    flush_reference_writes()
    classes = {}
    for kfile, file_ent in written:
        for longname, rec in kfile.classes.items():
            row = _row_at(*rec["key"])
            if row is not None:
                classes[row._id] = (file_ent, rec["key"][1], rec["key"][2], row)
    if not classes:
        return
    kinds = [kind_id(k) for k in _COUPLE_KINDS]
    cache: dict = {}

    def ent(i):
        if i is None:
            return None
        if i not in cache:
            cache[i] = EntityModel.get_or_none(EntityModel._id == i)
        return cache[i]

    def is_type(e):
        return e is not None and kind_family(e._kind_id) == "type" and "GenericParameter" not in _kind_name(e._kind_id)

    def type_of(e):
        seen = 0
        while e is not None and seen < 40 and not is_type(e):
            if "Package" in _kind_name(e._kind_id) or "File" in _kind_name(e._kind_id):
                return None
            parent = ent(e._parent_id)
            if parent is None and "." in (e._longname or ""):      # an external member: its class by name
                prefix = e._longname.rsplit(".", 1)[0]
                parent = next((r for r in entity_rows(prefix) if is_type(r)), None)
            e, seen = parent, seen + 1
        return e if is_type(e) else None

    def owner_class(e):
        seen = 0
        while e is not None and seen < 40 and not (is_type(e) and e._id in classes):
            e, seen = ent(e._parent_id), seen + 1
        return e if e is not None and e._id in classes else None

    pairs = set()
    for ref in ReferenceModel.select().where(
        ReferenceModel._kind_id.in_(kinds), ReferenceModel._file_id.in_([f._id for _, f in written])
    ):
        a = owner_class(ent(ref._scope_id))
        b = type_of(ent(ref._ent_id))
        if a is not None and b is not None and a._id != b._id:
            pairs.add((a._id, b._id))
    for a_id, b_id in sorted(pairs):
        file_ent, line, col, row = classes[a_id]
        _pair("Java Couple", "Java Coupleby", file_ent, line, col, row, ent(b_id))


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
    "annotation": ("Java Use Annotation", "Java Useby Annotation"),
    "set": ("Java Set", "Java Setby"),
    "modify": ("Java Modify", "Java Modifyby"),
}


def _fold_facades(kfiles) -> None:
    """Java reaches a top-level function through its file's facade class, ``FooKt.helper(2)``: the Java passes
    made an entity ``p.FooKt.helper`` at the function's position (``kotlin_interop``), and that is the Kotlin
    entity ``p.helper``. Re-point what refers to the first at the second and drop it."""
    from openunderstand.ounderstand import kotlin_interop

    for kfile in kfiles:
        for callable_, ghost_name in kotlin_interop.facade_functions(kfile):
            ghost = _row_at(ghost_name, *callable_["key"][1:]) if entity_rows(ghost_name) else None
            real = _row_at(*callable_["key"])
            if ghost is None or real is None or ghost._id == real._id or not is_placeholder_kind(ghost._kind_id):
                continue
            for field in (ReferenceModel._ent, ReferenceModel._scope):
                ReferenceModel.update({field: real._id}).where(field == ghost._id).execute()
            EntityModel.update({EntityModel._parent: real._id}).where(EntityModel._parent == ghost._id).execute()
            ghost.delete_instance()
            forget_entity_rows()


def _deref_variant(occ, forward: str, inverse: str):
    """A name followed by ``.member`` is only partly read, set or modified: Understand's Deref Partial kinds."""
    if occ["m"] != "use" or not occ.get("deref"):
        return forward, inverse
    word = {"set": "Set", "modify": "Modify"}.get(occ["deref"], "Use")
    return f"Java {word} Deref Partial", f"Java {word}by Deref Partial"


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


def _java_method_row(owner: str, name: str, nargs: int, site=None):
    """The Java method row a call with ``nargs`` arguments names, or ``None`` when not unique.

    ``site`` is the (line, column) the resolver already chose by argument type."""
    from openunderstand.ounderstand import symbol_table

    longname = f"{owner}.{name}"
    rows = [r for r in entity_rows(longname) if kind_family(r._kind_id) == "method"]
    if len(rows) == 1:
        return rows[0]
    if not isinstance(site, tuple):
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
    if kind == "annot":
        entry = index.classes.get(outcome[1])
        if entry is None or getattr(entry[0], "library", False):
            return [("annotation", _library_entity(outcome[1]))]
        return [("annotation", _row_at(*entry[1]["key"]))]
    if kind == "create":
        kf, rec = index.classes[outcome[1]]
        if getattr(kf, "library", False):
            return [("create", _library_entity(outcome[1]))]
        return [("create", _row_at(*rec["key"]))]
    if kind == "jcall":
        return [("call", _java_method_row(outcome[1], outcome[2], outcome[3], outcome[4] if len(outcome) > 4 else None))]
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
        scope = _owner_row(occ.get("w") or occ["o"], file_ent)
        if occ.get("pk") and scope is not None:           # a lambda parameter: nothing else resolves it
            param = _row_at(*occ["pk"])
            if param is not None and not outcome:
                forward, inverse = _deref_variant(occ, *_POSITIONAL[occ["m"]])
                for name, owner, ent in ((forward, scope, param), (inverse, param, scope)):
                    ReferenceModel.get_or_create(
                        _kind=kind_id(name), _file=file_ent, _line=occ["l"], _column=col_1based(occ["c"]),
                        _ent=ent, _scope=owner,
                    )
        if not outcome or scope is None:
            continue
        for item in outcome:
            for label, row in _targets(item, index):
                if row is None:
                    continue
                forward, inverse = _POSITIONAL[occ["m"] if label == "var" else label]
                # a library property is a placeholder, and a partial dereference is of a variable the project declares
                if label == "var" and not is_placeholder_kind(row._kind_id):
                    forward, inverse = _deref_variant(occ, forward, inverse)
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
    with jdk_index.libraries():
        return _analyse(paths, root)


def _analyse(paths, root: str | None = None) -> kotlin_parser.Summary:
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
            written.append((kfile, _write_declarations(p, kfile, resolver)))
        for kfile, file_ent in written:
            _write_typed(kfile, file_ent)
            _write_super_qualifiers(kfile, file_ent)
            _write_receivers(kfile, file_ent)
            _write_annotations(kfile, file_ent)
            _write_type_args(kfile, file_ent)
        for kfile, file_ent in written:
            _write_supers(kfile, file_ent, resolver)
            _write_implicit_supers(kfile, file_ent)
            _write_overrides(kfile, file_ent, resolver)
            _write_owned_types(kfile, file_ent, kfile.casts, "Java Use Cast", "Java Useby Castby")
            _write_owned_types(kfile, file_ent, kfile.throws, "Java Throw", "Java Throwby")
            _write_owned_types(kfile, file_ent, kfile.bounds, "Java Use Constrains Couple", "Java Useby Constrains Coupleby")
            _write_set_inits(kfile, file_ent)
            _write_references(kfile, file_ent, resolver)
            _write_imports(kfile, file_ent, resolver)
        flush_reference_writes()
        _fold_facades([kfile for kfile, _ in written])
        _write_couples(written)
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
