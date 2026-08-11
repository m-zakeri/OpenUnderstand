from openunderstand.gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from openunderstand.gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener
from openunderstand.analysis_passes import class_properties


class UseAndUseByListener(JavaParserLabeledListener):
    """Collect every bare-identifier read: `Java Use` / `Java Useby`.

    Understand puts a Use at the *use site*, scoped to the method containing
    it, pointing at the entity being read:

        CDL.java:61:18  scope=org.json.CDL.getValue  ent=org.json.CDL.getValue.c

    This pass used to report the position of the enclosing *declaration*
    instead, so every read of `c` inside `getValue` collapsed onto one row --
    903 rows where Understand has 1810. It also recorded only the simple name
    and the package, so the used variable's long name came out `org.json.c`,
    shared by every `c` in the project.
    """

    def __init__(self):
        self.package_name = ""
        self.useBy = []

    @property
    def get_use(self):
        d = {}
        d["useBy"] = self.useBy
        return d

    def enterPackageDeclaration(self, ctx: JavaParserLabeled.PackageDeclarationContext):
        self.package_name = ctx.getText().replace("package", "").replace(";", "")

    def enterPrimary4(self, ctx: JavaParserLabeled.Primary4Context):
        identifier = ctx.IDENTIFIER()
        # findParents() walks to the enclosing scopes and prefixes the package,
        # so a read inside CDL.getValue yields ["org","json","CDL","getValue"]
        # -- nested classes included. The old walk up to the first
        # ClassDeclaration/MethodDeclaration kept only that one identifier.
        scope_longname = ".".join(
            class_properties.ClassPropertiesListener.findParents(ctx)
        )
        if not scope_longname:
            return
        self.useBy.append(
            {
                "name": identifier.getText(),
                "scope_longname": scope_longname,
                "line": identifier.symbol.line,
                "column": identifier.symbol.column,
                "package": self.package_name,
            }
        )
