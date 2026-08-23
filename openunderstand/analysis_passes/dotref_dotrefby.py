from openunderstand.gen.javaLabeled.JavaParserLabeledListener import (
    JavaParserLabeledListener,
)
from openunderstand.gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
import openunderstand.analysis_passes.class_properties as class_properties


class DotRef_DotRefBy(JavaParserLabeledListener):
    """Collect `Java DotRef`: a *type* used as the receiver of a dotted expression.

    `Character.forDigit(...)`, `JSONObject.testValidity(v)`, `Locale.ROOT` --
    Understand points at the receiver's identifier and scopes the reference to
    the enclosing method:

        Cookie.java:59:27  scope=org.json.Cookie.escape  ent=java.lang.Character

    A receiver that is a *variable* is not a DotRef -- `sb.append(...)` is a Use
    Deref Partial. This pass used to accept any receiver whose text appeared in
    a list of class names, which is why it needs the type test below.

    The state used to live in class attributes -- `implement = []` at class
    scope, mutated through `self.implement.append(...)`. Every instance shared
    one list, so each file re-emitted everything collected before it: the
    references for CookieList.java were written again against HTTP.java,
    HTTPTokener.java and every file after them. 2973 rows on TheAlgorithms, none
    of which matched Understand.
    """

    def __init__(self):
        self.package_name = ""
        self.imports = {}
        self.implement = []

    def enterPackageDeclaration(self, ctx: JavaParserLabeled.PackageDeclarationContext):
        self.package_name = ctx.qualifiedName().getText()

    def enterImportDeclaration(self, ctx: JavaParserLabeled.ImportDeclarationContext):
        longname = ctx.qualifiedName().getText()
        if ctx.getText().rstrip(";").endswith(".*"):
            # `import java.util.*` names a package. Taking the last segment
            # registered 'util' as if it were an importable type.
            # ponytail: a receiver that only a wildcard could resolve is left
            # unresolved rather than guessed -- this pass's precision comes
            # from refusing names it cannot place.
            return
        self.imports[longname.split(".")[-1]] = longname

    def enterExpression1(self, ctx: JavaParserLabeled.Expression1Context):
        if not ctx.DOT() or ctx.expression() is None:
            return
        receiver = ctx.expression().getText()
        # Only a bare name can be a type here. Anything else is a chained call
        # or an indexed access -- `sb.append(x).append(y)`, `a[i].f` -- whose
        # receiver is a value, not a type.
        if not receiver.isidentifier():
            return
        parents = class_properties.ClassPropertiesListener.findParents(ctx)
        if not parents:
            return
        scope_longname = ".".join(parents)
        # Resolved from the asking scope: `Node` is declared in several
        # packages, and without it the name binds to whichever was indexed
        # first rather than the one this file would actually see.
        longname = self.resolve_type(receiver, scope_longname)
        if longname is None:
            return
        token = ctx.start
        self.implement.append(
            {
                "scope_longname": scope_longname,
                "refent_name": receiver,
                "refent_longname": longname,
                "line": token.line,
                "col": token.column,
            }
        )

    def resolve_type(self, name, scope_longname=""):
        """Long name if `name` denotes a type, else None."""
        # Deferred: openunderstand.ounderstand's __init__ reaches oudb.api ->
        # parsing_process -> the module that imports this pass.
        from openunderstand.ounderstand import symbol_table

        if name in self.imports:
            return self.imports[name]
        in_project = symbol_table.resolve_type(name, scope_longname)
        if in_project:
            return in_project
        if name in symbol_table.JAVA_LANG_TYPES:
            return "java.lang." + name
        return None
