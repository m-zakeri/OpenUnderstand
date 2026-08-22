"""Declared type of every name a subtree brings into scope.

Several passes need to know what `x` is before they can say what `x.foo()`
calls or what `x.p = v` sets, and the database cannot answer it: all 1206
parameters and 2552 of 4634 variables on the TheAlgorithms benchmark have a
null `_type`. Reading it off the parse tree is both cheaper and complete.

This answers only what a declaration states. It does not infer the type of an
expression, so `a.b.c` resolves `b` on `a`'s type and stops -- naming `c` would
need the type of a field on another class.
"""

from antlr4 import ParseTreeWalker

from openunderstand.gen.javaLabeled.JavaParserLabeledListener import (
    JavaParserLabeledListener,
)


class DeclaredTypeCollector(JavaParserLabeledListener):
    """Collects `name -> declared type simple name`."""

    def __init__(self):
        self.types = {}

    def enterFormalParameter(self, ctx):
        self._record(ctx.typeType(), [ctx.variableDeclaratorId()])

    def enterLocalVariableDeclaration(self, ctx):
        self._record(ctx.typeType(), ctx.variableDeclarators().variableDeclarator())

    def enterFieldDeclaration(self, ctx):
        self._record(ctx.typeType(), ctx.variableDeclarators().variableDeclarator())

    def enterResource(self, ctx):
        """`try (Scanner input = new Scanner(System.in))` declares input.

        A resource is its own grammar rule, not a localVariableDeclaration, so
        every call on a try-with-resources variable had an unknown receiver --
        `input.nextLine()` was the single most common missing Java Call on
        TheAlgorithms. Its type is a classOrInterfaceType rather than a
        typeType.
        """
        self._record(ctx.classOrInterfaceType(), [ctx.variableDeclaratorId()])

    def enterEnhancedForControl(self, ctx):
        """`for (Edge e : edges)` declares e."""
        self._record(ctx.typeType(), [ctx.variableDeclaratorId()])

    def enterCatchClause(self, ctx):
        """`catch (JSONException e)` declares e.

        A catch parameter is its own grammar rule -- `catchType IDENTIFIER`,
        with no variableDeclaratorId -- so it was collected by nothing, and
        `e.getMessage()` was the single most common unresolved call receiver
        on JSON: 139 of the 170 with a bare name. A multi-catch names several
        types and no one of them is the answer, so only the single case is
        recorded.
        """
        identifier = ctx.IDENTIFIER()
        catch_type = ctx.catchType()
        if identifier is None or catch_type is None:
            return
        names = catch_type.qualifiedName()
        if len(names) != 1:
            return
        parts = names[0].IDENTIFIER()
        if parts:
            self.types[identifier.getText()] = parts[-1].getText()

    def _record(self, type_ctx, declarators):
        if type_ctx is None:
            return
        # Generic arguments and array brackets are not part of the type's name:
        # a field declared `Node<Element> firstElement` has type Node.
        name = type_ctx.getText().split("<")[0].split("[")[0]
        for declarator in declarators or []:
            # `variableDeclarator: variableDeclaratorId ('=' variableInitializer)?`
            # -- getText() on an initialised one is "temp=null", so the name has
            # to come from the id.
            declarator_id = getattr(declarator, "variableDeclaratorId", None)
            if callable(declarator_id):
                declarator = declarator_id() or declarator
            identifier = declarator.getText().split("[")[0]
            if identifier:
                self.types[identifier] = name


#: Declarations that open a scope of their own.
_NESTED_TYPE = (
    "ClassDeclaration",
    "InterfaceDeclaration",
    "EnumDeclaration",
    "AnnotationTypeDeclaration",
)


def collect(ctx) -> dict:
    """Declared types under `ctx`, keyed by simple name."""
    collector = DeclaredTypeCollector()
    ParseTreeWalker().walk(collector, ctx)
    return collector.types


def collect_own(ctx) -> dict:
    """`collect`, but not descending into a nested type declaration.

    A class body contains its nested classes, and the plain walk folded their
    fields in with its own: `Outer.items` is an ArrayList and
    `Outer.Inner.items` a String, and whichever was declared last won for both.
    That is a wrong receiver type for every `this.items` in the file, and a
    wrong target is worse than a missing one.
    """
    collector = DeclaredTypeCollector()
    # Exact names: `FormalParameters` is not a `FormalParameter`, and a prefix
    # match handed the plural context to a handler that reads typeType().
    handlers = {
        "FormalParameterContext": collector.enterFormalParameter,
        "LocalVariableDeclarationContext": collector.enterLocalVariableDeclaration,
        "FieldDeclarationContext": collector.enterFieldDeclaration,
        "ResourceContext": collector.enterResource,
        "EnhancedForControlContext": collector.enterEnhancedForControl,
        "CatchClauseContext": collector.enterCatchClause,
    }
    stack = [ctx]
    while stack:
        node = stack.pop()
        handler = handlers.get(type(node).__name__)
        if handler is not None:
            handler(node)
        for child in getattr(node, "children", None) or ():
            if hasattr(child, "getRuleIndex") and not type(child).__name__.startswith(
                _NESTED_TYPE
            ):
                stack.append(child)
    return collector.types
