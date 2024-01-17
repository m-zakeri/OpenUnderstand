from gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener
from analysis_passes.entity_manager_g11 import get_created_entity_longname


class ModifyListener(JavaParserLabeledListener):
    def __init__(self, entity_manager_object):
        self.entity_manager = entity_manager_object
        self.package = ""
        self._class = ""
        self.parent = ""
        self.name = ""
        self.enter_modify = False
        self.modify = []

    # package
    def enterPackageDeclaration(self, ctx: JavaParserLabeled.PackageDeclarationContext):

        self.package = ctx.qualifiedName().getText()

    # class parent
    def enterClassDeclaration(self, ctx: JavaParserLabeled.ClassDeclarationContext):

        self._class = ctx.IDENTIFIER().getText() + "."

        self.parent = ctx.IDENTIFIER().getText()

    # exit class parent
    def exitClassDeclaration(self, ctx: JavaParserLabeled.ClassDeclarationContext):

        self._class = ""

    # method parent
    def enterMethodDeclaration(self, ctx: JavaParserLabeled.MethodDeclarationContext):

        self.parent = self._class + ctx.IDENTIFIER().getText()

    # interface parent
    def enterInterfaceDeclaration(
        self, ctx: JavaParserLabeled.InterfaceDeclarationContext
    ):

        self.parent = ctx.IDENTIFIER().getText()

    def enterExpression1(self, ctx: JavaParserLabeled.Expression1Context):

        if self.enter_modify:

            self.name = ctx.IDENTIFIER().getText()

    def enterExpression6(self, ctx: JavaParserLabeled.Expression6Context):

        [line, col] = str(ctx.start).split(",")[3].split(":")

        parents = self.entity_manager.get_or_create_parent_entities(ctx)

        parent = parents[-1][1]

        name = (
            ctx.expression().getText().replace("this", "").replace(".", "").lstrip("_")
        )

        longname = self.package + "." + self.parent + "." + name

        self.modify.append(
            {
                "kind": 208,
                "file": self.entity_manager.file_ent,
                "line": line,
                "column": col.replace("]", ""),
                "ent": longname,
                "scope": parent[0],
                "modifiers": None
            }
        )

    def enterExpression7(self, ctx: JavaParserLabeled.Expression7Context):

        [line, col] = str(ctx.start).split(",")[3].split(":")

        parents = self.entity_manager.get_or_create_parent_entities(ctx)

        parent = parents[-1][1]

        name = (
            ctx.expression().getText().replace("this", "").replace(".", "").lstrip("_")
        )

        longname = self.package + "." + self.parent + "." + name

        if name not in ["1", "2", "3", "4", "5", "6", "7", "8", "9"]:

            self.modify.append(
                {
                    "kind": 208,
                    "file": self.entity_manager.file_ent,
                    "line": line,
                    "column": col.replace("]", ""),
                    "ent": longname,
                    "scope": parent[0],
                    "modifiers":None
                }
            )

    def enterExpression21(self, ctx: JavaParserLabeled.Expression21Context):

        operations = ["+=", "-=", "/=", "*=", "&=", "|=", "^=", "%="]

        if ctx.children[1].getText() in operations:

            name = (
                ctx.expression()[0]
                .getText()
                .replace("this", "")
                .replace(".", "")
                .lstrip("_")
            )

            longname = self.package + "." + self.parent + "." + name

            [line, col] = str(ctx.start).split(",")[3].split(":")

            parents = self.entity_manager.get_or_create_parent_entities(ctx)

            parent = parents[-1][1]

            self.modify.append(
                {
                    "kind": 208,
                    "file": self.entity_manager.file_ent,
                    "line": line,
                    "column": col.replace("]", ""),
                    "ent": longname,
                    "scope": parent[0],
                    "modifiers":None
                }
            )

    def exitExpression6(self, ctx: JavaParserLabeled.Expression6Context):

        self.enter_modify = False

    def exitExpression7(self, ctx: JavaParserLabeled.Expression7Context):

        self.enter_modify = False

    def exitExpression21(self, ctx: JavaParserLabeled.Expression21Context):
        self.enter_modify = False

    @staticmethod
    def get_different_combinations(longname):

        names_array = longname.split(".")
        variable_name = names_array[-1]
        for i in range(1, len(names_array)):
            candidate_longname = ".".join(names_array[0 : len(names_array) - i])
            ent = get_created_entity_longname(candidate_longname + "." + variable_name)
            if ent is not None:
                return ent
        return None
