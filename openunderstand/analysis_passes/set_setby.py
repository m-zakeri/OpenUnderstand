

#expression -> NEW creator


"""
## Description
This module find all OpenUnderstand call and callby references in a Java project


## References


"""

__author__ = 'Amirhossein Derakhshan'
__version__ = '0.1.0'

from gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener
from gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
import analysis_passes.class_properties as class_properties


class Set_Setby(JavaParserLabeledListener):
    def __init__(self):
        self.currentmethod=""

    def enterMethodDeclaration(self, ctx: JavaParserLabeled.MethodDeclarationContext):
        self.functions.append(ctx.IDENTIFIER().getText())
        self.currentmethod=ctx.IDENTIFIER().getText()

    def enterExpression21(self, ctx:JavaParserLabeled.Expression21Context):
        try:
            if str(ctx.ASSIGN()) == "=":
                print("--------------------------------")
                try:
                    print("variable=" + ctx.getChild(0).getChild(0).IDENTIFIER().getText())
                    print("method=" + self.currentmethod)
                except:
                    print("variable=" + str(ctx.getChild(0).getChild(2)))
                    print("method=" + self.currentmethod)
                print("--------------------------------")
        except:
            print("undiscovered state")

    def enterVariableDeclarator(self, ctx:JavaParserLabeled.VariableDeclaratorContext):
        if str(ctx.ASSIGN()) == "=":
            print("--------------------------------")
            print("variable=" + str(ctx.variableDeclaratorId().getChild(0)))
            print("method=" + self.currentmethod)
            print()
            print("--------------------------------")



