from gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener
from gen.javaLabeled.JavaParserLabeled import JavaParserLabeled


class ImplementClassNames(JavaParserLabeledListener):

    class_names = []

    def enterClassDeclaration(self, ctx: JavaParserLabeled.ClassDeclarationContext):
        self.class_names.append(ctx.IDENTIFIER().getText())