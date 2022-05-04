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

class SetPartial_SetPartialby(JavaParserLabeledListener):
    def __init__(self):
        self.parentMethod = ""
        self.varList = []

    def enterExpression21(self, ctx:JavaParserLabeled.Expression21Context):
        pass
