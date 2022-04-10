from openunderstand.gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener
from openunderstand.gen.javaLabeled.JavaParserLabeled import JavaParserLabeled

class CastAndCastByListener(JavaParserLabeledListener):
    cast = []


    def findParentClassOrMethod(ctx):
        parent = ""
        while(ctx is not None):
            if(type(ctx).__name__ == "ClassDeclarationContext" or type(ctx).__name__=="MethodDeclarationContext"):
                parent = ctx.IDENTIFIER().getText()
            ctx = ctx.parentCtx
        return parent

    def enterExpression5(self, ctx:JavaParserLabeled.Expression5Context):
        castTo = ctx.typeType().__name__
        parentClassContainsTheCast = CastAndCastByListener.findParentClassOrInterface(ctx)
        """in this state we have the name of the referenced class and the referenced by class .
        the data of each class and the insertion to database => todo
        """