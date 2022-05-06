# expression -> NEW creator


"""
## Description
This module find all OpenUnderstand call and callby references in a Java project


## References


"""

__author__ = 'Mohammad ali Samadi'
__version__ = '0.1.0'

from gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener
from gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
import analysis_passes.class_properties as class_properties

class Setpartial_Setpartialby(JavaParserLabeledListener):
    def __init__(self):
        self.Currentmethod = ""
        self.setpartial = []
        self.dict = []

    @property
    def get_dict(self):
        return self.dict

    @property
    def get_Currentmethod(self):
        return self.Currentmethod

    @property
    def get_setpartial(self):
        return self.setpartial

    def enterMethodDeclaration(self, ctx: JavaParserLabeled.MethodDeclarationContext):
        self.Currentmethod = ctx.IDENTIFIER().getText()

    def enterExpression2(self, ctx: JavaParserLabeled.Expression21Context):
        self.setpartial.append(self, ctx.getChild(0).IDENTIFIER().getText())
        self.dict.append(self, dict(zip(self.Currentmethod, self.setpartial)))
