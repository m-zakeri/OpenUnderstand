from openunderstand.gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener
from openunderstand.gen.javaLabeled.JavaParserLabeled import JavaParserLabeled


class DSCmetric(JavaParserLabeledListener):
    def __init__(self):
        self.currentmethod=""

    def enterMethodDeclaration(self, ctx: JavaParserLabeled.MethodDeclarationContext):
        self.currentmethod=ctx.IDENTIFIER().getText()


    def enterExpression21(self, ctx:JavaParserLabeled.Expression21Context):
        try:
            if str(ctx.ASSIGN())=='=':
                print("--------------------------------")
                try:
                    print("variable=" + ctx.getChild(0).getChild(0).IDENTIFIER().getText())
                    print("method=" + self.currentmethod)
                    print("line=" + str(ctx.start).split(",")[3].split(":")[0])
                    print("col=" + str(ctx.start).split(",")[3].split(":")[1])

                except:
                    print("variable=" + str(ctx.getChild(0).getChild(2)))
                    print("method=" + self.currentmethod)
                    print("line=" + str(ctx.start).split(",")[3].split(":")[0])
                    print("col=" + str(ctx.start).split(",")[3].split(":")[1])
                print("--------------------------------")
        except:
            print("undiscovered state")

    def enterVariableDeclarator(self, ctx:JavaParserLabeled.VariableDeclaratorContext):
        if (str(ctx.ASSIGN())=="="):
            print("--------------------------------")
            print("variable=" + str(ctx.variableDeclaratorId().getChild(0)))
            print("method=" + self.currentmethod)
            print("line=" + str(ctx.start).split(",")[3].split(":")[0])
            print("col=" + str(ctx.start).split(",")[3].split(":")[1])
            print("--------------------------------")

