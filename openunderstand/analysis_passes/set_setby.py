# expression -> NEW creator


"""
## Description
This module find all OpenUnderstand set and setby references in a Java project


## References


"""

__author__ = 'Amirhossein Derakhshan ,Mojtaba Safari'
__version__ = '0.1.0'

from gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener
from gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
import analysis_passes.class_properties as class_properties


class Set_Setby(JavaParserLabeledListener):
    """
    #Todo: Implementing the ANTLR listener pass for Java set and Java setby reference kind
    """

    def __init__(self):
        self.current_method = ""
        self.all_sets = []

    def enterMethodDeclaration(self, ctx: JavaParserLabeled.MethodDeclarationContext):
        self.current_method = ctx.IDENTIFIER().getText()

    def enterExpression21(self, ctx: JavaParserLabeled.Expression21Context):
        try:
            if str(ctx.ASSIGN()) == "=":
                # print("--------------------------------")
                try:
                    self.all_sets.append({"variable": ctx.getChild(0).getChild(0).IDENTIFIER().getText()
                                             , "method": self.current_method})
                    # print("variable=" + ctx.getChild(0).getChild(0).IDENTIFIER().getText())
                    # print("method=" + self.current_method)
                except:
                    self.all_sets.append({"variable": str(ctx.getChild(0).getChild(2)),
                                          "method": self.current_method})
                    # print("variable=" + str(ctx.getChild(0).getChild(2)))
                    # print("method=" + self.current_method)
                # print("--------------------------------")
        except:
            return {"variable": "undiscovered state",
                    "method": self.current_method}

    def enterVariableDeclarator(self, ctx: JavaParserLabeled.VariableDeclaratorContext):
        if str(ctx.ASSIGN()) == "=":
            # print("--------------------------------")
            str(ctx.start).split(",")[3].split(":")
            self.all_sets.append({"variable": str(ctx.variableDeclaratorId().getChild(0)),
                                  "method": self.current_method,
                                  "line": str(ctx.start).split(",")[3].split(":")[0],
                                  "col": str(ctx.start).split(",")[3].split(":")[1]})
            # print("variable=" + str(ctx.variableDeclaratorId().getChild(0)))
            # print("method=" + self.current_method)
            # print()
            # print("--------------------------------")
