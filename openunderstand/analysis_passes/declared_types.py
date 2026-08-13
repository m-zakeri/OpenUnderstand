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

from openunderstand.gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener


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


def collect(ctx) -> dict:
    """Declared types under `ctx`, keyed by simple name."""
    collector = DeclaredTypeCollector()
    ParseTreeWalker().walk(collector, ctx)
    return collector.types
