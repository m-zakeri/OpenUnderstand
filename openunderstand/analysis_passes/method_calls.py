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


class MethodCallListener(JavaParserLabeledListener):
    def __init__(self, file_address=""):
        self.file_address = file_address
        self.calls = []

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
            "scope_longname": ".".join(
                class_properties.ClassPropertiesListener.findParents(ctx)
            ),
            "line": identifier.symbol.line,
            "col": identifier.symbol.column,
        })
