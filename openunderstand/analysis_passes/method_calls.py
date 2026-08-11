"""Record every method-call site, resolved or not.

The existing call pass resolves a call against the classes it can see in the
one file being parsed, so on the JSON benchmark it found 172 of the 1722 calls
Understand reports. Most calls in a project cross files, and `process_file`
never sees more than one.

Rather than build a project-wide symbol table up front, this pass records the
call site unconditionally and lets the write layer create a placeholder entity
for a name it cannot resolve locally. `merge_placeholder_entities()` already
runs after every file has been parsed and folds a placeholder into the real
entity when exactly one project-wide match exists -- which is the symbol table,
arrived at from the other direction.
"""

from openunderstand.gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from openunderstand.gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener
import openunderstand.analysis_passes.class_properties as class_properties
from openunderstand.analysis_passes import declared_types


class MethodCallListener(JavaParserLabeledListener):
    def __init__(self, file_address=""):
        self.file_address = file_address
        self.calls = []
        #: Declared types in scope. A class's fields are collected when the
        #: class opens and a method's parameters and locals when it opens, both
        #: of which precede any call inside them.
        self.field_types = {}
        self.local_types = {}

    def enterClassDeclaration(self, ctx: JavaParserLabeled.ClassDeclarationContext):
        body = ctx.classBody()
        if body is not None:
            self.field_types = declared_types.collect(body)

    def enterMethodDeclaration(self, ctx: JavaParserLabeled.MethodDeclarationContext):
        self.local_types = declared_types.collect(ctx)

    def enterConstructorDeclaration(self, ctx: JavaParserLabeled.ConstructorDeclarationContext):
        self.local_types = declared_types.collect(ctx)

    def declared_type(self, name):
        """Simple name of `name`'s declared type: a local first, then a field."""
        if not name:
            return None
        return self.local_types.get(name) or self.field_types.get(name)

    def enterMethodCall0(self, ctx: JavaParserLabeled.MethodCall0Context):
        identifier = ctx.IDENTIFIER()
        if identifier is None:
            return
        parent = ctx.parentCtx
        receiver = None
        # `a.b()` parses as expression1 with the call as its right-hand side;
        # a bare `b()` has no receiver and is therefore a call on `this`.
        if type(parent).__name__ == "Expression1Context":
            expression = parent.expression()
            if expression is not None:
                receiver = expression.getText()
        self.calls.append({
            "name": identifier.getText(),
            "receiver": receiver,
            # Declared type of the receiver, when the source states one. The
            # write layer needs it to place the call: without it a name is
            # resolved project-wide and `entry.getValue()` on a Map.Entry
            # became a call to org.json.CDL.getValue, the only getValue the
            # project declares.
            "receiver_type": self.declared_type(
                receiver if receiver and receiver.isidentifier() else None),
            "scope_longname": ".".join(
                class_properties.ClassPropertiesListener.findParents(ctx)
            ),
            "line": identifier.symbol.line,
            "col": identifier.symbol.column,
        })
