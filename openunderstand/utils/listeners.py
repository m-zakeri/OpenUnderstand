from gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener
from utils.tools import get_parent_long_name


class FileIndexListener(JavaParserLabeledListener):
    def __init__(self):
        self.package_name = "(Unnamed_Package)"
        self.classes = []
        self.methods = []

        self.long_name = self.package_name

    @property
    def in_class(self) -> bool:
        return self.long_name != self.package_name

    def enterPackageDeclaration(self, ctx: JavaParserLabeled.PackageDeclarationContext):
        self.package_name = ctx.qualifiedName().getText()

    def exitPackageDeclaration(self, ctx: JavaParserLabeled.PackageDeclarationContext):
        self.long_name = self.package_name

    def enterClassDeclaration(self, ctx: JavaParserLabeled.ClassDeclarationContext):
        class_simple_name = ctx.IDENTIFIER().getText()
        self.long_name += f".{class_simple_name}"

        class_info = {
            "name": class_simple_name,
            "longname": self.long_name,
            "parent_longname": get_parent_long_name(self.long_name)
        }
        self.classes.append(class_info)

    def exitClassDeclaration(self, ctx: JavaParserLabeled.ClassDeclarationContext):
        self.long_name = get_parent_long_name(self.long_name)

    def enterConstructorDeclaration(self, ctx: JavaParserLabeled.ConstructorDeclarationContext):
        method_simple_name = ctx.IDENTIFIER().getText()
        self.long_name += f".{method_simple_name}"

    def exitConstructorDeclaration(self, ctx: JavaParserLabeled.ConstructorDeclarationContext):
        self.long_name = get_parent_long_name(self.long_name)
        print(self.long_name)

    def enterMethodDeclaration(self, ctx: JavaParserLabeled.MethodDeclarationContext):
        method_simple_name = ctx.IDENTIFIER().getText()
        self.long_name += f".{method_simple_name}"

    def exitMethodDeclaration(self, ctx: JavaParserLabeled.MethodDeclarationContext):
        self.long_name = get_parent_long_name(self.long_name)
