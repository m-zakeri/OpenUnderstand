# expression -> NEW creator


"""
## Description
This module find all OpenUnderstand call and callby references in a Java project


## References


"""

__author__ = 'Soheil Hoseini'
__version__ = '0.1.0'

from gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener
from gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
import analysis_passes.class_properties as class_properties


class SetPartialSetByPartial(JavaParserLabeledListener):

    def __init__(self):
        self.currentMethod = ""
        self.sourceClass = ""
        self.currentClass = ""
        self.partialsList = []

    @property
    def getPartialsList(self):
        return self.partialsList

    # Save the name of the current method
    def enterMethodDeclaration(self, ctx: JavaParserLabeled.MethodDeclarationContext):
        self.currentMethod = ctx.IDENTIFIER().getText()

    # Check if we have a field assignment
    def enterExpression21(self, ctx: JavaParserLabeled.Expression21Context):
        if ctx.ASSIGN() == "=" and ctx.getChild(0).Dot() == "0":
            instanceName = ctx.getChild(0).getChild(0).getChild(0).IDENTIFIER().getText()
            fieldName = ctx.getChild(0).IDENTIFIER().getText()
            self.partialsList.append({"currentMethod": self.currentMethod, "sourceClass": self.sourceClass
                                         , "currentClass": self.currentClass, "instanceName": instanceName
                                         , "fieldName": fieldName})

    # Save the name of the source class
    def enterClassOrInterfaceType(self, ctx: JavaParserLabeled.ClassOrInterfaceTypeContext):
        self.sourceClass = ctx.IDENTIFIER().getText()

    # Save the name of the current class
    def enterClassDeclaration(self, ctx: JavaParserLabeled.ClassDeclarationContext):
        self.currentClass = ctx.IDENTIFIER().getText()
