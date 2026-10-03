"""Java Use Cast / Java Useby Castby: the type named in a cast expression.
Also the plain Java Use of the type in `x instanceof T` and `x instanceof T v`,
which is the same question -- an expression naming a type -- asked of another
operator.

    (JSONObject) o        ->  Use Cast on org.json.JSONObject
    (T) array[i]          ->  Use Cast on Sorts.HeapSort.sort.T
    (int) x               ->  nothing

A cast names a type, and a reference needs an entity to point at. A primitive
has none -- Understand reports 10 Use Cast on TheAlgorithms and every cast to
int, char or double is absent from them -- so primitives are skipped. The old
pass emitted all of them, which is 64 of its 69 wrong rows.

Six of Understand's ten are casts to a *type parameter*, resolved against the
method or class that declares it (`Sorts.HeapSort.sort.T`, not `T` and not
`Sorts.HeapSort.T`), so the declaring generic is searched before the project.

The reference sits on the type name, not on the opening parenthesis: the old
pass took ctx.start, one column short of where Understand puts it every time.
"""

from openunderstand.gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from openunderstand.gen.javaLabeled.JavaParserLabeledListener import (
    JavaParserLabeledListener,
)
import openunderstand.analysis_passes.class_properties as class_properties

PRIMITIVES = {
    "int",
    "long",
    "short",
    "byte",
    "char",
    "float",
    "double",
    "boolean",
    "void",
}


def _declaring_generic(ctx, name):
    """Long name of the method or class declaring type parameter `name`.

    Walks out to each enclosing declaration and asks whether it introduced the
    name in its `<...>`. Returns None when nothing did, which is the common
    case -- most casts name an ordinary type.
    """

    def type_parameters(node):
        getter = getattr(node, "typeParameters", None)
        return getter() if callable(getter) else None

    node = ctx.parentCtx
    while node is not None:
        identifier = getattr(node, "IDENTIFIER", None)
        owner = identifier() if callable(identifier) else None
        if owner is not None and not isinstance(owner, list):
            declared = type_parameters(node) or type_parameters(node.parentCtx)
            if declared is not None:
                for parameter in declared.typeParameter():
                    if parameter.IDENTIFIER().getText() == name:
                        return ".".join(
                            class_properties.ClassPropertiesListener.findParents(node)
                            + [owner.getText()]
                        )
        node = node.parentCtx
    return None


class CastAndCastBy(JavaParserLabeledListener):
    def __init__(self, file_longname=""):
        self.file_longname = file_longname
        #: Positioned relations, written by Project.addTypeRelationRefs.
        self.relations = []
        self.imports = {}
        self.wildcards = []

    def enterImportDeclaration(self, ctx: JavaParserLabeled.ImportDeclarationContext):
        longname = ctx.qualifiedName().getText()
        if ctx.getText().rstrip(";").endswith(".*"):
            self.wildcards.append(longname)
            return
        self.imports[longname.split(".")[-1]] = longname

    def enterExpression5(self, ctx: JavaParserLabeled.Expression5Context):
        self._type_use(ctx, ctx.typeType(), "Java Use Cast")

    def enterExpression13(self, ctx: JavaParserLabeled.Expression13Context):
        """`x instanceof T`: a plain Use of T, at the type.

        Understand writes one on 144 of JSON's 145 instanceof expressions and
        nothing here wrote any of them.
        """
        self._type_use(ctx, ctx.typeType(), "Java Use")

    def enterExpression27(self, ctx: JavaParserLabeled.Expression27Context):
        """`x instanceof T name` (Java 16): the same Use of T as without the
        name. The variable itself is a local -- the pattern is spelled as a
        localVariableDeclaration -- so Define, Set Init and Typed come from the
        passes that handle locals."""
        declaration = ctx.pattern().localVariableDeclaration()
        if declaration is not None:
            self._type_use(ctx, declaration.typeType(), "Java Use")

    def _type_use(self, ctx, type_ctx, kind):
        from openunderstand.ounderstand import symbol_table

        if type_ctx is None or type_ctx.classOrInterfaceType() is None:
            return  # primitive, or `(int[])`
        named = type_ctx.classOrInterfaceType()
        identifiers = named.IDENTIFIER()
        name = ".".join(i.getText() for i in identifiers)
        if name in PRIMITIVES:
            return

        parents = class_properties.ClassPropertiesListener.findParents(ctx)
        if not parents:
            return
        scope = ".".join(parents)

        target = _declaring_generic(ctx, name)
        if target is not None:
            target = f"{target}.{name}"
        else:
            target = symbol_table.resolve_type(name, scope)
        if not target:
            # Never a bare simple name: merge_placeholder_entities() would fold
            # it into whichever single project entity happens to share it.
            target = symbol_table.resolve_type_name(
                name, self.imports, self.wildcards, scope
            )
        if not target or "." not in target:
            return

        token = named.start
        self.relations.append(
            {
                "kind": kind,
                "scope_longname": scope,
                "ent_longname": target,
                "name": identifiers[-1].getText(),
                "line": token.line,
                "col": token.column,
            }
        )
