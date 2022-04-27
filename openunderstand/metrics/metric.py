from openunderstand.gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from openunderstand.gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener


class DSCmetric(JavaParserLabeledListener):
    def __init__(self):
        self.arr = []
        self.tmp = []
        self.name = []
        self.null = []
        self.mmd = []

    @property
    def get_arr(self):
        return self.arr

    @property
    def get_tmp(self):
        return self.tmp

    @property
    def get_name(self):
        return self.name

    @property
    def get_mmd(self):
        return self.mmd


    def enterBlockStatement1(self, ctx:JavaParserLabeled.BlockStatement1Context):
        try:
            self.arr.append(ctx.statement().RETURN().getText())
        except:
            pass

    def enterPrimary4(self, ctx:JavaParserLabeled.Primary4Context):
        parent = ctx.parentCtx
        parent = parent.parentCtx

        try:
            self.null.append(parent.RETURN().getText())
            self.tmp.append(ctx.getText())

        except:
            pass

    def enterExpression21(self, ctx:JavaParserLabeled.Expression21Context):
        if(ctx.ASSIGN().getText()=="="):
            parent = ctx.parentCtx
            parent = parent.parentCtx
            parent = parent.parentCtx
            parent = parent.parentCtx
            parent = parent.parentCtx
            parent = parent.parentCtx

            #remove constructor
            try:
                parent.memberDeclaration().constructorDeclaration()

            except:
                self.mmd.append(ctx.getChild(2).getText())



    def enterMethodDeclaration(self, ctx: JavaParserLabeled.MethodDeclarationContext):
        self.name.append(ctx.IDENTIFIER().getText())
