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
an override hides what it overrides. Types carry their type arguments (``Ty``): ``List<Point>``
yields ``Point`` for a loop, an index, ``first()`` or a lambda's ``it``, a call binds its own
type parameters from its receiver, arguments and lambdas, and an unknown or conflicting binding
is left unknown. What it does not: a Java getter read as a Kotlin property, bounds and
expected types steering inference, and a receiver the project cannot type.
"""

from __future__ import annotations

import re

from openunderstand.oudb import jdk_index, kotlin_index
from openunderstand.analysis_passes.kotlin_declarations import FILE_OWNER
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
    "java.lang.Integer": "kotlin.Int",
    "java.lang.Long": "kotlin.Long",
    "java.lang.Short": "kotlin.Short",
    "java.lang.Byte": "kotlin.Byte",
    "java.lang.Double": "kotlin.Double",
    "java.lang.Float": "kotlin.Float",
    "java.lang.Character": "kotlin.Char",
    "java.lang.Boolean": "kotlin.Boolean",
    "java.lang.Iterable": "kotlin.collections.MutableIterable",
    "java.util.Iterator": "kotlin.collections.MutableIterator",
    "java.util.ListIterator": "kotlin.collections.MutableListIterator",
    "java.util.Collection": "kotlin.collections.MutableCollection",
    "java.util.List": "kotlin.collections.MutableList",
    "java.util.Set": "kotlin.collections.MutableSet",
    "java.util.Map": "kotlin.collections.MutableMap",
    "java.util.Map.Entry": "kotlin.collections.MutableMap.MutableEntry",
}

#: Types whose operators the compiler inlines: `Int + Int` is arithmetic, not a call anyone
#: reads, and Java's analysis records none either. An operator or infix call whose
#: declaration belongs to one of these writes no reference.
INTRINSIC_OWNERS = frozenset(
    "kotlin." + n for n in "Int Long Short Byte Double Float Char Boolean UInt ULong UShort UByte String".split()
)
_ARRAYS = re.compile(r"kotlin\.[A-Za-z]*Array")

#: What a `for` loop over these does not call: the compiler loops over a range, an array or a
#: string directly, without an iterator object.
LOOP_INTRINSIC = frozenset(
    "kotlin.ranges." + n for n in
    "IntRange LongRange CharRange UIntRange ULongRange IntProgression LongProgression "
    "CharProgression UIntProgression ULongProgression".split()
) | {"kotlin.String", "kotlin.CharSequence"}

class Ty(tuple):
    """A resolved type: ``(kind, name)`` for equality and hashing, plus the type arguments it carries.

    Every comparison in this module (hierarchy membership, applicability, overload choice) is
    about the *erased* type, which is exactly what a 2-tuple does; the arguments ride along as an
    attribute so ``List<Point>`` and ``List<String>`` are the same key and still tell apart when
    an element type is asked. ``args`` holds a ``Ty`` or ``None`` (unknown) per argument.
    """

    args: tuple = ()

    def __new__(cls, kind, name, args=()):
        t = super().__new__(cls, (kind, name))
        t.args = tuple(args)
        return t

    def __repr__(self):
        return f"{self[1]}<{', '.join(map(repr, self.args))}>" if self.args else f"{self[1]}"


class _Library:
    """Stands for the file of a standard-library declaration, whose names are fully qualified."""

    library = True


LIB = _Library()


def _a(t) -> tuple:
    return getattr(t, "args", ())


def _parse_generic(text: str):
    """``java.util.Set<java.util.Map$Entry<K,V>>`` as ``(name, [args])`` and the text left over;
    ``? extends X`` reads as ``X`` and a bare ``?`` as the name ``?``."""
    i = 0
    while i < len(text) and text[i] not in "<>,":
        i += 1
    name, text = text[:i], text[i:]
    for bound in ("?extends", "?super"):
        if name.startswith(bound):
            name = name[len(bound):]
    args = []
    if text.startswith("<"):
        text = text[1:]
        while True:
            arg, text = _parse_generic(text)
            args.append(arg)
            if text.startswith(","):
                text = text[1:]
                continue
            if text.startswith(">"):
                text = text[1:]
            break
    return (name, args), text


def with_args(t, args):
    """``t`` carrying ``args``, or ``t`` unchanged when none of them is known."""
    return Ty(t[0], t[1], args) if t is not None and any(a is not None for a in args) else t


def _deep(t):
    """A key that tells ``List<Point>`` from ``List<String>``, which ``==`` on a ``Ty`` does not."""
    if t is None:
        return None
    return (t[0], t[1], tuple(_deep(a) for a in _a(t)))


def _pnames(expr) -> set:
    """The type parameters a type expression mentions."""
    if not isinstance(expr, tuple) or not expr:
        return set()
    if expr[0] == "p":
        return {expr[1]}
    out = set()
    for part in expr[1:]:
        if isinstance(part, tuple):
            if part and isinstance(part[0], str):
                out |= _pnames(part)
            else:
                for x in part:
                    out |= _pnames(x)
    return out


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
    # a `*` import never brings in a JDK type Kotlin maps to its own: `import java.util.*` leaves
    # `List` and `Map` the Kotlin ones
    steps.append([c for c in (f"{fq}.{name}" for fq, alias, star in kfile.imports if star) if c not in KOTLIN_FOR])
    steps.append([f"{p}.{name}" for p in (*kotlin_index.DEFAULT_PACKAGES, "java.lang")])
    steps.append([name])
    for candidates in steps:
        for candidate in candidates:
            if project_has(candidate):
                return ("project", candidate)
            if library_type(candidate):
                return ("lib", candidate)
    return None


def _arity_ok(rec, nargs) -> bool:
    if nargs is None:                  # a callable reference: any arity
        return True
    params = rec["params"]
    required = sum(1 for default, vararg, _ in params if not default and not vararg)
    if any(vararg for _, vararg, _ in params):
        return nargs >= required
    return required <= nargs <= len(params)


def _java_arity_ok(written: tuple, nargs) -> bool:
    if nargs is None:
        return True
    variadic = bool(written) and written[-1].endswith("...")
    return len(written) == nargs or (variadic and nargs >= len(written) - 1)


def _ckey(candidate):
    """Identity of a candidate declaration. A library function is one placeholder entity named
    by its long name however many overloads it has, so its overloads are not ambiguous."""
    kf, rec = candidate
    return rec["key"][0] if getattr(kf, "library", False) else rec["key"]


def _contains(desc, marker) -> bool:
    if isinstance(desc, tuple):
        return (desc and desc[0] == marker) or any(_contains(x, marker) for x in desc[1:] if isinstance(x, tuple))
    return False


#: What a Gradle Kotlin script imports without writing it (the DSL's extensions are in the first).
GRADLE_SCRIPT_PACKAGES = ("org.gradle.kotlin.dsl", "org.gradle.api", "org.gradle.api.plugins", "org.gradle.api.tasks",
                          "org.gradle.api.provider", "org.gradle.api.file", "org.gradle.api.artifacts")


#: The accessors Gradle generates for the extensions of its core plugins (``java { }``, ``sourceSets { }``). They are
#: generated per build, so no jar declares them; the lambda's receiver is the extension, which is what makes the
#: calls inside resolve. The accessor call itself names no declaration and writes nothing.
GRADLE_ACCESSORS = {
    "java": "org.gradle.api.plugins.JavaPluginExtension",
    "sourceSets": "org.gradle.api.tasks.SourceSetContainer",
    "base": "org.gradle.api.plugins.BasePluginExtension",
    "application": "org.gradle.api.plugins.JavaApplication",
    "publishing": "org.gradle.api.publish.PublishingExtension",
    "reporting": "org.gradle.api.reporting.ReportingExtension",
    "testing": "org.gradle.testing.base.TestingExtension",
}


#: Stdlib scope functions whose one parameter is named ``block``. The stdlib index carries no parameter names, so
#: ``apply(plugin = "x")`` in a Gradle script would otherwise be taken for ``T.apply(block)`` instead of ``Project.apply``.
_BLOCK_FUNCTIONS = frozenset({"apply", "also", "let", "run", "with", "takeIf", "takeUnless", "use", "repeat"})


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
        self.packages: set = set()        # every package the project's Kotlin files declare, prefixes too
        self.aliases: dict = {}           # project typealias longname -> (kfile, target text, scope, expr, tparams)
        for kf in project:
            parts = kf.package.split(".") if kf.package else []
            self.packages.update(".".join(parts[: i + 1]) for i in range(len(parts)))
            for longname, _mods, target, scope, *more in kf.aliases:
                if target:
                    texpr, tps = (more + [None, ()])[:2] if more else (None, ())
                    self.aliases[longname] = (kf, target, scope, texpr, tuple(tps or ()))
        ours = {kf.package for kf in project}
        third = kotlin_index.third_party_packages()
        # a library's rows for a package the project declares itself would only make every name ambiguous
        for kf in [*project, *[lf for lf in kotlin_index.library_files() if not (lf.package in third and lf.package in ours)]]:
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
        self._ref_arity = None      # (arity, unbound) a callable reference's expected function type asks for
        self._ctx = None            # the call being resolved: its arguments, for applicability
        self._ptypes: dict = {}
        self._infer: dict = {}      # (file, call id) -> the type parameters its call binds
        self._tainted: set = set()  # calls inferred while their enclosing call was still being resolved
        self._lambda_recv: list = []  # the implicit receivers of the lambdas around the occurrence being resolved
        self._lam_ctx = None          # (occurrence, file) being resolved: where `this` is asked from
        self._pending: set = set()    # calls being resolved right now
        self._cycle: set = set()      # the pending calls the computation in progress had to ask about
        self._assuper: dict = {}

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
            kf, target, scope, *_ = ix.aliases[longname]
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

    # -- type arguments ---------------------------------------------------------
    def tparams_of(self, t):
        """The type parameters a class declares, or ``None`` when its declaration is not seen."""
        if t is not None and t[0] == "class":
            entry = self.ix.classes.get(t[1])
            return tuple(entry[1].get("tparams") or ()) if entry else None
        return None

    def kclass(self, t):
        """``t`` as a Kotlin class carrying its arguments: the JDK's ``List`` is Kotlin's ``MutableList``."""
        if t is None:
            return None
        if t[0] == "class":
            return t
        if t[0] == "lib" and t[1] in KOTLIN_FOR and KOTLIN_FOR[t[1]] in self.ix.classes:
            k = ("class", KOTLIN_FOR[t[1]])
            return with_args(k, _a(t)) if len(self.tparams_of(k) or ()) == len(_a(t)) else k
        return None

    def class_env(self, t) -> dict:
        k = self.kclass(t)
        return dict(zip(self.tparams_of(k) or (), _a(k))) if k is not None and _a(k) else {}

    def inst(self, expr, env, kf, scope, depth=0):
        """A type expression as a type, with the type parameters in ``env`` replaced; ``None`` if unknown."""
        if not isinstance(expr, tuple) or depth > 6:
            return None
        if expr[0] == "p":
            if expr[1] in env or len(expr) < 3:
                return env.get(expr[1])
            return self.inst(expr[2], {}, kf, scope, depth + 1)      # unbound: its upper bound
        if expr[0] != "c":
            return None
        _, name, args = expr
        if getattr(kf, "library", False):
            fq = name
        else:
            hit = lookup_type(name, kf, scope, self._has)
            fq = hit[1] if hit else None
        if not fq:
            return None
        if fq not in self.ix.classes:
            alias = self.ix.aliases.get(fq)
            if alias is not None:
                akf, _text, ascope, aexpr, atps = alias
            else:
                known = kotlin_index.alias_expression(fq)
                akf, ascope, (atps, aexpr) = (LIB, (), known) if known else (None, None, (None, None))
            if aexpr is not None:
                inner = {tp: self.inst(a, env, kf, scope, depth + 1) for tp, a in zip(atps or (), args)}
                return self.inst(aexpr, inner, akf, ascope, depth + 1)
        base = self.expand(fq)
        if base is None:
            return None
        declared = self.tparams_of(base)
        if not args or (declared is not None and len(declared) != len(args)):
            return base
        return with_args(base, [self.inst(a, env, kf, scope, depth + 1) for a in args])

    def supers_g(self, t):
        """The direct supertypes of ``t`` with the arguments ``t`` gives them."""
        if t[0] == "class":
            kf, rec = self.ix.classes[t[1]]
            env = self.class_env(t)
            out = (self.inst(e, env, kf, rec["scope"]) for e in rec.get("super_exprs") or ())
            return [x for x in out if x is not None]
        if t[0] == "lib":
            out = []
            declared, generic = jdk_index.generic_supertypes(t[1])
            for raw in generic:                              # `TaskCollection<org.gradle.api.Task>`
                parsed = self._library_type(raw, dict(zip(declared, _a(t))))
                if parsed is not None:
                    out.append(parsed)
            written = {x[1] for x in out}
            for s in jdk_index.supertypes(t[1]):
                if s in written:
                    continue                                  # already there, with its arguments
                mapped = KOTLIN_FOR.get(s)
                same = mapped in self.ix.classes and len(self.tparams_of(("class", mapped)) or ()) == len(_a(t))
                out.append(Ty("lib", s, _a(t) if same else ()))
            k = self.kclass(t)
            if k is not None:
                out.append(k)
            return out
        return []

    def _library_type(self, text, env):
        """A javap type (``a.B<c.D, T>``) as a ``Ty``; a name in ``env`` is a type parameter bound there."""
        text = text.strip().replace("? super ", "").replace("? extends ", "")
        if text == "?":
            return None
        head, _, tail = text.partition("<")
        if head in env:
            return env[head]
        args, depth, current = [], 0, ""
        for ch in tail[:-1] if tail else "":
            depth += (ch == "<") - (ch == ">")
            if ch == "," and depth == 0:
                args.append(current)
                current = ""
            else:
                current += ch
        if current.strip():
            args.append(current)
        base = self.expand(head)
        if base is None:
            return None
        return with_args(base, [self._library_type(a, env) for a in args])

    def as_super(self, t, target, depth=0, seen=None):
        """``t`` seen as ``target`` (an erased type), with the arguments that gives it, or ``None``."""
        if t[:2] == target:
            return t
        if depth > 14:
            return None
        key = (_deep(t), target)
        if depth == 0 and key in self._assuper:
            return self._assuper[key]
        seen = seen if seen is not None else set()
        result = None
        if _deep(t) not in seen:
            seen.add(_deep(t))
            for sup in self.supers_g(t):           # a path that kept the arguments beats one that lost them
                found = self.as_super(sup, target, depth + 1, seen)
                if found is not None and (result is None or (_a(found) and not _a(result))):
                    result = found
                    if _a(found):
                        break
        if depth == 0:
            self._assuper[key] = result
        return result

    def member_env(self, owner, recv) -> dict:
        """The owner's type parameters as ``recv`` binds them, for a member found on ``recv``."""
        if not owner or recv is None or recv[0] not in ("class", "lib", "java") or not _a(recv):
            return {}
        seen = self.as_super(recv, ("class", owner))
        return self.class_env(seen) if seen is not None else {}

    def unify(self, expr, t, env, kf, scope, free):
        """Bind the type parameters ``expr`` mentions by matching it against the type ``t``.

        A parameter bound twice to unrelated types, or matched against an unknown, is poisoned
        to ``None`` rather than guessed: ``listOf(Circle(), Square())`` is not ``List<Circle>``.
        """
        if not isinstance(expr, tuple):
            return
        if t is None:
            for n in _pnames(expr):
                if n not in env:
                    env[n] = None
                    free.add(n)
            return
        if expr[0] == "p":
            n = expr[1]
            if n not in env:
                env[n] = t
                free.add(n)
            elif n in free and env[n] is not None and _deep(env[n]) != _deep(t):
                a, b = env[n], t
                if self.is_subtype(a, b):
                    env[n] = b
                elif not self.is_subtype(b, a):
                    env[n] = None
            return
        if expr[0] != "c" or not expr[2] or t[0] not in ("class", "lib", "java"):
            return
        target = self.type_name(expr[1], kf, scope) if not getattr(kf, "library", False) else self.expand(expr[1])
        seen = self.as_super(t, tuple(target[:2])) if target is not None else None
        if seen is None or len(_a(seen)) != len(expr[2]):
            for n in _pnames(expr):
                if n not in env:
                    env[n] = None
                    free.add(n)
            return
        for sub_expr, sub_t in zip(expr[2], _a(seen)):
            self.unify(sub_expr, sub_t, env, kf, scope, free)

    def infer(self, hit, kf, occ) -> dict:
        """The type parameters a resolved call binds: the receiver's, then the call's own.

        Stage one reads the receiver, the explicit ``<T>`` and the arguments' types; stage two
        reads what each lambda argument evaluates to, which may itself ask stage one's answer
        for its parameters -- so the dictionary is published before stage two runs.
        """
        key = (kf.path, occ["id"]) if occ is not None else None
        if key is not None and key in self._infer:
            return self._infer[key]
        env: dict = {}
        if key is not None:
            self._infer[key] = env
        free: set = set()
        kind = hit[0]
        if kind == "fun":
            kf2, rec = hit[1]
            recv = hit[2] if len(hit) > 2 else None
            if rec["owner"] and not rec["ctor"]:
                env.update(self.member_env(rec["owner"], recv))
            for tp in rec.get("tparams", ()):
                env.pop(tp, None)
            names, scope2 = tuple(rec.get("tparams", ())), rec["scope"]
            if rec.get("receiver_expr") is not None and recv is not None and recv[0] in ("class", "lib", "java"):
                self.unify(rec["receiver_expr"], recv, env, kf2, scope2, free)
            params = rec["params"]
            ptexprs = rec.get("ptexprs") or ()
        elif kind == "ctor_call":
            kf2, rec = hit[2]
            names, scope2 = tuple(self.tparams_of(("class", hit[1])) or ()), rec["scope"]
            params, ptexprs = rec["params"], rec.get("ptexprs") or ()
        elif kind == "ctor":
            names, kf2, scope2, params, ptexprs = tuple(self.tparams_of(("class", hit[1])) or ()), kf, (), (), ()
        else:
            return env
        if occ is not None:
            for name, targ in zip(names, occ.get("targs") or ()):
                env[name] = self.inst(targ, {}, kf, occ["s"])
            if not occ["named"] and ptexprs:
                for i, desc in enumerate(occ["args"]):
                    if desc is not None and desc[0] == "lambda":
                        continue
                    pe = ptexprs[i] if i < len(ptexprs) else (ptexprs[-1] if params and params[-1][1] else None)
                    if pe is not None:
                        at = self.type_of(desc, kf, occ["s"], occ["o"]) if desc is not None else None
                        if at is not None and at[0] not in ("class", "lib", "java"):
                            at = None
                        self.unify(pe, at, env, kf2, scope2, free)
            self._expected(kind, hit, occ, env, kf, kf2, scope2, names)
            for i, desc in enumerate(occ["args"]):          # stage two: what the lambdas evaluate to
                if desc is None or desc[0] != "lambda" or not ptexprs:
                    continue
                pe = ptexprs[i] if i < len(ptexprs) and isinstance(ptexprs[i], tuple) and ptexprs[i][0] == "fn" \
                    else ptexprs[-1]
                if not isinstance(pe, tuple) or pe[0] != "fn" or not (_pnames(pe[3]) - set(env)):
                    continue
                value = self.type_of(desc[1], kf, occ["s"], occ["o"]) if len(desc) > 1 and desc[1] else None
                if value is not None and value[0] not in ("class", "lib", "java"):
                    value = None
                self.unify(pe[3], value, env, kf2, scope2, free)
        if key is not None and key in self._tainted:        # computed without its enclosing call's answer
            self._tainted.discard(key)
            self._infer.pop(key, None)
        return env

    def _argument_expectation(self, occ, kf):
        """The type the enclosing call's parameter wants of this call, `f(emptyList())`: its declared type
        under what that call has bound so far. ``None`` when the enclosing call is unknown or still being
        resolved (then this result must not be remembered, it will be asked again)."""
        link = occ.get("arg_of")
        if link is None:
            return None
        parent_key = (kf.path, link[0])
        target = self.call_target(link[0], kf) if parent_key not in self._callee else self._callee[parent_key]
        if target is None or target[0] != "fun":
            if parent_key in self._callee and self._callee[parent_key] is None:
                self._tainted.add((kf.path, occ["id"]))
            return None
        kf2, rec = target[1]
        ptexprs = rec.get("ptexprs") or ()
        if link[1] >= len(ptexprs) and not (rec["params"] and rec["params"][-1][1]):
            return None
        pe = ptexprs[link[1]] if link[1] < len(ptexprs) else ptexprs[-1]
        env = self.infer(target, kf, kf.occurrences[link[0]])
        wanted = self.inst(pe, env, kf2, rec["scope"])
        return wanted if wanted is not None and wanted[0] in ("class", "lib", "java") else None

    def _expected(self, kind, hit, occ, env, kf, kf2, scope2, names):
        """Bind what the arguments left unbound from the type the call's value is stored in.

        ``val xs: List<Point> = emptyList()`` binds ``T`` by matching the declared result
        ``List<T>`` against ``List<Point>``. Weaker than an argument, so it only fills gaps, and
        only when the declared type is a supertype-shaped match (anything else binds nothing).
        """
        expected = occ.get("exp")
        missing = [n for n in names if n not in env]
        given = self._argument_expectation(occ, kf) if expected is None and missing else None
        if (expected is None and given is None) or not missing:
            return
        want = self.inst(expected, {}, kf, occ["s"]) if expected is not None else given
        if want is None or want[0] not in ("class", "lib", "java"):
            return
        shape = hit[1][1].get("ret_expr") if kind == "fun" else ("c", hit[1], tuple(("p", n) for n in names))
        trial: dict = {}
        self.unify(shape, want, trial, kf2, scope2, set())
        for n in missing:
            if trial.get(n) is not None:
                env[n] = trial[n]

    def lambda_param_ty(self, desc, kf, scope):
        """The type of lambda parameter ``index``: written, or what the callee's function type says."""
        _, call_id, position, index, declared = desc
        if declared:
            return self.type_name(declared, kf, scope)
        if call_id is None or position == -2:
            return None
        hit = self.call_target(call_id, kf)
        if hit is None or hit[0] != "fun":
            return None
        kf2, rec = hit[1]
        ptexprs = rec.get("ptexprs") or ()
        if not ptexprs:
            return None
        slot = position if 0 <= position < len(ptexprs) else len(ptexprs) - 1
        fn = ptexprs[slot]
        if not isinstance(fn, tuple) or fn[0] != "fn":
            fn = ptexprs[-1]
        if not isinstance(fn, tuple) or fn[0] != "fn" or index >= len(fn[2]):
            return None
        return self.inst(fn[2][index], self.infer(hit, kf, kf.occurrences[call_id]), kf2, rec["scope"])

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
            out.extend(self.expand(s) or ("lib", s) for s in jdk_index.supertypes(ln))   # a Kotlin library type is a class
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

    # -- which candidates the arguments allow ----------------------------------
    def _arg_types(self):
        """The types of the call's arguments: a type, ``"lambda"`` or ``None`` (unknown)."""
        ctx = self._ctx
        if ctx is None:
            return []
        if ctx["types"] is None:
            ctx["types"] = []          # guards against re-entry while the types are worked out
            occ, kf = ctx["occ"], ctx["kf"]
            out = []
            for desc in occ["args"]:
                if desc is not None and desc[0] == "lambda":
                    out.append("lambda")
                    continue
                t = self.type_of(desc, kf, occ["s"], occ["o"]) if desc is not None else None
                if t is not None and t[0] == "static" and (self.ix.classes.get(t[1]) or (None, {}))[1].get("object"):
                    t = ("class", t[1])                # an `object` passed as a value is an instance of itself
                out.append(t if t is not None and t[0] in ("class", "java", "lib") else None)
            ctx["types"] = out
        return ctx["types"]

    def _param_accepts(self, kf2, rec, index, argument) -> bool:
        ptypes = rec.get("ptypes") or ()
        params = rec["params"]
        if index < len(ptypes):
            pt = ptypes[index]
        elif params and params[-1][1] and ptypes:
            pt = ptypes[-1]
        else:
            return True
        if argument is None or argument == "lambda" or pt is None or pt == "*" or pt in rec.get("tparams", ()):
            return True
        if pt.startswith("<fn>"):
            return False               # a value of a known class where a function is wanted
        key = (rec["key"], index)
        if key not in self._ptypes:
            self._ptypes[key] = self.type_name(pt, kf2, rec["scope"])
        target = self._ptypes[key]
        if target is None:
            return True
        if target in self.hierarchy(argument):
            return True
        # an integer literal adapts to Long, Short and Byte; a lenient reading keeps Int too
        return argument == ("class", "kotlin.Int") and target[1] in ("kotlin.Long", "kotlin.Short", "kotlin.Byte")

    def _reference_arity(self, occ, kf):
        """The function type a callable reference is passed as, as ``(arity, parameter types)`` with ``None``
        for a type not known, or ``None`` when the reference is not an argument of a known function."""
        link = occ.get("arg_of")
        if link is None:
            return None
        parent_key = (kf.path, link[0])
        target = self.call_target(link[0], kf) if parent_key not in self._callee else self._callee[parent_key]
        if target is None or target[0] != "fun":
            return None
        kf2, rec = target[1]
        ptexprs = rec.get("ptexprs") or ()
        if link[1] >= len(ptexprs):
            return None
        fn = ptexprs[link[1]]
        if not isinstance(fn, tuple) or fn[0] != "fn":
            return None
        env = self.infer(target, kf, kf.occurrences[link[0]])
        given = ([fn[1]] if fn[1] is not None else []) + list(fn[2])
        types = []
        for expr in given:
            t = self.inst(expr, env, kf2, rec["scope"])
            types.append(t if t is not None and t[0] in ("class", "lib", "java") else None)
        return len(given), types

    def _fits(self, candidate, nargs) -> bool:
        """Arity, and the arguments' types where both sides are known."""
        kf2, rec = candidate
        ctx = self._ctx
        if ctx is not None and ctx["occ"]["named"] and getattr(kf2, "library", False) and not rec.get("pnames") \
                and rec["name"] in _BLOCK_FUNCTIONS and any(
                    n not in (None, "*", "block") for n in ctx["occ"].get("argnames") or ()):
            return False
        if nargs is None and self._ref_arity is not None:
            (wanted, given), unbound, typed = self._ref_arity  # `Type::member` takes its receiver as the first argument
            skip = 1 if unbound and (rec["owner"] is not None or rec.get("receiver")) else 0
            if wanted - skip < 0 or not _arity_ok(rec, wanted - skip):
                return False
            return not typed or all(self._param_accepts(kf2, rec, i - skip, t)
                                    for i, t in enumerate(given) if i >= skip and t is not None)
        if not _arity_ok(rec, nargs):
            return False
        ctx = self._ctx
        if ctx is not None and ctx["occ"]["named"] and rec.get("pnames"):
            return self._named_fits(kf2, rec, ctx["occ"])
        if ctx is None or ctx["occ"]["named"] or not rec.get("ptypes"):
            return True
        vararg = next((j for j, p in enumerate(rec["params"]) if p[1]), None)
        # every positional argument from a vararg on is one of its elements, even when parameters follow it
        return all(self._param_accepts(kf2, rec, i if vararg is None or i < vararg else vararg, a)
                   for i, a in enumerate(self._arg_types()))

    def _named_fits(self, kf2, rec, occ) -> bool:
        """Whether the arguments, some written ``name = value``, can bind this declaration's parameters.

        A positional argument takes the next parameter, a named one its parameter by name, a trailing
        lambda the last; every parameter without a default must be bound, and a bound parameter's
        type must accept its argument where both are known. A spread argument (``*xs``) or arguments
        not aligned with their names say nothing here.
        """
        names, args = occ.get("argnames") or [], occ["args"]
        pnames, params = rec["pnames"], rec["params"]
        if len(names) != len(args) or len(pnames) != len(params):
            return True
        types = self._arg_types()
        named = {pnames.index(n) for n in names if n not in (None, "*") and n in pnames}
        if any(n not in (None, "*") and n not in pnames for n in names):
            return False
        bound, position, checks = {}, 0, []
        vararg = next((j for j, p in enumerate(params) if p[1]), None)
        spread = {i for i, n in enumerate(names) if n == "*"}       # `*xs`: an array standing for the elements
        for i, name in enumerate(names):
            if name not in (None, "*"):
                j = pnames.index(name)
            else:
                if args[i] is not None and args[i][0] == "lambda" and i == len(args) - 1 \
                        and len(params) - 1 not in named and len(params) - 1 not in bound:
                    j = len(params) - 1                     # a trailing lambda takes the last parameter
                else:
                    while position in named or position in bound:
                        position += 1                       # a positional argument takes the next free one
                    j = position
                    if j != vararg:
                        position += 1                       # the elements of a vararg all take it
                if j >= len(params):
                    if not (params and params[-1][1]):
                        return False
                    j = len(params) - 1
            if j in bound and not params[j][1]:
                return False
            bound[j] = i
            checks.append((j, i))
        if any(not default and not vararg and j not in bound for j, (default, vararg, _) in enumerate(params)):
            return False
        # a value typed `Any` may have been smart-cast to what the parameter wants: it excludes nothing
        return all(self._param_accepts(kf2, rec, j, types[i]) for j, i in checks
                   if i < len(types) and types[i] != ("class", "kotlin.Any") and i not in spread)

    def _unknown_arguments(self) -> bool:
        return self._ctx is not None and any(a is None for a in self._arg_types())

    # -- one hierarchy level -------------------------------------------------
    def _fun_level(self, t, name, nargs):
        kind, ln = t
        if kind == "class":
            recs = self.ix.members_funs.get(ln, {}).get(name, [])
            fits = [("fun", r) for r in recs if self._fits(r, nargs)]
            if not recs and nargs == 0 and name.startswith("component") and name[9:].isdigit():
                return self._data_component(ln, int(name[9:]))
            return fits
        if kind == "java":
            return self._java_funs(ln, name, nargs)
        if kind == "lib" and jdk_index.known(ln):
            declaring = jdk_index.declaring_type(ln, name, arity=nargs)
            return [("jdkfun", declaring, name)] if declaring else []
        return []

    def overridden(self, rec, variable=False):
        """The outcome naming the member a declaration marked ``override`` overrides, or ``None``.

        The supertypes are searched nearest first, as a call is; the first level declaring the
        name with the same number of parameters (and, among several, the same parameter types)
        is the one. Two candidates that cannot be told apart are refused, as a call refuses.
        """
        owner = rec.get("owner")
        if not owner or owner not in self.ix.classes or rec.get("receiver") is not None:
            return None
        for ty in self.hierarchy(("class", owner))[1:]:
            if ty == OPAQUE or ty[0] not in ("class", "java", "lib"):
                continue
            if variable:
                hits = self._var_level(ty[:2], rec["name"])
            else:
                nargs = len(rec["params"])
                hits = self._fun_level(ty[:2], rec["name"], nargs)
                hits = [h for h in hits if h[0] != "fun" or len(h[1][1]["params"]) == nargs]
                if len(hits) > 1:
                    mine = tuple(rec.get("ptypes") or ())
                    same = [h for h in hits if h[0] == "fun" and tuple(h[1][1].get("ptypes") or ()) == mine]
                    hits = same if same else hits
            hits = [h for h in hits if h[0] != "dataprop"]
            if len(hits) != 1:
                if hits:
                    return None
                continue
            hit = hits[0]
            if hit[0] == "fun":
                return ("call", hit[1])
            if hit[0] == "var":
                return ("var", hit[1])
            if hit[0] == "jdkfun":
                return ("jdkcall", hit[1], hit[2])
            if hit[0] == "jdkvar":
                return ("jdkvar", hit[1], hit[2])
            if hit[0] == "jfun":
                return ("jcall", hit[1], hit[2], hit[3], hit[4])
            if hit[0] == "jvar":
                return ("jvar", hit[1], hit[2])
            return None
        return None

    def is_interface_type(self, fq):
        """Whether the type named ``fq`` is an interface: a project class, a Kotlin library type or a JDK one."""
        entry = self.ix.classes.get(fq)
        if entry is not None:
            return entry[1].get("decl") == "interface"
        return kotlin_index.is_interface(fq) or jdk_index.is_interface(fq) or symbol_table.is_interface(fq)

    def _data_component(self, ln, position):
        """A data class's synthesised ``componentN``: it returns its Nth primary-constructor property."""
        data = self.ix.classes[ln][1].get("data") or []
        if not 1 <= position <= len(data):
            return []
        props = self.ix.members_vars.get(ln, {}).get(data[position - 1], [])
        return [("dataprop", props[0])] if len(props) == 1 else []

    def _java_funs(self, ln, name, nargs):
        entries = symbol_table.INDEX.methods.get(f"{ln}.{name}") or []
        fits = [e for e in entries if _java_arity_ok(e[0], nargs)]
        if nargs is None:              # a reference names the method, not a call: only an unoverloaded one
            return [("jfun", ln, name, len(fits[0][0]), 0)] if len(fits) == 1 else []
        if len(fits) <= 1:
            return [("jfun", ln, name, nargs, 0)] if fits else []
        site = symbol_table.overload_site(f"{ln}.{name}", self._java_argument_types(nargs))
        if site is not None:
            return [("jfun", ln, name, nargs, site)]
        return [("jfun", ln, name, nargs, i) for i in range(len(fits))]

    #: Kotlin's primitives as the Java overload resolution names them.
    _JAVA_PRIMITIVE = {
        "kotlin.Int": "int", "kotlin.Long": "long", "kotlin.Short": "short", "kotlin.Byte": "byte",
        "kotlin.Double": "double", "kotlin.Float": "float", "kotlin.Boolean": "boolean", "kotlin.Char": "char",
        "kotlin.String": "java.lang.String", "kotlin.Any": "java.lang.Object", "kotlin.CharSequence": "java.lang.CharSequence",
    }

    def _java_argument_types(self, nargs):
        """The call's argument types as Java names (``None`` where unknown), for choosing a Java overload."""
        types = self._arg_types() if self._ctx is not None and len(self._ctx["occ"]["args"]) == nargs else []
        out = []
        for i in range(nargs):
            t = types[i] if i < len(types) else None
            if t is None or t == "lambda":
                out.append(None)
            elif t[1] in self._JAVA_PRIMITIVE:
                out.append(self._JAVA_PRIMITIVE[t[1]])
            elif t[0] in ("java", "lib") or (t[0] == "class" and t[1] in self.ix.classes and
                                              not t[1].startswith("kotlin.")):
                out.append(t[1])
            else:
                out.append(None)
        return out

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
        if hit[0] == "var" and hit[1][1].get("owner"):
            # one property however many platforms declare it (`expect val Default` and each `actual`)
            return ("property", hit[1][1]["owner"], hit[1][1]["name"])
        if hit[0] in ("fun", "var"):
            return _ckey(hit[1])
        if hit[0] == "dataprop":
            return ("dataprop", hit[1][1]["key"])
        return hit

    def find(self, t, level):
        """The single declaration at the nearest hierarchy level that has one.

        ``AMBIGUOUS`` when that level has several, ``OPAQUE`` when nothing was found but
        a supertype could not be seen into, ``None`` when nothing declares it. A hit
        behind an unseen supertype is ambiguous: the unseen type might declare it too.
        """
        unseen = False
        levels = self.hierarchy(t)
        for position, ty in enumerate(levels):
            if ty == OPAQUE:
                unseen = True
                continue
            hits = level(ty)
            if hits:
                if len({self.hit_key(h) for h in hits}) != 1:
                    return AMBIGUOUS
                if unseen and position > 0:
                    return AMBIGUOUS
                if self._unknown_arguments() and hits[0][0] == "fun" and self._shadowed_differently(
                    hits[0], levels[position + 1:], level
                ):
                    return AMBIGUOUS
                if len(hits) > 1 and all(h[0] == "fun" for h in hits):      # one library entity, many overloads
                    exact = self._exact_overloads(hits)
                    return ("fun", self._merged([h[1] for h in (exact or hits)]))
                return hits[0]
        return OPAQUE if unseen else None

    def _exact_overloads(self, hits):
        """The overloads whose every parameter type is exactly the (known) argument's: Kotlin prefers them
        (`1..2` is `rangeTo(Int)`, though an `Int` literal also fits `rangeTo(Long)`)."""
        if self._ctx is None or self._ctx["occ"]["named"]:
            return []
        types = self._arg_types()
        if not types or any(t is None for t in types):
            return []
        return [h for h in hits if len(h[1][1]["params"]) == len(types)
                and all(self._param_ty(h[1][0], h[1][1], i) == t for i, t in enumerate(types))]

    def _shadowed_differently(self, hit, later_levels, level) -> bool:
        """Whether a farther level declares a *different* overload the arguments might select.

        An override repeats its parameter types; a different signature further up is a
        distinct overload, and with an argument whose type is unknown the nearer one may
        be the wrong pick (``Job.plus(Job)`` against ``CoroutineContext.plus(CoroutineContext)``).
        """
        mine = hit[1][1].get("ptypes")
        for ty in later_levels:
            if ty == OPAQUE:
                continue
            for other in level(ty):
                if other[0] == "fun" and other[1][1].get("ptypes") != mine:
                    return True
        return False

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
    def var_type(self, kf, rec, recv=None):
        key = rec["key"]
        if key in self._busy:
            return None
        expr = rec.get("declared_expr")
        if expr is not None:
            return self.inst(expr, self.member_env(rec["owner"], recv), kf, rec["scope"])
        if rec["declared"]:
            return self.type_name(rec["declared"], kf, rec["scope"])
        if rec["init"] is None:
            return None
        self._busy.add(key)
        try:
            return self.type_of(rec["init"], kf, rec["scope"], owner=key)
        finally:
            self._busy.discard(key)

    def return_type(self, kf, rec, env=None):
        if rec["ctor"]:
            return ("class", rec["owner"])
        expr = rec.get("ret_expr")
        if expr is not None:
            return self.inst(expr, env or {}, kf, rec["scope"])
        if rec["ret"]:
            return self.type_name(rec["ret"], kf, rec["scope"])
        if rec["ret_init"] is None or rec["key"] in self._busy:
            return None
        self._busy.add(rec["key"])
        try:
            return self.type_of(rec["ret_init"], kf, rec["scope"], owner=rec["key"])
        finally:
            self._busy.discard(rec["key"])

    def _generic_env(self, hit, kf, occ):
        """For a library method with type parameters of its own: (return text, environment), else ``None``.

        The receiver binds the declaring type's parameters, an explicit ``<T>`` and the arguments' types
        bind the method's (``Class<S>`` against ``Detekt::class.java``).
        """
        if occ is None or kf is None or len(hit) < 3:
            return None
        found = jdk_index.generic_method(hit[1], hit[2], occ["a"])
        if found is None:
            return None
        tparams, ret, params = found
        env: dict = {}
        recv = hit[3] if len(hit) > 3 else None
        declared, _ = jdk_index.generic_supertypes(hit[1])
        seen = self.as_super(recv, ("lib", hit[1])) if recv is not None and declared else None
        if seen is not None:
            env.update(zip(declared, _a(seen)))
        for name, targ in zip(tparams, occ.get("targs") or ()):
            env[name] = self.inst(targ, {}, kf, occ["s"])
        if not occ["named"]:
            free: set = set()
            for i, desc in enumerate(occ["args"]):
                if desc is None or desc[0] == "lambda" or i >= len(params):
                    continue
                at = self.type_of(desc, kf, occ["s"], occ["o"])
                if at is not None and at[0] in ("class", "lib", "java"):
                    self._unify_text(params[i], at, env, set(tparams), free)
        return ret, {k: v for k, v in env.items() if v is not None}

    def _unify_text(self, text, t, env, mtps, free):
        """Bind the method type parameters ``text`` (a javap type) mentions by matching it against ``t``."""
        text = text.strip().replace("? super ", "").replace("? extends ", "").rstrip(".")
        head, _, tail = text.partition("<")
        if head in mtps:
            if head not in env:
                env[head] = t
                free.add(head)
            return
        if not tail:
            return
        args, depth, current = [], 0, ""
        for ch in tail[:-1]:
            depth += (ch == "<") - (ch == ">")
            if ch == "," and depth == 0:
                args.append(current)
                current = ""
            else:
                current += ch
        args.append(current)
        base = self.expand(head)
        seen = self.as_super(t, tuple(base[:2])) if base is not None else None
        if seen is not None and len(_a(seen)) == len(args):
            for sub_text, sub_t in zip(args, _a(seen)):
                if sub_t is not None:
                    self._unify_text(sub_text, sub_t, env, mtps, free)

    def hit_type(self, hit, kf=None, occ=None):
        """The type a resolved call or name evaluates to (``occ``: the call, for its type arguments)."""
        kind = hit[0]
        if kind == "fun":
            env = self.infer(hit, kf, occ) if occ is not None and kf is not None \
                else self.member_env(hit[1][1]["owner"], hit[2] if len(hit) > 2 else None)
            return self.return_type(*hit[1], env)
        if kind in ("ctor", "ctor_call"):
            cls = ("class", hit[1])
            tps = self.tparams_of(cls)
            if tps and occ is not None and kf is not None:
                env = self.infer(hit, kf, occ)
                return with_args(cls, [env.get(tp) for tp in tps])
            return cls
        if kind in ("jctor", "libctor"):
            t = ("java" if kind == "jctor" else "lib", hit[1])
            if occ is not None and kf is not None and occ.get("targs"):
                return with_args(t, [self.inst(a, {}, kf, occ["s"]) for a in occ["targs"]])
            return t
        if kind == "jfun":
            return self.expand(symbol_table.return_type(hit[1], hit[2]))
        if kind == "jdkfun":
            recv = hit[3] if len(hit) > 3 else None
            generic = self._generic_env(hit, kf, occ)
            if generic is not None:
                typed = self._library_type(generic[0], generic[1])
                if typed is not None:
                    return typed
            index = jdk_index.returned_type_parameter(hit[1], hit[2]) if recv is not None and _a(recv) else None
            if index is not None:                       # `ArrayList<Point>.get(0)` returns the receiver's E
                seen = self.as_super(recv, ("lib", hit[1]))
                if seen is not None and index < len(_a(seen)) and _a(seen)[index] is not None:
                    return _a(seen)[index]
            composite = jdk_index.composite_return(hit[1], hit[2]) if recv is not None and _a(recv) else None
            if composite is not None:                   # `Map<K, V>.entrySet()` is `Set<Map.Entry<K, V>>`
                built = self._composite_type(composite, recv)
                if built is not None:
                    return built
            return self.expand(jdk_index.return_type(hit[1], hit[2]))
        if kind in ("var", "dataprop"):
            return self.var_type(*hit[1], hit[2] if len(hit) > 2 else None)
        if kind == "jvar":
            return self.expand(symbol_table.member_type(hit[1], hit[2]))
        if kind == "jdkvar":
            return self.expand(jdk_index.field_type(hit[1], hit[2]))
        return None

    def _composite_type(self, composite, recv):
        """A JDK method's return type written with its type's own parameters, under the receiver's arguments."""
        declaring, params, text = composite
        seen = self.as_super(recv, ("lib", declaring))
        if seen is None or not _a(seen):
            return None
        env = dict(zip(params, _a(seen)))
        parsed, rest = _parse_generic(text)
        if rest:
            return None
        return self._build_generic(parsed, env)

    def _build_generic(self, node, env):
        name, args = node
        if name in env:
            return env[name] if not args else None
        if name == "?":
            return None
        base = self.expand(name.replace("$", "."))
        if base is None:
            return None
        return with_args(base, [self._build_generic(a, env) for a in args])

    @staticmethod
    def tag(hit, recv):
        """``hit`` remembering the receiver type it was found on, so its type arguments can be read."""
        if isinstance(hit, tuple) and hit[0] in ("fun", "var", "dataprop", "jdkfun") and len(hit) in (2, 3) \
                and (len(hit) == 2 or hit[0] == "jdkfun") \
                and recv is not None and recv[0] in ("class", "lib", "java"):
            return (*hit, recv)
        return hit

    # -- the type of an expression -------------------------------------------
    def type_of(self, desc, kf, scope, owner=None):
        if desc is None:
            return None
        kind = desc[0]
        if kind == "lit":
            return self.expand(desc[1])
        if kind == "cast":
            return self.type_name(desc[1], kf, scope)
        if kind == "narrow":                    # a smart cast of a member path: `if (a.b is Foo)`
            cast = self.inst(desc[2], {}, kf, scope)
            if cast is not None and cast[0] in ("class", "lib", "java"):
                return cast
            return self.type_of(desc[1], kf, scope, owner)
        if kind == "classlit":                  # `X::class` is a KClass<X>, `X::class.java` a Class<X>
            target = self.type_of(desc[1], kf, scope, owner)
            if target is not None and target[0] == "static":
                target = ("class", target[1])
            if target is None or target[0] not in ("class", "lib", "java"):
                return None
            holder = self.expand("java.lang.Class" if desc[2] else "kotlin.reflect.KClass")
            return with_args(holder, [target]) if holder is not None else None
        if kind == "lparam":
            return self.lambda_parameter_type(desc, kf, scope)
        if kind == "delegate":
            _, value, provided = desc
            call = self.call_target(provided[4], kf)
            if isinstance(call, tuple):
                return self.hit_type(call)         # provideDelegate answers: that is the delegate
            return self.type_of(value, kf, scope, owner)
        if kind == "element":
            _, iterable, following = desc
            return self.element_type(iterable, kf, scope, owner) or self.type_of(following, kf, scope, owner)
        if kind == "this":
            return self.this_type(kf, scope, owner)
        if kind == "super":
            chain = self.class_chain(scope)
            return ("super", chain[0]) if chain else None
        if kind == "name":
            name, binding = desc[1], desc[2]
            narrowed = desc[3] if len(desc) > 3 else None
            if narrowed is not None:                  # a smart cast: `if (x is Foo)` makes `x` a Foo here
                cast = self.inst(narrowed, {}, kf, scope)
                if cast is not None and cast[0] in ("class", "lib", "java"):
                    return cast
            if binding is not None:
                if binding[0] == "local":
                    entry = self.ix.variables.get(binding[1])
                    return self.var_type(*entry) if entry else None
                if binding[0] == "lparam":
                    return self.lambda_parameter_type(binding, kf, scope)
                return None
            hit = self.free_var(name, kf, scope, owner)
            if isinstance(hit, tuple):
                return self.hit_type(hit)
            if hit is not None:
                return None                # ambiguous or unseen: a name, but not a known one
            cls = self.type_name(name, kf, scope)
            if cls and cls[0] == "class":
                return ("static", cls[1])
            if cls is None and name in self.ix.packages:
                return ("package", name)    # `a` in `a.b.C.f()`
            return cls                      # a Java or library class used as a receiver
        if kind == "member":
            _, recv, name = desc
            rt = self.type_of(recv, kf, scope, owner)
            if rt is not None and rt[0] == "package":
                fq = f"{rt[1]}.{name}"
                if fq in self.ix.classes:
                    return ("static", fq)
                if fq in self.ix.packages:
                    return ("package", fq)
                tops = [c for c in self.ix.top_vars.get((rt[1], name), []) if c[1]["receiver"] is None]
                return self.var_type(*tops[0]) if len(tops) == 1 else None
            hit = self.find_member(rt, lambda t, n=name: self._var_level(t, n))
            if isinstance(hit, tuple):
                return self.hit_type(self.tag(hit, rt))
            if hit is None and rt is not None and rt[0] in ("java", "lib"):
                accessor = self.synthetic_property(rt, name, "use")
                if accessor is not None:
                    return self.hit_type(accessor)
            if rt is not None and rt[0] == "static":
                nested = self.ix.nested.get(rt[1], {}).get(name)
                if nested:
                    return ("static", nested)
            return None
        if kind == "call":
            call = self.call_target(desc[4], kf)
            return self.hit_type(call, kf, kf.occurrences[desc[4]]) if isinstance(call, tuple) else None
        return None

    def lambda_parameter_type(self, desc, kf, scope):
        """The type of a lambda's destructured parameter: written, or the callee's lambda parameter type.

        ``{ (k, v): Pair<A, B> -> }`` says it. Otherwise the lambda is an argument of a call, and
        that call's parameter, a function type ``(Map.Entry<K, V>) -> R``, names the type of the
        lambda's first parameter -- recorded only when it is a class.
        """
        _, call_id, position, index, declared = desc
        if declared:
            return self.type_name(declared, kf, scope)
        found = self.lambda_param_ty(desc, kf, scope)
        if found is not None:
            return found
        if call_id is None or index != 0 or position == -2:
            return None
        hit = self.call_target(call_id, kf)
        if hit is None or hit[0] != "fun":
            return None
        kf2, rec = hit[1]
        ptypes = rec.get("ptypes") or ()
        if not ptypes:
            return None
        slot = position if 0 <= position < len(ptypes) else len(ptypes) - 1
        text = ptypes[slot]
        if not text or not text.startswith("<fn>:"):
            return None
        return self.type_name(text[5:], kf2, rec["scope"])

    def element_type(self, desc, kf, scope, owner):
        """What a loop over ``desc`` yields: its ``Iterable``'s element, or a map's entry.

        The type arguments say it when the iterable's are known. Where they are not, a map
        still yields its entries, ``withIndex()`` an ``IndexedValue`` and ``zip`` a ``Pair``,
        and anything else is left to ``next()``'s declared type.
        """
        rt = self.type_of(desc, kf, scope, owner)
        if rt is not None and rt[0] in ("class", "lib", "java"):
            iterable = self.as_super(rt, ("class", "kotlin.collections.Iterable"))
            if iterable is not None and _a(iterable) and _a(iterable)[0] is not None:
                return _a(iterable)[0]
        if desc[0] == "call" and desc[2] in ("withIndex", "zip"):
            hit = self.call_target(desc[4], kf)
            if hit is not None and hit[0] == "fun" and getattr(hit[1][0], "library", False):
                return ("class", "kotlin.collections.IndexedValue" if desc[2] == "withIndex" else "kotlin.Pair")
        if rt is not None and rt[0] in ("class", "lib", "java"):
            for source, entry in (("MutableMap", "MutableMap.MutableEntry"), ("Map", "Map.Entry")):
                mapped = self.as_super(rt, ("class", "kotlin.collections." + source))
                if mapped is not None:
                    return with_args(("class", "kotlin.collections." + entry), _a(mapped))
        return None

    def _extension_receiver(self, owner):
        """The type an extension function or property is declared on, for the code of ``owner``, or ``None``."""
        entry = self.ix.callables.get(owner)
        if entry is not None and entry[1]["receiver"] and not entry[1]["ctor"]:
            return self.type_name(entry[1]["receiver"], entry[0], entry[1]["scope"])
        entry = self.ix.variables.get(owner)           # `val Long.isClosed get() = ...`
        if entry is not None and entry[1].get("receiver"):
            return self.type_name(entry[1]["receiver"], entry[0], entry[1]["scope"])
        return None

    def _has_extension_receiver(self, owner) -> bool:
        entry = self.ix.callables.get(owner)
        if entry is not None and entry[1]["receiver"] and not entry[1]["ctor"]:
            return True
        entry = self.ix.variables.get(owner)
        return entry is not None and bool(entry[1].get("receiver"))

    def this_type(self, kf, scope, owner):
        if self._lam_ctx is not None:
            occ, kf0 = self._lam_ctx
            for call_id, position in reversed(occ["lam"]):
                if call_id is None:
                    return None                       # an anonymous function with a receiver of its own
                target = self.call_target(call_id, kf0)
                if target is not None and target[0] == "fun":
                    if self.receiver_lambda(call_id, position, kf0):
                        return self.lambda_receiver_type(call_id, position, kf0)
                    continue                          # an ordinary Kotlin lambda: `this` is outside it
                if target is not None and target[0] == "jdkfun":
                    if self.receiver_lambda(call_id, position, kf0):
                        return self.lambda_receiver_type(call_id, position, kf0)
                    continue                          # an indexed library method whose parameter is no Action
                return None                           # a Java or unindexed callee: a SAM lambda may take a receiver
        if owner == FILE_OWNER:
            return self.script_receiver(kf)
        if self._has_extension_receiver(owner):
            return self._extension_receiver(owner)
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
        if kf.path.endswith(".gradle.kts"):
            yield [(p, name) for p in GRADLE_SCRIPT_PACKAGES]

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

    def _param_ty(self, kf2, rec, i):
        key = (rec["key"], i)
        if key not in self._ptypes:
            pts = rec.get("ptypes") or ()
            text = pts[i] if i < len(pts) else None
            self._ptypes[key] = self.type_name(text, kf2, rec["scope"]) if text and text != "*" and \
                not text.startswith("<fn>") and text not in rec.get("tparams", ()) else None
        return self._ptypes[key]

    def most_specific(self, candidates):
        """The one overload whose parameter types are all at least as specific as every other's, or ``None``.

        Kotlin picks it when several overloads accept the arguments: ``launch(job)`` with one overload
        taking a ``CoroutineContext`` and another a ``Job`` is the ``Job`` one. A position whose types
        are unknown, or unrelated, makes the comparison undecided.
        """
        def below(c, d):                               # c's parameters are subtypes of d's, somewhere strictly
            strict = False
            for i in range(min(len(c[1]["params"]), len(d[1]["params"]))):
                tc, td = (c[1].get("ptypes") or ()), (d[1].get("ptypes") or ())
                if i < len(tc) and i < len(td) and tc[i] == td[i]:
                    continue                           # written the same: no difference here
                a, b = self._param_ty(c[0], c[1], i), self._param_ty(d[0], d[1], i)
                if a is None or b is None:
                    return False
                if a == b:
                    continue
                if b not in self.hierarchy(a):
                    return False
                strict = True
            return strict

        best = [c for c in candidates if all(c is d or _ckey(c) == _ckey(d) or below(c, d) for d in candidates)]
        return best[0] if len({_ckey(c) for c in best}) == 1 else None

    def _choose(self, candidates):
        """One distinct declaration out of these, ``AMBIGUOUS`` for several, ``None`` for none."""
        distinct = {_ckey(c) for c in candidates}
        if not distinct:
            return None
        if len(distinct) > 1:
            # a fixed-arity overload beats a vararg one taking the same arguments
            fixed = [c for c in candidates if not any(p[1] for p in c[1]["params"])]
            if len({_ckey(c) for c in fixed}) == 1 and len(fixed) < len(candidates):
                return ("fun", self._merged(fixed))
            specific = self.most_specific(candidates)
            if specific is not None:
                return ("fun", self._merged([specific, *(c for c in candidates if c is not specific and _ckey(c) == _ckey(specific))]))
            return AMBIGUOUS
        return ("fun", self._merged(candidates))

    def _merged(self, candidates):
        """One declaration standing for same-named overloads; its type is unknown if they disagree.

        Overloads of an extension that differ only in the receiver they extend (`DomainObjectCollection`,
        `NamedDomainObjectCollection`, `TaskCollection`: `withType`) agree on a call to the narrowest one:
        the receiver that is a subtype of all the others' decides, as Kotlin's most specific choice does."""
        first = candidates[0]
        if len(candidates) > 1 and getattr(first[0], "library", False) and \
                len({(c[1]["ret"], c[1]["ret_init"], c[1].get("ret_expr")) for c in candidates}) > 1:
            narrowest = self._narrowest_receiver(candidates)
            if narrowest is not None:
                return narrowest
            return (first[0], {**first[1], "ret": None, "ret_init": None, "ret_expr": None})
        return first

    def _narrowest_receiver(self, candidates):
        tys = []
        for c in candidates:
            text = c[1].get("receiver")
            ty = self.type_name(text, c[0], c[1]["scope"]) if text and text != "*" else None
            if ty is None:
                return None
            tys.append(ty)
        if len({_deep(t) for t in tys}) == 1 or len(set(tys)) == 1:
            return None          # same receiver, different results (`sumOf` by what the lambda returns): undecided
        for c, ty in zip(candidates, tys):
            if all(other == ty or other in self.hierarchy(ty) for other in tys):
                return c
        return None

    def top_level_hit(self, name, nargs, kf):
        for tier in self.tiers(name, kf):
            found = [c for pkg, orig in tier for c in self._top_funs_at(pkg, orig)
                     if c[1]["receiver"] is None and self._fits(c, nargs)]
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
                    if rec["receiver"] is None or not self._fits((kf2, rec), nargs):
                        continue
                    if self._extension_applies(kf2, rec, applies):
                        found.append((kf2, rec))
            hit = self._choose(self._most_specific_receivers(found))
            if hit is not None:
                return hit
        return None

    def _most_specific_receivers(self, found):
        """Of several applicable extensions, the ones whose receiver no other's receiver is a subtype of:
        ``KtClass.isAbstract()`` beats ``KtModifierListOwner.isAbstract()`` when both are imported."""
        if len(found) < 2:
            return found
        receivers = [self.type_name(rec["receiver"], kf2, rec["scope"]) for kf2, rec in found]
        if any(r is None for r in receivers):
            return found
        kept = [c for c, r in zip(found, receivers)
                if not any(o != r and self.is_subtype(o, r) for o in receivers)]
        return kept or found

    def synthetic_property(self, rt, name, mode):
        """A Java getter read as a Kotlin property: ``file.name`` calls ``getName()`` (``isX`` for a
        boolean), ``file.name = v`` calls ``setName(v)``. A field or Kotlin member of that name wins
        before this is asked; Kotlin's own types (``kotlin.*``) have real properties and are skipped."""
        if rt[0] == "lib" and (rt[1].startswith("kotlin.") or rt[1] in KOTLIN_FOR):
            return None
        cap = name[:1].upper() + name[1:]
        if mode == "set":
            names, nargs = (f"set{cap}",), 1
        elif mode == "use":
            names, nargs = (f"get{cap}", f"is{cap}"), 0
        else:
            return None
        found = []
        for accessor in names:
            hit = self.find_member(rt, lambda t, n=accessor: self._fun_level(t, n, nargs))
            if isinstance(hit, tuple) and hit[0] in ("jfun", "jdkfun"):
                found.append(hit)
        if not found and mode == "set":
            # Gradle's lazy properties have no setter: `name = "x"` assigns through `getName()`'s Property<T>
            hit = self.find_member(rt, lambda t, n=f"get{cap}": self._fun_level(t, n, 0))
            if isinstance(hit, tuple) and hit[0] == "jdkfun" and \
                    (jdk_index.return_type(hit[1], hit[2]) or "").rsplit(".", 1)[-1].endswith("Property"):
                found.append(hit)
        return found[0] if len(found) == 1 else None

    def extension_var_hit(self, rt, name, kf):
        """The extension property named ``name`` that applies to a receiver of type ``rt``."""
        if rt is None or rt[0] not in ("class", "java", "lib"):
            return None
        applies = set(self.hierarchy(rt))
        for tier in self.tiers(name, kf):
            found = [c for pkg, orig in tier for c in self.ix.top_vars.get((pkg, orig), [])
                     if c[1]["receiver"] is not None and self._extension_applies(c[0], c[1], applies)]
            distinct = {_ckey(c) for c in found}
            if len(distinct) == 1:
                return ("var", found[0], rt)
            if distinct:
                return AMBIGUOUS
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
            if key in self._pending:
                self._cycle.add(key)           # asked while still being resolved: an answer built on this is provisional
            return self._callee[key]
        self._callee[key] = None   # a call whose receiver depends on itself
        self._pending.add(key)
        outer, self._cycle = self._cycle, set()
        try:
            result = self._resolve_call(kf.occurrences[occurrence_id], kf)
        finally:
            self._pending.discard(key)
            asked = self._cycle - {key}
            self._cycle = outer | asked
        result = result if isinstance(result, tuple) else None
        if asked:
            # it leaned on a call that was still being resolved (`flowOf(it)` needs `it`, which needs the
            # enclosing call's lambda result, which is this call): do not remember an answer given without it
            del self._callee[key]
        else:
            self._callee[key] = result
        return result

    def _resolve_call(self, occ, kf):
        saved, self._ctx = self._ctx, {"occ": occ, "kf": kf, "types": None}
        saved_receivers, saved_ctx = self._lambda_recv, self._lam_ctx
        self._lam_ctx = (occ, kf)
        if occ["r"] is None and occ["b"] is None:
            # a call is resolved against the receivers of the lambdas around *it*, whoever asks first
            around = self.lambda_receivers(occ, kf)
            self._lambda_recv = around if around is not None else []
        try:
            if occ.get("init"):
                return self._resolve_init(occ, kf)
            result = self._resolve_named(occ, kf, occ["n"])
            if not isinstance(result, tuple) and occ.get("alt"):
                result = self._resolve_named(occ, kf, occ["alt"])     # `+=`: plusAssign, else plus
            if not isinstance(result, tuple) and occ["r"] is None and not occ.get("op"):
                result = self._invoke_on_value(occ, kf)               # `f(x)` where f is an object
            return result
        finally:
            self._ctx = saved
            self._lambda_recv = saved_receivers
            self._lam_ctx = saved_ctx

    def _resolve_named(self, occ, kf, name):
        nargs, scope, owner, recv = occ["a"], occ["s"], occ["o"], occ["r"]
        if recv is None:
            binding = occ["b"]
            if binding is not None:
                if binding[0] == "fun":
                    cands = [self.ix.callables[k] for k in binding[1] if k in self.ix.callables]
                    return self._choose([c for c in cands if self._fits(c, nargs)])
                return None
            return self.free_call(name, nargs, kf, scope, owner)
        rt = self.type_of(recv, kf, scope, owner)
        if rt is None:
            return None
        return self.qualified_call(rt, name, nargs, kf)

    def _invoke_on_value(self, occ, kf):
        """``f(x)`` where ``f`` is a variable or property whose type declares ``invoke``."""
        name, nargs = occ["n"], occ["a"]
        binding = occ["b"]
        if binding is not None:
            if binding[0] != "local" or binding[1] not in self.ix.variables:
                return None
            rt = self.var_type(*self.ix.variables[binding[1]])
        else:
            hit = self.free_var(name, kf, occ["s"], occ["o"])
            rt = self.hit_type(hit) if isinstance(hit, tuple) else None
        if rt is None:
            return None
        hit = self.find_member(rt, lambda t: self._fun_level(t, "invoke", nargs))
        return self.tag(hit, rt) if isinstance(hit, tuple) else None

    def constructor(self, t, nargs, exclude=None):
        kind, target = t
        if kind == "java":
            return ("jctor", target, nargs)
        if kind == "lib":
            return ("libctor", target)
        ctors = [c for c in self.ix.ctors.get(target, []) if c[1]["key"] != exclude]
        fits = [c for c in ctors if self._fits(c, nargs)]
        if len({_ckey(c) for c in fits}) == 1:
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

    @staticmethod
    def script_receiver_name(path: str):
        """What ``this`` is in a Gradle Kotlin script: its Settings, Gradle or Project."""
        base = path.rsplit("/", 1)[-1]
        if base == "settings.gradle.kts":
            return "org.gradle.api.initialization.Settings"
        if base == "init.gradle.kts" or base.endswith(".init.gradle.kts"):
            return "org.gradle.api.invocation.Gradle"
        return "org.gradle.api.Project" if base.endswith(".gradle.kts") else None

    def script_receiver(self, kf):
        named = self.script_receiver_name(kf.path)
        return self.expand(named) if named else None

    def implicit_receivers(self, kf, scope, owner):
        """The ``this`` values in scope, innermost first; ``None`` stands for one we cannot type."""
        out = list(self._lambda_recv)         # `T.() -> R` lambdas around the code, innermost first
        if owner == FILE_OWNER and self.script_receiver(kf) is not None:
            out.append(self.script_receiver(kf))      # the top level of a Gradle script
        if self._has_extension_receiver(owner):
            out.append(self._extension_receiver(owner))
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
                return self.tag(hit, rt)
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
        if rt[0] == "package":              # `a.b.foo()` or `a.b.Point(1)`
            fq = f"{rt[1]}.{name}"
            if fq in self.ix.classes:
                return self.constructor(("class", fq), nargs)
            hit = self._choose([c for c in self.ix.top_funs.get((rt[1], name), [])
                                if c[1]["receiver"] is None and self._fits(c, nargs)])
            return hit if hit is not AMBIGUOUS else None
        hit = self.find_member(rt, lambda t: self._fun_level(t, name, nargs))
        if hit is OPAQUE or hit is AMBIGUOUS:
            return None
        if hit is not None:
            if hit[0] in ("jdkfun", "jfun") and self._ctx is not None and self._ctx["occ"].get("targs") \
                    and rt[0] in ("class", "java", "lib"):
                # `tasks.register<Jar>("x")`: a Java member knows no type arguments, so an extension
                # declaring as many type parameters is what the call names
                ext = self.extension_hit(rt, name, nargs, kf)
                if ext is not None and ext is not AMBIGUOUS and \
                        len(ext[1][1].get("tparams", ())) == len(self._ctx["occ"]["targs"]):
                    return self.tag(ext, rt)
            return self.tag(hit, rt)
        if rt[0] == "static":
            nested = self.ix.nested.get(rt[1], {}).get(name)
            if nested:
                return self.constructor(("class", nested), nargs)
            for root in self.static_roots(rt[1]):        # `Type.f()` where f extends Type's companion or object
                hit = self.extension_hit(root, name, nargs, kf)
                if hit is not None and hit is not AMBIGUOUS:
                    return self.tag(hit, root)
            return None
        if rt[0] in ("class", "java", "lib", "super"):
            subject = ("class", rt[1]) if rt[0] == "super" else rt
            hit = self.extension_hit(subject, name, nargs, kf)
            return self.tag(hit, rt if rt[0] != "super" else subject) if hit is not AMBIGUOUS else None
        return None

    # -- bare names ----------------------------------------------------------
    def free_var(self, name, kf, scope, owner, mode="use"):
        """A hit, ``AMBIGUOUS``/``OPAQUE`` when the name exists but cannot be pinned, or ``None``."""
        for rt in self.implicit_receivers(kf, scope, owner):
            if rt is None:
                return OPAQUE
            hit = self.find(rt, lambda t: self._var_level(t, name))
            if hit is not None:
                return hit
            if rt[0] in ("java", "lib"):                   # `rootProject` in an extension on Gradle's Project
                accessor = self.synthetic_property(rt, name, mode if mode == "set" else "use")
                if accessor is not None:
                    return accessor
        for tier in self.tiers(name, kf):
            found = [c for pkg, orig in tier for c in self._top_vars_at(pkg, orig) if c[1]["receiver"] is None]
            distinct = {_ckey(c) for c in found}
            if len(distinct) == 1:
                return ("var", found[0])
            if distinct:
                return AMBIGUOUS
        return None

    # -- the entry point -----------------------------------------------------
    def _named_lambda_param(self, call_id, kf, rec):
        """Index of the parameter a lambda passed by name (``onCompletion = { ... }``) binds to, when the
        call has exactly one such lambda and the callee names its parameters."""
        occ = kf.occurrences[call_id]
        names = occ.get("argnames") or []
        lam = [n for n, a in zip(names, occ["args"]) if n not in (None, "*") and a is not None and a[0] == "lambda"]
        pnames = rec.get("pnames") or ()
        if len(lam) != 1 or lam[0] not in pnames or len(pnames) != len(rec["params"]):
            return None
        return pnames.index(lam[0])

    def _accessor_type(self, call_id, position, kf):
        """The extension a generated Gradle accessor's trailing lambda is the receiver of: ``java { }``."""
        if call_id is None or position != -1 or not kf.path.endswith(".gradle.kts"):
            return None
        occ = kf.occurrences[call_id]
        named = GRADLE_ACCESSORS.get(occ["n"])
        if named is None or occ["r"] is not None or occ["b"] is not None or self.call_target(call_id, kf) is not None:
            return None
        return self.expand(named)

    def receiver_lambda(self, call_id, position, kf) -> bool:
        if call_id is None:
            return True                        # an anonymous function that writes its own receiver
        occ = kf.occurrences[call_id]
        if self._accessor_type(call_id, position, kf) is not None:
            return True
        target = self.call_target(call_id, kf)
        if target is not None and target[0] == "fun":
            params = target[1][1]["params"]
            if not params:
                return False
            if position == -2:                 # a named argument: its parameter, else any of them
                j = self._named_lambda_param(call_id, kf, target[1][1])
                return params[j][2] if j is not None else any(p[2] for p in params)
            return params[position if 0 <= position < len(params) else -1][2]
        if target is not None and target[0] == "jdkfun":
            return self._action_spec(call_id, position, target, kf) is not None    # a Gradle `Action<T>` parameter
        if target is not None:
            return False                       # a Java or constructor callee: no receiver lambdas
        return occ["n"] in RECEIVER_LAMBDAS

    def _action_spec(self, call_id, position, target, kf):
        """The receiver spec of the Gradle ``Action<T>`` parameter this lambda is passed as, or ``None``."""
        if position == -2:
            return None
        nargs = kf.occurrences[call_id]["a"]
        index = nargs - 1 if position == -1 else position
        return jdk_index.action_receiver(target[1], target[2], nargs, index)

    def lambda_receiver_type(self, call_id, position, kf):
        """The type of ``this`` inside a ``T.() -> R`` lambda, from the callee's function type, or ``None``."""
        if call_id is None:
            return None
        accessor = self._accessor_type(call_id, position, kf)
        if accessor is not None:
            return accessor
        target = self.call_target(call_id, kf)
        if target is not None and target[0] == "jdkfun":
            # Kotlin's SAM-with-receiver plugin: a lambda for Gradle's `Action<T>` is `T.() -> Unit`
            spec = self._action_spec(call_id, position, target, kf)
            if spec is None:
                return None
            if spec.startswith("@"):                    # a type parameter of the method, bound by its arguments
                generic = self._generic_env(target, kf, kf.occurrences[call_id])
                t = generic[1].get(spec[1:]) if generic is not None else None
            elif spec.startswith("#"):                  # a type argument of the object the call is made on
                recv = target[3] if len(target) > 3 else None
                seen = self.as_super(recv, ("lib", target[1])) if recv is not None else None
                args = _a(seen) if seen is not None else ()
                t = args[int(spec[1:])] if int(spec[1:]) < len(args) else None
            else:
                t = self.expand(spec)
            return t if t is not None and t[0] in ("class", "lib", "java") else None
        if target is None or target[0] != "fun":
            return None
        kf2, rec = target[1]
        ptexprs = rec.get("ptexprs") or ()
        if not ptexprs:
            return None
        if position == -2:
            position = self._named_lambda_param(call_id, kf, rec)
            if position is None:
                return None
        fn = ptexprs[position] if 0 <= position < len(ptexprs) else ptexprs[-1]
        if not isinstance(fn, tuple) or fn[0] != "fn" or fn[1] is None:
            return None
        t = self.inst(fn[1], self.infer(target, kf, kf.occurrences[call_id]), kf2, rec["scope"])
        return t if t is not None and t[0] in ("class", "lib", "java") else None

    def lambda_receivers(self, occ, kf):
        """The receivers of the receiver-lambdas around ``occ``, innermost first; ``None`` if one is unknown
        (the name may belong to it, so nothing is resolved), ``[]`` if there is none."""
        out = []
        for call_id, position in reversed(occ["lam"]):
            if not self.receiver_lambda(call_id, position, kf):
                continue
            t = self.lambda_receiver_type(call_id, position, kf)
            if t is None:
                return None
            out.append(t)
        return out

    def blocked(self, occ, kf) -> bool:
        """Whether the occurrence sits in a lambda whose implicit receiver may own the name."""
        return any(self.receiver_lambda(call_id, pos, kf) for call_id, pos in occ["lam"])

    def _loop_intrinsic(self, occ, kf) -> bool:
        """Whether this ``for`` loops over a range, array or string, with no iterator to call."""
        rt = self.type_of(occ["loop"], kf, occ["s"], occ["o"])
        return rt is not None and rt[0] in ("class", "lib") and \
            (rt[1] in LOOP_INTRINSIC or bool(_ARRAYS.fullmatch(rt[1])))

    def _primitive_receiver(self, occ, kf) -> bool:
        """Whether the operator's receiver is a primitive or an array: ``1..n`` is inlined
        whichever declaration (a member, or an extension on Comparable) the name finds."""
        if occ["r"] is None:
            return False
        rt = self.type_of(occ["r"], kf, occ["s"], occ["o"])
        if rt is None or rt[0] not in ("class", "lib"):
            return False
        name = KOTLIN_FOR.get(rt[1], rt[1])        # the JDK's String and boxes are Kotlin's primitives
        return name in INTRINSIC_OWNERS or bool(_ARRAYS.fullmatch(name))

    @staticmethod
    def _intrinsic(rec) -> bool:
        """Whether an operator's declaration is a primitive's or an array's, which the compiler inlines."""
        for owner in (rec["owner"], rec["receiver"]):
            if owner and (owner in INTRINSIC_OWNERS or _ARRAYS.fullmatch(owner)):
                return True
        return False

    @staticmethod
    def _type_read(cls) -> list:
        """A class named where a value is expected (a static receiver) is read, as a ``Use`` of it."""
        if cls is None or cls[0] not in ("class", "java", "lib"):
            return []
        return [("ref", ("create", cls[1]) if cls[0] == "class" else
                 ("jcreate", cls[1], 0) if cls[0] == "java" else ("libcreate", cls[1]))]

    def _reference(self, occ, kf) -> list:
        """What ``::name`` / ``Type::name`` / ``obj::name`` names, as call-style outcomes, or ``[]``.

        An overloaded name is refused at first; the function type the reference is passed as then narrows it,
        by arity and, if that is not enough, by parameter types."""
        found = self._reference_of(occ, kf)
        if found:
            return found
        arity = self._reference_arity(occ, kf)
        if arity is None:
            return []
        recv = occ["r"]
        rt = self.type_of(recv, kf, occ["s"], occ["o"]) if recv is not None else None
        # `Type::member` leaves the receiver to the caller; an object's `Util::f` is bound to the object
        unbound = rt is not None and rt[0] == "static" and not (self.ix.classes.get(rt[1]) or (None, {}))[1].get("object")
        try:
            for typed in (False, True):
                self._ref_arity = (arity, unbound, typed)
                found = self._reference_of(occ, kf)
                if found:
                    return found
            return []
        finally:
            self._ref_arity = None

    def _reference_of(self, occ, kf) -> list:
        name, recv, scope, owner = occ["n"], occ["r"], occ["s"], occ["o"]
        if occ.get("type_only"):               # the `Type` in `Type::member`
            written = occ["type_only"]
            if isinstance(written, tuple):     # an expression receiver: a type only if no variable has the name
                if written[0] == "name" and (written[2] is not None or
                                             self.free_var(written[1], kf, scope, owner) is not None):
                    return []
                cls = self.type_of(written, kf, scope, owner)
                cls = ("class", cls[1]) if cls is not None and cls[0] == "static" else (
                    cls if cls is not None and cls[0] in ("java", "lib") and written[0] == "name" else None)
            else:
                cls = self.type_name(written, kf, scope)
            if cls is None:
                return []
            return [("create", cls[1]) if cls[0] == "class" else
                    ("jcreate", cls[1], 0) if cls[0] == "java" else ("libcreate", cls[1])]
        if recv is None:
            binding = occ["b"]
            if binding is not None:
                if binding[0] == "fun":
                    cands = [self.ix.callables[k] for k in binding[1] if k in self.ix.callables]
                    hit = self._choose(cands)
                elif binding[0] == "local" and binding[1] in self.ix.variables:
                    hit = ("var", self.ix.variables[binding[1]])
                else:
                    return []
            else:
                hit = self.free_call(name, None, kf, scope, owner)
                if not isinstance(hit, tuple):
                    hit = self.free_var(name, kf, scope, owner)
        else:
            rt = self.type_of(recv, kf, scope, owner)
            if rt is None:
                return []
            hit = None
            if rt[0] == "static":                  # `Type::member` is the instance member first
                inst = ("class", rt[1])
                hit = self.find(inst, lambda t: self._fun_level(t, name, None))
                if hit is None:
                    hit = self.find(inst, lambda t: self._var_level(t, name))
                if hit is AMBIGUOUS or hit is OPAQUE:
                    return []
            if not isinstance(hit, tuple):
                hit = self.qualified_call(rt, name, None, kf)
            if not isinstance(hit, tuple) and rt[0] != "static":
                hit = self.find_member(rt, lambda t: self._var_level(t, name))
            subject = ("class", rt[1]) if rt[0] == "static" else rt
            if not isinstance(hit, tuple) and rt[0] == "static":
                found = self.extension_hit(subject, name, None, kf)    # `Point::ext`: unbound, so the instance type
                hit = found if isinstance(found, tuple) else None
            if not isinstance(hit, tuple):
                found = self.extension_var_hit(subject, name, kf)       # `Point::twice`
                hit = found if isinstance(found, tuple) else None
        if not isinstance(hit, tuple):
            return []
        kind = hit[0]
        if kind == "fun":
            return [("call", hit[1])]
        if kind in ("var", "dataprop"):
            return [("var", hit[1])]
        if kind == "ctor_call":
            return [("call", hit[2])]
        if kind == "ctor":
            return [("create", hit[1])]
        if kind == "jfun":
            return [("jcall", hit[1], hit[2], hit[3], hit[4])]
        if kind == "jctor":
            return [("jcreate", hit[1], hit[2])]
        if kind == "jdkfun":
            return [("jdkcall", hit[1], hit[2])]
        if kind == "libctor":
            return [("libcreate", hit[1])]
        if kind in ("jvar", "jdkvar"):
            return [hit]
        return []

    def resolve(self, occ, kf):
        """The declarations an occurrence refers to, as a list of tagged tuples, or ``[]``.

        ``("call", (kf, rec))``, ``("create", class)``, ``("var", (kf, rec))`` for Kotlin
        (project or standard library); ``("jcall", type, name, nargs)``,
        ``("jcreate", type, nargs)``, ``("jvar", type, name)`` for Java in the project;
        ``("jdkcall", type, name)``, ``("jdkvar", type, name)``, ``("libcreate", fq)``
        for the JDK and library classes.
        """
        if occ["r"] is not None and _contains(occ["r"], "this") and self.blocked(occ, kf):
            return []
        saved, saved_ctx = self._lambda_recv, self._lam_ctx
        self._lam_ctx = (occ, kf)
        if occ["r"] is None and occ["b"] is None:
            receivers = self.lambda_receivers(occ, kf)
            if receivers is None:
                self._lam_ctx = saved_ctx
                return []
            self._lambda_recv = receivers
        try:
            return self._resolve(occ, kf)
        finally:
            self._lambda_recv = saved
            self._lam_ctx = saved_ctx

    def _resolve(self, occ, kf):
        if occ["t"] == "ref":
            wrap = "dotref" if occ.get("dotref") else "ref"
            return [(wrap, o) for o in self._reference(occ, kf)]
        if occ["t"] == "call":
            if occ.get("loop") is not None and self._loop_intrinsic(occ, kf):
                return []
            if occ.get("op") and occ.get("sym") and self._primitive_receiver(occ, kf):
                return []
            target = self.call_target(occ["id"], kf)
            if target is None:
                return []
            init = occ.get("init")   # a delegation call creates nothing: the object exists
            kind = target[0]
            if occ.get("annot") and kind in ("ctor", "ctor_call", "libctor") and \
                    (kind == "libctor" or self.ix.classes[target[1]][1]["decl"] == "annotation"):
                return [("annot", target[1])]       # `Inner(1)` inside an annotation is an annotation
            if kind == "dataprop":
                return [("var", target[1])]       # componentN of a data class reads that property
            if kind == "fun" and occ["n"] == "equals" and occ.get("op") and \
                    target[1][1]["owner"] == "kotlin.Any":
                return []      # `==` on a type with no equals of its own: the universal default says nothing
            if kind == "jdkfun" and occ["n"] == "equals" and occ.get("op") and target[1] == "java.lang.Object":
                return []
            if kind == "fun":
                if occ.get("op") and self._intrinsic(target[1][1]):
                    return []
                return [("call", target[1])]
            if kind == "ctor":
                return [] if init else [("create", target[1])]
            if kind == "ctor_call":
                return ([] if init else [("create", target[1])]) + [("call", target[2])]
            if kind == "jfun":
                return [("jcall", target[1], target[2], target[3], target[4])]
            if kind == "jctor":
                return [("jcall", target[1], target[1].rsplit(".", 1)[-1], target[2])] + \
                    ([] if init else [("jcreate", target[1], target[2])])
            if kind == "jdkfun":
                return [("jdkcall", target[1], target[2])]
            if kind == "libctor":
                return [] if init else [("libcreate", target[1])]
            return []
        # a name
        if occ["m"] == "skip":                 # the head of `Outer.Inner::class`, read as a DotRef instead
            return []
        if occ["r"] is None:
            binding = occ["b"]
            if binding is not None:
                if binding[0] == "local" and binding[1] in self.ix.variables:
                    return [("var", self.ix.variables[binding[1]])]
                return []
            hit = self.free_var(occ["n"], kf, occ["s"], occ["o"], occ["m"])
            if hit is None and occ["m"] == "use":
                cls = self.type_name(occ["n"], kf, occ["s"])
                if cls is None and occ["n"] in self.ix.packages:
                    return [("ref", ("package", occ["n"]))]                      # `a` in `a.b.C.f()`
                return self._type_read(cls)                                       # `Util` in `Util.twice()`
        else:
            rt = self.type_of(occ["r"], kf, occ["s"], occ["o"])
            if rt is not None and rt[0] == "package":
                fq = f"{rt[1]}.{occ['n']}"
                if fq in self.ix.classes:
                    return self._type_read(("class", fq))
                if fq in self.ix.packages:
                    return [("ref", ("package", fq))]
                tops = [c for c in self.ix.top_vars.get((rt[1], occ["n"]), []) if c[1]["receiver"] is None]
                return [("var", tops[0])] if len(tops) == 1 else []
            hit = self.find_member(rt, lambda t, n=occ["n"]: self._var_level(t, n))
            if hit is None and rt is not None and rt[0] in ("class", "java", "lib"):
                hit = self.extension_var_hit(rt, occ["n"], kf)               # `p.twice`, `list.lastIndex`
            if hit is None and rt is not None and rt[0] in ("java", "lib"):
                accessor = self.synthetic_property(rt, occ["n"], occ["m"])    # `file.name` is getName()
                if accessor is not None:
                    return [("jcall", accessor[1], accessor[2], accessor[3], accessor[4])] if accessor[0] == "jfun" \
                        else [("jdkcall", accessor[1], accessor[2])]
            if hit is None and rt is not None and rt[0] == "static" and occ["m"] == "use":
                nested = self.ix.nested.get(rt[1], {}).get(occ["n"])
                if nested:
                    return self._type_read(("class", nested))                     # `Outer.Inner.f()`
        if not isinstance(hit, tuple):
            return []
        if hit[0] == "var":
            return [("var", hit[1])]
        if hit[0] == "jvar":
            return [("jvar", hit[1], hit[2])]
        if hit[0] == "jdkvar":
            return [("jdkvar", hit[1], hit[2])]
        if hit[0] == "jfun":
            return [("jcall", hit[1], hit[2], hit[3], hit[4])]    # a Java getter read as a property
        if hit[0] == "jdkfun":
            return [("jdkcall", hit[1], hit[2])]
        return []
