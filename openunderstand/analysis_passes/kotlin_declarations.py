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
inside a lambda, an anonymous function or an object literal, accessors'
parameters, and catch/when-subject variables.

**Facts for resolution.** Besides the entities, the collector records what
``kotlin_symbols`` needs to resolve calls and names later: ``classes`` (supertypes,
companion), ``callables`` (arity, extension receiver, return type), ``variables``
(declared type, or the initialiser's descriptor) and the ``occurrences`` the
expression walker (``kotlin_expressions``) finds in bodies and initialisers.

Long names are Java's shape: ``pkg.Outer.Inner.member``, a parameter or local
``pkg.Outer.fn.name``, a constructor ``pkg.C.C``. A top-level function or
property is ``pkg.name``, defined in its file.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from antlr4.tree.Tree import TerminalNode

from openunderstand.analysis_passes.kotlin_expressions import Env, ExprWalker
from openunderstand.analysis_passes.kotlin_tree import (
    children,
    find,
    first,
    has_token,
    name_of,
    named_type,
    name_pos as _name,
    rule,
    source_text,
    user_type_name,
)
from openunderstand.utils import kind_names as K

_VISIBILITY = {"public", "protected", "private"}


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
    classes: dict = field(default_factory=dict)  # longname -> supertypes, companion, ...
    callables: list = field(default_factory=list)  # functions and constructors
    variables: list = field(default_factory=list)  # properties, parameters, locals
    occurrences: list = field(default_factory=list)  # calls and names, unresolved


class _Collector:
    def __init__(self, path: str):
        self.out = KFile(path)
        self.package: list[str] = []
        self.class_envs: dict = {}  # class scope -> Env of its primary constructor's parameters
        self.primary_keys: dict = {}  # class scope -> its primary constructor's entity key

    # -- facts for resolution ---------------------------------------------
    def walker(self, owner, scope, env, receiver_lambda=False):
        return ExprWalker(self, owner, scope, env, receiver_lambda)

    def variable_fact(self, key, name, owner, kind, type_ctx=None, init=None, scope=(), vis=None, receiver=None):
        self.out.variables.append(
            {
                "key": key, "name": name, "owner": owner, "kind": kind,
                "declared": name_of(type_ctx) if type_ctx is not None else None,
                "init": init, "scope": tuple(scope), "vis": vis, "receiver": receiver,
            }
        )

    def callable_fact(self, key, name, owner, ctor, params, receiver, ret, ret_init, local, scope,
                      vis=None, tparams=(), ptypes=()):
        self.out.callables.append(
            {
                "key": key, "name": name, "owner": owner, "ctor": ctor, "params": params,
                "receiver": receiver, "ret": ret, "ret_init": ret_init, "local": local,
                "scope": tuple(scope), "vis": vis, "tparams": tuple(tparams),
                "ptypes": tuple(ptypes),    # one per parameter: a class name, "<fn>" or None (unknown)
            }
        )

    @staticmethod
    def type_parameter_names(ctx) -> tuple:
        tp = first(ctx, "typeParameters")
        return tuple(_name(first(p, "simpleIdentifier"))[0] for p in children(tp, "typeParameter")) if tp is not None else ()

    @staticmethod
    def owner_of(scope, top_level):
        return None if top_level else ".".join(scope)

    @staticmethod
    def data_components(cls_ctx, mods) -> list:
        """A data class's ``componentN`` order: its primary constructor's ``val``/``var`` parameters."""
        if "data" not in mods:
            return []
        pc = first(cls_ctx, "primaryConstructor")
        params = first(pc, "classParameters") if pc is not None else None
        return [
            _name(first(cp, "simpleIdentifier"))[0]
            for cp in (children(params, "classParameter") if params is not None else [])
            if has_token(cp, "val") or has_token(cp, "var")
        ]

    def supertypes(self, cls_ctx) -> list:
        specs = first(cls_ctx, "delegationSpecifiers")
        names = []
        for annotated in children(specs, "annotatedDelegationSpecifier") if specs is not None else []:
            spec = first(annotated, "delegationSpecifier")
            if spec is None:
                continue
            for inner in spec.children or []:
                user = None
                if rule(inner) == "userType":
                    user = inner
                elif rule(inner) in ("constructorInvocation", "explicitDelegation"):
                    user = first(inner, "userType")
                if user is not None:
                    names.append(user_type_name(user))
        return names

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
        return {m.getText().strip() for m in children(modifiers_ctx, "modifier")}

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
        self.out.aliases.append((longname, mods, name_of(target), tuple(scope)))
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
        self.out.classes[longname] = {
            "name": _name(ident)[0], "decl": decl, "object": False, "companion": None,
            "supers": self.supertypes(ctx), "scope": tuple(inner), "key": (longname, line, col),
            "vis": self.visibility(mods), "data": self.data_components(ctx, mods),
        }
        self.type_parameters(ctx, inner)
        self.primary_constructor(ctx, inner, decl)
        self.header_calls(ctx, inner, (longname, line, col))
        self.members(first(ctx, "classBody"), inner, decl, in_object=False)
        enum_body = first(ctx, "enumClassBody")
        if enum_body is not None:
            for entries in children(enum_body, "enumEntries"):
                for entry in children(entries, "enumEntry"):
                    self.enum_entry(entry, inner)
            self.members(enum_body, inner, decl, in_object=False)

    def header_calls(self, cls_ctx, scope, class_key):
        """The superclass constructors a class header invokes: ``class A : Base(x)``."""
        specs = first(cls_ctx, "delegationSpecifiers")
        for annotated in children(specs, "annotatedDelegationSpecifier") if specs is not None else []:
            spec = first(annotated, "delegationSpecifier")
            invocation = first(spec, "constructorInvocation") if spec is not None else None
            if invocation is None:
                continue
            owner = self.primary_keys.get(tuple(scope), class_key)
            env = Env(self.class_envs.get(tuple(scope)))
            self.walker(owner, scope, env).header_call(
                first(invocation, "userType"), first(invocation, "valueArguments")
            )

    def enum_entry(self, entry, scope):
        key = self.add(
            first(entry, "simpleIdentifier"),
            scope,
            decl=K.ENUM_CONSTANT,
            type_text=scope[-1],
            ctx=entry,
            modifiers=("public", "static", "final"),
        )
        self.out.variables.append(
            {"key": key, "name": _name(first(entry, "simpleIdentifier"))[0],
             "owner": ".".join(scope), "kind": "property", "declared": scope[-1],
             "init": None, "scope": tuple(scope), "vis": ["public"], "receiver": None}
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
        self.out.classes[longname] = {
            "name": _name(ident)[0], "decl": K.CLASS, "object": True, "companion": None,
            "supers": self.supertypes(ctx), "scope": tuple(scope + [_name(ident)[0]]),
            "key": (longname, line, col), "vis": self.visibility(mods),
        }
        self.members(first(ctx, "classBody"), scope + [_name(ident)[0]], K.CLASS, in_object=True)

    def companion(self, ctx, scope):
        mods = self.mods(first(ctx, "modifiers"))
        ident = first(ctx, "simpleIdentifier")
        name = _name(ident)[0] if ident is not None else "Companion"
        longname, line, col = self.add(
            ident,
            scope,
            decl=K.CLASS,
            type_text="Class",
            ctx=ctx,
            modifiers=self.visibility(mods) + ["final", "static"],
            name=name,
        )
        self.out.classes[longname] = {
            "name": name, "decl": K.CLASS, "object": True, "companion": None,
            "supers": self.supertypes(ctx), "scope": tuple(scope + [name]),
            "key": (longname, line, col), "vis": self.visibility(mods),
        }
        outer = self.out.classes.get(".".join(scope))
        if outer is not None:
            outer["companion"] = longname
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
                elif name == "anonymousInitializer":
                    owner = self.out.classes.get(".".join(scope))
                    if owner is not None:
                        env = Env(self.class_envs.get(tuple(scope)))
                        self.walker(owner["key"], scope, env).walk(c)

    def primary_constructor(self, cls_ctx, scope, owner_decl):
        pc = first(cls_ctx, "primaryConstructor")
        if pc is None or owner_decl in (K.INTERFACE, K.ANNOTATION):
            return
        params = first(pc, "classParameters")
        mods = self.mods(first(pc, "modifiers"))
        cname = scope[-1]
        ctor_scope = scope + [cname]
        # the constructor's entity sits at the class name, as a record's does
        ctor_key = self.add(
            first(cls_ctx, "simpleIdentifier"),
            scope,
            decl=K.CONSTRUCTOR,
            type_text=None,
            ctx=pc,
            modifiers=self.visibility(mods),
            name=cname,
            span=False,
        )
        env = Env()
        fact_params, defaults, ptypes = [], [], []
        for cp in children(params, "classParameter") if params is not None else []:
            pmods = self.mods(first(cp, "modifiers"))
            ident = first(cp, "simpleIdentifier")
            name = _name(ident)[0]
            type_ctx = first(cp, "type_")
            default = first(cp, "expression")
            if has_token(cp, "val") or has_token(cp, "var"):
                fmods = self.visibility(pmods) if (_VISIBILITY & pmods) else ["public"]
                if has_token(cp, "val"):
                    fmods.append("final")
                key = self.add(
                    ident, scope, decl=K.FIELD, type_text=type_ctx.getText(), ctx=cp, modifiers=fmods, span=False
                )
                self.typed(key, type_ctx, scope)
                self.variable_fact(key, name, ".".join(scope), "property", type_ctx, scope=scope, vis=self.visibility(pmods))
            else:
                key = self.add(
                    ident, ctor_scope, decl=K.PARAMETER, type_text=type_ctx.getText(), ctx=cp, modifiers=(), span=False
                )
                self.typed(key, type_ctx, scope)
                self.variable_fact(key, name, ctor_key[0], "param", type_ctx, scope=scope)
                env.names[name] = ("local", key)
            fact_params.append((default is not None, "vararg" in pmods, _fn_receiver(type_ctx)))
            ptypes.append(_param_type(type_ctx))
            if default is not None:
                defaults.append((ctor_key, default))   # a default value runs in the constructor
        self.class_envs[tuple(scope)] = env
        self.primary_keys[tuple(scope)] = ctor_key
        self.callable_fact(
            ctor_key, cname, ".".join(scope), True, fact_params, None, None, None, False, scope,
            vis=self.visibility(mods), ptypes=ptypes,
        )
        for key, default in defaults:
            self.walker(key, scope, Env(env)).walk(default)

    def secondary_constructor(self, ctx, scope):
        mods = self.mods(first(ctx, "modifiers"))
        cname = scope[-1]
        longname, line, col = self.add(
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
        key = (longname, d["line"], d["col"])
        inner = scope + [cname]
        infos = self.parameters(first(ctx, "functionValueParameters"), inner, scope, longname)
        env = Env()
        for info in infos:
            env.names[info["name"]] = ("local", info["key"])
        self.callable_fact(
            key, cname, ".".join(scope), True, [(i["default"], i["vararg"], i["fnrecv"]) for i in infos],
            None, None, None, False, inner, vis=self.visibility(mods),
            ptypes=[i["ptype"] for i in infos],
        )
        walker = self.walker(key, inner, env)
        for info in infos:
            if info["default_ctx"] is not None:
                walker.walk(info["default_ctx"])
        walker.walk(first(ctx, "constructorDelegationCall"))
        walker.walk(first(ctx, "block"))

    def function(self, ctx, scope, top_level, in_object, owner=None, env=None):
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
        key = (longname, line, col)
        inner = scope + [name]
        if ret is not None:
            self.typed(key, ret, inner)   # inner: sees the function's <T>
        self.type_parameters(ctx, inner)
        infos = self.parameters(first(ctx, "functionValueParameters"), inner, inner, longname)
        fenv = Env(env)
        for info in infos:
            fenv.names[info["name"]] = ("local", info["key"])
        walker = self.walker(key, inner, fenv)
        for info in infos:
            if info["default_ctx"] is not None:
                walker.walk(info["default_ctx"])
        ret_init = None
        if body is not None:
            for part in body.children or []:
                if rule(part) == "expression" and ret is None:
                    ret_init = walker.walk(part)
                else:
                    walker.walk(part)
        receiver = first(ctx, "receiverType")
        self.callable_fact(
            key, name, None if (top_level or env is not None) else ".".join(scope), False,
            [(i["default"], i["vararg"], i["fnrecv"]) for i in infos],
            name_of(receiver) if receiver is not None else None,
            name_of(ret) if ret is not None else None, ret_init, env is not None, inner,
            vis=self.visibility(mods), tparams=self.type_parameter_names(ctx),
            ptypes=[i["ptype"] for i in infos],
        )
        return key

    def parameters(self, params, owner_scope, type_scope, owner_longname=None):
        """Declare a function's parameters; returns what the callers need about each."""
        infos = []
        if params is None:
            return infos
        for fp in children(params, "functionValueParameter"):
            param = first(fp, "parameter")
            type_ctx = first(param, "type_")
            mods = self.mods(first(fp, "modifiers"))
            key = self.add(
                first(param, "simpleIdentifier"),
                owner_scope,
                decl=K.PARAMETER,
                type_text=type_ctx.getText(),
                ctx=fp,
                modifiers=(),
                span=False,
            )
            self.typed(key, type_ctx, type_scope)
            name = _name(first(param, "simpleIdentifier"))[0]
            self.variable_fact(key, name, owner_longname, "param", type_ctx, scope=type_scope)
            default = first(fp, "expression")
            infos.append(
                {"key": key, "name": name, "default": default is not None, "default_ctx": default,
                 "vararg": "vararg" in mods, "fnrecv": _fn_receiver(type_ctx),
                 "ptype": _param_type(type_ctx)}
            )
        return infos

    def property(self, ctx, scope, top_level, in_object):
        head = first(ctx, "propertyDeclarationHead")
        mods = self.mods(first(head, "modifiers"))
        is_val = has_token(head, "val")
        out_mods = self.visibility(mods)
        if is_val or "const" in mods:
            out_mods.append("final")
        if top_level or in_object:
            out_mods.append("static")
        keys = []
        for variable in self.variables(head):
            ident = first(variable, "simpleIdentifier")
            type_ctx = first(variable, "type_")
            key = self.add(
                ident,
                scope,
                decl=K.FIELD,
                type_text=type_ctx.getText() if type_ctx is not None else None,
                ctx=ctx,
                modifiers=out_mods,
                span=False,
            )
            if type_ctx is not None:
                self.typed(key, type_ctx, scope)
            keys.append((key, variable, type_ctx))
        if not keys:
            return
        # the first variable owns the code: an initialiser, a delegate, accessors
        key, variable, type_ctx = keys[0]
        env = Env(None if top_level else self.class_envs.get(tuple(scope)))
        receiver_lambda = _fn_receiver(type_ctx)
        walker = self.walker(key, scope, env, receiver_lambda)
        init = None
        for part in head.children or []:
            if rule(part) == "expression":
                init = walker.walk(part)
            elif rule(part) == "propertyDelegate":
                walker.walk(part)
        accessor_env = Env(env)
        accessor_env.names["value"] = ("shadow",)
        accessor_env.names["field"] = ("shadow",)
        accessors = self.walker(key, scope, accessor_env)
        for part in ctx.children or []:
            if rule(part) in ("propertyAccessors", "explicitBackingField"):
                accessors.walk(part)
        owner = None if top_level else ".".join(scope)
        receiver = first(head, "receiverType")
        for k, v, t in keys:
            self.variable_fact(
                k, _name(first(v, "simpleIdentifier"))[0], owner, "property", t,
                init=init if (t is None and len(keys) == 1) else None, scope=scope,
                vis=self.visibility(mods), receiver=name_of(receiver) if receiver is not None else None,
            )

    @staticmethod
    def variables(head):
        single = first(head, "variableDeclaration")
        if single is not None:
            return [single]
        multi = first(head, "multiVariableDeclaration")
        return [first(e, "variableDeclaration") for e in children(multi, "destructuringEntry")] if multi is not None else []

    # -- locals (called by the expression walker) ---------------------------
    def local(self, ctx, scope, env, init, entry_inits=None):
        """Declare a local (or each entry of ``val (a, b) = e``, typed by its ``componentN`` call)."""
        head = first(ctx, "propertyDeclarationHead")
        mods = ("final",) if has_token(head, "val") else ()
        variables = self.variables(head)
        for position, variable in enumerate(variables):
            if len(variables) == 1:
                value = init
            else:
                value = entry_inits[position] if entry_inits and position < len(entry_inits) else None
            key = self.local_variable(variable, scope, ctx, mods, value)
            env.names[_name(first(variable, "simpleIdentifier"))[0]] = ("local", key)

    def for_variables(self, ctx, scope, env, element=None, entry_inits=None):
        """Declare a ``for`` loop's variables; ``element`` types a single one, ``entry_inits`` each
        entry of ``for ((a, b) in ...)``."""
        found = [(v, ctx, element) for v in children(ctx, "variableDeclaration")]
        for multi in children(ctx, "multiVariableDeclaration"):
            for position, e in enumerate(children(multi, "destructuringEntry")):
                value = entry_inits[position] if entry_inits and position < len(entry_inits) else None
                found.append((first(e, "variableDeclaration"), ctx, value))
        for variable, owner_ctx, value in found:
            key = self.local_variable(variable, scope, owner_ctx, (), value)
            env.names[_name(first(variable, "simpleIdentifier"))[0]] = ("local", key)

    def local_variable(self, variable, scope, ctx, mods, init):
        type_ctx = first(variable, "type_")
        key = self.add(
            first(variable, "simpleIdentifier"),
            scope,
            decl=K.LOCAL,
            type_text=type_ctx.getText() if type_ctx is not None else None,
            ctx=ctx,
            modifiers=mods,
            span=False,
        )
        if type_ctx is not None:
            self.typed(key, type_ctx, scope)
        self.variable_fact(
            key, _name(first(variable, "simpleIdentifier"))[0], ".".join(scope), "local", type_ctx,
            init=init if type_ctx is None else None, scope=scope,
        )
        return key


def _param_type(type_ctx):
    """A parameter's type for overload applicability: a class name, ``"<fn>"`` or ``None``."""
    if type_ctx is None:
        return None
    if find(type_ctx, "functionType") is not None and name_of(type_ctx) is None:
        return "<fn>"
    return name_of(type_ctx)


def _fn_receiver(type_ctx) -> bool:
    """Whether a declared type is a function type with a receiver: ``T.() -> Unit``."""
    if type_ctx is None:
        return False
    fn = find(type_ctx, "functionType")
    return fn is not None and first(fn, "receiverType") is not None


def collect(tree, path: str) -> KFile:
    """The facts for one parsed ``.kt`` file."""
    return _Collector(path).file(tree)
