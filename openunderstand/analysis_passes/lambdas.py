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
from openunderstand.gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener
import openunderstand.analysis_passes.class_properties as class_properties


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
        # Numbered per enclosing method, not per file: A_Star has one
        # lambda_expr_1 in aStar and Kruskal another in kruskal.
        index = self._counts[scope] = self._counts.get(scope, 0) + 1
        name = f"(lambda_expr_{index})"

        token = ctx.start
        self.relations.append({
            "kind": "Java Use Ptr",
            "scope_longname": scope,
            "ent_longname": f"{scope}.{name}",
            "ent_kind": "Java Method Lambda",
            "name": name,
            "line": token.line,
            "col": token.column,
        })
