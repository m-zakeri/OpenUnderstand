from gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener


class TypedAndTypedByListener(JavaParserLabeledListener):
    def __init__(self, file_name):
        self.file_name = file_name
        # self.typed = []
        self.typedBy = []

    @property
    def get_type(self):
        d = {}
        # d['typed'] = self.typed
        d['typedBy'] = self.typedBy
        return d

    def enterFieldDeclaration(self, ctx: JavaParserLabeled.FieldDeclarationContext):
        # ==========typed/typedby=============
        ctx1 = ctx.variableDeclarators()
        ctx11 = ctx1.variableDeclarator()[0].variableDeclaratorId()
        ctx2 = ctx.typeType()

        line2 = ctx2.children[0].children[0].symbol.line
        column2 = ctx2.children[0].children[0].symbol.column
        line1 = ctx11.IDENTIFIER().symbol.line
        column1 = ctx11.IDENTIFIER().symbol.column

        self.typedBy.append((ctx11.getText(), ctx2.getText(), line1, column1, line2, column2))
        # self.typed.append((ctx2.getText(), ctx11.getText()))



