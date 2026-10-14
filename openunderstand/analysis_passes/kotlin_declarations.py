"""What a Kotlin file declares: the first Kotlin entity pass, parse tree to facts.

Collects, with no database access, everything ``ounderstand.kotlin_project``
needs to write a file's entities: its package and imports, one ``addDefineRefs``
dictionary per declaration, and the declared type written on each declaration
that has one (for ``Java Typed``).

**Kinds are Java's.** Understand has no Kotlin vocabulary and this project
invents none, so a Kotlin class is a ``Java Class Type ...``, a function a
``Java Method ...``. A Kotlin entity is told apart by its file (``.kt``). Because
a kind name encodes modifiers, Kotlin's are mapped on the way in; with no
Understand oracle for Kotlin these rules are choices, not measurements:

* visibility: ``public`` unless written otherwise (Kotlin's default), and
  ``internal`` (module-wide) as ``Default``;
* ``final``: a class or method is final unless ``open``, ``abstract``,
  ``sealed``, an interface or an ``override``; a ``val`` and a ``const val`` are
  final;
* ``static``: top-level functions and properties, members of an ``object`` or
  a ``companion object``, and a nested class that is not ``inner``;
* ``abstract``: ``abstract`` or ``sealed`` classes, and any interface or abstract
  method written without a body.

**Declared**: the package; classes, interfaces, ``enum`` and ``annotation``
classes, objects and companion objects (a companion is a class named
``Companion`` unless named); enum entries; functions; primary and secondary
constructors; properties (a ``val``/``var`` constructor parameter is one);
parameters; type parameters; type aliases; and locals and ``for`` variables in
function bodies. A type alias has no kind of its own, so it is a class-kind
entity whose ``type`` reads ``typealias <target>``. **Not declared**: anything
inside a lambda, an anonymous function or an object literal, ``init`` blocks, accessors' parameters, and
catch/when-subject variables.

Long names are Java's shape: ``pkg.Outer.Inner.member``, a parameter or local
``pkg.Outer.fn.name``, a constructor ``pkg.C.C``. A top-level function or
property is ``pkg.name``, defined in its file.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from antlr4.tree.Tree import TerminalNode

from openunderstand.utils import kind_names as K

_RULE_CACHE: dict = {}
_SKIP = {"lambdaLiteral", "objectLiteral", "anonymousFunction"}
_VISIBILITY = {"public", "protected", "private"}


def rule(ctx) -> str | None:
    """The grammar rule a context came from (``None`` for a token)."""
    if isinstance(ctx, TerminalNode):
        return None
    cls = type(ctx)
    name = _RULE_CACHE.get(cls)
    if name is None:
        raw = cls.__name__[: -len("Context")]
        name = _RULE_CACHE[cls] = raw[0].lower() + raw[1:]
    return name


def children(ctx, name: str | None = None):
    return [
        c for c in (ctx.children or []) if name is None or rule(c) == name
    ]


def first(ctx, name: str):
    for c in ctx.children or []:
        if rule(c) == name:
            return c
    return None


def find(ctx, name: str):
    """The first descendant of rule ``name`` in pre-order, or ``None``."""
    for c in ctx.children or []:
        if rule(c) == name:
            return c
        if not isinstance(c, TerminalNode):
            hit = find(c, name)
            if hit is not None:
                return hit
    return None


def has_token(ctx, text: str) -> bool:
    return any(isinstance(c, TerminalNode) and c.getText() == text for c in ctx.children or [])


def source_text(ctx) -> str:
    start, stop = ctx.start, ctx.stop
    if stop is None:
        return ""
    return start.getInputStream().getText(start.start, stop.stop)


def _name(simple_identifier) -> tuple[str, int, int]:
    token = simple_identifier.start
    return token.text.strip("`"), token.line, token.column


@dataclass
class KFile:
    path: str
    package: str = ""
    package_pos: list = field(default_factory=list)  # (name, line, col) per segment
    imports: list = field(default_factory=list)  # (fqname, alias or None, star)
    defines: list = field(default_factory=list)  # addDefineRefs dictionaries
    types: list = field(default_factory=list)  # declared types to turn into Typed
    top_types: list = field(default_factory=list)  # (name, longname, line, col) for Contain
    aliases: list = field(default_factory=list)  # top-level typealiases: (longname, modifiers)


class _Collector:
    def __init__(self, path: str):
        self.out = KFile(path)
        self.package: list[str] = []

    # -- entry -------------------------------------------------------------
    def file(self, tree):
        header = find(tree, "packageHeader")
        ident = find(header, "identifier") if header is not None else None
        if ident is not None:
            for sid in children(ident, "simpleIdentifier"):
                self.out.package_pos.append(_name(sid))
            self.package = [n for n, _, _ in self.out.package_pos]
            self.out.package = ".".join(self.package)
        imports = first(tree, "importList")
        for imp in children(imports, "importHeader") if imports is not None else []:
            ident = first(imp, "identifier")
            alias = first(imp, "importAlias")
            self.out.imports.append(
                (
                    ident.getText().replace("`", ""),
                    _name(first(alias, "simpleIdentifier"))[0] if alias is not None else None,
                    has_token(imp, "*"),
                )
            )
        for top in children(tree, "topLevelObject"):
            member = first(top, "memberPropertyDeclaration")
            if member is not None:
                self.property(member, self.package, top_level=True, in_object=False)
            else:
                self.declaration(first(top, "declaration"), self.package, top_level=True, in_object=False)
        return self.out

    # -- helpers -----------------------------------------------------------
    def add(self, ident, scope, *, decl, type_text, ctx, modifiers, span=True, name=None, implicit=False):
        text, line, col = _name(ident) if ident is not None else (name, ctx.start.line, ctx.start.column)
        if name is not None:
            text = name
        scope_longname = ".".join(scope)
        stop = ctx.stop
        spanned = None
        if span and stop is not None and stop.text == "}":
            spanned = ((ctx.start.line, ctx.start.column), (stop.line, stop.column))
        top = len(scope) == len(self.package)
        self.out.defines.append(
            {
                "contents": source_text(ctx),
                "type": type_text,
                "decl": decl,
                "modifiers": list(modifiers),
                "span": spanned,
                "parent": ".".join(self.package),
                "scope": None if top else scope[-1],
                "ent": text,
                "scope_longname": "" if top else scope_longname,
                "ent_longname": (scope_longname + "." + text) if scope_longname else text,
                "line": line,
                "col": col,
                "implicit": implicit,
            }
        )
        return (scope_longname + "." + text) if scope_longname else text, line, col

    @staticmethod
    def mods(modifiers_ctx) -> set:
        if modifiers_ctx is None:
            return set()
        return {m.getText() for m in children(modifiers_ctx, "modifier")}

    @staticmethod
    def visibility(mods: set) -> list:
        for v in _VISIBILITY:
            if v in mods:
                return [v]
        return [] if "internal" in mods else ["public"]

    def typed(self, owner, type_ctx, scope):
        """Remember the named type written on a declaration, for ``Java Typed``."""
        named = named_type(type_ctx)
        if named is None:
            return
        name, line, col = named
        self.out.types.append(
            {
                "owner": owner,  # (longname, line, col) of the declared entity
                "name": name,
                "line": line,
                "col": col,
                "enclosing": list(scope),
            }
        )

    # -- declarations ------------------------------------------------------
    def declaration(self, decl, scope, *, top_level, in_object, owner=None):
        if decl is None:
            return
        for c in decl.children or []:
            name = rule(c)
            if name == "classDeclaration":
                self.klass(c, scope, top_level, in_object)
            elif name == "objectDeclaration":
                self.obj(c, scope, top_level)
            elif name == "functionDeclaration":
                self.function(c, scope, top_level, in_object, owner)
            elif name == "propertyDeclaration":
                self.property(c, scope, top_level, in_object)
            elif name == "typeAlias" and top_level:
                self.type_alias(c, scope)

    def type_alias(self, ctx, scope):
        """``typealias A<T> = Target``: a type name, so a class-family entity.

        There is no alias kind in the vocabulary, so it takes the plain class
        kind (a type family member other declarations can resolve to) and its
        ``type`` reads ``typealias <target>``, which is how a consumer tells it
        from a class. It is typed by its target when that names a class.
        """
        mods = self.mods(first(ctx, "modifiers"))
        ident = first(ctx, "simpleIdentifier")
        name = _name(ident)[0]
        target = [c for c in ctx.children or [] if rule(c) == "type_"][-1]
        out_mods = self.visibility(mods)
        if first(ctx, "typeParameters") is not None:
            out_mods.append("generic")
        longname, line, col = self.add(
            ident,
            scope,
            decl=K.CLASS,
            type_text="typealias " + target.getText(),
            ctx=ctx,
            modifiers=out_mods,
            span=False,
        )
        self.out.top_types.append((name, longname, line, col))
        self.out.aliases.append((longname, mods))
        inner = scope + [name]
        self.type_parameters(ctx, inner)
        self.typed((longname, line, col), target, inner)

    def type_parameters(self, ctx, scope_with_owner):
        tp = first(ctx, "typeParameters")
        if tp is None:
            return
        for param in children(tp, "typeParameter"):
            self.add(
                first(param, "simpleIdentifier"),
                scope_with_owner,
                decl=K.TYPE_PARAMETER,
                type_text=None,
                ctx=param,
                modifiers=(),
                span=False,
            )

    def klass(self, ctx, scope, top_level, in_object):
        mods = self.mods(first(ctx, "modifiers"))
        ident = first(ctx, "simpleIdentifier")
        is_interface = has_token(ctx, "interface")
        if is_interface:
            decl = K.INTERFACE
        elif "annotation" in mods:
            decl = K.ANNOTATION
        elif "enum" in mods or first(ctx, "enumClassBody") is not None:
            decl = K.ENUM
        else:
            decl = K.CLASS
        out_mods = self.visibility(mods)
        if decl == K.CLASS or decl == K.ENUM:
            if "abstract" in mods or "sealed" in mods:
                out_mods.append("abstract")
            elif not ({"open"} & mods) and decl == K.CLASS:
                out_mods.append("final")
            if "sealed" in mods:
                out_mods.append("sealed")
        elif "sealed" in mods:
            out_mods.append("sealed")
        if not top_level and "inner" not in mods:
            out_mods.append("static")
        if first(ctx, "typeParameters") is not None:
            out_mods.append("generic")
        longname, line, col = self.add(
            ident, scope, decl=decl, type_text="Class", ctx=ctx, modifiers=out_mods
        )
        inner = scope + [_name(ident)[0]]
        if top_level:
            self.out.top_types.append((_name(ident)[0], longname, line, col))
        self.type_parameters(ctx, inner)
        self.primary_constructor(ctx, inner, decl)
        self.members(first(ctx, "classBody"), inner, decl, in_object=False)
        enum_body = first(ctx, "enumClassBody")
        if enum_body is not None:
            for entries in children(enum_body, "enumEntries"):
                for entry in children(entries, "enumEntry"):
                    self.enum_entry(entry, inner)
            self.members(enum_body, inner, decl, in_object=False)

    def enum_entry(self, entry, scope):
        self.add(
            first(entry, "simpleIdentifier"),
            scope,
            decl=K.ENUM_CONSTANT,
            type_text=scope[-1],
            ctx=entry,
            modifiers=("public", "static", "final"),
        )
        body = first(entry, "classBody")
        if body is not None:
            self.members(body, scope + [_name(first(entry, "simpleIdentifier"))[0]], K.CLASS, in_object=False)

    def obj(self, ctx, scope, top_level):
        mods = self.mods(first(ctx, "modifiers"))
        ident = first(ctx, "simpleIdentifier")
        out_mods = self.visibility(mods) + ["final"]
        if not top_level:
            out_mods.append("static")
        longname, line, col = self.add(
            ident, scope, decl=K.CLASS, type_text="Class", ctx=ctx, modifiers=out_mods
        )
        if top_level:
            self.out.top_types.append((_name(ident)[0], longname, line, col))
        self.members(first(ctx, "classBody"), scope + [_name(ident)[0]], K.CLASS, in_object=True)

    def companion(self, ctx, scope):
        mods = self.mods(first(ctx, "modifiers"))
        ident = first(ctx, "simpleIdentifier")
        name = _name(ident)[0] if ident is not None else "Companion"
        self.add(
            ident,
            scope,
            decl=K.CLASS,
            type_text="Class",
            ctx=ctx,
            modifiers=self.visibility(mods) + ["final", "static"],
            name=name,
        )
        self.members(first(ctx, "classBody"), scope + [name], K.CLASS, in_object=True)

    def members(self, body, scope, owner_decl, in_object):
        if body is None:
            return
        listing = first(body, "classMemberDeclarations")
        if listing is None:
            return
        for member in children(listing, "classMemberDeclaration"):
            for c in member.children or []:
                name = rule(c)
                if name == "memberPropertyDeclaration":
                    self.property(c, scope, top_level=False, in_object=in_object)
                elif name == "declaration":
                    self.declaration(c, scope, top_level=False, in_object=in_object, owner=owner_decl)
                elif name in ("companionObject", "companionBlock"):
                    self.companion(c, scope)
                elif name == "secondaryConstructor":
                    self.secondary_constructor(c, scope)

    def primary_constructor(self, cls_ctx, scope, owner_decl):
        pc = first(cls_ctx, "primaryConstructor")
        if pc is None or owner_decl in (K.INTERFACE, K.ANNOTATION):
            return
        params = first(pc, "classParameters")
        mods = self.mods(first(pc, "modifiers"))
        cname = scope[-1]
        ctor_scope = scope + [cname]
        # the constructor's entity sits at the class name, as a record's does
        self.add(
            first(cls_ctx, "simpleIdentifier"),
            scope,
            decl=K.CONSTRUCTOR,
            type_text=None,
            ctx=pc,
            modifiers=self.visibility(mods),
            name=cname,
            span=False,
        )
        for cp in children(params, "classParameter") if params is not None else []:
            pmods = self.mods(first(cp, "modifiers"))
            ident = first(cp, "simpleIdentifier")
            type_ctx = first(cp, "type_")
            if has_token(cp, "val") or has_token(cp, "var"):
                fmods = self.visibility(pmods) if (_VISIBILITY & pmods) else ["public"]
                if has_token(cp, "val"):
                    fmods.append("final")
                longname, line, col = self.add(
                    ident, scope, decl=K.FIELD, type_text=type_ctx.getText(), ctx=cp, modifiers=fmods, span=False
                )
                self.typed((longname, line, col), type_ctx, scope)
            else:
                longname, line, col = self.add(
                    ident, ctor_scope, decl=K.PARAMETER, type_text=type_ctx.getText(), ctx=cp, modifiers=(), span=False
                )
                self.typed((longname, line, col), type_ctx, scope)

    def secondary_constructor(self, ctx, scope):
        mods = self.mods(first(ctx, "modifiers"))
        cname = scope[-1]
        self.add(
            None,
            scope,
            decl=K.CONSTRUCTOR,
            type_text=None,
            ctx=ctx,
            modifiers=self.visibility(mods),
            name=cname,
        )
        # position: the `constructor` keyword
        d = self.out.defines[-1]
        for c in ctx.children or []:
            if isinstance(c, TerminalNode) and c.getText() == "constructor":
                d["line"], d["col"] = c.symbol.line, c.symbol.column
        self.parameters(first(ctx, "functionValueParameters"), scope + [cname], scope)
        self.body(first(ctx, "block"), scope + [cname])

    def function(self, ctx, scope, top_level, in_object, owner=None):
        mods = self.mods(first(ctx, "modifiers"))
        ident = first(ctx, "simpleIdentifier")
        body = first(ctx, "functionBody")
        out_mods = self.visibility(mods)
        if "abstract" in mods or body is None:
            out_mods.append("abstract")
        elif owner in (K.INTERFACE, K.ANNOTATION):
            pass  # an interface method with a body is open
        elif not ({"open", "override"} & mods) or "final" in mods:
            out_mods.append("final")
        if top_level or in_object:
            out_mods.append("static")
        if first(ctx, "typeParameters") is not None:
            out_mods.append("generic")
        ret = None
        for c in ctx.children or []:
            if rule(c) == "type_":
                ret = c
        name, _, _ = _name(ident)
        longname, line, col = self.add(
            ident,
            scope,
            decl=K.METHOD,
            type_text=ret.getText() if ret is not None else "Unit",
            ctx=ctx,
            modifiers=out_mods,
        )
        inner = scope + [name]
        if ret is not None:
            self.typed((longname, line, col), ret, inner)   # inner: sees the function's <T>
        self.type_parameters(ctx, inner)
        self.parameters(first(ctx, "functionValueParameters"), inner, inner)
        if body is not None:
            self.body(body, inner)

    def parameters(self, params, owner_scope, type_scope):
        if params is None:
            return
        for fp in children(params, "functionValueParameter"):
            param = first(fp, "parameter")
            type_ctx = first(param, "type_")
            mods = self.mods(first(fp, "modifiers"))
            longname, line, col = self.add(
                first(param, "simpleIdentifier"),
                owner_scope,
                decl=K.PARAMETER,
                type_text=type_ctx.getText(),
                ctx=fp,
                modifiers=(),
                span=False,
            )
            self.typed((longname, line, col), type_ctx, type_scope)

    def property(self, ctx, scope, top_level, in_object):
        head = first(ctx, "propertyDeclarationHead")
        mods = self.mods(first(head, "modifiers"))
        is_val = has_token(head, "val")
        out_mods = self.visibility(mods)
        if is_val or "const" in mods:
            out_mods.append("final")
        if top_level or in_object:
            out_mods.append("static")
        for variable in self.variables(head):
            ident = first(variable, "simpleIdentifier")
            type_ctx = first(variable, "type_")
            longname, line, col = self.add(
                ident,
                scope,
                decl=K.FIELD,
                type_text=type_ctx.getText() if type_ctx is not None else None,
                ctx=ctx,
                modifiers=out_mods,
                span=False,
            )
            if type_ctx is not None:
                self.typed((longname, line, col), type_ctx, scope)

    @staticmethod
    def variables(head):
        single = first(head, "variableDeclaration")
        if single is not None:
            return [single]
        multi = first(head, "multiVariableDeclaration")
        return [first(e, "variableDeclaration") for e in children(multi, "destructuringEntry")] if multi is not None else []

    # -- bodies ------------------------------------------------------------
    def body(self, ctx, scope):
        """Locals, local functions and local classes in a function body.

        Skips lambdas, anonymous functions and object literals: what they
        declare belongs to a scope this pass does not model yet.
        """
        if ctx is None:
            return
        for c in ctx.children or []:
            name = rule(c)
            if name is None or name in _SKIP:
                continue
            if name == "propertyDeclaration":
                self.local(c, scope)
                self.body(c, scope)
            elif name == "classDeclaration":
                self.klass(c, scope, top_level=False, in_object=False)
            elif name == "objectDeclaration":
                self.obj(c, scope, top_level=False)
            elif name == "functionDeclaration":
                self.function(c, scope, top_level=False, in_object=False)
            elif name == "forStatement":
                for v in children(c, "variableDeclaration"):
                    self.local_variable(v, scope, c, ())
                for multi in children(c, "multiVariableDeclaration"):
                    for e in children(multi, "destructuringEntry"):
                        self.local_variable(first(e, "variableDeclaration"), scope, c, ())
                self.body(c, scope)
            else:
                self.body(c, scope)

    def local(self, ctx, scope):
        head = first(ctx, "propertyDeclarationHead")
        mods = ("final",) if has_token(head, "val") else ()
        for variable in self.variables(head):
            self.local_variable(variable, scope, ctx, mods)

    def local_variable(self, variable, scope, ctx, mods):
        type_ctx = first(variable, "type_")
        longname, line, col = self.add(
            first(variable, "simpleIdentifier"),
            scope,
            decl=K.LOCAL,
            type_text=type_ctx.getText() if type_ctx is not None else None,
            ctx=ctx,
            modifiers=mods,
            span=False,
        )
        if type_ctx is not None:
            self.typed((longname, line, col), type_ctx, scope)


def named_type(type_ctx):
    """``(dotted name, line, col)`` of the class a type names, or ``None``.

    The position is the last identifier, where Understand anchors a ``Typed``.
    A nullable ``T?`` and a parenthesised type name ``T``; a function type, an
    intersection and ``dynamic`` name no class, and type arguments are left to a
    later pass.
    """
    if type_ctx is None:
        return None
    ctx = type_ctx
    for _ in range(8):
        name = rule(ctx)
        if name == "type_":
            if first(ctx, "type_") is not None:  # `A & B`
                return None
            inner = None
            for c in ctx.children or []:
                if rule(c) in ("parenthesizedType", "nullableType", "typeReference", "functionType"):
                    inner = c
            if inner is None:
                return None
            ctx = inner
        elif name == "parenthesizedType":
            ctx = first(ctx, "type_")
        elif name == "nullableType":
            ctx = first(ctx, "typeReference") or first(ctx, "parenthesizedType")
        elif name == "typeReference":
            user = first(ctx, "userType")
            if user is None:
                return None
            parts = children(user, "simpleUserType")
            names = [_name(first(p, "simpleIdentifier"))[0] for p in parts]
            _, line, col = _name(first(parts[-1], "simpleIdentifier"))
            return ".".join(names), line, col
        else:
            return None
        if ctx is None:
            return None
    return None


def collect(tree, path: str) -> KFile:
    """The facts for one parsed ``.kt`` file."""
    return _Collector(path).file(tree)
