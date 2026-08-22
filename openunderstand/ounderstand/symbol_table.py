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

from openunderstand.oudb import jdk_index
from openunderstand.utils import antler_parser


class _DeclarationIndex:
    """Simple name -> long names declaring it, project-wide."""

    def __init__(self):
        self.by_simple_name: dict[str, set[str]] = {}
        self.types: dict[str, set[str]] = {}
        self.supertypes: dict[str, list[str]] = {}
        self.methods: dict[str, list[tuple[tuple[str, ...], bool, bool]]] = {}
        self.return_types: dict[str, str] = {}
        self.field_types: dict[tuple[str, str], str] = {}
        self.file_imports: dict[str, tuple[dict, list]] = {}
        self.interfaces: set[str] = set()
        self.overloads: dict[str, list] = {}
        self.superclasses: dict[str, tuple] = {}
        self.files = 0

    def add(self, simple_name: str, longname: str, is_type: bool = False):
        if not simple_name or not longname:
            return
        self.by_simple_name.setdefault(simple_name, set()).add(longname)
        if is_type:
            self.types.setdefault(simple_name, set()).add(longname)

    @staticmethod
    def _closest(
        candidates, simple_name: str, scope_longname: str, local_only: bool = False
    ) -> str | None:
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
        package = scope_longname.rsplit(".", 1)[0] if scope_longname else ""
        if package:
            local = [c for c in candidates if c.startswith(package + ".")]
            if len(local) == 1:
                return local[0]
        if local_only:
            return None
        if len(candidates) == 1:
            return next(iter(candidates))
        return None

    def resolve(self, simple_name: str, scope_longname: str = "") -> str | None:
        """Long name for a simple name, or None when it is ambiguous."""
        return self._closest(
            self.by_simple_name.get(simple_name), simple_name, scope_longname
        )

    def resolve_type(
        self, simple_name: str, scope_longname: str = "", local_only: bool = False
    ) -> str | None:
        """Long name for a *type's* simple name, or None when it is ambiguous."""
        return self._closest(
            self.types.get(simple_name), simple_name, scope_longname, local_only
        )

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

    def overridden_declaration(
        self, owner: str, member: str, parameters: tuple
    ) -> str | None:
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
                    f"{resolved}.{member}", ()
                ):
                    if declared == parameters and not (abstract and generic):
                        return resolved
                found = search(resolved)
                if found:
                    return found
            return None

        return search(owner)

    def __len__(self):
        return sum(len(v) for v in self.by_simple_name.values())


INDEX = _DeclarationIndex()

JAVA_LANG_TYPES = frozenset(
    name
    for name, longnames in jdk_index._load()["by_simple"].items()
    if any(l.rsplit(".", 1)[0] == "java.lang" for l in longnames)
)


def _jdk_package(name):
    """Package declaring a JDK simple name, when exactly one does."""
    return jdk_index.package_of(name)


class _PackageTable(dict):
    """Simple name -> package, answered from the JDK index on demand.

    Kept as a mapping because the passes read it like one; nothing is
    materialised, so widening the index widens this with it.
    """

    def get(self, name, default=None):
        return _jdk_package(name) or default

    def __contains__(self, name):
        return _jdk_package(name) is not None

    def __getitem__(self, name):
        found = _jdk_package(name)
        if found is None:
            raise KeyError(name)
        return found


#: Simple name -> the JDK package declaring it.
JDK_TYPE_PACKAGES = _PackageTable()


class _FieldTable(dict):
    """(owning type, field) -> the field's declared type, from the JDK index.

    `System.out` is a java.io.PrintStream, and Understand attributes a call on
    it to PrintStream rather than to System. The hand-written version knew
    System.out and System.err and nothing else; this knows 303 types' fields.
    """

    def get(self, key, default=None):
        owner, field = key
        return jdk_index.field_type(owner, field) or default

    def __contains__(self, key):
        return self.get(key) is not None


JDK_FIELD_TYPES = _FieldTable()


class _OverridableTable(dict):
    """JDK type -> {member: parameter count}, for override attribution.

    Every interface in the index, not the seven that were listed by hand --
    which is what left java.awt.Window.paint and the AWT listeners unreported.
    """

    def get(self, longname, default=None):
        return jdk_index.members(longname) or default

    def __getitem__(self, longname):
        return jdk_index.members(longname)

    def __contains__(self, longname):
        return bool(jdk_index.members(longname))


JDK_OVERRIDABLE = _OverridableTable()


class _OverridableBySimpleName(dict):
    """Simple name -> long name, for a supertype named in `implements`."""

    def get(self, name, default=None):
        longname = jdk_index.resolve_simple(name)
        return longname if longname and jdk_index.members(longname) else default


JDK_OVERRIDABLE_BY_SIMPLE_NAME = _OverridableBySimpleName()


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
        JavaParserLabeledListener,
    )
    from antlr4 import ParseTreeWalker

    class _Supertypes(JavaParserLabeledListener):
        """Records `class X extends Y` as a long name -> simple name pair."""

        def __init__(self):
            self.pairs = []
            self.superclasses = {}
            self.methods = {}
            self.returns = {}
            self.fields = {}
            self.imports = {}
            self.wildcards = []
            self.overloads = {}

        def enterClassDeclaration(self, ctx):
            parents = class_properties.ClassPropertiesListener.findParents(ctx)
            longname = ".".join(parents + [ctx.IDENTIFIER().getText()])
            supers = []
            if ctx.EXTENDS() is not None and ctx.typeType() is not None:
                supers.append(ctx.typeType().getText().split("<")[0])
            if ctx.IMPLEMENTS() is not None and ctx.typeList() is not None:
                supers += [t.getText().split("<")[0] for t in ctx.typeList().typeType()]
            if supers:
                self.pairs.append((longname, supers))
            if ctx.EXTENDS() is not None and ctx.typeType() is not None:
                self.superclasses[longname] = ctx.typeType().getText().split("<")[0]

        def enterEnumDeclaration(self, ctx):
            """`enum MyEnum implements JSONString` -- plus the implicit parent.

            Enums were skipped entirely, so `enum MyEnum implements JSONString`
            coupled MyEnum to its own supertype, and `myEnum.name()` in a
            *caller* found no declaring type at all: `name` is java.lang.Enum's,
            which is every enum's superclass and was recorded for none of them.
            """
            parents = class_properties.ClassPropertiesListener.findParents(ctx)
            longname = ".".join(parents + [ctx.IDENTIFIER().getText()])
            supers = ["java.lang.Enum"]
            if ctx.typeList() is not None:
                supers += [t.getText().split("<")[0] for t in ctx.typeList().typeType()]
            self.pairs.append((longname, supers))

        def enterInterfaceDeclaration(self, ctx):
            if ctx.EXTENDS() is None or ctx.typeList() is None:
                return
            parents = class_properties.ClassPropertiesListener.findParents(ctx)
            longname = ".".join(parents + [ctx.IDENTIFIER().getText()])
            self.pairs.append(
                (
                    longname,
                    [t.getText().split("<")[0] for t in ctx.typeList().typeType()],
                )
            )

        # ------------------------------------------------------- signatures

        def enterImportDeclaration(self, ctx):
            longname = ctx.qualifiedName().getText()
            if ctx.getText().rstrip(";").endswith(".*"):
                self.wildcards.append(longname)
            elif ctx.STATIC() is None:
                self.imports[longname.split(".")[-1]] = longname

        def enterEnumConstant(self, ctx):
            """`VAL1` in `enum MyEnum { VAL1, VAL2 }` is a static field of MyEnum.

            Nothing recorded them, so `MyEnum.VAL1.equals(x)` had no receiver
            type and every member reached through an enum constant resolved to
            nothing -- two of JSON's classes couple to java.lang.Enum for
            exactly that call and we had neither.
            """
            identifier = ctx.IDENTIFIER()
            if identifier is None:
                return
            owner = ".".join(class_properties.ClassPropertiesListener.findParents(ctx))
            self.fields[(owner, identifier.getText())] = owner

        def enterFieldDeclaration(self, ctx):
            type_ctx = ctx.typeType()
            declarators = ctx.variableDeclarators()
            if type_ctx is None or declarators is None:
                return
            owner = ".".join(class_properties.ClassPropertiesListener.findParents(ctx))
            written = type_ctx.getText().split("<")[0]
            for declarator in declarators.variableDeclarator() or []:
                identifier = declarator.variableDeclaratorId()
                if identifier is not None:
                    self.fields[(owner, identifier.getText().split("[")[0])] = written

        def enterMethodDeclaration(self, ctx):
            self._signature(ctx)

        def enterConstructorDeclaration(self, ctx):
            # Constructors overload too -- org.json.JSONObject has six -- and
            # _signature() skips them because they have no return type.
            self._overload(ctx)

        def enterInterfaceMethodDeclaration(self, ctx):
            self._signature(ctx)

        def _overload(self, ctx):
            """Record one declaration's parameter count and its position."""
            identifier = ctx.IDENTIFIER()
            if identifier is None or isinstance(identifier, list):
                return
            parents = class_properties.ClassPropertiesListener.findParents(ctx)
            longname = ".".join(parents + [identifier.getText()])
            symbol = identifier.symbol
            self.overloads.setdefault(longname, []).append(
                (parameter_types(ctx), symbol.line, symbol.column + 1)
            )

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
                (parameter_types(ctx), abstract, generic)
            )
            self._overload(ctx)

            declared = getattr(ctx, "typeTypeOrVoid", None)
            declared = declared() if callable(declared) else None
            written = declared.getText() if declared is not None else None
            if written:
                written = written.split("<")[0].split("[")[0]
            if written and written not in ("void", ""):
                previous = self.returns.get(longname, written)
                # Overloads with different return types cannot place a call.
                self.returns[longname] = written if previous == written else ""
            elif longname in self.returns:
                self.returns[longname] = ""

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
        index.overloads.update(
            {
                name: [entry + (path,) for entry in entries]
                for name, entries in supertypes.overloads.items()
            }
        )
        index.superclasses.update(
            {name: (written, path) for name, written in supertypes.superclasses.items()}
        )
        index.return_types.update({k: v for k, v in supertypes.returns.items() if v})
        index.field_types.update(supertypes.fields)
        index.file_imports[path] = (supertypes.imports, supertypes.wildcards)
        for declaration in listener.defines:
            index.add(
                declaration["ent"],
                declaration["ent_longname"],
                is_type=declaration.get("decl")
                in ("class", "interface", "enum", "annotation"),
            )
            if declaration.get("decl") in ("interface", "annotation"):
                index.interfaces.add(declaration["ent_longname"])

    INDEX = index
    return index


def is_interface(longname: str) -> bool:
    """Whether a long name is a project interface or annotation type."""
    return longname in INDEX.interfaces


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
        head, _, rest = name.partition(".")
        outer = resolve_type(head, scope_longname)
        if outer:
            return outer + "." + rest
        return name
    in_scope = resolve_type(name, scope_longname, local_only=True)
    if in_scope:
        return in_scope
    if name in JAVA_LANG_TYPES:
        return "java.lang." + name
    if wildcards and len(wildcards) == 1 and name[:1].isupper():
        return wildcards[0] + "." + name
    from_jdk = jdk_index.resolve_simple(name, tuple(wildcards or ()))
    if from_jdk:
        return from_jdk
    return resolve_type(name, scope_longname)


def resolve_in_file(name: str, file_path: str, scope_longname: str = "") -> str | None:
    """Long name for a type as written in `file_path`, or None.

    The one entry point a pass needs: it applies the file's own imports without
    the pass having to collect them. A third-party type resolves here exactly
    as Understand resolves it -- from the import statement, with no jar
    involved. Understand records `org.junit.After` as an Unknown Annotation
    with no members, which is all an import can tell anyone.
    """
    imports, wildcards = INDEX.file_imports.get(file_path, ({}, []))
    return resolve_type_name(name, imports, wildcards, scope_longname)


def member_type(owner: str, field: str) -> str | None:
    """Declared type of `owner.field`, project or JDK, or None.

    The one place a field's type is answered. A pass walking a single file can
    only see the fields of the class it is in, so a chain leaving that class --
    `node.next.previous`, `System.out` -- needed either a hand-written table or
    a guess. Both are gone: project fields come from the index built before the
    passes run, and JDK fields from the generated index.
    """
    if not owner or not field:
        return None
    written = INDEX.field_types.get((owner, field))
    if written:
        # Resolved against the declaring type's own scope, which is the
        # package the field was declared in.
        return resolve_type_name(written, None, None, owner) or None
    return jdk_index.field_type(owner, field)


def return_type(owner: str, member: str, scope_longname: str = "") -> str | None:
    """Long name of the type `owner.member(...)` evaluates to, or None.

    Answers for a *project* method, which `jdk_index.return_type` cannot: it
    covers java./javax. only, so a chain through one of the project's own
    methods -- `x.nextTo(';').trim()` -- had nowhere to land. Follows the
    `extends`/`implements` chain the way a call does, because the method may
    be declared on a supertype.

    Returns None rather than a guess when the written type does not resolve.
    A wrong target is worse than a missing one.
    """
    declaring = INDEX.declaring_type(owner, member) or owner
    written = INDEX.return_types.get(f"{declaring}.{member}")
    if not written:
        return None
    return resolve_type_name(written, None, None, scope_longname or declaring)


def declaring_type(type_longname: str, member: str) -> str | None:
    """Class in `type_longname`'s hierarchy that declares `member`, or None."""
    return INDEX.declaring_type(type_longname, member)


#: A primitive may be passed where a wider one is expected.
_WIDENING = {
    "byte": {"short", "int", "long", "float", "double"},
    "short": {"int", "long", "float", "double"},
    "char": {"int", "long", "float", "double"},
    "int": {"long", "float", "double"},
    "long": {"float", "double"},
    "float": {"double"},
}
_BOXES = {
    "boolean": "java.lang.Boolean",
    "byte": "java.lang.Byte",
    "char": "java.lang.Character",
    "short": "java.lang.Short",
    "int": "java.lang.Integer",
    "long": "java.lang.Long",
    "float": "java.lang.Float",
    "double": "java.lang.Double",
}
#: Every box except Boolean and Character is a java.lang.Number.
_NOT_A_NUMBER = {"java.lang.Boolean", "java.lang.Character"}
_PRIMITIVES = frozenset(_BOXES) | {"void"}


def _parameter_longname(written, imports, wildcards, scope):
    """A declared parameter type as a long name, or None when it will not place.

    None means "do not judge this argument on it": a type variable (`T`) never
    resolves, and refusing the whole candidate over one would throw away every
    generic method.
    """
    base = written.split("<")[0].replace("...", "").strip()
    arrays = "[]" * base.count("[")
    base = base.split("[")[0]
    if not base:
        return None
    if base in _PRIMITIVES:
        return base + arrays
    resolved = resolve_type_name(
        base, imports, wildcards, scope
    ) or jdk_index.resolve_simple(base)
    return (resolved + arrays) if resolved else None


def _argument_fits(argument, parameter):
    """0 no, 1 assignable, 2 exactly this type -- Java's "most specific" rule.

    Scored rather than boolean because that is how the overload is chosen:
    `put(String, int)` and `put(String, Object)` both accept an int and Java
    calls the first, so an exact match has to outrank a widening one.
    """
    if parameter is None or argument is None:
        return 1  # unknown on either side judges nothing
    if argument == parameter:
        return 2
    if argument == "null":
        return 0 if parameter in _PRIMITIVES else 1
    if argument in _PRIMITIVES:
        if parameter in _WIDENING.get(argument, ()):
            return 1
        boxed = _BOXES.get(argument)
        if parameter == boxed:
            return 1
        if parameter == "java.lang.Object":
            return 1
        if parameter == "java.lang.Number" and boxed not in _NOT_A_NUMBER:
            return 1
        return 0
    if parameter in _PRIMITIVES:
        return 1 if _BOXES.get(parameter) == argument else 0
    if parameter == "java.lang.Object":
        return 1
    return 1 if parameter in ancestors(argument) else 0


def overload_site(longname: str, argument_types) -> tuple | None:
    """(line, column) of the overload a call with these argument types names.

    Understand counts distinct callee *entities*, and two overloads are two
    entities. Resolving `JSONObject.put(...)` by long name returned whichever
    row was created first, so a method calling three overloads counted one
    callee: 80 of JSON's methods had a callee name set identical to
    Understand's and a lower CountOutput for exactly that.

    Arity settles 68 of JSON's 100 overloaded names and none of the ones that
    matter -- `org.json.JSONArray.put` is 17 overloads and
    `org.json.JSONObject.put` 8 taking two arguments each -- so the types are
    matched too, scored for specificity the way Java resolves a call.

    None whenever the answer is not unique. A wrong overload is a wrong callee,
    and falling back to the first row is no worse than what came before.
    """
    entries = INDEX.overloads.get(longname)
    if not entries or len(entries) < 2 or argument_types is None:
        return None
    count = len(argument_types)
    scope = longname.rsplit(".", 1)[0]
    scored = []
    for written, line, column, path in entries:
        variadic = bool(written) and written[-1].endswith("...")
        if len(written) != count and not (variadic and count >= len(written) - 1):
            continue
        imports, wildcards = INDEX.file_imports.get(path, (None, None))
        total, fits = 0, True
        for index, argument in enumerate(argument_types):
            if index >= len(written):
                break  # swallowed by the variadic tail
            declared = _parameter_longname(written[index], imports, wildcards, scope)
            points = _argument_fits(argument, declared)
            if not points:
                fits = False
                break
            total += points
        if fits:
            # A fixed-arity candidate beats a variadic one taking the same
            # arguments, which is what Java does.
            scored.append((total + (0 if variadic else 1), line, column))
    if not scored:
        return None
    best = max(entry[0] for entry in scored)
    winners = [entry for entry in scored if entry[0] == best]
    return (winners[0][1], winners[0][2]) if len(winners) == 1 else None


def superclass_of(longname: str) -> str | None:
    """The class `longname` extends, java.lang.Object when it extends nothing.

    `super(...)` in a constructor calls the superclass's constructor, and
    Understand records it: `GenericBean.GenericBean`'s `super();` is a
    `Java Call` to java.lang.Object.Object. An enum's is java.lang.Enum.
    """
    if longname in INDEX.interfaces:
        return None
    entry = INDEX.superclasses.get(longname)
    if entry is None:
        parents = INDEX.supertypes.get(longname) or []
        if "java.lang.Enum" in parents:
            return "java.lang.Enum"
        return "java.lang.Object"
    written, path = entry
    imports, wildcards = INDEX.file_imports.get(path, (None, None))
    return resolve_type_name(written, imports, wildcards, longname)


def declaring_type_anywhere(type_longname: str, member: str) -> str | None:
    """The type declaring `member`, searching the project *and* then the JDK.

    `INDEX.declaring_type` stops at the project boundary and `jdk_index` knows
    only java./javax., so neither answers for `e.getMessage()` on an
    org.json.JSONException: the declaration is java.lang.Throwable's, three
    supertypes up and across that boundary. Understand couples 15 of JSON's
    classes to java.lang.Throwable for exactly that, and we had none.

    Kept separate from `declaring_type()`, which the Call pass uses: making
    calls resolve across the boundary too would change what every
    `Java Call` targets, and that is its own measurement.
    """
    if not type_longname or not member:
        return None
    found = INDEX.declaring_type(type_longname, member)
    if found:
        return found
    seen, pending = set(), [type_longname]
    while pending:
        current = pending.pop(0)
        if not current or current in seen:
            continue
        seen.add(current)
        found = jdk_index.declaring_type(current, member)
        if found:
            return found
        for parent in INDEX.supertypes.get(current, []):
            resolved = resolve_type_name(parent, None, None, current)
            if resolved:
                pending.append(resolved)
    # Only once the whole chain is exhausted. Object is every type's ancestor,
    # so consulting it inside the walk would answer for `equals` before
    # java.lang.Enum got the chance to.
    return "java.lang.Object" if jdk_index.declares_on_object(member) else None


def ancestors(longname: str) -> set:
    """Every supertype of `longname`, transitively, across the JDK boundary.

    Understand couples a class to neither itself nor an ancestor: it reports no
    org.json.JSONException -> java.lang.Throwable even though the constructors
    take one, and no JSONMLParserConfiguration -> org.json.ParserConfiguration.
    Excluding only java.lang.Object left six of those on JSON.
    """
    found, pending = set(), [longname]
    while pending:
        current = pending.pop()
        for parent in INDEX.supertypes.get(current, []):
            resolved = resolve_type_name(parent, None, None, current)
            if resolved and resolved not in found:
                found.add(resolved)
                pending.append(resolved)
        for parent in jdk_index.supertypes(current):
            if parent not in found:
                found.add(parent)
                pending.append(parent)
    return found


def is_project_type(longname: str) -> bool:
    """True when this long name is a type declared in the analysed source.

    Distinct from "does this name resolve": `java.lang.String` resolves through
    the JDK index and is not a project type. Understand needs the distinction
    because it writes some inverse references only for entities the project
    actually declares -- a `Java Couple` to `java.lang.String` carries no
    `Java Coupleby`, because there is no analysed entity to hang it on. On
    JSON the split is exact: 228 of Understand's 840 forward couples have an
    inverse, and all 228 target project types while none of the other 612 do.

    Tested against the whole index rather than the per-file catalogue a pass
    happens to hold: keying on one file's classes reported 364 forward couples
    against 3 inverses, because a couple to a class declared elsewhere in the
    project looked external.
    """
    if not longname:
        return False
    return longname in INDEX.types.get(longname.rsplit(".", 1)[-1], ())


def resolve_type(
    simple_name: str, scope_longname: str = "", local_only: bool = False
) -> str | None:
    """Long name for a *type's* simple name, or None if none resolves.

    resolve() searches every declaration, so a variable named `value` and a
    class named `Value` compete. A pass that already knows it is looking at a
    type position wants only the classes, interfaces, enums and annotations.

    Pass the asking scope. Without it a name several packages declare -- `Node`
    appears in DataStructures.Stacks, DataStructures.Lists and more -- binds to
    whichever was indexed first rather than the one in the caller's own
    package, and the reference is attributed to the wrong class.
    """
    return INDEX.resolve_type(simple_name, scope_longname, local_only)


def _java_files(root: str):
    for directory, _, names in os.walk(root):
        for name in names:
            if fnmatch(name, "*.java"):
                yield os.path.join(directory, name)
