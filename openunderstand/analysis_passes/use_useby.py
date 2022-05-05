from gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener


class UseAndUseByListener(JavaParserLabeledListener):
    def __init__(self, file_name):
        self.file_name = file_name
        # self.use = []
        self.useBy = []

    @property
    def get_use(self):
        d = {}
        # d['use'] = self.use
        d['useBy'] = self.useBy
        return d


    def enterPrimary4(self, ctx: JavaParserLabeled.Primary4Context):
        # ==========used/usedby=============
        is_None = False
        VI = ctx

        while (type(ctx) != JavaParserLabeled.ClassDeclarationContext and type(
                ctx) != JavaParserLabeled.MethodDeclarationContext):
            if(ctx.parentCtx):
                ctx = ctx.parentCtx
            else:
                is_None = True
                break


        if(not is_None):
            line1 = VI.IDENTIFIER().symbol.line
            column1 = VI.IDENTIFIER().symbol.column
            line2 = ctx.IDENTIFIER().symbol.line
            column2 = ctx.IDENTIFIER().symbol.column

            # self.use.append((ctx.IDENTIFIER().getText(), VI.getText()))
            self.useBy.append((VI.getText(), ctx.IDENTIFIER().getText(), line1, column1, line2, column2))