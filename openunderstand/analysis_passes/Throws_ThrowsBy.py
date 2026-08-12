"""Java Throw / Java Throwby: the exceptions a declaration says it throws.

Understand records one reference per exception in a `throws` clause, scoped to
the *method* and positioned on the exception's own token:

    AESEncryption.java:84:14  scope=ciphers.AESEncryption.decryptText
                              ent=java.security.NoSuchAlgorithmException

The previous implementation took `qualifiedNameList().getText().split(",")[-1]`
-- only the *last* exception of the clause -- stored it as the bare written
text, scoped it to the enclosing class, and positioned it at the method's own
start token. It produced 2 rows against Understand's 23 on TheAlgorithms and
none of them matched.

It also resolved each name by walking the project directory for a matching
file and slicing the path at a hard-coded "org" component, which raised
`'org' is not in list` on any project not rooted at org/. The glue swallowed
that, so the pass silently produced nothing at all for those files.
"""

from openunderstand.gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener
from openunderstand.gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
import openunderstand.analysis_passes.class_properties as class_properties


class Throws_TrowsBy(JavaParserLabeledListener):
    def __init__(self):
        #: Positioned relations, written by Project.addTypeRelationRefs.
        self.relations = []
        #: Retained for callers that still read it; nothing populates it now.
        self.implement = []
        self.imports = {}
        self.wildcards = []

    def enterImportDeclaration(self, ctx: JavaParserLabeled.ImportDeclarationContext):
        longname = ctx.qualifiedName().getText()
        if ctx.getText().rstrip(";").endswith(".*"):
            self.wildcards.append(longname)
            return
        self.imports[longname.split(".")[-1]] = longname

    # ------------------------------------------------------------- the shapes

    def enterMethodDeclaration(self, ctx: JavaParserLabeled.MethodDeclarationContext):
        self._record(ctx)

    def enterConstructorDeclaration(
        self, ctx: JavaParserLabeled.ConstructorDeclarationContext
    ):
        self._record(ctx)

    def enterInterfaceMethodDeclaration(
        self, ctx: JavaParserLabeled.InterfaceMethodDeclarationContext
    ):
        self._record(ctx)

    # ------------------------------------------------------------------ guts

    def _record(self, ctx):
        names = getattr(ctx, "qualifiedNameList", None)
        names = names() if callable(names) else None
        if names is None:
            return
        identifier = ctx.IDENTIFIER()
        if identifier is None or isinstance(identifier, list):
            return

        from openunderstand.ounderstand import symbol_table

        parents = class_properties.ClassPropertiesListener.findParents(ctx)
        scope_longname = ".".join(parents + [identifier.getText()])
        for qualified in names.qualifiedName():
            longname = symbol_table.resolve_type_name(
                qualified.getText(), self.imports, self.wildcards, scope_longname)
            if longname is None:
                continue
            token = qualified.start
            self.relations.append({
                "kind": "Java Throw",
                "scope_longname": scope_longname,
                "ent_longname": longname,
                "name": longname.rsplit(".", 1)[-1],
                "line": token.line,
                "col": token.column,
            })
