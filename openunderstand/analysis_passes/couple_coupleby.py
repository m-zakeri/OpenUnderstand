"""
## Description
This module find all OpenUnderstand call and callby references in a Java project


## References


"""

__author__ = 'Shaghayegh Mobasher , Setayesh kouloubandi ,Parisa Alaie'
__version__ = '0.1.0'

from gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener
from gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
import analysis_passes.class_properties as class_properties


class ImplementCoupleAndImplementByCoupleBy(JavaParserLabeledListener):
    """
    #Todo: Implementing the ANTLR listener pass for Java Call and Java Callby reference kind
    """
    implement = []

    def enterClassDeclaration(self, ctx:JavaParserLabeled.ClassDeclarationContext):
        if ctx.IMPLEMENTS():
            scope_parents = class_properties.ClassPropertiesListener.findParents(ctx)
            if len(scope_parents) == 1:
                scope_longname = scope_parents[0]
            else:
                scope_longname = ".".join(scope_parents)

            [line, col] = str(ctx.start).split(",")[3].split(":")
            for myType in ctx.typeList().typeType():
                if myType.classOrInterfaceType():
                    myType_longname = ".".join([x.getText() for x in myType.classOrInterfaceType().IDENTIFIER()])
                    self.implement.append({"scope_kind": "Class", "scope_name": ctx.IDENTIFIER().__str__(),
                                           "scope_longname": scope_longname,
                                           "scope_parent": scope_parents[-2] if len(scope_parents) > 2 else None,
                                           "scope_contents": ctx.getText(),
                                           "scope_modifiers":
                                               class_properties.ClassPropertiesListener.findClassOrInterfaceModifiers(ctx),
                                           "line": line,
                                           "col": col[:-1],
                                           "type_ent_longname": myType_longname})

    def enterEnumDeclaration(self, ctx:JavaParserLabeled.EnumDeclarationContext):
        if ctx.IMPLEMENTS():
            scope_parents = class_properties.ClassPropertiesListener.findParents(ctx)
            if len(scope_parents) == 1:
                scope_longname = scope_parents[0]
            else:
                scope_longname = ".".join(scope_parents)

            [line, col] = str(ctx.start).split(",")[3].split(":")  # line, column
            for myType in ctx.typeList().typeType():
                if myType.classOrInterfaceType():
                    myType_longname = ".".join([x.getText() for x in myType.classOrInterfaceType().IDENTIFIER()])
                    self.implement.append({"scope_kind": "Enum", "scope_name": ctx.IDENTIFIER().__str__(),
                                           "scope_longname": scope_longname,
                                           "scope_parent": scope_parents[-2] if len(scope_parents) > 2 else None,
                                           "scope_contents": ctx.getText(),
                                           "scope_modifiers":
                                               class_properties.ClassPropertiesListener.findClassOrInterfaceModifiers(
                                                   ctx),
                                           "line": line,
                                           "col": col[:-1],
                                           "type_ent_longname": myType_longname})
