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
        line = ctx.IDENTIFIER().symbol.line
        col = ctx.IDENTIFIER().symbol.column
        scope_parents = class_properties.ClassPropertiesListener.findParents(ctx)

        if len(scope_parents) == 1:
            scope_longname = scope_parents[0]
        else:
            scope_longname = ".".join(scope_parents)

        scope_longname = ".".join(scope_parents + [name])
        if not self.packageInfo:
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
