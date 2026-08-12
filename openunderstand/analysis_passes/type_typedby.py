"""Java Typed / Java Typedby: what a declaration is declared as.

Understand records the reference against the *declared entity* and points it at
the type, positioned on the type's own token:

    CDL.java:55:30  scope=org.json.CDL.getValue.x   ent=org.json.JSONTokener
    CDL.java:58:9   scope=org.json.CDL.getValue.sb  ent=java.lang.StringBuilder
    CDL.java:55:14  scope=org.json.CDL.getValue     ent=java.lang.String

This pass used to emit both ends as simple names and let the write layer glue
the package on the front, which produced `org.json.x` for a local of
`CDL.getValue` and `org.json.String` for java.lang.String -- 24 of 1062
references matched Understand on JSON, 31 of 3717 on TheAlgorithms.

Understand emits no Typed for a primitive or for `void`; those were
`org.json.char` rows here.
"""

from openunderstand.gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from openunderstand.gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener
import openunderstand.analysis_passes.class_properties as class_properties


#: A declaration of one of these is not a reference to anything.
PRIMITIVES = frozenset(
    "byte short int long float double boolean char void var".split())


class TypedAndTypedByListener(JavaParserLabeledListener):
    def __init__(self):
        self.package_name = ""
        self.imports = {}
        self.typedBy = []

    @property
    def get_type(self):
        d = {}
        d["typedBy"] = self.typedBy
        return d

    def enterPackageDeclaration(self, ctx: JavaParserLabeled.PackageDeclarationContext):
        self.package_name = ctx.qualifiedName().getText()

    def enterImportDeclaration(self, ctx: JavaParserLabeled.ImportDeclarationContext):
        longname = ctx.qualifiedName().getText()
        if ctx.getText().rstrip(";").endswith(".*"):
            return          # a package, not a type
        self.imports[longname.split(".")[-1]] = longname

    # ---------------------------------------------------------------- helpers

    def resolve_type(self, name, scope_longname):
        """Long name of a type's simple name, or None if it names no type."""
        from openunderstand.ounderstand import symbol_table

        if not name or name in PRIMITIVES:
            return None
        if name in self.imports:
            return self.imports[name]
        if "." in name:
            return name
        in_project = symbol_table.resolve_type(name, scope_longname)
        if in_project:
            return in_project
        if name in symbol_table.JAVA_LANG_TYPES:
            return "java.lang." + name
        # Neither declared, imported nor implicitly available. Understand names
        # it from the JDK it indexes; this project cannot, and a package-glued
        # guess is what produced org.json.String.
        return None

    def record(self, ctx, declared_name, type_ctx):
        """Record `declared_name is of type_ctx`, positioned on the type."""
        if type_ctx is None or not declared_name:
            return
        # findParents() stops at the enclosing scopes, so the declared entity's
        # own name has to be appended: a local of CDL.getValue is
        # org.json.CDL.getValue.sb, not org.json.sb.
        parents = class_properties.ClassPropertiesListener.findParents(ctx)
        if not parents:
            return
        enclosing = ".".join(parents)
        # Generic arguments are their own reference kind (Typed
        # GenericArgument); the raw type is what Typed points at.
        type_name = type_ctx.getText().split("<")[0].split("[")[0]
        type_longname = self.resolve_type(type_name, enclosing)
        if type_longname is None:
            return
        token = type_ctx.start
        self.typedBy.append({
            "name": declared_name,
            "scope_longname": f"{enclosing}.{declared_name}",
            "type_name": type_name,
            "type_longname": type_longname,
            "line": token.line,
            "col": token.column,
        })

    @staticmethod
    def _declared_names(declarators):
        for declarator in declarators or []:
            identifier = declarator.variableDeclaratorId()
            if identifier is not None:
                yield identifier.getText().split("[")[0]

    # ------------------------------------------------------------- the shapes

    def enterFieldDeclaration(self, ctx: JavaParserLabeled.FieldDeclarationContext):
        for name in self._declared_names(
                ctx.variableDeclarators().variableDeclarator()):
            self.record(ctx, name, ctx.typeType())

    def enterLocalVariableDeclaration(
        self, ctx: JavaParserLabeled.LocalVariableDeclarationContext
    ):
        for name in self._declared_names(
                ctx.variableDeclarators().variableDeclarator()):
            self.record(ctx, name, ctx.typeType())

    def enterFormalParameter(self, ctx: JavaParserLabeled.FormalParameterContext):
        identifier = ctx.variableDeclaratorId()
        if identifier is not None:
            self.record(ctx, identifier.getText().split("[")[0], ctx.typeType())

    def enterMethodDeclaration(self, ctx: JavaParserLabeled.MethodDeclarationContext):
        """A method is typed by its return type."""
        returns = ctx.typeTypeOrVoid()
        if returns is None:
            return
        self.record(ctx, ctx.IDENTIFIER().getText(), returns.typeType())
