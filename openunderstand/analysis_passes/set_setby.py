# expression -> NEW creator


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
        self.currentmethod = ""
        self.allsets = []
        self.counter = -1
        self.invardec = False
        self.inexp21 = False

    def enterMethodDeclaration(self, ctx: JavaParserLabeled.MethodDeclarationContext):
        self.currentmethod = ctx.IDENTIFIER().getText()

    def enterExpression21(self, ctx: JavaParserLabeled.Expression21Context):
        self.counter += 1
        self.allsets.append({"variable": None, "method": None, "line": None, "col": None})
        self.inexp21 = True

    def enterExpression2(self, ctx: JavaParserLabeled.Expression2Context):
        self.counter -= 1
        self.allsets.pop()
        self.inexp21 = False

    def exitExpression21(self, ctx: JavaParserLabeled.Expression21Context):
        self.inexp21 = False

    def enterPrimary4(self, ctx: JavaParserLabeled.Primary4Context):
        if self.inexp21:
            self.allsets[self.counter]["variable"] = ctx.IDENTIFIER().getText()
            self.allsets[self.counter]["method"] = self.currentmethod
            self.allsets[self.counter]["line"] = str(ctx.start).split(",")[3].split(":")[0]
            self.allsets[self.counter]["col"] = (str(ctx.start).split(",")[3].split(":")[1])[:-1]

    def enterVariableDeclarator(self, ctx: JavaParserLabeled.VariableDeclaratorContext):
        if str(ctx.ASSIGN()) == "=":
            self.counter += 1
            self.allsets.append({"variable": None, "method": None, "line": None, "col": None})
            self.invardec = True

    def exitVariableDeclarator(self, ctx: JavaParserLabeled.VariableDeclaratorContext):
        self.invardec = False

    def enterVariableDeclaratorId(self, ctx: JavaParserLabeled.VariableDeclaratorIdContext):
        if self.invardec:
            self.allsets[self.counter]["variable"] = ctx.IDENTIFIER().getText()
            self.allsets[self.counter]["method"] = self.currentmethod
            self.allsets[self.counter]["line"] = str(ctx.start).split(",")[3].split(":")[0]
            self.allsets[self.counter]["col"] = (str(ctx.start).split(",")[3].split(":")[1])[:-1]

    def enterExpression1(self, ctx: JavaParserLabeled.Expression1Context):
        if self.inexp21:
            self.allsets[self.counter]["variable"] = ctx.IDENTIFIER().getText()
            self.allsets[self.counter]["method"] = self.currentmethod
            self.allsets[self.counter]["line"] = str(ctx.start).split(",")[3].split(":")[0]
            self.allsets[self.counter]["col"] = (str(ctx.start).split(",")[3].split(":")[1])[:-1]
