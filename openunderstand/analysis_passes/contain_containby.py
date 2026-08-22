from openunderstand.gen.javaLabeled.JavaParserLabeledListener import (
    JavaParserLabeledListener,
)
from openunderstand.gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
import openunderstand.analysis_passes.class_properties as class_properties


class ContainAndContainBy(JavaParserLabeledListener):
    def __init__(self):
        self.contain = []
        self.packageInfo = []

    def enterPackageDeclaration(self, ctx: JavaParserLabeled.PackageDeclarationContext):
        self.packageInfo = []
        longname = ""
        for x in range(len(ctx.qualifiedName().IDENTIFIER())):
            if x == 0:
                longname = str(ctx.qualifiedName().IDENTIFIER()[x])
            else:
                longname = longname + "." + str(ctx.qualifiedName().IDENTIFIER()[x])

        self.packageInfo.append(
            {
                "name": ctx.qualifiedName().IDENTIFIER()[-1],
                "longname": longname,
                "kind": "Package",
                "contents": "",
                "parent": None,
                "type": "Package",
                "value": None,
            }
        )

    def enterClassDeclaration(self, ctx: JavaParserLabeled.ClassDeclarationContext):
        self._record(ctx, "Class")

    # A package contains every type it declares, not only its classes.
    # Understand writes Contain for `interface JSONString` at the same
    # position it writes Define, and this pass handled `class` alone -- so
    # org.json's four interfaces and annotations had no container, and
    # CountDeclClass reported 24 against Understand's 30.
    def enterInterfaceDeclaration(
        self, ctx: JavaParserLabeled.InterfaceDeclarationContext
    ):
        self._record(ctx, "Interface")

    def enterAnnotationTypeDeclaration(
        self, ctx: JavaParserLabeled.AnnotationTypeDeclarationContext
    ):
        self._record(ctx, "Annotation")

    def enterEnumDeclaration(self, ctx: JavaParserLabeled.EnumDeclarationContext):
        self._record(ctx, "Enum")

    def _record(self, ctx, kind):
        name = ctx.IDENTIFIER().getText()
        # The reference sits on the class's name, not on the `class` keyword:
        # ctx.start put every one of these exactly len("class ") = 6 columns
        # to the left of where Understand reports it.
        line = ctx.IDENTIFIER().symbol.line
        col = ctx.IDENTIFIER().symbol.column
        scope_parents = class_properties.ClassPropertiesListener.findParents(ctx)

        if len(scope_parents) == 1:
            scope_longname = scope_parents[0]
        else:
            scope_longname = ".".join(scope_parents)

        # findParents() already yields the package components followed by any
        # enclosing types, but stops short of this class. So the fully
        # qualified name is those parents plus this class's own name --
        # prefixing packageLongName here produced "org.json.org.json", and
        # omitting `name` left the class's longname pointing at its package.
        scope_longname = ".".join(scope_parents + [name])
        if not self.packageInfo:
            # No `package` declaration, so the class is in the default package
            # and there is no package entity to contain it. This indexed [0]
            # unconditionally and raised IndexError, which the glue logged and
            # swallowed -- taking the whole pass down for all 7 default-package
            # files on TheAlgorithms, Kruskal and BSTIterative among them.
            return
        packageName = self.packageInfo[0]["name"]
        packageLongName = self.packageInfo[0]["longname"]
        packageKind = self.packageInfo[0]["kind"]
        packageContent = self.packageInfo[0]["contents"]
        packageParent = self.packageInfo[0]["parent"]
        packageType = self.packageInfo[0]["type"]
        packageValue = self.packageInfo[0]["value"]

        parent = scope_parents[-2] if len(scope_parents) > 2 else None
        modifiers = (
            class_properties.ClassPropertiesListener.findClassOrInterfaceModifiers(ctx)
        )
        content = ctx.getText()

        self.contain.append(
            {
                "package_name": packageName.getText(),
                "package_longname": packageLongName,
                "package_kind": packageKind,
                "package_content": packageContent,
                "package_parent": packageParent,
                "package_type": packageType,
                "package_value": packageValue,
                "name": name,
                "longname": scope_longname,
                "parent": parent,
                "kind": kind,
                "line": line,
                "col": col,
                "modifiers": modifiers,
                "content": content,
                "type": kind,
                "value": None,
            }
        )
