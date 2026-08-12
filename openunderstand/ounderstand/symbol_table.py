"""A project-wide index of declarations, built before the per-file passes run.

`process_file` sees one file. A pass that meets `basic_operation.sum` while
walking `fibonacci.java` has no way to know what that name refers to, so it
invents a placeholder entity -- 51 of the 68 spurious entities on the
calculator_app fixture, and the reason reference recall sits below half.

`merge_placeholder_entities()` repairs some of this after the fact, but only
where exactly one project-wide candidate matches, and it cannot help a pass
that needed the answer *while* deciding what to write.

This module does the cheap half of the work up front: one pass over every file
recording what each declares, keyed by simple name. It is deliberately not a
type checker -- it answers "which declarations in this project are called
`sum`, and what are their long names", which is what the passes actually need.
"""

from __future__ import annotations

import os
from fnmatch import fnmatch

from antlr4 import FileStream

from openunderstand.utils import antler_parser


class _DeclarationIndex:
    """Simple name -> long names declaring it, project-wide."""

    def __init__(self):
        self.by_simple_name: dict[str, set[str]] = {}
        # All the long names declaring a type under this simple name, not just
        # the first one indexed. Keeping only the first meant every `Node` in
        # TheAlgorithms resolved to DataStructures.Stacks.Node whichever
        # package actually declared it -- 92 of Couple's 159 false positives
        # there, and the same error reached DotRef through resolve_type().
        self.types: dict[str, set[str]] = {}
        #: Class long name -> the simple names it extends *and* implements.
        #: Interfaces matter as much as superclasses: Understand reports
        #: BinarySearch.find as overriding SearchAlgorithm.find, and recording
        #: only `extends` found 5 of TheAlgorithms' 47 Overrides.
        self.supertypes: dict[str, list[str]] = {}
        #: Method long name -> every declaration under it, each as
        #: (parameter type names, is_abstract, is_generic).
        #:
        #: `Java Overrides` needs the *supertype's* declaration, which lives in
        #: another file, to tell an override from a same-named overload:
        #: MaxHeap.getElement(int) does not override Heap.getElement().
        #:
        #: A list, not one entry: overloads share a long name. SortAlgorithm
        #: declares both `sort(T[])` and `sort(List<T>)`, and keeping one
        #: dropped the abstract generic overload that Understand refuses to
        #: report -- which is 15 wrong rows, one per class implementing it.
        self.methods: dict[str, list[tuple[tuple[str, ...], bool, bool]]] = {}
        self.files = 0

    def add(self, simple_name: str, longname: str, is_type: bool = False):
        if not simple_name or not longname:
            return
        self.by_simple_name.setdefault(simple_name, set()).add(longname)
        if is_type:
            self.types.setdefault(simple_name, set()).add(longname)

    @staticmethod
    def _closest(candidates, simple_name: str, scope_longname: str) -> str | None:
        """The candidate an asking scope would bind, or None when ambiguous.

        Innermost scope first, the way Java resolves: a declaration in the
        scope that asked wins over one in its enclosing scope, which wins over
        one further out. Then a declaration in the asking scope's own package;
        otherwise a unique match wins and an ambiguous one is refused.
        Refusing beats guessing: a wrong resolution silently misattributes
        every reference built on it.

        Without the innermost walk the ambiguity check below refused every
        name more than one scope declares -- `c` in CDL.getValue and in
        CDL.rowToJSONArray resolved to neither.
        """
        if not candidates:
            return None
        scope = scope_longname
        while scope:
            candidate = scope + "." + simple_name
            if candidate in candidates:
                return candidate
            scope = scope.rsplit(".", 1)[0] if "." in scope else ""
        if len(candidates) == 1:
            return next(iter(candidates))
        package = scope_longname.rsplit(".", 1)[0] if scope_longname else ""
        if package:
            local = [c for c in candidates if c.startswith(package + ".")]
            if len(local) == 1:
                return local[0]
        return None

    def resolve(self, simple_name: str, scope_longname: str = "") -> str | None:
        """Long name for a simple name, or None when it is ambiguous."""
        return self._closest(
            self.by_simple_name.get(simple_name), simple_name, scope_longname)

    def resolve_type(self, simple_name: str, scope_longname: str = "") -> str | None:
        """Long name for a *type's* simple name, or None when it is ambiguous."""
        return self._closest(
            self.types.get(simple_name), simple_name, scope_longname)

    def declares(self, type_longname: str, member: str) -> bool:
        return f"{type_longname}.{member}" in self.by_simple_name.get(member, ())

    def declaring_type(self, type_longname: str, member: str) -> str | None:
        """The class in `type_longname`'s hierarchy that declares `member`.

        Understand attributes a call to the class that *declares* the method,
        not to the static type of the receiver: `XMLTokener extends
        JSONTokener` and `next()` is declared in the parent, so
        `x.next()` on an XMLTokener is a call to org.json.JSONTokener.next.

        Returns None when no class in the chain declares it -- which includes
        every method inherited from the JDK, since a supertype outside the
        project has no members here to search. Understand reports
        JSONObject.Null.equals as java.lang.Object.equals; this cannot.
        """
        seen = set()
        current = type_longname
        while current and current not in seen:
            if self.declares(current, member):
                return current
            seen.add(current)
            for parent in self.supertypes.get(current, []):
                resolved = self.resolve_type(parent, current)
                if resolved and resolved not in seen:
                    found = self.declaring_type(resolved, member)
                    if found:
                        return found
            return None
        return None

    def overridden_declaration(self, owner: str, member: str,
                               parameters: tuple) -> str | None:
        """The supertype whose declaration of `member` this one overrides.

        Stricter than declaring_type(): an override has to match the
        signature, and `MaxHeap.getElement(int)` does not override
        `Heap.getElement()`. Parameter *types* are compared as written, not
        just counted, because SortAlgorithm's two `sort` overloads both take
        one argument and only one of them is overridden. This is not full Java
        overload resolution -- an inherited generic renamed from T to E would
        defeat it -- but it separates every case in either benchmark.

        An *abstract generic* declaration is skipped, because Understand does
        not report overrides of one. `Sorts.SortAlgorithm.sort(T[] unsorted)`
        has no Overriddenby in Understand's own database even though fifteen
        classes implement it, while its concrete `sort(List<T>)` sibling and
        the non-generic abstract `Heap.getElement()` both do. Emitting them
        anyway was 21 of this pass's 23 wrong rows on TheAlgorithms.
        """
        seen = set()

        def search(current):
            if not current or current in seen:
                return None
            seen.add(current)
            for parent in self.supertypes.get(current, []):
                resolved = self.resolve_type(parent, current)
                if not resolved:
                    continue
                for declared, abstract, generic in self.methods.get(
                        f"{resolved}.{member}", ()):
                    if declared == parameters and not (abstract and generic):
                        return resolved
                found = search(resolved)
                if found:
                    return found
            return None

        return search(owner)

    def __len__(self):
        return sum(len(v) for v in self.by_simple_name.values())


#: Populated by build(); read by the passes through resolve().
INDEX = _DeclarationIndex()

#: java.lang is imported implicitly, so a bare `Integer` or `Character` carries
#: no import to resolve it against and is declared nowhere in the project. Only
#: the names that actually turn up are listed -- this is a lookup table, not a
#: model of the JDK.
#: ponytail: a name outside this set, outside the imports and outside the
#: project is left unresolved rather than guessed. Widen it if parity shows a
#: type being missed.
JAVA_LANG_TYPES = frozenset(
    """Boolean Byte Character Class ClassLoader Comparable Deprecated Double
    Enum Error Exception Float FunctionalInterface Integer Iterable Long Math
    Number Object Override Package Process Runtime SafeVarargs Short String
    StringBuffer StringBuilder SuppressWarnings System Thread Throwable
    Void""".split()
)

#: Declared type of well-known JDK fields, keyed by (owning type, field).
#:
#: Understand resolves a field access to the field's *declared* type and
#: couples to that as well as to the owner, so `System.out.println(...)` gives
#: both java.lang.System and java.io.PrintStream. Reproducing that in general
#: needs a model of the JDK's members, which this project has no access to;
#: these are the ones that actually occur. On TheAlgorithms, System.out alone
#: accounts for 144 of Understand's 1182 couples.
#:
#: ponytail: a hand-written table, so it covers exactly what is listed and
#: nothing else. System.in is deliberately absent -- no file in either
#: benchmark uses it, so there is no measurement to say whether Understand
#: couples it, and a guess here would be indistinguishable from a fix.
JDK_FIELD_TYPES = {
    ("java.lang.System", "out"): "java.io.PrintStream",
    ("java.lang.System", "err"): "java.io.PrintStream",
}

#: Overridable members of the JDK supertypes, as member -> parameter count.
#:
#: Most overrides in a real project are of JDK types, not of project ones: 15
#: of JSON's 15 and 34 of TheAlgorithms' 47. Understand indexes the whole Java
#: library and can see java.lang.Object.toString; this project cannot, and
#: CLAUDE.md is right that matching on the method *name* alone would claim an
#: override of every same-named method anywhere. Matching a name **and its
#: parameter count** against a supertype the class explicitly names is a
#: different question, and one the parse tree can answer.
#:
#: java.lang.Object is the exception that needs no `implements`: every class
#: extends it, so its five overridable members are always in scope. The rest
#: apply only where the class names them.
#:
#: ponytail: a hand-written table of the core language and collection
#: contracts. It is not a model of the JDK -- java.awt.event.ActionListener and
#: java.awt.Window are deliberately absent, so TheAlgorithms' six AWT overrides
#: stay unreported rather than pull the whole AWT hierarchy in behind them.
#: Add an interface here when parity shows one being missed.
JDK_OVERRIDABLE = {
    "java.lang.Object": {
        "toString": 0, "hashCode": 0, "equals": 1, "clone": 0, "finalize": 0,
    },
    "java.lang.Iterable": {"iterator": 0, "forEach": 1, "spliterator": 0},
    "java.lang.Runnable": {"run": 0},
    "java.lang.Comparable": {"compareTo": 1},
    "java.util.Iterator": {
        "hasNext": 0, "next": 0, "remove": 0, "forEachRemaining": 1,
    },
    "java.util.Comparator": {"compare": 2},
}

#: Simple name -> long name, for the supertypes named in JDK_OVERRIDABLE.
JDK_OVERRIDABLE_BY_SIMPLE_NAME = {
    longname.rsplit(".", 1)[-1]: longname for longname in JDK_OVERRIDABLE
}


def parameter_types(ctx) -> tuple:
    """Declared parameter types of a method declaration, as written.

    Compared textually between an override and the declaration above it, so
    both ends have to be read the same way -- the pass and the index share
    this rather than each counting parameters its own way.
    """
    parameters = getattr(ctx, "formalParameters", None)
    parameters = parameters() if callable(parameters) else None
    listed = parameters.formalParameterList() if parameters is not None else None
    if listed is None:
        return ()
    names = []
    formal = getattr(listed, "formalParameter", None)
    if callable(formal):
        names += [p.typeType().getText() for p in (formal() or [])]
    last = getattr(listed, "lastFormalParameter", None)
    last = last() if callable(last) else None
    if last is not None:
        names.append(last.typeType().getText() + "...")
    return tuple(names)


def build(root: str) -> _DeclarationIndex:
    """Index every declaration under `root`. Safe to call more than once."""
    global INDEX
    index = _DeclarationIndex()

    # Imported here: the listener imports class_properties, which imports the
    # generated parser, and this module is imported by the CLI before sys.path
    # has been arranged in some entry points.
    from openunderstand.analysis_passes.define_definein import DefineListener
    from openunderstand.analysis_passes import class_properties
    from openunderstand.gen.javaLabeled.JavaParserLabeledListener import (
        JavaParserLabeledListener)
    from antlr4 import ParseTreeWalker

    class _Supertypes(JavaParserLabeledListener):
        """Records `class X extends Y` as a long name -> simple name pair."""

        def __init__(self):
            self.pairs = []
            self.methods = {}

        def enterClassDeclaration(self, ctx):
            parents = class_properties.ClassPropertiesListener.findParents(ctx)
            longname = ".".join(parents + [ctx.IDENTIFIER().getText()])
            supers = []
            if ctx.EXTENDS() is not None and ctx.typeType() is not None:
                supers.append(ctx.typeType().getText().split("<")[0])
            if ctx.IMPLEMENTS() is not None and ctx.typeList() is not None:
                supers += [t.getText().split("<")[0]
                           for t in ctx.typeList().typeType()]
            if supers:
                self.pairs.append((longname, supers))

        def enterInterfaceDeclaration(self, ctx):
            if ctx.EXTENDS() is None or ctx.typeList() is None:
                return
            parents = class_properties.ClassPropertiesListener.findParents(ctx)
            longname = ".".join(parents + [ctx.IDENTIFIER().getText()])
            self.pairs.append(
                (longname, [t.getText().split("<")[0]
                            for t in ctx.typeList().typeType()]))

        # ------------------------------------------------------- signatures

        def enterMethodDeclaration(self, ctx):
            self._signature(ctx)

        def enterInterfaceMethodDeclaration(self, ctx):
            self._signature(ctx)

        def _signature(self, ctx):
            identifier = ctx.IDENTIFIER()
            if identifier is None or isinstance(identifier, list):
                return
            parents = class_properties.ClassPropertiesListener.findParents(ctx)
            longname = ".".join(parents + [identifier.getText()])

            body = ctx.methodBody()
            abstract = body is None or body.block() is None
            # <T> is on the genericMethodDeclaration wrapper, never on the
            # declaration that carries the name -- except in an interface,
            # where the typeParameters are inline.
            generic = (
                getattr(ctx.parentCtx, "typeParameters", None) is not None
                and callable(getattr(ctx.parentCtx, "typeParameters", None))
                and ctx.parentCtx.typeParameters() is not None
            ) or (
                callable(getattr(ctx, "typeParameters", None))
                and ctx.typeParameters() is not None
            )
            self.methods.setdefault(longname, []).append(
                (parameter_types(ctx), abstract, generic))

    for path in _java_files(root):
        try:
            tree = antler_parser.parse(
                FileStream(path, encoding="utf8"), "compilationUnit"
            )
            listener = DefineListener(path)
            ParseTreeWalker().walk(t=tree, listener=listener)
            supertypes = _Supertypes()
            ParseTreeWalker().walk(t=tree, listener=supertypes)
        except Exception:
            # A file that will not parse contributes nothing; the per-file
            # pass over it logs the failure in its own right.
            continue
        index.files += 1
        index.supertypes.update(supertypes.pairs)
        index.methods.update(supertypes.methods)
        for declaration in listener.defines:
            index.add(
                declaration["ent"],
                declaration["ent_longname"],
                is_type=declaration.get("decl") in ("class", "interface", "enum",
                                                    "annotation"),
            )

    INDEX = index
    return index


def resolve(simple_name: str, scope_longname: str = "") -> str | None:
    return INDEX.resolve(simple_name, scope_longname)


def resolve_type_name(name, imports=None, wildcards=None, scope_longname=""):
    """Long name for a type as written in source, or None if it cannot be placed.

    The order javac uses: an explicit single-type import, then an already
    qualified name, then the project's own types (innermost scope outward),
    then implicit java.lang, then a lone `import x.y.*`. Refusing beats
    guessing -- a wrong type silently misattributes every reference built on
    it.

    Several passes grew near-copies of this; they should converge here.
    """
    if not name:
        return None
    name = name.split("<")[0].split("[")[0]
    if not name:
        return None
    if imports and name in imports:
        return imports[name]
    if "." in name:
        return name
    in_project = resolve_type(name, scope_longname)
    if in_project:
        return in_project
    if name in JAVA_LANG_TYPES:
        return "java.lang." + name
    if wildcards and len(wildcards) == 1:
        return wildcards[0] + "." + name
    return None


def declaring_type(type_longname: str, member: str) -> str | None:
    """Class in `type_longname`'s hierarchy that declares `member`, or None."""
    return INDEX.declaring_type(type_longname, member)


def resolve_type(simple_name: str, scope_longname: str = "") -> str | None:
    """Long name for a *type's* simple name, or None if none resolves.

    resolve() searches every declaration, so a variable named `value` and a
    class named `Value` compete. A pass that already knows it is looking at a
    type position wants only the classes, interfaces, enums and annotations.

    Pass the asking scope. Without it a name several packages declare -- `Node`
    appears in DataStructures.Stacks, DataStructures.Lists and more -- binds to
    whichever was indexed first rather than the one in the caller's own
    package, and the reference is attributed to the wrong class.
    """
    return INDEX.resolve_type(simple_name, scope_longname)


def _java_files(root: str):
    for directory, _, names in os.walk(root):
        for name in names:
            if fnmatch(name, "*.java"):
                yield os.path.join(directory, name)
