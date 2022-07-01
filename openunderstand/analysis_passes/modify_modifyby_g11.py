# expression -> NEW creator


"""
## Description
This module find all OpenUnderstand call and callby references in a Java project


## References


"""

__author__ = 'Shaghayegh Mobasher , Setayesh kouloubandi ,Parisa Alaie'
__version__ = '0.1.0'

from openunderstand.gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener
from openunderstand.gen.javaLabeled.JavaParserLabeled import JavaParserLabeled


class ModifyModifyByListener(JavaParserLabeledListener):
    """
    #Todo: Implementing the ANTLR listener pass for Java Call and Java Callby reference kind

    """
    modifyBy = []
    scope = None
    ent = None
    isE7 = False

    def enterClassDeclaration(self, ctx:JavaParserLabeled.ClassDeclarationContext):
        self.scope = ctx.IDENTIFIER().getText()
        # print(self.scope)

    def enterMethodDeclaration(self, ctx: JavaParserLabeled.MethodDeclarationContext):
        self.scope = ctx.IDENTIFIER().getText()
        # print(self.scope)

    def enterExpression0(self, ctx:JavaParserLabeled.Expression0Context):
        self.ent = ctx.getText()

    def exitExpression0(self, ctx:JavaParserLabeled.Expression0Context):
        if self.isE7:
            line_col = str(ctx.children[1].start).split(",")[3][:-1].split(':')
            # print("Modify ----", end=" ")
            # print("Expression 7 ->", line_col, self.scope)
            self.modifyBy.append({
                "scope": self.scope, "ent": self.ent,
                "line": line_col[0], "col": line_col[1]
            })

    def enterExpression6(self, ctx: JavaParserLabeled.Expression6Context):
        self.isE7 = False
        line_col = str(ctx.children[0].start).split(",")[3][:-1].split(':')
        # print("Modify ----", end=" ")
        # print("Expression 6 ->", line_col, self.scope)
        self.modifyBy.append({
            "scope": self.scope, "ent": self.ent,
            "line": line_col[0], "col": line_col[1]
        })

    def enterExpression7(self, ctx: JavaParserLabeled.Expression7Context):
        self.isE7 = True

    def enterExpression21(self, ctx: JavaParserLabeled.Expression21Context):
        self.isE7 = False
        operations = ['+=', '-=', '/=', '*=', '&=', '|=', '^=', '%=']
        line_col = str(ctx.children[0].start).split(",")[3][:-1].split(':')
        if ctx.children[1].getText() in operations:
            # print("Modify ----", end=" ")
            # print("Expression 21 ->", line_col, self.scope)
            self.modifyBy.append({
                "scope": self.scope, "ent": self.ent,
                "line": line_col[0], "col": line_col[1]
            })
