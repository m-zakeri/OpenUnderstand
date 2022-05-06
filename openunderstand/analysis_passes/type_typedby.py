from gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener


class TypedAndTypedByListener(JavaParserLabeledListener):
    def __init__(self, file_name):
        self.file_name = file_name
        self.package_name = ""
        # self.typed = []
        self.typedBy = []

    @property
    def get_type(self):
        d = {}
        # d['typed'] = self.typed
        d['typedBy'] = self.typedBy
        return d

    def enterPackageDeclaration(self, ctx:JavaParserLabeled.PackageDeclarationContext):
        self.package_name = ctx.getText().replace("package", "").replace(";", "")

    def enterFieldDeclaration(self, ctx: JavaParserLabeled.FieldDeclarationContext):
        # ==========typed/typedby=============
        ctx1 = ctx.variableDeclarators()
        ctx11 = ctx1.variableDeclarator()[0].variableDeclaratorId()
        ctx2 = ctx.typeType()

        line2 = ctx2.children[0].children[0].symbol.line
        column2 = ctx2.children[0].children[0].symbol.column
        line1 = ctx11.IDENTIFIER().symbol.line
        column1 = ctx11.IDENTIFIER().symbol.column

        self.typedBy.append((ctx11.getText(), ctx2.getText(), line1, column1, line2, column2, self.package_name))
        # self.typed.append((ctx2.getText(), ctx11.getText()))

    # khode enum
    def enterEnumDeclaration(self, ctx: JavaParserLabeled.EnumDeclarationContext):
        name = ctx.IDENTIFIER()
        type = ctx.ENUM()

        line2 = ctx.ENUM().symbol.line
        column2 = ctx.ENUM().symbol.column
        line1 = ctx.IDENTIFIER().symbol.line
        column1 = ctx.IDENTIFIER().symbol.column

        self.typedBy.append((ctx.IDENTIFIER().getText(), type.getText(), line1, column1, line2, column2, self.package_name))

    # type haye enum
    def enterEnumConstant(self, ctx: JavaParserLabeled.EnumConstantContext):
        # type enum
        enum_type = ctx.IDENTIFIER()
        # esme khode enum
        pctx = ctx.parentCtx.parentCtx

        line2 = enum_type.symbol.line
        column2 = enum_type.symbol.column
        line1 = pctx.IDENTIFIER().symbol.line
        column1 = pctx.IDENTIFIER().symbol.column

        self.typedBy.append((pctx.IDENTIFIER().getText(), ctx.getText(), line1, column1, line2, column2, self.package_name))

    def enterMethodDeclaration(self, ctx: JavaParserLabeled.MethodDeclarationContext):
        # method types
        t = ctx.typeTypeOrVoid()
        try:

            ctx2 = t.typeType()

            line2 = ctx2.children[0].children[0].symbol.line
            column2 = ctx2.children[0].children[0].symbol.column
            line1 = ctx.IDENTIFIER().symbol.line
            column1 = ctx.IDENTIFIER().symbol.column
        except:
            ctx2 = t.VOID()

            line2 = t.children[0].symbol.line
            column2 = t.children[0].symbol.column
            line1 = ctx.IDENTIFIER().symbol.line
            column1 = ctx.IDENTIFIER().symbol.column

        self.typedBy.append((ctx.IDENTIFIER().getText(), ctx2.getText(), line1, column1, line2, column2, self.package_name))

    def enterFormalParameter(self, ctx: JavaParserLabeled.FormalParameterContext):
        ctx1 = ctx.variableDeclaratorId()
        ctx2 = ctx.typeType()

        line2 = ctx2.children[0].children[0].symbol.line
        column2 = ctx2.children[0].children[0].symbol.column
        line1 = ctx1.IDENTIFIER().symbol.line
        column1 = ctx1.IDENTIFIER().symbol.column

        self.typedBy.append((ctx1.getText(), ctx2.getText(), line1, column1, line2, column2, self.package_name))

    def enterLocalVariableDeclaration(self, ctx: JavaParserLabeled.LocalVariableDeclarationContext):
        # baraye try va catch va function
        ctx1 = ctx.variableDeclarators()
        ctx11 = ctx1.variableDeclarator()[0].variableDeclaratorId()
        ctx2 = ctx.typeType()

        line2 = ctx2.children[0].children[0].symbol.line
        column2 = ctx2.children[0].children[0].symbol.column
        line1 = ctx11.IDENTIFIER().symbol.line
        column1 = ctx11.IDENTIFIER().symbol.column

        self.typedBy.append((ctx11.getText(), ctx2.getText(), line1, column1, line2, column2, self.package_name))