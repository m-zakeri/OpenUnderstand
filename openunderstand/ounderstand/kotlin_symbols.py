"""Resolve Kotlin calls and names against the project's declarations.

``kotlin_expressions`` records what is written; this decides what it means, from
the facts every Kotlin file produced. It needs no database: ``Index`` is built
from the ``KFile`` facts alone (so an update rebuilds only what changed) and
``Resolver`` answers, for one occurrence, which declaration it refers to.

**It refuses before it guesses.** A resolution is returned only when exactly one
declaration fits; two candidates, an unknown receiver type or a name that could
belong to a lambda's implicit receiver all give ``None``, and the caller writes no
reference. Kotlin's resolution is subtle (overloads, extensions, inference,
implicit receivers) and a wrong target is worse than a missing one.

What it resolves: a bare name or call through, in order, local functions, the
extension receiver's members, the enclosing classes' members (inherited ones from
project supertypes and a companion's included), the package and imports; a
constructor call to a project class; and a qualified name or call on a receiver
whose type is known -- ``this``, a typed variable or property, a literal, a cast, a
constructor, a call to a function with a declared (or trivially inferred) return
type, a class or object used as a receiver -- including project extension
functions on it. What it does not: overloads that differ only by argument type
(arity only), infix and operator calls, invocations of function-typed values,
callees in Java or in a library, and a receiver the project cannot type.
"""

from __future__ import annotations

from openunderstand.oudb import jdk_index, kotlin_index

#: Library functions that give their lambda a receiver. An unqualified name inside
#: such a lambda may be a member of it, so it is not resolved. A project function
#: is judged by its own parameter types instead.
RECEIVER_LAMBDAS = frozenset(
    "apply run with buildString buildList buildMap buildSet buildSequence sequence iterator "
    "launch async runBlocking coroutineScope supervisorScope withContext produce actor flow "
    "channelFlow callbackFlow withTimeout withTimeoutOrNull dependencies plugins repositories "
    "tasks".split()
)


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


class Index:
    """Everything the project's Kotlin files declare, keyed for lookup."""

    def __init__(self, kfiles):
        self.files = {k.path: k for k in kfiles}
        self.classes: dict = {}           # longname -> (kfile, record)
        self.callables: dict = {}         # key -> (kfile, record)
        self.variables: dict = {}         # key -> (kfile, record)
        self.members_funs: dict = {}      # class longname -> name -> [(kfile, rec)]
        self.members_vars: dict = {}
        self.ctors: dict = {}             # class longname -> [(kfile, rec)]
        self.top_funs: dict = {}          # (package, name) -> [(kfile, rec)]
        self.top_vars: dict = {}
        self.nested: dict = {}            # class longname -> name -> longname
        for kf in kfiles:
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
        self.extensions = {}
        for (package, name), recs in self.top_funs.items():
            for kf, rec in recs:
                if rec["receiver"] is not None:
                    self.extensions.setdefault(name, []).append((kf, rec))

    def has_class(self, longname: str) -> bool:
        return longname in self.classes


def _arity_ok(rec, nargs: int) -> bool:
    params = rec["params"]
    required = sum(1 for default, vararg, _ in params if not default and not vararg)
    if any(vararg for _, vararg, _ in params):
        return nargs >= required
    return required <= nargs <= len(params)


def _contains(desc, marker) -> bool:
    if isinstance(desc, tuple):
        return (desc and desc[0] == marker) or any(_contains(x, marker) for x in desc[1:] if isinstance(x, tuple))
    return False


class Resolver:
    def __init__(self, index: Index):
        self.ix = index
        self._callee: dict = {}
        self._busy: set = set()

    # -- types -------------------------------------------------------------
    def type_name(self, name, kfile, scope):
        """A written class name as a type: ``("class", ln)``, ``("lib", fq)`` or ``None``."""
        if not name:
            return None
        hit = lookup_type(name, kfile, scope, self.ix.has_class)
        if hit is None:
            return None
        return ("class", hit[1]) if hit[0] == "project" else ("lib", hit[1])

    def supers(self, ln):
        """Project supertypes of a class, nearest first, without repeats."""
        out, queue = [], [ln]
        while queue:
            current = queue.pop(0)
            entry = self.ix.classes.get(current)
            if entry is None:
                continue
            kf, rec = entry
            for text in rec["supers"]:
                t = self.type_name(text, kf, rec["scope"])
                if t and t[0] == "class" and t[1] not in out and t[1] != ln:
                    out.append(t[1])
                    queue.append(t[1])
        return out

    def is_subtype(self, ln, parent) -> bool:
        return ln == parent or parent in self.supers(ln)

    def class_chain(self, scope):
        """Enclosing classes of a scope, innermost first."""
        chain = []
        for d in range(len(scope), 0, -1):
            name = ".".join(scope[:d])
            if name in self.ix.classes:
                chain.append(name)
        return chain

    # -- members -----------------------------------------------------------
    def member_funs(self, ln, name):
        found = []
        for cls in [ln, *self.supers(ln)]:
            found += self.ix.members_funs.get(cls, {}).get(name, [])
        return found

    def member_vars(self, ln, name):
        found = []
        for cls in [ln, *self.supers(ln)]:
            found += self.ix.members_vars.get(cls, {}).get(name, [])
        return found

    def with_companion(self, ln):
        """The class and, for its own members, its companion."""
        entry = self.ix.classes.get(ln)
        companion = entry[1]["companion"] if entry else None
        return [ln] + ([companion] if companion else [])

    # -- variables and callables as types -----------------------------------
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

    # -- the type of an expression -------------------------------------------
    def type_of(self, desc, kf, scope, owner=None):
        if desc is None:
            return None
        kind = desc[0]
        if kind == "lit":
            return ("lib", desc[1])
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
            target = self.free_var(name, kf, scope, owner)
            if target is not None:
                return self.var_type(*target)
            cls = self.type_name(name, kf, scope)
            return ("static", cls[1]) if cls and cls[0] == "class" else None
        if kind == "member":
            _, recv, name = desc
            rt = self.type_of(recv, kf, scope, owner)
            target = self.member_of(rt, name)
            if target is not None and target[0] == "var":
                return self.var_type(*target[1])
            if target is not None and target[0] == "class":
                return ("static", target[1])
            return None
        if kind == "call":
            call = self.call_target(desc[4], kf)
            if call is None:
                return None
            if call[0] == "fun":
                return self.return_type(*call[1])
            if call[0] in ("ctor", "ctor_call"):
                return ("class", call[1])
        return None

    def this_type(self, kf, scope, owner):
        entry = self.ix.callables.get(owner)
        if entry is not None and entry[1]["receiver"] and not entry[1]["ctor"]:
            return self.type_name(entry[1]["receiver"], entry[0], entry[1]["scope"])
        chain = self.class_chain(scope)
        return ("class", chain[0]) if chain else None

    def member_of(self, rt, name):
        """A property or nested class named ``name`` on a typed receiver."""
        if rt is None or rt[0] not in ("class", "static", "super"):
            return None
        classes = [rt[1]]
        if rt[0] == "super":
            classes = self.supers(rt[1])
        if rt[0] == "static":
            entry = self.ix.classes.get(rt[1])
            classes = self.with_companion(rt[1]) if entry and not entry[1]["object"] else [rt[1]]
        found = []
        for cls in classes:
            found += self.member_vars(cls, name)
        distinct = {rec["key"] for _, rec in found}
        if len(distinct) == 1:
            return ("var", found[0])
        if not distinct and rt[0] == "static":
            nested = self.ix.nested.get(rt[1], {}).get(name)
            if nested:
                return ("class", nested)
        return None

    # -- calls ---------------------------------------------------------------
    def call_target(self, occurrence_id, kf):
        """What a call occurrence resolves to: ``("fun", (kf, rec))``, ``("ctor", class)`` or ``None``."""
        key = (kf.path, occurrence_id)
        if key in self._callee:
            return self._callee[key]
        self._callee[key] = None   # a call whose receiver depends on itself
        occ = kf.occurrences[occurrence_id]
        result = self._resolve_call(occ, kf)
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
                    return self._pick([self.ix.callables[k] for k in binding[1] if k in self.ix.callables], nargs)
                return None
            return self.free_call(name, nargs, kf, scope, owner)
        rt = self.type_of(recv, kf, scope, owner)
        if rt is None:
            return None
        return self.qualified_call(rt, name, nargs, kf)

    def _resolve_init(self, occ, kf):
        """``this(...)``, ``super(...)`` and a class header's ``: Base(...)``."""
        name, nargs, scope = occ["n"], occ["a"], occ["s"]
        chain = self.class_chain(scope)
        if name == "<this>":
            return self.constructor(chain[0], nargs, exclude=occ["o"]) if chain else None
        if name == "<super>":
            if not chain:
                return None
            for parent in self.supers(chain[0]):
                if self.ix.classes[parent][1]["decl"] != "interface":
                    return self.constructor(parent, nargs)
            return None
        cls = self.type_name(name, kf, scope)
        if cls is None or cls[0] != "class":
            return None
        return self.constructor(cls[1], nargs)

    def _pick(self, candidates, nargs):
        fits = [c for c in candidates if _arity_ok(c[1], nargs)]
        distinct = {c[1]["key"] for c in fits}
        if len(distinct) == 1:
            return ("fun", fits[0])
        return None

    def constructor(self, class_ln, nargs, exclude=None):
        ctors = [c for c in self.ix.ctors.get(class_ln, []) if c[1]["key"] != exclude]
        if not ctors:
            return ("ctor", class_ln) if nargs == 0 else None
        fits = [c for c in ctors if _arity_ok(c[1], nargs)]
        if len({c[1]["key"] for c in fits}) == 1:
            return ("ctor_call", class_ln, fits[0])
        return ("ctor", class_ln)   # the class is known, which of its constructors is not

    def implicit_receivers(self, kf, scope, owner):
        """The ``this`` values in scope, innermost first; ``None`` stands for one we cannot type."""
        out = []
        entry = self.ix.callables.get(owner)
        if entry is not None and entry[1]["receiver"] and not entry[1]["ctor"]:
            out.append(self.type_name(entry[1]["receiver"], entry[0], entry[1]["scope"]))
        out += [("class", ln) for ln in self.class_chain(scope)]
        return out

    def extension_candidates(self, rt, name, kf):
        """Project extension functions named ``name`` that apply to a receiver of type ``rt``."""
        found = []
        for kf2, rec in self.visible_extensions(name, kf):
            receiver = self.type_name(rec["receiver"], kf2, rec["scope"])
            if receiver is None:
                continue
            if receiver == ("lib", "kotlin.Any"):
                found.append((kf2, rec))
            elif rt[0] == "lib" and receiver == rt:
                found.append((kf2, rec))
            elif rt[0] in ("class", "super") and receiver[0] == "class" and self.is_subtype(rt[1], receiver[1]):
                found.append((kf2, rec))
        return found

    def free_call(self, name, nargs, kf, scope, owner):
        """An unqualified call, in Kotlin's order: each implicit receiver's members
        and then its extensions, innermost receiver first; then top-level functions."""
        for rt in self.implicit_receivers(kf, scope, owner):
            if rt is None:
                return None            # a type-parameter receiver: any name may be its member
            if rt[0] == "class":
                cands = []
                for cls in self.with_companion(rt[1]):
                    cands += self.member_funs(cls, name)
                hit = self._pick(cands, nargs)
                if hit:
                    return hit
                if any(_arity_ok(c[1], nargs) for c in cands):
                    return None        # ambiguous at the innermost level that has it
            extensions = self.extension_candidates(rt, name, kf)
            hit = self._pick(extensions, nargs)
            if hit:
                return hit
            if any(_arity_ok(c[1], nargs) for c in extensions):
                return None
        hit = self._pick(self.top_level(name, kf, nargs), nargs)
        if hit:
            return hit
        cls = self.type_name(name, kf, scope)
        if cls and cls[0] == "class":
            return self.constructor(cls[1], nargs)
        return None

    def top_level(self, name, kf, nargs):
        """Top-level functions without a receiver visible from a file: package and imports."""
        found = list(self.ix.top_funs.get((kf.package, name), []))
        for fq, alias, star in kf.imports:
            if star:
                found += self.ix.top_funs.get((fq, name), [])
            elif (alias or fq.rsplit(".", 1)[-1]) == name:
                package, _, original = fq.rpartition(".")
                found += self.ix.top_funs.get((package, original), [])
        seen, out = set(), []
        for kf2, rec in found:
            if rec["receiver"] is None and rec["key"] not in seen:
                seen.add(rec["key"])
                out.append((kf2, rec))
        return out

    def visible_extensions(self, name, kf):
        found = []
        for kf2, rec in self.ix.extensions.get(name, []):
            package = kf2.package
            if package == kf.package or any(
                (star and fq == package) or (not star and fq == f"{package}.{name}") or (not star and alias and fq == f"{package}.{rec['name']}")
                for fq, alias, star in kf.imports
            ):
                found.append((kf2, rec))
        return found

    def qualified_call(self, rt, name, nargs, kf):
        kind, target = rt
        cands = []
        if kind in ("class", "super", "static"):
            classes = {"class": [target], "super": self.supers(target) if kind == "super" else [], "static": []}[kind]
            if kind == "static":
                entry = self.ix.classes.get(target)
                classes = self.with_companion(target) if entry and not entry[1]["object"] else [target]
            for cls in classes:
                cands += self.member_funs(cls, name)
            if kind == "static":
                nested = self.ix.nested.get(target, {}).get(name)
                if nested and not cands:
                    return self.constructor(nested, nargs)
        if not cands:
            cands = self.extension_candidates(rt, name, kf)
        return self._pick(cands, nargs)

    # -- bare names ----------------------------------------------------------
    def free_var(self, name, kf, scope, owner):
        entry = self.ix.callables.get(owner)
        if entry is not None and entry[1]["receiver"] and not entry[1]["ctor"]:
            rt = self.type_name(entry[1]["receiver"], entry[0], entry[1]["scope"])
            if rt is None:
                return None
            if rt[0] == "class":
                found = self.member_vars(rt[1], name)
                if len({r["key"] for _, r in found}) == 1:
                    return found[0]
        for ln in self.class_chain(scope):
            found = []
            for cls in self.with_companion(ln):
                found += self.member_vars(cls, name)
            distinct = {r["key"] for _, r in found}
            if len(distinct) == 1:
                return found[0]
            if distinct:
                return None
        found = list(self.ix.top_vars.get((kf.package, name), []))
        for fq, alias, star in kf.imports:
            if star:
                found += self.ix.top_vars.get((fq, name), [])
            elif (alias or fq.rsplit(".", 1)[-1]) == name:
                package, _, original = fq.rpartition(".")
                found += self.ix.top_vars.get((package, original), [])
        distinct = {r["key"] for _, r in found}
        return found[0] if len(distinct) == 1 else None

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
            return params[position if position >= 0 and position < len(params) else -1][2]
        return occ["n"] in RECEIVER_LAMBDAS

    def blocked(self, occ, kf) -> bool:
        """Whether the occurrence sits in a lambda whose implicit receiver may own the name."""
        return any(self.receiver_lambda(call_id, pos, kf) for call_id, pos in occ["lam"])

    def resolve(self, occ, kf):
        """The declaration an occurrence refers to, as a list of ``(kind, ...)`` or ``[]``.

        ``("call", (kf, rec))``, ``("create", class longname)``, ``("var", (kf, rec))``.
        """
        if occ["r"] is None and self.blocked(occ, kf):
            if occ["b"] is None:
                return []
        if occ["r"] is not None and _contains(occ["r"], "this") and self.blocked(occ, kf):
            return []
        if occ["t"] == "call":
            target = self.call_target(occ["id"], kf)
            if target is None:
                return []
            if target[0] == "fun":
                return [("call", target[1])]
            init = occ.get("init")   # a delegation call creates nothing: the object exists
            if target[0] == "ctor":
                return [] if init else [("create", target[1])]
            if target[0] == "ctor_call":
                return ([] if init else [("create", target[1])]) + [("call", target[2])]
            return []
        # a name
        if occ["r"] is None:
            binding = occ["b"]
            if binding is not None:
                if binding[0] == "local" and binding[1] in self.ix.variables:
                    return [("var", self.ix.variables[binding[1]])]
                return []
            target = self.free_var(occ["n"], kf, occ["s"], occ["o"])
            return [("var", target)] if target is not None else []
        rt = self.type_of(occ["r"], kf, occ["s"], occ["o"])
        target = self.member_of(rt, occ["n"])
        if target is not None and target[0] == "var":
            return [("var", target[1])]
        return []
