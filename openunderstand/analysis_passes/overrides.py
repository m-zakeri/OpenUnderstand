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
import openunderstand.analysis_passes.class_properties as class_properties


class OverridesListener(JavaParserLabeledListener):
    def __init__(self):
        #: Positioned relations, written by Project.addTypeRelationRefs.
        self.relations = []

    def enterMethodDeclaration(self, ctx: JavaParserLabeled.MethodDeclarationContext):
        self._record(ctx)

    def enterInterfaceMethodDeclaration(
        self, ctx: JavaParserLabeled.InterfaceMethodDeclarationContext
    ):
        self._record(ctx)

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
        parameters = symbol_table.parameter_types(ctx)

        declaring = symbol_table.INDEX.overridden_declaration(owner, name, parameters)
        if declaring is None:
            declaring = self._anonymous_supertype(
                symbol_table, ctx, owner, name, parameters
            )
        if declaring is None:
            declaring = self._jdk_supertype(symbol_table, owner, name, len(parameters))
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

    @staticmethod
    def _anonymous_supertype(symbol_table, ctx, owner, name, parameters):
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
                    in_project = symbol_table.resolve_type(simple, owner)
                    if in_project:
                        for (
                            declared,
                            abstract,
                            generic,
                        ) in symbol_table.INDEX.methods.get(f"{in_project}.{name}", ()):
                            if declared == parameters and not (abstract and generic):
                                return in_project
                    longname = symbol_table.JDK_OVERRIDABLE_BY_SIMPLE_NAME.get(simple)
                    if longname and symbol_table.JDK_OVERRIDABLE[longname].get(
                        name
                    ) == len(parameters):
                        return longname
                return None
            node = node.parentCtx
        return None

    @staticmethod
    def _jdk_supertype(symbol_table, owner, name, arity):
        """A JDK interface this class names that declares `name`/`arity`."""
        for supertype in symbol_table.INDEX.supertypes.get(owner, []):
            longname = symbol_table.JDK_OVERRIDABLE_BY_SIMPLE_NAME.get(
                supertype.rsplit(".", 1)[-1]
            )
            if longname is None:
                continue
            if symbol_table.JDK_OVERRIDABLE[longname].get(name) == arity:
                return longname
        return None
