"""What Java sees of the Kotlin in a mixed project, as a contribution to the Java symbol table.

A Java pass resolves ``new Foo(1)``, ``f.bar()`` and ``Foo.Companion.make()`` against ``symbol_table.INDEX``,
which is built from the Java files only, so a call into Kotlin was left a bare unresolved name. This turns a
Kotlin file's facts into the same per-file dictionary a Java file contributes (``symbol_table.build``), so the
Java passes write real references to the Kotlin entities. Only a project that has Kotlin files pays for it.

Covered: classes, interfaces and objects (``Foo.INSTANCE``), nested and companion classes, their constructors
and public or protected member functions, with parameter and return types written the way Java writes them.
Top-level functions are static methods of the file's facade class (``FooKt.helper()``), which Java names but the
Kotlin entity (``p.helper``) does not: Java gets the facade, and ``kotlin_project`` folds what the Java passes
made of it into the Kotlin entity (``facade_name``, ``facade_functions``). Not covered, and left unresolved as
before: property accessors (``getName()``), ``@JvmStatic`` shortcuts, ``internal`` members (their JVM
names are mangled), and extension functions.
"""

from __future__ import annotations

#: Kotlin type names as Java writes them.
_JAVA_NAME = {
    "Int": "int", "Long": "long", "Boolean": "boolean", "Double": "double", "Float": "float",
    "Short": "short", "Byte": "byte", "Char": "char", "Unit": "void", "Any": "Object",
    "kotlin.Int": "int", "kotlin.Long": "long", "kotlin.Boolean": "boolean", "kotlin.Double": "double",
    "kotlin.Float": "float", "kotlin.Short": "short", "kotlin.Byte": "byte", "kotlin.Char": "char",
    "kotlin.Unit": "void", "kotlin.Any": "Object",
}


def java_type(written):
    """A Kotlin type name as Java text, or ``None`` when Java could not say (a function type)."""
    if not written or written.startswith("<"):
        return None
    return _JAVA_NAME.get(written, written)


def facade_name(kfile) -> str:
    """The JVM class holding a file's top-level functions: ``p.FooKt`` for ``p/Foo.kt``."""
    import os

    base = os.path.splitext(os.path.basename(kfile.path))[0]
    return ".".join([*([kfile.package] if kfile.package else []), base[:1].upper() + base[1:] + "Kt"])


def facade_functions(kfile):
    """The file's top-level functions Java can call: ``(callable, facade method long name)``."""
    facade = facade_name(kfile)
    return [
        (c, f"{facade}.{c['name']}") for c in kfile.callables
        if c.get("owner") is None and not c.get("ctor") and not c.get("local") and _visible(c.get("vis"))
    ]


def _visible(vis) -> bool:
    """Whether Java can name it: ``public`` and ``protected`` (``internal`` is mangled, ``private`` is hidden)."""
    return bool(vis) and bool({"public", "protected"} & set(vis))


def contribution(kfile) -> dict:
    """One Kotlin file's share of the Java index, in ``symbol_table.build``'s per-file shape."""
    path = kfile.path
    classes = {ln: rec for ln, rec in kfile.classes.items() if _visible(rec.get("vis")) or rec.get("decl") == "interface"}
    supertypes, superclasses, methods, overloads, returns, fields = {}, {}, {}, {}, {}, {}
    for longname, rec in classes.items():
        written = [s for s in rec.get("supers", ()) if s]
        if written:
            supertypes[longname] = written
        for sup in kfile.supers:
            if sup["owner"][0] == longname and sup.get("ctor"):
                superclasses[longname] = (sup["name"], path)
        if rec.get("object"):
            fields[(longname, "INSTANCE")] = longname.rsplit(".", 1)[-1]
        if rec.get("companion"):
            fields[(longname, "Companion")] = rec["companion"].rsplit(".", 1)[-1]
    for callable_ in kfile.callables:
        owner = callable_.get("owner")
        if owner not in classes or callable_.get("local") or not _visible(callable_.get("vis")):
            continue
        name = callable_["name"]
        types = tuple(java_type(t) or "Object" for t in (callable_.get("ptypes") or ["Object"] * len(callable_["params"])))
        if len(types) != len(callable_["params"]):
            types = tuple("Object" for _ in callable_["params"])
        longname = callable_["key"][0]
        _, line, column = callable_["key"]
        if callable_.get("ctor"):
            ctor = f"{owner}.{owner.rsplit('.', 1)[-1]}"
            overloads.setdefault(ctor, []).append((types, line, column + 1, path))
            continue
        if callable_.get("receiver"):
            continue                                                      # an extension is a static helper in Java
        methods.setdefault(longname, []).append((types, False, bool(callable_.get("tparams"))))
        overloads.setdefault(longname, []).append((types, line, column + 1, path))
        result = java_type(callable_.get("ret"))
        if result and result != "void":
            previous = returns.get(longname, result)
            returns[longname] = result if previous == result else ""
    functions = facade_functions(kfile)
    defines = [d for d in kfile.defines if d.get("ent_longname")]
    if functions:
        facade = facade_name(kfile)
        defines.append({"ent": facade.rsplit(".", 1)[-1], "ent_longname": facade, "decl": "class"})
        for callable_, longname in functions:
            _, line, column = callable_["key"]
            types = [java_type(t) or "Object" for t in (callable_.get("ptypes") or ["Object"] * len(callable_["params"]))]
            if len(types) != len(callable_["params"]):
                types = ["Object"] * len(callable_["params"])
            if callable_.get("receiver"):                                   # an extension takes its receiver first
                types.insert(0, java_type(callable_["receiver"].rsplit(".", 1)[-1]) or "Object")
            types = tuple(types)
            methods.setdefault(longname, []).append((types, False, bool(callable_.get("tparams"))))
            overloads.setdefault(longname, []).append((types, line, column + 1, path))
            result = java_type(callable_.get("ret"))
            if result and result != "void":
                previous = returns.get(longname, result)
                returns[longname] = result if previous == result else ""
    imports = {(alias or fq.rsplit(".", 1)[-1]): fq for fq, alias, star in kfile.imports if not star}
    wildcards = [fq for fq, _, star in kfile.imports if star]
    return {
        "supertypes": supertypes,
        "methods": methods,
        "overloads": overloads,
        "superclasses": superclasses,
        "return_types": {k: v for k, v in returns.items() if v},
        "generic_returns": {},
        "type_parameters": {ln: list(rec["tparams"]) for ln, rec in classes.items() if rec.get("tparams")},
        "qualified": {},
        "type_bounds": {},
        "field_types": fields,
        "imports": (imports, wildcards),
        "defines": defines,
    }
