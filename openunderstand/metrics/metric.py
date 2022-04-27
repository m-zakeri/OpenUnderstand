from openunderstand.gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from openunderstand.gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener


class DSCmetric(JavaParserLabeledListener):
    def __init__(self):
        self.arr = []
        self.tmp = []
        self.null = []

    @property
    def get_arr(self):
        return self.arr

    @property
    def get_tmp(self):
        return self.tmp


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