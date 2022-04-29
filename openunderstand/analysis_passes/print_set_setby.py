from  gen.JavaParserLabeled import  JavaParserLabeled
from  gen.JavaParserLabeledListener import JavaParserLabeledListener


class DSCmetric(JavaParserLabeledListener):
    def __init__(self):
        self.dc=0
        self.functions=[]
        self.classname=dict()
        self.currentclass=""
        self.currentmethod=""

    def enterClassDeclaration(self, ctx:JavaParserLabeled.ClassDeclarationContext):
        self.dc+=1
        self.classname[ctx.IDENTIFIER().__str__()]=0
        self.currentclass=ctx.IDENTIFIER().__str__()


    def enterFieldDeclaration(self, ctx:JavaParserLabeled.FieldDeclarationContext):
        self.classname[self.currentclass]+=1


    def enterMethodDeclaration(self, ctx: JavaParserLabeled.MethodDeclarationContext):
        self.functions.append(ctx.IDENTIFIER().getText())
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

