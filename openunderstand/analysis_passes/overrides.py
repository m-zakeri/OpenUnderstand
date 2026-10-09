"""Java Overrides / Java Overriddenby.

A method overrides the one a supertype declares under the same name and
signature:

    MaxHeap.java:118:22  scope=DataStructures.Heaps.MaxHeap.getElement
                         ent=DataStructures.Heaps.Heap.getElement

Understand reports the pair from both ends, positioned on the *overriding*
method's name.

Three sources, tried in order, because the nearest declaration wins:

  1. a supertype inside the project, via symbol_table.overridden_declaration();
  2. a JDK supertype the class explicitly names -- `implements Iterator` makes
     `hasNext()` an override of java.util.Iterator.hasNext;
  3. java.lang.Object, which needs no `implements` because every class extends
     it. This is where most real overrides come from: all 15 of JSON's are of
     JDK members and 10 of those are Object's.

Signature matters. `MaxHeap.getElement(int)` is an overload, not an override of
`Heap.getElement()`, so the parameter types have to agree -- see
symbol_table.overridden_declaration() for that and for the abstract-generic
rule Understand applies.

Not reported: an override declared in an *anonymous* class. `new Iterator<T>()
{ ... }` names its supertype in a creator expression rather than a class
declaration, so the supertype index never sees it -- 3 of JSON's 15 and 6 of
TheAlgorithms' 47. Understand reports them against the enclosing method.
"""

from openunderstand.gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from openunderstand.gen.javaLabeled.JavaParserLabeledListener import (
    JavaParserLabeledListener,
)
import re

import openunderstand.analysis_passes.class_properties as class_properties


class OverridesListener(JavaParserLabeledListener):
    def __init__(self):
        #: Positioned relations, written by Project.addTypeRelationRefs.
        self.relations = []
        self.imports = {}
        self.wildcards = []

    def enterImportDeclaration(self, ctx: JavaParserLabeled.ImportDeclarationContext):
        longname = ctx.qualifiedName().getText()
        if ctx.STATIC() is not None:
            return
        if ctx.getText().rstrip(";").endswith(".*"):
            self.wildcards.append(longname)
        else:
            self.imports[longname.rsplit(".", 1)[-1]] = longname

    def enterMethodDeclaration(self, ctx: JavaParserLabeled.MethodDeclarationContext):
        self._record(ctx)

    def enterInterfaceMethodDeclaration(
        self, ctx: JavaParserLabeled.InterfaceMethodDeclarationContext
    ):
        self._record(ctx)

    def enterClassDeclaration(self, ctx: JavaParserLabeled.ClassDeclarationContext):
        if ctx.recordKeyword() is not None:
            parents = class_properties.ClassPropertiesListener.findParents(ctx)
            _RECORDS.add(".".join(parents + [ctx.IDENTIFIER().getText()]))

    def _record(self, ctx):
        from openunderstand.ounderstand import symbol_table

        identifier = ctx.IDENTIFIER()
        if identifier is None or isinstance(identifier, list):
            return
        name = identifier.getText()
        parents = class_properties.ClassPropertiesListener.findParents(ctx)
        if not parents:
            return
        owner = ".".join(parents)  # the class declaring this method
        if _private(ctx):
            # A private method overrides nothing: jfreechart's private
            # readObject was reported overriding its superclass's, 180 times.
            # A static one *hides*, and Understand reports that as Overrides
            # (`main` in three of TheAlgorithms' list classes).
            return
        parameters = symbol_table.parameter_types(ctx)

        declaring = symbol_table.INDEX.overridden_declaration(owner, name, parameters)
        if declaring is None:
            declaring = self._anonymous_supertype(
                symbol_table, ctx, owner, name, parameters
            )
        if declaring is None:
            declaring = _jdk_ancestor(symbol_table, owner, name, parameters)
        if declaring is None:
            if symbol_table.JDK_OVERRIDABLE["java.lang.Object"].get(name) == len(
                parameters
            ):
                declaring = "java.lang.Object"
        if declaring is None:
            return

        self.relations.append(
            {
                "kind": "Java Overrides",
                "scope_longname": f"{owner}.{name}",
                "ent_longname": f"{declaring}.{name}",
                "name": name,
                "line": identifier.symbol.line,
                "col": identifier.symbol.column,
            }
        )

    def _anonymous_supertype(self, symbol_table, ctx, owner, name, parameters):
        """The type an enclosing `new Iterator<T>() { ... }` implements.

        An anonymous class names its supertype in a creator expression rather
        than a class declaration, so the supertype index never sees it and the
        method looks like it overrides nothing. Understand scopes these to the
        enclosing method -- org.json.XML.codePointIterator.iterator.hasNext.
        """
        node = ctx.parentCtx
        while node is not None:
            if type(node).__name__.startswith("Creator"):
                created = node.createdName()
                identifiers = created.IDENTIFIER() if created is not None else None
                if identifiers:
                    simple = identifiers[-1].getText()
                    written = ".".join(i.getText() for i in identifiers)
                    in_project = symbol_table.resolve_type(simple, owner)
                    if in_project:
                        for (
                            declared,
                            abstract,
                            generic,
                        ) in symbol_table.INDEX.methods.get(f"{in_project}.{name}", ()):
                            if symbol_table.parameters_fit(
                                declared, parameters
                            ) and not (abstract and generic):
                                return in_project
                    # Up from the created type into the JDK: `new
                    # JComponentPopup() { show }` overrides JPopupMenu.show
                    # two levels up -- 247 rows on jhotdraw and ganttproject.
                    created_type = in_project or symbol_table.resolve_type_name(
                        written, self.imports, self.wildcards, owner
                    )
                    return _jdk_ancestor(
                        symbol_table, created_type, name, parameters,
                        include_self=True,
                    )
                return None
            node = node.parentCtx
        return None


def _private(ctx):
    node = ctx.parentCtx
    while node is not None and not type(node).__name__.startswith(
        ("ClassBodyDeclaration", "InterfaceBodyDeclaration")
    ):
        node = node.parentCtx
    if node is None:
        return False
    modifiers = getattr(node, "modifier", None)
    modifiers = modifiers() if callable(modifiers) else []
    return any(m.getText() == "private" for m in modifiers or [])


def _jdk_ancestor(symbol_table, owner, name, parameters, include_self=False):
    """The nearest JDK type above `owner` declaring `name(parameters)`.

    Walks the whole ancestry, project and JDK, nearest first and the
    superclass before the interfaces, resolving each project supertype the
    way its own file does. Matched on erased parameter types from
    jdk_signatures.txt.gz: one arity per name sent ZippedFileReader.read past
    Reader to Readable, and a type variable matches no array -- `compare(int[], int[])`
    overrides nothing in Understand's database.
    """
    from openunderstand.oudb import jdk_index

    if not owner:
        return None
    seen = set()
    level = [owner] if include_self else _parents(symbol_table, owner)
    while level:
        following = []
        for current in level:
            if current in seen:
                continue
            seen.add(current)
            described = jdk_index.signature_type(current)
            if described is not None:
                supers, overloads = described
                if any(_fits(p, parameters) for p in overloads.get(name, ())):
                    return current
                following.extend(supers)
            elif jdk_index.known(current):
                following.extend(jdk_index.supertypes(current))
            else:
                following.extend(_parents(symbol_table, current))
        level = following
    return None


def _fits(declared, written):
    if len(declared) != len(written):
        return False
    for jdk, ours in zip(declared, written):
        ours = _erase(ours)
        if jdk == "?":
            # A type variable takes any reference type but an array:
            # `compare(Point, Point)` overrides Comparator<Point>.compare in
            # Understand's database and `compare(int[], int[])` does not.
            if ours.endswith("]") or ours in _PRIMITIVES:
                return False
        elif jdk != ours:
            return False
    return True


_PRIMITIVES = frozenset(
    ("boolean", "byte", "char", "short", "int", "long", "float", "double")
)


def _erase(written):
    while "<" in written:
        written = re.sub(r"<[^<>]*>", "", written)
    written = written.replace("...", "[]")
    base, dims = re.match(r"([^\[]*)((?:\[\])*)$", written).groups()
    return base.rsplit(".", 1)[-1] + dims


def _parents(symbol_table, longname):
    """Direct supertypes, the superclass first: Understand attributes
    `KSubset.equals` to java.lang.Object, not to the Comparator it implements,
    and a record's equals/hashCode/toString to java.lang.Record."""
    index = symbol_table.INDEX
    imports, wildcards = index.file_imports.get(
        index.type_files.get(longname), (None, None)
    )
    found = []
    superclass = (
        "java.lang.Record" if longname in _RECORDS
        else symbol_table.superclass_of(longname)
    )
    if superclass:
        found.append(superclass)
    for written in index.supertypes.get(longname, []):
        resolved = symbol_table.resolve_type_name(
            written.split("<")[0], imports, wildcards, longname
        )
        if resolved:
            found.append(resolved)
    return list(dict.fromkeys(found))


#: Long names of the records seen so far; set by the listener as it meets them.
_RECORDS = set()
