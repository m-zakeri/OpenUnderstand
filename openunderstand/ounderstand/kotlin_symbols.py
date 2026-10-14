"""Resolve Kotlin calls and names against the project, Java and the libraries.

``kotlin_expressions`` records what is written; this decides what it means, from
the facts every Kotlin file produced plus three other sources of declarations:

* the **Kotlin standard library**, from ``oudb/kotlin_index`` -- generated from its
  own source, shaped like a project file, so ``println``, ``listOf`` and
  ``list.map { }`` are looked up exactly as a project function is;
* the project's **Java** classes, through ``symbol_table`` (a Kotlin file calling
  Java code in the same project);
* the **JDK**, through ``jdk_index``, with the handful of JDK types Kotlin sees as
  its own (``java.util.List`` is ``kotlin.collections.MutableList``) mapped over.

It needs no database. ``Index`` is built from facts alone (so an update rebuilds only
what changed) and ``Resolver`` answers, for one occurrence, which declaration it
refers to.

**It refuses before it guesses.** A resolution is returned only when exactly one
declaration fits; two candidates, an unknown receiver type, a supertype this cannot
see into (which might declare the name) or a name that may belong to a lambda's
implicit receiver all give ``None``, and the caller writes no reference. Kotlin's
resolution is subtle and a wrong target is worse than a missing one.

What it resolves: a bare name or call through, in order, local functions, then each
implicit receiver's members and extensions (innermost first), then top-level
functions by Kotlin's precedence (explicit import, same package, ``*`` import,
default import), then constructors; and a qualified name or call on a receiver whose
type is known -- ``this``, a typed variable or property, a literal, a cast, a
constructor, a call to a function with a declared (or trivially inferred) return
type, a class or object name. Members are found level by level up the hierarchy, so
an override hides what it overrides. What it does not: overloads that differ only by
argument type (arity only), infix and operator calls, ``invoke``, a Java getter read
as a Kotlin property, and a receiver the project cannot type.
"""

from __future__ import annotations

from openunderstand.oudb import jdk_index, kotlin_index
from openunderstand.ounderstand import symbol_table

#: Library functions that give their lambda a receiver, used only when the callee
#: itself is not found: a callee found in the project or the stdlib index is judged by
#: its own parameter types instead.
RECEIVER_LAMBDAS = frozenset(
    "apply run with buildString buildList buildMap buildSet buildSequence sequence iterator "
    "launch async runBlocking coroutineScope supervisorScope withContext produce actor flow "
    "channelFlow callbackFlow withTimeout withTimeoutOrNull dependencies plugins repositories "
    "tasks".split()
)

#: JDK types Kotlin sees as its own, so an extension declared on the Kotlin type applies
#: to a value the JDK declares. The mutable Kotlin interface is used where the JDK type is
#: mutable, as Kotlin does.
KOTLIN_FOR = {
    "java.lang.Object": "kotlin.Any",
    "java.lang.String": "kotlin.String",
    "java.lang.CharSequence": "kotlin.CharSequence",
    "java.lang.Comparable": "kotlin.Comparable",
    "java.lang.Number": "kotlin.Number",
    "java.lang.Throwable": "kotlin.Throwable",
    "java.lang.Exception": "kotlin.Exception",
    "java.lang.RuntimeException": "kotlin.RuntimeException",
    "java.lang.Error": "kotlin.Error",
    "java.lang.Enum": "kotlin.Enum",
    "java.lang.Iterable": "kotlin.collections.MutableIterable",
    "java.util.Iterator": "kotlin.collections.MutableIterator",
    "java.util.ListIterator": "kotlin.collections.MutableListIterator",
    "java.util.Collection": "kotlin.collections.MutableCollection",
    "java.util.List": "kotlin.collections.MutableList",
    "java.util.Set": "kotlin.collections.MutableSet",
    "java.util.Map": "kotlin.collections.MutableMap",
    "java.util.Map.Entry": "kotlin.collections.MutableMap.MutableEntry",
}

AMBIGUOUS = object()   # a level declares the name but no single declaration fits
OPAQUE = ("opaque",)   # a supertype this cannot see into


def library_type(longname: str) -> bool:
    return kotlin_index.known(longname) or jdk_index.known(longname)


def lookup_type(name: str, kfile, enclosing, project_has):
    """Where ``name`` points from ``kfile``: ``("project", longname)``, ``("lib", fq)`` or ``None``.

    Kotlin's order: the enclosing scopes (nested types), explicit imports and
    aliases, the file's package, ``*`` imports, the default imports, then the name
    as written. A project declaration beats a library type at the same step.
    """
    first = name.split(".", 1)[0]
    rest = name[len(first):]
    package_depth = len(kfile.package.split(".")) if kfile.package else 0
    steps = [[".".join(enclosing[:d]) + "." + name for d in range(len(enclosing), package_depth, -1)]]
    steps.append([fq + rest for fq, alias, star in kfile.imports if not star and (alias or fq.rsplit(".", 1)[-1]) == first])
    steps.append([f"{kfile.package}.{name}" if kfile.package else name])
    steps.append([f"{fq}.{name}" for fq, alias, star in kfile.imports if star])
    steps.append([f"{p}.{name}" for p in (*kotlin_index.DEFAULT_PACKAGES, "java.lang")])
    steps.append([name])
    for candidates in steps:
        for candidate in candidates:
            if project_has(candidate):
                return ("project", candidate)
            if library_type(candidate):
                return ("lib", candidate)
    return None


def _arity_ok(rec, nargs: int) -> bool:
    params = rec["params"]
    required = sum(1 for default, vararg, _ in params if not default and not vararg)
    if any(vararg for _, vararg, _ in params):
        return nargs >= required
    return required <= nargs <= len(params)


def _java_arity_ok(written: tuple, nargs: int) -> bool:
    variadic = bool(written) and written[-1].endswith("...")
    return len(written) == nargs or (variadic and nargs >= len(written) - 1)


def _contains(desc, marker) -> bool:
    if isinstance(desc, tuple):
        return (desc and desc[0] == marker) or any(_contains(x, marker) for x in desc[1:] if isinstance(x, tuple))
    return False


class Index:
    """Everything the project and the Kotlin standard library declare, keyed for lookup."""

    def __init__(self, kfiles):
        project = list(kfiles)
        self.files = {k.path: k for k in project}
        self.classes: dict = {}           # longname -> (kfile, record)
        self.callables: dict = {}         # key -> (kfile, record)
        self.variables: dict = {}         # key -> (kfile, record)
        self.members_funs: dict = {}      # class longname -> name -> [(kfile, rec)]
        self.members_vars: dict = {}
        self.ctors: dict = {}             # class longname -> [(kfile, rec)]
        self.top_funs: dict = {}          # (package, name) -> [(kfile, rec)]
        self.top_vars: dict = {}
        self.nested: dict = {}            # class longname -> name -> longname
        self.aliases: dict = {}           # project typealias longname -> (kfile, target text, scope)
        for kf in project:
            for longname, _mods, target, scope in kf.aliases:
                if target:
                    self.aliases[longname] = (kf, target, scope)
        for kf in [*project, *kotlin_index.library_files()]:
            for ln, rec in kf.classes.items():
                self.classes[ln] = (kf, rec)
                head, _, name = ln.rpartition(".")
                self.nested.setdefault(head, {})[name] = ln
            for rec in kf.callables:
                self.callables[rec["key"]] = (kf, rec)
                if rec["ctor"]:
                    self.ctors.setdefault(rec["owner"], []).append((kf, rec))
                elif rec["local"]:
                    continue
                elif rec["owner"] is None:
                    self.top_funs.setdefault((kf.package, rec["name"]), []).append((kf, rec))
                else:
                    self.members_funs.setdefault(rec["owner"], {}).setdefault(rec["name"], []).append((kf, rec))
            for rec in kf.variables:
                self.variables[rec["key"]] = (kf, rec)
                if rec["kind"] != "property":
                    continue
                if rec["owner"] is None:
                    self.top_vars.setdefault((kf.package, rec["name"]), []).append((kf, rec))
                else:
                    self.members_vars.setdefault(rec["owner"], {}).setdefault(rec["name"], []).append((kf, rec))

    def has_class(self, longname: str) -> bool:
        return longname in self.classes


class Resolver:
    def __init__(self, index: Index):
        self.ix = index
        self._callee: dict = {}
        self._busy: set = set()
        self._hierarchy: dict = {}
        self._receivers: dict = {}

    # -- types -------------------------------------------------------------
    def _java(self, longname: str) -> bool:
        return bool(longname) and symbol_table.is_project_type(longname)

    def _has(self, longname: str) -> bool:
        return longname in self.ix.classes or longname in self.ix.aliases or self._java(longname) \
            or kotlin_index.alias_target(longname) is not None

    def expand(self, longname, depth=0):
        """A fully qualified type name as a type: Kotlin class, Java class, library type; aliases followed."""
        if not longname or depth > 6:
            return None
        ix = self.ix
        if longname in ix.classes:
            return ("class", longname)
        if longname in ix.aliases:
            kf, target, scope = ix.aliases[longname]
            return self.type_name(target, kf, scope, depth + 1)
        target = kotlin_index.alias_target(longname)
        if target:
            return self.expand(target, depth + 1)
        if self._java(longname):
            return ("java", longname)
        if jdk_index.known(longname) or kotlin_index.known(longname):
            return ("lib", longname)
        return None

    def type_name(self, name, kfile, scope, depth=0):
        """A written class name as a type, or ``None``."""
        if not name:
            return None
        if getattr(kfile, "library", False):
            return self.expand(name, depth)
        hit = lookup_type(name, kfile, scope, self._has)
        return self.expand(hit[1], depth) if hit else None

    def direct_supers(self, t):
        kind, ln = t
        out = []
        if kind == "class":
            kf, rec = self.ix.classes[ln]
            for text in rec["supers"]:
                out.append(self.type_name(text, kf, rec["scope"]) or OPAQUE)
        elif kind == "java":
            for written in symbol_table.INDEX.supertypes.get(ln, []):
                resolved = symbol_table._resolve_supertype(written, ln)
                out.append((self.expand(resolved) if resolved else None) or OPAQUE)
        elif kind == "lib":
            out.extend(("lib", s) for s in jdk_index.supertypes(ln))
            if ln in KOTLIN_FOR:
                out.append(("class", KOTLIN_FOR[ln]))
        return out

    def hierarchy(self, t):
        """``t`` and its supertypes, nearest first; ``OPAQUE`` marks a supertype not seen into."""
        cached = self._hierarchy.get(t)
        if cached is not None:
            return cached
        out, queue = [], [t]
        while queue:
            current = queue.pop(0)
            if current in out:
                continue
            out.append(current)
            if current != OPAQUE:
                queue.extend(self.direct_supers(current))
        if t[0] in ("class", "java", "lib") and ("class", "kotlin.Any") not in out:
            out.append(("class", "kotlin.Any"))     # every type is an Any
        self._hierarchy[t] = out
        return out

    def is_subtype(self, t, parent) -> bool:
        return parent in self.hierarchy(t)

    def class_chain(self, scope):
        """Enclosing classes of a scope, innermost first."""
        chain = []
        for d in range(len(scope), 0, -1):
            name = ".".join(scope[:d])
            if name in self.ix.classes:
                chain.append(name)
        return chain

    # -- one hierarchy level -------------------------------------------------
    def _fun_level(self, t, name, nargs):
        kind, ln = t
        if kind == "class":
            recs = self.ix.members_funs.get(ln, {}).get(name, [])
            return [("fun", r) for r in recs if _arity_ok(r[1], nargs)]
        if kind == "java":
            return self._java_funs(ln, name, nargs)
        if kind == "lib" and jdk_index.known(ln):
            declaring = jdk_index.declaring_type(ln, name, arity=nargs)
            return [("jdkfun", declaring, name)] if declaring else []
        return []

    def _java_funs(self, ln, name, nargs):
        entries = symbol_table.INDEX.methods.get(f"{ln}.{name}") or []
        fits = [e for e in entries if _java_arity_ok(e[0], nargs)]
        if len(fits) <= 1:
            return [("jfun", ln, name, nargs, 0)] if fits else []
        site = symbol_table.overload_site(f"{ln}.{name}", [None] * nargs)
        if site is not None:
            return [("jfun", ln, name, nargs, site)]
        return [("jfun", ln, name, nargs, i) for i in range(len(fits))]

    def _var_level(self, t, name):
        kind, ln = t
        if kind == "class":
            return [("var", r) for r in self.ix.members_vars.get(ln, {}).get(name, [])]
        if kind == "java":
            return [("jvar", ln, name)] if (ln, name) in symbol_table.INDEX.field_types else []
        if kind == "lib" and jdk_index.known(ln):
            declaring = jdk_index.declares_field(ln, name)
            return [("jdkvar", declaring, name)] if declaring else []
        return []

    @staticmethod
    def hit_key(hit):
        if hit[0] in ("fun", "var"):
            return hit[1][1]["key"]
        return hit

    def find(self, t, level):
        """The single declaration at the nearest hierarchy level that has one.

        ``AMBIGUOUS`` when that level has several, ``OPAQUE`` when nothing was found but
        a supertype could not be seen into, ``None`` when nothing declares it. A hit
        behind an unseen supertype is ambiguous: the unseen type might declare it too.
        """
        unseen = False
        for position, ty in enumerate(self.hierarchy(t)):
            if ty == OPAQUE:
                unseen = True
                continue
            hits = level(ty)
            if hits:
                if len({self.hit_key(h) for h in hits}) != 1:
                    return AMBIGUOUS
                return AMBIGUOUS if (unseen and position > 0) else hits[0]
        return OPAQUE if unseen else None

    def static_roots(self, ln):
        """Where ``Name.member`` looks for a class used as a receiver: the object itself, or its companion."""
        entry = self.ix.classes.get(ln)
        if entry is None:
            return []
        rec = entry[1]
        roots = [("class", ln)] if rec["object"] else []
        if rec["companion"]:
            roots.append(("class", rec["companion"]))
        return roots

    def find_member(self, rt, level):
        if rt is None:
            return None
        if rt[0] == "static":
            for root in self.static_roots(rt[1]):
                hit = self.find(root, level)
                if hit is not None:
                    return hit
            return None
        if rt[0] == "super":
            for ty in self.hierarchy(("class", rt[1]))[1:]:
                hit = self.find(ty, level)
                if hit is not None:
                    return hit
            return None
        return self.find(rt, level)

    # -- types of declarations ------------------------------------------------
    def var_type(self, kf, rec):
        key = rec["key"]
        if key in self._busy:
            return None
        if rec["declared"]:
            return self.type_name(rec["declared"], kf, rec["scope"])
        if rec["init"] is None:
            return None
        self._busy.add(key)
        try:
            return self.type_of(rec["init"], kf, rec["scope"], owner=key)
        finally:
            self._busy.discard(key)

    def return_type(self, kf, rec):
        if rec["ctor"]:
            return ("class", rec["owner"])
        if rec["ret"]:
            return self.type_name(rec["ret"], kf, rec["scope"])
        if rec["ret_init"] is None or rec["key"] in self._busy:
            return None
        self._busy.add(rec["key"])
        try:
            return self.type_of(rec["ret_init"], kf, rec["scope"], owner=rec["key"])
        finally:
            self._busy.discard(rec["key"])

    def hit_type(self, hit):
        """The type a resolved call or name evaluates to."""
        kind = hit[0]
        if kind == "fun":
            return self.return_type(*hit[1])
        if kind in ("ctor", "ctor_call"):
            return ("class", hit[1])
        if kind == "jctor":
            return ("java", hit[1])
        if kind == "libctor":
            return ("lib", hit[1])
        if kind == "jfun":
            return self.expand(symbol_table.return_type(hit[1], hit[2]))
        if kind == "jdkfun":
            return self.expand(jdk_index.return_type(hit[1], hit[2]))
        if kind == "var":
            return self.var_type(*hit[1])
        if kind == "jvar":
            return self.expand(symbol_table.member_type(hit[1], hit[2]))
        if kind == "jdkvar":
            return self.expand(jdk_index.field_type(hit[1], hit[2]))
        return None

    # -- the type of an expression -------------------------------------------
    def type_of(self, desc, kf, scope, owner=None):
        if desc is None:
            return None
        kind = desc[0]
        if kind == "lit":
            return self.expand(desc[1])
        if kind == "cast":
            return self.type_name(desc[1], kf, scope)
        if kind == "this":
            return self.this_type(kf, scope, owner)
        if kind == "super":
            chain = self.class_chain(scope)
            return ("super", chain[0]) if chain else None
        if kind == "name":
            _, name, binding = desc
            if binding is not None:
                if binding[0] == "local":
                    entry = self.ix.variables.get(binding[1])
                    return self.var_type(*entry) if entry else None
                return None
            hit = self.free_var(name, kf, scope, owner)
            if isinstance(hit, tuple):
                return self.hit_type(hit)
            if hit is not None:
                return None                # ambiguous or unseen: a name, but not a known one
            cls = self.type_name(name, kf, scope)
            if cls and cls[0] == "class":
                return ("static", cls[1])
            return cls                      # a Java or library class used as a receiver
        if kind == "member":
            _, recv, name = desc
            rt = self.type_of(recv, kf, scope, owner)
            hit = self.find_member(rt, lambda t, n=name: self._var_level(t, n))
            if isinstance(hit, tuple):
                return self.hit_type(hit)
            if rt is not None and rt[0] == "static":
                nested = self.ix.nested.get(rt[1], {}).get(name)
                if nested:
                    return ("static", nested)
            return None
        if kind == "call":
            call = self.call_target(desc[4], kf)
            return self.hit_type(call) if isinstance(call, tuple) else None
        return None

    def this_type(self, kf, scope, owner):
        entry = self.ix.callables.get(owner)
        if entry is not None and entry[1]["receiver"] and not entry[1]["ctor"]:
            return self.type_name(entry[1]["receiver"], entry[0], entry[1]["scope"])
        chain = self.class_chain(scope)
        return ("class", chain[0]) if chain else None

    # -- visibility of top-level declarations -----------------------------------
    @staticmethod
    def tiers(name, kf):
        """Where a top-level name may come from, strongest first: Kotlin's precedence."""
        explicit = []
        for fq, alias, star in kf.imports:
            if not star and (alias or fq.rsplit(".", 1)[-1]) == name:
                package, _, original = fq.rpartition(".")
                explicit.append((package, original))
        yield explicit
        yield [(kf.package, name)]
        yield [(fq, name) for fq, alias, star in kf.imports if star]
        yield [(p, name) for p in kotlin_index.DEFAULT_PACKAGES]

    def _top_funs_at(self, package, original):
        found = list(self.ix.top_funs.get((package, original), []))
        entry = self.ix.classes.get(package)       # `import a.Object.member`
        if entry is not None and entry[1]["object"]:
            found += self.ix.members_funs.get(package, {}).get(original, [])
        return found

    def _top_vars_at(self, package, original):
        found = list(self.ix.top_vars.get((package, original), []))
        entry = self.ix.classes.get(package)
        if entry is not None and entry[1]["object"]:
            found += self.ix.members_vars.get(package, {}).get(original, [])
        return found

    @staticmethod
    def _choose(candidates):
        """One distinct declaration out of these, ``AMBIGUOUS`` for several, ``None`` for none."""
        distinct = {c[1]["key"] for c in candidates}
        if not distinct:
            return None
        if len(distinct) > 1:
            # a fixed-arity overload beats a vararg one taking the same arguments
            fixed = [c for c in candidates if not any(p[1] for p in c[1]["params"])]
            if len({c[1]["key"] for c in fixed}) == 1 and len(fixed) < len(candidates):
                return ("fun", fixed[0])
            return AMBIGUOUS
        return ("fun", candidates[0])

    def top_level_hit(self, name, nargs, kf):
        for tier in self.tiers(name, kf):
            found = [c for pkg, orig in tier for c in self._top_funs_at(pkg, orig)
                     if c[1]["receiver"] is None and _arity_ok(c[1], nargs)]
            hit = self._choose(found)
            if hit is not None:
                return hit
        return None

    def extension_hit(self, rt, name, nargs, kf):
        """The extension function named ``name`` that applies to a receiver of type ``rt``."""
        applies = set(self.hierarchy(rt))
        for tier in self.tiers(name, kf):
            found = []
            for pkg, orig in tier:
                for kf2, rec in self.ix.top_funs.get((pkg, orig), []):
                    if rec["receiver"] is None or not _arity_ok(rec, nargs):
                        continue
                    if self._extension_applies(kf2, rec, applies):
                        found.append((kf2, rec))
            hit = self._choose(found)
            if hit is not None:
                return hit
        return None

    def _extension_applies(self, kf2, rec, applies) -> bool:
        text = rec["receiver"]
        if text == "*" or text in rec.get("tparams", ()):
            return True                      # `fun <T> T.also(...)`: any receiver
        key = rec["key"]
        if key not in self._receivers:
            self._receivers[key] = self.type_name(text, kf2, rec["scope"])
        receiver = self._receivers[key]
        return receiver is not None and receiver in applies

    # -- calls ---------------------------------------------------------------
    def call_target(self, occurrence_id, kf):
        """What a call occurrence resolves to (a hit tuple), or ``None``."""
        key = (kf.path, occurrence_id)
        if key in self._callee:
            return self._callee[key]
        self._callee[key] = None   # a call whose receiver depends on itself
        result = self._resolve_call(kf.occurrences[occurrence_id], kf)
        result = result if isinstance(result, tuple) else None
        self._callee[key] = result
        return result

    def _resolve_call(self, occ, kf):
        name, nargs, scope, owner = occ["n"], occ["a"], occ["s"], occ["o"]
        if occ.get("init"):
            return self._resolve_init(occ, kf)
        recv = occ["r"]
        if recv is None:
            binding = occ["b"]
            if binding is not None:
                if binding[0] == "fun":
                    cands = [self.ix.callables[k] for k in binding[1] if k in self.ix.callables]
                    return self._choose([c for c in cands if _arity_ok(c[1], nargs)])
                return None
            return self.free_call(name, nargs, kf, scope, owner)
        rt = self.type_of(recv, kf, scope, owner)
        if rt is None:
            return None
        return self.qualified_call(rt, name, nargs, kf)

    def constructor(self, t, nargs, exclude=None):
        kind, target = t
        if kind == "java":
            return ("jctor", target, nargs)
        if kind == "lib":
            return ("libctor", target)
        ctors = [c for c in self.ix.ctors.get(target, []) if c[1]["key"] != exclude]
        fits = [c for c in ctors if _arity_ok(c[1], nargs)]
        if len({c[1]["key"] for c in fits}) == 1:
            return ("ctor_call", target, fits[0])
        return ("ctor", target)   # the class is known, which of its constructors is not

    def _resolve_init(self, occ, kf):
        """``this(...)``, ``super(...)`` and a class header's ``: Base(...)``."""
        name, nargs, scope = occ["n"], occ["a"], occ["s"]
        chain = self.class_chain(scope)
        if name == "<this>":
            return self.constructor(("class", chain[0]), nargs, exclude=occ["o"]) if chain else None
        if name == "<super>":
            if not chain:
                return None
            for ty in self.hierarchy(("class", chain[0]))[1:]:
                if ty[0] == "class" and self.ix.classes[ty[1]][1]["decl"] != "interface":
                    return self.constructor(ty, nargs)
                if ty[0] in ("java", "lib"):
                    return self.constructor(ty, nargs)
            return None
        cls = self.type_name(name, kf, scope)
        return self.constructor(cls, nargs) if cls and cls[0] in ("class", "java", "lib") else None

    def implicit_receivers(self, kf, scope, owner):
        """The ``this`` values in scope, innermost first; ``None`` stands for one we cannot type."""
        out = []
        entry = self.ix.callables.get(owner)
        if entry is not None and entry[1]["receiver"] and not entry[1]["ctor"]:
            out.append(self.type_name(entry[1]["receiver"], entry[0], entry[1]["scope"]))
        for ln in self.class_chain(scope):
            out.append(("class", ln))
            companion = self.ix.classes[ln][1]["companion"]
            if companion:
                out.append(("class", companion))
        return out

    def free_call(self, name, nargs, kf, scope, owner):
        """An unqualified call, in Kotlin's order: each implicit receiver's members
        and then its extensions, innermost receiver first; then top-level functions;
        then a constructor."""
        for rt in self.implicit_receivers(kf, scope, owner):
            if rt is None:
                return None            # a type-parameter receiver: any name may be its member
            hit = self.find(rt, lambda t: self._fun_level(t, name, nargs))
            if hit is OPAQUE or hit is AMBIGUOUS:
                return None
            if hit is not None:
                return hit
            hit = self.extension_hit(rt, name, nargs, kf)
            if hit is AMBIGUOUS:
                return None
            if hit is not None:
                return hit
        hit = self.top_level_hit(name, nargs, kf)
        if hit is AMBIGUOUS:
            return None
        if hit is not None:
            return hit
        cls = self.type_name(name, kf, scope)
        if cls and cls[0] in ("class", "java", "lib"):
            return self.constructor(cls, nargs)
        return None

    def qualified_call(self, rt, name, nargs, kf):
        hit = self.find_member(rt, lambda t: self._fun_level(t, name, nargs))
        if hit is OPAQUE or hit is AMBIGUOUS:
            return None
        if hit is not None:
            return hit
        if rt[0] == "static":
            nested = self.ix.nested.get(rt[1], {}).get(name)
            if nested:
                return self.constructor(("class", nested), nargs)
            return None
        if rt[0] in ("class", "java", "lib", "super"):
            subject = ("class", rt[1]) if rt[0] == "super" else rt
            hit = self.extension_hit(subject, name, nargs, kf)
            return hit if hit is not AMBIGUOUS else None
        return None

    # -- bare names ----------------------------------------------------------
    def free_var(self, name, kf, scope, owner):
        """A hit, ``AMBIGUOUS``/``OPAQUE`` when the name exists but cannot be pinned, or ``None``."""
        for rt in self.implicit_receivers(kf, scope, owner):
            if rt is None:
                return OPAQUE
            hit = self.find(rt, lambda t: self._var_level(t, name))
            if hit is not None:
                return hit
        for tier in self.tiers(name, kf):
            found = [c for pkg, orig in tier for c in self._top_vars_at(pkg, orig) if c[1]["receiver"] is None]
            distinct = {c[1]["key"] for c in found}
            if len(distinct) == 1:
                return ("var", found[0])
            if distinct:
                return AMBIGUOUS
        return None

    # -- the entry point -----------------------------------------------------
    def receiver_lambda(self, call_id, position, kf) -> bool:
        occ = kf.occurrences[call_id]
        target = self.call_target(call_id, kf)
        if target is not None and target[0] == "fun":
            params = target[1][1]["params"]
            if not params:
                return False
            if position == -2:                 # a named argument: any parameter may be it
                return any(p[2] for p in params)
            return params[position if 0 <= position < len(params) else -1][2]
        if target is not None:
            return False                       # a Java or constructor callee: no receiver lambdas
        return occ["n"] in RECEIVER_LAMBDAS

    def blocked(self, occ, kf) -> bool:
        """Whether the occurrence sits in a lambda whose implicit receiver may own the name."""
        return any(self.receiver_lambda(call_id, pos, kf) for call_id, pos in occ["lam"])

    def resolve(self, occ, kf):
        """The declarations an occurrence refers to, as a list of tagged tuples, or ``[]``.

        ``("call", (kf, rec))``, ``("create", class)``, ``("var", (kf, rec))`` for Kotlin
        (project or standard library); ``("jcall", type, name, nargs)``,
        ``("jcreate", type, nargs)``, ``("jvar", type, name)`` for Java in the project;
        ``("jdkcall", type, name)``, ``("jdkvar", type, name)``, ``("libcreate", fq)``
        for the JDK and library classes.
        """
        if occ["r"] is None and self.blocked(occ, kf) and occ["b"] is None:
            return []
        if occ["r"] is not None and _contains(occ["r"], "this") and self.blocked(occ, kf):
            return []
        if occ["t"] == "call":
            target = self.call_target(occ["id"], kf)
            if target is None:
                return []
            init = occ.get("init")   # a delegation call creates nothing: the object exists
            kind = target[0]
            if kind == "fun":
                return [("call", target[1])]
            if kind == "ctor":
                return [] if init else [("create", target[1])]
            if kind == "ctor_call":
                return ([] if init else [("create", target[1])]) + [("call", target[2])]
            if kind == "jfun":
                return [("jcall", target[1], target[2], target[3])]
            if kind == "jctor":
                return [("jcall", target[1], target[1].rsplit(".", 1)[-1], target[2])] + \
                    ([] if init else [("jcreate", target[1], target[2])])
            if kind == "jdkfun":
                return [("jdkcall", target[1], target[2])]
            if kind == "libctor":
                return [] if init else [("libcreate", target[1])]
            return []
        # a name
        if occ["r"] is None:
            binding = occ["b"]
            if binding is not None:
                if binding[0] == "local" and binding[1] in self.ix.variables:
                    return [("var", self.ix.variables[binding[1]])]
                return []
            hit = self.free_var(occ["n"], kf, occ["s"], occ["o"])
        else:
            rt = self.type_of(occ["r"], kf, occ["s"], occ["o"])
            hit = self.find_member(rt, lambda t, n=occ["n"]: self._var_level(t, n))
        if not isinstance(hit, tuple):
            return []
        if hit[0] == "var":
            return [("var", hit[1])]
        if hit[0] == "jvar":
            return [("jvar", hit[1], hit[2])]
        if hit[0] == "jdkvar":
            return [("jdkvar", hit[1], hit[2])]
        return []
