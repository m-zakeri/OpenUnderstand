"""Java Use Ptr / Java Useby Ptr: a lambda expression.

    Comparator.comparingInt(a -> a.getDistance())
                            ^ Use Ptr, scope=A_Star.A_Star.aStar
                              ent=A_Star.A_Star.aStar.(lambda_expr_1)

Understand gives every lambda an entity of its own -- kind `Java Method
Lambda`, named `(lambda_expr_N)` and numbered from 1 within the method that
encloses it, in source order. The reference is scoped to that method and sits
on the lambda's first token, which is its first parameter rather than the `->`.

Both halves exist: 19 Use Ptr and 19 Useby Ptr on TheAlgorithms.

The entity's long name is the only place it is ever declared, so the relation
carries its kind -- created as Unknown it would be a placeholder, and
merge_placeholder_entities() folds those into whatever shares the simple name.
"""

from openunderstand.gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from openunderstand.gen.javaLabeled.JavaParserLabeledListener import (
    JavaParserLabeledListener,
)
import openunderstand.analysis_passes.class_properties as class_properties


def _lambda_source(ctx):
    """The lambda's own text, plus a newline so its last line counts.

    Every line and statement metric reads an entity's contents, and a lambda
    had none, so all of them answered 0 -- CountLineCodeExe disagreed with
    Understand on 145 of jenetics' lambdas. The newline is what Understand
    counts as the end of a line: `s -> f(s));` is one line to it.
    """
    stream = ctx.start.getInputStream()
    try:
        return stream.getText(ctx.start.start, ctx.stop.stop) + "\n"
    except Exception:
        return ""


class LambdaListener(JavaParserLabeledListener):
    def __init__(self, file_longname=""):
        self.file_longname = file_longname
        #: Positioned relations, written by Project.addTypeRelationRefs.
        self.relations = []
        #: Enclosing method long name -> how many lambdas seen in it so far.
        self._counts = {}

    def enterLambdaExpression(self, ctx: JavaParserLabeled.LambdaExpressionContext):
        parents = class_properties.ClassPropertiesListener.findParents(ctx)
        if not parents:
            return
        scope = ".".join(parents)
        # The name comes from class_properties, which is also what puts the
        # segment into every scope chain running through the body: one
        # numbering, so an entity and its declaring scope cannot disagree.
        name = class_properties.lambda_name(ctx)
        if name is None:
            return

        token = ctx.start
        self.relations.append(
            {
                "kind": "Java Use Ptr",
                "scope_longname": scope,
                "ent_longname": f"{scope}.{name}",
                "ent_kind": "Java Method Lambda",
                "name": name,
                "line": token.line,
                "col": token.column,
                "contents": _lambda_source(ctx),
            }
        )

        # After the Use Ptr above, which is what declares the lambda: written
        # first, this End made the lambda its own scope and created it as an
        # Unknown class placeholder that the declaration then never upgraded
        # -- five of JSON's lambdas lost their kind.
        # Understand ends a lambda with an End and no Begin, unlike every other
        # declaration: *on* the closing brace of a block body, but just *past*
        # the last character of an expression body. 35 of JSON's.
        body = ctx.lambdaBody()
        close = body.stop if body is not None else None
        if close is not None:
            column = close.column
            if not isinstance(body, JavaParserLabeled.LambdaBody1Context):
                column += len(close.text)
            self.relations.append(
                {
                    "kind": "Java End",
                    "scope_longname": f"{scope}.{name}",
                    "ent_longname": f"{scope}.{name}",
                    # No ent_kind: the Use Ptr above declares the lambda, and
                    # the writer re-parents an ent_kind lambda to the scope --
                    # which here is the lambda itself.
                    "name": name,
                    "line": close.line,
                    "col": column,
                }
            )
